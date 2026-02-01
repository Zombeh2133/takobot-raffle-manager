const { contextBridge, ipcRenderer } = require('electron');

// Expose electron API to renderer
contextBridge.exposeInMainWorld('electronAPI', {
  // App version
  onAppVersion: (callback) => ipcRenderer.on('app-version', (event, version) => callback(version)),
  
  // Update events
  onUpdateStatus: (callback) => ipcRenderer.on('update-status', (event, message) => callback(message)),
  onUpdateAvailable: (callback) => ipcRenderer.on('update-available', (event, version) => callback(version)),
  onUpdateProgress: (callback) => ipcRenderer.on('update-progress', (event, percent) => callback(percent)),
  onUpdateDownloaded: (callback) => ipcRenderer.on('update-downloaded', () => callback()),
  
  // Update actions
  checkForUpdates: () => ipcRenderer.send('check-for-updates'),
  downloadUpdate: () => ipcRenderer.send('download-update'),
  quitAndInstall: () => ipcRenderer.send('quit-and-install')
});
