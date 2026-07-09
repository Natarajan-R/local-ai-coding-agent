# Architecture

A local-first, autonomous AI coding agent built as a **finite state machine**
around a local LLM (Ollama). This document is the reference map of how it works.

- [Control loop (FSM)](#control-loop-fsm)
- [Component map](#component-map)
- [Phases](#phases-orchestrator)
- [Tools](#tools)
- [Code understanding: AST + tree-sitter + LSP](#code-understanding)
- [Sandbox](#sandbox)
- [Guardrails](#guardrails)
- [Reliability & observability](#reliability--observability)
- [Extension points](#extension-points)

## Control loop (FSM)

```text
IDLE ──start──▶ PLANNING ──plan_ready──▶ EXECUTING ──execution_done──▶ EVALUATING
                                             ▲                              │
                                       retry │                       passed │ failed
                                             │                              ▼
                                         REFLEXING ◀───────failed────────  DONE
                                             │ give_up
                                             ▼
                                           ERROR
```

Terminal states: `DONE`, `ERROR`, `ABORTED`. Transitions are an explicit table in
[fsm.py](src/agent/fsm.py); an invalid transition raises rather than silently
mis-stepping. Each transition is logged and audited.

## Component map

```text
src/agent/
  orchestrator.py     FSM loop coordinator; wires everything together
  fsm.py              States + transition table
  state.py            AgentFrame — mutable per-run state (plan, messages, retries)
  memory.py           Persistent per-project memory (.ai-agent/memory.jsonl)
  context.py          Token-budget trimming to fit the model context window
  prompts.py          System prompt, few-shot examples, tool format
  telemetry.py        Per-run token/timing stats
  errors.py           Exception hierarchy (AgentError/TransientError/…)
  logging.py          Rich console + file log (plain or JSON), run_id correlation
  cli/
    main.py           Typer CLI: run / bench / build-sandbox / version
    bench.py          Benchmark runner
  model/
    client.py         Async Ollama client (chat, streaming, tool schemas, health)
  perception/
    indexer.py        Workspace crawler → repo skeleton
    languages.py      LanguageRouter (picks a skeleton backend per extension)
    python_driver.py  Python skeletons via stdlib ast
    treesitter_driver.py  Java/JS/TS/Go/Shell/PowerShell/C#/Rust/Ruby/C/C++
    java_driver.py / shell_driver.py   Regex fallbacks when tree-sitter absent
    analysis.py       AST syntax validation of edits (Python)
    symbols.py        SQLite symbol graph (defs + imports) for find_symbol/find_importers
    lsp.py            Async JSON-RPC LSP client (semantic navigation)
  tools/
    registry.py       Tool definitions + dispatch (sync & async handlers)
    parser.py         Tolerant tool-call parser (native / fenced / tag / bare)
    patcher.py        Exact + whitespace-fuzzy search/replace, unified diff
  sandbox/
    config.py         SandboxConfig (backend, limits, network, timeout)
    manager.py        Local (subprocess) + Docker backends; async aexec()
    Dockerfile        Sandbox image (python + node + build tooling)
  evaluation/
    evaluator.py      Project-type detection → run tests (or compile check)
    reflexion.py      LLM failure diagnosis → lesson for the next attempt
  guardrails/
    policy.py         Composes the guardrails below
    paths.py          Workspace path confinement
    commands.py       Command deny-list (regex + AST)
    ast_commands.py   bashlex AST analysis (resists obfuscation)
    secrets.py        Secret scanning / redaction
    approval.py       Human-in-the-loop approval gate
    audit.py          Append-only JSONL audit trail
  server/
    app.py            aiohttp server: /, /ws, /api/health; drives the Orchestrator
    broadcaster.py    Event fan-out + async human-approval broker
    ui.py             Self-contained web dashboard (inline HTML/CSS/JS)
  utils/
    circuit_breaker.py  Trip on repeated model failure
    retry.py            Exponential backoff + jitter
```

## Phases (orchestrator)

[orchestrator.py](src/agent/orchestrator.py) implements each state:

1. **PLANNING** — [`WorkspaceIndexer`](src/agent/perception/indexer.py) builds a
   compact repo skeleton (file tree + code signatures). The model returns a short
   numbered plan. The execution conversation is seeded with the system prompt, the
   plan, and any prior reflexion lessons.
2. **EXECUTING** — a bounded loop (`--max-steps`, default 25). Each step calls the
   model with the tool schemas, parses **one** tool call, executes it via the
   [`ToolRegistry`](src/agent/tools/registry.py), and appends the result. `finish`
   ends the phase. A **no-progress guard** tracks every tool-call signature seen
   this phase; repeating any prior action nudges the model and, after a few
   repeats, bails to evaluation (prevents wandering loops).
3. **EVALUATING** — the [`Evaluator`](src/agent/evaluation/evaluator.py) detects the
   project type (marker files or `--test-command`) and runs the right test command
   (`pytest`, `npm test`, `go test`, `cargo test`, maven/gradle), off the event
   loop. No tests → a compile check. pytest exit code 5 (no tests collected) is
   treated as "no tests", not a failure.
4. **REFLEXING** — on failure, [`ReflexionEngine`](src/agent/evaluation/reflexion.py)
   asks the model to diagnose the root cause and produce a lesson fed into the next
   EXECUTING pass. Bounded by `--max-retries`. When the budget is exhausted, an
   optional **escalation gate** asks a human (console or web) for a hint once; a
   hint grants one more round, otherwise the run ends in ERROR.

## Tools

Registered in [registry.py](src/agent/tools/registry.py); every tool returns a
`ToolResult`, output is truncated and secret-scrubbed.

| Tool | Purpose |
| --- | --- |
| `read_file(path, start_line?, end_line?)` | Read a file or a 1-indexed line range |
| `write_file(path, content)` | Create/overwrite; Python edits get AST syntax validation |
| `search_replace(path, search, replace)` | Exact, else whitespace-fuzzy unique replace |
| `list_files(directory?)` | Recursive listing, optionally scoped to a subtree |
| `search_text(query)` | Grep file contents to locate code in a large repo |
| `outline(path)` | A file's class/function signatures (no bodies) |
| `find_symbol(name)` | Where a class/function/method is defined (SQLite symbol graph) |
| `find_importers(name)` | Which files import a module/symbol (impact analysis) |
| `run_command(command)` | Guarded + approved; runs in the sandbox, off the event loop |
| `find_definition(path, line, character)` | LSP go-to-definition *(when a server is up)* |
| `find_references(path, line, character)` | LSP find-references *(when a server is up)* |
| `get_diagnostics()` | LSP compiler/lint diagnostics *(when a server is up)* |
| `finish(summary)` | Signal completion |

The [parser](src/agent/tools/parser.py) accepts native Ollama tool calls, fenced
JSON, `<tool_call>` tags, or a bare JSON object — local models are inconsistent.

## Code understanding

Three complementary layers, all local and offline:

- **AST skeletons (Python)** — [python_driver.py](src/agent/perception/python_driver.py)
  reduces a file to class/function signatures via stdlib `ast`.
- **Tree-sitter skeletons (11 languages)** — [treesitter_driver.py](src/agent/perception/treesitter_driver.py)
  parses Java, JavaScript, TypeScript/TSX, Go, Shell, PowerShell, C#, Rust, Ruby,
  C, and C++. Each grammar ships as a `tree-sitter-<lang>` wheel (compiled parser
  bundled → no runtime download). Error-tolerant; regex fallback if a grammar is
  missing. Adding a language is one `LangSpec` entry.
- **LSP (semantic navigation)** — [lsp.py](src/agent/perception/lsp.py) is a
  zero-dependency async JSON-RPC client. `LSPManager` is **polymorphic**: it maps
  each file extension to the right server (pylsp / gopls / typescript-language-
  server / rust-analyzer / clangd), pools one client per server, and starts it
  lazily only when the binary is present. Exposes go-to-definition, find-references,
  and diagnostics; edits of any language are synced via `didOpen`/`didChange`.
  100% local — no data leaves the host.
- **AST edit validation** — [analysis.py](src/agent/perception/analysis.py) parses
  every Python file the agent writes and surfaces syntax errors in the tool result
  immediately (before the evaluation phase).
- **Adaptive repo map + dynamic exploration** — [indexer.py](src/agent/perception/indexer.py)
  gives small repos a full skeleton up front; large repos (> ~40 files) get a
  compact directory overview instead, and the agent explores on demand with
  `search_text` (grep), `outline` (a file's signatures), directory-scoped
  `list_files`, and range `read_file`. This keeps the planning prompt bounded no
  matter how big the repository is.
- **Symbol graph (structured RAG)** — [symbols.py](src/agent/perception/symbols.py)
  builds a lazy in-memory **SQLite** index of every definition (name, kind, path,
  line) and Python imports, via the language profiles' `extract_symbols`. Powers
  `find_symbol` (precise cross-language "go to definition by name") and
  `find_importers` (impact analysis) without spending context — the scalable
  complement to textual search and the Python-only LSP.

## Sandbox

[`SandboxManager`](src/agent/sandbox/manager.py) is a facade over two backends with
`start`/`exec`/`aexec`/`stop`:

- **DockerSandbox** — container with CPU/memory limits, network off by default
  (`--network` to enable), workspace bind-mounted at `/workspace`, run as the host
  `uid:gid` so bind-mounted files stay editable. Commands are wrapped in coreutils
  `timeout` so nothing hangs the agent.
- **LocalSandbox** — `subprocess` rooted at the workspace with a timeout; used
  automatically when Docker is unavailable. PATH is prefixed with the agent's venv
  so `python`/`pytest` resolve consistently.

`aexec()` runs the (blocking) backend off the asyncio event loop via
`asyncio.to_thread`, so a long test suite doesn't freeze an embedding server.

Build the image with `ai-agent build-sandbox`.

## Guardrails

[`SecurityPolicy`](src/agent/guardrails/policy.py) composes:

- **paths** — every path is resolved and confined to the workspace (blocks `..`,
  absolute and symlink escapes).
- **commands** — a regex deny-list blocks destructive commands (`rm -rf /`, `sudo`,
  fork bombs, disk writes, `curl | sh`, …), followed by an **AST pass** (bashlex,
  [ast_commands.py](src/agent/guardrails/ast_commands.py)) that inspects the real
  executable of every command in pipes/subshells/substitutions, normalises
  quoting (so `s"u"do` is caught), resolves simple `VAR=value` assignments, and
  blocks destructive commands carrying an unresolved `$VAR` (so `ROOT=/; rm -rf
  $ROOT` can't slip through). The container/timeout remains the hard boundary.
- **secrets** — scans/redacts API keys, tokens, private keys from tool output.
- **approval** — human confirmation for risky actions (skipped in `--auto`).
- **audit** — every guarded action appended to `logs/audit.jsonl`.

## Persistent memory

[memory.py](src/agent/memory.py) gives the agent an **agent-curated, per-project
memory** that survives across runs — the "resume where we left off" capability.

- Stored as one compact fact per line in `<workspace>/.ai-agent/memory.jsonl`
  (kinds: `convention`, `lesson`, `preference`, `note`), de-duplicated.
- **Written** by the model via the `remember` tool, and automatically from a
  human escalation hint.
- **Recalled** at the start of the next run: `MemoryStore.format_for_prompt()`
  produces a capped, most-recent-first block injected into the planning and
  execution context (so it can't overrun the window). The indexer ignores the
  `.ai-agent/` directory.
- Managed with `ai-agent memory` (view/clear) and toggled per run with
  `--memory` / `--no-memory`.

## Reliability & observability

Every model call runs as `circuit_breaker(retry(call))`:

- **async_retry** ([retry.py](src/agent/utils/retry.py)) — exponential backoff +
  jitter on transient errors (`--model-retries`). Streaming, non-streaming, and
  reflexion share the resilient call.
- **CircuitBreaker** ([circuit_breaker.py](src/agent/utils/circuit_breaker.py)) —
  opens after repeated failure (skips retries while the model is down), half-opens
  on recovery.
- **No-progress detection** + **bounded reflexion retries** + **`--max-steps`** keep
  a misbehaving local model from running away.
- **Context/token budget** ([context.py](src/agent/context.py)) — before every
  model call the conversation is trimmed to fit the window (`--num-ctx`): pin the
  system prompt + task/plan primer + most recent turns, drop the oldest middle
  history (with an elision marker), hard-truncate as a last resort. Prevents
  Ollama from silently dropping the system prompt on large repos/long runs.
- **Defensive perception** — indexing/parsing never crash the run; unparseable
  files are skipped.

Observability:

- **run_id** correlation on every log line and audit record.
- **Logging** ([logging.py](src/agent/logging.py)) — Rich console + `logs/agent.log`,
  optionally JSON lines (`--json-logs`).
- **Audit trail** — `logs/audit.jsonl`: `task_start`, `plan_created`, `tool_call`,
  `command_check`, `evaluation`, `reflexion`, `error`, `task_end` (with token
  accounting).
- **Run summary** — model calls, tokens, time, throughput, circuit state.

## Web server (optional)

`ai-agent serve` starts an [aiohttp](src/agent/server/app.py) dashboard — the
"agent server + webview" pattern from `expert_review.md` §7, with a browser as the
webview (no VS Code extension required, though the same WebSocket API supports one).

- The Orchestrator takes an optional **`event_sink`** (sync, non-blocking) and
  emits structured events: `run_started`, `state_changed`, `token`, `plan`,
  `tool_call`, `tool_result`, `evaluation`, `reflexion`, `approval_required`,
  `run_finished`. The [`Broadcaster`](src/agent/server/broadcaster.py) fans these
  out to every connected WebSocket client.
- **Approvals** are bidirectional: with interactive mode, `run_command` approval
  goes through an async **`approval_callback`**; the [`ApprovalBroker`](src/agent/server/broadcaster.py)
  publishes `approval_required` and awaits the browser's `approval` message
  (times out to deny). The CLI path still uses the synchronous console prompt.
- The UI ([ui.py](src/agent/server/ui.py)) is a single self-contained page (no
  external assets, light/dark aware) that renders state pills, the streaming plan,
  tool-call cards, approval buttons, and the final run summary.

The `/ws` endpoint is gated by a per-session token (printed in the dashboard URL;
`--no-auth` is refused on non-loopback binds), and `serve` picks the first free
port at/after the requested one. aiohttp is an optional `[web]` extra; `serve`
reports a friendly message if absent.

A **VS Code extension** ([vscode-extension/](vscode-extension/)) is a second client
of the same WebSocket API: the extension host holds the socket and streams events
into a webview, surfacing approvals and hint requests as native VS Code dialogs.

## Extension points

- **New language (skeletons):** add a `LangSpec` in `treesitter_driver._SPEC`.
- **New tool:** register a `Tool` in `ToolRegistry` (sync or async handler).
- **New LSP server:** pass a custom `cmd` to `LSPClient` (defaults to `pylsp`).
- **New evaluator target:** add a marker in `evaluator.PROJECT_MARKERS` or use
  `--test-command`.
- **New sandbox backend:** implement `start`/`exec`/`stop` and wire into
  `SandboxManager._select_backend`.

See the roadmap and known limitations in [README.md](README.md#status--roadmap)
and the deeper analysis in [expert_review.md](expert_review.md).
