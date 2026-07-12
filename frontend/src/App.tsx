import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect, createContext, useContext } from 'react'
import { api } from './api'
import Dashboard from './pages/Dashboard'
import BidWorkspace from './pages/BidWorkspace'
import BidDetail from './pages/BidDetail'
import AgentDetail from './pages/AgentDetail'
import KnowledgeBase from './pages/KnowledgeBase'
import Login from './pages/Login'
import ExecutiveDashboard from './pages/ExecutiveDashboard'
import SettingsPage from './pages/SettingsPage'
import HITLGates from './pages/HITLGates'
import OrgView from './pages/OrgView'
import CommandPalette from './components/CommandPalette'
import TelemetryPanel from './components/TelemetryPanel'
import { LayoutDashboard, FolderKanban, Database, BarChart3, LogOut, Settings, ShieldCheck, Building2, Bell, Search, Activity } from 'lucide-react'

interface User { id: string; email: string; name: string; role: string; avatar: string }
interface AuthCtx { user: User | null; login: (email: string, pw: string) => Promise<void>; logout: () => void }
const AuthContext = createContext<AuthCtx>({ user: null, login: async () => {}, logout: () => {} })
export const useAuth = () => useContext(AuthContext)

function App() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      api.getMe().then(u => setUser(u)).catch(() => localStorage.removeItem('token')).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (email: string, pw: string) => {
    const res = await api.login(email, pw)
    localStorage.setItem('token', res.token)
    setUser(res.user)
  }
  const logout = () => { localStorage.removeItem('token'); setUser(null) }

  if (loading) return <div className="loading-page"><div className="loading-spinner" /><span style={{color:'var(--text-muted)'}}>Loading platform...</span></div>

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {!user ? <Login /> : <AuthenticatedApp />}
    </AuthContext.Provider>
  )
}

function AuthenticatedApp() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/bids', icon: FolderKanban, label: 'Bid Workspace' },
    { path: '/hitl', icon: ShieldCheck, label: 'HITL Gates' },
    { path: '/knowledge', icon: Database, label: 'Knowledge Base' },
    { path: '/executive', icon: BarChart3, label: 'Executive View' },
    { path: '/org', icon: Building2, label: 'Organization' },
  ]
  const [pendingGates, setPendingGates] = useState(0)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [telemetryOpen, setTelemetryOpen] = useState(false)

  // Global Ctrl+K / Cmd+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setPaletteOpen(p => !p)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // Ctrl+Shift+T — toggle telemetry panel
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'T') {
        e.preventDefault()
        setTelemetryOpen(p => !p)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  useEffect(() => {
    const fetchPending = () =>
      api.getPendingGates().then((g: any[]) => setPendingGates(g?.length || 0)).catch(() => {})
    fetchPending()
    const t = setInterval(fetchPending, 30_000)  // refresh every 30s
    return () => clearInterval(t)
  }, [])

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  // Dynamic page title
  let pageTitle = 'Dashboard'
  if (location.pathname.startsWith('/bids/') && location.pathname.includes('/agent/')) {
    pageTitle = 'Agent Detail'
  } else if (location.pathname.startsWith('/bids/') && location.pathname !== '/bids') {
    pageTitle = 'Bid Detail'
  } else if (location.pathname === '/settings') {
    pageTitle = 'Settings'
  } else {
    pageTitle = navItems.find(n => isActive(n.path))?.label || 'Dashboard'
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <img src="/arise-mark.svg" alt="ARISE" style={{ height: 32, width: 32, objectFit: 'contain', flexShrink: 0, borderRadius: 7 }} />
            <div style={{ paddingLeft: 10, minWidth: 0 }}>
              <div style={{fontSize:18,fontWeight:900,lineHeight:1.2,letterSpacing:'2.5px',background:'linear-gradient(90deg,#06B6D4,#3B82F6,#8B5CF6)',WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent'}}>ARISE</div>
              <div style={{fontSize:9,color:'#3B82F6',letterSpacing:'0.5px',lineHeight:1.3,marginTop:1,fontWeight:700}}>Autonomous RFP Intelligence</div>
            </div>
          </div>
        </div>
        <nav className="sidebar-nav">
          <div className="nav-section-label">Main</div>
          {navItems.map(item => (
            <button key={item.path} className={`nav-item ${isActive(item.path) ? 'active' : ''}`} onClick={() => navigate(item.path)}>
              <item.icon size={18} className="nav-icon" />
              {item.label}
              {/* HITL pending badge */}
              {item.path === '/hitl' && pendingGates > 0 && (
                <span style={{
                  marginLeft:'auto', minWidth:18, height:18, borderRadius:9,
                  background:'var(--status-danger)', color:'#fff',
                  fontSize:10, fontWeight:700, display:'flex', alignItems:'center',
                  justifyContent:'center', padding:'0 4px',
                }}>{pendingGates > 9 ? '9+' : pendingGates}</span>
              )}
            </button>
          ))}
          <div className="nav-section-label">System</div>
          <button className={`nav-item ${location.pathname === '/settings' ? 'active' : ''}`} onClick={() => navigate('/settings')}>
            <Settings size={18} className="nav-icon" />Settings
          </button>
        </nav>
        <div className="sidebar-footer">
          <div className="user-card">
            <div className="user-avatar">{user?.avatar || '??'}</div>
            <div className="user-info">
              <div className="user-name">{user?.name}</div>
              <div className="user-role">{user?.email}</div>
            </div>
            <button onClick={logout} style={{background:'none',border:'none',color:'var(--text-muted)',padding:4}} title="Logout"><LogOut size={16} /></button>
          </div>
        </div>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <h1 className="topbar-title">{pageTitle}</h1>
          <div className="topbar-actions">
            {/* Live telemetry toggle */}
            <button
              className="btn btn-ghost"
              style={{ fontSize: 12, gap: 5, padding: '5px 10px', position: 'relative' }}
              onClick={() => setTelemetryOpen(p => !p)}
              title="Live Telemetry (Ctrl+Shift+T)">
              <Activity size={14} style={{ color: telemetryOpen ? '#10B981' : undefined }} />
              <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>Monitor</span>
              {/* Live pulse dot */}
              <span style={{
                position: 'absolute', top: 4, right: 4, width: 5, height: 5, borderRadius: '50%',
                background: '#10B981',
                boxShadow: '0 0 0 0 rgba(16,185,129,0.4)',
                animation: 'telemetryPulse 2s infinite',
              }} />
            </button>
            <button className="btn btn-ghost" style={{ fontSize:12, gap:5, padding:'5px 10px' }}
              onClick={() => setPaletteOpen(true)} title="Search (Ctrl+K)">
              <Search size={14} />
              <span style={{ color:'var(--text-muted)', fontSize:11 }}>Search</span>
              <kbd style={{ fontSize:9, padding:'1px 5px', borderRadius:4, background:'var(--bg-tertiary)',
                border:'1px solid var(--border-subtle)', fontFamily:'var(--font-mono)', color:'var(--text-muted)' }}>⌘K</kbd>
            </button>
            {/* Notification bell */}
            {pendingGates > 0 && (
              <button className="btn btn-ghost" style={{ position:'relative', padding:'6px 10px' }}
                onClick={() => navigate('/hitl')} title={`${pendingGates} pending HITL gate${pendingGates > 1 ? 's' : ''}`}>
                <Bell size={16} />
                <span style={{
                  position:'absolute', top:2, right:2, width:14, height:14,
                  background:'var(--status-danger)', borderRadius:7,
                  fontSize:9, fontWeight:700, color:'#fff',
                  display:'flex', alignItems:'center', justifyContent:'center',
                }}>{pendingGates > 9 ? '9+' : pendingGates}</span>
              </button>
            )}
          </div>
        </header>
        <div className="page-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/bids" element={<BidWorkspace />} />
            <Route path="/bids/:bidId" element={<BidDetail />} />
            <Route path="/bids/:bidId/agent/:agentName" element={<AgentDetail />} />
            <Route path="/hitl" element={<HITLGates />} />
            <Route path="/knowledge" element={<KnowledgeBase />} />
            <Route path="/executive" element={<ExecutiveDashboard />} />
            <Route path="/org" element={<OrgView />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </div>
      </main>
      {/* Global Command Palette — accessible from any page */}
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      {/* Live Telemetry Panel */}
      <TelemetryPanel open={telemetryOpen} onClose={() => setTelemetryOpen(false)} />
    </div>
  )
}

export default App
