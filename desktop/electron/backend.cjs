const { spawn } = require('node:child_process')
const fs = require('node:fs')
const net = require('node:net')
const path = require('node:path')

const backendDir = path.resolve(__dirname, '../../backend')
const pythonPath = path.join(backendDir, '.venv', 'Scripts', 'python.exe')
let child = null
let stopping = false

async function main() {
  if (await isPortOpen(8000)) {
    console.log('Backend already running at http://127.0.0.1:8000')
    keepAlive()
    return
  }

  if (!fs.existsSync(pythonPath)) {
    console.error(`Backend Python environment not found: ${pythonPath}`)
    console.error('Create it from the backend directory before launching Electron.')
    process.exit(1)
  }

  child = spawn(
    pythonPath,
    ['-m', 'alembic', 'upgrade', 'head'],
    {
      cwd: backendDir,
      env: {
        ...process.env,
        DATABASE_URL: process.env.ERGOQUIPT_DATABASE_URL || 'sqlite:///./dev_server.sqlite3',
      },
      stdio: 'inherit',
      windowsHide: true,
    },
  )

  child.on('exit', (code, signal) => {
    if (!stopping) {
      if (code === 0) {
        startBackend()
        return
      }
      child = null
      console.error(`Database migration failed (${signal || code || 0}).`)
      process.exit(code || 1)
    }
  })
}

function startBackend() {
  child = spawn(
    pythonPath,
    ['-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'],
    {
      cwd: backendDir,
      env: backendEnvironment(),
      stdio: 'inherit',
      windowsHide: true,
    },
  )
  child.on('exit', (code, signal) => {
    child = null
    if (!stopping) {
      console.error(`Backend stopped unexpectedly (${signal || code || 0}).`)
      process.exit(code || 1)
    }
  })
}

function backendEnvironment() {
  return {
    ...process.env,
    DATABASE_URL: process.env.ERGOQUIPT_DATABASE_URL || 'sqlite:///./dev_server.sqlite3',
  }
}

function isPortOpen(port) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host: '127.0.0.1', port })
    const finish = (open) => {
      socket.destroy()
      resolve(open)
    }
    socket.setTimeout(500)
    socket.once('connect', () => finish(true))
    socket.once('timeout', () => finish(false))
    socket.once('error', () => finish(false))
  })
}

function keepAlive() {
  setInterval(() => {}, 60_000)
}

function shutdown() {
  if (stopping) return
  stopping = true
  if (!child) {
    process.exit(0)
    return
  }

  child.kill()
  const timeout = setTimeout(() => child?.kill('SIGKILL'), 5_000)
  child.once('exit', () => {
    clearTimeout(timeout)
    process.exit(0)
  })
}

process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)
process.on('SIGHUP', shutdown)

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
