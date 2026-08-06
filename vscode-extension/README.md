# AI Coding Agent — VS Code extension

Drive the local [AI Coding Agent](../README.md) from inside VS Code. The
extension connects to a running `ai-agent serve` instance over its WebSocket API
and gives you a **chat panel**: each message you send is one task run, and the
agent's plan, tool calls, evaluation and summary render as its reply. Earlier
turns stay in the thread, so the panel is a transcript of the session.

**Command approvals and "I'm stuck" hint requests** are answered either inline in
the thread or with native VS Code dialogs — see
[`aiAgent.promptStyle`](#settings). Only one of the two is offered for a given
decision, so you are never asked the same thing twice.

The browser dashboard (`ai-agent serve`) and this extension are two clients of
the same local WebSocket server.

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

- **AI Agent: Open Chat** — opens the chat panel.
- **AI Agent: Open Dashboard** — alias for the same panel (kept for existing keybindings).
- **AI Agent: Run Task…** — prompts for a task and starts a run.

In the panel: type a task and press **Enter** to send (**Shift+Enter** for a new
line). Tool calls are collapsed by default — click one to see its full arguments
or output. **Clear** empties the transcript; **Pause / Resume / Stop** control the
active run.

Only one run executes at a time (the server refuses a second), so the composer is
disabled while a task is in flight.

### Approvals and hints

When the agent asks to run a command you get **Approve / Deny**; when it exhausts
its retries you get a **hint box**. By default these appear *inline in the thread*
when the panel is visible, and as *native VS Code dialogs* when it is not — so a
run started from the command palette can still be answered with the panel closed.
Force one or the other with `aiAgent.promptStyle`.

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `aiAgent.serverUrl` | `ws://127.0.0.1:8765` | URL of the `ai-agent serve` instance |
| `aiAgent.token` | `""` | Session token printed by `ai-agent serve` (the `?token=…` value). Required unless the server runs with `--no-auth`; without it the WebSocket is rejected with a 403. |
| `aiAgent.autoApprove` | `false` | Run in `--auto` mode (skip approval prompts) |
| `aiAgent.promptStyle` | `auto` | Where approval/hint prompts are answered: `auto` (inline when the chat panel is visible, native otherwise), `inline`, or `native`. |

## Notes

This is a separate TypeScript artifact and is **not** covered by the Python test
suite. Packaging (`vsce package`) and a native side-by-side diff on file writes
(via `vscode.diff`) are natural follow-ups.
