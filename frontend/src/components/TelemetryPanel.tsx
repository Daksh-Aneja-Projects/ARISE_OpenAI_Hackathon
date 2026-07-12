/**
 * TelemetryPanel â€” Live backend telemetry sidebar
 *
 * A collapsible right-side drawer that connects to /api/ws/telemetry
 * and renders live charts + event log updating every second:
 *
 *   - Agent calls/sec sparkline + per-agent bar chart
 *   - LLM tokens/sec sparkline
 *   - Request throughput sparkline
 *   - Active pipeline list (live)
 *   - Rolling 30-entry event log
 *
 * Uses recharts (already in project).
 * Opens via toggle button in topbar or Ctrl+Shift+T.
 */
import { useState, useEffect, useCallback } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import {
  Activity, Zap, Cpu, X, ChevronRight, ChevronLeft,
  Clock, AlertTriangle, CheckCircle, Loader2, Radio,
} from 'lucide-react'
import { useReliableWebSocket, buildWsUrl } from '../hooks/useReliableWebSocket'

// â”€â”€â”€ Types â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
interface AgentStat { calls: number; errors: number; avg_ms: number; error_rate: number }
interface ActivePipeline { bid_id: string; stage: string; elapsed_s: number }
interface TelEvent { t: number; type: string; agent?: string; bid_id?: string; duration_ms?: number; ok?: boolean; provider?: string; tokens?: number; stage?: string; status?: string; msg?: string }
interface TelSnapshot {
  ts: number
  uptime_seconds: number
  totals: { agent_calls: number; llm_calls: number; tokens_in: number; tokens_out: number; pipeline_runs: number; errors: number; requests: number }
  rates: { agent_calls_sec: number; llm_calls_sec: number; tokens_sec: number; errors_sec: number; requests_sec: number }
  series: { agent_calls: number[]; llm_calls: number[]; tokens: number[]; errors: number[]; requests: number[] }
  agents: Record<string, AgentStat>
  active_pipelines: ActivePipeline[]
  providers: Record<string, number>
  events: TelEvent[]
}

// â”€â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function fmtUptime(s: number) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60
  return h > 0 ? `${h}h ${m}m` : m > 0 ? `${m}m ${sec}s` : `${sec}s`
}
function seriesToPoints(arr: number[]) {
  return arr.map((v, i) => ({ i, v }))
}
function eventIcon(type: string) {
  if (type === 'agent') return 'ðŸ¤–'
  if (type === 'llm') return 'âš¡'
  if (type === 'pipeline_start') return 'â–¶'
  if (type === 'pipeline_end') return 'â– '
  if (type === 'stage') return 'â†’'
  if (type === 'error') return 'âš '
  return 'â€¢'
}
function eventColor(type: string) {
  if (type === 'error') return '#EF4444'
  if (type === 'pipeline_start') return '#3B82F6'
  if (type === 'pipeline_end') return '#10B981'
  if (type === 'agent') return '#8B5CF6'
  if (type === 'llm') return '#F59E0B'
  return '#9CA3AF'
}
function eventLabel(ev: TelEvent) {
  if (ev.type === 'agent') return `${ev.agent} ${ev.ok ? 'âœ“' : 'âœ-'} ${ev.duration_ms}ms`
  if (ev.type === 'llm') return `AI Engine Â· ${ev.tokens ?? 0} tokens`
  if (ev.type === 'pipeline_start') return `Pipeline started ${ev.bid_id?.slice(-6)}`
  if (ev.type === 'pipeline_end') return `Pipeline ${ev.status} ${ev.bid_id?.slice(-6)}`
  if (ev.type === 'stage') return `Stage: ${ev.stage}`
  if (ev.type === 'error') return `Error [${ev.agent || ''}]: ${ev.msg}`
  return ev.type
}

const PANEL_WIDTH = 380

// â”€â”€â”€ Sparkline card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function Spark({ label, series, color, unit, current }: {
  label: string; series: number[]; color: string; unit: string; current: number
}) {
  const pts = seriesToPoints(series.slice(-40))
  return (
    <div style={{ marginBottom: 10, background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', padding: '8px 10px', border: '1px solid var(--border-subtle)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
        <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px', fontWeight: 600 }}>{label}</span>
        <span style={{ fontSize: 16, fontWeight: 800, color, fontFamily: 'var(--font-mono)' }}>
          {current}<span style={{ fontSize: 9, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 2 }}>{unit}</span>
        </span>
      </div>
      <ResponsiveContainer width="100%" height={36}>
        <AreaChart data={pts} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={`grad-${label}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.5}
            fill={`url(#grad-${label})`} dot={false} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// â”€â”€â”€ Main Panel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export default function TelemetryPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [snap, setSnap] = useState<TelSnapshot | null>(null)
  const [tab, setTab] = useState<'metrics' | 'agents' | 'events'>('metrics')
  const handleTelemetry = useCallback((data: unknown) => {
    try { setSnap(data as TelSnapshot) } catch {}
  }, [])

  const wsUrl = buildWsUrl('/api/ws/telemetry')
  const { status } = useReliableWebSocket(wsUrl, handleTelemetry, {
    enabled: open,
    maxRetries: 10,
    baseDelayMs: 1000,
  })
  const connected = status === 'open'

  if (!open) return null

  const totals = snap?.totals
  const rates = snap?.rates
  const series = snap?.series

  return (
    <>
      {/* Backdrop â€” click to close */}
      <div
        onClick={onClose}
        style={{ position: 'fixed', inset: 0, zIndex: 8998, background: 'transparent' }}
      />

      {/* Panel */}
      <div style={{
        position: 'fixed', top: 0, right: 0, height: '100vh', width: PANEL_WIDTH,
        background: 'var(--bg-secondary)', borderLeft: '1px solid var(--border-subtle)',
        boxShadow: '-8px 0 40px rgba(0,0,0,0.08)', zIndex: 8999,
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
        animation: 'slideInRight 200ms cubic-bezier(0.4,0,0.2,1)',
      }}>

        {/* Header */}
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Radio size={14} style={{ color: connected ? '#10B981' : '#9CA3AF',
                animation: connected ? 'pulse 2s infinite' : 'none' }} />
              <span style={{ fontSize: 13, fontWeight: 800 }}>Live Telemetry</span>
            </div>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center' }}>
              {snap && (
                <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  â†‘{fmtUptime(snap.uptime_seconds)}
                </span>
              )}
              <span style={{
                fontSize: 9, padding: '2px 7px', borderRadius: 10, fontWeight: 700,
                background: connected ? 'rgba(16,185,129,0.1)' : 'rgba(156,163,175,0.1)',
                color: connected ? '#10B981' : '#9CA3AF',
              }}>{connected ? 'LIVE' : 'CONNECTINGâ€¦'}</span>
              <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: 'var(--text-muted)', display: 'flex' }}>
                <X size={16} />
              </button>
            </div>
          </div>

          {/* KPI row */}
          {snap && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, marginTop: 12 }}>
              {[
                { label: 'Agents', value: totals?.agent_calls ?? 0, color: '#8B5CF6' },
                { label: 'LLM', value: totals?.llm_calls ?? 0, color: '#F59E0B' },
                { label: 'Errors', value: totals?.errors ?? 0, color: '#EF4444' },
                { label: 'Pipelines', value: totals?.pipeline_runs ?? 0, color: '#3B82F6' },
              ].map(k => (
                <div key={k.label} style={{ textAlign: 'center', padding: '6px 4px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: 16, fontWeight: 800, color: k.color, fontFamily: 'var(--font-mono)' }}>{k.value}</div>
                  <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.3px' }}>{k.label}</div>
                </div>
              ))}
            </div>
          )}

          {/* Tab bar */}
          <div style={{ display: 'flex', gap: 2, marginTop: 10 }}>
            {(['metrics', 'agents', 'events'] as const).map(t => (
              <button key={t} onClick={() => setTab(t)} style={{
                flex: 1, padding: '5px 0', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer',
                fontSize: 11, fontWeight: tab === t ? 700 : 400, transition: 'all 150ms',
                background: tab === t ? 'var(--accent-primary, #0066FF)' : 'var(--bg-tertiary)',
                color: tab === t ? '#fff' : 'var(--text-muted)',
              }}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 14 }}>

          {/* â”€â”€ Metrics tab â”€â”€ */}
          {tab === 'metrics' && snap && (
            <div>
              <Spark label="Agent Calls / sec" series={series?.agent_calls ?? []}
                color="#8B5CF6" unit="/s" current={rates?.agent_calls_sec ?? 0} />
              <Spark label="LLM Calls / sec" series={series?.llm_calls ?? []}
                color="#F59E0B" unit="/s" current={rates?.llm_calls_sec ?? 0} />
              <Spark label="Tokens / sec" series={series?.tokens ?? []}
                color="#06B6D4" unit="tok/s" current={rates?.tokens_sec ?? 0} />
              <Spark label="HTTP Requests / sec" series={series?.requests ?? []}
                color="#3B82F6" unit="/s" current={rates?.requests_sec ?? 0} />
              <Spark label="Errors / sec" series={series?.errors ?? []}
                color="#EF4444" unit="/s" current={rates?.errors_sec ?? 0} />

              {/* Active pipelines */}
              {snap.active_pipelines.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 }}>
                    Active Pipelines ({snap.active_pipelines.length})
                  </div>
                  {snap.active_pipelines.map(p => (
                    <div key={p.bid_id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', marginBottom: 4, background: 'rgba(59,130,246,0.05)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(59,130,246,0.15)' }}>
                      <Loader2 size={11} style={{ color: '#3B82F6', animation: 'spin 1s linear infinite', flexShrink: 0 }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 11, fontWeight: 600, fontFamily: 'var(--font-mono)' }}>â€¦{p.bid_id.slice(-8)}</div>
                        <div style={{ fontSize: 10, color: '#3B82F6' }}>{p.stage}</div>
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{p.elapsed_s}s</div>
                    </div>
                  ))}
                </div>
              )}

              {/* AI Engine call distribution */}
              {Object.keys(snap.providers).length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 }}>
                    Engine Distribution
                  </div>
                  {Object.entries(snap.providers).map(([, cnt], i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 11, flex: 1, color: 'var(--text-secondary)' }}>Engine {i + 1}</span>
                      <div style={{ height: 6, borderRadius: 3, background: '#8B5CF6', width: Math.max(4, (cnt / Math.max(...Object.values(snap.providers))) * 100) + 'px', flexShrink: 0 }} />
                      <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', width: 28, textAlign: 'right' }}>{cnt}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* â”€â”€ Agents tab â”€â”€ */}
          {tab === 'agents' && snap && (
            <div>
              {Object.keys(snap.agents).length === 0 && (
                <div style={{ textAlign: 'center', padding: '30px 16px', fontSize: 12, color: 'var(--text-muted)' }}>
                  No agent calls recorded yet.<br />Run a pipeline to see agent stats.
                </div>
              )}
              {Object.entries(snap.agents)
                .sort(([, a], [, b]) => b.calls - a.calls)
                .map(([name, s]) => (
                  <div key={name} style={{ marginBottom: 8, padding: '10px 12px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'capitalize' }}>{name.replace(/_/g, ' ')}</span>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{s.avg_ms}ms avg</span>
                        {s.errors > 0 && (
                          <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 8, background: 'rgba(239,68,68,0.1)', color: '#EF4444', fontWeight: 700 }}>
                            {s.error_rate}% err
                          </span>
                        )}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 10 }}>
                      <div>
                        <div style={{ fontSize: 9, color: 'var(--text-muted)' }}>Calls</div>
                        <div style={{ fontSize: 14, fontWeight: 800, color: '#8B5CF6' }}>{s.calls}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 9, color: 'var(--text-muted)' }}>Success</div>
                        <div style={{ fontSize: 14, fontWeight: 800, color: '#10B981' }}>{s.calls - s.errors}</div>
                      </div>
                      {s.errors > 0 && (
                        <div>
                          <div style={{ fontSize: 9, color: 'var(--text-muted)' }}>Errors</div>
                          <div style={{ fontSize: 14, fontWeight: 800, color: '#EF4444' }}>{s.errors}</div>
                        </div>
                      )}
                      <div style={{ flex: 1 }}>
                        {/* Mini success bar */}
                        <div style={{ fontSize: 9, color: 'var(--text-muted)', marginBottom: 4 }}>Success rate</div>
                        <div style={{ height: 5, borderRadius: 3, background: 'var(--border-subtle)', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${((s.calls - s.errors) / s.calls) * 100}%`, background: s.errors > 0 ? '#F59E0B' : '#10B981', borderRadius: 3, transition: 'width 500ms' }} />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          )}

          {/* â”€â”€ Events tab â”€â”€ */}
          {tab === 'events' && (
            <div>
              {(!snap || snap.events.length === 0) && (
                <div style={{ textAlign: 'center', padding: '30px 16px', fontSize: 12, color: 'var(--text-muted)' }}>
                  No events yet. Events stream here in real time.
                </div>
              )}
              {snap && [...snap.events].reverse().map((ev, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '5px 0', borderBottom: '1px solid var(--border-subtle)', minWidth: 0 }}>
                  <span style={{ fontSize: 12, flexShrink: 0, marginTop: 1, color: eventColor(ev.type) }}>{eventIcon(ev.type)}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.4, wordBreak: 'break-word' }}>
                      {eventLabel(ev)}
                    </div>
                    <div style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 1 }}>
                      {new Date(ev.t * 1000).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {!snap && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 200, gap: 10 }}>
              <div className="loading-spinner" style={{ width: 24, height: 24 }} />
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Connecting to telemetry streamâ€¦</div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: '8px 14px', borderTop: '1px solid var(--border-subtle)', display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
          <div style={{ width: 6, height: 6, borderRadius: 3, background: connected ? '#10B981' : '#9CA3AF', flexShrink: 0 }} />
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>ws/telemetry Â· 1s interval</span>
          <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-muted)' }}>ARISE Monitor</span>
        </div>
      </div>
    </>
  )
}