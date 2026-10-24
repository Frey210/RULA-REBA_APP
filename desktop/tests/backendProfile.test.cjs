const assert = require('node:assert/strict')
const { test } = require('node:test')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const crypto = require('node:crypto')
const { installedEnvironment, backendIsReady } = require('../electron/backend-profile.cjs')
const { version } = require('../package.json')

test('installed profile is explicit and preserves its key/database', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ergosight-profile-'))
  try {
    assert.throws(() => installedEnvironment(root), /not found/)
    assert.equal(fs.readdirSync(root).length, 0)
    fs.writeFileSync(path.join(root, 'ergosight.sqlite3'), 'existing data')
    assert.throws(() => installedEnvironment(root, true), /no profile secret/)
    assert.equal(fs.existsSync(path.join(root, '.jwt-secret')), false)
    fs.unlinkSync(path.join(root, 'ergosight.sqlite3'))
    const first = installedEnvironment(root, true)
    fs.writeFileSync(path.join(root, 'ergosight.sqlite3'), 'existing data')
    assert.deepEqual(installedEnvironment(root), first)
    assert.deepEqual(installedEnvironment(root, true), first)
    assert.equal(fs.readFileSync(path.join(root, 'ergosight.sqlite3'), 'utf8'), 'existing data')
    const profile_id = crypto.createHmac('sha256', first.JWT_SECRET_KEY).update(`ergosight-profile-v1:${first.DATABASE_URL}`).digest('hex')
    const original = global.fetch
    try {
      global.fetch = async () => ({ ok: true, json: async () => ({ app_version: version, profile_id }) })
      assert.equal(await backendIsReady(first), true)
      await assert.rejects(backendIsReady({ ...first, JWT_SECRET_KEY: 'different secret' }), /data profile/)
      await assert.rejects(backendIsReady({ ...first, DATABASE_URL: 'sqlite:///other.sqlite3' }), /data profile/)
      global.fetch = async () => ({ ok: true, json: async () => ({ app_version: 'old', profile_id }) })
      await assert.rejects(backendIsReady(first), /version differs/)
      global.fetch = async () => { throw new Error('offline') }
      assert.equal(await backendIsReady(first), false)
    } finally {
      global.fetch = original
    }
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})
