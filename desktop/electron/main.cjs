const { app, BrowserWindow, ipcMain } = require('electron')
const os = require('node:os')
const path = require('node:path')

const isDev = Boolean(process.env.VITE_DEV_SERVER_URL)

function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1120,
    minHeight: 720,
    backgroundColor: '#f7f8fa',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (isDev) {
    win.loadURL(process.env.VITE_DEV_SERVER_URL)
  } else {
    win.loadFile(path.join(__dirname, '../dist/index.html'))
  }
}

ipcMain.handle('devices:discover', async () => {
  const targets = getLocalSubnetTargets(8765)
  const results = await Promise.allSettled(targets.map((target) => probeDevice(target)))
  return results
    .filter((result) => result.status === 'fulfilled' && result.value)
    .map((result) => result.value)
})

ipcMain.handle('devices:pair', async (_event, payload) => {
  const backendUrl = normalizeBackendUrlForDevice(payload.backendUrl, payload.baseUrl)
  const response = await fetch(`${payload.baseUrl}/pairing/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      pairing_code: payload.pairingCode,
      backend_url: backendUrl,
    }),
  })

  if (!response.ok) {
    throw new Error(`Pairing failed: ${response.status}`)
  }
  return response.json()
})

ipcMain.handle('network:backend-url-for-device', async (_event, payload) => {
  return normalizeBackendUrlForDevice(payload.backendUrl, payload.baseUrl)
})

function getLocalSubnetTargets(port) {
  const interfaces = os.networkInterfaces()
  const addresses = []

  for (const entries of Object.values(interfaces)) {
    for (const entry of entries ?? []) {
      if (entry.family !== 'IPv4' || entry.internal) {
        continue
      }
      const parts = entry.address.split('.')
      if (parts.length !== 4) {
        continue
      }
      const prefix = `${parts[0]}.${parts[1]}.${parts[2]}`
      for (let host = 1; host <= 254; host += 1) {
        const ip = `${prefix}.${host}`
        if (ip !== entry.address) {
          addresses.push({ ip, port, baseUrl: `http://${ip}:${port}` })
        }
      }
    }
  }

  return addresses
}

async function probeDevice(target) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 450)
  try {
    const response = await fetch(`${target.baseUrl}/pairing/info`, {
      signal: controller.signal,
    })
    if (!response.ok) {
      return null
    }
    const info = await response.json()
    if (info.service !== 'ergoquipt-edge') {
      return null
    }
    return {
      cam_id: info.cam_id,
      hostname: info.hostname,
      address: target.ip,
      port: target.port,
      status: info.status,
      paired: info.paired,
      baseUrl: target.baseUrl,
    }
  } catch {
    return null
  } finally {
    clearTimeout(timeout)
  }
}

function normalizeBackendUrlForDevice(backendUrl, deviceBaseUrl) {
  try {
    const backend = new URL(backendUrl)
    if (!['127.0.0.1', 'localhost'].includes(backend.hostname)) {
      return backend.toString().replace(/\/$/, '')
    }

    const device = new URL(deviceBaseUrl)
    const localIp = findLocalIpForPeer(device.hostname)
    if (!localIp) {
      return backend.toString().replace(/\/$/, '')
    }
    backend.hostname = localIp
    return backend.toString().replace(/\/$/, '')
  } catch {
    return backendUrl
  }
}

function findLocalIpForPeer(peerIp) {
  const peerParts = peerIp.split('.')
  if (peerParts.length !== 4) {
    return null
  }
  const peerPrefix = `${peerParts[0]}.${peerParts[1]}.${peerParts[2]}`
  const interfaces = os.networkInterfaces()

  for (const entries of Object.values(interfaces)) {
    for (const entry of entries ?? []) {
      if (entry.family !== 'IPv4' || entry.internal) {
        continue
      }
      if (entry.address.startsWith(`${peerPrefix}.`)) {
        return entry.address
      }
    }
  }
  return null
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
