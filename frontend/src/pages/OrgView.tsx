 
import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'
import {
  Building2, ChevronDown,
  Target, Users, Layers,
  Crown, Star, ArrowDown
} from 'lucide-react'

interface OrgMetrics {
  total_deals: number
  direct_deals: number
  active_deals: number
  won_deals: number
  lost_deals: number
  total_revenue: number
  won_revenue: number
  avg_win_probability: number
  win_rate: number
}

interface OrgNode {
  id: string
  role: string
  practice: string
  level: number
  highlight: boolean
  is_self: boolean
  metrics: OrgMetrics
  children: OrgNode[]
}

const LEVEL_COLORS = ['#F59E0B', '#3B82F6', '#06B6D4', '#8B5CF6', '#EC4899']
const LEVEL_ICONS = [Crown, Building2, Users, Target, Layers]
const LEVEL_LABELS = ['', 'Executive Leadership', 'Corporate Officers', 'Service Line Heads', 'Practice Directors']

function formatCurrency(val: number): string {
  if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`
  if (val >= 1e3) return `$${(val / 1e3).toFixed(0)}K`
  if (val === 0) return '—'
  return `$${val.toFixed(0)}`
}

/* ── Compact KPI Pill ── */
function KPIPill({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px',
      background: `${color}08`, borderRadius: 20, border: `1px solid ${color}18`,
    }}>
      <span style={{ fontSize: 18, fontWeight: 800, color, lineHeight: 1 }}>{value}</span>
      <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, fontWeight: 600 }}>{label}</span>
    </div>
  )
}

/* ── Org Node Card ── */
function NodeCard({ node, onSelect, isSelected }: { node: OrgNode; onSelect: (n: OrgNode) => void; isSelected: boolean }) {
  const m = node.metrics
  const color = LEVEL_COLORS[node.level - 1] || LEVEL_COLORS[3]
  const hasActivity = m.total_deals > 0

  return (
    <button
      onClick={() => onSelect(node)}
      style={{
        all: 'unset', cursor: 'pointer', display: 'flex', flexDirection: 'column',
        padding: '16px 18px', borderRadius: 14,
        background: isSelected ? `${color}10` : 'var(--bg-glass)',
        border: `1.5px solid ${isSelected ? color : 'var(--border-subtle)'}`,
        transition: 'all 0.2s ease', position: 'relative', overflow: 'hidden',
        boxShadow: isSelected ? `0 0 0 1px ${color}20, 0 4px 12px ${color}10` : 'none',
      }}
      onMouseEnter={e => {
        if (!isSelected) { e.currentTarget.style.borderColor = `${color}60`; e.currentTarget.style.transform = 'translateY(-1px)' }
      }}
      onMouseLeave={e => {
        if (!isSelected) { e.currentTarget.style.borderColor = 'var(--border-subtle)'; e.currentTarget.style.transform = 'none' }
      }}
    >
      {node.is_self && (
        <div style={{
          position: 'absolute', top: 8, right: 8, fontSize: 9, fontWeight: 700,
          color: '#F59E0B', background: 'rgba(245,158,11,0.1)', padding: '2px 8px',
          borderRadius: 6, display: 'flex', alignItems: 'center', gap: 3,
        }}><Star size={8} /> YOU</div>
      )}
      {node.highlight && !node.is_self && (
        <div style={{
          position: 'absolute', top: 8, right: 8, fontSize: 8, fontWeight: 700,
          color: color, background: `${color}10`, padding: '2px 7px', borderRadius: 6,
        }}>CHAIN</div>
      )}

      {/* Role & Practice */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: hasActivity ? 12 : 0 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: `linear-gradient(135deg, ${color}, ${color}cc)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 15, fontWeight: 800, color: '#fff', flexShrink: 0,
        }}>{node.role.charAt(0)}</div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{node.role}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{node.practice}</div>
        </div>
      </div>

      {/* Inline metrics */}
      {hasActivity && (
        <div style={{ display: 'flex', gap: 12, borderTop: '1px solid var(--border-subtle)', paddingTop: 10 }}>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#3B82F6' }}>{m.total_deals}</div>
            <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.3 }}>Deals</div>
          </div>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#10B981' }}>{m.won_deals}</div>
            <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.3 }}>Won</div>
          </div>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: '#8B5CF6' }}>{formatCurrency(m.total_revenue)}</div>
            <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.3 }}>Pipeline</div>
          </div>
          {m.win_rate > 0 && (
            <div style={{ textAlign: 'center', flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: '#F59E0B' }}>{m.win_rate}%</div>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.3 }}>Win</div>
            </div>
          )}
        </div>
      )}

      {node.children?.length > 0 && (
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: hasActivity ? 8 : 10, display: 'flex', alignItems: 'center', gap: 4 }}>
          <Users size={10} /> {node.children.length} reports
        </div>
      )}
    </button>
  )
}

/* ── Level Row ── */
function LevelRow({ level, nodes, selectedNode, onSelect }: {
  level: number; nodes: OrgNode[]; selectedNode: OrgNode | null; onSelect: (n: OrgNode) => void
}) {
  const color = LEVEL_COLORS[level - 1] || LEVEL_COLORS[3]
  const LevelIcon = LEVEL_ICONS[level - 1] || Target
  const [expanded, setExpanded] = useState(nodes.some(n => n.is_self || n.highlight))

  // Sort: self first, then highlighted, then by deals
  const sorted = [...nodes].sort((a, b) => {
    if (a.is_self) return -1; if (b.is_self) return 1
    if (a.highlight && !b.highlight) return -1; if (!a.highlight && b.highlight) return 1
    return b.metrics.total_deals - a.metrics.total_deals
  })

  const preview = sorted.slice(0, 4)
  const rest = sorted.slice(4)

  return (
    <div style={{ position: 'relative' }}>
      {/* Level Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14,
        padding: '10px 16px', background: `${color}06`, borderRadius: 12,
        border: `1px solid ${color}12`,
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: `linear-gradient(135deg, ${color}, ${color}cc)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <LevelIcon size={16} color="#fff" />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
            {LEVEL_LABELS[level] || `Level ${level}`}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {nodes.length} {nodes.length === 1 ? 'member' : 'members'}
          </div>
        </div>
        <div style={{
          fontSize: 10, fontWeight: 700, color: color,
          background: `${color}10`, padding: '3px 10px', borderRadius: 6,
        }}>L{level}</div>
      </div>

      {/* Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: level === 1 ? '1fr' : 'repeat(auto-fill, minmax(220px, 1fr))',
        gap: 10, maxWidth: level === 1 ? 400 : undefined,
      }}>
        {preview.map(n => (
          <NodeCard key={n.id} node={n} onSelect={onSelect} isSelected={selectedNode?.id === n.id} />
        ))}
      </div>

      {/* Expand/collapse for >4 members */}
      {rest.length > 0 && (
        <>
          {expanded && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
              gap: 10, marginTop: 10,
            }}>
              {rest.map(n => (
                <NodeCard key={n.id} node={n} onSelect={onSelect} isSelected={selectedNode?.id === n.id} />
              ))}
            </div>
          )}
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              all: 'unset', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              gap: 6, width: '100%', padding: '8px 0', marginTop: 8,
              fontSize: 11, fontWeight: 600, color: color,
              borderRadius: 8, transition: 'background 0.2s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = `${color}08`}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <ChevronDown size={14} style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
            {expanded ? 'Show less' : `Show ${rest.length} more`}
          </button>
        </>
      )}
    </div>
  )
}

/* ── Connector between levels ── */
function LevelConnector() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '6px 0' }}>
      <ArrowDown size={16} style={{ color: 'var(--border-subtle)' }} />
    </div>
  )
}

/* ── Selected Node Detail Panel ── */
function DetailPanel({ node }: { node: OrgNode }) {
  const m = node.metrics
  const color = LEVEL_COLORS[node.level - 1] || LEVEL_COLORS[3]

  return (
    <div style={{
      padding: '20px 24px', background: 'var(--bg-glass)', borderRadius: 16,
      border: `1px solid ${color}20`, position: 'sticky', top: 16,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <div style={{
          width: 48, height: 48, borderRadius: 12,
          background: `linear-gradient(135deg, ${color}, ${color}cc)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 22, fontWeight: 800, color: '#fff',
        }}>{node.role.charAt(0)}</div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800 }}>{node.role}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{node.practice}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
        {[
          { label: 'Total Deals', value: m.total_deals, color: '#3B82F6' },
          { label: 'Won Deals', value: m.won_deals, color: '#10B981' },
          { label: 'Active', value: m.active_deals, color: '#06B6D4' },
          { label: 'Lost', value: m.lost_deals, color: '#EF4444' },
          { label: 'Pipeline', value: formatCurrency(m.total_revenue), color: '#8B5CF6' },
          { label: 'Won Rev', value: formatCurrency(m.won_revenue), color: '#10B981' },
          { label: 'Win Rate', value: m.win_rate > 0 ? `${m.win_rate}%` : '—', color: '#F59E0B' },
          { label: 'Avg Win %', value: m.avg_win_probability > 0 ? `${m.avg_win_probability}%` : '—', color: '#06B6D4' },
        ].map(s => (
          <div key={s.label} style={{ padding: '10px 12px', background: 'var(--bg-secondary)', borderRadius: 10, border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>{s.label}</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: s.color, marginTop: 2 }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Direct Reports */}
      {node.children?.length > 0 && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 }}>
            Direct Reports ({node.children.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {node.children.map(c => (
              <div key={c.id} style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px',
                background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-subtle)',
              }}>
                <div style={{
                  width: 28, height: 28, borderRadius: 7,
                  background: `linear-gradient(135deg, ${LEVEL_COLORS[c.level - 1] || '#6B7280'}, ${LEVEL_COLORS[c.level - 1] || '#6B7280'}cc)`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 12, fontWeight: 700, color: '#fff',
                }}>{c.role.charAt(0)}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.role}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{c.practice}</div>
                </div>
                {c.metrics.total_deals > 0 && (
                  <span style={{ fontSize: 11, fontWeight: 700, color: '#3B82F6' }}>{c.metrics.total_deals}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}


/* ── Main Page ── */
export default function OrgView() {
  const [tree, setTree] = useState<OrgNode | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedNode, setSelectedNode] = useState<OrgNode | null>(null)

  const fetchTree = useCallback(async () => {
    try {
      const data = await api.getOrgTree()
      setTree(data)
    } catch (e: any) {
      setError(e.message)
    }
    setLoading(false)
  }, [])

  useEffect(() => { void fetchTree() }, [fetchTree])

  if (loading) return <div className="loading-page"><div className="loading-spinner" /><span style={{ color: 'var(--text-muted)' }}>Loading org structure...</span></div>
  if (error) return <div className="glass-card" style={{ textAlign: 'center', padding: 60 }}><div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div><div style={{ color: 'var(--text-muted)' }}>{error}</div></div>
  if (!tree) return null

  // Collect nodes per level
  const collectLevel = (node: OrgNode, target: number, result: OrgNode[] = []): OrgNode[] => {
    if (node.level === target) result.push(node)
    node.children?.forEach(c => collectLevel(c, target, result))
    return result
  }

  const levels = [1, 2, 3, 4].map(l => ({ level: l, nodes: l === 1 ? [tree] : collectLevel(tree, l) })).filter(l => l.nodes.length > 0)
  const rm = tree.metrics

  return (
    <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
      {/* Main Column */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 12,
            background: 'linear-gradient(135deg, #3B82F6, #8B5CF6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Building2 size={22} color="#fff" />
          </div>
          <div style={{ flex: 1 }}>
            <h2 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>Organization Pipeline</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: 12, margin: '2px 0 0' }}>
              Hierarchical bid pipeline across {levels.reduce((s, l) => s + l.nodes.length, 0)} team members
            </p>
          </div>
        </div>

        {/* Global KPI Strip */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
          <KPIPill label="Deals" value={rm.total_deals} color="#3B82F6" />
          <KPIPill label="Pipeline" value={formatCurrency(rm.total_revenue)} color="#10B981" />
          <KPIPill label="Won" value={rm.won_deals} color="#8B5CF6" />
          <KPIPill label="Active" value={rm.active_deals} color="#06B6D4" />
          <KPIPill label="Win Rate" value={rm.win_rate > 0 ? `${rm.win_rate}%` : '—'} color="#F59E0B" />
        </div>

        {/* Level Rows */}
        {levels.map((l, i) => (
          <div key={l.level}>
            <LevelRow level={l.level} nodes={l.nodes} selectedNode={selectedNode} onSelect={setSelectedNode} />
            {i < levels.length - 1 && <LevelConnector />}
          </div>
        ))}

        {/* Footer */}
        <div style={{
          textAlign: 'center', fontSize: 10, color: 'var(--text-muted)',
          letterSpacing: 1.5, textTransform: 'uppercase', marginTop: 32, paddingBottom: 8,
        }}>
          ARISE · Autonomous RFP Intelligence and Sales Engine
        </div>
      </div>

      {/* Detail Sidebar */}
      {selectedNode && (
        <div style={{ width: 320, flexShrink: 0 }}>
          <DetailPanel node={selectedNode} />
        </div>
      )}
    </div>
  )
}
