const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export type AuthTokens = {
  access_token: string
  refresh_token: string
  token_type: string
}

export type CameraNode = {
  id: string
  cam_id: string
  hostname: string | null
  device_type: string | null
  status: string
  paired_at: string | null
  metadata_json: {
    display_name?: string
    edge_base_url?: string
    [key: string]: unknown
  }
}

export type PairingToken = {
  pairing_id: string
  pairing_code: string
  expires_at: string
}

export type SessionRecord = {
  id: string
  session_code: string
  status: string
  started_at: string | null
  stopped_at: string | null
  notes: string | null
  metadata_json: {
    camera_node_ids?: string[]
    edge_start_results?: EdgeCommandResult[]
    edge_stop_results?: EdgeCommandResult[]
    [key: string]: unknown
  }
}

export type EdgeCommandResult = {
  cam_id: string
  status: string
  detail: string
}

export type WorkerRecord = {
  id: string
  employee_number: string | null
  name: string
  department: string | null
  position: string | null
  is_active: boolean
}

export type SessionWorkerRecord = {
  id: string
  session_id: string
  worker_id: string | null
  worker_name: string | null
  employee_number: string | null
  edge_worker_id: string
  tracking_id: number | null
  identity_status: string
  reid_confidence: number | null
  confirmed_at: string | null
}

export type ErgonomicEventRecord = {
  id: string
  session_id: string
  camera_node_id: string
  session_worker_id: string
  worker_id: string | null
  worker_name: string | null
  employee_number: string | null
  edge_worker_id: string
  event_type: string
  status: string
  severity: string
  started_at: string
  ended_at: string | null
  duration_ms: number | null
  score_type: string | null
  score: number | null
  risk_level: string | null
  confidence: number | null
  metadata_json: Record<string, unknown>
  reviewed_assessment_types: string[]
}

export type ScoreAggregateRecord = {
  average: number | null
  peak: number | null
  samples: number
}

export type WorkerExposureSummaryRecord = {
  session_worker_id: string
  worker_id: string | null
  worker_name: string | null
  employee_number: string | null
  edge_worker_id: string
  first_seen_at: string | null
  last_seen_at: string | null
  detection_count: number
  high_risk_event_count: number
  sustained_event_count: number
  high_risk_duration_ms: number
  reviewed_event_count: number
  rula: ScoreAggregateRecord
  reba: ScoreAggregateRecord
}

export type SessionExposureSummaryRecord = {
  session_id: string
  worker_count: number
  event_count: number
  high_risk_event_count: number
  sustained_event_count: number
  high_risk_duration_ms: number
  reviewed_event_count: number
  workers: WorkerExposureSummaryRecord[]
}

export type EventReviewRecord = {
  id: string
  assessment_type: 'rula' | 'reba'
  assessment_status: string
  provisional_score: number | null
  provisional_risk_level: string | null
  score: number
  risk_level: string
  manual_inputs: Record<string, number>
  breakdown: Record<string, unknown>
  notes: string | null
  reviewed_by: string | null
  calculated_at: string
}

export type EventSnapshotRecord = {
  id: string
  snapshot_type: string
  captured_at: string
  content_url: string
  metadata: Record<string, unknown>
}

export type EventDetailRecord = {
  id: string
  angles: Record<string, number | null>
  assessment_quality: {
    status?: string
    measured_components?: number
    required_components?: number
    limitations?: string[]
    [key: string]: unknown
  }
  provisional_scores: Record<string, {
    score?: number
    risk?: string
    risk_level?: string
    breakdown?: Record<string, number>
  }>
  reviews: EventReviewRecord[]
  snapshots: EventSnapshotRecord[]
}

export type WorkerEnrollmentImage = {
  id: string
  worker_id: string
  view: 'front' | 'left' | 'right'
  content_type: string
  file_size: number
  width: number
  height: number
  quality_status: 'good' | 'review_needed' | string
  quality_details: {
    issues?: string[]
    metrics?: Record<string, number | string>
    [key: string]: unknown
  }
  updated_at: string
  image_url: string
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    })
  } catch (err) {
    if (err instanceof TypeError) {
      throw new Error(`Cannot reach backend at ${API_BASE_URL}. Start FastAPI or check CORS/network settings.`, {
        cause: err,
      })
    }
    throw err
  }

  if (!response.ok) {
    const detailText = await response.text()
    let message = detailText
    try {
      const parsed = JSON.parse(detailText) as { detail?: unknown }
      if (typeof parsed.detail === 'string') {
        message = parsed.detail
      }
    } catch {
      message = detailText
    }
    throw new Error(message || `Request failed: ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export async function apiBlob(path: string, token: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) {
    throw new Error(await response.text() || `Request failed: ${response.status}`)
  }
  return response.blob()
}

export function liveWebSocketUrl(sessionId: string, token: string): string {
  const base = API_BASE_URL.replace(/^http/, 'ws')
  return `${base}/ws/v1/sessions/${encodeURIComponent(sessionId)}/live?token=${encodeURIComponent(token)}`
}
