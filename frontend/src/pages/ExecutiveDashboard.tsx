import React, { useState, useEffect } from 'react'
import { api } from '../api'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, CartesianGrid, Legend } from 'recharts'
import {
  TrendingUp, Award, AlertTriangle, DollarSign, Target, Users, CheckCircle,
  Building2, ChevronDown, Briefcase, Layers, GitBranch, Crown, Star, ArrowRight
} from 'lucide-react'

interface ExecData {
  summary: {
    total_bids: number; active_bids: number; won: number; lost: number;
    win_rate: number; total_pipeline_tcv: number; won_tcv: number; lost_tcv: number;
  };
  pipeline_by_stage: { stage: string; count: number; tcv: number }[];
  risk_distribution: Record<string, number>;
  industry_breakdown: { industry: string; count: number; tcv: number; won: number; lost: number }[];
  contract_type_breakdown: { type: string; count: number; tcv: number }[];
  avg_win_probability: number;
}

interface OrgMetrics {
  total_deals: number; direct_deals: number; active_deals: number; won_deals: number;
  lost_deals: number; total_revenue: number; won_revenue: number;
  avg_win_probability: number; win_rate: number;
}
interface OrgNode {
  id: string; role: string; practice: string; level: number;
  highlight: boolean; is_self: boolean; metrics: OrgMetrics; children: OrgNode[];
}

const STAGE_LABELS: Record<string, string> = {
  created: 'Created', intake_processing: 'Intake', intake_review: 'Intake Review',
  bid_no_bid: 'Bid/No-Bid', scope_building: 'Scope', scope_review: 'Scope Review',
  solution_design: 'Solution', solution_review: 'Solution Review',
  commercial_modeling: 'Commercial', commercial_approval: 'Commercial Approval',
  compliance_review: 'Compliance', legal_sign_off: 'Legal',
  output_generation: 'Output Gen', qa_review: 'QA', final_review: 'Final Review',
  proposal_review: 'Proposal Review', submitted: 'Submitted', won: 'Won', lost: 'Lost', abandoned: 'Abandoned', no_bid: 'No-Bid'
}
const RISK_COLORS: Record<string, string> = { low: '#10B981', medium: '#F59E0B', high: '#EF4444', critical: '#DC2626' }
const CHART_COLORS = ['#3B82F6', '#10B981', '#8B5CF6', '#F59E0B', '#EC4899', '#06B6D4', '#EF4444']

function formatTCV(v: number) {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1000) return `$${(v / 1000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

const LEVEL_META: Record<number, { label: string; icon: React.ElementType; color: string; gradient: string; desc: string }> = {
  1: { label: 'CEO & Managing Director', icon: Crown, color: '#F59E0B', gradient: 'linear-gradient(135deg, #F59E0B, #D97706)', desc: 'Global leadership' },
  2: { label: 'Corporate Executives', icon: Building2, color: '#3B82F6', gradient: 'linear-gradient(135deg, #3B82F6, #2563EB)', desc: 'C-Suite, CVPs, Presidents' },
  3: { label: 'Service Line Heads', icon: Users, color: '#06B6D4', gradient: 'linear-gradient(135deg, #06B6D4, #0891B2)', desc: 'Service line ownership' },
  4: { label: 'Directors', icon: Target, color: '#8B5CF6', gradient: 'linear-gradient(135deg, #8B5CF6, #7C3AED)', desc: 'Domain practice leads' },
}

/* ── Org: Member Card ── */
function MemberCard({ node }: { node: OrgNode }) {
  const m = node.metrics
  const meta = LEVEL_META[node.level] || LEVEL_META[4]
  return (
    <div className={`org-member-card ${node.is_self ? 'org-member-self' : ''} ${node.highlight ? 'org-member-highlight' : ''}`}>
      {node.is_self && <div className="org-self-tag"><Star size={9} /> You</div>}
      <div className="org-member-top">
        <div className="org-member-avatar" style={{ background: meta.gradient }}>{node.role.charAt(0)}</div>
        <div className="org-member-info">
          <div className="org-member-role">{node.role}</div>
          <div className="org-member-practice">{node.practice}</div>
        </div>
        {node.highlight && !node.is_self && (
          <div className="org-branch-tag" style={{ color: meta.color, borderColor: `${meta.color}40`, background: `${meta.color}0A` }}>
            <GitBranch size={10} /> Chain
          </div>
        )}
      </div>
      <div className="org-member-metrics">
        <div className="org-member-stat"><span className="org-member-stat-val" style={{ color: '#3B82F6' }}>{m.total_deals}</span><span className="org-member-stat-lbl">Deals</span></div>
        <div className="org-member-stat"><span className="org-member-stat-val" style={{ color: '#059669' }}>{m.total_revenue > 0 ? formatTCV(m.total_revenue) : '$0'}</span><span className="org-member-stat-lbl">Revenue</span></div>
        <div className="org-member-stat"><span className="org-member-stat-val" style={{ color: '#7C3AED' }}>{m.won_deals}</span><span className="org-member-stat-lbl">Won</span></div>
        <div className="org-member-stat"><span className="org-member-stat-val" style={{ color: '#D97706' }}>{m.win_rate > 0 ? `${m.win_rate}%` : '0%'}</span><span className="org-member-stat-lbl">Win%</span></div>
      </div>
      {node.children?.length > 0 && (
        <div className="org-member-children-hint"><Users size={11} /> {node.children.length} direct reports</div>
      )}
    </div>
  )
}

/* ── Org: Accordion ── */
function LevelAccordion({ level, nodes, isOpen, onToggle, globalMetrics }: {
  level: number; nodes: OrgNode[]; isOpen: boolean; onToggle: () => void; globalMetrics?: OrgMetrics
}) {
  const meta = LEVEL_META[level] || LEVEL_META[4]
  const Icon = meta.icon
  const lm = nodes.reduce((a, n) => ({
    deals: a.deals + n.metrics.total_deals, rev: a.rev + n.metrics.total_revenue, won: a.won + n.metrics.won_deals,
  }), { deals: 0, rev: 0, won: 0 })
  const d = level === 1 && globalMetrics ? { deals: globalMetrics.total_deals, rev: globalMetrics.total_revenue, won: globalMetrics.won_deals } : lm

  return (
    <div className={`org-accordion ${isOpen ? 'org-accordion-open' : ''}`}>
      <button className="org-accordion-header" onClick={onToggle}>
        <div className="org-accordion-left">
          <div className="org-accordion-icon" style={{ background: meta.gradient }}><Icon size={18} color="white" /></div>
          <div className="org-accordion-title-group">
            <div className="org-accordion-level-tag" style={{ color: meta.color, background: `${meta.color}12`, borderColor: `${meta.color}30` }}>Level {level}</div>
            <div className="org-accordion-title">{meta.label}</div>
            <div className="org-accordion-desc">{meta.desc}</div>
          </div>
        </div>
        <div className="org-accordion-stats">
          <div className="org-accordion-stat"><span className="org-accordion-stat-val">{level === 1 ? 1 : nodes.length}</span><span className="org-accordion-stat-lbl">{level === 1 ? 'Leader' : 'Members'}</span></div>
          <div className="org-accordion-stat"><span className="org-accordion-stat-val">{d.deals}</span><span className="org-accordion-stat-lbl">Deals</span></div>
          <div className="org-accordion-stat"><span className="org-accordion-stat-val">{d.rev > 0 ? formatTCV(d.rev) : '$0'}</span><span className="org-accordion-stat-lbl">Revenue</span></div>
          <div className="org-accordion-stat"><span className="org-accordion-stat-val">{d.won}</span><span className="org-accordion-stat-lbl">Won</span></div>
        </div>
        <div className={`org-accordion-chevron ${isOpen ? 'org-accordion-chevron-open' : ''}`}><ChevronDown size={20} /></div>
      </button>
      {isOpen && (
        <div className="org-accordion-body">
          {level === 1 ? (
            <div style={{ maxWidth: 480 }}>{nodes.map(n => <MemberCard key={n.id} node={n} />)}</div>
          ) : (
            <div className="org-members-grid">
              {[...nodes].sort((a, b) => a.is_self ? -1 : b.is_self ? 1 : a.highlight && !b.highlight ? -1 : !a.highlight && b.highlight ? 1 : 0)
                .map(n => <MemberCard key={n.id} node={n} />)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ═══════════ MAIN COMPONENT ═══════════ */
export default function ExecutiveDashboard() {
  const [activeTab, setActiveTab] = useState<'pipeline' | 'org'>('pipeline')
  const [data, setData] = useState<ExecData | null>(null)
  const [tree, setTree] = useState<OrgNode | null>(null)
  const [loading, setLoading] = useState(true)
  const [openLevels, setOpenLevels] = useState<Record<number, boolean>>({ 1: false, 2: false, 3: true, 4: false })

  useEffect(() => {
    Promise.all([
      api.getExecutiveDashboard().catch(() => null),
      api.getOrgTree().catch(() => null),
    ]).then(([d, t]) => { setData(d); setTree(t) }).finally(() => setLoading(false))
  }, [])

  const toggleLevel = (l: number) => setOpenLevels(p => ({ ...p, [l]: !p[l] }))

  if (loading) return <div className="loading-page"><div className="loading-spinner" /><span style={{ color: 'var(--text-muted)' }}>Loading executive dashboard...</span></div>

  const collectLevel = (node: OrgNode, target: number, result: OrgNode[] = []): OrgNode[] => {
    if (node.level === target) result.push(node)
    node.children?.forEach(c => collectLevel(c, target, result))
    return result
  }

  /* ── Pipeline Tab ── */
  const renderPipelineTab = () => {
    if (!data) return <div className="empty-state"><div className="empty-title">No data available</div></div>
    const { summary } = data
    const riskData = Object.entries(data.risk_distribution).map(([k, v]) => ({ name: k, value: v })).filter(d => d.value > 0)
    
    const pipelineDataMap = new Map(data.pipeline_by_stage.map(s => [s.stage, s]))
    const knownStages = Object.keys(STAGE_LABELS)
    const backendStages = data.pipeline_by_stage.map(s => s.stage)
    const allStages = Array.from(new Set([...knownStages, ...backendStages]))
    const pipelineData = allStages.map(s => {
      const existing = pipelineDataMap.get(s)
      return existing ? { ...existing, label: STAGE_LABELS[s] || s } : { stage: s, count: 0, tcv: 0, label: STAGE_LABELS[s] || s }
    })
    
    const normalizedBreakdown = data.industry_breakdown.map(d => {
      if (d.industry === 'Retail') return { ...d, industry: 'Retail & CPG' }
      return d
    })
    const defaultIndustries = ["Financial Services", "Retail & CPG", "Manufacturing", "Healthcare & Life Sciences", "Technology", "Energy & Utilities", "Telecommunications", "Public Sector", "Other"]
    const allUnique = Array.from(new Set([...defaultIndustries, ...normalizedBreakdown.map(d => d.industry)])).filter(i => i !== 'Unknown')
    const industryData = allUnique.map(ind => {
      const existing = normalizedBreakdown.find(d => d.industry === ind)
      return existing || { industry: ind, count: 0, tcv: 0, won: 0, lost: 0 }
    }).sort((a, b) => b.count - a.count)

    const metrics = [
      { label: 'Total Bids', value: summary.total_bids, icon: Users, color: '#3B82F6', gradient: true },
      { label: 'Win Rate', value: `${summary.win_rate.toFixed(0)}%`, icon: Award, color: '#10B981' },
      { label: 'Pipeline TCV', value: formatTCV(summary.total_pipeline_tcv), icon: DollarSign, color: '#8B5CF6' },
      { label: 'Active Bids', value: summary.active_bids, icon: Target, color: '#F59E0B' },
      { label: 'Won', value: summary.won, icon: CheckCircle, color: '#10B981' },
      { label: 'Lost', value: summary.lost, icon: AlertTriangle, color: '#EF4444' },
      { label: 'Avg Win Prob', value: `${(data.avg_win_probability * 100).toFixed(0)}%`, icon: TrendingUp, color: '#06B6D4' },
      { label: 'Won TCV', value: formatTCV(summary.won_tcv), icon: DollarSign, color: '#10B981' },
    ]

    const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: { name: string; value: string | number; color: string }[]; label?: string }) => {
      if (!active || !payload?.length) return null
      return (
        <div style={{ background: 'white', border: '1px solid #E5E7EB', borderRadius: 12, padding: '12px 16px', boxShadow: '0 10px 40px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#111', marginBottom: 6 }}>{label}</div>
          {payload.map((p: { color?: string; name?: string; value?: string | number }, i: number) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, marginTop: 2 }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: p.color }} />
              <span style={{ color: '#6B7280' }}>{p.name}:</span>
              <span style={{ fontWeight: 700 }}>{p.value}</span>
            </div>
          ))}
        </div>
      )
    }

    return (
      <>
        <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
          {metrics.map(m => (
            <div className="metric-card" key={m.label}>
              <div className="metric-icon" style={{ background: `${m.color}15` }}><m.icon size={20} style={{ color: m.color }} /></div>
              <div className="metric-label">{m.label}</div>
              <div className={`metric-value ${m.gradient ? 'gradient' : ''}`} style={{ fontSize: 28 }}>{m.value}</div>
            </div>
          ))}
        </div>

        {/* Row 1: Pipeline Area Chart + Risk Donut */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20, marginBottom: 20 }}>
          <div className="glass-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 4, height: 18, borderRadius: 2, background: 'linear-gradient(to bottom, #3B82F6, #8B5CF6)' }} />
                Pipeline by Stage
              </h3>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.8 }}>{pipelineData.length} stages</span>
            </div>
            <div style={{ height: 300, minHeight: 300, minWidth: 0 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={pipelineData} margin={{ top: 30, right: 20, bottom: 80, left: 0 }}>
                  <defs>
                    <linearGradient id="gradBarBids" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#3B82F6" />
                      <stop offset="100%" stopColor="#8B5CF6" />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.04)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: '#6B7280', fontSize: 10, fontWeight: 600 }} angle={-45} textAnchor="end" interval={0} axisLine={{ stroke: '#E5E7EB' }} tickLine={false} dy={5} />
                  <YAxis tick={{ fill: '#6B7280', fontSize: 10 }} axisLine={false} tickLine={false} dx={-5} />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,0,0,0.02)' }} />
                  <Legend verticalAlign="top" align="right" height={30} iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: '#6B7280', paddingBottom: 20 }} />
                  <Bar dataKey="count" fill="url(#gradBarBids)" radius={[4, 4, 0, 0]} name="Bids" barSize={32} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="glass-card" style={{ display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 4, height: 18, borderRadius: 2, background: 'linear-gradient(to bottom, #F59E0B, #EF4444)' }} />
              Risk Distribution
            </h3>
            <div style={{ flex: 1, minHeight: 240, minWidth: 0, position: 'relative' }}>
              {riskData.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={riskData} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={4} dataKey="value" strokeWidth={0}>
                        {riskData.map((entry, i) => <Cell key={entry.name} fill={RISK_COLORS[entry.name] || CHART_COLORS[i]} />)}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)' }}>{summary.active_bids}</div>
                    <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Active</div>
                  </div>
                </>
              ) : <div className="empty-state" style={{ paddingTop: 60 }}><div className="empty-title" style={{ fontSize: 14 }}>No active bids</div></div>}
            </div>
            {riskData.length > 0 && (
              <div style={{ display: 'flex', justifyContent: 'center', gap: 16, paddingTop: 8 }}>
                {riskData.map(r => (
                  <div key={r.name} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
                    <div style={{ width: 8, height: 8, borderRadius: 2, background: RISK_COLORS[r.name] }} />
                    <span style={{ textTransform: 'capitalize', color: 'var(--text-muted)' }}>{r.name}</span>
                    <span style={{ fontWeight: 700 }}>{r.value}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Row 2: Industry + Contract Type */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
          <div className="glass-card">
            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 4, height: 18, borderRadius: 2, background: 'linear-gradient(to bottom, #8B5CF6, #EC4899)' }} />
              Industry Breakdown
            </h3>
              <div style={{ height: 320, minHeight: 320, minWidth: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={industryData} layout="vertical" margin={{ top: 20, left: 0, right: 20, bottom: 10 }}>
                    <defs>
                      <linearGradient id="gradIndustry" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#8B5CF6" />
                        <stop offset="100%" stopColor="#EC4899" />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.04)" horizontal={false} />
                    <XAxis type="number" tick={{ fill: '#9CA3AF', fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="industry" tick={{ fill: '#6B7280', fontSize: 11, fontWeight: 500 }} width={160} axisLine={false} tickLine={false} />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,0,0,0.02)' }} />
                    <Legend verticalAlign="top" align="right" height={30} iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: '#6B7280', paddingBottom: 10 }} />
                    <Bar dataKey="count" fill="url(#gradIndustry)" radius={[0, 4, 4, 0]} name="Bids" barSize={16} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
          </div>

          <div className="glass-card">
            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 4, height: 18, borderRadius: 2, background: 'linear-gradient(to bottom, #06B6D4, #3B82F6)' }} />
              Contract Type Mix
            </h3>
            {data.contract_type_breakdown.length > 0 ? (
              <div style={{ height: 280, position: 'relative' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <defs>
                      {CHART_COLORS.map((c, i) => (
                        <linearGradient key={i} id={`cGrad${i}`} x1="0" y1="0" x2="1" y2="1">
                          <stop offset="0%" stopColor={c} stopOpacity={1} />
                          <stop offset="100%" stopColor={c} stopOpacity={0.7} />
                        </linearGradient>
                      ))}
                    </defs>
                    <Pie data={data.contract_type_breakdown} cx="50%" cy="50%" innerRadius={50} outerRadius={85} paddingAngle={4} dataKey="count" strokeWidth={0}
                      label={(props: unknown) => {
                        const p = props as { cx: number; x: number; y: number; payload?: { type: string; count: number } }
                        return (
                          <text x={p.x} y={p.y} fill="#374151" fontSize={11} fontWeight={600} textAnchor={p.x > p.cx ? 'start' : 'end'} dominantBaseline="central">
                            {((p.payload && p.payload.type) || '?').toUpperCase()}: {p.payload?.count || 0}
                          </text>
                        )
                      }}>
                      {data.contract_type_breakdown.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                    <Legend verticalAlign="bottom" height={30} iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: '#6B7280', paddingTop: 10 }} />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
                  <div style={{ fontSize: 22, fontWeight: 800 }}>{summary.total_bids}</div>
                  <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Total</div>
                </div>
              </div>
            ) : <div className="empty-state" style={{ paddingTop: 40 }}><div className="empty-title" style={{ fontSize: 14 }}>No data yet</div></div>}
          </div>
        </div>

        {/* Win/Loss Table */}
        <div className="glass-card">
          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 4, height: 18, borderRadius: 2, background: 'linear-gradient(to bottom, #10B981, #3B82F6)' }} />
            Win/Loss by Industry
          </h3>
          <table className="data-table">
            <thead><tr><th>Industry</th><th style={{ textAlign: 'right' }}>Total</th><th style={{ textAlign: 'right' }}>Won</th><th style={{ textAlign: 'right' }}>Lost</th><th style={{ textAlign: 'right' }}>Win Rate</th><th style={{ textAlign: 'right' }}>TCV</th></tr></thead>
            <tbody>
              {industryData.length === 0 ? (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>No data</td></tr>
              ) : industryData.map(ind => {
                const total = ind.won + ind.lost
                const wr = total > 0 ? (ind.won / total * 100).toFixed(0) : '0'
                return (
                  <tr key={ind.industry}>
                    <td style={{ fontWeight: 600 }}>{ind.industry}</td>
                    <td style={{ textAlign: 'right' }}>{ind.count}</td>
                    <td style={{ textAlign: 'right', color: 'var(--status-success)', fontWeight: 600 }}>{ind.won}</td>
                    <td style={{ textAlign: 'right', color: 'var(--status-danger)', fontWeight: 600 }}>{ind.lost}</td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ width: 40, height: 4, borderRadius: 2, background: '#E5E7EB', overflow: 'hidden' }}>
                          <div style={{ width: `${wr}%`, height: '100%', borderRadius: 2, background: Number(wr) >= 50 ? '#10B981' : '#F59E0B' }} />
                        </div>
                        <span style={{ color: Number(wr) >= 50 ? 'var(--status-success)' : 'var(--status-warning)', fontWeight: 600 }}>{wr}%</span>
                      </div>
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600 }}>{formatTCV(ind.tcv)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </>
    )
  }

  /* ── Org Tab ── */
  const renderOrgTab = () => {
    if (!tree) return <div className="empty-state"><div className="empty-title">Org data unavailable</div></div>
    const rm = tree.metrics
    const l1 = [tree], l2 = collectLevel(tree, 2), l3 = collectLevel(tree, 3), l4 = collectLevel(tree, 4)
    const Conn = () => (
      <div className="org-accordion-connector"><div className="org-accordion-connector-line" /><ArrowRight size={14} style={{ color: 'var(--text-muted)' }} /><div className="org-accordion-connector-line" /></div>
    )
    return (
      <>
        {/* Position Badge + KPI */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 }}>
          <div className="org-your-position-badge">
            <Star size={12} />
            <div>
              <div style={{ fontSize: 11, fontWeight: 700 }}>Your Position</div>
              <div style={{ fontSize: 10, opacity: 0.8 }}>Service Line Head · Enterprise Platform Services</div>
            </div>
          </div>
        </div>

        <div className="org-kpi-strip">
          {[
            { l: 'Total Deals', v: rm.total_deals, i: Briefcase, c: '#3B82F6' },
            { l: 'Pipeline Revenue', v: rm.total_revenue > 0 ? formatTCV(rm.total_revenue) : '$0', i: DollarSign, c: '#059669' },
            { l: 'Won Deals', v: rm.won_deals, i: Award, c: '#7C3AED' },
            { l: 'Active', v: rm.active_deals, i: Target, c: '#06B6D4' },
            { l: 'Win Rate', v: rm.win_rate > 0 ? `${rm.win_rate}%` : '0%', i: TrendingUp, c: '#D97706' },
            { l: 'Org Levels', v: '4', i: Layers, c: '#EC4899' },
          ].map(k => (
            <div className="org-mini-metric" key={k.l}>
              <div className="org-mini-metric-icon" style={{ background: `${k.c}14` }}><k.i size={14} style={{ color: k.c }} /></div>
              <div><div className="org-mini-metric-value">{k.v}</div><div className="org-mini-metric-label">{k.l}</div></div>
            </div>
          ))}
        </div>

        <div className="org-accordions">
          <LevelAccordion level={1} nodes={l1} isOpen={openLevels[1]} onToggle={() => toggleLevel(1)} globalMetrics={rm} />
          <Conn />
          <LevelAccordion level={2} nodes={l2} isOpen={openLevels[2]} onToggle={() => toggleLevel(2)} />
          <Conn />
          <LevelAccordion level={3} nodes={l3} isOpen={openLevels[3]} onToggle={() => toggleLevel(3)} />
          <Conn />
          <LevelAccordion level={4} nodes={l4} isOpen={openLevels[4]} onToggle={() => toggleLevel(4)} />
        </div>
        <div style={{ textAlign: 'center', fontSize: 10, color: 'var(--text-muted)', letterSpacing: 1.5, textTransform: 'uppercase', marginTop: 24 }}>
          ARISE · Organization Hierarchy · Bid Management
        </div>
      </>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 24, fontWeight: 800 }}>Executive View</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>Pipeline analytics, org structure & strategic KPIs</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs" style={{ marginBottom: 24 }}>
        <button className={`tab ${activeTab === 'pipeline' ? 'active' : ''}`} onClick={() => setActiveTab('pipeline')}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><TrendingUp size={14} /> Pipeline & Analytics</span>
        </button>
        <button className={`tab ${activeTab === 'org' ? 'active' : ''}`} onClick={() => setActiveTab('org')}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><Building2 size={14} /> Org Structure</span>
        </button>
      </div>

      {activeTab === 'pipeline' ? renderPipelineTab() : renderOrgTab()}
    </div>
  )
}
