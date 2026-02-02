const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const { autoUpdater } = require('electron-updater');
const log = require('electron-log');

let mainWindow;

// Configure logging
log.transports.file.level = 'info';
autoUpdater.logger = log;

// Auto-updater configuration
autoUpdater.autoDownload = false;  // Manual download
autoUpdater.autoInstallOnAppQuit = true;
autoUpdater.setFeedURL({
  provider: 'generic',
  url: 'http://107.22.96.217/updates/'
});

// Enable persistent cookie storage - CRITICAL FIX for "Remember Me"
app.commandLine.appendSwitch('disable-features', 'SameSiteByDefaultCookies');

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 1020,
    resizable: true,
    minWidth: 800,      // Reduced minimum for better flexibility
    minHeight: 600,     // Reduced minimum for better flexibility
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      devTools: true,
      webSecurity: false,  // Allow localhost requests
      preload: path.join(__dirname, 'preload.js'),
      partition: 'persist:raffle-app'  // CRITICAL: Enable persistent session storage
    },
    icon: path.join(__dirname, 'icon.ico')
  });

  // Configure session to persist cookies - CRITICAL FIX
  const session = mainWindow.webContents.session;
  
  // Enable persistent storage for cookies
  session.setUserAgent(session.getUserAgent() + ' RaffleApp/1.0');
  
  // Log cookie changes for debugging
  session.cookies.on('changed', (event, cookie, cause, removed) => {
    if (!removed && cookie.name === 'session') {
      log.info(`✅ Session cookie ${cause}: domain=${cookie.domain}, expires=${cookie.expirationDate}`);
    }
  });

  // REMOVED: Fixed zoom - now using responsive CSS
  // mainWindow.webContents.setZoomFactor(0.85);
  
  // Dev Tools available but not auto-opened (press F12 or Ctrl+Shift+I to open)
  // mainWindow.webContents.openDevTools();

  // Open external links in system browser instead of in-app
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Also handle navigation attempts
  mainWindow.webContents.on('will-navigate', (event, url) => {
    // Allow navigation within your app domain
    if (url.startsWith('http://107.22.96.217/') || url.startsWith('http://localhost:')) {
      return; // Allow internal navigation
    }

    // Block and open external links in browser
    event.preventDefault();
    shell.openExternal(url);
  });

  // Enable console logging
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[Renderer] ${message}`);
  });

  // Check if user is already logged in before deciding which page to load
  const checkSession = async () => {
    try {
      // Wait a moment for session to be ready
      await new Promise(resolve => setTimeout(resolve, 500));

      const response = await fetch('http://107.22.96.217/api/auth/current-user', {
        credentials: 'include',
        headers: {
          'Accept': 'application/json'
        }
      });
      const data = await response.json();

      if (data.ok && data.data) {
        // User is logged in, go to dashboard
        log.info(`✅ User session restored: ${data.data.username}`);
        mainWindow.loadURL('http://107.22.96.217/dashboard');
      } else {
        // Not logged in, go to login page
        log.info('No active session found, redirecting to login');
        mainWindow.loadURL('http://107.22.96.217/login');
      }
    } catch (error) {
      // On error, default to login page
      log.error('Session check failed:', error);
      mainWindow.loadURL('http://107.22.96.217/login');
    }
  };

  checkSession();

  // Send version to renderer
  mainWindow.webContents.on('did-finish-load', () => {
    mainWindow.webContents.send('app-version', app.getVersion());
  });
}

// Auto-updater events
autoUpdater.on('checking-for-update', () => {
  log.info('Checking for updates...');
  if (mainWindow) {
    mainWindow.webContents.send('update-status', 'Checking for updates...');
  }
});

autoUpdater.on('update-available', (info) => {
  log.info('Update available:', info.version);
  if (mainWindow) {
    mainWindow.webContents.send('update-available', info.version);
  }
});

autoUpdater.on('update-not-available', () => {
  log.info('No updates available');
  if (mainWindow) {
    mainWindow.webContents.send('update-status', 'App is up to date');
  }
});

autoUpdater.on('download-progress', (progress) => {
  log.info(`Download progress: ${progress.percent}%`);
  if (mainWindow) {
    mainWindow.webContents.send('update-progress', progress.percent);
  }
});

autoUpdater.on('update-downloaded', (info) => {
  log.info('Update downloaded:', info.version);
  if (mainWindow) {
    mainWindow.webContents.send('update-downloaded');
  }
});

autoUpdater.on('error', (error) => {
  log.error('Auto-updater error:', error);
  if (mainWindow) {
    mainWindow.webContents.send('update-status', 'Update check failed');
  }
});

// IPC handlers for manual update check
ipcMain.on('check-for-updates', () => {
  if (mainWindow) {
    mainWindow.webContents.send('update-status', 'Checking for updates...');
  }
  autoUpdater.checkForUpdates();
});

ipcMain.on('download-update', () => {
  autoUpdater.downloadUpdate();
});

ipcMain.on('quit-and-install', () => {
  autoUpdater.quitAndInstall(false, true);
});

app.whenReady().then(async () => {
  try {
    // Backends are already running via systemctl services
    console.log('✅ Connecting to localhost backends via nginx...');
    console.log('✅ Persistent session enabled with partition: persist:raffle-app');
    createWindow();

  } catch (error) {
    console.error('Error during startup:', error);
    createWindow();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});
