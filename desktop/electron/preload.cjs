const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('ergoquipt', {
  discoverDevices: () => ipcRenderer.invoke('devices:discover'),
})

