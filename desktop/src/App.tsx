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
  LinearProgress,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Paper,
  Stack,
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
  RadioReceiver,
  Settings,
  ShieldCheck,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import './App.css'
import {
  apiRequest,
  liveWebSocketUrl,
} from './api'
import type { AuthTokens, CameraNode, PairingToken, SessionRecord } from './api'
import type { DiscoveredDevice } from './types'

const drawerWidth = 248

const navItems = [
  { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { key: 'live', label: 'Live Assessment', icon: Activity },
  { key: 'review', label: 'Session Review', icon: ClipboardCheck },
  { key: 'history', label: 'History', icon: History },
  { key: 'reports', label: 'Reports', icon: FileText },
  { key: 'settings', label: 'Settings', icon: Settings },
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
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking')
  const [error, setError] = useState<string | null>(null)

  const token = tokens?.access_token ?? null

  useEffect(() => {
    void refreshBackendStatus()
  }, [])

  const refreshData = useCallback(async () => {
    if (!token) return
    try {
      const [nodes, sessionRows] = await Promise.all([
        apiRequest<CameraNode[]>('/api/v1/camera-nodes', {}, token),
        apiRequest<SessionRecord[]>('/api/v1/sessions', {}, token),
      ])
      setCameraNodes(nodes)
      setSessions(sessionRows)
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
            token={tokens.access_token}
            cameraNodes={cameraNodes}
            sessions={sessions}
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
  token,
  cameraNodes,
  sessions,
  refreshData,
}: {
  activePage: string
  token: string
  cameraNodes: CameraNode[]
  sessions: SessionRecord[]
  refreshData: () => Promise<void>
}) {
  if (activePage === 'live') {
    return <LiveAssessment token={token} sessions={sessions} />
  }
  if (activePage === 'settings') {
    return <SettingsPage token={token} cameraNodes={cameraNodes} refreshData={refreshData} />
  }
  if (activePage === 'history') {
    return <SessionList title="History" sessions={sessions} />
  }
  if (activePage === 'reports') {
    return <Placeholder title="Reports" icon={FileText} />
  }
  if (activePage === 'review') {
    return <Placeholder title="Session Review" icon={ClipboardCheck} />
  }
  return <Dashboard cameraNodes={cameraNodes} sessions={sessions} refreshData={refreshData} />
}

function Dashboard({
  cameraNodes,
  sessions,
  refreshData,
}: {
  cameraNodes: CameraNode[]
  sessions: SessionRecord[]
  refreshData: () => Promise<void>
}) {
  const running = sessions.filter((session) => session.status === 'running').length
  const paired = cameraNodes.length

  return (
    <Stack spacing={3}>
      <PageTitle title="Dashboard" action={<Button onClick={refreshData}>Refresh</Button>} />
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

function LiveAssessment({ token, sessions }: { token: string; sessions: SessionRecord[] }) {
  const [sessionId, setSessionId] = useState(sessions[0]?.session_code ?? '')
  const [events, setEvents] = useState<string[]>([])
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    if (!sessionId) return
    const ws = new WebSocket(liveWebSocketUrl(sessionId, token))
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (event) => {
      setEvents((current) => [event.data, ...current].slice(0, 20))
    }
    return () => ws.close()
  }, [sessionId, token])

  return (
    <Stack spacing={3}>
      <PageTitle title="Live Assessment" action={<StatusChip status={connected ? 'online' : 'offline'} />} />
      <Paper className="panel" elevation={0}>
        <Stack direction="row" spacing={2}>
          <TextField
            select
            label="Session"
            value={sessionId}
            onChange={(event) => setSessionId(event.target.value)}
            sx={{ minWidth: 320 }}
          >
            {sessions.map((session) => (
              <MenuItem key={session.id} value={session.session_code}>
                {session.session_code}
              </MenuItem>
            ))}
          </TextField>
        </Stack>
        <Divider sx={{ my: 2 }} />
        <Box className="eventFeed">
          {events.length ? (
            events.map((event, index) => <pre key={`${index}-${event.slice(0, 12)}`}>{event}</pre>)
          ) : (
            <Typography color="text.secondary">Waiting for edge stream.</Typography>
          )}
        </Box>
      </Paper>
    </Stack>
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

  async function createPairing() {
    setLoading(true)
    try {
      const nextPairing = await apiRequest<PairingToken>(
        '/api/v1/device-pairings',
        { method: 'POST', body: JSON.stringify({}) },
        token,
      )
      setPairing(nextPairing)
    } finally {
      setLoading(false)
    }
  }

  async function discoverDevices() {
    setLoading(true)
    try {
      const discovered = await window.ergoquipt?.discoverDevices()
      setDevices(discovered ?? [])
    } finally {
      setLoading(false)
    }
  }

  return (
    <Stack spacing={3}>
      <PageTitle title="Settings" action={<Button onClick={refreshData}>Refresh</Button>} />
      <Paper className="panel" elevation={0}>
        <Stack direction="row" spacing={2}>
          <Button variant="contained" startIcon={<RadioReceiver size={18} />} onClick={discoverDevices}>
            Scan devices
          </Button>
          <Button variant="outlined" startIcon={<ShieldCheck size={18} />} onClick={createPairing}>
            Create pairing code
          </Button>
        </Stack>
        {loading ? <LinearProgress sx={{ mt: 2 }} /> : null}
        {pairing ? (
          <Alert severity="success" sx={{ mt: 2 }}>
            Pairing code: <strong>{pairing.pairing_code}</strong>
          </Alert>
        ) : null}
      </Paper>
      <DeviceTable cameraNodes={cameraNodes} />
      <Paper className="panel" elevation={0}>
        <Typography variant="h6">Discovered Devices</Typography>
        <Divider sx={{ my: 2 }} />
        {devices.length ? (
          devices.map((device) => (
            <Stack key={`${device.address}:${device.port}`} direction="row" spacing={2} className="rowLine">
              <Typography>{device.hostname}</Typography>
              <Chip size="small" label={device.address} />
              <Chip size="small" label={device.status} />
            </Stack>
          ))
        ) : (
          <Typography color="text.secondary">No local edge devices discovered.</Typography>
        )}
      </Paper>
    </Stack>
  )
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

function DeviceTable({ cameraNodes }: { cameraNodes: CameraNode[] }) {
  return (
    <Paper className="panel" elevation={0}>
      <Typography variant="h6">Camera Nodes</Typography>
      <Divider sx={{ my: 2 }} />
      {cameraNodes.length ? (
        cameraNodes.map((node) => (
          <Box key={node.id} className="rowLine rowFlex">
            <Camera size={18} />
            <Typography sx={{ minWidth: 120 }}>{node.cam_id}</Typography>
            <Typography sx={{ minWidth: 180 }}>{node.hostname ?? '-'}</Typography>
            <Chip size="small" label={node.status} color={node.status === 'online' ? 'success' : 'default'} />
          </Box>
        ))
      ) : (
        <Typography color="text.secondary">No paired camera nodes.</Typography>
      )}
    </Paper>
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
