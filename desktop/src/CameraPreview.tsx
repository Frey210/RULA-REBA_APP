import { useEffect, useState } from 'react'
import { Alert, Box, Typography } from '@mui/material'
import { Camera } from 'lucide-react'
import { apiBlob } from './api'

export function CameraPreview({ cameraId, label, token, fps, overlay }: {
  cameraId: string; label: string; token: string; fps: number; overlay: boolean
}) {
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let disposed = false
    let timer: ReturnType<typeof setTimeout>
    let request: AbortController | null = null
    let failures = 0
    async function nextFrame() {
      request = new AbortController()
      const timeout = setTimeout(() => request?.abort(), 2500)
      try {
        const blob = await apiBlob(`/api/v1/camera-nodes/${cameraId}/frame?overlay=${overlay}`, token, request.signal)
        if (!disposed) {
          setUrl(URL.createObjectURL(blob))
          setError('')
          failures = 0
        }
      } catch {
        failures += 1
        if (!disposed) {
          setUrl(null)
          setError('Camera unavailable. Check the USB camera and device connection, or run Scan LAN.')
        }
      } finally {
        clearTimeout(timeout)
        if (!disposed) timer = setTimeout(() => void nextFrame(), failures ? Math.min(1000 * 2 ** (failures - 1), 10000) : 1000 / fps)
      }
    }
    void nextFrame()
    return () => { disposed = true; clearTimeout(timer); request?.abort() }
  }, [cameraId, token, fps, overlay])
  useEffect(() => () => { if (url) URL.revokeObjectURL(url) }, [url])
  return <Box className="cameraPreview" role="group" aria-label={`${label} live camera`}>
    {url ? <img className="cameraStream" src={url} alt={`${label} live camera`} /> : (
      <Box className="snapshotPlaceholder"><Camera size={32} /><Typography>Waiting for camera</Typography></Box>
    )}
    {error ? <Alert severity="warning" role="status" sx={{ position: 'absolute', bottom: 12, left: 12, right: 12 }}>{error}</Alert> : null}
  </Box>
}
