const { app, BrowserWindow, dialog, ipcMain } = require('electron')
const { spawn } = require('node:child_process')
const crypto = require('node:crypto')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

const isDev = Boolean(process.env.VITE_DEV_SERVER_URL)
let backendProcess = null
let backendLogFd = null
let mainWindow = null

function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1120,
    minHeight: 720,
    backgroundColor: '#f7f8fa',
    icon: isDev
      ? path.resolve(__dirname, '../build/icon.png')
      : path.join(process.resourcesPath, 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })
  mainWindow = win
  win.on('closed', () => {
    mainWindow = null
  })

  if (isDev) {
    win.loadURL(process.env.VITE_DEV_SERVER_URL)
  } else {
    win.loadFile(path.join(__dirname, '../dist/index.html'))
  }
}

async function startPackagedBackend() {
  if (await backendIsReady()) return

  const executable = path.join(process.resourcesPath, 'backend', 'ergosight-backend.exe')
  if (!fs.existsSync(executable)) {
    throw new Error(`Bundled backend not found: ${executable}`)
  }

  const dataDir = app.getPath('userData')
  const mediaDir = path.join(dataDir, 'media')
  const logDir = path.join(dataDir, 'logs')
  fs.mkdirSync(mediaDir, { recursive: true })
  fs.mkdirSync(logDir, { recursive: true })

  const secretPath = path.join(dataDir, '.jwt-secret')
  if (!fs.existsSync(secretPath)) {
    fs.writeFileSync(secretPath, crypto.randomBytes(48).toString('hex'), { encoding: 'utf8', mode: 0o600 })
  }

  backendLogFd = fs.openSync(path.join(logDir, 'backend.log'), 'a')
  backendProcess = spawn(executable, [], {
    cwd: dataDir,
    env: {
      ...process.env,
      APP_NAME: 'ERGoSIGHT Backend',
      ENVIRONMENT: 'production',
      DATABASE_URL: `sqlite:///${path.join(dataDir, 'ergosight.sqlite3').replaceAll('\\', '/')}`,
      MEDIA_ROOT: mediaDir,
      JWT_SECRET_KEY: fs.readFileSync(secretPath, 'utf8').trim(),
    },
    stdio: ['ignore', backendLogFd, backendLogFd],
    windowsHide: true,
  })

  backendProcess.once('exit', () => {
    backendProcess = null
  })

  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (await backendIsReady()) return
    if (!backendProcess) break
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error(`Backend did not start. See ${path.join(logDir, 'backend.log')}`)
}

async function backendIsReady() {
  try {
    const response = await fetch('http://127.0.0.1:8000/openapi.json', {
      signal: AbortSignal.timeout(800),
    })
    if (!response.ok) return false
    const schema = await response.json()
    return Boolean(schema.paths?.['/api/v1/sessions/{session_id}/events'])
  } catch {
    return false
  }
}

function stopPackagedBackend() {
  backendProcess?.kill()
  backendProcess = null
  if (backendLogFd !== null) fs.closeSync(backendLogFd)
  backendLogFd = null
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
      edge_base_url: payload.baseUrl,
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

ipcMain.handle('network:status', async (_event, payload) => {
  return edgeRequest(payload.baseUrl, '/network/status')
})

ipcMain.handle('network:wifi-scan', async (_event, payload) => {
  return edgeRequest(payload.baseUrl, '/network/wifi')
})

ipcMain.handle('network:wifi-connect', async (_event, payload) => {
  return edgeRequest(payload.baseUrl, '/network/wifi/connect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ssid: payload.ssid, password: payload.password }),
  })
})

async function edgeRequest(baseUrl, pathName, options = {}) {
  const response = await fetch(`${baseUrl}${pathName}`, {
    ...options,
    signal: AbortSignal.timeout(45000),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.detail || `Edge request failed: ${response.status}`)
  }
  return response.json()
}

function getLocalSubnetTargets(port) {
  const interfaces = os.networkInterfaces()
  const addresses = [
    { ip: '10.55.0.1', port, baseUrl: `http://10.55.0.1:${port}` },
    { ip: '10.42.0.1', port, baseUrl: `http://10.42.0.1:${port}` },
  ]

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

  return [...new Map(addresses.map((target) => [target.baseUrl, target])).values()]
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

const hasInstanceLock = app.requestSingleInstanceLock()

if (!hasInstanceLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (!mainWindow) return
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.focus()
  })

  app.whenReady().then(async () => {
    try {
      if (!isDev) await startPackagedBackend()
      createWindow()
    } catch (error) {
      dialog.showErrorBox('ERGoSIGHT could not start', error instanceof Error ? error.message : String(error))
      app.quit()
      return
    }

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createWindow()
      }
    })
  })
}

app.on('before-quit', stopPackagedBackend)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
