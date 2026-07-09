# AI Coding Agent

A local-first, autonomous AI coding agent and **reference implementation**. It
plans, edits code, runs commands in a sandbox, evaluates the result with tests,
and reflects on failures — all driven by a local model served by
[Ollama](https://ollama.com/). **No code or credentials leave your machine.**

> **New here? Start with the [User Guide](USER_GUIDE.md)** — install, first run,
> commands, recipes, the web UI, and troubleshooting.

- [Features](#features)
- [Requirements](#requirements)
- [Setup](#setup-virtualenv--pip)
- [Usage](#usage)
- [Model selection](#model-selection)
- [Status & roadmap](#status--roadmap)
- [Testing](#testing)

## Features

- **FSM control loop** — `plan → execute → evaluate → reflect` with bounded retries.
- **Local model** via Ollama (`qwen2.5:7b` by default); async client with streaming.
- **Code understanding** — stdlib AST for Python, **tree-sitter** for 11 more
  languages, and an optional **LSP client** for semantic navigation (all offline).
- **Robust editing** — whitespace-tolerant `search_replace`, line-range reads,
  and AST syntax validation of every Python edit.
- **Sandboxed execution** — Docker (CPU/mem limits, network off, command timeouts)
  with an automatic local fallback; commands run off the async event loop.
- **Language-agnostic evaluation** — detects `pytest` / `npm test` / `go test` /
  `cargo test` / maven / gradle, or use `--test-command`.
- **Guardrails** — workspace path confinement, destructive-command deny-list,
  secret scanning/redaction, human approval, append-only audit log.
- **Resilience** — every model call is `circuit_breaker(retry(...))`; no-progress
  loop detection and bounded reflexion retries keep runs from running away.
- **Observability** — structured logging (plain or JSON), run-correlated audit
  trail (`logs/audit.jsonl`), and a per-run token/time/throughput summary.
- **Web dashboard** — `ai-agent serve` opens a local, self-contained UI that
  streams the run live (plan, tokens, tool calls, evaluation) and lets you
  **approve/deny commands in the browser**.

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com/) running locally (`ollama serve`) with a model pulled:
  `ollama pull qwen2.5:7b`
- **Optional:** Docker (stronger sandbox isolation), and `python-lsp-server`
  (semantic navigation). The agent runs fine without either.

## Setup (virtualenv + pip)

```bash
cd ai-coding-agent
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt   # runtime + tree-sitter + LSP + test/lint
pip install -e .                       # install the `agent`/`ai-agent` CLI
```

Or simply `make setup`. Tree-sitter grammars and `python-lsp-server` are included
in `requirements*.txt`; the agent degrades gracefully if any are absent.

## Usage

```bash
# Installed console script:
ai-agent run "Create a hello.py that prints Hello, World!"

# Options: model / workspace / non-interactive / custom test command:
ai-agent run "Make the tests pass" --model qwen2.5:7b -w workspace --auto \
  --test-command "npm test"

# Docker sandbox (build the image once):
ai-agent build-sandbox
ai-agent run "..." --sandbox docker --network   # --network allows pip/npm install

# Without installing (from a checkout):
python run.py run "Add a factorial function to math_utils.py"

# Benchmarks:
ai-agent bench

# Web dashboard (needs the [web] extra; requirements-dev already includes it):
ai-agent serve --workspace workspace --port 8765     # then open http://127.0.0.1:8765
```

The dashboard streams the plan, tokens, tool calls, and evaluation live, and (in
interactive mode) prompts you to approve or deny each command before it runs. A
**VS Code extension** (see [vscode-extension/](vscode-extension/)) is a second
client of the same server, with native Approve/Deny and hint dialogs.

**Key options:** `--workspace/-w`, `--model/-m`, `--host`, `--interactive/--auto`,
`--sandbox auto|docker|local`, `--network/--no-network`, `--test-command`,
`--max-retries`, `--max-steps`, `--model-retries`, `--num-ctx`,
`--stream/--no-stream`, `--json-logs`, `--audit-dir`, `--log-level`. Most also
read an `AI_AGENT_*` environment variable.

With `--stream` (default) the plan and tool calls print live. Every run ends with
a summary of model calls, tokens, time and throughput (also in `logs/audit.jsonl`).

## Model selection

The default is **`qwen2.5:7b`**. In a head-to-head evaluation on this agent's own
task loop (6 coding tasks × 2 passes, local sandbox), `qwen2.5:7b` solved **12/12**
while `qwen2.5-coder:7b` solved **10/12** — the coder model reliably looped on the
*edit-an-existing-file* task. The coder model is faster on greenfield "create a
file" work (`--model qwen2.5-coder:7b`). Any Ollama chat model works.

## Status & roadmap

### Implemented

| Area | What |
| --- | --- |
| Control | FSM loop; no-progress detection; bounded retries; `--max-steps`; **human escalation gate** (hint on exhausted retries) |
| Model | Async Ollama client; streaming; tool schemas; health check |
| Tools | read (line ranges) / write / fuzzy search_replace / list / search_text / outline / **find_symbol** / **find_importers** / run_command / finish |
| Perception | Python AST; tree-sitter for Java, JS, TS/TSX, Go, Shell, PowerShell, C#, Rust, Ruby, C, C++; AST edit validation; adaptive repo map + on-demand exploration; **symbol graph (SQLite defs/imports)** |
| Semantics | Polymorphic LSP: `find_definition` / `find_references` / `get_diagnostics`, routing each file to its server (pylsp / gopls / typescript-language-server / rust-analyzer / clangd) when installed |
| Sandbox | Local + Docker; CPU/mem limits; command timeouts; non-blocking exec; `build-sandbox` |
| Evaluation | Project-type detection (pytest/npm/go/cargo/maven/gradle) + `--test-command`; reflexion |
| Guardrails | Path confinement; regex + AST (bashlex) command guard (resolves `$VAR`, blocks unresolved-variable destructive commands); secret redaction; approval; audit trail |
| Reliability | Circuit breaker; backoff retries; defensive perception; context/token-budget trimming (`--num-ctx`) |
| Memory | Persistent per-project memory (`.ai-agent/memory.jsonl`): `remember` tool + escalation hints, recalled into the next run's context |
| Observability | run_id correlation; plain/JSON logs; token/time telemetry |
| Interfaces | CLI; `ai-agent serve` WebSocket dashboard (token-authenticated, auto free-port) + **VS Code extension**; native/browser approval & hint gating |
| Tooling | Typer CLI; env-var config; benchmarks; pytest suite; ruff; GitHub Actions CI |

### Roadmap (feasible within local-first constraints)

- **Auto-diagnostics feedback loop** — surface LSP semantic errors immediately
  after each edit. *Deliberately not done*: it would add a blocking wait to every
  edit for modest gain; instead the agent gets immediate AST syntax validation on
  writes, an on-demand `get_diagnostics` tool, and reflexion on test/compile
  failures. Could be added as an opt-in flag.
- **Native VS Code diff approval** — side-by-side `vscode.diff` before file writes
  (the extension currently shows approvals as native dialogs).
- **Additional tree-sitter languages / LSP servers** — one entry each.

### Not implemented (by design / out of scope)

- **Cloud model providers** — this is deliberately local-first; a provider adapter
  could be added but isn't present.
- **Multi-file transactional edits / parallel multi-agent orchestration** —
  single-run, single-session by design. (Persistent cross-run *memory* is now
  implemented — see the Memory row above.)
- **Full IDE feature parity** (rename refactors, semantic highlighting) — the LSP
  client exposes definition/references/diagnostics only.

See [expert_review.md](expert_review.md) for a deep analysis and rationale, and
[ARCHITECTURE.md](ARCHITECTURE.md) for the design.

## Testing

```bash
make test      # pytest         (unit tests need neither Ollama nor Docker)
make lint      # ruff
```

Tests that need Ollama, Docker, or `pylsp` skip automatically when those aren't
available. CI (GitHub Actions) runs ruff + pytest on Python 3.11 and 3.12.

## Documentation

- **[User Guide](USER_GUIDE.md)** — how to install and use the agent (start here).
- [ARCHITECTURE.md](ARCHITECTURE.md) — how it works internally.
- [CONTRIBUTING.md](CONTRIBUTING.md) — developing on the codebase.
- [vscode-extension/](vscode-extension/) — the VS Code extension.
- [expert_review.md](expert_review.md) — deep analysis and rationale.

## License

MIT
