const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('ergoquipt', {
  discoverDevices: () => ipcRenderer.invoke('devices:discover'),
  pairDevice: (payload) => ipcRenderer.invoke('devices:pair', payload),
  backendUrlForDevice: (payload) => ipcRenderer.invoke('network:backend-url-for-device', payload),
  networkStatus: (payload) => ipcRenderer.invoke('network:status', payload),
  scanWifi: (payload) => ipcRenderer.invoke('network:wifi-scan', payload),
  connectWifi: (payload) => ipcRenderer.invoke('network:wifi-connect', payload),
})
