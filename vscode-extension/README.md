# AI Coding Agent — VS Code extension

Drive the local [AI Coding Agent](../README.md) from inside VS Code. The
extension connects to a running `ai-agent serve` instance over its WebSocket API
and shows a **live run dashboard** (plan, tokens, tool calls, evaluation, summary)
in a webview, while surfacing **command approvals and "I'm stuck" hint requests as
native VS Code dialogs**.

This reuses the exact server protocol described in `expert_review.md` §7 (Path B:
agent server + webview) — the browser dashboard (`ai-agent serve`) and this
extension are two clients of the same local WebSocket server.

## Install (recommended)

A prebuilt package ships in this folder — no Node or build step needed:

```bash
code --install-extension vscode-extension/ai-coding-agent-0.1.0.vsix
```

Or in VS Code: **Extensions → ⋯ → Install from VSIX…**. The extension is then in
every VS Code window permanently. Then run the agent server and use the commands
(see [Prerequisites](#prerequisites) and [Commands](#build--run-development)).

## Prerequisites

1. Install and run the agent server (from the repo root):
   ```bash
   pip install -e '.[web]'      # or: pip install -r requirements-dev.txt
   ai-agent serve --no-auth --workspace .   # serves ws://127.0.0.1:8765 (no token)
   ```
   For a shared/secure setup, drop `--no-auth` and paste the printed `?token=…` into
   the `aiAgent.token` setting.
2. Node.js 18+ — only if you want to **build** the extension yourself (below).

## Build & run (development)

Rebuild the `.vsix` yourself with `npm install && npm run package`. To develop:

```bash
cd vscode-extension
npm install
npm run compile
```

Then press **F5** in VS Code (with this folder open) to launch an Extension
Development Host — this folder ships a `.vscode/launch.json`, so F5 works with no
extra setup. (Re-run `npm run compile` after editing `src/`, since F5 runs `out/`.)
In it:

- **AI Agent: Open Dashboard** — opens the live run viewer.
- **AI Agent: Run Task…** — prompts for a task and starts a run.

When the agent asks to run a command, VS Code shows an **Approve / Deny** dialog.
When it exhausts its retries, VS Code shows an **input box** to type a hint.

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `aiAgent.serverUrl` | `ws://127.0.0.1:8765` | URL of the `ai-agent serve` instance |
| `aiAgent.token` | `""` | Session token printed by `ai-agent serve` (the `?token=…` value). Required unless the server runs with `--no-auth`; without it the WebSocket is rejected with a 403. |
| `aiAgent.autoApprove` | `false` | Run in `--auto` mode (skip approval prompts) |

## Notes

This is a separate TypeScript artifact and is **not** covered by the Python test
suite. Packaging (`vsce package`) and a native side-by-side diff on file writes
(via `vscode.diff`) are natural follow-ups.
