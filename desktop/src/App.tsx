/* eslint-disable react-hooks/set-state-in-effect */
import {
  Alert,
  AppBar,
  Box,
  Button,
  Checkbox,
  Chip,
  CssBaseline,
  Divider,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Drawer,
  FormControlLabel,
  IconButton,
  InputAdornment,
  LinearProgress,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Paper,
  Stack,
  Switch,
  Tab,
  Tabs,
  TextField,
  ThemeProvider,
  Toolbar,
  Tooltip,
  Typography,
  createTheme,
} from '@mui/material'
import {
  Activity,
  BarChart3,
  Camera,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  Play,
  Plus,
  Square,
  ClipboardCheck,
  FileText,
  FileArchive,
  FileSpreadsheet,
  History,
  Download,
  Eye,
  EyeOff,
  LayoutDashboard,
  LogOut,
  Pencil,
  RadioReceiver,
  RefreshCw,
  RotateCcw,
  Save,
  Settings,
  ShieldCheck,
  Trash2,
  UserRound,
  Wifi,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import './App.css'
import ergosightLogo from './assets/ergosight-logo.png'
import { CameraPreview } from './CameraPreview'
import { retainWorkerInsights, insightIsLive } from './liveInsights'
import type { LiveDetection, LiveDetectionEvent, WorkerInsightSnapshot } from './liveInsights'
import {
  apiBlob,
  apiRequest,
  liveWebSocketUrl,
} from './api'
import type {
  AuthTokens,
  CameraNode,
  ErgonomicEventRecord,
  EventDetailRecord,
  EventReviewRecord,
  ExposureOverviewRecord,
  PairingToken,
  ReportRecord,
  SessionRecord,
  SessionExposureSummaryRecord,
  SessionWorkerRecord,
  WorkerEnrollmentImage,
  WorkerRecord,
} from './api'
import type { DiscoveredDevice, EdgeNetworkStatus, WifiNetwork } from './types'

const drawerWidth = 248
const backendUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const tokenStorageKey = 'ergoquipt.tokens'

function readStoredTokens(): AuthTokens | null {
  const raw = localStorage.getItem(tokenStorageKey) ?? sessionStorage.getItem(tokenStorageKey)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthTokens
  } catch {
    localStorage.removeItem(tokenStorageKey)
    sessionStorage.removeItem(tokenStorageKey)
    return null
  }
}

function storeTokens(tokens: AuthTokens, persistent: boolean) {
  localStorage.removeItem(tokenStorageKey)
  sessionStorage.removeItem(tokenStorageKey)
  const storage = persistent ? localStorage : sessionStorage
  storage.setItem(tokenStorageKey, JSON.stringify(tokens))
}

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
    primary: { main: '#0077a8' },
    secondary: { main: '#394b59' },
    background: { default: '#f4f7f9', paper: '#ffffff' },
    success: { main: '#1f7a55' },
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
  components: {
    MuiDrawer: {
      styleOverrides: {
        paper: { backgroundColor: '#0b1218', color: '#eef7fb', borderRight: 0 },
      },
    },
    MuiListItemIcon: {
      styleOverrides: { root: { minWidth: 42, color: '#8fa6b4' } },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          margin: '3px 10px',
          borderRadius: 6,
          '&.Mui-selected': {
            color: '#ffffff',
            backgroundColor: 'rgba(0, 185, 255, 0.18)',
            '& .MuiListItemIcon-root': { color: '#00b9ff' },
          },
          '&.Mui-selected:hover': { backgroundColor: 'rgba(0, 185, 255, 0.24)' },
        },
      },
    },
  },
})

function App() {
  const [tokens, setTokens] = useState<AuthTokens | null>(() => {
    return readStoredTokens()
  })
  const [keepLoggedIn, setKeepLoggedIn] = useState(() => Boolean(localStorage.getItem(tokenStorageKey)))
  const [authReady, setAuthReady] = useState(tokens === null)
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
    if (!token || !authReady) return
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
  }, [authReady, token])

  useEffect(() => {
    if (!token || !authReady) return
    const active = sessions.filter((session) => ['running', 'preparing'].includes(session.status))
    const heartbeat = () => active.forEach((session) => {
      void apiRequest(`/api/v1/sessions/${session.id}/operator-heartbeat`, { method: 'POST' }, token).catch(() => {})
    })
    heartbeat()
    const timer = window.setInterval(heartbeat, 5000)
    return () => window.clearInterval(timer)
  }, [authReady, token, sessions])

  useEffect(() => {
    if (!tokens || authReady) return
    let cancelled = false
    async function restoreAuthentication() {
      try {
        await apiRequest('/api/v1/auth/me', {}, tokens?.access_token)
        if (!cancelled) setAuthReady(true)
      } catch {
        try {
          const refreshed = await apiRequest<AuthTokens>('/api/v1/auth/refresh', {
            method: 'POST',
            body: JSON.stringify({ refresh_token: tokens?.refresh_token }),
          })
          if (!cancelled) {
            storeTokens(refreshed, keepLoggedIn)
            setTokens(refreshed)
            setAuthReady(true)
          }
        } catch {
          if (!cancelled) logout()
        }
      }
    }
    void restoreAuthentication()
    return () => {
      cancelled = true
    }
  }, [authReady, keepLoggedIn, tokens])

  useEffect(() => {
    if (token && authReady) {
      void refreshData()
      const timer = window.setInterval(() => void refreshData(), 5000)
      return () => window.clearInterval(timer)
    }
  }, [authReady, token, refreshData])

  async function refreshBackendStatus() {
    try {
      await apiRequest<{ status: string }>('/health')
      setBackendStatus('online')
    } catch {
      setBackendStatus('offline')
    }
  }

  function handleLogin(nextTokens: AuthTokens, persistent: boolean) {
    storeTokens(nextTokens, persistent)
    setKeepLoggedIn(persistent)
    setTokens(nextTokens)
    setAuthReady(true)
  }

  function logout() {
    localStorage.removeItem(tokenStorageKey)
    sessionStorage.removeItem(tokenStorageKey)
    setTokens(null)
    setAuthReady(true)
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

  if (!authReady) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box className="loginPage"><Box sx={{ width: 280 }}><LinearProgress /></Box></Box>
      </ThemeProvider>
    )
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box className="appShell">
        <AppBar position="fixed" elevation={0} className="topBar">
          <Toolbar>
            <ShieldCheck size={22} color="#0077a8" />
            <Typography variant="h6" sx={{ ml: 1, flexGrow: 1 }}>
              ERGoSIGHT
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
            <img className="drawerLogo" src={ergosightLogo} alt="ERGoSIGHT" />
            <Typography variant="body2">HSE Operator Console</Typography>
          </Box>
          <List>
            {navItems.map((item) => {
              const Icon = item.icon
              return (
                <ListItemButton
                  key={item.key}
                  selected={activePage === item.key}
                  onClick={() => { setActivePage(item.key); window.scrollTo(0, 0) }}
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
  onLogin: (tokens: AuthTokens, keepLoggedIn: boolean) => void
  backendStatus: string
}) {
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [keepLoggedIn, setKeepLoggedIn] = useState(false)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (mode === 'register' && password !== confirmPassword) return
    setLoading(true)
    setError(null)
    try {
      if (mode === 'register') {
        await apiRequest('/api/v1/auth/register', {
          method: 'POST',
          body: JSON.stringify({ email, username, full_name: fullName, password }),
        })
      }
      const tokens = await apiRequest<AuthTokens>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      onLogin(tokens, keepLoggedIn)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  const passwordsMismatch = mode === 'register' && confirmPassword.length > 0 && password !== confirmPassword

  function switchMode() {
    setMode(mode === 'login' ? 'register' : 'login')
    setError(null)
    setConfirmPassword('')
  }

  const passwordAdornment = (
    <InputAdornment position="end">
      <IconButton
        edge="end"
        aria-label={showPassword ? 'Hide password' : 'Show password'}
        onClick={() => setShowPassword((visible) => !visible)}
      >
        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
      </IconButton>
    </InputAdornment>
  )

  return (
    <Box className="loginPage">
      <Box className="loginShell">
        <img className="loginLogo" src={ergosightLogo} alt="ERGoSIGHT AI-Based Ergonomic Monitoring System" />
        <Paper className="loginPanel" elevation={0}>
          <Stack spacing={3}>
          <Typography variant="h5">Operator Sign In</Typography>
          <Stack direction="row" spacing={1}>
            <StatusChip status={backendStatus} />
            <Chip size="small" label="JWT secured" color="primary" variant="outlined" />
          </Stack>
          {error ? <Alert severity="error">{error}</Alert> : null}
          <Box component="form" onSubmit={submit}>
            <Stack spacing={2}>
              <TextField
                label="Email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              {mode === 'register' ? (
                <>
                  <TextField label="Username" required autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
                  <TextField label="Full Name" required autoComplete="name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
                </>
              ) : null}
              <TextField
                label="Password"
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                slotProps={{ input: { endAdornment: passwordAdornment } }}
              />
              {mode === 'register' ? (
                <TextField
                  label="Confirm Password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  error={passwordsMismatch}
                  helperText={passwordsMismatch ? 'Passwords do not match' : confirmPassword && password === confirmPassword ? 'Passwords match' : ' '}
                  slotProps={{ input: { endAdornment: passwordAdornment } }}
                />
              ) : null}
              <FormControlLabel
                control={<Checkbox checked={keepLoggedIn} onChange={(event) => setKeepLoggedIn(event.target.checked)} />}
                label="Keep me logged in"
              />
              {loading ? <LinearProgress /> : null}
              <Button
                type="submit"
                variant="contained"
                disabled={loading || (mode === 'register' && (!username.trim() || !fullName.trim() || !confirmPassword || passwordsMismatch))}
              >
                {mode === 'login' ? 'Login' : 'Create User Account'}
              </Button>
              <Button onClick={switchMode}>
                {mode === 'login' ? 'Sign Up' : 'Back to Login'}
              </Button>
            </Stack>
          </Box>
          </Stack>
        </Paper>
      </Box>
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
    return <SessionList title="History" sessions={sessions} token={token} refreshData={refreshData} />
  }
  if (activePage === 'workers') {
    return <WorkerRegistry token={token} workers={workers} refreshData={refreshData} />
  }
  if (activePage === 'reports') {
    return <ReportsPage token={token} sessions={sessions} />
  }
  if (activePage === 'review') {
    return <SessionReview token={token} sessions={sessions} workers={workers} refreshData={refreshData} />
  }
  return (
    <Dashboard
      token={token}
      cameraNodes={cameraNodes}
      sessions={sessions}
      refreshData={refreshData}
      openDevices={() => setActivePage('settings')}
    />
  )
}

function Dashboard({
  token,
  cameraNodes,
  sessions,
  refreshData,
  openDevices,
}: {
  token: string
  cameraNodes: CameraNode[]
  sessions: SessionRecord[]
  refreshData: () => Promise<void>
  openDevices: () => void
}) {
  const running = sessions.filter((session) => session.status === 'running').length
  const paired = cameraNodes.length
  const [analyticsDays, setAnalyticsDays] = useState(7)
  const [analytics, setAnalytics] = useState<ExposureOverviewRecord | null>(null)
  const [analyticsLoading, setAnalyticsLoading] = useState(false)
  const [analyticsError, setAnalyticsError] = useState<string | null>(null)

  const loadAnalytics = useCallback(async () => {
    setAnalyticsLoading(true)
    setAnalyticsError(null)
    try {
      const overview = await apiRequest<ExposureOverviewRecord>(
        `/api/v1/analytics/overview?days=${analyticsDays}`,
        {},
        token,
      )
      setAnalytics(overview)
    } catch (err) {
      setAnalyticsError(err instanceof Error ? err.message : 'Failed to load exposure analytics.')
    } finally {
      setAnalyticsLoading(false)
    }
  }, [analyticsDays, token])

  useEffect(() => {
    void loadAnalytics()
  }, [loadAnalytics])

  async function refreshDashboard() {
    await Promise.all([refreshData(), loadAnalytics()])
  }

  const maxDailyExposure = Math.max(
    1,
    ...(analytics?.daily_trend.map((day) => day.high_risk_duration_ms) ?? []),
  )

  return (
    <Stack spacing={3}>
      <PageTitle
        title="Dashboard"
        action={
          <Stack direction="row" spacing={1}>
            <Button variant="contained" startIcon={<Camera size={18} />} onClick={openDevices}>
              Add Edge Camera
            </Button>
            <Button onClick={refreshDashboard}>Refresh</Button>
          </Stack>
        }
      />
      <Box className="metricGrid">
        <Metric label="Paired Cameras" value={paired} icon={Camera} />
        <Metric label="Running Sessions" value={running} icon={Activity} />
        <Metric label="Review Queue" value={sessions.filter((s) => s.status === 'review_pending').length} icon={ClipboardCheck} />
        <Metric label="Reports" value={0} icon={BarChart3} />
      </Box>
      <Box className="analyticsTitleBar">
        <Box>
          <Typography variant="h6">Exposure Analytics</Typography>
          <Typography variant="body2" color="text.secondary">
            {analytics?.session_count ?? 0} sessions in the selected period
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
          <Chip size="small" label={`Avg RULA ${analytics?.rula.average ?? '-'}`} />
          <Chip size="small" label={`Peak RULA ${analytics?.rula.peak ?? '-'}`} />
          <Chip size="small" label={`Avg REBA ${analytics?.reba.average ?? '-'}`} />
          <Chip size="small" label={`Peak REBA ${analytics?.reba.peak ?? '-'}`} />
          <TextField
            select
            size="small"
            label="Period"
            value={analyticsDays}
            onChange={(event) => setAnalyticsDays(Number(event.target.value))}
            sx={{ width: 120 }}
          >
            <MenuItem value={7}>7 days</MenuItem>
            <MenuItem value={30}>30 days</MenuItem>
            <MenuItem value={90}>90 days</MenuItem>
          </TextField>
        </Stack>
      </Box>
      {analyticsLoading ? <LinearProgress /> : null}
      {analyticsError ? <Alert severity="error">{analyticsError}</Alert> : null}
      <Box className="metricGrid">
        <Metric label="Observed Workers" value={analytics?.worker_count ?? 0} icon={UserRound} />
        <Metric label="High Risk Events" value={analytics?.high_risk_event_count ?? 0} icon={ShieldCheck} />
        <Metric label="Exposure Minutes" value={Math.round((analytics?.high_risk_duration_ms ?? 0) / 60_000)} icon={Activity} />
        <Metric label="Reviewed Assessments" value={analytics?.reviewed_assessment_count ?? 0} icon={ClipboardCheck} />
      </Box>
      <Box className="analyticsGrid">
        <Paper className="panel" elevation={0}>
          <Typography variant="h6">Highest Exposure Workers</Typography>
          <Divider sx={{ my: 2 }} />
          {analytics?.top_workers.length ? analytics.top_workers.map((worker, index) => (
            <Box key={worker.worker_key} className="analyticsRow">
              <Typography className="analyticsRank">{index + 1}</Typography>
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Typography sx={{ fontWeight: 700 }}>{worker.worker_name}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {worker.session_count} sessions - {worker.high_risk_event_count} high-risk events
                </Typography>
              </Box>
              <Box className="analyticsValue">
                <Typography sx={{ fontWeight: 700 }}>{formatDuration(worker.high_risk_duration_ms)}</Typography>
                <Typography variant="caption" color="text.secondary">R {worker.rula.peak ?? '-'} / REBA {worker.reba.peak ?? '-'}</Typography>
              </Box>
            </Box>
          )) : <Typography color="text.secondary">No worker exposure data.</Typography>}
        </Paper>
        <Paper className="panel" elevation={0}>
          <Typography variant="h6">Highest Risk Sessions</Typography>
          <Divider sx={{ my: 2 }} />
          {analytics?.top_sessions.length ? analytics.top_sessions.map((session, index) => (
            <Box key={session.session_id} className="analyticsRow">
              <Typography className="analyticsRank">{index + 1}</Typography>
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Typography sx={{ fontWeight: 700 }}>{session.notes || session.session_code}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {session.worker_count} workers - {session.high_risk_event_count} high-risk events
                </Typography>
              </Box>
              <Box className="analyticsValue">
                <Typography sx={{ fontWeight: 700 }}>{formatDuration(session.high_risk_duration_ms)}</Typography>
                <Typography variant="caption" color="text.secondary">R {session.peak_rula ?? '-'} / REBA {session.peak_reba ?? '-'}</Typography>
              </Box>
            </Box>
          )) : <Typography color="text.secondary">No session risk data.</Typography>}
        </Paper>
      </Box>
      <Paper className="panel" elevation={0}>
        <Typography variant="h6">Daily Exposure Trend</Typography>
        <Divider sx={{ my: 2 }} />
        {analytics?.daily_trend.length ? (
          <Box className="trendList">
            {analytics.daily_trend.map((day) => (
              <Box key={day.day} className="trendRow">
                <Typography variant="body2" sx={{ width: 92 }}>{formatAnalyticsDay(day.day)}</Typography>
                <Box className="trendTrack">
                  <Box className="trendBar" sx={{ width: `${Math.max(2, day.high_risk_duration_ms / maxDailyExposure * 100)}%` }} />
                </Box>
                <Typography variant="body2" sx={{ minWidth: 72, textAlign: 'right' }}>{formatDuration(day.high_risk_duration_ms)}</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ minWidth: 110 }}>
                  {day.high_risk_event_count} events
                </Typography>
              </Box>
            ))}
          </Box>
        ) : <Typography color="text.secondary">No daily exposure data.</Typography>}
      </Paper>
      <Paper className="panel" elevation={0}>
        <Typography variant="h6">Worst Posture Events</Typography>
        <Divider sx={{ my: 2 }} />
        {analytics?.worst_events.length ? analytics.worst_events.map((event) => (
          <Box key={event.event_id} className="analyticsRow">
            <ShieldCheck size={18} />
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Typography sx={{ fontWeight: 700 }}>{event.worker_name} - {event.session_code}</Typography>
              <Typography variant="caption" color="text.secondary">{formatDateTime(event.started_at)}</Typography>
            </Box>
            <Chip size="small" label={event.severity} color={severityColor(event.severity)} />
            {event.score !== null ? <Chip size="small" label={`${event.score_type?.toUpperCase()} ${event.score}`} /> : null}
            <Chip size="small" label={event.reviewed ? 'reviewed' : 'pending'} color={event.reviewed ? 'success' : 'default'} />
            <Typography variant="body2" sx={{ minWidth: 56, textAlign: 'right' }}>{formatDuration(event.duration_ms)}</Typography>
          </Box>
        )) : <Typography color="text.secondary">No high-risk posture events.</Typography>}
      </Paper>
      <DeviceTable cameraNodes={cameraNodes} />
      <SessionList title="Recent Sessions" sessions={sessions.slice(0, 5)} token={token} refreshData={refreshData} />
    </Stack>
  )
}

function formatAnalyticsDay(value: string): string {
  return new Date(`${value}T00:00:00`).toLocaleDateString([], { day: '2-digit', month: 'short' })
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
  const [insightSnapshots, setInsightSnapshots] = useState<Record<string, WorkerInsightSnapshot[]>>({})
  const [sessionWorkers, setSessionWorkers] = useState<SessionWorkerRecord[]>([])
  const [connected, setConnected] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [showStream, setShowStream] = useState(true)
  const [showOverlay, setShowOverlay] = useState(true)
  const [streamFps, setStreamFps] = useState<number | 'auto'>('auto')
  const [previewSettingsOpen, setPreviewSettingsOpen] = useState(false)
  const [streamCamId, setStreamCamId] = useState('')
  const [previewCameraChoice, setPreviewCameraChoice] = useState('session')
  const [focusedCamId, setFocusedCamId] = useState('')
  const [cameraPage, setCameraPage] = useState(0)
  const [insightsOpen, setInsightsOpen] = useState(false)
  const [inspectorWorkerId, setInspectorWorkerId] = useState('')
  const [newSessionOpen, setNewSessionOpen] = useState(false)
  const [sessionError, setSessionError] = useState(false)
  const [assigningWorkerId, setAssigningWorkerId] = useState<string | null>(null)
  const [now, setNow] = useState(() => Date.now())

  const activeSession = sessions.find((session) => session.session_code === sessionCode)
  const sessionCameraIds = activeSession?.metadata_json.camera_node_ids ?? []
  const sessionBusy = Boolean(activeSession && ['running', 'preparing', 'stopping'].includes(activeSession.status))
  const sessionCameras = cameraNodes.filter(camera => sessionCameraIds.includes(camera.cam_id))
  const previewCamera = cameraNodes.find(camera => 'camera:' + camera.id === previewCameraChoice)
  const validPreviewChoice = previewCameraChoice.startsWith('camera:') && !previewCamera ? 'session' : previewCameraChoice
  const defaultPreviewCameras = sessionCameraIds.length ? sessionCameras : cameraNodes
  const wallCameras = sessionBusy ? sessionCameras : previewCamera ? [previewCamera]
    : validPreviewChoice === 'all' ? cameraNodes : defaultPreviewCameras
  const streamCamera = wallCameras.find(camera => camera.cam_id === streamCamId) ?? wallCameras[0]
  const pageCount = Math.max(1, Math.ceil(wallCameras.length / 4))
  const currentPage = Math.min(cameraPage, pageCount - 1)
  const focusedCamera = wallCameras.find(camera => camera.cam_id === focusedCamId)
  const visibleCameras = focusedCamera ? [focusedCamera] : wallCameras.slice(currentPage * 4, currentPage * 4 + 4)
  const sessionRunning = activeSession?.status === 'running' || activeSession?.status === 'preparing'
  const sessionCamerasReady = sessionCameraIds.length > 0 && sessionCameras.length === sessionCameraIds.length && sessionCameras.every(camera => camera.status === 'online' && camera.metadata_json.health?.camera_available)
  const insightRun = activeSession?.metadata_json.edge_runs?.[streamCamera?.cam_id ?? '']
  const visibleInsightSnapshots = (insightSnapshots[streamCamera?.cam_id ?? ''] ?? []).filter(row =>
    (row.session_id === activeSession?.session_code || row.session_id === activeSession?.id) && (!insightRun || row.run_id === insightRun))
  const selectedInspectorWorker = visibleInsightSnapshots.some(row => row.detection.worker_id === inspectorWorkerId) ? inspectorWorkerId : ''
  const inspectorSnapshots = selectedInspectorWorker ? visibleInsightSnapshots.filter(row => row.detection.worker_id === selectedInspectorWorker) : visibleInsightSnapshots
  const activeWorkerCount = wallCameras.reduce((total, camera) => {
    const event = events.find(row => row.cam_id === camera.cam_id && (!activeSession?.metadata_json.edge_runs?.[camera.cam_id] || row.run_id === activeSession.metadata_json.edge_runs[camera.cam_id]))
    return total + (event && insightIsLive(event.timestamp, now, connected, sessionRunning) ? event.detections.length : 0)
  }, 0)
  const selectedCamerasReady = selectedCamIds.length > 0 && selectedCamIds.every((id) =>
    cameraNodes.some(camera => camera.cam_id === id && camera.status === 'online' && camera.metadata_json.health?.camera_available))

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    if (!sessionCode && sessions[0]) {
      setSessionCode(sessions[0].session_code)
    }
  }, [sessionCode, sessions])

  useEffect(() => {
    if (!sessionCode) return
    setInsightSnapshots({})
    setPreviewCameraChoice('session')
    setCameraPage(0)
    setFocusedCamId('')
    setInsightsOpen(false)
    setInspectorWorkerId('')
    let disposed = false
    let timer: ReturnType<typeof setTimeout>
    let ws: WebSocket
    let attempts = 0
    function connect() {
      ws = new WebSocket(liveWebSocketUrl(sessionCode))
      ws.onopen = () => { ws.send(JSON.stringify({ token })); setConnected(true); attempts = 0 }
      ws.onclose = () => {
        setConnected(false)
        if (!disposed) timer = setTimeout(connect, Math.min(1000 * 2 ** attempts++, 10000))
      }
      ws.onmessage = (event) => {
        if (disposed) return
        const parsed = JSON.parse(event.data) as LiveDetectionEvent
        setEvents((current) => [parsed, ...current].slice(0, 50))
        setInsightSnapshots(current => ({ ...current,
          [parsed.cam_id]: retainWorkerInsights(current[parsed.cam_id] ?? [], parsed) }))
      }
    }
    connect()
    return () => { disposed = true; clearTimeout(timer); ws?.close() }
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
    setAssigningWorkerId(sessionWorkerId)
    setSessionError(false)
    setMessage(null)
    try {
      const updated = await apiRequest<SessionWorkerRecord>(
        `/api/v1/sessions/${activeSession.id}/workers/${sessionWorkerId}`,
        { method: 'PATCH', body: JSON.stringify({ worker_id: workerId }) },
        token,
      )
      setSessionWorkers(current => current.map(row => row.id === updated.id ? updated : row))
    } catch (err) {
      setSessionError(true)
      setMessage(err instanceof Error ? err.message : 'Worker assignment failed. Try again.')
    } finally {
      setAssigningWorkerId(null)
    }
  }

  async function createAndStartSession() {
    if (!selectedCamIds.length) {
      setMessage('Select at least one paired camera node.')
      return
    }
    setLoading(true)
    setSessionError(false)
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
      setNewSessionOpen(false)
      setEvents([])
      setMessage('Session started. Waiting for edge detection events.')
      await refreshData()
    } catch (err) {
      setSessionError(true)
      setMessage(err instanceof Error ? `Start session failed: ${err.message}` : 'Start session failed.')
    } finally {
      setLoading(false)
    }
  }

  async function startSelectedSession() {
    if (!activeSession) return
    setLoading(true)
    setSessionError(false)
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
      setSessionError(true)
      setMessage(err instanceof Error ? `Start session failed: ${err.message}` : 'Start session failed.')
    } finally {
      setLoading(false)
    }
  }

  async function stopSelectedSession() {
    if (!activeSession) return
    setLoading(true)
    setSessionError(false)
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
      setSessionError(true)
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

  function inspectCamera(camId: string) {
    setInspectorWorkerId('')
    setStreamCamId(camId)
    setInsightsOpen(true)
    setCameraPage(Math.floor(Math.max(0, wallCameras.findIndex(camera => camera.cam_id === camId)) / 4))
    if (focusedCamera) setFocusedCamId(camId)
  }

  function goToCameraPage(page: number) {
    setInspectorWorkerId('')
    setCameraPage(page)
    if (insightsOpen) setStreamCamId(wallCameras[page * 4]?.cam_id ?? '')
  }

  function openNewSession() {
    setInsightsOpen(false)
    setSelectedCamIds(cameraNodes.filter(camera => camera.status === 'online' && camera.metadata_json.health?.camera_available).map(camera => camera.cam_id))
    setNotes('')
    setMessage(null)
    setSessionError(false)
    setNewSessionOpen(true)
  }

  return (
    <Box className="assessmentWorkspace">
      <Box className="assessmentControls">
        <Box className="assessmentHeading">
          <Typography variant="h5">Live Assessment</Typography>
          <Chip size="small" label={connected ? 'Backend connected' : sessionCode ? 'Backend reconnecting' : 'No session selected'} color={connected ? 'success' : sessionCode ? 'warning' : 'default'} />
        </Box>
        <Box className="sessionControlRow">
          <TextField select size="small" label="Session" value={activeSession ? sessionCode : ''} className="sessionPicker"
            onChange={event => { setSessionCode(event.target.value); setEvents([]); setMessage(null) }}>
            <MenuItem value="" disabled>{sessions.length ? 'Select session' : 'No sessions'}</MenuItem>
            {sessions.map(session => <MenuItem key={session.id} value={session.session_code}>
              {session.session_code} - {formatMetricName(session.status)}
            </MenuItem>)}
          </TextField>
          <Button variant="contained" startIcon={<Play size={16} />} disabled={loading || !activeSession || !sessionCamerasReady || !['created', 'review_pending', 'failed'].includes(activeSession.status)} onClick={startSelectedSession}>Start session</Button>
          <Button color="error" variant="outlined" startIcon={<Square size={16} />} disabled={loading || !sessionBusy} onClick={stopSelectedSession}>Stop session</Button>
          <Button variant="outlined" startIcon={<Plus size={16} />} disabled={loading || sessionBusy || !cameraNodes.length} onClick={openNewSession}>New session</Button>
        </Box>
        <Box className="previewControlRow">
          {!sessionBusy ? <TextField select size="small" label="Preview camera" value={validPreviewChoice}
            disabled={loading || !cameraNodes.length} className="previewCameraPicker"
            onChange={event => {
              setPreviewCameraChoice(event.target.value)
              setCameraPage(0)
              setFocusedCamId('')
              setInsightsOpen(false)
              setInspectorWorkerId('')
            }}>
            <MenuItem value="session">{activeSession ? 'Session cameras' : 'All paired cameras'}</MenuItem>
            {activeSession ? <MenuItem value="all">All paired cameras</MenuItem> : null}
            {cameraNodes.map(camera => <MenuItem key={camera.id} value={'camera:' + camera.id}>
              {String(camera.metadata_json.display_name || camera.cam_id)} ({camera.cam_id}){camera.status === 'online' ? '' : ' - Offline'}
            </MenuItem>)}
          </TextField> : null}
          <FormControlLabel control={<Switch size="small" checked={showStream} onChange={event => setShowStream(event.target.checked)} />} label="Video" />
          <FormControlLabel control={<Switch size="small" checked={showOverlay} onChange={event => setShowOverlay(event.target.checked)} />} label="Overlay" />
          <Chip label={streamFps === 'auto' ? 'Preview: Auto' : 'Preview: ' + streamFps + ' FPS'} size="small" />
          <Tooltip title="Preview settings"><IconButton aria-label="Preview settings" aria-expanded={previewSettingsOpen}
            onClick={() => setPreviewSettingsOpen(open => !open)}><Settings size={18} /></IconButton></Tooltip>
          {previewSettingsOpen ? <TextField select size="small" label="Preview FPS" value={streamFps}
            onChange={event => setStreamFps(event.target.value === 'auto' ? 'auto' : Number(event.target.value))} sx={{ width: 140 }}>
            <MenuItem value="auto">Auto</MenuItem><MenuItem value={4}>4</MenuItem><MenuItem value={8}>8</MenuItem><MenuItem value={12}>12</MenuItem>
          </TextField> : null}
          <Typography variant="caption" className="wallSummary">{wallCameras.length} cameras / {activeWorkerCount} tracks visible</Typography>
          {!focusedCamera && pageCount > 1 ? <Box className="cameraPagination">
            <Tooltip title="Previous cameras"><span><IconButton aria-label="Previous cameras" disabled={currentPage === 0} onClick={() => goToCameraPage(currentPage - 1)}><ChevronLeft size={18} /></IconButton></span></Tooltip>
            <Typography variant="caption">{currentPage + 1} / {pageCount}</Typography>
            <Tooltip title="Next cameras"><span><IconButton aria-label="Next cameras" disabled={currentPage >= pageCount - 1} onClick={() => goToCameraPage(currentPage + 1)}><ChevronRight size={18} /></IconButton></span></Tooltip>
          </Box> : null}
        </Box>
        {loading ? <LinearProgress /> : null}
        {message ? <Alert severity={sessionError ? 'error' : 'info'} onClose={() => setMessage(null)}>{message}</Alert> : null}
      </Box>

      <Box className="wallWorkspace" data-inspector={insightsOpen && Boolean(streamCamera)}>
      {visibleCameras.length ? <Box className="cameraWall" data-count={visibleCameras.length}>
        {visibleCameras.map(camera => {
          const label = String(camera.metadata_json.display_name || camera.cam_id)
          const ready = camera.status === 'online' && camera.metadata_json.health?.camera_available
          const latest = events.find(event => event.cam_id === camera.cam_id && (!activeSession?.metadata_json.edge_runs?.[camera.cam_id] || event.run_id === activeSession.metadata_json.edge_runs[camera.cam_id]))
          const count = latest && insightIsLive(latest.timestamp, now, connected, sessionRunning) ? latest.detections.length : 0
          return <Box component="article" className="cameraTile" data-selected={insightsOpen && streamCamera?.cam_id === camera.cam_id} key={camera.id} aria-label={camera.cam_id + ' camera'}>
            <Box className="cameraTileHeader">
              <Box className="cameraTileIdentity"><Typography variant="subtitle2" title={label} noWrap>{label}</Typography>
                <Typography variant="caption" color="text.secondary">{camera.cam_id} / {count} visible</Typography></Box>
              <Chip size="small" label={ready ? 'Ready' : camera.status === 'online' ? 'No camera' : 'Offline'} color={ready ? 'success' : 'default'} />
              <Tooltip title="Assign workers"><span><IconButton disabled={!sessionCameraIds.includes(camera.cam_id)} aria-label={'Assign workers for ' + camera.cam_id} aria-controls="camera-worker-inspector" aria-expanded={insightsOpen && streamCamera?.cam_id === camera.cam_id} onClick={() => inspectCamera(camera.cam_id)}><UserRound size={18} /></IconButton></span></Tooltip>
              <Tooltip title={focusedCamera ? 'Show all cameras' : 'Focus camera'}><IconButton aria-label={(focusedCamera ? 'Show all cameras from ' : 'Focus camera ') + camera.cam_id}
                onClick={() => { setFocusedCamId(focusedCamera ? '' : camera.cam_id); if (insightsOpen) setStreamCamId(camera.cam_id) }}>{focusedCamera ? <Minimize2 size={18} /> : <Maximize2 size={18} />}</IconButton></Tooltip>
            </Box>
            <Box className="livePreview">
              {showStream && camera.status === 'online' ? <CameraPreview cameraId={camera.id} label={camera.cam_id} token={token} fps={streamFps} overlay={showOverlay} />
                : <Box className="cameraPaused"><Camera size={28} /><Typography variant="body2">{showStream ? 'Device offline' : 'Preview paused'}</Typography></Box>}
            </Box>
          </Box>
        })}
      </Box> : <Box className="cameraWallEmpty"><Camera size={32} /><Typography>No paired cameras</Typography>
        <Button startIcon={<RefreshCw size={16} />} onClick={() => void refreshData()}>Refresh devices</Button></Box>}

      {insightsOpen && streamCamera ? <Box component="aside" role="region" aria-label="Camera workers" className="workerInspectorPanel" id="camera-worker-inspector">
        <Box className="workerInspector">
          <Box className="workerInspectorHeading"><Typography variant="h6">Workers</Typography>
            <Tooltip title="Close worker panel"><IconButton aria-label="Close worker panel" onClick={() => setInsightsOpen(false)}><X size={20} /></IconButton></Tooltip></Box>
          <TextField autoFocus select size="small" label="Camera" value={streamCamera?.cam_id ?? ''} onChange={event => inspectCamera(event.target.value)}>
            {wallCameras.map(camera => <MenuItem key={camera.id} value={camera.cam_id}>{String(camera.metadata_json.display_name || camera.cam_id)}</MenuItem>)}
          </TextField>
          <TextField select size="small" label="Worker" value={selectedInspectorWorker} disabled={!visibleInsightSnapshots.length} onChange={event => setInspectorWorkerId(event.target.value)}>
            <MenuItem value="">All workers ({visibleInsightSnapshots.length})</MenuItem>
            {visibleInsightSnapshots.map(row => {
              const worker = sessionWorkers.find(worker => worker.edge_worker_id === row.detection.worker_id && worker.run_id === row.run_id)
              return <MenuItem key={row.detection.worker_id} value={row.detection.worker_id}>
                {worker?.worker_name ? worker.worker_name + ' / ' : ''}{row.detection.worker_id}
              </MenuItem>
            })}
          </TextField>
          {sessionError && message ? <Alert severity="error" onClose={() => setMessage(null)}>{message}</Alert> : null}
          <Box className="workerInspectorBody">
            <DetectionInsights snapshots={inspectorSnapshots} now={now} connected={connected} running={sessionRunning}
              workers={workers} sessionWorkers={sessionWorkers} assignWorker={assignWorker} assigningWorkerId={assigningWorkerId} />
          </Box>
        </Box>
      </Box> : null}
      </Box>
      <Dialog open={newSessionOpen} onClose={() => { if (!loading) setNewSessionOpen(false) }} fullWidth maxWidth="sm">
        <DialogTitle>New assessment session</DialogTitle>
        <DialogContent>
          <Box className="sessionCameraChoices">
            {cameraNodes.map(camera => <FormControlLabel key={camera.id}
              control={<Checkbox checked={selectedCamIds.includes(camera.cam_id)} disabled={loading || camera.status !== 'online' || !camera.metadata_json.health?.camera_available} onChange={() => toggleCamera(camera.cam_id)} />}
              label={<Box><Typography variant="body2">{String(camera.metadata_json.display_name || camera.cam_id)}</Typography>
                <Typography variant="caption" color="text.secondary">{camera.cam_id} / {camera.status === 'online' && camera.metadata_json.health?.camera_available ? 'Camera ready' : 'Unavailable'}</Typography></Box>} />)}
          </Box>
          <TextField label="Session notes" value={notes} onChange={event => setNotes(event.target.value)} fullWidth multiline minRows={2} disabled={loading} sx={{ mt: 2 }} />
          {sessionError && message ? <Alert severity="error" sx={{ mt: 2 }}>{message}</Alert> : null}
          {loading ? <LinearProgress sx={{ mt: 2 }} /> : null}
        </DialogContent>
        <DialogActions><Button disabled={loading} onClick={() => setNewSessionOpen(false)}>Cancel</Button>
          <Button variant="contained" startIcon={<Play size={16} />} disabled={loading || !selectedCamerasReady} onClick={createAndStartSession}>
            {loading ? 'Starting...' : 'Start session'}
          </Button></DialogActions>
      </Dialog>

    </Box>
  )
}

function DetectionInsights({
  snapshots,
  now,
  connected,
  running,
  workers,
  sessionWorkers,
  assignWorker,
  assigningWorkerId,
}: {
  snapshots: WorkerInsightSnapshot[]
  now: number
  connected: boolean
  running: boolean
  workers: WorkerRecord[]
  sessionWorkers: SessionWorkerRecord[]
  assignWorker: (sessionWorkerId: string, workerId: string | null) => Promise<void>
  assigningWorkerId: string | null
}) {
  if (!snapshots.length) {
    return (
      <Box className="insightPanel emptyInsight">
        <Typography variant="h6">Detection Insights</Typography>
        <Typography color="text.secondary">No workers observed yet.</Typography>
      </Box>
    )
  }

  const liveCount = snapshots.filter(row => insightIsLive(row.timestamp, now, connected, running)).length
  const status = !running ? 'Session inactive' : !connected ? 'Disconnected' : liveCount ? 'Live' : 'No workers visible'
  return (
    <Box className="insightPanel">
      <Box className="insightHeader">
        <Box>
          <Typography variant="h6">Detection Insights</Typography>
          <Typography variant="body2" color="text.secondary">
            {snapshots[0].cam_id} - {liveCount} live / {snapshots.length} observed
          </Typography>
        </Box>
        <Chip size="small" color={liveCount ? 'success' : 'default'} label={status} />
      </Box>

      <Box className="workerList">
        {snapshots.map((row) => (
          <WorkerInsightCard
            key={`${row.cam_id}/${row.run_id}/${row.detection.worker_id}`}
            detection={row.detection}
            isLive={insightIsLive(row.timestamp, now, connected, running)}
            lastSeenAt={row.timestamp}
            now={now}
            workers={workers}
            sessionWorker={sessionWorkers.find((worker) => worker.edge_worker_id === row.detection.worker_id && worker.run_id === row.run_id)}
            assignWorker={assignWorker}
            assigningWorkerId={assigningWorkerId}
          />
        ))}
      </Box>

    </Box>
  )
}

function WorkerInsightCard({
  detection,
  isLive,
  lastSeenAt,
  now,
  workers,
  sessionWorker,
  assignWorker,
  assigningWorkerId,
}: {
  detection: LiveDetection
  isLive: boolean
  lastSeenAt: number
  now: number
  workers: WorkerRecord[]
  sessionWorker?: SessionWorkerRecord
  assignWorker: (sessionWorkerId: string, workerId: string | null) => Promise<void>
  assigningWorkerId: string | null
}) {
  const rula = readRiskScore(detection.metadata?.rula)
  const reba = readRiskScore(detection.metadata?.reba)
  const angles = readAngles(detection.metadata?.angles)
  const assessmentQuality = readAssessmentQuality(detection.metadata?.assessment_quality)
  const identityStatus = readMetadataString(detection.metadata?.identity_status)
  const keypointCount = detection.keypoints?.points.length ?? 0
  const bbox = detection.bbox.map((value) => Math.round(value))
  return (
    <Box className="workerCard" role="group" aria-label={detection.worker_id + ' worker'}>
      <Box className="workerAssignmentRow">
      <Box>
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

      <Typography className="workerCardStatus" variant="caption" color="text.secondary" sx={{ minHeight: 20 }}>
        {isLive ? 'Live measurements' : `Last seen ${Math.max(0, Math.floor((now - lastSeenAt) / 1000))}s ago / not live`}
      </Typography>
      </Box>
      <TextField
        select
        size="small"
        label="Assign worker"
        value={sessionWorker?.worker_id ?? ''}
        disabled={!sessionWorker || assigningWorkerId !== null}
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
      </Box>
      <Box sx={{ height: 2 }}>{sessionWorker && assigningWorkerId === sessionWorker.id ? <LinearProgress /> : null}</Box>

      <Box className="workerScoreRow">
        <Chip size="small" label={`RULA ${rula.score} ${rula.risk}`} color={riskColor(rula.risk)} />
        <Chip size="small" label={`REBA ${reba.score} ${reba.risk}`} color={riskColor(reba.risk)} />
        <Chip size="small" variant="outlined" label={`Pose ${assessmentQuality}`} />
        <Chip size="small" variant="outlined" label={`Identity ${identityStatus}`} />
      </Box>

      <details className="workerMeasurements">
      <summary>Measurements</summary>
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
      </details>
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

function formatDateTime(timestamp: string): string {
  return new Date(timestamp).toLocaleString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    day: '2-digit',
    month: 'short',
  })
}

function formatDuration(durationMs: number): string {
  if (durationMs < 60_000) {
    return `${Math.round(durationMs / 1000)}s`
  }
  return `${Math.round(durationMs / 60_000)}m`
}

function eventLabel(eventType: string): string {
  if (eventType === 'high_risk_posture') return 'High Risk Posture'
  if (eventType === 'sustained_high_risk') return 'Sustained High Risk'
  if (eventType === 'worker_observed') return 'Worker Observed'
  if (eventType === 'worker_entered') return 'Worker Entered'
  if (eventType === 'worker_left') return 'Worker Left'
  return eventType.replaceAll('_', ' ')
}

function severityColor(severity: string): 'default' | 'success' | 'warning' | 'error' {
  if (severity === 'critical') return 'error'
  if (severity === 'high') return 'warning'
  if (severity === 'low') return 'success'
  return 'default'
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

  async function setWorkerActive(workerId: string, isActive: boolean) {
    setLoading(true)
    try {
      await apiRequest<WorkerRecord>(
        `/api/v1/workers/${workerId}`,
        {
          method: 'PATCH',
          body: JSON.stringify({ is_active: isActive }),
        },
        token,
      )
      await refreshData()
      setMessage(isActive ? 'Worker activated.' : 'Worker deactivated.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to update worker status.')
    } finally {
      setLoading(false)
    }
  }

  async function deleteWorker(worker: WorkerRecord) {
    const confirmed = window.confirm(
      `Delete ${worker.name}? Workers with session history cannot be deleted and should be deactivated instead.`,
    )
    if (!confirmed) return

    setLoading(true)
    try {
      await apiRequest(`/api/v1/workers/${worker.id}`, { method: 'DELETE' }, token)
      await refreshData()
      setMessage('Worker deleted.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to delete worker.')
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
              <Box className="workerActions">
                {worker.is_active ? (
                  <Button
                    color="warning"
                    size="small"
                    startIcon={<X size={16} />}
                    disabled={loading}
                    onClick={() => void setWorkerActive(worker.id, false)}
                  >
                    Deactivate
                  </Button>
                ) : (
                  <Button
                    color="success"
                    size="small"
                    startIcon={<RotateCcw size={16} />}
                    disabled={loading}
                    onClick={() => void setWorkerActive(worker.id, true)}
                  >
                    Activate
                  </Button>
                )}
                <Button
                  color="error"
                  size="small"
                  startIcon={<Trash2 size={16} />}
                  disabled={loading}
                  onClick={() => void deleteWorker(worker)}
                >
                  Delete
                </Button>
              </Box>
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
        {enrollmentViews.map((view) => {
          const record = images.find((image) => image.view === view.key)
          const issues = record?.quality_details.issues ?? []
          return (
            <Box key={view.key} className="enrollmentView">
              <Box className="enrollmentPreview">
                {imageUrls[view.key] ? (
                  <img src={imageUrls[view.key]} alt={`${worker.name} ${view.label}`} />
                ) : (
                  <UserRound size={34} />
                )}
              </Box>
              <Box className="enrollmentViewHeader">
                <Typography variant="body2" sx={{ fontWeight: 700 }}>{view.label}</Typography>
                {record ? (
                  <Chip
                    size="small"
                    label={record.quality_status === 'good' ? 'Good' : 'Review'}
                    color={record.quality_status === 'good' ? 'success' : 'warning'}
                  />
                ) : null}
              </Box>
              {record ? (
                <Typography variant="caption" color="text.secondary">
                  {record.width}x{record.height} - {formatFileSize(record.file_size)}
                </Typography>
              ) : (
                <Typography variant="caption" color="text.secondary">No photo uploaded.</Typography>
              )}
              {issues.length ? (
                <Box className="enrollmentIssues">
                  {issues.slice(0, 2).map((issue) => (
                    <Typography key={issue} variant="caption" color="text.secondary">{issue}</Typography>
                  ))}
                </Box>
              ) : null}
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
          )
        })}
      </Box>
      {message ? <Typography variant="caption" color="text.secondary">{message}</Typography> : null}
    </Box>
  )
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
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
  const [manualIp, setManualIp] = useState('10.55.0.1')
  const [backendReachableUrl, setBackendReachableUrl] = useState(backendUrl)
  const [networkDevice, setNetworkDevice] = useState<DiscoveredDevice | null>(null)
  const [networkStatus, setNetworkStatus] = useState<EdgeNetworkStatus | null>(null)
  const [wifiNetworks, setWifiNetworks] = useState<WifiNetwork[]>([])
  const [wifiSsid, setWifiSsid] = useState('')
  const [wifiPassword, setWifiPassword] = useState('')
  const [showWifiPassword, setShowWifiPassword] = useState(false)
  const [networkLoading, setNetworkLoading] = useState(false)
  const [networkMessage, setNetworkMessage] = useState<string | null>(null)
  const [networkError, setNetworkError] = useState(false)
  const [exportingDiagnostics, setExportingDiagnostics] = useState(false)
  const isElectron = Boolean(window.ergoquipt)

  async function exportDiagnostics() {
    setExportingDiagnostics(true)
    try {
      const blob = await apiBlob('/api/v1/diagnostics', token)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'ergosight-diagnostics.zip'
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Diagnostic export failed. Try again.')
    } finally {
      setExportingDiagnostics(false)
    }
  }

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
        await Promise.all(
          discovered
            .filter((device) => device.paired)
            .map((device) => attachEdgeBaseUrl(device.cam_id, device.baseUrl)),
        )
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
        throw new Error('Not an ERGoSIGHT edge device')
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
      if (device.paired) await attachEdgeBaseUrl(device.cam_id, device.baseUrl)
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
      const reachable = window.ergoquipt?.backendUrlForDevice
        ? await window.ergoquipt.backendUrlForDevice({ baseUrl: device.baseUrl, backendUrl: backendReachableUrl })
        : backendReachableUrl
      const result = await apiRequest<{ status: string; cam_id: string }>('/api/v1/device-pairings/relay', {
        method: 'POST', body: JSON.stringify({ cam_id: device.cam_id, pairing_code: pairing.pairing_code,
          edge_base_url: device.baseUrl, backend_url: reachable }),
      }, token)
      setMessage(`Paired ${result?.cam_id ?? device.cam_id}`)
      await attachEdgeBaseUrl(result?.cam_id ?? device.cam_id, device.baseUrl)
      setPairing(null)
      await probeDevice(device.baseUrl)
      await refreshData()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Pairing failed. Check the device connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  async function openNetworkSetup(device: DiscoveredDevice) {
    setNetworkDevice(device)
    setNetworkStatus(null)
    setWifiNetworks([])
    setWifiSsid('')
    setWifiPassword('')
    setNetworkMessage(null)
    setNetworkError(false)
    setNetworkLoading(true)
    try {
      const node = cameraNodes.find((node) => node.cam_id === device.cam_id)
      if (!node) throw new Error('Pair this camera to your account first.')
      const [status, scan] = await Promise.all([
        apiRequest<EdgeNetworkStatus>(`/api/v1/camera-nodes/${node.id}/network/status`, {}, token),
        apiRequest<{ networks: WifiNetwork[] }>(`/api/v1/camera-nodes/${node.id}/network/wifi`, {}, token),
      ])
      setNetworkStatus(status)
      setWifiNetworks(scan.networks)
      const connected = scan.networks.find((network) => network.connected)
      if (connected && !status.hotspot) setWifiSsid(connected.ssid)
    } catch (err) {
      setNetworkError(true)
      setNetworkMessage(err instanceof Error ? err.message : 'Unable to read device networks.')
    } finally {
      setNetworkLoading(false)
    }
  }

  async function refreshWifiNetworks() {
    if (!networkDevice) return
    setNetworkLoading(true)
    setNetworkMessage(null)
    setNetworkError(false)
    try {
      const node = cameraNodes.find((node) => node.cam_id === networkDevice.cam_id)
      if (!node) throw new Error('Pair this camera first.')
      const scan = await apiRequest<{ networks: WifiNetwork[] }>(`/api/v1/camera-nodes/${node.id}/network/wifi`, {}, token)
      setWifiNetworks(scan.networks)
    } catch (err) {
      setNetworkError(true)
      setNetworkMessage(err instanceof Error ? err.message : 'Wi-Fi scan failed.')
    } finally {
      setNetworkLoading(false)
    }
  }

  async function submitWifi(event: FormEvent) {
    event.preventDefault()
    if (!networkDevice) return
    if (!wifiSsid.trim() || (wifiPassword.length > 0 && wifiPassword.length < 8)) {
      setNetworkError(true)
      setNetworkMessage('Enter an SSID and a password of at least 8 characters, or leave it empty for an open network.')
      return
    }
    setNetworkLoading(true)
    setNetworkMessage(null)
    setNetworkError(false)
    try {
      const node = cameraNodes.find((node) => node.cam_id === networkDevice.cam_id)
      if (!node) throw new Error('Pair this camera first.')
      await apiRequest(`/api/v1/camera-nodes/${node.id}/network/wifi/connect`, {
        method: 'POST', body: JSON.stringify({ ssid: wifiSsid.trim(), password: wifiPassword }),
      }, token)
      setNetworkMessage(`Connecting to ${wifiSsid.trim()}. Reconnect this laptop to that Wi-Fi, then run Scan LAN.`)
    } catch (err) {
      setNetworkError(true)
      setNetworkMessage(err instanceof Error ? err.message : 'Wi-Fi connection failed.')
    } finally {
      setNetworkLoading(false)
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
      <PageTitle title="Devices" action={<Stack direction="row" spacing={1}>
        <Button startIcon={<Download size={16} />} disabled={exportingDiagnostics} onClick={() => void exportDiagnostics()}>
          {exportingDiagnostics ? 'Exporting…' : 'Diagnostics'}
        </Button>
        <Button onClick={refreshData}>Refresh</Button>
      </Stack>} />
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
              <Button
                size="small"
                variant="outlined"
                startIcon={<Wifi size={16} />}
                disabled={!device.paired || loading}
                onClick={() => void openNetworkSetup(device)}
              >
                Set up Wi-Fi
              </Button>
              <Button size="small" variant="contained" disabled={!pairing || loading} onClick={() => pairDevice(device)}>
                {pairing ? 'Pair' : 'Create code first'}
              </Button>
            </Box>
          ))
        ) : (
          <Typography color="text.secondary">No edge devices listed yet. Use Scan LAN or Probe IP.</Typography>
        )}
      </Paper>
      <Dialog open={Boolean(networkDevice)} onClose={() => setNetworkDevice(null)} fullWidth maxWidth="sm">
        <Box component="form" onSubmit={submitWifi}>
          <DialogTitle>Wi-Fi setup</DialogTitle>
          <DialogContent dividers>
            <Stack spacing={2}>
              <Typography color="text.secondary">
                {networkDevice?.hostname} · {networkDevice?.address}
              </Typography>
              {networkStatus ? (
                <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap' }}>
                  <Chip
                    size="small"
                    color={networkStatus.hotspot ? 'warning' : 'success'}
                    label={networkStatus.hotspot ? `Setup hotspot: ${networkStatus.hotspot_ssid}` : `Wi-Fi: ${networkStatus.wifi.connection ?? 'disconnected'}`}
                  />
                  <Chip size="small" label={`Direct LAN: ${networkStatus.direct_lan_address}`} />
                </Stack>
              ) : null}
              <Stack direction="row" spacing={2} sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="subtitle2">Available networks</Typography>
                <IconButton
                  aria-label="Refresh Wi-Fi networks"
                  disabled={networkLoading}
                  onClick={() => void refreshWifiNetworks()}
                >
                  <RefreshCw size={18} />
                </IconButton>
              </Stack>
              <List className="wifiNetworkList" disablePadding>
                {wifiNetworks.map((network) => (
                  <ListItemButton
                    key={network.ssid}
                    selected={wifiSsid === network.ssid}
                    onClick={() => setWifiSsid(network.ssid)}
                  >
                    <ListItemIcon><Wifi size={18} /></ListItemIcon>
                    <ListItemText primary={network.ssid} secondary={`${network.security} · ${network.signal}% signal`} />
                    {network.connected ? <Chip size="small" color="success" label="Connected" /> : null}
                  </ListItemButton>
                ))}
                {!wifiNetworks.length && !networkLoading ? (
                  <Typography color="text.secondary" sx={{ p: 2 }}>No networks found. Enter the SSID manually.</Typography>
                ) : null}
              </List>
              <TextField
                required
                label="Network name (SSID)"
                value={wifiSsid}
                onChange={(event) => setWifiSsid(event.target.value)}
                slotProps={{ htmlInput: { maxLength: 32 } }}
              />
              <TextField
                label="Wi-Fi password"
                type={showWifiPassword ? 'text' : 'password'}
                value={wifiPassword}
                onChange={(event) => setWifiPassword(event.target.value)}
                helperText="Leave empty only for an open network."
                slotProps={{
                  htmlInput: { minLength: wifiPassword ? 8 : undefined, maxLength: 63 },
                  input: { endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label={showWifiPassword ? 'Hide Wi-Fi password' : 'Show Wi-Fi password'}
                        onClick={() => setShowWifiPassword((current) => !current)}
                        edge="end"
                      >
                        {showWifiPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                      </IconButton>
                    </InputAdornment>
                  ) },
                }}
              />
              {networkLoading ? <LinearProgress /> : null}
              {networkMessage ? <Alert severity={networkError ? 'error' : 'info'}>{networkMessage}</Alert> : null}
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setNetworkDevice(null)}>Close</Button>
            <Button type="submit" variant="contained" disabled={networkLoading || !wifiSsid.trim()}>
              Connect
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  )
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

type ReviewFormState = {
  load_score: number
  coupling_score: number
  activity_score: number
  wrist_twist_score: number
  notes: string
  angle_overrides: Record<string, number>
}

const emptyReviewForm: ReviewFormState = {
  load_score: 0,
  coupling_score: 0,
  activity_score: 0,
  wrist_twist_score: 1,
  angle_overrides: {},
  notes: '',
}

function SessionReview({
  token,
  sessions,
  workers,
  refreshData,
}: {
  token: string
  sessions: SessionRecord[]
  workers: WorkerRecord[]
  refreshData: () => Promise<void>
}) {
  const reviewSessions = sessions.filter((session) => ['running', 'review_pending', 'completed'].includes(session.status))
  const [selectedSessionId, setSelectedSessionId] = useState(reviewSessions[0]?.id ?? '')
  const [events, setEvents] = useState<ErgonomicEventRecord[]>([])
  const [summary, setSummary] = useState<SessionExposureSummaryRecord | null>(null)
  const [selectedEventId, setSelectedEventId] = useState('')
  const [eventDetail, setEventDetail] = useState<EventDetailRecord | null>(null)
  const [assessmentType, setAssessmentType] = useState<'reba' | 'rula'>('reba')
  const [reviewForm, setReviewForm] = useState<ReviewFormState>(emptyReviewForm)
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null)
  const [inspectEvidence, setInspectEvidence] = useState(false)
  const [loading, setLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [workerFilter, setWorkerFilter] = useState('all')
  const [eventTypeFilter, setEventTypeFilter] = useState('all')
  const [severityFilter, setSeverityFilter] = useState('all')
  const [reviewFilter, setReviewFilter] = useState('all')
  const [sortMode, setSortMode] = useState<'time' | 'risk'>('time')
  const [identityWorkerId, setIdentityWorkerId] = useState('')

  useEffect(() => {
    if (!selectedSessionId && reviewSessions[0]?.id) {
      setSelectedSessionId(reviewSessions[0].id)
    }
  }, [reviewSessions, selectedSessionId])

  useEffect(() => {
    if (!selectedSessionId) {
      setEvents([])
      setSummary(null)
      return
    }
    let cancelled = false
    async function loadEvents() {
      setLoading(true)
      setMessage(null)
      try {
        const [rows, sessionSummary] = await Promise.all([
          apiRequest<ErgonomicEventRecord[]>(
            `/api/v1/sessions/${selectedSessionId}/events`,
            {},
            token,
          ),
          apiRequest<SessionExposureSummaryRecord>(
            `/api/v1/sessions/${selectedSessionId}/summary`,
            {},
            token,
          ),
        ])
        if (!cancelled) {
          setEvents(rows)
          setSummary(sessionSummary)
          setSelectedEventId((current) => {
            if (rows.some((row) => row.id === current)) return current
            return rows.find((row) => row.event_type === 'high_risk_posture')?.id ?? rows[0]?.id ?? ''
          })
        }
      } catch (err) {
        if (!cancelled) {
          const detail = err instanceof Error ? err.message : 'Failed to load session events.'
          setMessage(
            detail === 'Not Found'
              ? 'The running backend does not support Session Review. Close all running app/backend processes, then start Electron again.'
              : detail,
          )
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }
    void loadEvents()
    return () => {
      cancelled = true
    }
  }, [selectedSessionId, token])

  useEffect(() => {
    if (!selectedEventId) {
      setEventDetail(null)
      return
    }
    let cancelled = false
    async function loadDetail() {
      setDetailLoading(true)
      try {
        const detail = await apiRequest<EventDetailRecord>(
          `/api/v1/sessions/${selectedSessionId}/events/${selectedEventId}`,
          {},
          token,
        )
        if (!cancelled) {
          setEventDetail(detail)
          setMessage(null)
        }
      } catch (err) {
        if (!cancelled) setMessage(err instanceof Error ? err.message : 'Failed to load event detail.')
      } finally {
        if (!cancelled) setDetailLoading(false)
      }
    }
    void loadDetail()
    return () => {
      cancelled = true
    }
  }, [selectedEventId, selectedSessionId, token])

  const eventReviews = eventDetail?.reviews
  useEffect(() => {
    const review = eventReviews?.find((row) => row.assessment_type === assessmentType)
    setReviewForm(review ? formFromReview(review) : emptyReviewForm)
  }, [assessmentType, eventReviews])

  const evidenceEventId = eventDetail?.id
  const hasEvidence = Boolean(eventDetail?.snapshots.length)
  useEffect(() => {
    if (!evidenceEventId || hasEvidence) return
    let cancelled = false
    let attempts = 0
    let timer: ReturnType<typeof setTimeout>
    async function pollEvidence() {
      try {
        const detail = await apiRequest<EventDetailRecord>(`/api/v1/sessions/${selectedSessionId}/events/${evidenceEventId}`, {}, token)
        if (cancelled) return
        if (detail.snapshots.length) {
          setEventDetail((current) => current?.id === detail.id ? { ...current, snapshots: detail.snapshots } : current)
        } else if (++attempts < 20) timer = setTimeout(() => void pollEvidence(), 500)
      } catch { /* Evidence can remain unavailable after the source buffer expires. */ }
    }
    timer = setTimeout(() => void pollEvidence(), 500)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [evidenceEventId, hasEvidence, selectedSessionId, token])

  useEffect(() => {
    const selected = events.find((event) => event.id === selectedEventId)
    setIdentityWorkerId(selected?.worker_id ?? '')
  }, [events, selectedEventId])

  useEffect(() => {
    const snapshot = eventDetail?.snapshots[0]
    if (!snapshot) {
      setSnapshotUrl(null)
      return
    }
    let cancelled = false
    void apiBlob(snapshot.content_url, token)
      .then((blob) => {
        if (!cancelled) setSnapshotUrl(URL.createObjectURL(blob))
      })
      .catch(() => {
        if (!cancelled) setSnapshotUrl(null)
      })
    return () => {
      cancelled = true
    }
  }, [eventDetail, token])

  useEffect(() => () => {
    if (snapshotUrl) URL.revokeObjectURL(snapshotUrl)
  }, [snapshotUrl])

  async function reloadEventDetail() {
    if (!selectedEventId) return
    const detail = await apiRequest<EventDetailRecord>(
      `/api/v1/sessions/${selectedSessionId}/events/${selectedEventId}`,
      {},
      token,
    )
    setEventDetail(detail)
  }

  async function saveReview() {
    if (!selectedEventId) return
    setSaving(true)
    setMessage(null)
    try {
      await apiRequest(
        `/api/v1/sessions/${selectedSessionId}/events/${selectedEventId}/reviews/${assessmentType}`,
        {
          method: 'PUT',
          body: JSON.stringify(reviewForm),
        },
        token,
      )
      await reloadEventDetail()
      setEvents((current) => current.map((event) => (
        event.id === selectedEventId
          ? {
              ...event,
              reviewed_assessment_types: Array.from(
                new Set([...event.reviewed_assessment_types, assessmentType]),
              ),
            }
          : event
      )))
      const nextSummary = await apiRequest<SessionExposureSummaryRecord>(
        `/api/v1/sessions/${selectedSessionId}/summary`,
        {},
        token,
      )
      setSummary(nextSummary)
      setMessage(`${assessmentType.toUpperCase()} review saved.`)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to save review.')
    } finally {
      setSaving(false)
    }
  }

  async function confirmIdentity() {
    if (!selectedEvent) return
    setSaving(true)
    setMessage(null)
    try {
      const assigned = await apiRequest<SessionWorkerRecord>(
        `/api/v1/sessions/${selectedSessionId}/workers/${selectedEvent.session_worker_id}`,
        {
          method: 'PATCH',
          body: JSON.stringify({ worker_id: identityWorkerId || null }),
        },
        token,
      )
      setEvents((current) => current.map((event) => (
        event.session_worker_id === assigned.id
          ? {
              ...event,
              worker_id: assigned.worker_id,
              worker_name: assigned.worker_name,
              employee_number: assigned.employee_number,
            }
          : event
      )))
      const nextSummary = await apiRequest<SessionExposureSummaryRecord>(
        `/api/v1/sessions/${selectedSessionId}/summary`,
        {},
        token,
      )
      setSummary(nextSummary)
      setMessage(assigned.worker_name ? `Identity confirmed as ${assigned.worker_name}.` : 'Identity cleared.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to confirm identity.')
    } finally {
      setSaving(false)
    }
  }

  async function completeReview() {
    if (!selectedSessionId) return
    setSaving(true)
    try {
      await apiRequest(`/api/v1/sessions/${selectedSessionId}/complete`, { method: 'POST' }, token)
      await refreshData()
      setMessage('Session review completed.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to complete session review.')
    } finally {
      setSaving(false)
    }
  }

  async function deleteSelectedSession() {
    if (!selectedSession || selectedSession.status === 'running') return
    const confirmed = window.confirm(
      `Delete ${selectedSession.session_code} and all of its detections, reviews, and snapshots?`,
    )
    if (!confirmed) return
    setSaving(true)
    setMessage(null)
    try {
      await apiRequest<void>(`/api/v1/sessions/${selectedSession.id}`, { method: 'DELETE' }, token)
      setSelectedSessionId('')
      setSelectedEventId('')
      setEvents([])
      setEventDetail(null)
      await refreshData()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to delete session.')
    } finally {
      setSaving(false)
    }
  }

  const selectedSession = sessions.find((session) => session.id === selectedSessionId)
  const selectedEvent = events.find((event) => event.id === selectedEventId)
  const highRiskEvents = events.filter((event) => event.event_type === 'high_risk_posture')
  const workerOptions = Array.from(
    new Map(events.map((event) => [event.session_worker_id, event.worker_name ?? event.edge_worker_id])).entries(),
  )
  const eventTypeOptions = Array.from(new Set(events.map((event) => event.event_type))).sort()
  const severityOptions = Array.from(new Set(events.map((event) => event.severity))).sort()
  const filteredEvents = events
    .filter((event) => workerFilter === 'all' || event.session_worker_id === workerFilter)
    .filter((event) => eventTypeFilter === 'all' || event.event_type === eventTypeFilter)
    .filter((event) => severityFilter === 'all' || event.severity === severityFilter)
    .filter((event) => {
      if (reviewFilter === 'reviewed') return event.reviewed_assessment_types.length > 0
      if (reviewFilter === 'pending') {
        return event.score !== null && event.reviewed_assessment_types.length === 0
      }
      return true
    })
    .sort((left, right) => {
      if (sortMode === 'risk') {
        const scoreDifference = (right.score ?? -1) - (left.score ?? -1)
        if (scoreDifference) return scoreDifference
      }
      return new Date(right.started_at).getTime() - new Date(left.started_at).getTime()
    })
  const currentReview = eventDetail?.reviews.find((row) => row.assessment_type === assessmentType)
  const provisional = eventDetail?.provisional_scores[assessmentType]
  const displayedBreakdown = currentReview?.breakdown ?? provisional?.breakdown ?? {}
  const requiredAngles = ['neck', 'trunk', 'ua_l', 'ua_r', 'la_l', 'la_r', 'leg_l', 'leg_r', 'wrist_l', 'wrist_r']
  const missingAngles = requiredAngles.filter((key) => typeof eventDetail?.angles[key] !== 'number')
  const missingManual = missingAngles.filter((key) => !Number.isFinite(reviewForm.angle_overrides[key]))
  const verifiedEvidence = eventDetail?.snapshots[0]?.metadata.source === 'verified_source_frame'
  const canFinalize = missingManual.length === 0 && Boolean(snapshotUrl) && verifiedEvidence
  const selectedWorkerSummary = summary?.workers.find(
    (worker) => worker.session_worker_id === selectedEvent?.session_worker_id,
  )

  return (
    <Stack spacing={3}>
      <Dialog open={inspectEvidence} onClose={() => setInspectEvidence(false)} maxWidth="lg" fullWidth>
        <DialogTitle>Posture Evidence</DialogTitle>
        <DialogContent>{snapshotUrl ? <img className="fullEvidence" src={snapshotUrl} alt="Recorded posture evidence" /> : null}</DialogContent>
        <DialogActions><Button onClick={() => setInspectEvidence(false)}>Close</Button></DialogActions>
      </Dialog>
      <PageTitle
        title="Session Review"
        action={selectedSession ? (
          <Stack direction="row" spacing={1}>
            {selectedSession.status === 'review_pending' ? (
              <Button variant="contained" startIcon={<ClipboardCheck size={18} />} disabled={saving} onClick={completeReview}>
                Complete Review
              </Button>
            ) : null}
            <Button
              color="error"
              variant="outlined"
              startIcon={<Trash2 size={17} />}
              disabled={saving || selectedSession.status === 'running'}
              onClick={deleteSelectedSession}
            >
              Delete Session
            </Button>
          </Stack>
        ) : null}
      />
      <Paper className="panel" elevation={0}>
        <Box className="reviewHeader">
          <TextField
            select
            label="Session"
            value={selectedSessionId}
            onChange={(event) => setSelectedSessionId(event.target.value)}
            sx={{ minWidth: 280 }}
          >
            {reviewSessions.map((session) => (
              <MenuItem key={session.id} value={session.id}>
                {session.session_code} - {session.status}
              </MenuItem>
            ))}
          </TextField>
          <Box sx={{ flex: 1 }}>
            <Typography sx={{ fontWeight: 700 }}>{selectedSession?.notes || selectedSession?.session_code || 'No session selected'}</Typography>
            <Typography variant="body2" color="text.secondary">
              {selectedSession ? `${selectedSession.status} - ${selectedSession.started_at ? formatDateTime(selectedSession.started_at) : 'not started'}` : 'Start or stop a session to review events.'}
            </Typography>
          </Box>
        </Box>
        {loading ? <LinearProgress sx={{ mt: 2 }} /> : null}
        {message ? <Alert severity="info" sx={{ mt: 2 }}>{message}</Alert> : null}
      </Paper>
      <Box className="metricGrid">
        <Metric label="Workers Observed" value={summary?.worker_count ?? 0} icon={UserRound} />
        <Metric label="High Risk Events" value={summary?.high_risk_event_count ?? highRiskEvents.length} icon={ShieldCheck} />
        <Metric label="Reviewed Events" value={summary?.reviewed_event_count ?? 0} icon={ClipboardCheck} />
        <Metric label="Exposure Minutes" value={Math.round((summary?.high_risk_duration_ms ?? 0) / 60_000)} icon={BarChart3} />
      </Box>
      <Paper className="panel reviewWorkspace" elevation={0}>
        <Box className="timelinePane">
          <Box className="reviewDetailHeader">
            <Typography variant="h6">Event Timeline</Typography>
            <Chip size="small" label={`${filteredEvents.length} of ${events.length}`} />
          </Box>
          <Divider sx={{ my: 2 }} />
          <Box
            className="timelineFilters"
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', lg: 'repeat(2, minmax(0, 1fr))' },
            }}
          >
            <TextField select size="small" label="Worker" value={workerFilter} onChange={(event) => setWorkerFilter(event.target.value)} sx={{ minWidth: 0, width: '100%' }}>
              <MenuItem value="all">All workers</MenuItem>
              {workerOptions.map(([id, label]) => <MenuItem key={id} value={id}>{label}</MenuItem>)}
            </TextField>
            <TextField select size="small" label="Event" value={eventTypeFilter} onChange={(event) => setEventTypeFilter(event.target.value)} sx={{ minWidth: 0, width: '100%' }}>
              <MenuItem value="all">All events</MenuItem>
              {eventTypeOptions.map((type) => <MenuItem key={type} value={type}>{eventLabel(type)}</MenuItem>)}
            </TextField>
            <TextField select size="small" label="Severity" value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)} sx={{ minWidth: 0, width: '100%' }}>
              <MenuItem value="all">All severity</MenuItem>
              {severityOptions.map((severity) => <MenuItem key={severity} value={severity}>{formatMetricName(severity)}</MenuItem>)}
            </TextField>
            <TextField select size="small" label="Review" value={reviewFilter} onChange={(event) => setReviewFilter(event.target.value)} sx={{ minWidth: 0, width: '100%' }}>
              <MenuItem value="all">All status</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="reviewed">Reviewed</MenuItem>
            </TextField>
            <TextField className="timelineSort" select size="small" label="Sort" value={sortMode} onChange={(event) => setSortMode(event.target.value as 'time' | 'risk')} sx={{ minWidth: 0, width: '100%', gridColumn: '1 / -1' }}>
              <MenuItem value="time">Latest first</MenuItem>
              <MenuItem value="risk">Worst first</MenuItem>
            </TextField>
          </Box>
          <Divider sx={{ my: 2 }} />
          {filteredEvents.length ? (
            <Stack spacing={1}>
              {filteredEvents.map((event) => (
                <Box
                  key={event.id}
                  className={`eventRow eventRowButton${event.id === selectedEventId ? ' selected' : ''}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => setSelectedEventId(event.id)}
                  onKeyDown={(keyEvent) => {
                    if (keyEvent.key === 'Enter' || keyEvent.key === ' ') setSelectedEventId(event.id)
                  }}
                >
                  <Box>
                    <Typography sx={{ fontWeight: 700 }}>{eventLabel(event.event_type)}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {event.worker_name ?? event.edge_worker_id} - {formatDateTime(event.started_at)}
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
                    {event.reviewed_assessment_types.length ? <Chip size="small" label="reviewed" color="success" /> : null}
                    <Chip size="small" label={event.severity} color={severityColor(event.severity)} />
                    {event.score ? <Chip size="small" label={`${event.score_type?.toUpperCase()} ${event.score}`} /> : null}
                    <Typography variant="caption" color="text.secondary">
                      {event.duration_ms !== null ? formatDuration(event.duration_ms) : 'active'}
                    </Typography>
                  </Stack>
                </Box>
              ))}
            </Stack>
          ) : (
            <Typography color="text.secondary">
              {events.length ? 'No events match the selected filters.' : 'No events recorded for this session yet.'}
            </Typography>
          )}
        </Box>

        <Box className="reviewDetailPane">
          <Box className="reviewDetailHeader">
            <Box>
              <Typography variant="h6">Review Evidence</Typography>
              <Typography variant="body2" color="text.secondary">
                {selectedEvent ? `${selectedEvent.worker_name ?? selectedEvent.edge_worker_id} - ${formatDateTime(selectedEvent.started_at)}` : 'No event selected'}
              </Typography>
            </Box>
            {eventDetail?.assessment_quality.status ? (
              <Chip size="small" label={`Pose ${eventDetail.assessment_quality.status}`} color={eventDetail.assessment_quality.status === 'good' ? 'success' : 'warning'} />
            ) : null}
          </Box>
          <Divider sx={{ my: 2 }} />
          {detailLoading ? <LinearProgress /> : null}
          {selectedEvent && eventDetail ? (
            <Stack spacing={2.5}>
              <Box className="identityReviewBar">
                <TextField
                  select
                  size="small"
                  label="Worker Identity"
                  value={identityWorkerId}
                  onChange={(event) => setIdentityWorkerId(event.target.value)}
                  sx={{ minWidth: 240 }}
                >
                  <MenuItem value="">Unassigned</MenuItem>
                  {workers.filter((worker) => worker.is_active).map((worker) => (
                    <MenuItem key={worker.id} value={worker.id}>
                      {worker.name}{worker.employee_number ? ` - ${worker.employee_number}` : ''}
                    </MenuItem>
                  ))}
                </TextField>
                <Button variant="outlined" disabled={saving} onClick={confirmIdentity}>
                  Confirm Identity
                </Button>
                {selectedWorkerSummary ? (
                  <Stack direction="row" spacing={0.75} sx={{ flexWrap: 'wrap' }}>
                    <Chip size="small" label={`Peak RULA ${selectedWorkerSummary.rula.peak ?? '-'}`} />
                    <Chip size="small" label={`Peak REBA ${selectedWorkerSummary.reba.peak ?? '-'}`} />
                    <Chip size="small" label={`${formatDuration(selectedWorkerSummary.high_risk_duration_ms)} exposure`} />
                  </Stack>
                ) : null}
              </Box>
              <Box className="evidenceGrid">
                <Box className="snapshotEvidence">
                  {snapshotUrl ? <img src={snapshotUrl} alt="Event posture evidence" /> : (
                    <Box className="snapshotPlaceholder">
                      <Camera size={28} />
                      <Typography variant="body2" color="text.secondary">No snapshot</Typography>
                    </Box>
                  )}
                  <Button size="small" startIcon={<Eye size={16} />} disabled={!snapshotUrl} onClick={() => setInspectEvidence(true)}>
                    Inspect Snapshot
                  </Button>
                </Box>
                <Box>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>Pose Measurements</Typography>
                  <Box className="reviewValueGrid">
                    {Object.entries(eventDetail.angles).slice(0, 10).map(([name, value]) => (
                      <Box key={name} className="reviewValue">
                        <Typography variant="caption" color="text.secondary">{formatMetricName(name)}</Typography>
                        <Typography sx={{ fontWeight: 700 }}>{typeof value === 'number' ? `${value.toFixed(1)} deg` : '-'}</Typography>
                      </Box>
                    ))}
                  </Box>
                  {eventDetail.assessment_quality.limitations?.length ? (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                      {eventDetail.assessment_quality.limitations.map(formatMetricName).join(' - ')}
                    </Typography>
                  ) : null}
                </Box>
              </Box>

              <Box className="assessmentSection">
                {!canFinalize ? <Alert severity="warning" sx={{ mb: 2 }}>
                  {missingManual.length ? `Incomplete posture: ${missingManual.map(formatMetricName).join(', ')}. Select another observation or enter verified manual measurements.`
                    : 'Verified evidence is unavailable for this posture. Select another observation.'}
                </Alert> : null}
                <Tabs value={assessmentType} onChange={(_, value: 'reba' | 'rula') => setAssessmentType(value)}>
                  <Tab value="reba" label="REBA" />
                  <Tab value="rula" label="RULA" />
                </Tabs>
                <Box className="scoreComparison">
                  <Box>
                    <Typography variant="caption" color="text.secondary">Provisional</Typography>
                    <Typography variant="h6">{provisional?.score ?? '-'}</Typography>
                    <Typography variant="body2">{provisional?.risk_level ?? provisional?.risk ?? 'Not available'}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Reviewed Final</Typography>
                    <Typography variant="h6">{currentReview?.score ?? '-'}</Typography>
                    <Typography variant="body2">{currentReview?.risk_level ?? 'Pending review'}</Typography>
                  </Box>
                </Box>

                <Box className="reviewFormGrid">
                  {missingAngles.map((key) => <TextField key={key} type="number" label={`${formatMetricName(key)} - manual (deg)`}
                    value={reviewForm.angle_overrides[key] ?? ''} disabled={!verifiedEvidence}
                    slotProps={{ htmlInput: { min: -180, max: 180, step: 0.1 } }}
                    onChange={(event) => {
                      const overrides = { ...reviewForm.angle_overrides }
                      if (event.target.value === '') delete overrides[key]
                      else overrides[key] = Number(event.target.value)
                      setReviewForm({ ...reviewForm, angle_overrides: overrides })
                    }} />)}
                  <TextField
                    select
                    label={assessmentType === 'reba' ? 'Load / Force' : 'Force / Load'}
                    value={reviewForm.load_score}
                    onChange={(event) => setReviewForm({ ...reviewForm, load_score: Number(event.target.value) })}
                  >
                    {(assessmentType === 'reba' ? rebaLoadOptions : rulaLoadOptions).map((option) => (
                      <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
                    ))}
                  </TextField>
                  {assessmentType === 'reba' ? (
                    <TextField select label="Coupling" value={reviewForm.coupling_score} onChange={(event) => setReviewForm({ ...reviewForm, coupling_score: Number(event.target.value) })}>
                      {couplingOptions.map((option) => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
                    </TextField>
                  ) : (
                    <TextField select label="Wrist Twist" value={reviewForm.wrist_twist_score} onChange={(event) => setReviewForm({ ...reviewForm, wrist_twist_score: Number(event.target.value) })}>
                      {wristTwistOptions.map((option) => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
                    </TextField>
                  )}
                  <TextField
                    select
                    label={assessmentType === 'reba' ? 'Activity' : 'Muscle Use'}
                    value={reviewForm.activity_score}
                    onChange={(event) => setReviewForm({ ...reviewForm, activity_score: Number(event.target.value) })}
                  >
                    {(assessmentType === 'reba' ? rebaActivityOptions : rulaActivityOptions).map((option) => (
                      <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
                    ))}
                  </TextField>
                  <TextField label="Review Notes" value={reviewForm.notes} onChange={(event) => setReviewForm({ ...reviewForm, notes: event.target.value })} multiline minRows={2} />
                </Box>
                <Button variant="contained" startIcon={<Save size={17} />} disabled={saving || !canFinalize} onClick={saveReview}>
                  Save {assessmentType.toUpperCase()} Review
                </Button>
              </Box>

              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>Score Breakdown</Typography>
                <Box className="reviewValueGrid">
                  {Object.entries(displayedBreakdown).filter(([, value]) => typeof value === 'number').map(([name, value]) => (
                    <Box key={name} className="reviewValue">
                      <Typography variant="caption" color="text.secondary">{formatMetricName(name)}</Typography>
                      <Typography sx={{ fontWeight: 700 }}>{String(value)}</Typography>
                    </Box>
                  ))}
                </Box>
              </Box>
            </Stack>
          ) : (
            <Typography color="text.secondary">Select an event from the timeline.</Typography>
          )}
        </Box>
      </Paper>
    </Stack>
  )
}

const rebaLoadOptions = [
  { value: 0, label: '< 5 kg (+0)' },
  { value: 1, label: '5-10 kg (+1)' },
  { value: 2, label: '> 10 kg (+2)' },
  { value: 3, label: '> 10 kg with shock / rapid force (+3)' },
]
const rulaLoadOptions = [
  { value: 0, label: '< 2 kg, intermittent (+0)' },
  { value: 1, label: '2-10 kg, intermittent (+1)' },
  { value: 2, label: '2-10 kg, static or repeated (+2)' },
  { value: 3, label: '> 10 kg or shock load (+3)' },
]
const couplingOptions = [
  { value: 0, label: 'Good (+0)' },
  { value: 1, label: 'Fair (+1)' },
  { value: 2, label: 'Poor (+2)' },
  { value: 3, label: 'Unacceptable (+3)' },
]
const rebaActivityOptions = [
  { value: 0, label: 'Normal (+0)' },
  { value: 1, label: 'Static, repeated, or rapid change (+1)' },
  { value: 2, label: 'Multiple activity conditions (+2)' },
]
const rulaActivityOptions = [
  { value: 0, label: 'Normal (+0)' },
  { value: 1, label: 'Static or repeated (+1)' },
]
const wristTwistOptions = [
  { value: 1, label: 'Mid-range (+1)' },
  { value: 2, label: 'Near end-range (+2)' },
]

function formFromReview(review: EventReviewRecord): ReviewFormState {
  return {
    load_score: review.manual_inputs.load_score ?? 0,
    coupling_score: review.manual_inputs.coupling_score ?? 0,
    activity_score: review.manual_inputs.activity_score ?? 0,
    wrist_twist_score: review.manual_inputs.wrist_twist_score ?? 1,
    angle_overrides: review.angle_overrides ?? {},
    notes: review.notes ?? '',
  }
}

function formatMetricName(value: string): string {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function ReportsPage({
  token,
  sessions,
}: {
  token: string
  sessions: SessionRecord[]
}) {
  const reportableSessions = sessions.filter((session) => !['preparing', 'running', 'stopping'].includes(session.status))
  const [selectedSessionId, setSelectedSessionId] = useState(reportableSessions[0]?.id ?? '')
  const [reports, setReports] = useState<ReportRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [downloading, setDownloading] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const selectedSession = sessions.find((session) => session.id === selectedSessionId)
  const selectedReport = reports.find((report) => report.session_id === selectedSessionId)

  const loadReports = useCallback(async () => {
    setLoading(true)
    setMessage(null)
    try {
      const rows = await apiRequest<ReportRecord[]>('/api/v1/reports', {}, token)
      setReports(rows)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to load reports.')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    void loadReports()
  }, [loadReports])

  useEffect(() => {
    if (!reportableSessions.some((session) => session.id === selectedSessionId)) {
      setSelectedSessionId(reportableSessions[0]?.id ?? '')
    }
  }, [reportableSessions, selectedSessionId])

  async function generateReport() {
    if (!selectedSessionId) return
    setGenerating(true)
    setMessage(null)
    try {
      const report = await apiRequest<ReportRecord>(
        `/api/v1/reports/sessions/${selectedSessionId}`,
        { method: 'POST' },
        token,
      )
      setReports((current) => [report, ...current.filter((row) => row.id !== report.id)])
      setMessage('Report ready.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to generate report.')
    } finally {
      setGenerating(false)
    }
  }

  async function downloadReport(report: ReportRecord, format: 'pdf' | 'xlsx' | 'zip' = 'pdf') {
    const endpoint = format === 'zip' ? report.archive_url : format === 'xlsx' ? report.excel_url : report.download_url
    if (!endpoint || downloading) return
    setDownloading(`${report.id}:${format}`)
    try {
      const blob = await apiBlob(endpoint, token)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `${report.metadata_json.session_code ?? 'session'}_${report.id}.${format}`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to download report.')
    } finally {
      setDownloading(null)
    }
  }

  function downloadActions(report: ReportRecord) {
    return <Box className="reportDownloads" aria-label="Report downloads">
      {([
        ['pdf', 'Download PDF', report.download_url, <FileText size={16} />],
        ['xlsx', 'Download Excel', report.excel_url, <FileSpreadsheet size={16} />],
        ['zip', 'Download ZIP', report.archive_url, <FileArchive size={16} />],
      ] as const).map(([format, name, endpoint, icon]) => <Tooltip key={format}
        title={endpoint ? name : 'Not included in this older report. Generate a new report.'}>
        <span><Button size="small" variant={format === 'zip' ? 'contained' : 'outlined'} startIcon={icon}
          disabled={!endpoint || downloading !== null} onClick={() => void downloadReport(report, format)}>
          {downloading === `${report.id}:${format}` ? 'Downloading...' : name}
        </Button></span>
      </Tooltip>)}
    </Box>
  }

  return (
    <Stack spacing={3}>
      <PageTitle
        title="Reports"
        action={<Button onClick={() => void loadReports()}>Refresh</Button>}
      />
      <Paper className="panel" elevation={0}>
        <Box className="reportsHeader">
          <Box>
            <Typography variant="h6">Session Documentation</Typography>
          </Box>
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', rowGap: 1 }}>
            <TextField
              select
              size="small"
              label="Session"
              value={selectedSessionId}
              onChange={(event) => setSelectedSessionId(event.target.value)}
              sx={{ minWidth: 220, maxWidth: '100%' }}
            >
              {reportableSessions.map((session) => (
                <MenuItem key={session.id} value={session.id}>
                  {session.session_code} - {session.status}
                </MenuItem>
              ))}
            </TextField>
            <Button
              variant="contained"
              startIcon={<FileText size={16} />}
              disabled={!reportableSessions.some((session) => session.id === selectedSessionId) || generating}
              onClick={generateReport}
            >
              {generating ? 'Generating…' : 'Generate Report'}
            </Button>
          </Stack>
        </Box>
        {selectedSession ? (
          <Box className="reportSessionSummary">
            <Chip size="small" label={selectedSession.status} />
            <Typography variant="body2" color="text.secondary">
              {selectedSession.notes || selectedSession.session_code}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {selectedSession.started_at ? formatDateTime(selectedSession.started_at) : 'Not started'}
            </Typography>
          </Box>
        ) : null}
        {selectedReport ? <Box className="selectedReportDownloads">
          {downloadActions(selectedReport)}
          {!selectedReport.excel_url || !selectedReport.archive_url ? <Alert severity="info" sx={{ mt: 1 }}>
            Excel or ZIP is unavailable in this older report. Select Generate Report to create all formats.
          </Alert> : null}
        </Box> : null}
        {generating || loading ? <LinearProgress sx={{ mt: 2 }} /> : null}
        {message ? <Alert severity={message.includes('Failed') ? 'error' : 'info'} sx={{ mt: 2 }}>{message}</Alert> : null}
      </Paper>

      <Paper className="panel" elevation={0}>
        <Typography variant="h6">Generated Reports</Typography>
        <Divider sx={{ my: 2 }} />
        {reports.length ? (
          <Box className="reportList">
            {reports.map((report) => (
              <Box key={report.id} className="reportRow">
                <FileText size={20} />
                <Box sx={{ minWidth: 0, flex: 1 }}>
                  <Typography sx={{ fontWeight: 700 }}>
                    {report.metadata_json.session_code ?? report.session_id ?? 'Session report'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {report.generated_at ? formatDateTime(report.generated_at) : '-'} - {report.status}
                  </Typography>
                </Box>
                <Box className="reportStats">
                  <Chip size="small" label={`${report.metadata_json.worker_count ?? 0} tracks`} />
                  <Chip size="small" label={`${report.metadata_json.event_count ?? 0} events`} />
                  <Chip size="small" label={`${report.metadata_json.reviewed_assessment_count ?? 0} reviewed`} />
                  <Chip size="small" label={`${report.metadata_json.photo_count ?? 0} photos`} />
                  {Number(report.metadata_json.omitted_photo_count ?? 0) > 0 ? <Chip size="small" color="warning" label={`${report.metadata_json.omitted_photo_count} photo${report.metadata_json.omitted_photo_count === 1 ? '' : 's'} unavailable`} /> : null}
                </Box>
                {downloadActions(report)}
              </Box>
            ))}
          </Box>
        ) : (
          <Typography color="text.secondary">No reports generated yet.</Typography>
        )}
      </Paper>
    </Stack>
  )
}

function SessionList({
  title,
  sessions,
  token,
  refreshData,
}: {
  title: string
  sessions: SessionRecord[]
  token: string
  refreshData: () => Promise<void>
}) {
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  async function deleteSession(session: SessionRecord) {
    if (session.status === 'running') return
    const confirmed = window.confirm(
      `Delete ${session.session_code} and all of its detections, reviews, and snapshots?`,
    )
    if (!confirmed) return
    setDeletingId(session.id)
    setMessage(null)
    try {
      await apiRequest<void>(`/api/v1/sessions/${session.id}`, { method: 'DELETE' }, token)
      await refreshData()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to delete session.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <Paper className="panel" elevation={0}>
      <Typography variant="h6">{title}</Typography>
      <Divider sx={{ my: 2 }} />
      {message ? <Alert severity="error" sx={{ mb: 2 }}>{message}</Alert> : null}
      {sessions.length ? (
        sessions.map((session) => (
          <Box key={session.id} className="rowLine rowFlex" sx={{ flexWrap: 'wrap' }}>
            <Typography sx={{ minWidth: 220 }}>{session.session_code}</Typography>
            <Chip size="small" label={session.status} />
            <Typography color="text.secondary" sx={{ flex: 1 }}>{session.notes ?? ''}</Typography>
            <Button
              color="error"
              size="small"
              startIcon={<Trash2 size={15} />}
              disabled={session.status === 'running' || deletingId === session.id}
              onClick={() => void deleteSession(session)}
            >
              Delete
            </Button>
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
        <Chip size="small" label={formatMetricName(node.status)} color={node.status === 'online' ? 'success' : 'default'} />
        <Chip size="small" label={node.metadata_json.health?.camera_available ? 'Camera ready' : 'Camera unavailable'}
          color={node.metadata_json.health?.camera_available ? 'success' : 'warning'} />
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
