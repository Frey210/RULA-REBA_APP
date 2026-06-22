const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('ergoquipt', {
  discoverDevices: () => ipcRenderer.invoke('devices:discover'),
  pairDevice: (payload) => ipcRenderer.invoke('devices:pair', payload),
  backendUrlForDevice: (payload) => ipcRenderer.invoke('network:backend-url-for-device', payload),
})
