/**
 * Worker Service - Handles backend communication and task execution
 */

const axios = require('axios');

// Force IPv4 for localhost connections
const dns = require('dns');
dns.setDefaultResultOrder('ipv4first');
const WebSocket = require('ws');
const os = require('os');
const si = require('systeminformation');
const { spawn, exec } = require('child_process');
const { v4: uuidv4 } = require('uuid');
const http = require('http');

// Supported AI Tools
const AI_TOOLS = {
  claude_code: {
    name: 'Claude Code',
    command: 'claude',
    checkArgs: ['--version'],
    provider: 'anthropic'
  },
  gemini_cli: {
    name: 'Gemini CLI',
    command: 'gemini',
    checkArgs: ['--version'],
    provider: 'google'
  },
  ollama: {
    name: 'Ollama',
    command: 'ollama',
    checkArgs: ['--version'],
    provider: 'ollama',
    httpCheck: 'http://localhost:11434/api/tags'
  },
  aider: {
    name: 'Aider',
    command: 'aider',
    checkArgs: ['--version'],
    provider: 'aider'
  }
};

class WorkerService {
  constructor(backendUrl) {
    this.backendUrl = backendUrl.replace(/\/$/, '');
    this.wsUrl = backendUrl.replace('http://', 'ws://').replace('https://', 'wss://');
    this.token = null;
    this.workerId = null;
    this.machineId = this.getMachineId();
    this.ws = null;
    this.isRunning = false;
    this.status = 'disconnected';
    this.currentTask = null;

    this.statusCallback = null;
    this.logCallback = null;
    this.toolsCallback = null;

    this.availableTools = [];
    this.toolVersions = {};

    this.heartbeatInterval = null;
    this.pollingInterval = null;
    this.reconnectTimeout = null;
  }

  getMachineId() {
    // Generate a persistent machine ID based on hardware
    const networkInterfaces = os.networkInterfaces();
    const macAddresses = [];

    for (const [name, interfaces] of Object.entries(networkInterfaces)) {
      for (const iface of interfaces) {
        if (iface.mac && iface.mac !== '00:00:00:00:00:00') {
          macAddresses.push(iface.mac);
        }
      }
    }

    // Create a simple hash from MAC addresses
    const hash = macAddresses.sort().join('-');
    return `desktop-${hash.substring(0, 8)}-${os.hostname()}`;
  }

  setToken(token) {
    this.token = token;
  }

  onStatusChange(callback) {
    this.statusCallback = callback;
  }

  onLog(callback) {
    this.logCallback = callback;
  }

  onToolsUpdate(callback) {
    this.toolsCallback = callback;
  }

  // ============ Tool Detection ============

  async detectAvailableTools() {
    this.log('info', 'Detecting available AI tools...');
    const detected = [];
    const versions = {};

    for (const [toolId, toolConfig] of Object.entries(AI_TOOLS)) {
      try {
        const result = await this.checkToolAvailability(toolId, toolConfig);
        if (result.available) {
          detected.push(toolId);
          versions[toolId] = result.version;
          this.log('info', `Found ${toolConfig.name}`, { version: result.version });
        }
      } catch (error) {
        this.log('debug', `${toolConfig.name} not available`, { error: error.message });
      }
    }

    this.availableTools = detected;
    this.toolVersions = versions;

    if (this.toolsCallback) {
      this.toolsCallback(this.getToolsInfo());
    }

    this.log('info', `Detected ${detected.length} AI tools`, { tools: detected });
    return detected;
  }

  async checkToolAvailability(toolId, toolConfig) {
    // Special handling for Ollama (HTTP check)
    if (toolConfig.httpCheck) {
      return await this.checkOllamaAvailability(toolConfig);
    }

    // CLI-based tools
    return new Promise((resolve) => {
      const proc = spawn(toolConfig.command, toolConfig.checkArgs, {
        shell: process.platform === 'win32',  // Only use shell on Windows
        windowsHide: true
      });

      let output = '';
      proc.stdout.on('data', (data) => { output += data.toString(); });
      proc.stderr.on('data', (data) => { output += data.toString(); });

      proc.on('close', (code) => {
        if (code === 0) {
          resolve({ available: true, version: output.trim().split('\n')[0] });
        } else {
          resolve({ available: false });
        }
      });

      proc.on('error', () => {
        resolve({ available: false });
      });

      // Timeout
      setTimeout(() => {
        proc.kill();
        resolve({ available: false });
      }, 5000);
    });
  }

  async checkOllamaAvailability(toolConfig) {
    return new Promise((resolve) => {
      const url = new URL(toolConfig.httpCheck);
      const req = http.get({
        hostname: url.hostname,
        port: url.port || 80,
        path: url.pathname,
        timeout: 3000
      }, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            const modelCount = json.models?.length || 0;
            resolve({
              available: true,
              version: `${modelCount} models available`
            });
          } catch {
            resolve({ available: true, version: 'running' });
          }
        });
      });

      req.on('error', () => {
        resolve({ available: false });
      });

      req.on('timeout', () => {
        req.destroy();
        resolve({ available: false });
      });
    });
  }

  getToolsInfo() {
    return this.availableTools.map(toolId => ({
      id: toolId,
      name: AI_TOOLS[toolId].name,
      provider: AI_TOOLS[toolId].provider,
      version: this.toolVersions[toolId] || 'unknown'
    }));
  }

  updateStatus(status) {
    this.status = status;
    if (this.statusCallback) {
      this.statusCallback(status);
    }
  }

  log(level, message, data = {}) {
    const logEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      ...data
    };

    console.log(`[${level.toUpperCase()}] ${message}`, data);

    if (this.logCallback) {
      this.logCallback(logEntry);
    }
  }

  async login(username, password) {
    try {
      const response = await axios.post(`${this.backendUrl}/api/v1/auth/login`, {
        username,
        password
      });

      if (response.data.access_token) {
        this.token = response.data.access_token;
        return {
          success: true,
          token: response.data.access_token,
          refreshToken: response.data.refresh_token,
          user: response.data.user
        };
      }

      return { success: false, error: 'No token received' };
    } catch (error) {
      const message = error.response?.data?.detail || error.message;
      return { success: false, error: message };
    }
  }

  async getSystemInfo() {
    try {
      const [cpu, mem, disk, osInfo] = await Promise.all([
        si.cpu(),
        si.mem(),
        si.fsSize(),
        si.osInfo()
      ]);

      return {
        os: `${osInfo.platform} ${osInfo.release}`,
        hostname: os.hostname(),
        cpu: {
          model: cpu.brand,
          cores: cpu.cores,
          speed: cpu.speed
        },
        memory: {
          total: Math.round(mem.total / 1024 / 1024 / 1024),
          unit: 'GB'
        },
        disk: disk.map(d => ({
          mount: d.mount,
          size: Math.round(d.size / 1024 / 1024 / 1024),
          unit: 'GB'
        }))
      };
    } catch (error) {
      return {
        os: `${os.platform()} ${os.release()}`,
        hostname: os.hostname(),
        cpu: { cores: os.cpus().length },
        memory: { total: Math.round(os.totalmem() / 1024 / 1024 / 1024), unit: 'GB' }
      };
    }
  }

  async getResourceUsage() {
    try {
      const [currentLoad, mem, disk] = await Promise.all([
        si.currentLoad(),
        si.mem(),
        si.fsSize()
      ]);

      const mainDisk = disk[0] || { use: 0 };

      return {
        cpu_percent: Math.round(currentLoad.currentLoad),
        memory_percent: Math.round((mem.used / mem.total) * 100),
        disk_percent: Math.round(mainDisk.use || 0)
      };
    } catch (error) {
      return {
        cpu_percent: 0,
        memory_percent: 0,
        disk_percent: 0
      };
    }
  }

  async start() {
    if (this.isRunning) {
      this.log('warn', 'Worker already running');
      return;
    }

    this.isRunning = true;
    this.updateStatus('connecting');
    this.log('info', 'Starting worker service');

    try {
      // Detect available AI tools
      await this.detectAvailableTools();

      if (this.availableTools.length === 0) {
        throw new Error('No AI tools available. Please install Claude Code, Gemini CLI, or Ollama.');
      }

      // Register with backend
      await this.register();

      // Start heartbeat
      this.startHeartbeat();

      // Start WebSocket connection
      this.connectWebSocket();

      // Start polling as fallback
      this.startPolling();

      this.updateStatus('online');
      this.log('info', 'Worker started successfully', { workerId: this.workerId });
    } catch (error) {
      this.updateStatus('error');
      this.log('error', 'Failed to start worker', { error: error.message });
      throw error;
    }
  }

  async stop() {
    this.log('info', 'Stopping worker service');
    this.isRunning = false;

    // Clear intervals
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }

    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    // Close WebSocket
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    // Send offline status
    if (this.workerId) {
      try {
        await this.sendHeartbeat('offline');
      } catch (e) {
        // Ignore errors during shutdown
      }
    }

    this.updateStatus('disconnected');
    this.log('info', 'Worker stopped');
  }

  async register() {
    const systemInfo = await this.getSystemInfo();

    const response = await axios.post(
      `${this.backendUrl}/api/v1/workers/register`,
      {
        machine_id: this.machineId,
        machine_name: `${os.hostname()} (Desktop App)`,
        system_info: systemInfo,
        tools: this.availableTools,
        tool_versions: this.toolVersions
      },
      {
        headers: { 'X-Worker-API-Key': this.token }
      }
    );

    this.workerId = response.data.worker_id;
    this.log('info', 'Worker registered', {
      workerId: this.workerId,
      tools: this.availableTools
    });
  }

  startHeartbeat() {
    const interval = 30000; // 30 seconds

    this.heartbeatInterval = setInterval(async () => {
      if (!this.isRunning) return;

      try {
        await this.sendHeartbeat(this.currentTask ? 'busy' : 'online');
      } catch (error) {
        this.log('warn', 'Heartbeat failed', { error: error.message });
      }
    }, interval);
  }

  async sendHeartbeat(status) {
    const resources = await this.getResourceUsage();

    await axios.post(
      `${this.backendUrl}/api/v1/workers/${this.workerId}/heartbeat`,
      {
        status,
        cpu_percent: resources.cpu_percent,
        memory_percent: resources.memory_percent,
        disk_percent: resources.disk_percent
      },
      {
        headers: { 'X-Worker-API-Key': this.token }
      }
    );
  }

  connectWebSocket() {
    if (this.ws) {
      this.ws.close();
    }

    const wsUrl = `${this.wsUrl}/api/v1/workers/${this.workerId}/ws`;
    this.log('info', 'Connecting to WebSocket', { url: wsUrl });

    try {
      this.ws = new WebSocket(wsUrl, {
        headers: { 'X-Worker-API-Key': this.token }
      });

      this.ws.on('open', () => {
        this.log('info', 'WebSocket connected');
      });

      this.ws.on('message', async (data) => {
        try {
          const message = JSON.parse(data.toString());
          await this.handleWebSocketMessage(message);
        } catch (error) {
          this.log('error', 'Failed to handle WebSocket message', { error: error.message });
        }
      });

      this.ws.on('close', () => {
        this.log('warn', 'WebSocket disconnected');
        this.scheduleReconnect();
      });

      this.ws.on('error', (error) => {
        this.log('error', 'WebSocket error', { error: error.message });
      });
    } catch (error) {
      this.log('error', 'Failed to connect WebSocket', { error: error.message });
      this.scheduleReconnect();
    }
  }

  scheduleReconnect() {
    if (!this.isRunning) return;

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    this.reconnectTimeout = setTimeout(() => {
      if (this.isRunning) {
        this.log('info', 'Reconnecting WebSocket...');
        this.connectWebSocket();
      }
    }, 5000);
  }

  async handleWebSocketMessage(message) {
    this.log('debug', 'Received WebSocket message', { type: message.type });

    switch (message.type) {
      case 'task_assignment':
        await this.executeTask(message.data);
        break;
      case 'remote_command':
        await this.executeRemoteCommand(message.data);
        break;
      case 'ping':
        this.ws.send(JSON.stringify({ type: 'pong' }));
        break;
      default:
        this.log('warn', 'Unknown message type', { type: message.type });
    }
  }

  startPolling() {
    const interval = 10000; // 10 seconds

    this.pollingInterval = setInterval(async () => {
      if (!this.isRunning || this.currentTask) return;

      try {
        const response = await axios.get(
          `${this.backendUrl}/api/v1/workers/${this.workerId}/pull-task`,
          {
            headers: { 'X-Worker-API-Key': this.token },
            timeout: 5000
          }
        );

        if (response.status === 200 && response.data) {
          await this.executeTask(response.data);
        }
      } catch (error) {
        if (error.response?.status !== 204) {
          this.log('debug', 'Polling check', { status: 'no tasks' });
        }
      }
    }, interval);
  }

  async executeTask(taskData) {
    const taskId = taskData.task_id || taskData.subtask_id;
    const preferredTool = taskData.tool || taskData.preferred_tool || this.availableTools[0];

    this.log('info', 'Executing task', {
      taskId,
      tool: preferredTool,
      description: taskData.description?.substring(0, 100)
    });

    this.currentTask = taskId;
    this.updateStatus('busy');

    try {
      // Execute with the specified or default tool
      const result = await this.runAITool(preferredTool, taskData.description, taskData.context);

      // Report success
      await axios.post(
        `${this.backendUrl}/api/v1/workers/${this.workerId}/task-complete`,
        {
          task_id: taskId,
          result: {
            output: result.output,
            metadata: result.metadata
          }
        },
        {
          headers: { 'X-Worker-API-Key': this.token }
        }
      );

      this.log('info', 'Task completed', { taskId });
    } catch (error) {
      this.log('error', 'Task failed', { taskId, error: error.message });

      // Report failure
      try {
        await axios.post(
          `${this.backendUrl}/api/v1/workers/${this.workerId}/task-failed`,
          {
            task_id: taskId,
            error: error.message
          },
          {
            headers: { 'X-Worker-API-Key': this.token }
          }
        );
      } catch (e) {
        this.log('error', 'Failed to report task failure', { error: e.message });
      }
    } finally {
      this.currentTask = null;
      this.updateStatus('online');
    }
  }

  // ============ AI Tool Execution ============

  async runAITool(toolId, instructions, context = {}) {
    if (!this.availableTools.includes(toolId)) {
      throw new Error(`Tool ${toolId} not available. Available: ${this.availableTools.join(', ')}`);
    }

    switch (toolId) {
      case 'claude_code':
        return await this.runClaudeCode(instructions, context);
      case 'gemini_cli':
        return await this.runGeminiCLI(instructions, context);
      case 'ollama':
        return await this.runOllama(instructions, context);
      case 'aider':
        return await this.runAider(instructions, context);
      default:
        throw new Error(`Unknown tool: ${toolId}`);
    }
  }

  async runClaudeCode(instructions, context = {}) {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      let output = '';
      let stderr = '';

      // Use 'claude' command with -p flag for non-interactive mode
      const proc = spawn('claude', ['-p'], {
        shell: true,
        env: { ...process.env }
      });

      // Send instructions via stdin
      proc.stdin.write(instructions);
      proc.stdin.end();

      proc.stdout.on('data', (data) => {
        output += data.toString();
      });

      proc.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      proc.on('close', (code) => {
        const duration = (Date.now() - startTime) / 1000;

        if (code === 0) {
          resolve({
            output: output.trim(),
            metadata: {
              tool: 'claude_code',
              duration,
              exitCode: code
            }
          });
        } else {
          reject(new Error(`Claude Code failed (exit ${code}): ${stderr || output}`));
        }
      });

      proc.on('error', (error) => {
        reject(new Error(`Failed to run Claude Code: ${error.message}`));
      });

      // Timeout after 5 minutes
      setTimeout(() => {
        proc.kill();
        reject(new Error('Claude Code execution timeout (5 minutes)'));
      }, 5 * 60 * 1000);
    });
  }

  async runGeminiCLI(instructions, context = {}) {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      let output = '';
      let stderr = '';

      const args = [
        '--model', context.model || 'gemini-1.5-flash',
        '--format', 'text'
      ];

      const proc = spawn('gemini', args, {
        shell: true,
        env: { ...process.env }
      });

      // Send instructions via stdin
      proc.stdin.write(instructions);
      proc.stdin.end();

      proc.stdout.on('data', (data) => {
        output += data.toString();
      });

      proc.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      proc.on('close', (code) => {
        const duration = (Date.now() - startTime) / 1000;

        if (code === 0) {
          resolve({
            output: output.trim(),
            metadata: {
              tool: 'gemini_cli',
              model: context.model || 'gemini-1.5-flash',
              duration,
              exitCode: code
            }
          });
        } else {
          reject(new Error(`Gemini CLI failed (exit ${code}): ${stderr || output}`));
        }
      });

      proc.on('error', (error) => {
        reject(new Error(`Failed to run Gemini CLI: ${error.message}`));
      });

      // Timeout after 5 minutes
      setTimeout(() => {
        proc.kill();
        reject(new Error('Gemini CLI execution timeout (5 minutes)'));
      }, 5 * 60 * 1000);
    });
  }

  async runOllama(instructions, context = {}) {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      const model = context.model || 'llama2';
      const ollamaUrl = context.url || 'http://localhost:11434';

      const payload = JSON.stringify({
        model: model,
        prompt: instructions,
        stream: false
      });

      const url = new URL(`${ollamaUrl}/api/generate`);
      const options = {
        hostname: url.hostname,
        port: url.port || 11434,
        path: url.pathname,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payload)
        },
        timeout: 5 * 60 * 1000 // 5 minutes
      };

      const req = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          const duration = (Date.now() - startTime) / 1000;
          try {
            const json = JSON.parse(data);
            resolve({
              output: json.response || '',
              metadata: {
                tool: 'ollama',
                model: model,
                duration,
                evalCount: json.eval_count,
                promptEvalCount: json.prompt_eval_count
              }
            });
          } catch (e) {
            reject(new Error(`Failed to parse Ollama response: ${e.message}`));
          }
        });
      });

      req.on('error', (error) => {
        reject(new Error(`Ollama request failed: ${error.message}`));
      });

      req.on('timeout', () => {
        req.destroy();
        reject(new Error('Ollama execution timeout (5 minutes)'));
      });

      req.write(payload);
      req.end();
    });
  }

  async runAider(instructions, context = {}) {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      let output = '';
      let stderr = '';

      const args = ['--message', instructions];

      // Add working directory if provided
      if (context.workingDirectory) {
        args.push('--directory', context.workingDirectory);
      }

      // Add yes-always to avoid prompts
      args.push('--yes-always');

      const proc = spawn('aider', args, {
        shell: true,
        env: { ...process.env }
      });

      proc.stdout.on('data', (data) => {
        output += data.toString();
      });

      proc.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      proc.on('close', (code) => {
        const duration = (Date.now() - startTime) / 1000;

        if (code === 0) {
          resolve({
            output: output.trim(),
            metadata: {
              tool: 'aider',
              duration,
              exitCode: code
            }
          });
        } else {
          reject(new Error(`Aider failed (exit ${code}): ${stderr || output}`));
        }
      });

      proc.on('error', (error) => {
        reject(new Error(`Failed to run Aider: ${error.message}`));
      });

      // Timeout after 10 minutes (Aider can be slower)
      setTimeout(() => {
        proc.kill();
        reject(new Error('Aider execution timeout (10 minutes)'));
      }, 10 * 60 * 1000);
    });
  }

  async executeRemoteCommand(data) {
    const { command, requestId } = data;
    this.log('info', 'Executing remote command', { command: command.substring(0, 50) });

    try {
      const result = await new Promise((resolve) => {
        exec(command, { timeout: 30000 }, (error, stdout, stderr) => {
          resolve({
            success: !error,
            stdout,
            stderr,
            error: error?.message
          });
        });
      });

      // Send result back via WebSocket
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({
          type: 'command_result',
          requestId,
          result
        }));
      }
    } catch (error) {
      this.log('error', 'Remote command failed', { error: error.message });
    }
  }

  getStatus() {
    return {
      status: this.status,
      workerId: this.workerId,
      machineId: this.machineId,
      currentTask: this.currentTask,
      isRunning: this.isRunning,
      tools: this.availableTools,
      toolVersions: this.toolVersions
    };
  }

  getAvailableTools() {
    return this.getToolsInfo();
  }
}

module.exports = WorkerService;
