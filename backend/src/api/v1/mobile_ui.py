"""
Mobile UI - Simple web interface for mobile control
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

MOBILE_HTML = '''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Agent Controller</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e; color: #eee; min-height: 100vh; padding: 16px;
        }
        .header { text-align: center; padding: 20px 0; border-bottom: 1px solid #333; margin-bottom: 20px; }
        .header h1 { font-size: 1.5rem; color: #00d4ff; }
        .status-bar { display: flex; justify-content: center; gap: 20px; margin: 15px 0; }
        .status-item { display: flex; align-items: center; gap: 8px; font-size: 0.9rem; }
        .status-dot { width: 10px; height: 10px; border-radius: 50%; }
        .status-dot.green { background: #00ff88; }
        .status-dot.red { background: #ff4444; }
        .card { background: #16213e; border-radius: 12px; padding: 16px; margin-bottom: 16px; border: 1px solid #333; }
        .card-title { font-size: 1.1rem; color: #00d4ff; margin-bottom: 12px; display: flex; justify-content: space-between; }
        .badge { background: #00d4ff; color: #000; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; }
        .item { background: #1a1a2e; border-radius: 8px; padding: 12px; margin-bottom: 8px; }
        .item-name { font-weight: 600; margin-bottom: 4px; }
        .item-info { font-size: 0.85rem; color: #888; }
        .status { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-top: 6px; }
        .status.idle, .status.completed { background: #00ff88; color: #000; }
        .status.busy, .status.in_progress { background: #00d4ff; color: #000; }
        .status.pending { background: #666; }
        .status.failed { background: #ff4444; }
        .input-group { margin-bottom: 12px; }
        .input-group label { display: block; margin-bottom: 6px; color: #888; font-size: 0.9rem; }
        .input-group textarea { width: 100%; padding: 12px; border: 1px solid #333; border-radius: 8px; background: #1a1a2e; color: #fff; font-size: 1rem; min-height: 100px; }
        .btn { width: 100%; padding: 14px; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; }
        .btn-primary { background: linear-gradient(135deg, #00d4ff, #0099cc); color: #000; }
        .btn-refresh { background: #333; color: #fff; margin-top: 10px; }
        .tabs { display: flex; gap: 8px; margin-bottom: 16px; }
        .tab { flex: 1; padding: 12px; text-align: center; background: #333; border-radius: 8px; cursor: pointer; }
        .tab.active { background: #00d4ff; color: #000; }
        .empty { text-align: center; color: #666; padding: 20px; }
        .msg { padding: 12px; border-radius: 8px; margin-bottom: 16px; }
        .msg.success { background: #00ff88; color: #000; }
        .msg.error { background: #ff4444; color: #fff; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Multi-Agent Controller</h1>
        <div class="status-bar">
            <div class="status-item"><div class="status-dot" id="apiStatus"></div><span>API</span></div>
            <div class="status-item"><div class="status-dot" id="dbStatus"></div><span>DB</span></div>
            <div class="status-item"><div class="status-dot" id="redisStatus"></div><span>Redis</span></div>
        </div>
    </div>

    <div class="tabs">
        <div class="tab active" onclick="showTab('workers',this)">Workers</div>
        <div class="tab" onclick="showTab('tasks',this)">Tasks</div>
        <div class="tab" onclick="showTab('create',this)">+ New</div>
    </div>

    <div id="message"></div>

    <div id="workers-tab">
        <div class="card">
            <div class="card-title"><span>Active Workers</span><span class="badge" id="workerCount">0</span></div>
            <div id="workerList"><div class="empty">Loading...</div></div>
        </div>
    </div>

    <div id="tasks-tab" style="display:none;">
        <div class="card">
            <div class="card-title"><span>Tasks</span><span class="badge" id="taskCount">0</span></div>
            <div id="taskList"><div class="empty">Loading...</div></div>
        </div>
    </div>

    <div id="create-tab" style="display:none;">
        <div class="card">
            <div class="card-title">Create New Task</div>
            <div class="input-group">
                <label>Task Description</label>
                <textarea id="taskDesc" placeholder="Describe what you want the AI to do..."></textarea>
            </div>
            <button class="btn btn-primary" onclick="createTask()">Create Task</button>
        </div>
    </div>

    <button class="btn btn-refresh" onclick="refresh()">Refresh</button>

    <script>
        const API = window.location.origin;

        function showTab(tab, el) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('[id$="-tab"]').forEach(t => t.style.display = 'none');
            el.classList.add('active');
            document.getElementById(tab + '-tab').style.display = 'block';
        }

        function showMsg(msg, type) {
            const el = document.getElementById('message');
            el.innerHTML = '<div class="msg ' + type + '">' + msg + '</div>';
            setTimeout(() => el.innerHTML = '', 3000);
        }

        async function api(endpoint, opts = {}) {
            const headers = { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true', ...opts.headers };
            const res = await fetch(API + endpoint, { ...opts, headers });
            return res.json();
        }

        async function checkHealth() {
            try {
                const d = await api('/api/v1/health');
                document.getElementById('apiStatus').className = 'status-dot ' + (d.status === 'healthy' ? 'green' : 'red');
                document.getElementById('dbStatus').className = 'status-dot ' + (d.database === 'connected' ? 'green' : 'red');
                document.getElementById('redisStatus').className = 'status-dot ' + (d.redis === 'connected' ? 'green' : 'red');
            } catch (e) {
                document.getElementById('apiStatus').className = 'status-dot red';
            }
        }

        async function loadWorkers() {
            const el = document.getElementById('workerList');
            try {
                const d = await api('/api/v1/workers');
                const w = d.workers || [];
                document.getElementById('workerCount').textContent = w.length;
                if (w.length === 0) { el.innerHTML = '<div class="empty">No workers online</div>'; return; }
                el.innerHTML = w.map(x => `
                    <div class="item">
                        <div class="item-name">${x.machine_name}</div>
                        <div class="item-info">Tools: ${(x.tools||[]).join(', ')||'None'} | CPU: ${(x.cpu_percent||0).toFixed(1)}% | RAM: ${(x.memory_percent||0).toFixed(1)}%</div>
                        <span class="status ${x.status}">${x.status}</span>
                    </div>
                `).join('');
            } catch (e) { el.innerHTML = '<div class="empty">Failed to load</div>'; }
        }

        async function loadTasks() {
            const el = document.getElementById('taskList');
            try {
                const d = await api('/api/v1/tasks');
                const t = d.tasks || [];
                document.getElementById('taskCount').textContent = t.length;
                if (t.length === 0) { el.innerHTML = '<div class="empty">No tasks yet</div>'; return; }
                el.innerHTML = t.slice(0,10).map(x => `
                    <div class="item">
                        <div class="item-name">${(x.description||'').substring(0,80)}</div>
                        <div class="item-info">Progress: ${x.progress||0}%</div>
                        <span class="status ${x.status}">${x.status}</span>
                    </div>
                `).join('');
            } catch (e) { el.innerHTML = '<div class="empty">Failed to load</div>'; }
        }

        async function createTask() {
            const desc = document.getElementById('taskDesc').value.trim();
            if (!desc) { showMsg('Please enter a description', 'error'); return; }
            try {
                const d = await api('/api/v1/tasks', { method: 'POST', body: JSON.stringify({ description: desc }) });
                if (d.task_id) {
                    showMsg('Task created!', 'success');
                    document.getElementById('taskDesc').value = '';
                    loadTasks();
                } else { showMsg(d.detail || 'Failed', 'error'); }
            } catch (e) { showMsg('Error: ' + e.message, 'error'); }
        }

        function refresh() { checkHealth(); loadWorkers(); loadTasks(); }
        refresh();
        setInterval(refresh, 30000);
    </script>
</body>
</html>'''


@router.get("/", response_class=HTMLResponse)
async def mobile_ui() -> HTMLResponse:
    """Serve mobile UI"""
    return HTMLResponse(content=MOBILE_HTML)
