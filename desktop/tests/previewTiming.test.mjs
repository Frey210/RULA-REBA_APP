import assert from 'node:assert/strict'
import test from 'node:test'
import { sameFrame, previewInterval, previewDelay } from '../src/previewTiming.ts'

test('compares exact frame bytes, including different sizes', () => {
  assert.equal(sameFrame(null, new Uint8Array([1])), false)
  assert.equal(sameFrame(new Uint8Array([1]), new Uint8Array([1])), true)
  assert.equal(sameFrame(new Uint8Array([1]), new Uint8Array([2])), false)
  assert.equal(sameFrame(new Uint8Array([1]), new Uint8Array([1, 2])), false)
})

test('auto slows duplicate polling and probes faster for new frames within bounds', () => {
  assert.ok(previewInterval(125, true) > 125)
  assert.ok(previewInterval(125, false) < 125)
  assert.equal(previewInterval(250, true), 250)
  assert.equal(previewInterval(1000 / 12, false), 1000 / 12)
})

test('request duration counts toward pacing; failures back off without an unbounded exponent', () => {
  assert.equal(previewDelay(125, 40, 0), 85)
  assert.equal(previewDelay(125, 200, 0), 10)
  assert.equal(previewDelay(125, 10, 1), 1000)
  assert.equal(previewDelay(125, 10, 10000), 10000)
})
