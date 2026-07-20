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
// The server sends `connected` (with the model/workspace config) once, the moment the
// socket opens — long before a webview exists to hear it. Keep it so a panel opened
// later can still be told what it is connected *to*, not merely that it is connected.
let lastConnected: unknown;

export function activate(context: vscode.ExtensionContext): void {
  output = vscode.window.createOutputChannel("AI Coding Agent");
  context.subscriptions.push(
    vscode.commands.registerCommand("aiAgent.openDashboard", () => openDashboard(context)),
    vscode.commands.registerCommand("aiAgent.runTask", () => runTaskCommand(context)),
    output
  );

  // Watch workspace changes and refresh file explorer in the webview
  const watcher = vscode.workspace.createFileSystemWatcher("**/*");
  watcher.onDidCreate(() => sendWorkspaceFiles());
  watcher.onDidChange(() => sendWorkspaceFiles());
  watcher.onDidDelete(() => sendWorkspaceFiles());
  context.subscriptions.push(
    watcher,
    vscode.workspace.onDidChangeWorkspaceFolders(() => sendWorkspaceFiles())
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
  const kind = (obj as { type?: string })?.type;
  // Control messages (stop/pause/resume) are time-sensitive: if the socket is
  // not open right now, queuing them on a future "open" that may never arrive
  // silently drops them — the user clicks Stop and nothing happens, with no clue
  // why. Surface it instead. (A "run" can legitimately wait for the socket.)
  const isControl = kind === "stop" || kind === "pause" || kind === "resume";
  if (s.readyState === WebSocket.OPEN) {
    s.send(payload);
  } else if (isControl) {
    output.appendLine(`Cannot send '${kind}': not connected to the server.`);
    toWebview({ event: "error", message: `Cannot ${kind} — the connection to 'ai-agent serve' is down. Is the server running?` });
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
  socket.on("close", () => {
    lastConnected = undefined;
    toWebview({ event: "host_status", connected: false });
  });
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
  if (msg.event === "connected") {
    lastConnected = msg;
  }
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

async function sendWorkspaceFiles(): Promise<void> {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    toWebview({ event: "workspace_files", folders: [], activeFolder: "", files: [] });
    return;
  }

  const activeFolder = folders[0];
  const relativePattern = new vscode.RelativePattern(activeFolder, "**/*");
  const uris = await vscode.workspace.findFiles(
    relativePattern,
    "**/{node_modules,.git,.venv,__pycache__,out,dist,build,.gemini,logs}/**"
  );
  
  const files = uris.map(u => vscode.workspace.asRelativePath(u, false));
  toWebview({
    event: "workspace_files",
    folders: folders.map(f => ({ name: f.name, path: f.uri.fsPath })),
    activeFolder: activeFolder.name,
    files: files
  });
}

async function openFileInEditor(relativePath: string): Promise<void> {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) { return; }
  const activeFolder = folders[0];
  const fileUri = vscode.Uri.joinPath(activeFolder.uri, relativePath);
  try {
    const doc = await vscode.workspace.openTextDocument(fileUri);
    await vscode.window.showTextDocument(doc);
  } catch (err: any) {
    vscode.window.showErrorMessage(`Failed to open file: ${err.message}`);
  }
}

async function selectWorkspaceFolder(): Promise<void> {
  const options: vscode.OpenDialogOptions = {
    canSelectFiles: false,
    canSelectFolders: true,
    canSelectMany: false,
    openLabel: "Select Workspace Folder"
  };
  const uri = await vscode.window.showOpenDialog(options);
  if (uri && uri[0]) {
    vscode.commands.executeCommand("vscode.openFolder", uri[0]);
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
      if (m.type === "ready") {
        // Replay connection status and workspace details to fresh webview.
        toWebview({ event: "host_status", connected: socket?.readyState === WebSocket.OPEN });
        if (lastConnected) {
          toWebview(lastConnected);
        }
        sendWorkspaceFiles();
      } else if (m.type === "run") {
        sendToServer({ type: "run", task: m.task, options: { interactive: !config<boolean>("autoApprove", false) } });
      } else if (m.type === "pause") {
        sendToServer({ type: "pause" });
      } else if (m.type === "resume") {
        sendToServer({ type: "resume" });
      } else if (m.type === "stop") {
        sendToServer({ type: "stop" });
      } else if (m.type === "openFile") {
        openFileInEditor(m.path);
      } else if (m.type === "selectFolder") {
        selectWorkspaceFolder();
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
  body {
    font-family: var(--vscode-font-family);
    color: var(--vscode-foreground);
    background: var(--vscode-editor-background);
    padding: 10px;
    margin: 0;
    display: flex;
    flex-direction: column;
    height: 100vh;
    box-sizing: border-box;
  }
  #header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--vscode-panel-border);
    padding-bottom: 6px;
    margin-bottom: 10px;
    flex-shrink: 0;
  }
  #workspace-info {
    font-size: 12px;
    font-weight: bold;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .link-btn {
    color: var(--vscode-textLink-foreground);
    cursor: pointer;
    text-decoration: underline;
    background: none;
    border: none;
    padding: 0;
    font: inherit;
  }
  #container {
    display: flex;
    flex: 1;
    gap: 15px;
    min-height: 0;
  }
  #explorer-panel {
    width: 220px;
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--vscode-panel-border);
    padding-right: 12px;
    min-height: 0;
    flex-shrink: 0;
  }
  #explorer-title {
    font-size: 11px;
    text-transform: uppercase;
    font-weight: bold;
    margin-bottom: 8px;
    opacity: 0.8;
  }
  #file-list {
    flex: 1;
    overflow-y: auto;
    font-family: var(--vscode-editor-font-family);
    font-size: 12px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .file-item {
    cursor: pointer;
    padding: 4px 6px;
    border-radius: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .file-item:hover {
    background: var(--vscode-list-hoverBackground);
  }
  .file-icon {
    font-size: 12px;
  }
  .file-new {
    color: var(--vscode-gitDecoration-addedResourceForeground);
    font-weight: bold;
  }
  .file-modified {
    color: var(--vscode-gitDecoration-modifiedResourceForeground);
    font-weight: bold;
  }
  #main-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  #composer {
    display: flex;
    gap: 6px;
    margin-bottom: 8px;
    flex-shrink: 0;
  }
  textarea {
    flex: 1;
    background: var(--vscode-input-background);
    color: var(--vscode-input-foreground);
    border: 1px solid var(--vscode-input-border);
    border-radius: 4px;
    padding: 6px;
    font: inherit;
    resize: none;
  }
  #controls {
    display: flex;
    gap: 6px;
    margin-bottom: 8px;
    align-items: center;
    flex-shrink: 0;
  }
  button {
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    border: 0;
    padding: 4px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
  }
  button:hover {
    background: var(--vscode-button-hoverBackground);
  }
  button.secondary {
    background: var(--vscode-button-secondaryBackground);
    color: var(--vscode-button-secondaryForeground);
  }
  button.secondary:hover {
    background: var(--vscode-button-secondaryHoverBackground);
  }
  button.danger {
    background: var(--vscode-errorForeground);
    color: var(--vscode-editor-background);
  }
  #status {
    font-size: 12px;
    opacity: .7;
  }
  #feed {
    flex: 1;
    overflow-y: auto;
    border: 1px solid var(--vscode-panel-border);
    border-radius: 4px;
    padding: 8px;
    background: var(--vscode-editorWidget-background);
  }
  .card {
    border-left: 3px solid var(--vscode-panel-border);
    padding: 6px 8px;
    margin: 6px 0;
    background: var(--vscode-editor-background);
    border-radius: 4px;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .tool { border-left-color: var(--vscode-charts-blue); }
  .ok { border-left-color: var(--vscode-charts-green); }
  .fail { border-left-color: var(--vscode-charts-red); }
  .tag { font-size: 11px; opacity: .7; }
  .stream { font-family: var(--vscode-editor-font-family); font-size: 12px; opacity: .85; }
</style>
</head>
<body>
  <div id="header">
    <div id="workspace-info">📁 Loading workspace…</div>
    <div id="status">Connecting…</div>
  </div>
  <div id="container">
    <div id="explorer-panel">
      <div id="explorer-title">Project Files</div>
      <div id="file-list">📁 Loading...</div>
    </div>
    <div id="main-panel">
      <div id="composer">
        <textarea id="task" rows="2" placeholder="Describe a coding task…"></textarea>
        <button id="run">Run</button>
      </div>
      <div id="controls">
        <button id="clear" class="secondary">Clear</button>
        <button id="pause" class="secondary" style="display:none;">Pause</button>
        <button id="resume" class="secondary" style="display:none;">Resume</button>
        <button id="stop" class="danger" style="display:none;">Stop</button>
      </div>
      <div id="feed"></div>
    </div>
  </div>
<script nonce="${n}">
  const vscode = acquireVsCodeApi();
  const feed = document.getElementById('feed');
  const statusEl = document.getElementById('status');
  const runBtn = document.getElementById('run');
  const pauseBtn = document.getElementById('pause');
  const resumeBtn = document.getElementById('resume');
  const stopBtn = document.getElementById('stop');

  let streamEl = null;
  let allFiles = [];
  const modifiedFiles = {};

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

  function setControlState(state) {
    if (state === 'running') {
      pauseBtn.style.display = 'inline-block';
      resumeBtn.style.display = 'none';
      stopBtn.style.display = 'inline-block';
    } else if (state === 'paused') {
      pauseBtn.style.display = 'none';
      resumeBtn.style.display = 'inline-block';
      stopBtn.style.display = 'inline-block';
    } else {
      pauseBtn.style.display = 'none';
      resumeBtn.style.display = 'none';
      stopBtn.style.display = 'none';
    }
  }

  function updateExplorer() {
    const list = document.getElementById('file-list');
    list.innerHTML = '';
    
    if (allFiles.length === 0) {
      const empty = document.createElement('div');
      empty.style.opacity = '0.5';
      empty.style.fontStyle = 'italic';
      empty.textContent = 'No files found';
      list.appendChild(empty);
      return;
    }

    allFiles.forEach(file => {
      const item = document.createElement('div');
      item.className = 'file-item';
      
      const change = modifiedFiles[file];
      if (change === 'new') {
        item.classList.add('file-new');
      } else if (change === 'modified') {
        item.classList.add('file-modified');
      }

      const icon = document.createElement('span');
      icon.className = 'file-icon';
      icon.textContent = change === 'new' ? '✚' : change === 'modified' ? '✏' : '📄';
      item.appendChild(icon);

      const name = document.createElement('span');
      name.textContent = file;
      item.appendChild(name);

      item.addEventListener('click', () => {
        vscode.postMessage({ type: 'openFile', path: file });
      });
      list.appendChild(item);
    });
  }

  window.addEventListener('message', (ev) => {
    const e = ev.data;
    switch (e.event) {
      case 'host_status': statusEl.textContent = e.connected ? 'Connected' : 'Disconnected'; break;
      case 'connected': statusEl.textContent = 'Ready · ' + (e.config ? e.config.model : ''); break;
      case 'run_started':
        feed.innerHTML='';
        streamEl=null;
        for (const k in modifiedFiles) delete modifiedFiles[k];
        updateExplorer();
        statusEl.textContent='Running…';
        card('', 'task', e.task);
        setControlState('running');
        break;
      case 'state_changed': streamEl=null; card('', 'state', e.state); break;
      case 'token': ensureStream(e.label).textContent += e.text; break;
      case 'memory_loaded': card('', 'memory', 'Recalled ' + e.count + ' fact(s) learned in previous runs'); break;
      case 'context_trimmed': streamEl=null; card('', 'context trimmed',
        (e.dropped ? 'Dropped ' + e.dropped + ' old step(s) to fit the window'
                   : 'Truncated to fit the window') + ' — ~' + e.est_tokens + ' tokens sent'); break;
      case 'escalation_resolved': card('ok', 'hint accepted', e.hint); break;
      case 'no_progress': streamEl=null; card('fail', 'no progress',
        'Repeated ' + e.tool + ' with no progress — stopping this phase and evaluating'); break;
      case 'give_up':
        streamEl=null;
        setControlState('idle');
        card('fail', 'gave up',
          'Retry budget exhausted after ' + e.retries + (e.retries === 1 ? ' retry' : ' retries')
          + '. Stopping instead of looping.' + (e.summary ? '\\n' + e.summary : ''));
        break;
      case 'plan': streamEl=null; card('', 'plan', e.text); break;
      case 'tool_call':
        streamEl=null;
        card('tool', 'tool: ' + e.tool, JSON.stringify(e.args));
        if (e.tool === 'write_file' || e.tool === 'search_replace' || e.tool === 'replace_all' || e.tool === 'add_docstring') {
          const filePath = e.args.path;
          if (filePath) {
            modifiedFiles[filePath] = e.tool === 'write_file' ? 'new' : 'modified';
            updateExplorer();
          }
        }
        break;
      case 'tool_result': card(e.ok ? 'ok' : 'fail', 'result: ' + e.tool, e.content); break;
      case 'evaluation': card(e.passed ? 'ok' : 'fail', 'evaluation', e.summary); break;
      case 'reflexion': card('', 'reflexion #' + e.retry, e.lesson); break;
      case 'approval_required': card('', 'approval (answer in the VS Code prompt)', e.detail); break;
      case 'escalation_required': card('', 'stuck — hint requested (see prompt)', e.context); break;
      case 'run_paused':
        setControlState('paused');
        statusEl.textContent = 'Paused';
        card('', 'paused', 'Run paused — click Resume to continue.');
        break;
      case 'run_resumed':
        setControlState('running');
        statusEl.textContent = 'Running…';
        card('', 'resumed', 'Run resumed.');
        break;
      case 'run_stopped':
        streamEl = null;
        setControlState('idle');
        statusEl.textContent = 'Stopped';
        card('fail', 'stopped', 'Run stopped by you' + (e.reason ? ' (' + e.reason + ')' : '') + '.');
        break;
      case 'run_finished':
        statusEl.textContent='Finished: ' + e.final_state;
        setControlState('idle');
        if (e.summary) card(e.final_state==='done'?'ok':'fail', 'summary', e.summary);
        if (e.stats) card('', 'telemetry', e.stats.model_calls + ' model calls · '
          + e.stats.total_tokens + ' tokens · ' + (e.stats.total_seconds||0).toFixed(1)
          + 's · $0.00');
        break;
      case 'error':
        setControlState('idle');
        card('fail', 'error', e.message);
        break;
      case 'workspace_files':
        allFiles = e.files;
        const wsInfo = document.getElementById('workspace-info');
        if (e.folders && e.folders.length > 0) {
          wsInfo.innerHTML = '📁 Workspace: <strong>' + e.activeFolder + '</strong>';
        } else {
          wsInfo.innerHTML = '📁 No folder open · <button class="link-btn" id="btn-select-folder">Open Folder</button>';
          document.getElementById('btn-select-folder')?.addEventListener('click', () => {
            vscode.postMessage({ type: 'selectFolder' });
          });
        }
        updateExplorer();
        break;
    }
  });

  runBtn.addEventListener('click', () => {
    const task = document.getElementById('task').value.trim();
    if (task) vscode.postMessage({ type: 'run', task });
  });

  document.getElementById('clear').addEventListener('click', () => {
    feed.innerHTML = '';
    streamEl = null;
  });

  pauseBtn.addEventListener('click', () => {
    vscode.postMessage({ type: 'pause' });
  });

  resumeBtn.addEventListener('click', () => {
    vscode.postMessage({ type: 'resume' });
  });

  stopBtn.addEventListener('click', () => {
    vscode.postMessage({ type: 'stop' });
  });

  vscode.postMessage({ type: 'ready' });
</script>
</body>
</html>`;
}
