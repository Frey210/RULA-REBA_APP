import { useEffect, useState } from 'react'
import { Alert, Box, Typography } from '@mui/material'
import { Camera } from 'lucide-react'
import { apiBlob } from './api'
import { previewDelay, previewInterval, sameFrame } from './previewTiming'

export function CameraPreview({ cameraId, label, token, fps, overlay }: {
  cameraId: string; label: string; token: string; fps: number | 'auto'; overlay: boolean
}) {
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [actualFps, setActualFps] = useState(0)
  useEffect(() => {
    let disposed = false
    let timer: ReturnType<typeof setTimeout>
    let request: AbortController | null = null
    let failures = 0
    let interval = 125
    let previous: Uint8Array | null = null
    let displayed = 0
    let measuredAt = performance.now()
    async function nextFrame() {
      const startedAt = performance.now()
      request = new AbortController()
      const timeout = setTimeout(() => request?.abort(), 2500)
      try {
        const blob = await apiBlob(`/api/v1/camera-nodes/${cameraId}/frame?overlay=${overlay}`, token, request.signal)
        const bytes = new Uint8Array(await blob.arrayBuffer())
        const duplicate = sameFrame(previous, bytes)
        if (fps === 'auto') interval = previewInterval(interval, duplicate)
        if (!disposed) {
          if (!duplicate) {
            previous = bytes
            setUrl(URL.createObjectURL(blob))
            displayed += 1
          }
          setError('')
          failures = 0
          const now = performance.now()
          if (now - measuredAt >= 1000) {
            setActualFps(displayed * 1000 / (now - measuredAt))
            measuredAt = now
            displayed = 0
          }
        }
      } catch {
        failures += 1
        if (!disposed) {
          setUrl(null)
          previous = null
          setActualFps(0)
          setError('Camera unavailable. Check the USB camera and device connection, or run Scan LAN.')
        }
      } finally {
        clearTimeout(timeout)
        if (!disposed) timer = setTimeout(() => void nextFrame(),
          previewDelay(fps === 'auto' ? interval : 1000 / fps, performance.now() - startedAt, failures))
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
    {url && !error ? <Typography component="span" sx={{ position: 'absolute', top: 8, right: 8,
      bgcolor: 'rgba(0,0,0,0.8)', color: '#fff', px: 1, py: 0.25, fontSize: 12, borderRadius: 1 }}>
      {fps === 'auto' ? 'Auto' : 'Preview'} / {actualFps.toFixed(1)} FPS
    </Typography> : null}
    {error ? <Alert severity="warning" role="status" sx={{ position: 'absolute', bottom: 12, left: 12, right: 12 }}>{error}</Alert> : null}
  </Box>
}
