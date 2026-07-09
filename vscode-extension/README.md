# AI Coding Agent — VS Code extension

Drive the local [AI Coding Agent](../README.md) from inside VS Code. The
extension connects to a running `ai-agent serve` instance over its WebSocket API
and shows a **live run dashboard** (plan, tokens, tool calls, evaluation, summary)
in a webview, while surfacing **command approvals and "I'm stuck" hint requests as
native VS Code dialogs**.

This reuses the exact server protocol described in `expert_review.md` §7 (Path B:
agent server + webview) — the browser dashboard (`ai-agent serve`) and this
extension are two clients of the same local WebSocket server.

## Prerequisites

1. Install and run the agent server (from the repo root):
   ```bash
   pip install -e '.[web]'      # or: pip install -r requirements-dev.txt
   ai-agent serve --workspace .  # serves ws://127.0.0.1:8765
   ```
2. Node.js 18+ to build the extension.

## Build & run (development)

```bash
cd vscode-extension
npm install
npm run compile
```

Then press **F5** in VS Code (with this folder open) to launch an Extension
Development Host. In it:

- **AI Agent: Open Dashboard** — opens the live run viewer.
- **AI Agent: Run Task…** — prompts for a task and starts a run.

When the agent asks to run a command, VS Code shows an **Approve / Deny** dialog.
When it exhausts its retries, VS Code shows an **input box** to type a hint.

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `aiAgent.serverUrl` | `ws://127.0.0.1:8765` | URL of the `ai-agent serve` instance |
| `aiAgent.autoApprove` | `false` | Run in `--auto` mode (skip approval prompts) |

## Notes

This is a separate TypeScript artifact and is **not** covered by the Python test
suite. Packaging (`vsce package`) and a native side-by-side diff on file writes
(via `vscode.diff`) are natural follow-ups.
