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
    minWidth: 1200,
    minHeight: 800,
    webPreferences: {
      partition: 'persist:raffle-app',
      nodeIntegration: false,
      contextIsolation: true,
      devTools: true,
      webSecurity: false,  // Allow localhost requests
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'icon.ico')
  });

  // Configure session to persist cookies - CRITICAL FIX
  const session = mainWindow.webContents.session;

  // Enable persistent storage for cookies
  session.setUserAgent(session.getUserAgent() + ' RaffleApp/1.0');

  // Log ALL cookies on startup to verify persistence
  session.cookies.get({}).then((cookies) => {
    log.info(`📦 Found ${cookies.length} stored cookies on startup`);
    const sessionCookie = cookies.find(c => c.name === 'session');
    if (sessionCookie) {
      log.info(`✅ Session cookie found: domain=${sessionCookie.domain}, expires=${sessionCookie.expirationDate}`);
    } else {
      log.info('❌ No session cookie found on startup');
    }
  }).catch(err => {
    log.error('Error reading cookies:', err);
  });

  // Log cookie changes for debugging
  session.cookies.on('changed', (event, cookie, cause, removed) => {
    if (cookie.name === 'session') {
      if (removed) {
        log.info(`❌ Session cookie removed: ${cause}`);
      } else {
        log.info(`✅ Session cookie ${cause}: domain=${cookie.domain}, expires=${cookie.expirationDate}, httpOnly=${cookie.httpOnly}`);
      }
    }
  });

  // Set zoom level to 85% to reduce scrolling
  mainWindow.webContents.setZoomFactor(0.85);

 // Remove the menu bar
  mainWindow.setMenu(null);

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
      // Check if we have a session cookie stored
      const cookies = await session.cookies.get({ name: 'session' });
      
      if (cookies && cookies.length > 0) {
        log.info(`✅ Session cookie exists, attempting to restore session...`);
        // Load dashboard, which will check auth on the server side
        mainWindow.loadURL('http://107.22.96.217/dashboard');
      } else {
        // No session cookie, go to login
        log.info('❌ No session cookie found, redirecting to login');
        mainWindow.loadURL('http://107.22.96.217/login');
      }
    } catch (error) {
      // On error, default to login page
      log.error('Session check failed:', error);
      mainWindow.loadURL('http://107.22.96.217/login');
    }
  };

  // Wait a moment for session to be fully initialized
  setTimeout(() => {
    checkSession();
  }, 500);

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
    
    // Log where cookies are stored
    const userData = app.getPath('userData');
    console.log(`📁 User data directory: ${userData}`);
    
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
