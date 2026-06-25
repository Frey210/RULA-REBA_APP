/* eslint-disable react-hooks/immutability, react-hooks/set-state-in-effect */
import {
  Alert,
  AppBar,
  Box,
  Button,
  Chip,
  CssBaseline,
  Divider,
  Drawer,
  FormControlLabel,
  LinearProgress,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Paper,
  Stack,
  Switch,
  TextField,
  ThemeProvider,
  Toolbar,
  Typography,
  createTheme,
} from '@mui/material'
import {
  Activity,
  BarChart3,
  Camera,
  ClipboardCheck,
  FileText,
  History,
  LayoutDashboard,
  LogOut,
  Pencil,
  RadioReceiver,
  Save,
  Settings,
  ShieldCheck,
  Trash2,
  UserRound,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import './App.css'
import {
  apiBlob,
  apiRequest,
  liveWebSocketUrl,
} from './api'
import type {
  AuthTokens,
  CameraNode,
  PairingToken,
  SessionRecord,
  SessionWorkerRecord,
  WorkerEnrollmentImage,
  WorkerRecord,
} from './api'
import type { DiscoveredDevice } from './types'

const drawerWidth = 248
const backendUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

const navItems = [
  { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { key: 'live', label: 'Live Assessment', icon: Activity },
  { key: 'review', label: 'Session Review', icon: ClipboardCheck },
  { key: 'history', label: 'History', icon: History },
  { key: 'workers', label: 'Workers', icon: UserRound },
  { key: 'reports', label: 'Reports', icon: FileText },
  { key: 'settings', label: 'Devices', icon: Settings },
]

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#176d6a' },
    secondary: { main: '#8a5a12' },
    background: { default: '#f6f7f8', paper: '#ffffff' },
    success: { main: '#287d4f' },
    warning: { main: '#a76405' },
    error: { main: '#b42318' },
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: 'Inter, Segoe UI, Arial, sans-serif',
    h5: { fontWeight: 700 },
    h6: { fontWeight: 700 },
    button: { textTransform: 'none', fontWeight: 700 },
  },
})

function App() {
  const [tokens, setTokens] = useState<AuthTokens | null>(() => {
    const raw = localStorage.getItem('ergoquipt.tokens')
    return raw ? (JSON.parse(raw) as AuthTokens) : null
  })
  const [activePage, setActivePage] = useState('dashboard')
  const [cameraNodes, setCameraNodes] = useState<CameraNode[]>([])
  const [sessions, setSessions] = useState<SessionRecord[]>([])
  const [workers, setWorkers] = useState<WorkerRecord[]>([])
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking')
  const [error, setError] = useState<string | null>(null)

  const token = tokens?.access_token ?? null

  useEffect(() => {
    void refreshBackendStatus()
  }, [])

  const refreshData = useCallback(async () => {
    if (!token) return
    try {
      const [nodes, sessionRows, workerRows] = await Promise.all([
        apiRequest<CameraNode[]>('/api/v1/camera-nodes', {}, token),
        apiRequest<SessionRecord[]>('/api/v1/sessions', {}, token),
        apiRequest<WorkerRecord[]>('/api/v1/workers', {}, token),
      ])
      setCameraNodes(nodes)
      setSessions(sessionRows)
      setWorkers(workerRows)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    }
  }, [token])

  useEffect(() => {
    if (token) {
      void refreshData()
    }
  }, [token, refreshData])

  async function refreshBackendStatus() {
    try {
      await apiRequest<{ status: string }>('/health')
      setBackendStatus('online')
    } catch {
      setBackendStatus('offline')
    }
  }

  function handleLogin(nextTokens: AuthTokens) {
    localStorage.setItem('ergoquipt.tokens', JSON.stringify(nextTokens))
    setTokens(nextTokens)
  }

  function logout() {
    localStorage.removeItem('ergoquipt.tokens')
    setTokens(null)
    setCameraNodes([])
    setSessions([])
    setWorkers([])
  }

  if (!tokens) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <LoginScreen onLogin={handleLogin} backendStatus={backendStatus} />
      </ThemeProvider>
    )
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box className="appShell">
        <AppBar position="fixed" elevation={0} className="topBar">
          <Toolbar>
            <ShieldCheck size={22} />
            <Typography variant="h6" sx={{ ml: 1, flexGrow: 1 }}>
              ErgoQuipt
            </Typography>
            <StatusChip status={backendStatus} />
            <Button color="inherit" startIcon={<LogOut size={18} />} onClick={logout}>
              Logout
            </Button>
          </Toolbar>
        </AppBar>

        <Drawer
          variant="permanent"
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box' },
          }}
        >
          <Toolbar />
          <Box className="drawerHeader">
            <Typography variant="overline">Workspace</Typography>
            <Typography variant="body2">HSE Operator Console</Typography>
          </Box>
          <List>
            {navItems.map((item) => {
              const Icon = item.icon
              return (
                <ListItemButton
                  key={item.key}
                  selected={activePage === item.key}
                  onClick={() => setActivePage(item.key)}
                >
                  <ListItemIcon>
                    <Icon size={20} />
                  </ListItemIcon>
                  <ListItemText primary={item.label} />
                </ListItemButton>
              )
            })}
          </List>
        </Drawer>

        <Box component="main" className="mainPane">
          <Toolbar />
          {error ? <Alert severity="error">{error}</Alert> : null}
          <Page
            activePage={activePage}
            setActivePage={setActivePage}
            token={tokens.access_token}
            cameraNodes={cameraNodes}
            sessions={sessions}
            workers={workers}
            refreshData={refreshData}
          />
        </Box>
      </Box>
    </ThemeProvider>
  )
}

function LoginScreen({
  onLogin,
  backendStatus,
}: {
  onLogin: (tokens: AuthTokens) => void
  backendStatus: string
}) {
  const [email, setEmail] = useState('operator@example.com')
  const [password, setPassword] = useState('strong-password')
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    try {
      if (mode === 'register') {
        await apiRequest('/api/v1/auth/register', {
          method: 'POST',
          body: JSON.stringify({ email, password, full_name: 'HSE Operator' }),
        })
      }
      const tokens = await apiRequest<AuthTokens>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      onLogin(tokens)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box className="loginPage">
      <Paper className="loginPanel" elevation={0}>
        <Stack spacing={3}>
          <Box className="inlineTitle">
            <ShieldCheck size={28} />
            <Typography variant="h5">ErgoQuipt</Typography>
          </Box>
          <Stack direction="row" spacing={1}>
            <StatusChip status={backendStatus} />
            <Chip size="small" label="JWT secured" color="primary" variant="outlined" />
          </Stack>
          {error ? <Alert severity="error">{error}</Alert> : null}
          <Box component="form" onSubmit={submit}>
            <Stack spacing={2}>
              <TextField label="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
              <TextField
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {loading ? <LinearProgress /> : null}
              <Button type="submit" variant="contained" disabled={loading}>
                {mode === 'login' ? 'Login' : 'Create account'}
              </Button>
              <Button onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
                {mode === 'login' ? 'Create first user' : 'Use existing user'}
              </Button>
            </Stack>
          </Box>
        </Stack>
      </Paper>
    </Box>
  )
}

function Page({
  activePage,
  setActivePage,
  token,
  cameraNodes,
  sessions,
  workers,
  refreshData,
}: {
  activePage: string
  setActivePage: (page: string) => void
  token: string
  cameraNodes: CameraNode[]
  sessions: SessionRecord[]
  workers: WorkerRecord[]
  refreshData: () => Promise<void>
}) {
  if (activePage === 'live') {
    return <LiveAssessment token={token} sessions={sessions} workers={workers} cameraNodes={cameraNodes} refreshData={refreshData} />
  }
  if (activePage === 'settings') {
    return <SettingsPage token={token} cameraNodes={cameraNodes} refreshData={refreshData} />
  }
  if (activePage === 'history') {
    return <SessionList title="History" sessions={sessions} />
  }
  if (activePage === 'workers') {
    return <WorkerRegistry token={token} workers={workers} refreshData={refreshData} />
  }
  if (activePage === 'reports') {
    return <Placeholder title="Reports" icon={FileText} />
  }
  if (activePage === 'review') {
    return <Placeholder title="Session Review" icon={ClipboardCheck} />
  }
  return (
    <Dashboard
      cameraNodes={cameraNodes}
      sessions={sessions}
      refreshData={refreshData}
      openDevices={() => setActivePage('settings')}
    />
  )
}

function Dashboard({
  cameraNodes,
  sessions,
  refreshData,
  openDevices,
}: {
  cameraNodes: CameraNode[]
  sessions: SessionRecord[]
  refreshData: () => Promise<void>
  openDevices: () => void
}) {
  const running = sessions.filter((session) => session.status === 'running').length
  const paired = cameraNodes.length

  return (
    <Stack spacing={3}>
      <PageTitle
        title="Dashboard"
        action={
          <Stack direction="row" spacing={1}>
            <Button variant="contained" startIcon={<Camera size={18} />} onClick={openDevices}>
              Add Edge Camera
            </Button>
            <Button onClick={refreshData}>Refresh</Button>
          </Stack>
        }
      />
      <Box className="metricGrid">
        <Metric label="Paired Cameras" value={paired} icon={Camera} />
        <Metric label="Running Sessions" value={running} icon={Activity} />
        <Metric label="Review Queue" value={sessions.filter((s) => s.status === 'review_pending').length} icon={ClipboardCheck} />
        <Metric label="Reports" value={0} icon={BarChart3} />
      </Box>
      <DeviceTable cameraNodes={cameraNodes} />
      <SessionList title="Recent Sessions" sessions={sessions.slice(0, 5)} />
    </Stack>
  )
}

type LiveDetectionEvent = {
  event_type: string
  session_id: string
  cam_id: string
  frame_id: number
  timestamp: number
  detections: LiveDetection[]
}

type LiveDetection = {
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

function LiveAssessment({
  token,
  sessions,
  workers,
  cameraNodes,
  refreshData,
}: {
  token: string
  sessions: SessionRecord[]
  workers: WorkerRecord[]
  cameraNodes: CameraNode[]
  refreshData: () => Promise<void>
}) {
  const [sessionCode, setSessionCode] = useState(sessions[0]?.session_code ?? '')
  const [selectedCamIds, setSelectedCamIds] = useState<string[]>(() => cameraNodes.map((node) => node.cam_id).slice(0, 1))
  const [notes, setNotes] = useState('')
  const [events, setEvents] = useState<LiveDetectionEvent[]>([])
  const [sessionWorkers, setSessionWorkers] = useState<SessionWorkerRecord[]>([])
  const [connected, setConnected] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [showStream, setShowStream] = useState(true)
  const [showOverlay, setShowOverlay] = useState(true)
  const [streamFps, setStreamFps] = useState(8)

  const activeSession = sessions.find((session) => session.session_code === sessionCode)
  const latestEvent = events[0]
  const latestVisibleEvent = events.find(
    (event) => event.detections.length > 0 && (latestEvent?.timestamp ?? event.timestamp) - event.timestamp <= 2_000,
  )
  const selectedSessionEdgeResults = activeSession?.metadata_json.edge_start_results ?? []
  const streamCamera = findStreamCamera(activeSession, cameraNodes, selectedCamIds)
  const streamUrl = showStream && streamCamera ? buildStreamUrl(streamCamera, streamFps, showOverlay) : null
  const activeWorkerCount = latestEvent?.detections.length ?? 0
  const recentWorkerCount = new Set(events.flatMap((event) => event.detections.map((detection) => detection.worker_id))).size

  useEffect(() => {
    if (!sessionCode && sessions[0]) {
      setSessionCode(sessions[0].session_code)
    }
  }, [sessionCode, sessions])

  useEffect(() => {
    if (!sessionCode) return
    const ws = new WebSocket(liveWebSocketUrl(sessionCode, token))
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (event) => {
      const parsed = JSON.parse(event.data) as LiveDetectionEvent
      setEvents((current) => [parsed, ...current].slice(0, 50))
    }
    return () => ws.close()
  }, [sessionCode, token])

  useEffect(() => {
    const sessionId = activeSession?.id
    if (!sessionId) {
      setSessionWorkers([])
      return
    }

    async function loadSessionWorkers() {
      try {
        const rows = await apiRequest<SessionWorkerRecord[]>(
          `/api/v1/sessions/${sessionId}/workers`,
          {},
          token,
        )
        setSessionWorkers(rows)
      } catch {
        setSessionWorkers([])
      }
    }

    void loadSessionWorkers()
    if (activeSession?.status !== 'running') return
    const interval = window.setInterval(() => void loadSessionWorkers(), 1_500)
    return () => window.clearInterval(interval)
  }, [activeSession?.id, activeSession?.status, token])

  async function assignWorker(sessionWorkerId: string, workerId: string | null) {
    if (!activeSession) return
    const updated = await apiRequest<SessionWorkerRecord>(
      `/api/v1/sessions/${activeSession.id}/workers/${sessionWorkerId}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ worker_id: workerId }),
      },
      token,
    )
    setSessionWorkers((current) =>
      current.map((row) => row.id === updated.id ? updated : row),
    )
  }

  async function createAndStartSession() {
    if (!selectedCamIds.length) {
      setMessage('Select at least one paired camera node.')
      return
    }
    setLoading(true)
    setMessage(null)
    try {
      const session = await apiRequest<SessionRecord>(
        '/api/v1/sessions',
        {
          method: 'POST',
          body: JSON.stringify({
            camera_node_ids: selectedCamIds,
            notes: notes.trim() || null,
          }),
        },
        token,
      )
      const started = await apiRequest<SessionRecord>(
        `/api/v1/sessions/${session.id}/start`,
        { method: 'POST' },
        token,
      )
      setSessionCode(started.session_code)
      setEvents([])
      setMessage('Session started. Waiting for edge detection events.')
      await refreshData()
    } catch (err) {
      setMessage(err instanceof Error ? `Start session failed: ${err.message}` : 'Start session failed.')
    } finally {
      setLoading(false)
    }
  }

  async function startSelectedSession() {
    if (!activeSession) return
    setLoading(true)
    setMessage(null)
    try {
      const started = await apiRequest<SessionRecord>(
        `/api/v1/sessions/${activeSession.id}/start`,
        { method: 'POST' },
        token,
      )
      setSessionCode(started.session_code)
      setEvents([])
      setMessage('Session started. Waiting for edge detection events.')
      await refreshData()
    } catch (err) {
      setMessage(err instanceof Error ? `Start session failed: ${err.message}` : 'Start session failed.')
    } finally {
      setLoading(false)
    }
  }

  async function stopSelectedSession() {
    if (!activeSession) return
    setLoading(true)
    setMessage(null)
    try {
      await apiRequest<SessionRecord>(
        `/api/v1/sessions/${activeSession.id}/stop`,
        { method: 'POST' },
        token,
      )
      setMessage('Session stopped.')
      await refreshData()
    } catch (err) {
      setMessage(err instanceof Error ? `Stop session failed: ${err.message}` : 'Stop session failed.')
    } finally {
      setLoading(false)
    }
  }

  function toggleCamera(camId: string) {
    setSelectedCamIds((current) =>
      current.includes(camId) ? current.filter((id) => id !== camId) : [...current, camId],
    )
  }

  return (
    <Stack spacing={3}>
      <PageTitle title="Live Assessment" action={<StatusChip status={connected ? 'online' : 'offline'} />} />
      <Paper className="panel" elevation={0}>
        <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap', rowGap: 1 }}>
          <TextField
            select
            label="Session"
            value={sessionCode}
            onChange={(event) => {
              setSessionCode(event.target.value)
              setEvents([])
            }}
            sx={{ minWidth: 320 }}
          >
            {sessions.map((session) => (
              <MenuItem key={session.id} value={session.session_code}>
                {session.session_code} - {session.status}
              </MenuItem>
            ))}
          </TextField>
          <Button variant="contained" disabled={loading || !activeSession || activeSession.status === 'running'} onClick={startSelectedSession}>
            Start Selected
          </Button>
          <Button color="error" variant="outlined" disabled={loading || !activeSession || activeSession.status !== 'running'} onClick={stopSelectedSession}>
            Stop
          </Button>
        </Stack>
        {selectedSessionEdgeResults.length ? (
          <Box className="pairingSteps" sx={{ mt: 2 }}>
            {selectedSessionEdgeResults.map((result) => (
              <Chip
                key={`${result.cam_id}-${result.status}`}
                size="small"
                color={result.status === 'started' ? 'success' : result.status === 'error' ? 'error' : 'default'}
                label={`${result.cam_id}: ${result.status}`}
              />
            ))}
          </Box>
        ) : null}
        <Divider sx={{ my: 2 }} />
        <Box className="metricGrid">
          <Metric label="Live Events" value={events.length} icon={Activity} />
          <Metric label="Latest Frame" value={latestEvent?.frame_id ?? 0} icon={Camera} />
          <Metric label="People in Frame" value={activeWorkerCount} icon={ClipboardCheck} />
          <Metric label="Recent Workers" value={recentWorkerCount} icon={BarChart3} />
        </Box>
      </Paper>

      <Paper className="panel" elevation={0}>
        <Typography variant="h6">Start New Session</Typography>
        <Divider sx={{ my: 2 }} />
        <Stack spacing={2}>
          <Box className="pairingSteps">
            {cameraNodes.map((node) => {
              const label = node.metadata_json.display_name ?? node.cam_id
              const selected = selectedCamIds.includes(node.cam_id)
              return (
                <Chip
                  key={node.id}
                  clickable
                  color={selected ? 'primary' : 'default'}
                  label={`${label} (${node.status})`}
                  onClick={() => toggleCamera(node.cam_id)}
                />
              )
            })}
          </Box>
          <TextField label="Session notes" value={notes} onChange={(event) => setNotes(event.target.value)} />
          <Button variant="contained" disabled={loading || !cameraNodes.length} onClick={createAndStartSession}>
            Create and Start Session
          </Button>
        </Stack>
        {loading ? <LinearProgress sx={{ mt: 2 }} /> : null}
        {message ? (
          <Alert severity="info" sx={{ mt: 2 }}>
            {message}
          </Alert>
        ) : null}
      </Paper>

      <Paper className="panel" elevation={0}>
        <Stack direction="row" spacing={2} sx={{ alignItems: 'center', flexWrap: 'wrap', rowGap: 1 }}>
          <Typography variant="h6">Live Stream</Typography>
          <FormControlLabel
            control={<Switch checked={showStream} onChange={(event) => setShowStream(event.target.checked)} />}
            label="Camera"
          />
          <FormControlLabel
            control={<Switch checked={showOverlay} onChange={(event) => setShowOverlay(event.target.checked)} />}
            label="Overlay"
          />
          <TextField
            select
            size="small"
            label="FPS"
            value={streamFps}
            onChange={(event) => setStreamFps(Number(event.target.value))}
            sx={{ width: 110 }}
          >
            <MenuItem value={4}>4</MenuItem>
            <MenuItem value={8}>8</MenuItem>
            <MenuItem value={12}>12</MenuItem>
          </TextField>
        </Stack>
        <Divider sx={{ my: 2 }} />
        <Box className="liveGrid">
          <Box className="livePreview">
            {streamUrl ? (
              <img className="cameraStream" src={streamUrl} alt={`${streamCamera?.cam_id ?? 'Camera'} live stream`} />
            ) : latestVisibleEvent?.detections.length ? (
              <>
                <Typography variant="h6">{latestVisibleEvent.detections.length} worker(s) detected</Typography>
                <Typography>Latest frame: {latestVisibleEvent.frame_id}</Typography>
              </>
            ) : !streamCamera ? (
              <Typography color="text.secondary">Pair a camera node with an edge stream URL to show live video.</Typography>
            ) : (
              <Typography color="text.secondary">Waiting for Raspberry Pi detection events.</Typography>
            )}
          </Box>
          <DetectionInsights
            latestEvent={latestVisibleEvent}
            events={events}
            workers={workers}
            sessionWorkers={sessionWorkers}
            assignWorker={assignWorker}
          />
        </Box>
      </Paper>
    </Stack>
  )
}

function DetectionInsights({
  latestEvent,
  events,
  workers,
  sessionWorkers,
  assignWorker,
}: {
  latestEvent: LiveDetectionEvent | undefined
  events: LiveDetectionEvent[]
  workers: WorkerRecord[]
  sessionWorkers: SessionWorkerRecord[]
  assignWorker: (sessionWorkerId: string, workerId: string | null) => Promise<void>
}) {
  if (!latestEvent || !latestEvent.detections.length) {
    return (
      <Box className="insightPanel emptyInsight">
        <Typography variant="h6">Detection Insights</Typography>
        <Typography color="text.secondary">No detection event received yet.</Typography>
      </Box>
    )
  }

  return (
    <Box className="insightPanel">
      <Box className="insightHeader">
        <Box>
          <Typography variant="h6">Detection Insights</Typography>
          <Typography variant="body2" color="text.secondary">
            {latestEvent.cam_id} - frame {latestEvent.frame_id} - {latestEvent.detections.length} worker(s)
          </Typography>
        </Box>
        <Chip size="small" color="success" label="Live" />
      </Box>

      <Box className="workerList">
        {latestEvent.detections.map((detection) => (
          <WorkerInsightCard
            key={`${detection.worker_id}-${detection.tracking_id}`}
            detection={detection}
            workers={workers}
            sessionWorker={sessionWorkers.find((row) => row.edge_worker_id === detection.worker_id)}
            assignWorker={assignWorker}
          />
        ))}
      </Box>

      <Divider />
      <Typography variant="subtitle2">Recent Events</Typography>
      <Box className="eventList">
        {events.slice(0, 8).map((event) => (
          <Box className="eventItem" key={`${event.frame_id}-${event.timestamp}`}>
            <Box>
              <Typography sx={{ fontWeight: 700 }}>Frame {event.frame_id}</Typography>
              <Typography variant="caption" color="text.secondary">
                {event.detections.length} worker(s) - {formatTimestamp(event.timestamp)}
              </Typography>
            </Box>
            <Chip size="small" label={event.cam_id} />
          </Box>
        ))}
      </Box>
    </Box>
  )
}

function WorkerInsightCard({
  detection,
  workers,
  sessionWorker,
  assignWorker,
}: {
  detection: LiveDetection
  workers: WorkerRecord[]
  sessionWorker?: SessionWorkerRecord
  assignWorker: (sessionWorkerId: string, workerId: string | null) => Promise<void>
}) {
  const rula = readRiskScore(detection.metadata?.rula)
  const reba = readRiskScore(detection.metadata?.reba)
  const angles = readAngles(detection.metadata?.angles)
  const assessmentQuality = readAssessmentQuality(detection.metadata?.assessment_quality)
  const identityStatus = readMetadataString(detection.metadata?.identity_status)
  const keypointCount = detection.keypoints?.points.length ?? 0
  const bbox = detection.bbox.map((value) => Math.round(value))
  return (
    <Box className="workerCard">
      <Box className="workerCardHeader">
        <Box>
          <Typography variant="caption" color="text.secondary">
            {sessionWorker?.worker_name ? 'Confirmed Worker' : 'Edge Worker'}
          </Typography>
          <Typography sx={{ fontWeight: 700 }}>
            {sessionWorker?.worker_name ?? detection.worker_id}
          </Typography>
          {sessionWorker?.employee_number ? (
            <Typography variant="caption" color="text.secondary">
              {sessionWorker.employee_number} - {detection.worker_id}
            </Typography>
          ) : null}
        </Box>
        <Chip size="small" label={`Track #${detection.tracking_id}`} />
      </Box>

      <TextField
        select
        size="small"
        label="Assign worker"
        value={sessionWorker?.worker_id ?? ''}
        disabled={!sessionWorker}
        onChange={(event) => {
          if (sessionWorker) {
            void assignWorker(sessionWorker.id, event.target.value || null)
          }
        }}
      >
        <MenuItem value="">Unconfirmed</MenuItem>
        {workers.filter((worker) => worker.is_active).map((worker) => (
          <MenuItem key={worker.id} value={worker.id}>
            {worker.name}{worker.employee_number ? ` (${worker.employee_number})` : ''}
          </MenuItem>
        ))}
      </TextField>

      <Box className="workerScoreRow">
        <Chip size="small" label={`RULA ${rula.score} ${rula.risk}`} color={riskColor(rula.risk)} />
        <Chip size="small" label={`REBA ${reba.score} ${reba.risk}`} color={riskColor(reba.risk)} />
        <Chip size="small" variant="outlined" label={`Pose ${assessmentQuality}`} />
        <Chip size="small" variant="outlined" label={`Identity ${identityStatus}`} />
      </Box>

      <Box className="detailGrid">
        <InsightValue label="Confidence" value={formatPercent(detection.confidence)} />
        <InsightValue label="Re-ID" value={formatPercent(detection.reid_confidence)} />
        <InsightValue label="Keypoints" value={String(keypointCount)} />
        <InsightValue label="BBox" value={bbox.length ? bbox.join(', ') : '-'} />
      </Box>

      <Box className="angleGrid">
        <InsightValue label="Neck" value={formatAngle(angles.neck)} />
        <InsightValue label="Trunk" value={formatAngle(angles.trunk)} />
        <InsightValue label="Upper Arm" value={formatAngle(maxAngle(angles.ua_l, angles.ua_r))} />
        <InsightValue label="Elbow" value={formatAngle(maxAngle(angles.la_l, angles.la_r))} />
        <InsightValue label="Knee" value={formatAngle(maxAngle(angles.leg_l, angles.leg_r))} />
      </Box>
    </Box>
  )
}

function InsightValue({ label, value }: { label: string; value: string }) {
  return (
    <Box className="insightValue">
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography sx={{ fontWeight: 700 }}>{value}</Typography>
    </Box>
  )
}

function readRiskScore(value: unknown): { score: string; risk: string } {
  if (typeof value !== 'object' || value === null) {
    return { score: '-', risk: 'unknown' }
  }
  const record = value as Record<string, unknown>
  return {
    score: typeof record.score === 'number' || typeof record.score === 'string' ? String(record.score) : '-',
    risk: typeof record.risk === 'string' ? record.risk : 'unknown',
  }
}

function readAngles(value: unknown): Record<string, number> {
  if (typeof value !== 'object' || value === null) return {}
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .filter((entry): entry is [string, number] => typeof entry[1] === 'number'),
  )
}

function readAssessmentQuality(value: unknown): string {
  if (typeof value !== 'object' || value === null) return 'unknown'
  const status = (value as Record<string, unknown>).status
  return typeof status === 'string' ? status : 'unknown'
}

function readMetadataString(value: unknown): string {
  return typeof value === 'string' && value ? value : 'unknown'
}

function riskColor(risk: string): 'success' | 'warning' | 'error' | 'default' {
  const normalized = risk.toLowerCase()
  if (['acceptable', 'low', 'negligible'].includes(normalized)) return 'success'
  if (normalized.includes('further') || normalized.includes('medium') || normalized.includes('moderate')) return 'warning'
  if (normalized.includes('high') || normalized.includes('soon') || normalized.includes('immediately')) return 'error'
  return 'default'
}

function maxAngle(left?: number, right?: number): number | undefined {
  const values = [left, right].filter((value): value is number => typeof value === 'number')
  return values.length ? Math.max(...values) : undefined
}

function formatAngle(value?: number): string {
  return typeof value === 'number' ? `${Math.round(value)} deg` : '-'
}

function formatPercent(value?: number): string {
  if (value === undefined || value === null) return '-'
  return `${Math.round(value * 100)}%`
}

function formatTimestamp(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function findStreamCamera(
  activeSession: SessionRecord | undefined,
  cameraNodes: CameraNode[],
  selectedCamIds: string[],
): CameraNode | undefined {
  const sessionCamIds = activeSession?.metadata_json.camera_node_ids ?? []
  const preferredIds = sessionCamIds.length ? sessionCamIds : selectedCamIds
  return preferredIds
    .map((camId) => cameraNodes.find((node) => node.cam_id === camId))
    .find((node): node is CameraNode => Boolean(node?.metadata_json.edge_base_url))
}

function buildStreamUrl(camera: CameraNode, fps: number, overlay: boolean): string | null {
  const edgeBaseUrl = camera.metadata_json.edge_base_url
  if (typeof edgeBaseUrl !== 'string') return null
  const url = new URL('/stream/mjpeg', edgeBaseUrl)
  url.searchParams.set('width', '640')
  url.searchParams.set('height', '360')
  url.searchParams.set('fps', String(fps))
  url.searchParams.set('quality', '65')
  url.searchParams.set('overlay', overlay ? 'true' : 'false')
  return url.toString()
}

function WorkerRegistry({
  token,
  workers,
  refreshData,
}: {
  token: string
  workers: WorkerRecord[]
  refreshData: () => Promise<void>
}) {
  const [name, setName] = useState('')
  const [employeeNumber, setEmployeeNumber] = useState('')
  const [department, setDepartment] = useState('')
  const [position, setPosition] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  async function createWorker() {
    if (!name.trim()) {
      setMessage('Worker name is required.')
      return
    }
    setLoading(true)
    setMessage(null)
    try {
      await apiRequest<WorkerRecord>(
        '/api/v1/workers',
        {
          method: 'POST',
          body: JSON.stringify({
            name: name.trim(),
            employee_number: employeeNumber.trim() || null,
            department: department.trim() || null,
            position: position.trim() || null,
          }),
        },
        token,
      )
      setName('')
      setEmployeeNumber('')
      setDepartment('')
      setPosition('')
      await refreshData()
      setMessage('Worker added.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to add worker.')
    } finally {
      setLoading(false)
    }
  }

  async function deactivateWorker(workerId: string) {
    setLoading(true)
    try {
      await apiRequest(`/api/v1/workers/${workerId}`, { method: 'DELETE' }, token)
      await refreshData()
      setMessage('Worker deactivated.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to deactivate worker.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Stack spacing={3}>
      <PageTitle title="Workers" action={<Button onClick={refreshData}>Refresh</Button>} />
      <Paper className="panel" elevation={0}>
        <Typography variant="h6">Add Worker</Typography>
        <Divider sx={{ my: 2 }} />
        <Box className="workerForm">
          <TextField label="Name" value={name} onChange={(event) => setName(event.target.value)} />
          <TextField label="Employee number" value={employeeNumber} onChange={(event) => setEmployeeNumber(event.target.value)} />
          <TextField label="Department" value={department} onChange={(event) => setDepartment(event.target.value)} />
          <TextField label="Position" value={position} onChange={(event) => setPosition(event.target.value)} />
          <Button variant="contained" disabled={loading} onClick={createWorker}>Add Worker</Button>
        </Box>
        {loading ? <LinearProgress sx={{ mt: 2 }} /> : null}
        {message ? <Alert severity="info" sx={{ mt: 2 }}>{message}</Alert> : null}
      </Paper>
      <Paper className="panel" elevation={0}>
        <Typography variant="h6">Worker Registry</Typography>
        <Divider sx={{ my: 2 }} />
        {workers.length ? workers.map((worker) => (
          <Box key={worker.id} className="workerRegistryEntry">
            <Box className="rowLine rowFlex workerRegistryRow">
              <Box sx={{ flex: 1, minWidth: 220 }}>
                <Typography sx={{ fontWeight: 700 }}>{worker.name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {[worker.employee_number, worker.department, worker.position].filter(Boolean).join(' - ') || 'No additional details'}
                </Typography>
              </Box>
              <Chip size="small" label={worker.is_active ? 'active' : 'inactive'} color={worker.is_active ? 'success' : 'default'} />
              {worker.is_active ? (
                <Button
                  color="error"
                  size="small"
                  startIcon={<Trash2 size={16} />}
                  disabled={loading}
                  onClick={() => void deactivateWorker(worker.id)}
                >
                  Deactivate
                </Button>
              ) : null}
            </Box>
            <WorkerEnrollmentGallery token={token} worker={worker} />
          </Box>
        )) : (
          <Typography color="text.secondary">No workers registered.</Typography>
        )}
      </Paper>
    </Stack>
  )
}

const enrollmentViews = [
  { key: 'front', label: 'Front' },
  { key: 'left', label: 'Left Side' },
  { key: 'right', label: 'Right Side' },
] as const

function WorkerEnrollmentGallery({ token, worker }: { token: string; worker: WorkerRecord }) {
  const [images, setImages] = useState<WorkerEnrollmentImage[]>([])
  const [imageUrls, setImageUrls] = useState<Record<string, string>>({})
  const [message, setMessage] = useState<string | null>(null)
  const [loadingView, setLoadingView] = useState<string | null>(null)

  const loadImages = useCallback(async () => {
    const records = await apiRequest<WorkerEnrollmentImage[]>(
      `/api/v1/workers/${worker.id}/enrollment-images`,
      {},
      token,
    )
    const nextUrls: Record<string, string> = {}
    await Promise.all(records.map(async (record) => {
      const blob = await apiBlob(record.image_url, token)
      nextUrls[record.view] = URL.createObjectURL(blob)
    }))
    setImageUrls((current) => {
      Object.values(current).forEach((url) => URL.revokeObjectURL(url))
      return nextUrls
    })
    setImages(records)
  }, [token, worker.id])

  useEffect(() => {
    void loadImages().catch(() => setMessage('Failed to load enrollment photos.'))
    return () => {
      setImageUrls((current) => {
        Object.values(current).forEach((url) => URL.revokeObjectURL(url))
        return {}
      })
    }
  }, [loadImages])

  async function upload(view: string, file: File | undefined) {
    if (!file) return
    setLoadingView(view)
    setMessage(null)
    const form = new FormData()
    form.append('file', file)
    try {
      await apiRequest(
        `/api/v1/workers/${worker.id}/enrollment-images/${view}`,
        { method: 'PUT', body: form },
        token,
      )
      await loadImages()
      setMessage(`${view} view updated.`)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Upload failed.')
    } finally {
      setLoadingView(null)
    }
  }

  async function remove(view: string) {
    setLoadingView(view)
    try {
      await apiRequest(
        `/api/v1/workers/${worker.id}/enrollment-images/${view}`,
        { method: 'DELETE' },
        token,
      )
      await loadImages()
      setMessage(`${view} view removed.`)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Delete failed.')
    } finally {
      setLoadingView(null)
    }
  }

  return (
    <Box className="enrollmentSection">
      <Box className="enrollmentHeader">
        <Box>
          <Typography sx={{ fontWeight: 700 }}>Full-body enrollment</Typography>
          <Typography variant="caption" color="text.secondary">
            Front, left, and right views with normal work PPE.
          </Typography>
        </Box>
        <Chip size="small" label={`${images.length}/3 views`} color={images.length === 3 ? 'success' : 'default'} />
      </Box>
      <Box className="enrollmentGrid">
        {enrollmentViews.map((view) => (
          <Box key={view.key} className="enrollmentView">
            <Box className="enrollmentPreview">
              {imageUrls[view.key] ? (
                <img src={imageUrls[view.key]} alt={`${worker.name} ${view.label}`} />
              ) : (
                <UserRound size={34} />
              )}
            </Box>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>{view.label}</Typography>
            <Stack direction="row" spacing={1}>
              <Button component="label" size="small" variant="outlined" disabled={loadingView === view.key}>
                {imageUrls[view.key] ? 'Replace' : 'Upload'}
                <input
                  hidden
                  type="file"
                  accept="image/jpeg,image/png"
                  onChange={(event) => {
                    void upload(view.key, event.target.files?.[0])
                    event.target.value = ''
                  }}
                />
              </Button>
              {imageUrls[view.key] ? (
                <Button color="error" size="small" disabled={loadingView === view.key} onClick={() => void remove(view.key)}>
                  Remove
                </Button>
              ) : null}
            </Stack>
          </Box>
        ))}
      </Box>
      {message ? <Typography variant="caption" color="text.secondary">{message}</Typography> : null}
    </Box>
  )
}

function SettingsPage({
  token,
  cameraNodes,
  refreshData,
}: {
  token: string
  cameraNodes: CameraNode[]
  refreshData: () => Promise<void>
}) {
  const [pairing, setPairing] = useState<PairingToken | null>(null)
  const [devices, setDevices] = useState<DiscoveredDevice[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [manualIp, setManualIp] = useState('192.168.137.199')
  const [backendReachableUrl, setBackendReachableUrl] = useState(backendUrl)
  const isElectron = Boolean(window.ergoquipt)

  async function createPairing() {
    setLoading(true)
    setMessage(null)
    try {
      const nextPairing = await apiRequest<PairingToken>(
        '/api/v1/device-pairings',
        { method: 'POST', body: JSON.stringify({}) },
        token,
      )
      setPairing(nextPairing)
      setMessage('Pairing code created. Select a discovered device and click Pair.')
    } catch (err) {
      setMessage(err instanceof Error ? `Create pairing code failed: ${err.message}` : 'Create pairing code failed.')
    } finally {
      setLoading(false)
    }
  }

  async function discoverDevices() {
    setLoading(true)
    setMessage(null)
    try {
      if (window.ergoquipt?.discoverDevices) {
        const discovered = await window.ergoquipt.discoverDevices()
        setDevices(discovered)
        setMessage(discovered.length ? `Found ${discovered.length} edge device(s).` : 'No devices found on LAN scan.')
      } else {
        await probeManualIp()
      }
    } finally {
      setLoading(false)
    }
  }

  async function probeManualIp() {
    setLoading(true)
    setMessage(null)
    const baseUrl = manualIp.startsWith('http') ? manualIp : `http://${manualIp}:8765`
    try {
      const response = await fetch(`${baseUrl}/pairing/info`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const info = await response.json()
      if (info.service !== 'ergoquipt-edge') {
        throw new Error('Not an ErgoQuipt edge device')
      }
      const parsedUrl = new URL(baseUrl)
      const device = {
        cam_id: info.cam_id,
        hostname: info.hostname,
        address: parsedUrl.hostname,
        port: Number(parsedUrl.port || 8765),
        status: info.status,
        paired: info.paired,
        baseUrl,
      }
      setDevices([device])
      setMessage(`Found ${info.hostname} at ${baseUrl}.`)
      if (window.ergoquipt?.backendUrlForDevice) {
        const nextBackendUrl = await window.ergoquipt.backendUrlForDevice({
          baseUrl,
          backendUrl,
        })
        setBackendReachableUrl(nextBackendUrl)
      } else {
        setBackendReachableUrl(inferBackendUrlFromEdge(baseUrl))
      }
    } catch (err) {
      setDevices([])
      setMessage(err instanceof Error ? `Manual probe failed: ${err.message}` : 'Manual probe failed.')
    } finally {
      setLoading(false)
    }
  }

  async function pairDevice(device: DiscoveredDevice) {
    if (!pairing) return
    setLoading(true)
    setMessage(null)
    try {
      const result = window.ergoquipt?.pairDevice
        ? await window.ergoquipt.pairDevice({
            baseUrl: device.baseUrl,
            pairingCode: pairing.pairing_code,
            backendUrl: backendReachableUrl,
          })
        : await pairDeviceFromRenderer(device.baseUrl, pairing.pairing_code, backendReachableUrl)
      setMessage(`Paired ${result?.cam_id ?? device.cam_id}`)
      await attachEdgeBaseUrl(result?.cam_id ?? device.cam_id, device.baseUrl)
      setPairing(null)
      await probeDevice(device.baseUrl)
      await refreshData()
    } catch (err) {
      setMessage(err instanceof Error ? `Pairing failed: ${err.message}` : 'Pairing failed.')
    } finally {
      setLoading(false)
    }
  }

  async function attachEdgeBaseUrl(camId: string, edgeBaseUrl: string) {
    const cameraNodes = await apiRequest<CameraNode[]>('/api/v1/camera-nodes', {}, token)
    const camera = cameraNodes.find((node) => node.cam_id === camId)
    if (!camera) return
    await apiRequest<CameraNode>(
      `/api/v1/camera-nodes/${camera.id}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ edge_base_url: edgeBaseUrl }),
      },
      token,
    )
  }

  async function probeDevice(baseUrl: string) {
    const response = await fetch(`${baseUrl}/pairing/info`)
    if (!response.ok) {
      return
    }
    const info = await response.json()
    setDevices((current) =>
      current.map((device) =>
        device.baseUrl === baseUrl
          ? {
              ...device,
              status: info.status,
              paired: info.paired,
            }
          : device,
      ),
    )
  }

  return (
    <Stack spacing={3}>
      <PageTitle title="Devices" action={<Button onClick={refreshData}>Refresh</Button>} />
      <Paper className="panel" elevation={0}>
        <Typography variant="h6">Add Edge Camera</Typography>
        <Box className="pairingSteps" sx={{ my: 2 }}>
          <Chip size="small" color={devices.length ? 'success' : 'default'} label="1. Scan or probe Raspberry Pi" />
          <Chip size="small" color={pairing ? 'success' : 'default'} label="2. Create pairing code" />
          <Chip size="small" color={cameraNodes.length ? 'success' : 'default'} label="3. Pair camera node" />
        </Box>
        {!isElectron ? (
          <Alert severity="warning" sx={{ mb: 2 }}>
            Electron bridge is not available, so automatic LAN scan cannot run here. Manual IP probe and pairing still work.
          </Alert>
        ) : null}
        <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap', rowGap: 1 }}>
          <Button variant="contained" startIcon={<RadioReceiver size={18} />} onClick={discoverDevices}>
            Scan LAN
          </Button>
          <Button variant="outlined" startIcon={<ShieldCheck size={18} />} onClick={createPairing}>
            Create pairing code
          </Button>
          <TextField
            size="small"
            label="Manual edge IP"
            value={manualIp}
            onChange={(event) => setManualIp(event.target.value)}
          />
          <Button variant="outlined" onClick={probeManualIp}>
            Probe IP
          </Button>
        </Stack>
        <TextField
          sx={{ mt: 2, maxWidth: 520 }}
          fullWidth
          size="small"
          label="Backend URL sent to Raspberry Pi"
          value={backendReachableUrl}
          onChange={(event) => setBackendReachableUrl(event.target.value)}
        />
        {loading ? <LinearProgress sx={{ mt: 2 }} /> : null}
        {pairing ? (
          <Alert severity="success" sx={{ mt: 2 }}>
            Pairing code: <strong>{pairing.pairing_code}</strong>
          </Alert>
        ) : null}
        {message ? (
          <Alert severity="info" sx={{ mt: 2 }}>
            {message}
          </Alert>
        ) : null}
      </Paper>
      <DeviceTable cameraNodes={cameraNodes} token={token} refreshData={refreshData} editable />
      <Paper className="panel" elevation={0}>
        <Typography variant="h6">Discovered Devices</Typography>
        <Divider sx={{ my: 2 }} />
        {devices.length ? (
          devices.map((device) => (
            <Box key={`${device.address}:${device.port}`} className="rowLine rowFlex">
              <Typography sx={{ minWidth: 160 }}>{device.hostname}</Typography>
              <Chip size="small" label={device.cam_id} />
              <Chip size="small" label={device.address} />
              <Chip size="small" label={device.status} />
              <Chip size="small" label={device.paired ? 'paired' : 'unpaired'} color={device.paired ? 'success' : 'default'} />
              <Button size="small" variant="contained" disabled={!pairing || loading} onClick={() => pairDevice(device)}>
                {pairing ? 'Pair' : 'Create code first'}
              </Button>
            </Box>
          ))
        ) : (
          <Typography color="text.secondary">No edge devices listed yet. Use Scan LAN or Probe IP.</Typography>
        )}
      </Paper>
    </Stack>
  )
}

async function pairDeviceFromRenderer(baseUrl: string, pairingCode: string, backendReachableUrl: string) {
  const response = await fetch(`${baseUrl}/pairing/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      pairing_code: pairingCode,
      backend_url: backendReachableUrl,
      edge_base_url: baseUrl,
    }),
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `HTTP ${response.status}`)
  }

  return (await response.json()) as { status: string; cam_id: string }
}

function inferBackendUrlFromEdge(edgeBaseUrl: string): string {
  try {
    const edge = new URL(edgeBaseUrl)
    const parts = edge.hostname.split('.')
    if (parts.length === 4) {
      return `http://${parts[0]}.${parts[1]}.${parts[2]}.1:8000`
    }
  } catch {
    return backendUrl
  }
  return backendUrl
}

function SessionList({ title, sessions }: { title: string; sessions: SessionRecord[] }) {
  return (
    <Paper className="panel" elevation={0}>
      <Typography variant="h6">{title}</Typography>
      <Divider sx={{ my: 2 }} />
      {sessions.length ? (
        sessions.map((session) => (
          <Box key={session.id} className="rowLine rowFlex">
            <Typography sx={{ minWidth: 220 }}>{session.session_code}</Typography>
            <Chip size="small" label={session.status} />
            <Typography color="text.secondary">{session.notes ?? ''}</Typography>
          </Box>
        ))
      ) : (
        <Typography color="text.secondary">No sessions.</Typography>
      )}
    </Paper>
  )
}

function DeviceTable({
  cameraNodes,
  token,
  refreshData,
  editable = false,
}: {
  cameraNodes: CameraNode[]
  token?: string
  refreshData?: () => Promise<void>
  editable?: boolean
}) {
  return (
    <Paper className="panel" elevation={0}>
      <Typography variant="h6">Camera Nodes</Typography>
      <Divider sx={{ my: 2 }} />
      {cameraNodes.length ? (
        cameraNodes.map((node) => (
          <DeviceRow
            key={node.id}
            node={node}
            token={token}
            refreshData={refreshData}
            editable={editable}
          />
        ))
      ) : (
        <Typography color="text.secondary">No paired camera nodes.</Typography>
      )}
    </Paper>
  )
}

function DeviceRow({
  node,
  token,
  refreshData,
  editable,
}: {
  node: CameraNode
  token?: string
  refreshData?: () => Promise<void>
  editable: boolean
}) {
  const currentName = node.metadata_json.display_name ?? node.cam_id
  const [isEditing, setIsEditing] = useState(false)
  const [displayName, setDisplayName] = useState(currentName)
  const [message, setMessage] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setDisplayName(currentName)
  }, [currentName])

  async function renameDevice() {
    if (!token || !displayName.trim()) return
    setSaving(true)
    setMessage(null)
    try {
      await apiRequest<CameraNode>(
        `/api/v1/camera-nodes/${node.id}`,
        {
          method: 'PATCH',
          body: JSON.stringify({ display_name: displayName.trim() }),
        },
        token,
      )
      setIsEditing(false)
      await refreshData?.()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Rename failed.')
    } finally {
      setSaving(false)
    }
  }

  async function removeDevice() {
    if (!token) return
    const confirmed = window.confirm(`Remove ${currentName} from this account?`)
    if (!confirmed) return
    setSaving(true)
    setMessage(null)
    try {
      await apiRequest<void>(`/api/v1/camera-nodes/${node.id}`, { method: 'DELETE' }, token)
      await refreshData?.()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Remove failed.')
    } finally {
      setSaving(false)
    }
  }

  function cancelRename() {
    setDisplayName(currentName)
    setIsEditing(false)
    setMessage(null)
  }

  return (
    <Box className="rowLine">
      <Box className="rowFlex deviceRow">
        <Camera size={18} />
        <Box className="deviceName">
          {isEditing ? (
            <TextField
              size="small"
              label="Device name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              disabled={saving}
            />
          ) : (
            <>
              <Typography sx={{ fontWeight: 700 }}>{currentName}</Typography>
              <Typography variant="caption" color="text.secondary">
                Technical ID: {node.cam_id}
              </Typography>
            </>
          )}
        </Box>
        <Typography sx={{ minWidth: 180 }}>{node.hostname ?? '-'}</Typography>
        <Chip size="small" label={node.status} color={node.status === 'online' ? 'success' : 'default'} />
        {editable ? (
          <Stack direction="row" spacing={1} sx={{ ml: 'auto' }}>
            {isEditing ? (
              <>
                <Button size="small" startIcon={<Save size={16} />} disabled={saving} onClick={renameDevice}>
                  Save
                </Button>
                <Button size="small" startIcon={<X size={16} />} disabled={saving} onClick={cancelRename}>
                  Cancel
                </Button>
              </>
            ) : (
              <>
                <Button size="small" startIcon={<Pencil size={16} />} disabled={saving} onClick={() => setIsEditing(true)}>
                  Rename
                </Button>
                <Button size="small" color="error" startIcon={<Trash2 size={16} />} disabled={saving} onClick={removeDevice}>
                  Remove
                </Button>
              </>
            )}
          </Stack>
        ) : null}
      </Box>
      {message ? (
        <Typography variant="caption" color="error">
          {message}
        </Typography>
      ) : null}
    </Box>
  )
}

function Placeholder({ title, icon: Icon }: { title: string; icon: typeof FileText }) {
  return (
    <Paper className="panel emptyState" elevation={0}>
      <Icon size={28} />
      <Typography variant="h6">{title}</Typography>
      <Typography color="text.secondary">Pending backend workflow.</Typography>
    </Paper>
  )
}

function Metric({ label, value, icon: Icon }: { label: string; value: number; icon: typeof Camera }) {
  return (
    <Paper className="metric" elevation={0}>
      <Icon size={22} />
      <Box>
        <Typography variant="h5">{value}</Typography>
        <Typography color="text.secondary">{label}</Typography>
      </Box>
    </Paper>
  )
}

function PageTitle({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <Box className="pageTitle">
      <Typography variant="h5">{title}</Typography>
      {action}
    </Box>
  )
}

function StatusChip({ status }: { status: string }) {
  const color = useMemo(() => {
    if (status === 'online') return 'success'
    if (status === 'checking') return 'warning'
    return 'default'
  }, [status])
  return <Chip size="small" label={status} color={color} variant={status === 'offline' ? 'outlined' : 'filled'} />
}

export default App
