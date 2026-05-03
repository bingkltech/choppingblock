const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  controlWindow: (command) => ipcRenderer.invoke('window-control', command),
  openURL: (url) => ipcRenderer.invoke('open-url', url),
});
