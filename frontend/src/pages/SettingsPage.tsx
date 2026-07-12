import { useState, useEffect } from 'react'
import { useAuth } from '../App'
import { Save, Key, Database, Cpu, Bell, Shield, Check, AlertTriangle, Zap, RefreshCw, XCircle, BookOpen, HardDrive } from 'lucide-react'
import { api } from '../api'

interface SettingsState {
  openaiApiKey: string
  llmModel: string
  fastModel: string
  uploadDir: string
  maxUploadMb: number
  corsOrigins: string
  appName: string
  jwtExpiry: number
  notifyOnGateCreation: boolean
  notifyOnDeadlineWarning: boolean
  autoRunPipeline: boolean
}

const DEFAULT_SETTINGS: SettingsState = {
  openaiApiKey: '',
  llmModel: 'llama-3.3-70b-versatile',
  fastModel: 'llama-3.1-8b-instant',
  uploadDir: '../knowledge_base',
  maxUploadMb: 100,
  corsOrigins: 'http://localhost:5173,http://localhost:3000',
  appName: 'ARISE — Autonomous RFP Intelligence and Sales Engine',
  jwtExpiry: 24,
  notifyOnGateCreation: true,
  notifyOnDeadlineWarning: true,
  autoRunPipeline: false,
}

interface LLMStatus {
  pool_size: number
  available_slots: number
  cooled_down_slots: number
  total_tokens_used: number
  total_calls: number
  slot_stats: { slot: string; calls: number; errors: number; available: boolean; cooldown_remaining_s: number }[]
  tiers: Record<string, { description: string; engine_count: number }>
}

export default function SettingsPage() {
  const { user } = useAuth()
  const [settings, setSettings] = useState<SettingsState>(() => {
    const saved = localStorage.getItem('arise_settings')
    return saved ? { ...DEFAULT_SETTINGS, ...JSON.parse(saved) } : DEFAULT_SETTINGS
  })
  const [saved, setSaved] = useState(false)
  const [activeSection, setActiveSection] = useState('llm')
  const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ status: string; response?: string; error?: string } | null>(null)
  const [applying, setApplying] = useState(false)
  const [kbStats, setKbStats] = useState<any>(null)
  const [kbLoading, setKbLoading] = useState(false)

  const update = (key: keyof SettingsState, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }))
    setSaved(false)
  }

  const saveSettings = () => {
    localStorage.setItem('arise_settings', JSON.stringify(settings))
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  useEffect(() => {
    api.getLLMStatus().then(setLlmStatus).catch(() => {})
    // Load KB stats
    setKbLoading(true)
    api.getKnowledgeStats().then(setKbStats).catch(() => {}).finally(() => setKbLoading(false))
  }, [])

  const applyBYOK = async () => {
    setApplying(true)
    setTestResult(null)
    try {
      const payload: any = {}
      if (settings.openaiApiKey) payload.openai_api_key = settings.openaiApiKey
      const res = await api.setBYOK(payload)
      setLlmStatus(res)
      setTestResult({ status: 'success', response: 'Keys applied successfully' })
    } catch (e: any) {
      setTestResult({ status: 'error', error: e.message })
    }
    setApplying(false)
  }

  const clearBYOK = async () => {
    try {
      const res = await api.clearBYOK()
      setLlmStatus(res)
      update('openaiApiKey', '')
      setTestResult({ status: 'success', response: 'Reverted to server environment keys' })
    } catch (e: any) {
      setTestResult({ status: 'error', error: e.message })
    }
  }

  const testConnection = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await api.testLLM()
      setTestResult(res)
      setLlmStatus(res)
    } catch (e: any) {
      setTestResult({ status: 'error', error: e.message })
    }
    setTesting(false)
  }

  const hasAnyKey = !!settings.openaiApiKey

  // BYOK fields
  const PROVIDER_FIELDS: { key: keyof SettingsState; label: string; placeholder: string; hint: string; color: string }[] = [
    { key: 'openaiApiKey',    label: 'OpenAI API Key', placeholder: 'sk-••••••••••••••••', hint: 'Primary reasoning engine', color: '#10B981' },
  ]

  const sections = [
    { id: 'llm', icon: Cpu, label: 'LLM & API Keys' },
    { id: 'knowledge', icon: BookOpen, label: 'Knowledge & RAG' },
    { id: 'storage', icon: Database, label: 'Storage & Upload' },
    { id: 'notifications', icon: Bell, label: 'Notifications' },
    { id: 'security', icon: Shield, label: 'Security' },
  ]

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2 style={{ fontSize: 24, fontWeight: 800 }}>Settings</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
            Configure platform settings and API integrations
          </p>
        </div>
        <button className="btn btn-primary" onClick={saveSettings} style={{ gap: 6 }}>
          {saved ? <><Check size={16} /> Saved!</> : <><Save size={16} /> Save Changes</>}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 20 }}>
        {/* Section Nav */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {sections.map(s => (
            <button key={s.id} onClick={() => setActiveSection(s.id)}
              className={`nav-item ${activeSection === s.id ? 'active' : ''}`}
              style={{ textAlign: 'left', fontSize: 13 }}>
              <s.icon size={16} className="nav-icon" /> {s.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div>
          {activeSection === 'llm' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

              {/* AI Engine Pool Status Card */}
              <div className="glass-card" style={{ padding: 16 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Zap size={16} style={{ color: 'var(--accent-primary)' }} />
                  AI Engine Pool
                </h3>
                {llmStatus ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                    <div style={{ padding: 12, background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Active Engines</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: llmStatus.pool_size === 0 ? 'var(--status-danger)' : 'var(--status-success)' }}>
                        {llmStatus.pool_size} slots
                      </div>
                    </div>
                    <div style={{ padding: 12, background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>AI Calls</div>
                      <div style={{ fontSize: 16, fontWeight: 700 }}>{llmStatus.total_calls.toLocaleString()}</div>
                    </div>
                    <div style={{ padding: 12, background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Tokens Used</div>
                      <div style={{ fontSize: 16, fontWeight: 700 }}>{llmStatus.total_tokens_used.toLocaleString()}</div>
                    </div>
                  </div>
                ) : (
                  <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading AI engine status…</div>
                )}

                {/* Show total active slots — no vendor names */}
                {llmStatus && llmStatus.pool_size > 0 && (
                  <div style={{ marginTop: 12, padding: '8px 12px', borderRadius: 'var(--radius-sm)', background: 'rgba(34,197,94,0.06)', border: '1px solid rgba(34,197,94,0.15)', fontSize: 12, color: 'var(--status-success)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span>✓</span>
                    <span>{llmStatus.pool_size} AI inference {llmStatus.pool_size === 1 ? 'slot' : 'slots'} active · auto-failover enabled</span>
                  </div>
                )}
              </div>

              {/* BYOK Section */}
              <div className="glass-card">
                <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 6 }}>
                  <Key size={18} style={{ display: 'inline', marginRight: 8, verticalAlign: 'text-bottom' }} />
                  Bring Your Own Key
                </h3>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 20, lineHeight: 1.6 }}>
                  Provide your own API keys for any provider. They override the server's environment keys for your session.
                  You only need <strong>one</strong> provider — the system routes all agents through available providers.
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  {PROVIDER_FIELDS.map(pf => (
                    <div className="form-group" key={pf.key}>
                      <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ width: 8, height: 8, borderRadius: 4, background: pf.color, flexShrink: 0 }} />
                        {pf.label}
                      </label>
                      <div style={{ position: 'relative' }}>
                        <input className="form-input" type="password" value={settings[pf.key] as string}
                          onChange={e => update(pf.key, e.target.value)}
                          placeholder={pf.placeholder} style={{ paddingLeft: 36, fontSize: 12 }} />
                        <Key size={13} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                      </div>
                      <div className="form-hint">{pf.hint}</div>
                    </div>
                  ))}
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', gap: 8, marginTop: 20 }}>
                  <button id="apply-byok-btn" className="btn btn-primary" onClick={applyBYOK} disabled={applying || !hasAnyKey}
                    style={{ fontSize: 12, gap: 6, padding: '8px 18px' }}>
                    {applying ? <><RefreshCw size={13} className="spin" /> Applying...</> : <><Key size={13} /> Apply Keys</>}
                  </button>
                  <button id="test-llm-btn" className="btn btn-ghost" onClick={testConnection} disabled={testing}
                    style={{ fontSize: 12, gap: 6, padding: '8px 18px', border: '1px solid var(--border-subtle)' }}>
                    {testing ? <><RefreshCw size={13} className="spin" /> Testing...</> : <><Zap size={13} /> Test Connection</>}
                  </button>
                  <button id="clear-byok-btn" className="btn btn-ghost" onClick={clearBYOK}
                    style={{ fontSize: 12, gap: 6, padding: '8px 18px', border: '1px solid var(--border-subtle)', color: 'var(--status-danger)' }}>
                    <XCircle size={13} /> Revert to Env Keys
                  </button>
                </div>

                {/* Test Result */}
                {testResult && (
                  <div style={{
                    marginTop: 14, padding: 12, borderRadius: 'var(--radius-sm)',
                    background: testResult.status === 'success' ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
                    border: `1px solid ${testResult.status === 'success' ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
                  }}>
                    <div style={{ fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6,
                      color: testResult.status === 'success' ? 'var(--status-success)' : 'var(--status-danger)' }}>
                      {testResult.status === 'success' ? <Check size={14} /> : <AlertTriangle size={14} />}
                      {testResult.status === 'success' ? 'Success' : 'Failed'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                      {testResult.response || testResult.error}
                    </div>
                  </div>
                )}
              </div>

              {/* AI Intelligence Configuration */}
              <div className="glass-card">
                <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>
                  <Cpu size={18} style={{ display: 'inline', marginRight: 8, verticalAlign: 'text-bottom' }} />
                  AI Configuration
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div className="form-group">
                    <label className="form-label">Intelligence Mode</label>
                    <select className="form-input" defaultValue="balanced"
                      onChange={() => {/* tier routing is automatic */}}>
                      <option value="balanced">Balanced — optimal speed and quality for all tasks</option>
                      <option value="quality">Quality-first — maximum reasoning for critical decisions</option>
                      <option value="speed">Speed-first — fastest inference for high-volume pipelines</option>
                    </select>
                    <div className="form-hint">ARISE automatically routes each agent to the most appropriate engine for its task complexity. This setting adjusts the overall balance.</div>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Auto-Run Pipeline</label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                      <input type="checkbox" checked={settings.autoRunPipeline}
                        onChange={e => update('autoRunPipeline', e.target.checked)}
                        style={{ width: 18, height: 18, accentColor: 'var(--accent-primary)' }} />
                      <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                        Automatically run all pipeline agents sequentially after document upload
                      </span>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSection === 'knowledge' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* RAG Cache Stats */}
              <div className="glass-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <h3 style={{ fontSize: 15, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Zap size={16} style={{ color: '#8B5CF6' }} /> RAG Embedding Cache
                  </h3>
                  <button className="btn btn-ghost" style={{ fontSize: 12 }}
                    onClick={() => { setKbLoading(true); api.getKnowledgeStats().then(setKbStats).catch(() => {}).finally(() => setKbLoading(false)) }}>
                    <RefreshCw size={13} /> Refresh
                  </button>
                </div>
                {kbLoading && <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading stats…</div>}
                {kbStats && (
                  <>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 16 }}>
                      {[
                        { label: 'Cached Chunks', value: kbStats.rag?.total_chunks ?? 0, color: '#8B5CF6' },
                        { label: 'Total Documents', value: kbStats.db?.total_documents ?? 0, color: '#3B82F6' },
                        { label: 'KB Size', value: kbStats.db?.total_size_bytes >= 1e6
                          ? `${(kbStats.db.total_size_bytes / 1e6).toFixed(1)} MB`
                          : `${((kbStats.db?.total_size_bytes || 0) / 1e3).toFixed(0)} KB`, color: '#10B981' },
                      ].map(s => (
                        <div key={s.label} style={{ padding: 12, background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                          <div style={{ fontSize: 22, fontWeight: 800, color: s.color }}>{s.value}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{s.label}</div>
                        </div>
                      ))}
                    </div>
                    {/* By collection */}
                    <h4 style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Collections</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {Object.entries(kbStats.collections || {}).map(([col, info]: [string, any]) => (
                        <div key={col} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-glass)', border: '1px solid var(--border-subtle)' }}>
                          <HardDrive size={12} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                          <span style={{ fontSize: 12, fontWeight: 500, flex: 1 }}>{info.name}</span>
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{info.desc}</span>
                          <span style={{ fontSize: 11, fontWeight: 700, padding: '1px 8px', borderRadius: 10,
                            background: info.doc_count > 0 ? 'rgba(5,150,105,0.1)' : 'var(--bg-tertiary)',
                            color: info.doc_count > 0 ? '#059669' : 'var(--text-muted)' }}>
                            {info.doc_count} doc{info.doc_count !== 1 ? 's' : ''}
                          </span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {activeSection === 'storage' && (
            <div className="glass-card">
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>
                <Database size={18} style={{ display: 'inline', marginRight: 8, verticalAlign: 'text-bottom' }} />
                Storage & Upload
              </h3>

              <div className="form-group">
                <label className="form-label">Upload Directory</label>
                <input className="form-input" value={settings.uploadDir}
                  onChange={e => update('uploadDir', e.target.value)} />
              </div>
              <div className="form-group" style={{ marginTop: 16 }}>
                <label className="form-label">Max Upload Size (MB)</label>
                <input className="form-input" type="number" value={settings.maxUploadMb}
                  onChange={e => update('maxUploadMb', Number(e.target.value))} />
              </div>
              <div className="form-group" style={{ marginTop: 16 }}>
                <label className="form-label">Application Name</label>
                <input className="form-input" value={settings.appName}
                  onChange={e => update('appName', e.target.value)} />
              </div>
            </div>
          )}

          {activeSection === 'notifications' && (
            <div className="glass-card">
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>
                <Bell size={18} style={{ display: 'inline', marginRight: 8, verticalAlign: 'text-bottom' }} />
                Notifications
              </h3>

              {[
                { key: 'notifyOnGateCreation' as const, label: 'HITL Gate Created', desc: 'Notify when a new review gate is created' },
                { key: 'notifyOnDeadlineWarning' as const, label: 'Deadline Warning', desc: 'Alert when bid deadlines enter high-risk zone' },
              ].map(item => (
                <div key={item.key} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '14px 0', borderBottom: '1px solid var(--border-subtle)',
                }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>{item.label}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{item.desc}</div>
                  </div>
                  <input type="checkbox" checked={settings[item.key] as boolean}
                    onChange={e => update(item.key, e.target.checked)}
                    style={{ width: 20, height: 20, accentColor: 'var(--accent-primary)' }} />
                </div>
              ))}
            </div>
          )}

          {activeSection === 'security' && (
            <div className="glass-card">
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>
                <Shield size={18} style={{ display: 'inline', marginRight: 8, verticalAlign: 'text-bottom' }} />
                Security
              </h3>

              <div className="form-group">
                <label className="form-label">JWT Token Expiry (hours)</label>
                <input className="form-input" type="number" value={settings.jwtExpiry}
                  onChange={e => update('jwtExpiry', Number(e.target.value))} />
              </div>
              <div className="form-group" style={{ marginTop: 16 }}>
                <label className="form-label">CORS Origins</label>
                <input className="form-input" value={settings.corsOrigins}
                  onChange={e => update('corsOrigins', e.target.value)} />
                <div className="form-hint">Comma-separated list of allowed origins</div>
              </div>

              <div style={{ marginTop: 24, padding: 16, background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Current Session</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.8 }}>
                  <div>User: <strong style={{ color: 'var(--text-primary)' }}>{user?.name}</strong></div>
                  <div>Role: <strong style={{ color: 'var(--text-primary)' }}>{user?.role?.replace(/_/g, ' ')}</strong></div>
                  <div>Email: <strong style={{ color: 'var(--text-primary)' }}>{user?.email}</strong></div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
