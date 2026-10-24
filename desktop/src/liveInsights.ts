export type LiveDetectionEvent = {
  event_type: string
  session_id: string
  cam_id: string
  frame_id: number
  timestamp: number
  detections: LiveDetection[]
  run_id: string
}

export type LiveDetection = {
  worker_id: string
  tracking_id: number
  confidence?: number
  reid_confidence?: number
  bbox: number[]
  keypoints?: {
    format: string
    points: Array<{ id: number; name?: string; x: number; y: number; score?: number }>
  }
  metadata?: Record<string, unknown>
}

export type WorkerInsightSnapshot = Omit<LiveDetectionEvent, 'detections' | 'event_type'> & { detection: LiveDetection }

export function retainWorkerInsights(previous: WorkerInsightSnapshot[], event: LiveDetectionEvent): WorkerInsightSnapshot[] {
  const rows = new Map(previous.filter(row => row.cam_id === event.cam_id && row.run_id === event.run_id && row.session_id === event.session_id)
    .map(row => [row.detection.worker_id, row]))
  for (const detection of event.detections) {
    const old = rows.get(detection.worker_id)
    if (!old || old.timestamp <= event.timestamp) rows.set(detection.worker_id, {
      cam_id: event.cam_id, run_id: event.run_id, session_id: event.session_id,
      timestamp: event.timestamp, frame_id: event.frame_id, detection,
    })
  }
  const snapshots = [...rows.values()]
  const recent = new Set(snapshots.toSorted((a, b) => b.timestamp - a.timestamp).slice(0, 32).map(row => row.detection.worker_id))
  return snapshots.filter(row => recent.has(row.detection.worker_id))
}

export function insightIsLive(timestamp: number, now: number, connected: boolean, running: boolean): boolean {
  return connected && running && now - timestamp >= -1000 && now - timestamp < 2000
}
