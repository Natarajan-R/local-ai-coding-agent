"""Single-page dark-mode dashboard interface template."""
from __future__ import annotations

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AI Coding Agent Dashboard</title>
    <style>
        body {
            background-color: #121212;
            color: #e0e0e0;
            font-family: system-ui, sans-serif;
            margin: 0;
            display: flex;
            height: 100vh;
        }
        #sidebar {
            width: 300px;
            background-color: #1e1e1e;
            border-right: 1px solid #333;
            padding: 20px;
            display: flex;
            flex-direction: column;
        }
        #main {
            flex: 1;
            padding: 20px;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
        }
        .state-pill {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            background-color: #444;
            font-weight: bold;
        }
        .state-active { background-color: #007acc; }
        pre {
            background-color: #1e1e1e;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            border: 1px solid #333;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        .btn-approve { background-color: #28a745; color: white; }
        .btn-deny { background-color: #dc3545; color: white; }
    </style>
</head>
<body>
    <div id="sidebar">
        <h3>Configuration</h3>
        <p>Workspace: <span id="workspace-path">-</span></p>
        <p>FSM State: <span id="fsm-badge" class="state-pill">IDLE</span></p>
    </div>
    
    <div id="main">
        <h2>Active Task Execution</h2>
        <div id="approval-pane" style="display:none; background-color:#332222; padding:15px; border-radius:8px; border:1px solid #dc3545; margin-bottom:15px;">
            <p id="approval-text">Unsafe command execution request approval needed.</p>
            <button class="btn btn-approve" onclick="sendApproval(true)">Approve</button>
            <button class="btn btn-deny" onclick="sendApproval(false)">Deny</button>
        </div>
        
        <h4>Model Token Stream Output:</h4>
        <pre id="token-pane">Stream waiting to start...</pre>
    </div>

    <script>
        // Open WebSocket connection back to the server (forward the session token
        // carried in this page's URL, which the server requires to authorize).
        const _token = new URLSearchParams(window.location.search).get("token");
        const _proto = window.location.protocol === "https:" ? "wss" : "ws";
        const _q = _token ? ("?token=" + encodeURIComponent(_token)) : "";
        const ws = new WebSocket(`${_proto}://${window.location.host}/ws${_q}`);
        let currentApprovalId = null;

        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.event === "connected") {
                document.getElementById("workspace-path").innerText = data.config.workspace;
            }
            
            else if (data.event === "state_changed") {
                const badge = document.getElementById("fsm-badge");
                badge.innerText = data.state.toUpperCase();
                if (data.state === "executing") {
                    badge.className = "state-pill state-active";
                } else {
                    badge.className = "state-pill";
                }
            }
            
            else if (data.event === "token") {
                const pane = document.getElementById("token-pane");
                if (pane.innerText === "Stream waiting to start...") {
                    pane.innerText = "";
                }
                pane.innerText += data.text;
            }
            
            else if (data.event === "approval_required") {
                currentApprovalId = data.id;
                document.getElementById("approval-text").innerText = `Approve Action: ${data.action} - ${data.detail}`;
                document.getElementById("approval-pane").style.display = "block";
            }
        };

        function sendApproval(approved) {
            ws.send(JSON.stringify({
                "type": "approval",
                "id": currentApprovalId,
                "approved": approved
            }));
            document.getElementById("approval-pane").style.display = "none";
        }
    </script>
</body>
</html>
"""
