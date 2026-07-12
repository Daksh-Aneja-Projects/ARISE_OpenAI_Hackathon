 
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { ArrowLeft, Play, CheckCircle, XCircle, Clock, AlertTriangle, FileText, Inbox, Target, Layers, DollarSign, Scale, Search, BarChart3, Zap, Building2, PenTool, ArrowRight } from 'lucide-react'
import React from 'react'
import { IntakeRenderer, DataAnalystRenderer, BidNoBidRenderer, ScopeRenderer, SolutionRenderer, CompetitiveRenderer, CommercialRenderer, ComplianceRenderer, DiscoveryRenderer, AISolutioningRenderer, OutputRenderer, FeedbackRenderer, ClientIntelRenderer, ProposalWriterRenderer, TransitionChangeRenderer } from '../components/AgentRenderers'

const AGENT_ICONS: Record<string, React.FC<{size?: number; style?: React.CSSProperties; className?: string}>> = {
  intake: Inbox, data_analyst: BarChart3, client_intelligence: Building2,
  strategic_assessment: Target, solution_scope: Layers, automation_ai: Zap,
  commercial_model: DollarSign, compliance_risk: Scale,
  transition_change: ArrowRight,
  proposal_generator: PenTool, discovery: Search,
  feedback_learning: BarChart3,
}

const AGENT_META: Record<string, { label: string; description: string; color: string }> = {
  intake: { label: 'RFP Intake', description: 'Parses RFP documents, extracts key fields, and populates the BidManifest.', color: '#3B82F6' },
  data_analyst: { label: 'Data Intelligence', description: 'Comprehensive data extraction from RFP: users, countries, configurations, integrations, SLAs, and all quantifiable metrics.', color: '#7C3AED' },
  client_intelligence: { label: 'Client Intelligence', description: 'Web-powered client research: company profile, technology landscape, market position, and win strategy.', color: '#0D9488' },
  strategic_assessment: { label: 'Strategic Assessment', description: 'Calculates win probability, competitive landscape analysis, win themes, differentiators, and Go/No-Go recommendation.', color: '#10B981' },
  solution_scope: { label: 'Solution Design & Scoping', description: 'Technical architecture, operating model, WBS, effort estimation, and team model sizing.', color: '#8B5CF6' },
  automation_ai: { label: 'AI & Automation Advisory', description: 'AI/automation opportunity identification, ROI analysis, and implementation roadmap.', color: '#0EA5E9' },
  commercial_model: { label: 'Commercial & Pricing', description: 'Rate Card Engine + Pricing Optimizer. Resource loading, P&L, scenarios, margin guardrails.', color: '#06B6D4' },
  compliance_risk: { label: 'Risk & Compliance', description: 'Risk register with RFP citations, SLA/penalty analysis, and negotiation matrix.', color: '#EF4444' },
  transition_change: { label: 'Transition & Change Management', description: 'Transition phases, knowledge transfer, cutover plans, stakeholder change management, RACI governance, and wave rollout roadmap.', color: '#F97316' },
  proposal_generator: { label: 'Proposal Generator', description: 'Writes full proposal sections, assembles executive summary, methodology, team, case studies, and SOW with quality validation.', color: '#D946EF' },
  discovery: { label: 'Discovery & Clarifications', description: 'Gap analysis and client clarification questions from across all agents.', color: '#F97316' },
  feedback_learning: { label: 'Learning & Feedback', description: 'Institutional learning capture, win/loss analysis, and model calibration.', color: '#6366F1' },
}

/** Formats a number as USD currency with proper comma separators, e.g. $1,234,567 */
function fmtUSD(val: unknown): string {
  if (val === null || val === undefined) return '$0'
  const n = typeof val === 'string' ? parseFloat(val) : Number(val)
  if (isNaN(n)) return '$0'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(Math.round(n))
}

/** Renders markdown-like text with basic formatting */
function NarrativeRenderer({ text }: { text: string }) {
  if (!text) return null
  const paragraphs = text.split('\n\n').filter(Boolean)
  return (
    <div style={{ fontSize: 14, lineHeight: 1.8, color: 'var(--text-secondary)' }}>
      {paragraphs.map((p, i) => {
        const trimmed = p.trim()
        // Headers
        if (trimmed.startsWith('### ')) return <h4 key={i} style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', margin: '20px 0 8px' }}>{trimmed.slice(4)}</h4>
        if (trimmed.startsWith('## ')) return <h3 key={i} style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-primary)', margin: '24px 0 10px' }}>{trimmed.slice(3)}</h3>
        if (trimmed.startsWith('# ')) return <h2 key={i} style={{ fontSize: 20, fontWeight: 800, color: 'var(--text-primary)', margin: '28px 0 12px' }}>{trimmed.slice(2)}</h2>

        // Numbered/bullet lists
        const lines = trimmed.split('\n')
        const isList = lines.every(l => /^[\d]+\.|^[-â€¢*]/.test(l.trim()))
        if (isList) {
          return (
            <ul key={i} style={{ margin: '8px 0', paddingLeft: 24 }}>
              {lines.map((l, j) => (
                <li key={j} style={{ marginBottom: 6 }}>
                  {l.replace(/^[\d]+\.\s*|^[-â€¢*]\s*/, '').split('**').map((part, k) =>
                    k % 2 === 1 ? <strong key={k} style={{ color: 'var(--text-primary)' }}>{part}</strong> : part
                  )}
                </li>
              ))}
            </ul>
          )
        }

        // Regular paragraph with bold support
        return (
          <p key={i} style={{ marginBottom: 12 }}>
            {trimmed.split('**').map((part, k) =>
              k % 2 === 1 ? <strong key={k} style={{ color: 'var(--text-primary)' }}>{part}</strong> : part
            )}
          </p>
        )
      })}
    </div>
  )
}

export default function AgentDetail() {
  const { bidId, agentName } = useParams<{ bidId: string; agentName: string }>()
  const navigate = useNavigate()
  const [bid, setBid] = useState<Record<string, unknown> | null>(null)
  const [output, setOutput] = useState<Record<string, unknown> | null>(null)
  const [prevOutput, setPrevOutput] = useState<Record<string, unknown> | null>(null)
  const [showDiff, setShowDiff] = useState(false)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const meta = AGENT_META[agentName || ''] || { label: agentName, description: '', color: '#666' }
  const IconComp = AGENT_ICONS[agentName || ''] || FileText

  useEffect(() => {
    let mounted = true
    const fetchData = async () => {
      if (!bidId || !agentName) return
      try {
        const b = await api.getBid(bidId)
        if (mounted) setBid(b)
        try {
          const o = await api.getAgentOutput(bidId, agentName)
          if (mounted) { setOutput(o); setError(null) }
        } catch { if (mounted) setOutput(null) }
      } catch (e: unknown) { 
        if (mounted) setError(e instanceof Error ? e.message : 'Error loading data') 
      }
      if (mounted) setLoading(false)
    }
    fetchData()
    return () => { mounted = false }
  }, [bidId, agentName])

  const runAgent = async () => {
    if (!bidId || !agentName || running) return
    setRunning(true)
    setError(null)
    // Capture current output as "before" for diff
    if (output) setPrevOutput(output)
    setShowDiff(false)
    try {
      const result = await api.runAgent(bidId, agentName)
      setOutput(result)
      const b = await api.getBid(bidId)
      setBid(b)
    } catch (e: unknown) { 
      setError(e instanceof Error ? e.message : 'Agent execution failed') 
    }
    setRunning(false)
  }

  if (loading) return <div className="loading-page"><div className="loading-spinner" /><span style={{ color: 'var(--text-muted)' }}>Loading...</span></div>

  const hasOutput = output && output.status !== 'failed'
  const isFailed = output?.status === 'failed'
  // Safely unwrap agent result from the envelope {status, agent, result, timestamp}
   
  const agentResult: Record<string, any> = (() => {
    if (!output) return {}
    // If the output has a 'result' key, use it (standard envelope)
    if (output.result && typeof output.result === 'object') return output.result as Record<string, any>
    // Otherwise strip known envelope keys and use the rest
     
    const { status: _s, agent: _a, timestamp: _t, ...rest } = output as Record<string, any>
    return rest
  })()
  const narrative = agentResult?.narrative || ''
  const hitlSummary = agentResult?.hitl_summary || ''

  // Commercial-specific data
  const plModel = agentResult?.pl_model
  const resourcePlan = agentResult?.resource_plan
  const monthlyData = agentResult?.resource_loading?.monthly_summary

  // Automation AI-specific data
  const platformSections = agentResult?.platform_sections || []
  const prioritisationTable = agentResult?.prioritisation_table || []
  const priorityBreakdown = agentResult?.priority_breakdown
  const clientContext = agentResult?.client_context
  const crossPlatform = agentResult?.cross_platform || []

  // Strategic pipeline order â€” matches backend
  const AGENT_ORDER = [
    'intake', 'data_analyst', 'client_intelligence', 'strategic_assessment', 'solution_scope',
    'automation_ai', 'transition_change', 'commercial_model', 'compliance_risk', 'proposal_generator', 'discovery', 'feedback_learning',
  ]
  const currentIdx = AGENT_ORDER.indexOf(agentName || '')
  const prevAgent = currentIdx > 0 ? AGENT_ORDER[currentIdx - 1] : null
  const nextAgent = currentIdx < AGENT_ORDER.length - 1 ? AGENT_ORDER[currentIdx + 1] : null
  const prevMeta = prevAgent ? (AGENT_META[prevAgent] || { label: prevAgent }) : null
  const nextMeta = nextAgent ? (AGENT_META[nextAgent] || { label: nextAgent }) : null

  return (
    <div>
      {/* Navigation bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <button className="btn btn-ghost" onClick={() => navigate(`/bids/${bidId}`)} style={{ fontSize: 13, gap: 6 }}>
          <ArrowLeft size={14} /> Back to Bid
        </button>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {prevAgent && (
            <button
              className="btn btn-ghost"
              onClick={() => navigate(`/bids/${bidId}/agent/${prevAgent}`)}
              style={{ fontSize: 12, gap: 4, padding: '6px 12px', borderRadius: 8, border: '1px solid var(--border)' }}
            >
              <ArrowLeft size={12} /> {prevMeta?.label}
            </button>
          )}
          <span style={{ fontSize: 11, color: 'var(--text-muted)', padding: '0 4px' }}>
            {currentIdx + 1} / {AGENT_ORDER.length}
          </span>
          {nextAgent && (
            <button
              className="btn btn-ghost"
              onClick={() => navigate(`/bids/${bidId}/agent/${nextAgent}`)}
              style={{ fontSize: 12, gap: 4, padding: '6px 12px', borderRadius: 8, border: '1px solid var(--border)' }}
            >
              {nextMeta?.label} <ArrowLeft size={12} style={{ transform: 'rotate(180deg)' }} />
            </button>
          )}
        </div>
      </div>

      {/* Agent Header */}
      <div className="glass-card" style={{ marginBottom: 20, borderLeft: `4px solid ${meta.color}` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
            <div style={{ width: 48, height: 48, borderRadius: 12, background: `${meta.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <IconComp size={24} style={{ color: meta.color }} />
            </div>
            <div>
              <h2 style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>{meta.label}</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: 13, maxWidth: 600 }}>{meta.description}</p>
              {bid && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8, fontFamily: 'var(--font-mono)' }}>Bid: {bid.bid_reference as string} Â· {bid.client_name as string}</div>}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {hasOutput && <span className="status-badge low" style={{ fontSize: 12 }}><CheckCircle size={12} /> Completed</span>}
            {isFailed && <span className="status-badge high" style={{ fontSize: 12 }}><XCircle size={12} /> Failed</span>}
            {!output && <span className="status-badge" style={{ fontSize: 12, background: 'var(--bg-tertiary)' }}><Clock size={12} /> Not Run</span>}
            {/* Diff toggle â€” only shows after re-run */}
            {prevOutput && output && !running && (
              <button
                className={`btn ${showDiff ? 'btn-primary' : 'btn-ghost'}`}
                style={{ fontSize: 12, padding: '6px 12px', gap: 4 }}
                onClick={() => setShowDiff(d => !d)}
              >
                âš¡ {showDiff ? 'Hide Diff' : 'View Diff'}
              </button>
            )}
            <button className={`btn ${hasOutput ? 'btn-ghost' : 'btn-primary'}`} style={{ fontSize: 13, padding: '8px 18px' }} disabled={running} onClick={runAgent}>
              {running ? <><div className="loading-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Running...</> : <><Play size={14} /> {hasOutput ? 'Re-run' : 'Run Agent'}</>}
            </button>
          </div>
        </div>
        {output?.timestamp ? <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 12, fontFamily: 'var(--font-mono)' }}>Last run: {new Date(output.timestamp as string).toLocaleString()}</div> : null}
      </div>

      {/* Error */}
      {error && (
        <div className="glass-card" style={{ marginBottom: 20, borderLeft: '4px solid var(--status-danger)', background: 'rgba(239,68,68,0.06)' }}>
          <div style={{ display: 'flex', gap: 10 }}>
            <AlertTriangle size={18} style={{ color: 'var(--status-danger)', flexShrink: 0, marginTop: 2 }} />
            <div><div style={{ fontWeight: 700, marginBottom: 4, fontSize: 14 }}>Agent Error</div><div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{error}</div></div>
          </div>
        </div>
      )}

      {/* Diff Panel â€” before/after re-run comparison */}
      {showDiff && prevOutput && output && (
        <div className="glass-card" style={{ marginBottom: 20, borderLeft: '4px solid #7C3AED' }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
            <h3 style={{ fontSize:14, fontWeight:700, display:'flex', alignItems:'center', gap:8 }}>
              âš¡ Output Diff â€” Before vs After Re-run
            </h3>
            <button className="btn btn-ghost" style={{ fontSize:11 }} onClick={() => setShowDiff(false)}>Close</button>
          </div>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
            {['Before','After'].map((label, li) => {
              const src: any = li === 0 ? prevOutput : output
              const result: any = src?.result ?? src
              const keys = Object.keys(result).filter(k => !['status','agent','timestamp','stale'].includes(k))
              return (
                <div key={label}>
                  <div style={{ fontSize:11, fontWeight:700, marginBottom:10, color: li===0 ? '#DC2626':'#059669',
                    textTransform:'uppercase', letterSpacing:'0.5px' }}>{label}</div>
                  {keys.slice(0,6).map(k => {
                    const v = result[k]
                    const prevR: any = li===1 ? (prevOutput?.result ?? prevOutput) : {}
                    const changed = li===1 && JSON.stringify(v) !== JSON.stringify(prevR[k])
                    return (
                      <div key={k} style={{ marginBottom:10,
                        background: changed ? 'rgba(5,150,105,0.06)' : 'var(--bg-glass)',
                        border: changed ? '1px solid rgba(5,150,105,0.2)' : '1px solid var(--border-subtle)',
                        borderRadius:'var(--radius-md)', padding:'8px 12px' }}>
                        <div style={{ fontSize:10, fontWeight:700, color:'var(--text-muted)', textTransform:'uppercase',
                          display:'flex', alignItems:'center', gap:4 }}>
                          {k.replace(/_/g,' ')}
                          {changed && <span style={{ color:'#059669', fontSize:9 }}>â- changed</span>}
                        </div>
                        <div style={{ fontSize:12, color:'var(--text-secondary)', marginTop:4, lineHeight:1.5,
                          maxHeight:80, overflow:'hidden' }}>
                          {typeof v === 'string' ? v.substring(0,180) : Array.isArray(v) ? v.slice(0,3).join(', ') : JSON.stringify(v).substring(0,180)}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* HITL Summary */}
      {hitlSummary && (
        <div className="glass-card" style={{ marginBottom: 20, borderLeft: '4px solid #3B82F6', padding: '16px 20px' }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-muted)' }}>Summary</h3>
          <p style={{ fontSize: 14, color: 'var(--text-primary)', lineHeight: 1.7 }}>{hitlSummary}</p>
        </div>
      )}

      {/* P&L Card (Commercial Model only) */}
      {plModel && (
        <div className="glass-card" style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16 }}>ðŸ“Š Financial Model (Calculated)</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
            {[
              { label: 'Total Contract Value', value: fmtUSD(plModel.revenue?.total_contract_value) },
              { label: 'Monthly Price', value: fmtUSD(plModel.revenue?.monthly_price) },
              { label: 'Gross Margin', value: `${plModel.profitability?.margin_percent || 0}%` },
              { label: 'Gross Profit', value: fmtUSD(plModel.profitability?.gross_profit) },
            ].map(s => (
              <div key={s.label} style={{ padding: '12px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{s.label}</div>
                <div style={{ fontSize: 20, fontWeight: 800, marginTop: 4, color: 'var(--text-primary)' }}>{s.value}</div>
              </div>
            ))}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <h4 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Cost Breakdown</h4>
              <table className="data-table" style={{ fontSize: 12 }}>
                <tbody>
                  {Object.entries(plModel.costs || {}).map(([k, v]) => (
                    <tr key={k}><td style={{ textTransform: 'capitalize' }}>{k.replace(/_/g, ' ')}</td><td style={{ textAlign: 'right', fontWeight: k === 'total_cogs' ? 700 : 400 }}>{fmtUSD(v as number)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div>
              <h4 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Revenue & Profit</h4>
              <table className="data-table" style={{ fontSize: 12 }}>
                <tbody>
                  {Object.entries(plModel.revenue || {}).map(([k, v]) => (
                    <tr key={k}><td style={{ textTransform: 'capitalize' }}>{k.replace(/_/g, ' ')}</td><td style={{ textAlign: 'right' }}>{fmtUSD(v as number)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Resource Plan Table (Commercial Model) */}
      {resourcePlan && resourcePlan.length > 0 && (
        <div className="glass-card" style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16 }}>ðŸ‘¥ Resource Plan</h3>
          <table className="data-table">
            <thead><tr><th>Role</th><th>Location</th><th>FTEs</th><th>Start</th><th>Justification</th></tr></thead>
            <tbody>
              { }
              {resourcePlan.map((r: Record<string, any>, i: number) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{r.role}</td>
                  <td><span className={`status-badge ${r.location === 'onshore' ? 'medium' : 'low'}`} style={{ fontSize: 10 }}>{r.location}</span></td>
                  <td>{r.count}</td>
                  <td>M{r.start_month || 1}</td>
                  <td style={{ fontSize: 12, color: 'var(--text-muted)', maxWidth: 300 }}>{r.justification}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Month-wise Loading (Commercial Model) */}
      {monthlyData && monthlyData.length > 0 && (
        <div className="glass-card" style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16 }}>ðŸ“… Monthly Loading Summary</h3>
          <table className="data-table">
            <thead><tr><th>Month</th><th>FTEs</th><th>Monthly Cost</th></tr></thead>
            <tbody>
              { }
              {monthlyData.map((m: Record<string, any>) => (
                <tr key={m.month}><td>Month {m.month}</td><td>{m.fte}</td><td>${m.cost.toLocaleString()}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Automation & AI â€” Platform Sections + Prioritisation */}
      {platformSections.length > 0 && (
        <>
          {/* Priority Breakdown */}
          {priorityBreakdown && (
            <div className="glass-card" style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16 }}>âš¡ Automation Opportunities Overview</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 16 }}>
                {[
                  { label: 'Total', value: agentResult?.total_opportunities || 0, color: '#3B82F6' },
                  { label: 'Critical', value: priorityBreakdown.critical || 0, color: '#DC2626' },
                  { label: 'High', value: priorityBreakdown.high || 0, color: '#F59E0B' },
                  { label: 'Medium', value: priorityBreakdown.medium || 0, color: '#10B981' },
                  { label: 'Lower', value: priorityBreakdown.lower || 0, color: '#6B7280' },
                ].map(s => (
                  <div key={s.label} style={{ padding: '12px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{s.label}</div>
                    <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4, color: s.color }}>{s.value}</div>
                  </div>
                ))}
              </div>
              {clientContext?.products_in_scope && (
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Products: <strong style={{ color: 'var(--text-primary)' }}>{clientContext.products_in_scope.join(', ')}</strong></div>
              )}
            </div>
          )}

          {/* Per-Platform Sections */}
          { }
          {platformSections.map((section: Record<string, any>, si: number) => (
            <div className="glass-card" key={si} style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>{section.platform_name || section.platform}</h3>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>{section.platform_summary || section.summary} â€” {section.opportunity_count || section.opportunities?.length || 0} opportunities</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                { }
                {(section.opportunities || []).map((opp: Record<string, any>, oi: number) => {
                  const prioColor = opp.priority === 'CRITICAL' ? '#DC2626' : opp.priority === 'HIGH' ? '#F59E0B' : opp.priority === 'MEDIUM' ? '#10B981' : '#6B7280'
                  return (
                    <div key={oi} style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', borderLeft: `3px solid ${prioColor}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                        <div>
                          <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginRight: 8 }}>{opp.id}</span>
                          <span style={{ fontSize: 14, fontWeight: 700 }}>{opp.title}</span>
                        </div>
                        <span style={{ fontSize: 10, fontWeight: 700, color: prioColor, background: `${prioColor}15`, padding: '2px 8px', borderRadius: 4 }}>{opp.priority}</span>
                      </div>
                      {opp.rfp_trigger && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6, fontStyle: 'italic' }}>RFP: {opp.rfp_trigger}</div>}
                      <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8, lineHeight: 1.6 }}>{opp.what || opp.automation_description || ''}</div>
                      {(opp.sub_items || opp.specific_automations || []).length > 0 && (
                        <ul style={{ fontSize: 12, color: 'var(--text-secondary)', paddingLeft: 20, marginBottom: 8 }}>
                          { }
                          {(opp.sub_items || opp.specific_automations || []).map((item: any, ii: number) => (
                            <li key={ii} style={{ marginBottom: 3 }}>{typeof item === 'string' ? item : `${item.name}: ${item.description}`}</li>
                          ))}
                        </ul>
                      )}
                      <div style={{ display: 'flex', gap: 16, fontSize: 11, color: 'var(--text-muted)' }}>
                        <span>Effort: <strong>{opp.effort || opp.effort_estimate}</strong></span>
                        <span>Horizon: <strong>{opp.horizon}</strong></span>
                        {opp.risk_rating && <span>Risk: {'â˜…'.repeat(opp.risk_rating)}{'â˜†'.repeat(5 - opp.risk_rating)}</span>}
                      </div>
                      {opp.benefit && <div style={{ fontSize: 12, color: '#10B981', marginTop: 6 }}>â†- {typeof opp.benefit === 'string' ? opp.benefit : opp.expected_benefit}</div>}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}

          {/* Cross-Platform Opportunities */}
          {crossPlatform.length > 0 && (
            <div className="glass-card" style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Cross-Platform Opportunities</h3>
              { }
              {crossPlatform.map((opp: Record<string, any>, i: number) => (
                <div key={i} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', marginBottom: 8 }}>
                  <div style={{ fontSize: 13, fontWeight: 700 }}><span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginRight: 8 }}>{opp.id}</span>{opp.title}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{opp.description}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>Platforms: {(opp.platforms || []).join(', ')} Â· Effort: {opp.effort} Â· <span style={{ color: opp.priority === 'CRITICAL' ? '#DC2626' : '#F59E0B' }}>{opp.priority}</span></div>
                </div>
              ))}
            </div>
          )}

          {/* Prioritisation Table */}
          {prioritisationTable.length > 0 && (
            <div className="glass-card" style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16 }}>ðŸ“‹ Consolidated Prioritisation</h3>
              <table className="data-table">
                <thead><tr><th>ID</th><th>Opportunity</th><th>Platform</th><th>Risk</th><th>Effort</th><th>Horizon</th><th>Priority</th></tr></thead>
                <tbody>
                  { }
                  {prioritisationTable.map((row: Record<string, any>, i: number) => {
                    const prioColor = row.priority === 'CRITICAL' ? '#DC2626' : row.priority === 'HIGH' ? '#F59E0B' : row.priority === 'MEDIUM' ? '#10B981' : '#6B7280'
                    return (
                      <tr key={i}>
                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{row.id}</td>
                        <td style={{ fontWeight: 600, maxWidth: 280 }}>{row.title}</td>
                        <td style={{ fontSize: 12 }}>{row.platform}</td>
                        <td>{'â˜…'.repeat(row.risk_rating || 0)}{'â˜†'.repeat(5 - (row.risk_rating || 0))}</td>
                        <td style={{ fontSize: 12 }}>{row.effort}</td>
                        <td style={{ fontSize: 12 }}>{row.horizon}</td>
                        <td><span style={{ fontSize: 10, fontWeight: 700, color: prioColor }}>{row.priority}</span></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Agent-Specific Rich Cards */}
      {hasOutput && agentName === 'intake' && <IntakeRenderer data={agentResult} />}
      {hasOutput && agentName === 'data_analyst' && <DataAnalystRenderer data={agentResult} />}
      {hasOutput && agentName === 'client_intelligence' && <ClientIntelRenderer data={agentResult} />}
      {hasOutput && agentName === 'strategic_assessment' && <><BidNoBidRenderer data={agentResult} /><CompetitiveRenderer data={agentResult} /></>}
      {hasOutput && agentName === 'solution_scope' && <><ScopeRenderer data={agentResult} /><SolutionRenderer data={agentResult} /></>}
      {hasOutput && agentName === 'automation_ai' && <AISolutioningRenderer data={agentResult} />}
      {hasOutput && agentName === 'transition_change' && <TransitionChangeRenderer data={agentResult} />}
      {hasOutput && agentName === 'commercial_model' && <CommercialRenderer data={agentResult} />}
      {hasOutput && agentName === 'compliance_risk' && <ComplianceRenderer data={agentResult} />}
      {hasOutput && agentName === 'proposal_generator' && <ProposalWriterRenderer data={agentResult} manifest={bid?.manifest || {}} />}
      {hasOutput && agentName === 'discovery' && <DiscoveryRenderer data={agentResult} bidId={bidId} />}
      {hasOutput && agentName === 'feedback_learning' && <FeedbackRenderer data={agentResult} />}

      {/* Narrative */}
      {hasOutput && narrative && agentName !== 'proposal_generator' && (
        <div className="glass-card" style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileText size={16} /> Strategic Narrative
          </h3>
          <div>
            <NarrativeRenderer text={narrative as string} />
          </div>
        </div>
      )}

      {/* Empty state */}
      {!output && !error && (
        <div className="glass-card" style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 48, marginBottom: 16, display: 'flex', justifyContent: 'center' }}><IconComp size={48} /></div>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>Agent Not Yet Executed</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, maxWidth: 400, margin: '0 auto 20px' }}>
            Click "Run Agent" to execute {meta.label}. The agent will process the RFP through its OODA loop and produce a detailed analysis.
          </div>
          <button className="btn btn-primary" onClick={runAgent} disabled={running}>
            <Play size={16} /> {running ? 'Running...' : 'Run Agent Now'}
          </button>
        </div>
      )}
    </div>
  )
}