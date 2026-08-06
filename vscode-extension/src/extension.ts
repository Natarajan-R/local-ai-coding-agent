// AI Coding Agent — VS Code extension.
//
// The extension host holds a WebSocket to a running `ai-agent serve` instance and
// relays its structured events to a webview chat panel: each message you send is
// one task run, and the agent's plan / tool calls / evaluation render as its reply.
//
// Approval and hint prompts are answered either inline in the thread or with NATIVE
// VS Code dialogs — see `promptTarget()`. Only one of the two is offered at a time,
// so a single decision never gets asked twice.
import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import WebSocket from "ws";

let panel: vscode.WebviewPanel | undefined;
let socket: WebSocket | undefined;
let output: vscode.OutputChannel;
// Absolute path of the workspace the *agent* was started with (`ai-agent serve
// --workspace …`), learned from the `connected` event. This is the only tree the
// agent can read or write, and every path in a tool call is relative to it — so it,
// not the VS Code folder, is what the file panel must show.
let agentWorkspace: string | undefined;
let refreshTimer: NodeJS.Timeout | undefined;
// The server sends `connected` (with the model/workspace config) once, the moment the
// socket opens — long before a webview exists to hear it. Keep it so a panel opened
// later can still be told what it is connected *to*, not merely that it is connected.
let lastConnected: unknown;

export function activate(context: vscode.ExtensionContext): void {
  output = vscode.window.createOutputChannel("AI Coding Agent");
  context.subscriptions.push(
    vscode.commands.registerCommand("aiAgent.openChat", () => openChat(context)),
    // Kept so existing keybindings/muscle memory still work; same panel.
    vscode.commands.registerCommand("aiAgent.openDashboard", () => openChat(context)),
    vscode.commands.registerCommand("aiAgent.runTask", () => runTaskCommand(context)),
    output
  );

  // Watch workspace changes and refresh file explorer in the webview
  const watcher = vscode.workspace.createFileSystemWatcher("**/*");
  watcher.onDidCreate(() => scheduleWorkspaceRefresh());
  watcher.onDidChange(() => scheduleWorkspaceRefresh());
  watcher.onDidDelete(() => scheduleWorkspaceRefresh());
  context.subscriptions.push(
    watcher,
    vscode.workspace.onDidChangeWorkspaceFolders(() => scheduleWorkspaceRefresh())
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

// Where an approval / hint decision should be asked.
//
// Asking in both places at once would prompt the user twice for one decision, so
// exactly one target is chosen. "auto" prefers the thread when the chat panel is
// actually on screen, and falls back to a native dialog when it is hidden or
// closed — otherwise a run started from the command palette could block on a
// prompt nobody can see.
function promptTarget(): "inline" | "native" {
  const style = config<string>("promptStyle", "auto");
  if (style === "inline") { return "inline"; }
  if (style === "native") { return "native"; }
  return panel && panel.visible ? "inline" : "native";
}

async function handleServerEvent(msg: any): Promise<void> {
  if (msg.event === "connected") {
    lastConnected = msg;
    const ws = msg.config && msg.config.workspace;
    if (typeof ws === "string" && ws) {
      agentWorkspace = path.resolve(ws);
      sendWorkspaceFiles();
    }
  }
  // The agent's tree lives outside the editor's folder in the common case, where
  // no FileSystemWatcher fires. Re-scan when a run has actually changed something.
  if (msg.event === "run_finished" || msg.event === "run_stopped") {
    scheduleWorkspaceRefresh();
  }

  const interactive = msg.event === "approval_required" || msg.event === "escalation_required";
  const target = interactive ? promptTarget() : "native";

  // Mirror every event into the chat thread. Interactive events carry the chosen
  // target so the webview knows whether to render actionable controls or just a
  // read-only note pointing at the native dialog.
  toWebview(interactive ? { ...msg, promptTarget: target } : msg);

  if (target === "inline") {
    return; // the webview owns this decision; it replies with approval/hint.
  }

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

// Directories that are never worth showing: build output, caches, and vendored
// trees. `*.egg-info` matters more than it looks — it holds six near-identically
// named files that render as apparent duplicates in a narrow column.
const IGNORED_DIRS = new Set([
  "node_modules", ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
  ".ruff_cache", ".mypy_cache", "out", "dist", "build", ".gemini", "logs",
  ".idea", ".vscode", "htmlcov", ".ai-agent",
]);
const MAX_LISTED_FILES = 500;

// Walk the agent's workspace directly rather than using vscode.workspace.findFiles:
// the agent's root is frequently *not* the folder open in VS Code (here it was
// `ai-coding-agent/workspace`, a subdirectory), and findFiles cannot see outside
// the editor's folders at all.
function walkWorkspace(root: string): { files: string[]; truncated: boolean } {
  const files: string[] = [];
  let truncated = false;
  const stack: string[] = [root];
  while (stack.length > 0) {
    if (files.length >= MAX_LISTED_FILES) { truncated = true; break; }
    const dir = stack.pop() as string;
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;  // unreadable directory: skip rather than fail the whole listing
    }
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (IGNORED_DIRS.has(entry.name) || entry.name.endsWith(".egg-info")) { continue; }
        stack.push(full);
      } else if (entry.isFile()) {
        if (files.length >= MAX_LISTED_FILES) { truncated = true; break; }
        files.push(path.relative(root, full).split(path.sep).join("/"));
      }
    }
  }
  files.sort();
  return { files, truncated };
}

function sendWorkspaceFiles(): void {
  if (!agentWorkspace) {
    // Not connected yet, so the agent's root is unknown. Saying so beats listing
    // the editor's folder, which the agent may have no access to at all.
    toWebview({ event: "workspace_files", root: "", files: [], truncated: false, connected: false });
    return;
  }
  const { files, truncated } = walkWorkspace(agentWorkspace);
  toWebview({
    event: "workspace_files",
    root: agentWorkspace,
    rootName: path.basename(agentWorkspace),
    files,
    truncated,
    connected: true,
  });
}

// The watcher fires for every write in the editor's folder — during a pytest run
// that is hundreds of events, each previously triggering a full re-scan.
function scheduleWorkspaceRefresh(): void {
  if (refreshTimer) { clearTimeout(refreshTimer); }
  refreshTimer = setTimeout(() => { refreshTimer = undefined; sendWorkspaceFiles(); }, 400);
}

async function openFileInEditor(relativePath: string): Promise<void> {
  // Paths in the panel are relative to the agent's workspace, so resolve them
  // against that root — not the editor's folder, which is often a different tree.
  if (!agentWorkspace) { return; }
  const fileUri = vscode.Uri.file(path.join(agentWorkspace, relativePath));
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

function openChat(context: vscode.ExtensionContext): void {
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
      } else if (m.type === "approval") {
        sendToServer({ type: "approval", id: m.id, approved: !!m.approved });
      } else if (m.type === "hint") {
        sendToServer({ type: "hint", id: m.id, hint: m.hint ?? "" });
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
  openChat(context);
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
    padding: 3px 6px;
    border-radius: 3px;
    display: flex;
    align-items: baseline;
    gap: 6px;
    overflow: hidden;
  }
  /* The name carries its own truncation. Clipping on the flex row instead cut the
     glyph box and made trailing underscores invisible — "__init__.py" read as
     " init .py". line-height keeps descenders inside the box. */
  .file-name {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.5;
    flex-shrink: 0;
    max-width: 60%;
  }
  /* Directory shown after the name, truncated from the LEFT so the meaningful tail
     stays visible: six files under one long directory used to truncate to the same
     text and read as duplicates. */
  .file-dir {
    font-size: 10px;
    opacity: .55;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    direction: rtl;
    text-align: left;
    line-height: 1.5;
    flex: 1;
    min-width: 0;
  }
  #file-count {
    font-size: 10px;
    opacity: .6;
    margin-bottom: 6px;
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
    margin-top: 8px;
    flex-shrink: 0;
    align-items: flex-end;
  }
  #hint-row {
    font-size: 11px;
    opacity: .6;
    margin-top: 4px;
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
  #transcript {
    flex: 1;
    overflow-y: auto;
    border: 1px solid var(--vscode-panel-border);
    border-radius: 4px;
    padding: 10px;
    background: var(--vscode-editorWidget-background);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  #empty-state {
    margin: auto;
    text-align: center;
    opacity: .55;
    font-size: 12px;
    line-height: 1.6;
  }
  /* ---- chat turns ---------------------------------------------------- */
  .msg { display: flex; flex-direction: column; }
  .msg-role {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .06em;
    opacity: .6;
    margin-bottom: 3px;
  }
  .msg.user .bubble {
    align-self: flex-start;
    background: var(--vscode-textBlockQuote-background);
    border-left: 3px solid var(--vscode-charts-blue);
    padding: 7px 10px;
    border-radius: 4px;
    white-space: pre-wrap;
    word-break: break-word;
    max-width: 100%;
  }
  .msg.agent {
    border-left: 3px solid var(--vscode-panel-border);
    padding-left: 10px;
  }
  .msg.agent.done { border-left-color: var(--vscode-charts-green); }
  .msg.agent.failed { border-left-color: var(--vscode-charts-red); }
  .turn-status { font-size: 11px; opacity: .75; margin-bottom: 6px; }
  .activity { display: flex; flex-direction: column; gap: 5px; }
  /* ---- individual steps ---------------------------------------------- */
  .card {
    border-left: 3px solid var(--vscode-panel-border);
    padding: 5px 8px;
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
  details.step { background: var(--vscode-editor-background); border-radius: 4px; }
  details.step > summary {
    cursor: pointer;
    padding: 5px 8px;
    font-size: 11px;
    opacity: .8;
    list-style: none;
  }
  details.step > summary::-webkit-details-marker { display: none; }
  details.step > summary::before { content: '▸ '; opacity: .6; }
  details.step[open] > summary::before { content: '▾ '; }
  details.step > pre {
    margin: 0;
    padding: 0 8px 7px 8px;
    font-family: var(--vscode-editor-font-family);
    font-size: 11px;
    white-space: pre-wrap;
    word-break: break-word;
    opacity: .9;
  }
  /* ---- inline prompts ------------------------------------------------- */
  .prompt {
    border: 1px solid var(--vscode-inputValidation-warningBorder, var(--vscode-panel-border));
    background: var(--vscode-inputValidation-warningBackground, var(--vscode-editor-background));
    border-radius: 4px;
    padding: 8px;
  }
  .prompt-title { font-size: 11px; font-weight: 600; margin-bottom: 5px; }
  .prompt pre {
    margin: 0 0 8px 0;
    font-family: var(--vscode-editor-font-family);
    font-size: 12px;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .prompt-actions { display: flex; gap: 6px; align-items: center; }
  .prompt.answered { opacity: .65; }
  .answer-note { font-size: 11px; font-style: italic; opacity: .8; }
  .prompt input[type=text] {
    flex: 1;
    background: var(--vscode-input-background);
    color: var(--vscode-input-foreground);
    border: 1px solid var(--vscode-input-border);
    border-radius: 4px;
    padding: 4px 6px;
    font: inherit;
  }
</style>
</head>
<body>
  <div id="header">
    <div id="workspace-info">📁 Loading workspace…</div>
    <div id="status">Connecting…</div>
  </div>
  <div id="container">
    <div id="explorer-panel">
      <div id="explorer-title">Agent Workspace</div>
      <div id="file-count"></div>
      <div id="file-list">📁 Loading…</div>
    </div>
    <div id="main-panel">
      <div id="transcript">
        <div id="empty-state">
          Ask the agent to change your code.<br />
          Each message runs one task — you'll see its plan, tool calls and test results here.
        </div>
      </div>
      <div id="controls">
        <button id="clear" class="secondary">Clear</button>
        <button id="pause" class="secondary" style="display:none;">Pause</button>
        <button id="resume" class="secondary" style="display:none;">Resume</button>
        <button id="stop" class="danger" style="display:none;">Stop</button>
      </div>
      <div id="composer">
        <textarea id="task" rows="2" placeholder="Describe a coding task…"></textarea>
        <button id="run">Send</button>
      </div>
      <div id="hint-row">Enter to send · Shift+Enter for a new line</div>
    </div>
  </div>
<script nonce="${n}">
  const vscode = acquireVsCodeApi();
  const transcript = document.getElementById('transcript');
  const statusEl = document.getElementById('status');
  const runBtn = document.getElementById('run');
  const taskEl = document.getElementById('task');
  const pauseBtn = document.getElementById('pause');
  const resumeBtn = document.getElementById('resume');
  const stopBtn = document.getElementById('stop');

  let streamEl = null;      // live token sink inside the current turn
  let turnEl = null;        // the agent turn currently being written
  let activityEl = null;    // step container inside that turn
  let statusLineEl = null;  // one-line status at the top of the turn
  let awaitingRunStart = false;  // this webview sent the task, so don't echo it twice
  let running = false;
  let allFiles = [];
  let explorerRoot = '';
  let explorerTruncated = false;
  let explorerConnected = false;
  const modifiedFiles = {};

  // Keep the view pinned to the newest content only when the user is already at the
  // bottom; yanking the scroll while they are reading earlier turns is hostile.
  function nearBottom() {
    return transcript.scrollHeight - transcript.scrollTop - transcript.clientHeight < 80;
  }
  function scrollIfPinned(wasNear) {
    if (wasNear) { transcript.scrollTop = transcript.scrollHeight; }
  }

  function dropEmptyState() {
    const es = document.getElementById('empty-state');
    if (es) { es.remove(); }
  }

  function addUserMessage(text) {
    dropEmptyState();
    const wasNear = nearBottom();
    const wrap = document.createElement('div');
    wrap.className = 'msg user';
    const role = document.createElement('div');
    role.className = 'msg-role'; role.textContent = 'You';
    const bubble = document.createElement('div');
    bubble.className = 'bubble'; bubble.textContent = text;
    wrap.appendChild(role); wrap.appendChild(bubble);
    transcript.appendChild(wrap);
    scrollIfPinned(wasNear);
  }

  // Start a fresh agent turn. Unlike the old flat feed, previous turns are kept:
  // the transcript is the conversation history.
  function beginTurn() {
    dropEmptyState();
    const wasNear = nearBottom();
    turnEl = document.createElement('div');
    turnEl.className = 'msg agent';
    const role = document.createElement('div');
    role.className = 'msg-role'; role.textContent = 'Agent';
    statusLineEl = document.createElement('div');
    statusLineEl.className = 'turn-status'; statusLineEl.textContent = 'Working…';
    activityEl = document.createElement('div');
    activityEl.className = 'activity';
    turnEl.appendChild(role); turnEl.appendChild(statusLineEl); turnEl.appendChild(activityEl);
    transcript.appendChild(turnEl);
    streamEl = null;
    scrollIfPinned(wasNear);
    return turnEl;
  }

  function ensureTurn() {
    if (!activityEl) { beginTurn(); }
    return activityEl;
  }

  function setTurnStatus(text, cls) {
    if (statusLineEl) { statusLineEl.textContent = text; }
    if (turnEl && cls) { turnEl.classList.add(cls); }
  }

  // Append a step to the current agent turn.
  function card(cls, head, body) {
    const host = ensureTurn();
    const wasNear = nearBottom();
    const c = document.createElement('div'); c.className = 'card ' + (cls||'');
    const h = document.createElement('div'); h.className='tag'; h.textContent = head; c.appendChild(h);
    if (body != null) { const b = document.createElement('div'); b.textContent = body; c.appendChild(b); }
    host.appendChild(c); scrollIfPinned(wasNear); return c;
  }

  // Collapsed by default: tool payloads are long and usually noise until they matter.
  function step(head, body, cls) {
    const host = ensureTurn();
    const wasNear = nearBottom();
    const d = document.createElement('details');
    d.className = 'step card ' + (cls||'');
    const s = document.createElement('summary'); s.textContent = head; d.appendChild(s);
    if (body != null && body !== '') {
      const pre = document.createElement('pre'); pre.textContent = body; d.appendChild(pre);
    }
    host.appendChild(d); scrollIfPinned(wasNear); return d;
  }

  function ensureStream(label) {
    if (!streamEl) { const c = card('', label || 'model', ''); streamEl = document.createElement('div');
      streamEl.className = 'stream'; c.appendChild(streamEl); }
    return streamEl;
  }

  // A one-line gist for the collapsed summary: the path if there is one, else the
  // first short scalar argument. Keeps the thread scannable without expanding.
  function shortArgs(args) {
    if (!args || typeof args !== 'object') { return ''; }
    if (args.path) { return String(args.path); }
    for (const k in args) {
      const v = args[k];
      if (typeof v === 'string' && v.length <= 60) { return v; }
    }
    return '';
  }

  function setRunning(isRunning) {
    running = isRunning;
    runBtn.textContent = isRunning ? 'Running…' : 'Send';
    runBtn.disabled = isRunning;
    taskEl.placeholder = isRunning
      ? 'Waiting for the current task to finish…'
      : 'Describe a coding task…';
  }

  // ---- inline prompts -------------------------------------------------
  // Rendered only when the host says this panel owns the decision
  // (promptTarget === 'inline'); otherwise a read-only note points at the dialog.
  function addApprovalPrompt(id, detail, actionable) {
    const host = ensureTurn();
    const wasNear = nearBottom();
    const box = document.createElement('div');
    box.className = 'prompt';
    const title = document.createElement('div');
    title.className = 'prompt-title';
    title.textContent = actionable
      ? 'Approve this command?'
      : 'Approval required — answer in the VS Code prompt';
    box.appendChild(title);
    const pre = document.createElement('pre'); pre.textContent = detail || ''; box.appendChild(pre);
    if (actionable) {
      const actions = document.createElement('div');
      actions.className = 'prompt-actions';
      const yes = document.createElement('button'); yes.textContent = 'Approve';
      const no = document.createElement('button'); no.textContent = 'Deny'; no.className = 'secondary';
      const answer = (approved) => {
        vscode.postMessage({ type: 'approval', id: id, approved: approved });
        actions.remove();
        box.classList.add('answered');
        const note = document.createElement('div');
        note.className = 'answer-note';
        note.textContent = approved ? 'Approved' : 'Denied';
        box.appendChild(note);
      };
      yes.addEventListener('click', () => answer(true));
      no.addEventListener('click', () => answer(false));
      actions.appendChild(yes); actions.appendChild(no);
      box.appendChild(actions);
    }
    host.appendChild(box); scrollIfPinned(wasNear);
  }

  function addHintPrompt(id, context, actionable) {
    const host = ensureTurn();
    const wasNear = nearBottom();
    const box = document.createElement('div');
    box.className = 'prompt';
    const title = document.createElement('div');
    title.className = 'prompt-title';
    title.textContent = actionable
      ? 'The agent is stuck — give it a hint?'
      : 'Hint requested — answer in the VS Code prompt';
    box.appendChild(title);
    const pre = document.createElement('pre'); pre.textContent = context || ''; box.appendChild(pre);
    if (actionable) {
      const actions = document.createElement('div');
      actions.className = 'prompt-actions';
      const input = document.createElement('input');
      input.type = 'text';
      input.placeholder = 'e.g. the bug is an off-by-one in the loop';
      const send = document.createElement('button'); send.textContent = 'Send hint';
      const give = document.createElement('button'); give.textContent = 'Give up'; give.className = 'secondary';
      const answer = (hint) => {
        vscode.postMessage({ type: 'hint', id: id, hint: hint });
        actions.remove();
        box.classList.add('answered');
        const note = document.createElement('div');
        note.className = 'answer-note';
        note.textContent = hint ? 'Hint sent: ' + hint : 'Gave up';
        box.appendChild(note);
      };
      send.addEventListener('click', () => answer(input.value.trim()));
      give.addEventListener('click', () => answer(''));
      input.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') { ev.preventDefault(); answer(input.value.trim()); }
      });
      actions.appendChild(input); actions.appendChild(send); actions.appendChild(give);
      box.appendChild(actions);
      input.focus();
    }
    host.appendChild(box); scrollIfPinned(wasNear);
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
    const count = document.getElementById('file-count');
    list.innerHTML = '';

    if (!explorerConnected) {
      count.textContent = '';
      const empty = document.createElement('div');
      empty.style.opacity = '0.5';
      empty.style.fontStyle = 'italic';
      empty.textContent = 'Not connected — start the ai-agent serve process.';
      list.appendChild(empty);
      return;
    }

    count.textContent = allFiles.length + (explorerTruncated ? '+ files (capped)' : ' file' + (allFiles.length === 1 ? '' : 's'))
      + (explorerRoot ? ' in ' + explorerRoot : '');

    if (allFiles.length === 0) {
      const empty = document.createElement('div');
      empty.style.opacity = '0.5';
      empty.style.fontStyle = 'italic';
      empty.textContent = 'Workspace is empty';
      list.appendChild(empty);
      return;
    }

    allFiles.forEach(file => {
      const item = document.createElement('div');
      item.className = 'file-item';
      item.title = file;   // full path on hover; the row itself shows name + dir

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

      // Lead with the file name. Showing the full relative path truncated to a
      // 220px column made six distinct files under one directory render as the
      // same row six times.
      const slash = file.lastIndexOf('/');
      const base = slash === -1 ? file : file.slice(slash + 1);
      const dir = slash === -1 ? '' : file.slice(0, slash);

      const name = document.createElement('span');
      name.className = 'file-name';
      name.textContent = base;
      item.appendChild(name);

      if (dir) {
        const dirEl = document.createElement('span');
        dirEl.className = 'file-dir';
        dirEl.textContent = dir;
        item.appendChild(dirEl);
      }

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
        // The transcript is the conversation: keep earlier turns, start a new one.
        // A run launched from the command palette never passed through this webview,
        // so echo its task as the user's message; one we sent is already shown.
        if (!awaitingRunStart) { addUserMessage(e.task); }
        awaitingRunStart = false;
        for (const k in modifiedFiles) delete modifiedFiles[k];
        updateExplorer();
        statusEl.textContent='Running…';
        beginTurn();
        setRunning(true);
        setControlState('running');
        break;
      case 'state_changed': streamEl=null; setTurnStatus(e.state); break;
      case 'token': ensureStream(e.label).textContent += e.text; break;
      // Emitted instead of 'token' when the run is not streaming. Without this the
      // model's actual reply never appears — the one thing a chat must not drop.
      case 'assistant_message':
        streamEl = null;
        if (e.content && String(e.content).trim()) { card('', e.label || 'assistant', e.content); }
        break;
      case 'memory_loaded': card('', 'memory', 'Recalled ' + e.count + ' fact(s) learned in previous runs'); break;
      case 'context_trimmed': streamEl=null; card('', 'context trimmed',
        (e.dropped ? 'Dropped ' + e.dropped + ' old step(s) to fit the window'
                   : 'Truncated to fit the window') + ' — ~' + e.est_tokens + ' tokens sent'); break;
      case 'escalation_resolved': card('ok', 'hint accepted', e.hint); break;
      case 'no_progress': streamEl=null; card('fail', 'no progress',
        'Repeated ' + e.tool + ' with no progress — stopping this phase and evaluating'); break;
      case 'give_up':
        streamEl=null;
        setRunning(false);
        setControlState('idle');
        setTurnStatus('Gave up', 'failed');
        card('fail', 'gave up',
          'Retry budget exhausted after ' + e.retries + (e.retries === 1 ? ' retry' : ' retries')
          + '. Stopping instead of looping.' + (e.summary ? '\\n' + e.summary : ''));
        break;
      case 'plan': streamEl=null; card('', 'plan', e.text); break;
      case 'tool_call':
        streamEl=null;
        step('' + e.tool + '  ' + shortArgs(e.args), JSON.stringify(e.args, null, 2), 'tool');
        if (e.tool === 'write_file' || e.tool === 'search_replace' || e.tool === 'replace_all' || e.tool === 'add_docstring') {
          const filePath = e.args.path;
          if (filePath) {
            modifiedFiles[filePath] = e.tool === 'write_file' ? 'new' : 'modified';
            updateExplorer();
          }
        }
        break;
      case 'tool_result':
        step((e.ok ? '✓ ' : '✗ ') + e.tool, e.content, e.ok ? 'ok' : 'fail');
        break;
      case 'evaluation': card(e.passed ? 'ok' : 'fail', 'evaluation', e.summary); break;
      case 'reflexion': card('', 'reflexion #' + e.retry, e.lesson); break;
      case 'approval_required':
        streamEl = null;
        addApprovalPrompt(e.id, e.detail, e.promptTarget === 'inline');
        break;
      case 'escalation_required':
        streamEl = null;
        addHintPrompt(e.id, e.context, e.promptTarget === 'inline');
        break;
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
        setRunning(false);
        setControlState('idle');
        statusEl.textContent = 'Stopped';
        setTurnStatus('Stopped', 'failed');
        card('fail', 'stopped', 'Run stopped by you' + (e.reason ? ' (' + e.reason + ')' : '') + '.');
        break;
      case 'run_finished':
        streamEl = null;
        statusEl.textContent='Finished: ' + e.final_state;
        setRunning(false);
        setControlState('idle');
        setTurnStatus(e.final_state === 'done' ? 'Done' : 'Finished: ' + e.final_state,
                      e.final_state === 'done' ? 'done' : 'failed');
        if (e.summary) card(e.final_state==='done'?'ok':'fail', 'summary', e.summary);
        if (e.stats) card('', 'telemetry', e.stats.model_calls + ' model calls · '
          + e.stats.total_tokens + ' tokens · ' + (e.stats.total_seconds||0).toFixed(1)
          + 's · $0.00');
        // Close the turn so the next message starts a fresh one.
        turnEl = null; activityEl = null; statusLineEl = null;
        break;
      case 'error':
        awaitingRunStart = false;
        setRunning(false);
        setControlState('idle');
        card('fail', 'error', e.message);
        break;
      case 'workspace_files': {
        allFiles = e.files || [];
        explorerRoot = e.rootName || '';
        explorerTruncated = !!e.truncated;
        explorerConnected = !!e.connected;
        const wsInfo = document.getElementById('workspace-info');
        // Show the agent's root, not the editor's folder: they are frequently
        // different trees, and only this one is what the agent can touch.
        wsInfo.textContent = explorerConnected
          ? '📁 Agent workspace: ' + (e.root || '')
          : '📁 Not connected';
        updateExplorer();
        break;
      }
    }
  });

  function submitTask() {
    if (running) { return; }   // the server refuses a second concurrent run
    const task = taskEl.value.trim();
    if (!task) { return; }
    addUserMessage(task);
    awaitingRunStart = true;
    taskEl.value = '';
    vscode.postMessage({ type: 'run', task: task });
  }

  runBtn.addEventListener('click', submitTask);

  // Enter sends, Shift+Enter inserts a newline — the usual chat contract.
  taskEl.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); submitTask(); }
  });

  document.getElementById('clear').addEventListener('click', () => {
    transcript.innerHTML = '';
    streamEl = null; turnEl = null; activityEl = null; statusLineEl = null;
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
