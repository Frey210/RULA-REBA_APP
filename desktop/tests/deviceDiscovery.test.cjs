const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const path = require('node:path')

test('discovery prioritizes both direct LAN gateways and bounds broad scan concurrency', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../electron/main.cjs'), 'utf8')
  const start = source.indexOf('async function scanDevices(')
  const end = source.indexOf('function normalizeBackendUrlForDevice(', start)
  let active = 0
  let maximum = 0
  const calls = []
  const context = vm.createContext({ probeDevice: async (target, timeout) => {
    active += 1
    maximum = Math.max(maximum, active)
    calls.push([target.ip, timeout])
    await new Promise(resolve => setTimeout(resolve, 1))
    active -= 1
    return target.ip.endsWith('.1') ? target : null
  } })
  vm.runInContext(source.slice(start, end), context)
  const targets = Array.from({ length: 100 }, (_, index) => ({ ip: `10.55.2.${index + 2}` }))
  targets.push({ ip: '10.55.2.1' }, { ip: '10.55.3.1' })
  const result = await context.scanDevices(targets)
  assert.equal(result.length, 2)
  assert.deepEqual(calls.slice(0, 2), [['10.55.2.1', 1500], ['10.55.3.1', 1500]])
  assert.ok(maximum <= 32)
  assert.equal(calls.length, targets.length)
})
