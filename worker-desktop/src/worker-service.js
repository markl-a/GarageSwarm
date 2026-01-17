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
const { spawn } = require('child_process');
const { v4: uuidv4 } = require('uuid');

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
        tools: ['claude_code']
      },
      {
        headers: { 'X-Worker-API-Key': this.token }
      }
    );

    this.workerId = response.data.worker_id;
    this.log('info', 'Worker registered', { workerId: this.workerId });
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
    this.log('info', 'Executing task', { taskId, description: taskData.description?.substring(0, 100) });

    this.currentTask = taskId;
    this.updateStatus('busy');

    try {
      // Execute with Claude Code CLI
      const result = await this.runClaudeCode(taskData.description);

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

  async runClaudeCode(instructions) {
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
        reject(new Error('Task execution timeout (5 minutes)'));
      }, 5 * 60 * 1000);
    });
  }

  async executeRemoteCommand(data) {
    const { command, requestId } = data;
    this.log('info', 'Executing remote command', { command: command.substring(0, 50) });

    try {
      const { exec } = require('child_process');
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
      isRunning: this.isRunning
    };
  }
}

module.exports = WorkerService;
