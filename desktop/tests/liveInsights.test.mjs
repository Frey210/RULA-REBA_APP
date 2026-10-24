import assert from 'node:assert/strict'
import test from 'node:test'
import { retainWorkerInsights, insightIsLive } from '../src/liveInsights.ts'

function event(ids = ['A'], timestamp = 1000, run_id = 'run-1', cam_id = 'CAM_01', session_id = 'SESSION_01') {
  return { event_type: 'session_detection', session_id, cam_id, run_id, timestamp, frame_id: timestamp,
    detections: ids.map(worker_id => ({ worker_id, tracking_id: 1, bbox: [0, 0, 100, 200] })) }
}

test('empty frames retain last known cards without refreshing their timestamp', () => {
  const before = retainWorkerInsights([], event())
  const after = retainWorkerInsights(before, event([], 10000))
  assert.deepEqual(after, before)
  assert.equal(insightIsLive(after[0].timestamp, 10000, true, true), false)
})

test('missing worker remains in place while other workers update', () => {
  const first = retainWorkerInsights([], event(['A', 'B']))
  const second = retainWorkerInsights(first, event(['B'], 2000))
  assert.deepEqual(second.map(row => row.detection.worker_id), ['A', 'B'])
  assert.deepEqual(second.map(row => row.timestamp), [1000, 2000])
  const returning = event(['A'], 2500)
  returning.detections[0].tracking_id = 9
  const third = retainWorkerInsights(second, returning)
  assert.deepEqual(third.map(row => row.detection.worker_id), ['A', 'B'])
  assert.equal(third[0].detection.tracking_id, 9)
})

test('a different camera, run, or session cannot reuse old measurements', () => {
  const initial = retainWorkerInsights([], event())
  for (const next of [event([], 2000, 'run-2'), event([], 2000, 'run-1', 'CAM_02'), event([], 2000, 'run-1', 'CAM_01', 'SESSION_02')]) {
    assert.deepEqual(retainWorkerInsights(initial, next), [])
  }
})

test('out-of-order measurements cannot replace fresher worker data', () => {
  const initial = retainWorkerInsights([], event(['A'], 3000))
  assert.deepEqual(retainWorkerInsights(initial, event(['A'], 1000)), initial)
})

test('only the latest 32 worker snapshots are retained, in stable order', () => {
  let state = []
  for (let i = 0; i < 100; i++) state = retainWorkerInsights(state, event([String(i)], i))
  assert.equal(state.length, 32)
  assert.deepEqual(state.map(row => row.detection.worker_id), Array.from({ length: 32 }, (_, i) => String(68 + i)))
})

test('stopped, disconnected, expired, or future-dated measurements are never live', () => {
  assert.equal(insightIsLive(1000, 1500, true, true), true)
  assert.equal(insightIsLive(1000, 3000, true, true), false)
  assert.equal(insightIsLive(1000, 1500, false, true), false)
  assert.equal(insightIsLive(1000, 1500, true, false), false)
  assert.equal(insightIsLive(5000, 1500, true, true), false)
})
