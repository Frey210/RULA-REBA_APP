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
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
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
    const detail = await response.text()
    throw new Error(detail || `Request failed: ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export function liveWebSocketUrl(sessionId: string, token: string): string {
  const base = API_BASE_URL.replace(/^http/, 'ws')
  return `${base}/ws/v1/sessions/${encodeURIComponent(sessionId)}/live?token=${encodeURIComponent(token)}`
}
