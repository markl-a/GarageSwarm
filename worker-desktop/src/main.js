/**
 * GarageSwarm Worker - Electron Main Process
 */

const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, shell } = require('electron');
const path = require('path');
const Store = require('electron-store');
const WorkerService = require('./worker-service');

// Add global error handlers
process.on('uncaughtException', (err) => {
  console.error('Uncaught Exception:', err);
});
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Initialize persistent storage
console.log('Initializing store...');
let store;
try {
  store = new Store({
    defaults: {
      backendUrl: 'http://127.0.0.1:8002',
      autoStart: true,
      minimizeToTray: true
    }
  });
  console.log('Store initialized successfully');
} catch (err) {
  console.error('Store initialization failed:', err);
}

let mainWindow = null;
let tray = null;
let workerService = null;
let isQuitting = false;

// Prevent multiple instances (disabled for debugging)
// const gotTheLock = app.requestSingleInstanceLock();
// if (!gotTheLock) {
//   app.quit();
// } else {
//   app.on('second-instance', () => {
//     if (mainWindow) {
//       if (mainWindow.isMinimized()) mainWindow.restore();
//       mainWindow.focus();
//       mainWindow.show();
//     }
//   });
// }

function createWindow() {
  console.log('Creating window...');
  mainWindow = new BrowserWindow({
    width: 450,
    height: 600,
    minWidth: 400,
    minHeight: 500,
    resizable: true,
    frame: true,
    show: true,
    icon: path.join(__dirname, '../assets/icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  // Load the login page
  const loginPath = path.join(__dirname, 'pages/login.html');
  console.log('Loading file:', loginPath);
  mainWindow.loadFile(loginPath);
  console.log('File load initiated');

  mainWindow.webContents.on('did-finish-load', () => {
    console.log('Page loaded successfully');
    mainWindow.show();
    mainWindow.focus();
  });

  // Show window immediately
  mainWindow.once('ready-to-show', () => {
    console.log('Window ready to show');
    mainWindow.show();
  });

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('Page failed to load:', errorCode, errorDescription);
  });

  // Handle window close - for now, just close (disable minimize to tray for debugging)
  mainWindow.on('close', (event) => {
    console.log('Window close event');
    if (false && !isQuitting && store.get('minimizeToTray')) {
      event.preventDefault();
      mainWindow.hide();
      return false;
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Open DevTools in dev mode
  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools();
  }
}

function createTray() {
  // Create a simple tray icon (will be replaced with actual icon)
  const iconPath = path.join(__dirname, '../assets/icon.png');
  let trayIcon;

  try {
    trayIcon = nativeImage.createFromPath(iconPath);
    if (trayIcon.isEmpty()) {
      // Create a simple colored icon if file doesn't exist
      trayIcon = nativeImage.createEmpty();
    }
  } catch (e) {
    trayIcon = nativeImage.createEmpty();
  }

  tray = new Tray(trayIcon);

  updateTrayMenu('disconnected');

  tray.setToolTip('GarageSwarm Worker');

  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.focus();
      } else {
        mainWindow.show();
      }
    }
  });
}

function updateTrayMenu(status) {
  const statusText = {
    'disconnected': 'Disconnected',
    'connecting': 'Connecting...',
    'online': 'Online',
    'busy': 'Busy (Running Task)',
    'error': 'Error'
  };

  const contextMenu = Menu.buildFromTemplate([
    {
      label: `Status: ${statusText[status] || status}`,
      enabled: false
    },
    { type: 'separator' },
    {
      label: 'Open Dashboard',
      click: () => {
        const backendUrl = store.get('backendUrl');
        shell.openExternal(backendUrl.replace('/api', ''));
      }
    },
    {
      label: 'Show Window',
      click: () => {
        if (mainWindow) mainWindow.show();
      }
    },
    { type: 'separator' },
    {
      label: 'Settings',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.webContents.send('navigate', 'settings');
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        isQuitting = true;
        if (workerService) {
          workerService.stop().then(() => app.quit());
        } else {
          app.quit();
        }
      }
    }
  ]);

  if (tray) {
    tray.setContextMenu(contextMenu);
  }
}

// IPC Handlers
function setupIpcHandlers() {
  // Login handler
  ipcMain.handle('login', async (event, { backendUrl, username, password }) => {
    console.log('IPC login handler called:', { backendUrl, username });
    try {
      // Store backend URL
      store.set('backendUrl', backendUrl);

      // Initialize worker service
      workerService = new WorkerService(backendUrl);
      console.log('WorkerService created');

      // Login and get token
      console.log('Calling workerService.login...');
      const result = await workerService.login(username, password);
      console.log('Login result:', result);

      if (result.success) {
        // Store credentials (encrypted by electron-store)
        store.set('auth', {
          token: result.token,
          refreshToken: result.refreshToken,
          username: username
        });

        return { success: true, user: result.user };
      } else {
        return { success: false, error: result.error };
      }
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  // Logout handler
  ipcMain.handle('logout', async () => {
    try {
      if (workerService) {
        await workerService.stop();
        workerService = null;
      }
      store.delete('auth');
      updateTrayMenu('disconnected');
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  // Start worker handler
  ipcMain.handle('start-worker', async () => {
    try {
      if (!workerService) {
        const backendUrl = store.get('backendUrl');
        const auth = store.get('auth');

        if (!auth || !auth.token) {
          return { success: false, error: 'Not authenticated' };
        }

        workerService = new WorkerService(backendUrl);
        workerService.setToken(auth.token);
      }

      // Set up status callback
      workerService.onStatusChange((status) => {
        updateTrayMenu(status);
        if (mainWindow) {
          mainWindow.webContents.send('worker-status', status);
        }
      });

      // Set up log callback
      workerService.onLog((log) => {
        if (mainWindow) {
          mainWindow.webContents.send('worker-log', log);
        }
      });

      await workerService.start();
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  // Stop worker handler
  ipcMain.handle('stop-worker', async () => {
    try {
      if (workerService) {
        await workerService.stop();
        updateTrayMenu('disconnected');
      }
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  // Get stored settings
  ipcMain.handle('get-settings', () => {
    return {
      backendUrl: store.get('backendUrl'),
      autoStart: store.get('autoStart'),
      minimizeToTray: store.get('minimizeToTray'),
      auth: store.get('auth')
    };
  });

  // Save settings
  ipcMain.handle('save-settings', (event, settings) => {
    if (settings.backendUrl) store.set('backendUrl', settings.backendUrl);
    if (settings.autoStart !== undefined) store.set('autoStart', settings.autoStart);
    if (settings.minimizeToTray !== undefined) store.set('minimizeToTray', settings.minimizeToTray);
    return { success: true };
  });

  // Get worker status
  ipcMain.handle('get-worker-status', () => {
    if (workerService) {
      return workerService.getStatus();
    }
    return { status: 'disconnected', workerId: null };
  });

  // Execute remote command (for debugging)
  ipcMain.handle('execute-command', async (event, command) => {
    try {
      const { exec } = require('child_process');
      return new Promise((resolve) => {
        exec(command, { timeout: 30000 }, (error, stdout, stderr) => {
          resolve({
            success: !error,
            stdout: stdout,
            stderr: stderr,
            error: error ? error.message : null
          });
        });
      });
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
}

// App lifecycle
app.whenReady().then(() => {
  createWindow();
  createTray();
  setupIpcHandlers();

  // Auto-login if credentials exist
  const auth = store.get('auth');
  if (auth && auth.token && store.get('autoStart')) {
    // Attempt to auto-start worker
    setTimeout(async () => {
      try {
        const backendUrl = store.get('backendUrl');
        workerService = new WorkerService(backendUrl);
        workerService.setToken(auth.token);

        workerService.onStatusChange((status) => {
          updateTrayMenu(status);
          if (mainWindow) {
            mainWindow.webContents.send('worker-status', status);
          }
        });

        await workerService.start();

        if (mainWindow) {
          mainWindow.loadFile(path.join(__dirname, 'pages/dashboard.html'));
        }
      } catch (error) {
        console.error('Auto-start failed:', error);
        // Clear invalid auth
        store.delete('auth');
      }
    }, 1000);
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  console.log('window-all-closed event fired');
  if (process.platform !== 'darwin') {
    // Don't quit, keep running in tray
    console.log('Not quitting on Windows');
  }
});

app.on('before-quit', () => {
  console.log('before-quit event fired');
  isQuitting = true;
});

app.on('will-quit', () => {
  console.log('will-quit event fired');
});
