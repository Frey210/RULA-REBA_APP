const crypto = require('node:crypto')
const fs = require('node:fs')
const path = require('node:path')
const { version } = require('../package.json')

function installedEnvironment(dataDir, create = false) {
  const secretPath = path.join(dataDir, '.jwt-secret')
  const databasePath = path.join(dataDir, 'ergosight.sqlite3')
  if (create) {
    fs.mkdirSync(dataDir, { recursive: true })
    if (!fs.existsSync(secretPath)) {
      if (fs.existsSync(databasePath)) throw new Error('Existing database has no profile secret. Restore its backup; a new key would break camera pairing.')
      fs.writeFileSync(secretPath, crypto.randomBytes(48).toString('hex'), { encoding: 'utf8', mode: 0o600, flag: 'wx' })
    }
  } else if (!fs.existsSync(databasePath) || !fs.existsSync(secretPath)) {
    throw new Error('Installed ERGoSIGHT profile not found. Start the installed app first; no profile was changed.')
  }
  const secret = fs.readFileSync(secretPath, 'utf8').trim()
  if (secret.length < 32) throw new Error('Installed profile secret is incomplete. Restore its backup; do not reset pairing.')
  return {
    DATABASE_URL: `sqlite:///${databasePath.replaceAll('\\', '/')}`,
    MEDIA_ROOT: path.join(dataDir, 'media'),
    JWT_SECRET_KEY: secret,
  }
}

async function backendIsReady(environment) {
  let response
  try {
    response = await fetch('http://127.0.0.1:8000/api/v1/version', { signal: AbortSignal.timeout(1500) })
  } catch {
    return false
  }
  if (!response.ok) throw new Error('Another backend is using port 8000. Close the older ERGoSIGHT app before retrying.')
  const info = await response.json()
  if (info.app_version !== version) throw new Error('Backend version differs from this app. Close the older ERGoSIGHT app before retrying.')
  if (!environment.JWT_SECRET_KEY) throw new Error('Cannot verify the running backend profile. Close the other ERGoSIGHT app before retrying.')
  if (environment.JWT_SECRET_KEY) {
    const expected = crypto.createHmac('sha256', environment.JWT_SECRET_KEY)
      .update(`ergosight-profile-v1:${environment.DATABASE_URL}`).digest('hex')
    if (info.profile_id !== expected) throw new Error('Another ERGoSIGHT data profile is using port 8000. Close it before opening this profile; do not reset pairing.')
  }
  return true
}

module.exports = { installedEnvironment, backendIsReady }
