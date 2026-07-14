# AI Coding Agent — User Guide

A practical, task-oriented guide to using the agent. For the design see
[ARCHITECTURE.md](ARCHITECTURE.md); for a feature overview see [README.md](README.md).

## Contents

1. [What it does](#1-what-it-does)
2. [Install](#2-install)
3. [Your first run](#3-your-first-run)
4. [How a run works](#4-how-a-run-works)
5. [The commands](#5-the-commands)
6. [Options reference](#6-options-reference)
7. [Everyday recipes](#7-everyday-recipes)
8. [Interactive vs auto mode (approvals)](#8-interactive-vs-auto-mode-approvals)
9. [The web dashboard](#9-the-web-dashboard)
10. [The VS Code extension](#10-the-vs-code-extension)
11. [Working in large repositories](#11-working-in-large-repositories)
12. [Non-Python projects](#12-non-python-projects)
13. [Sandboxing (local vs Docker)](#13-sandboxing-local-vs-docker)
14. [Choosing a model](#14-choosing-a-model)
15. [Logs, audit trail & run summary](#15-logs-audit-trail--run-summary)
16. [Project memory (across runs)](#16-project-memory-across-runs)
17. [Configuration & environment variables](#17-configuration--environment-variables)
18. [Troubleshooting](#18-troubleshooting)
19. [Tips for best results](#19-tips-for-best-results)
20. [Safety](#20-safety)

---

## 1. What it does

You give it a task in plain English ("add a `--verbose` flag", "fix the failing
test in `stats.py`"). It **plans**, **edits files**, **runs commands** in a
sandbox, **runs your tests**, and **reflects on failures** to try again — all
using a local model via [Ollama](https://ollama.com/). Nothing leaves your machine.

It works on a **workspace** — a directory you point it at. It only reads and
writes inside that directory.

---

## 2. Install

**Prerequisites**

- Python 3.11+
- [Ollama](https://ollama.com/) running locally, with a model pulled:
  ```bash
  ollama serve            # start the server (if not already running)
  ollama pull qwen2.5:7b  # the default model
  ```
- Optional: Docker (stronger sandbox), Node.js (for the VS Code extension).

**Set up a virtual environment and install**

```bash
cd ai-coding-agent
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt   # runtime + tree-sitter + LSP + web + tests
pip install -e .                       # installs the `ai-agent` / `agent` command
```

Or just `make setup`. Verify:

```bash
ai-agent version
```

> The `requirements-dev.txt` install includes everything (multi-language parsing,
> LSP, the web UI, the AST command guard). A minimal `pip install -r
> requirements.txt` also works; optional features degrade gracefully if a
> dependency is missing.

---

## 3. Your first run

```bash
ai-agent run "Create hello.py that prints Hello, World!"
```

By default this uses the `workspace/` directory. Point it somewhere else with
`-w`:

```bash
ai-agent run "Add a factorial(n) function to mathutils.py" -w ./myproject
```

You'll see the plan and tool calls stream live, then a run summary. The file(s)
are created/edited in the workspace.

---

## 4. How a run works

The agent moves through a small state machine:

```
plan → execute → evaluate → (reflect → execute …) → done
```

- **Plan** — it scans the workspace and writes a short plan.
- **Execute** — it calls tools one at a time: read/write files, search, run
  commands, etc.
- **Evaluate** — it runs your tests (or a compile check) to see if the change works.
- **Reflect** — if evaluation fails, it diagnoses and retries (bounded by
  `--max-retries`). If it's still stuck, in interactive mode it can **ask you for
  a hint**.

The tools it can use include: `read_file`, `write_file`, `search_replace`,
`list_files`, `search_text` (grep), `outline` (file signatures), `find_symbol`,
`find_importers`, `run_command`, and semantic ones (`find_definition`,
`find_references`, `get_diagnostics`) when a language server is available.

---

## 5. The commands

| Command | What it does |
| --- | --- |
| `ai-agent run "<task>"` | Run the agent on one task (the main command). |
| `ai-agent serve` | Launch the web dashboard (browser UI). |
| `ai-agent bench` | Run the bundled benchmark tasks. |
| `ai-agent build-sandbox` | Build the Docker sandbox image. |
| `ai-agent version` | Print the version. |

You can also run without installing: `python run.py run "<task>"`, or via
`make run TASK="<task>"`.

---

## 6. Options reference

For `ai-agent run "<task>" [OPTIONS]`:

| Option | Default | Meaning |
| --- | --- | --- |
| `--workspace`, `-w` | `workspace` | Directory the agent works in. |
| `--model`, `-m` | `qwen2.5:7b` | Ollama model to use. |
| `--host` | `http://localhost:11434` | Ollama server URL. |
| `--interactive` / `--auto` | interactive | Prompt before running commands, or run unattended. |
| `--stream` / `--no-stream` | stream | Print tokens live, or not. |
| `--sandbox` | `auto` | `auto` \| `docker` \| `local` execution backend. |
| `--network` / `--no-network` | no-network | Allow network in the Docker sandbox (e.g. `pip`/`npm install`). |
| `--test-command` | (auto-detected) | Override how tests run, e.g. `"npm test"`, `"go test ./..."`. |
| `--max-steps` | `25` | Max tool calls in one execution phase. |
| `--max-retries` | `2` | How many times to reflect-and-retry on failure. |
| `--model-retries` | `3` | Backoff retries for a single model call. |
| `--num-ctx` | `8192` | Model context window (tokens); prompts are trimmed to fit. |
| `--audit-dir` | `logs` | Where `audit.jsonl` is written. |
| `--log-level` | `INFO` | Logging verbosity. |
| `--json-logs` | off | Write `logs/agent.log` as JSON lines. |

Most options also read an environment variable (`AI_AGENT_MODEL`,
`AI_AGENT_HOST`, `AI_AGENT_SANDBOX`, `AI_AGENT_NUM_CTX`,
`AI_AGENT_TEST_COMMAND`, `AI_AGENT_AUDIT_DIR`, `AI_AGENT_LOG_LEVEL`).

---

## 7. Everyday recipes

**Create a new file / script**
```bash
ai-agent run "Create a CLI in cli.py that greets a name passed as --name" -w app
```

**Fix a failing test (let it iterate)**
```bash
ai-agent run "Make the failing tests in test_orders.py pass" -w shop --max-retries 3
```

**Refactor / edit an existing function**
```bash
ai-agent run "In billing.py, make apply_discount return 0.0 when price is None"
```

**Run unattended (no approval prompts) — good for CI-like or trusted tasks**
```bash
ai-agent run "Add type hints to utils.py" --auto
```

**Add a feature that needs verification via a command**
```bash
ai-agent run "Add a factorial function to math.py and verify it prints 120 for 5"
```

**Use a bigger context window (if your model supports it)**
```bash
ai-agent run "Summarise how the auth module works and add docstrings" --num-ctx 16384
```

---

## 8. Interactive vs auto mode (approvals)

- **Interactive (default):** before the agent runs any shell command, it asks you
  to approve it. Type `y` to allow, `n` to deny. File edits are confined to the
  workspace and don't require approval.
- **Auto (`--auto`):** no prompts — the agent runs commands itself. Commands are
  still checked against the safety guard (dangerous commands like `sudo`,
  `rm -rf /`, `curl | sh` are blocked outright).

Use interactive when you want oversight; use `--auto` for trusted, self-contained
tasks.

**Getting unstuck (escalation):** in interactive mode, if the agent exhausts its
retries it will pause and ask you for a **hint**. Type a short pointer (e.g.
"the bug is an off-by-one in the loop") and it gets another round of attempts;
press Enter to let it give up.

---

## 9. The web dashboard

A local browser UI that streams the run and lets you approve commands and give
hints with buttons.

```bash
ai-agent serve --workspace ./myproject --port 8765
```

It prints a URL that includes a **session token** (the dashboard is
token-authenticated) — open exactly that URL, e.g.
`http://127.0.0.1:8765/?token=…`. If the port is busy it automatically picks the
next free one. Binds to loopback (`127.0.0.1`) by default; `--no-auth` is only
allowed on loopback.

Type a task, click **Run**, and watch the plan, tokens, tool calls, and evaluation
stream in. Toggle **Auto-approve** to skip command prompts. When the agent wants
to run a command you'll get **Approve / Deny** buttons; if it gets stuck you'll
get a **hint box**.

(Needs the web extra — included in `requirements-dev.txt`, or `pip install
'ai-coding-agent[web]'`.)

---

## 10. The VS Code extension

Drive the agent from inside VS Code, with **native Approve/Deny and hint dialogs**.

### Install it (recommended — one command)

The repo ships a prebuilt package, so you don't need Node or a build step:
```bash
code --install-extension vscode-extension/ai-coding-agent-0.1.0.vsix
```
(Or in VS Code: **Extensions → ⋯ → Install from VSIX…** and pick the `.vsix`.) The
extension is now available in **every** VS Code window — permanently, no dev host.

*Prefer to build it yourself?* `cd vscode-extension && npm install && npm run package`
produces the same `.vsix`.

### Use it

1. Start the server. For a quick local run, disable the token:
   ```bash
   ai-agent serve --no-auth --workspace .
   ```
   For a shared/secure setup, use `ai-agent serve --workspace .`, copy the
   `?token=…` it prints, and paste it into **Settings → `aiAgent.token`** (the server
   gates the WebSocket with it; without it the extension is rejected with a 403).
2. Command Palette → **AI Agent: Open Dashboard** or **AI Agent: Run Task…**

> `--no-auth` is allowed only on a loopback address (`127.0.0.1`), so nothing
> off-machine can reach it — fine locally, but keep the token for anything shared.

### Develop it (optional)

Open the `vscode-extension` folder and press **F5** to launch an Extension
Development Host — the folder ships a `.vscode/launch.json`, so F5 works with no setup.
Re-run `npm run compile` after editing `src/`, since F5 runs the compiled `out/`.

Settings: `aiAgent.serverUrl` (default `ws://127.0.0.1:8765`), `aiAgent.token`, and
`aiAgent.autoApprove`. See [vscode-extension/README.md](vscode-extension/README.md).

---

## 11. Working in large repositories

The agent adapts automatically:

- **Small repos** — it loads a full outline (file tree + signatures) up front.
- **Large repos** — it shows a compact directory overview and then **explores on
  demand** using `search_text` (grep), `find_symbol` (where something is defined),
  `find_importers` (who uses it), `outline` (a file's shape), and range reads.

You don't have to do anything special — just describe the task and (helpfully)
name the file or symbol if you know it:

```bash
ai-agent run "In the payments module, make refund() idempotent" -w ./big-service
```

The **token-budget manager** keeps every request within the model's context
window (`--num-ctx`), so it stays effective no matter the repo size.

---

## 12. Non-Python projects

Evaluation auto-detects the project type from marker files:

| Marker file | Test command used |
| --- | --- |
| `package.json` | `npm test` |
| `go.mod` | `go test ./...` |
| `Cargo.toml` | `cargo test` |
| `pom.xml` / `build.gradle` | maven / gradle |
| Python test files | `pytest` |

Override it any time:

```bash
ai-agent run "Fix the failing spec" -w ./web --test-command "npm run test:unit"
```

Code understanding (outlines, `find_symbol`) works across Java, JavaScript,
TypeScript, Go, Shell, PowerShell, C#, Rust, Ruby, C, and C++.

---

## 13. Sandboxing (local vs Docker)

Commands the agent runs are executed in a sandbox:

- **`--sandbox local`** (or auto-fallback) — runs in a subprocess rooted at the
  workspace, with a timeout. No Docker needed.
- **`--sandbox docker`** — runs in a container with CPU/memory limits, network
  disabled, and command timeouts. Build the image first:
  ```bash
  ai-agent build-sandbox
  ai-agent run "..." --sandbox docker
  ```
  If a task needs to install packages, allow the network: `--network`.
- **`--sandbox auto`** (default) — uses Docker if available, otherwise local.

---

## 14. Choosing a model

The default **`qwen2.5:7b`** is the most reliable in testing (it handles edits to
existing files well). Alternatives:

```bash
ai-agent run "Create a new parser module" --model qwen2.5-coder:7b   # fast on greenfield
ai-agent run "..." --model llama3.1:8b
```

Any Ollama chat model works. Pull it first (`ollama pull <model>`). Larger models
are more capable but slower on local hardware.

---

## 15. Logs, audit trail & run summary

- **Console:** the plan, tool calls, evaluation, and a **run summary** (model
  calls, tokens, time, throughput) print at the end.
- **`logs/agent.log`** — full application log (add `--json-logs` for JSON lines).
- **`logs/audit.jsonl`** — an append-only record of every significant action
  (task start, plan, each tool call, commands, evaluation, reflexion, task end),
  each tagged with a per-run `run_id`. Great for auditing what the agent did:
  ```bash
  cat logs/audit.jsonl | python -m json.tool   # or: jq . logs/audit.jsonl
  ```

Change the audit location with `--audit-dir`.

---

## 16. Project memory (across runs)

The agent keeps a small **persistent memory per project**, so it carries useful
knowledge from one run to the next (project conventions, lessons learned, your
preferences). This is separate from the code itself — your file changes are always
saved to disk; memory is the agent's *understanding*.

**Where it lives:** `<workspace>/.ai-agent/memory.jsonl` — one compact fact per
line. It travels with the project (add `.ai-agent/` to your `.gitignore`, or commit
it to share conventions with your team).

**How facts get saved:**

- The agent calls its own `remember` tool when it learns something durable
  (e.g. "This project keeps all config in settings.py").
- A **hint you give during escalation** is remembered automatically.

**How they're used:** at the start of the next run, the relevant facts are recalled
into the planning context (capped so they never overrun the context window). You'll
see `Loaded N memory entrie(s) into context` in the log.

**Inspect or clear it:**

```bash
ai-agent memory -w ./myproject           # view remembered facts (a table)
ai-agent memory -w ./myproject --clear   # forget everything
```

**Turn it off for a run:** `ai-agent run "…" --no-memory`.

You can also seed conventions yourself by editing `.ai-agent/memory.jsonl` (each
line: `{"id","kind","text","created","task"}`; `kind` is `convention` / `lesson` /
`preference` / `note`).

---

## 17. Configuration & environment variables

Anything you'd pass repeatedly can be set once via environment variables:

```bash
export AI_AGENT_MODEL=qwen2.5:7b
export AI_AGENT_SANDBOX=local
export AI_AGENT_NUM_CTX=8192
ai-agent run "..."     # picks these up automatically
```

Command-line flags always override environment variables.

---

## 18. Troubleshooting

**"Ollama is not reachable at http://localhost:11434"**
Start Ollama (`ollama serve`) and make sure the model is pulled (`ollama pull
qwen2.5:7b`). Point at a remote Ollama with `--host` / `AI_AGENT_HOST`.

**The agent keeps repeating the same action / loops**
It has built-in no-progress detection and will move on, but you can also lower
`--max-steps`. Try a more capable model, or phrase the task more concretely. On
edit-heavy tasks `qwen2.5:7b` is more reliable than `qwen2.5-coder:7b`.

**Edits fail with "search block not found"**
The agent uses a whitespace-tolerant fuzzy match, but very large or heavily
reformatted files can still be tricky. Point it at the specific file/function in
your task, or ask it to rewrite the file.

**Tests aren't detected / wrong test command**
Pass `--test-command "<your command>"` explicitly.

**A command was blocked**
The safety guard blocks dangerous commands. If a legitimate command is blocked,
rephrase it, or run that step yourself.

**Docker sandbox errors**
Run `ai-agent build-sandbox` first, ensure the Docker daemon is running, and add
`--network` if the task needs to fetch packages. Or just use `--sandbox local`.

**Runs are slow / context errors on big repos**
Increase `--num-ctx` if your model supports a larger window; otherwise the token
budget will trim context automatically (you may see "Context trimmed" in the log).

---

## 19. Tips for best results

- **Be specific.** Name the file, function, or symbol when you know it: "In
  `orders.py`, make `total()` include tax" beats "fix the totals".
- **State the acceptance criterion.** "…so that `test_total` passes" or "…and
  verify it prints 42" gives the agent a target to evaluate against.
- **Keep tasks focused.** One change at a time works better than a sweeping
  refactor. Chain runs for bigger work.
- **Provide tests** where you can — the agent uses them to know when it's done.
- **Use `--auto` for trusted, well-scoped tasks**; stay interactive when you want
  to watch each command.
- **Start with `qwen2.5:7b`**; switch models per task if needed.

---

## 20. Safety

- All file access is **confined to the workspace** (path traversal is blocked).
- Shell commands go through a **guard** (regex + AST) that blocks destructive
  commands (`sudo`, `rm -rf /`, fork bombs, `curl | sh`, disk writes, …) and, in
  interactive mode, require your **approval**.
- Commands run in a **sandbox** with timeouts (and, with Docker, resource limits
  and no network by default).
- Tool output is **scrubbed of secrets** (API keys, tokens) before logging.
- Everything is recorded in the **audit trail** (`logs/audit.jsonl`).

Even so, review what you run — especially in `--auto` mode on an important
workspace. Consider committing your work to git before a big autonomous run so
you can diff and roll back.
