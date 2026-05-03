const { app, BrowserWindow, screen, ipcMain, shell } = require('electron');
const path = require('path');

let win;

function createWindow() {
  const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;

  win = new BrowserWindow({
    width: 80,
    height: 80, 
    x: screenWidth - 100,
    y: screenHeight - 100,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    visibleOnAllWorkspaces: true,
    focusable: true,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });


  // Load the React app with the widget view parameter
  win.loadURL('http://localhost:5173/?view=widget');

  // win.webContents.openDevTools();
}

// IPC Handlers for React -> Electron communication
ipcMain.handle('window-control', (event, command) => {
  if (!win) return;
  switch (command) {
    case 'close':
      win.close();
      break;
    case 'minimize':
      win.minimize();
      break;
    case 'toggle-always-on-top':
      const isTop = win.isAlwaysOnTop();
      win.setAlwaysOnTop(!isTop);
      return !isTop;
    case 'open-external':
      // Placeholder for opening other apps or URLs
      break;
  }
});

ipcMain.handle('open-url', (event, url) => {
  shell.openExternal(url);
});

const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', (event, commandLine, workingDirectory) => {
    // Someone tried to run a second instance, we should focus our window.
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });

  app.whenReady().then(() => {
    createWindow();

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
      }
    });
  });
}


app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

