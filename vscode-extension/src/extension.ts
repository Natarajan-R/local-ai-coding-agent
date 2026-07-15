// AI Coding Agent — VS Code extension.
//
// The extension host holds a WebSocket to a running `ai-agent serve` instance,
// relays its structured events to a webview (a live run viewer + task composer),
// and answers approval / escalation prompts with NATIVE VS Code dialogs.
import * as vscode from "vscode";
import WebSocket from "ws";

let panel: vscode.WebviewPanel | undefined;
let socket: WebSocket | undefined;
let output: vscode.OutputChannel;

export function activate(context: vscode.ExtensionContext): void {
  output = vscode.window.createOutputChannel("AI Coding Agent");
  context.subscriptions.push(
    vscode.commands.registerCommand("aiAgent.openDashboard", () => openDashboard(context)),
    vscode.commands.registerCommand("aiAgent.runTask", () => runTaskCommand(context)),
    output
  );
}

export function deactivate(): void {
  socket?.close();
  socket = undefined;
}

function config<T>(key: string, fallback: T): T {
  return vscode.workspace.getConfiguration("aiAgent").get<T>(key, fallback);
}

function wsUrl(): string {
  const base = config<string>("serverUrl", "ws://127.0.0.1:8765").replace(/\/+$/, "");
  // `ai-agent serve` gates /ws with a per-session token by default; present it if
  // configured. Leave `aiAgent.token` blank only when the server runs with --no-auth.
  const token = config<string>("token", "").trim();
  return base + "/ws" + (token ? "?token=" + encodeURIComponent(token) : "");
}

function toWebview(msg: unknown): void {
  panel?.webview.postMessage(msg);
}

function sendToServer(obj: unknown): void {
  const s = ensureSocket();
  const payload = JSON.stringify(obj);
  if (s.readyState === WebSocket.OPEN) {
    s.send(payload);
  } else {
    s.once("open", () => s.send(payload));
  }
}

function ensureSocket(): WebSocket {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return socket;
  }
  const url = wsUrl();
  output.appendLine(`Connecting to ${url}`);
  socket = new WebSocket(url);
  socket.on("open", () => toWebview({ event: "host_status", connected: true }));
  socket.on("close", () => toWebview({ event: "host_status", connected: false }));
  socket.on("error", (err: Error) => {
    output.appendLine(`WebSocket error: ${err.message}`);
    toWebview({ event: "error", message: `Cannot reach ${url}. Is 'ai-agent serve' running?` });
  });
  socket.on("message", (data: WebSocket.RawData) => {
    let msg: any;
    try {
      msg = JSON.parse(data.toString());
    } catch {
      return;
    }
    handleServerEvent(msg);
  });
  return socket;
}

async function handleServerEvent(msg: any): Promise<void> {
  // Always mirror the event into the webview for the live view.
  toWebview(msg);

  // Native prompts for the interactive decisions.
  if (msg.event === "approval_required") {
    const choice = await vscode.window.showWarningMessage(
      `AI Agent wants to run a command:\n\n${msg.detail}`,
      { modal: false },
      "Approve",
      "Deny"
    );
    sendToServer({ type: "approval", id: msg.id, approved: choice === "Approve" });
  } else if (msg.event === "escalation_required") {
    const hint = await vscode.window.showInputBox({
      title: "AI Agent is stuck",
      prompt: "Provide a hint to help it, or leave empty to give up.",
      placeHolder: msg.context ? String(msg.context).slice(0, 120) : "",
      ignoreFocusOut: true,
    });
    sendToServer({ type: "hint", id: msg.id, hint: hint ?? "" });
  }
}

function openDashboard(context: vscode.ExtensionContext): void {
  if (panel) {
    panel.reveal(vscode.ViewColumn.Beside);
  } else {
    panel = vscode.window.createWebviewPanel(
      "aiAgentDashboard",
      "AI Coding Agent",
      vscode.ViewColumn.Beside,
      { enableScripts: true, retainContextWhenHidden: true }
    );
    panel.webview.html = getHtml(panel.webview);
    panel.onDidDispose(() => {
      panel = undefined;
    });
    panel.webview.onDidReceiveMessage((m: any) => {
      if (m.type === "run") {
        sendToServer({ type: "run", task: m.task, options: { interactive: !config<boolean>("autoApprove", false) } });
      }
    });
  }
  ensureSocket();
}

async function runTaskCommand(context: vscode.ExtensionContext): Promise<void> {
  openDashboard(context);
  const task = await vscode.window.showInputBox({
    title: "AI Coding Agent",
    prompt: "Describe the coding task",
    ignoreFocusOut: true,
  });
  if (task && task.trim()) {
    sendToServer({ type: "run", task: task.trim(), options: { interactive: !config<boolean>("autoApprove", false) } });
  }
}

function nonce(): string {
  let text = "";
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 24; i++) text += chars.charAt(Math.floor(Math.random() * chars.length));
  return text;
}

function getHtml(webview: vscode.Webview): string {
  const n = nonce();
  const csp = `default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${n}';`;
  return /* html */ `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta http-equiv="Content-Security-Policy" content="${csp}" />
<style>
  body { font-family: var(--vscode-font-family); color: var(--vscode-foreground);
    background: var(--vscode-editor-background); padding: 10px; }
  #composer { display: flex; gap: 6px; margin-bottom: 8px; }
  textarea { flex: 1; background: var(--vscode-input-background); color: var(--vscode-input-foreground);
    border: 1px solid var(--vscode-input-border); border-radius: 4px; padding: 6px; font: inherit; }
  button { background: var(--vscode-button-background); color: var(--vscode-button-foreground);
    border: 0; padding: 4px 12px; border-radius: 4px; cursor: pointer; }
  #status { font-size: 12px; opacity: .7; margin-bottom: 6px; }
  .card { border-left: 3px solid var(--vscode-panel-border); padding: 6px 8px; margin: 6px 0;
    background: var(--vscode-editorWidget-background); border-radius: 4px; white-space: pre-wrap; word-break: break-word; }
  .tool { border-left-color: var(--vscode-charts-blue); }
  .ok { border-left-color: var(--vscode-charts-green); }
  .fail { border-left-color: var(--vscode-charts-red); }
  .tag { font-size: 11px; opacity: .7; }
  .stream { font-family: var(--vscode-editor-font-family); font-size: 12px; opacity: .85; }
</style>
</head>
<body>
  <div id="composer">
    <textarea id="task" rows="2" placeholder="Describe a coding task…"></textarea>
    <button id="run">Run</button>
  </div>
  <div id="status">Connecting…</div>
  <div id="feed"></div>
<script nonce="${n}">
  const vscode = acquireVsCodeApi();
  const feed = document.getElementById('feed');
  const statusEl = document.getElementById('status');
  let streamEl = null;
  function card(cls, head, body) {
    const c = document.createElement('div'); c.className = 'card ' + (cls||'');
    const h = document.createElement('div'); h.className='tag'; h.textContent = head; c.appendChild(h);
    if (body != null) { const b = document.createElement('div'); b.textContent = body; c.appendChild(b); }
    feed.appendChild(c); c.scrollIntoView(); return c;
  }
  function ensureStream(label) {
    if (!streamEl) { const c = card('', label || 'model', ''); streamEl = document.createElement('div');
      streamEl.className = 'stream'; c.appendChild(streamEl); }
    return streamEl;
  }
  window.addEventListener('message', (ev) => {
    const e = ev.data;
    switch (e.event) {
      case 'host_status': statusEl.textContent = e.connected ? 'Connected' : 'Disconnected'; break;
      case 'connected': statusEl.textContent = 'Ready · ' + (e.config ? e.config.model : ''); break;
      case 'run_started': feed.innerHTML=''; streamEl=null; statusEl.textContent='Running…'; card('', 'task', e.task); break;
      case 'state_changed': streamEl=null; card('', 'state', e.state); break;
      case 'token': ensureStream(e.label).textContent += e.text; break;
      case 'memory_loaded': card('', 'memory', 'Recalled ' + e.count + ' fact(s) learned in previous runs'); break;
      case 'context_trimmed': streamEl=null; card('', 'context trimmed',
        (e.dropped ? 'Dropped ' + e.dropped + ' old step(s) to fit the window'
                   : 'Truncated to fit the window') + ' — ~' + e.est_tokens + ' tokens sent'); break;
      case 'escalation_resolved': card('ok', 'hint accepted', e.hint); break;
      case 'plan': streamEl=null; card('', 'plan', e.text); break;
      case 'tool_call': streamEl=null; card('tool', 'tool: ' + e.tool, JSON.stringify(e.args)); break;
      case 'tool_result': card(e.ok ? 'ok' : 'fail', 'result: ' + e.tool, e.content); break;
      case 'evaluation': card(e.passed ? 'ok' : 'fail', 'evaluation', e.summary); break;
      case 'reflexion': card('', 'reflexion #' + e.retry, e.lesson); break;
      case 'approval_required': card('', 'approval (answer in the VS Code prompt)', e.detail); break;
      case 'escalation_required': card('', 'stuck — hint requested (see prompt)', e.context); break;
      case 'run_finished': statusEl.textContent='Finished: ' + e.final_state;
        card(e.final_state==='done'?'ok':'fail', 'summary', e.summary || '');
        if (e.stats) card('', 'telemetry', e.stats.model_calls + ' model calls · '
          + e.stats.total_tokens + ' tokens · ' + (e.stats.total_seconds||0).toFixed(1)
          + 's · $0.00'); break;
      case 'error': card('fail', 'error', e.message); break;
    }
  });
  document.getElementById('run').addEventListener('click', () => {
    const task = document.getElementById('task').value.trim();
    if (task) vscode.postMessage({ type: 'run', task });
  });
</script>
</body>
</html>`;
}
