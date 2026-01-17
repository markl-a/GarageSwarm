/**
 * Preload script - Secure bridge between renderer and main process
 */
console.log('Preload script starting...');

const { contextBridge, ipcRenderer } = require('electron');
console.log('Electron modules loaded');

// Expose protected methods to renderer
contextBridge.exposeInMainWorld('workerAPI', {
  // Authentication
  login: (backendUrl, username, password) =>
    ipcRenderer.invoke('login', { backendUrl, username, password }),
  logout: () => ipcRenderer.invoke('logout'),

  // Worker control
  startWorker: () => ipcRenderer.invoke('start-worker'),
  stopWorker: () => ipcRenderer.invoke('stop-worker'),
  getWorkerStatus: () => ipcRenderer.invoke('get-worker-status'),

  // Settings
  getSettings: () => ipcRenderer.invoke('get-settings'),
  saveSettings: (settings) => ipcRenderer.invoke('save-settings', settings),

  // Remote command execution
  executeCommand: (command) => ipcRenderer.invoke('execute-command', command),

  // Event listeners
  onWorkerStatus: (callback) => {
    ipcRenderer.on('worker-status', (event, status) => callback(status));
  },
  onWorkerLog: (callback) => {
    ipcRenderer.on('worker-log', (event, log) => callback(log));
  },
  onNavigate: (callback) => {
    ipcRenderer.on('navigate', (event, page) => callback(page));
  },

  // Remove listeners
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  }
});

// Expose app info
console.log('Exposing appInfo...');
try {
  const pkg = require('../package.json');
  contextBridge.exposeInMainWorld('appInfo', {
    version: pkg.version,
    name: pkg.productName || 'Multi-Agent Worker'
  });
  console.log('appInfo exposed successfully');
} catch (err) {
  console.error('Failed to expose appInfo:', err);
}

console.log('Preload script completed');
