import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { TrendingUp, Users, AlertTriangle, Clock, DollarSign, Target, Plus, RefreshCw, Trash2, FolderKanban as FolderIcon } from 'lucide-react'

interface Stats { active_bids: number; total_pipeline_tcv: number; avg_win_probability: number; pending_hitl_gates: number; at_risk_bids: number; bids_won: number; bids_lost: number; avg_cycle_days: number }
interface Bid { id: string; bid_reference: string; client_name: string; client_industry: string; contract_type: string; products: string[]; status: string; deadline_risk: string; win_probability: number; estimated_tcv: number; submission_deadline: string; current_agent: string }

const STATUS_LABELS: Record<string, string> = {
  created: 'Created', intake_processing: 'Intake Processing', intake_review: 'Intake Review',
  bid_no_bid: 'Bid/No-Bid', scope_building: 'Scope Building', scope_review: 'Scope Review',
  solution_design: 'Solution Design', solution_review: 'Solution Review',
  strategy_alignment: 'Strategy Alignment', commercial_modeling: 'Commercial Modeling',
  commercial_approval: 'Commercial Approval', compliance_review: 'Compliance Review',
  legal_sign_off: 'Legal Sign-off', output_generation: 'Output Gen',
  qa_review: 'QA Review', final_review: 'Final Review',
  submitted: 'Submitted', won: 'Won', lost: 'Lost'
}

const AGENT_LABELS: Record<string, string> = {
  intake: 'RFP Intake', data_analyst: 'Data Intelligence', client_intelligence: 'Client Intel',
  strategic_assessment: 'Strategic Assessment', solution_scope: 'Solution Design', automation_ai: 'Automation AI',
  transition_change: 'Transition', commercial_model: 'Commercial', compliance_risk: 'Compliance',
  proposal_generator: 'Proposal Writer', discovery: 'Discovery', feedback_learning: 'Learning & Feedback',
  qa: 'QA Review', output: 'Output Gen',
}

function formatTCV(v: number) { return v >= 1_000_000 ? `$${(v/1_000_000).toFixed(1)}M` : `$${(v/1000).toFixed(0)}K` }
function daysUntil(d: string) { const diff = (new Date(d).getTime() - Date.now()) / 86400000; return Math.ceil(diff) }

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<Stats | null>(null)
  const [bids, setBids] = useState<Bid[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [s, b] = await Promise.all([api.getBidStats(), api.getBids()])
      setStats(s); setBids(b)
    } catch (e) { console.error('Dashboard fetch error:', e) }
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [])

  if (loading || !stats) return <div className="loading-page"><div className="loading-spinner" /><span style={{color:'var(--text-muted)'}}>Loading dashboard...</span></div>

  const metrics = [
    { label: 'Active Bids', value: stats.active_bids, icon: FolderIcon, color: '#2563EB', gradient: true },
    { label: 'Pipeline TCV', value: formatTCV(stats.total_pipeline_tcv), icon: DollarSign, color: '#059669' },
    { label: 'Avg Win Prob', value: `${(stats.avg_win_probability * 100).toFixed(0)}%`, icon: Target, color: '#7C3AED' },
    { label: 'At Risk', value: stats.at_risk_bids, icon: AlertTriangle, color: '#DC2626' },
  ]

  return (
    <div>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:24 }}>
        <div>
          <h2 style={{ fontSize:24, fontWeight:800 }}>Bid Pipeline</h2>
          <p style={{ color:'var(--text-muted)', fontSize:13, marginTop:4 }}>Real-time overview of all active pre-sales engagements</p>
        </div>
        <div style={{ display:'flex', gap:10 }}>
          <button className="btn btn-ghost" onClick={fetchData}><RefreshCw size={14} /> Refresh</button>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}><Plus size={14} /> New Bid</button>
          <button className="btn" style={{ background:'#DC2626', color:'#fff', border:'none' }} onClick={async () => {
            if (window.confirm('Reset ALL data? This will permanently delete all bids, KB documents, agent results, and generated files. This cannot be undone.')) {
              try { await api.clearAllBids(); await fetchData(); alert('All data reset successfully.') }
              catch (e) { alert('Reset failed: ' + e) }
            }
          }}><Trash2 size={14} /> Reset All Data</button>
        </div>
      </div>

      <div className="metrics-grid">
        {metrics.map(m => (
          <div className="metric-card" key={m.label}>
            <div className="metric-icon" style={{ background: `${m.color}15` }}>
              <m.icon size={20} style={{ color: m.color }} />
            </div>
            <div className="metric-label">{m.label}</div>
            <div className={`metric-value ${m.gradient ? 'gradient' : ''}`}>{m.value}</div>
          </div>
        ))}
      </div>

      <h3 style={{ fontSize:16, fontWeight:700, marginBottom:16 }}>Active Bids</h3>
      <div className="bids-grid">
        {bids.map(bid => (
          <div className="bid-card" key={bid.id} onClick={() => navigate(`/bids/${bid.id}`)} style={{ cursor: 'pointer' }}>
            <div className="bid-card-header">
              <div>
                <div className="bid-client">{bid.client_name}</div>
                <div className="bid-ref">{bid.bid_reference}</div>
              </div>
              <span className={`status-badge ${bid.deadline_risk}`}>{bid.deadline_risk} risk</span>
            </div>
            <div className="bid-card-body">
              <div className="bid-meta">
                {bid.client_industry && <span className="bid-tag industry">{bid.client_industry}</span>}
                {bid.contract_type && <span className="bid-tag type">{bid.contract_type.toUpperCase()}</span>}
                {bid.products?.slice(0,2).map(p => <span className="bid-tag product" key={p}>{p}</span>)}
              </div>
              <div style={{ display:'flex', alignItems:'center', gap:8, fontSize:13 }}>
                <span className="stage-badge">{STATUS_LABELS[bid.status] || bid.status}</span>
                <span style={{ color:'var(--text-muted)', fontSize:12 }}>â†’ {AGENT_LABELS[bid.current_agent] || bid.current_agent}</span>
              </div>
              {bid.win_probability != null && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                    <span>Win Probability</span><span style={{ fontWeight:600, color:'var(--text-primary)' }}>{(bid.win_probability <= 1 ? bid.win_probability * 100 : bid.win_probability).toFixed(0)}%</span>
                  </div>
                  <div className="prob-bar">
                    <div className={`prob-bar-fill ${(bid.win_probability <= 1 ? bid.win_probability : bid.win_probability / 100) >= 0.7 ? 'high' : (bid.win_probability <= 1 ? bid.win_probability : bid.win_probability / 100) >= 0.5 ? 'medium' : 'low'}`} style={{ width: `${(bid.win_probability <= 1 ? bid.win_probability * 100 : bid.win_probability)}%` }} />
                  </div>
                </div>
              )}
            </div>
            <div className="bid-card-footer">
              <div className="bid-stats">
                <div className="bid-stat">
                  <div className="bid-stat-value">{bid.estimated_tcv ? formatTCV(bid.estimated_tcv) : 'â€”'}</div>
                  <div className="bid-stat-label">TCV</div>
                </div>
                <div className="bid-stat">
                  <div className="bid-stat-value">{bid.submission_deadline ? daysUntil(bid.submission_deadline) : 'â€”'}</div>
                  <div className="bid-stat-label">Days Left</div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {showCreate && <CreateBidModal onClose={() => setShowCreate(false)} onCreated={(bid) => { setShowCreate(false); if (bid?.id) navigate(`/bids/${bid.id}`); else fetchData() }} />}
    </div>
  )
}


function FolderKanbanIcon({ size = 20, style = {} }: any) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={style}><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/></svg>
}

function CreateBidModal({ onClose, onCreated }: { onClose: () => void; onCreated: (bid: any) => void }) {
  const [form, setForm] = useState({
    client_name: '', client_industry: '', contract_type: 'ams', products: '',
    known_competitors: '', incumbent_vendor: '', rate_onshore: '', rate_offshore: '', rate_nearshore: '',
    deal_size_estimate: '', past_relationship: '', additional_context: '', org_unit_id: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [orgNodes, setOrgNodes] = useState<any[]>([])
  const update = (k: string, v: any) => setForm(f => ({ ...f, [k]: v }))

  useState(() => { api.getOrgNodes().then(setOrgNodes).catch(() => {}) })

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setSubmitting(true)
    try {
      const payload: any = {
        client_name: form.client_name, client_industry: form.client_industry,
        contract_type: form.contract_type, products: form.products.split(',').map(p => p.trim()),
      }
      if (form.org_unit_id) {
        payload.org_unit_id = form.org_unit_id
        const selectedNode = orgNodes.find((n: any) => n.id === form.org_unit_id)
        payload.org_unit_label = selectedNode?.label || ''
      }
      if (form.known_competitors.trim()) payload.known_competitors = form.known_competitors.split(',').map((c: string) => c.trim())
      if (form.incumbent_vendor.trim()) payload.incumbent_vendor = form.incumbent_vendor.trim()
      if (form.rate_onshore) payload.rate_onshore_usd = parseFloat(form.rate_onshore)
      if (form.rate_offshore) payload.rate_offshore_usd = parseFloat(form.rate_offshore)
      if (form.rate_nearshore) payload.rate_nearshore_usd = parseFloat(form.rate_nearshore)
      if (form.deal_size_estimate) payload.deal_size_estimate = form.deal_size_estimate
      if (form.past_relationship) payload.past_relationship = form.past_relationship
      if (form.additional_context.trim()) payload.additional_context = form.additional_context.trim()
      const bid = await api.createBid(payload)
      onCreated(bid)
    } catch (e) { console.error(e) }
    setSubmitting(false)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxHeight: '85vh', overflow: 'auto' }} onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Create New Bid</h2>
          <button className="modal-close" onClick={onClose}>Ã-</button>
        </div>
        <form onSubmit={submit}>
          <div className="form-group">
            <label className="form-label">Client Name *</label>
            <input className="form-input" required value={form.client_name} onChange={e => update('client_name', e.target.value)} placeholder="e.g. Barclays PLC" autoFocus />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Industry</label>
              <select className="form-input" value={form.client_industry} onChange={e => update('client_industry', e.target.value)}>
                <option value="">Select...</option>
                {['Financial Services','Healthcare','Retail','Manufacturing','Technology','Energy','Government','Telecom','Education'].map(i => <option key={i} value={i}>{i}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Contract Type</label>
              <select className="form-input" value={form.contract_type} onChange={e => update('contract_type', e.target.value)}>
                <option value="ams">AMS</option><option value="implementation">Implementation</option>
                <option value="advisory">Advisory</option><option value="staff_aug">Staff Augmentation</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Products (comma-separated)</label>
            <input className="form-input" value={form.products} onChange={e => update('products', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 14 }}>ðŸ¢</span> Organization Unit
            </label>
            <select
              className="form-input"
              value={form.org_unit_id}
              onChange={e => update('org_unit_id', e.target.value)}
              style={{
                appearance: 'none',
                WebkitAppearance: 'none',
                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 12px center',
                paddingRight: 36,
                cursor: 'pointer',
              }}
            >
              <option value="">â€” Select Organization Unit â€”</option>
              {orgNodes.map((n: any) => <option key={n.id} value={n.id}>{'    '.repeat(Math.max(0, n.level - 1))}{n.level > 1 ? 'â””â”€ ' : 'â- '}{n.role} â€” {n.practice}</option>)}
            </select>
          </div>

          <button type="button" className="btn btn-ghost" onClick={() => setShowAdvanced(!showAdvanced)}
            style={{ fontSize: 12, marginTop: 8, gap: 6, color: 'var(--text-accent)', padding: '6px 0' }}>
            {showAdvanced ? 'â–¾ Hide Strategic Inputs' : 'â–¸ Add Strategic Inputs (Optional)'}
          </button>

          {showAdvanced && (
            <div style={{ marginTop: 12, padding: 16, background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group"><label className="form-label">Known Competitors</label>
                  <input className="form-input" value={form.known_competitors} onChange={e => update('known_competitors', e.target.value)} placeholder="e.g. Infosys, Accenture" /></div>
                <div className="form-group"><label className="form-label">Incumbent Vendor</label>
                  <input className="form-input" value={form.incumbent_vendor} onChange={e => update('incumbent_vendor', e.target.value)} placeholder="Current vendor" /></div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginTop: 12 }}>
                <div className="form-group"><label className="form-label">Onshore $/hr</label>
                  <input className="form-input" type="number" step="5" value={form.rate_onshore} onChange={e => update('rate_onshore', e.target.value)} placeholder="150" /></div>
                <div className="form-group"><label className="form-label">Nearshore $/hr</label>
                  <input className="form-input" type="number" step="5" value={form.rate_nearshore} onChange={e => update('rate_nearshore', e.target.value)} placeholder="85" /></div>
                <div className="form-group"><label className="form-label">Offshore $/hr</label>
                  <input className="form-input" type="number" step="5" value={form.rate_offshore} onChange={e => update('rate_offshore', e.target.value)} placeholder="45" /></div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
                <div className="form-group"><label className="form-label">Deal Size</label>
                  <select className="form-input" value={form.deal_size_estimate} onChange={e => update('deal_size_estimate', e.target.value)}>
                    <option value="">Select...</option><option value="small">Small (&lt;$500K)</option>
                    <option value="mid">Mid ($500Kâ€“$2M)</option><option value="large">Large ($2Mâ€“$10M)</option>
                    <option value="enterprise">Enterprise ($10M+)</option>
                  </select></div>
                <div className="form-group"><label className="form-label">Client Relationship</label>
                  <select className="form-input" value={form.past_relationship} onChange={e => update('past_relationship', e.target.value)}>
                    <option value="">Select...</option><option value="new">New Client</option>
                    <option value="existing">Existing Client</option><option value="renewal">Renewal</option>
                  </select></div>
              </div>
              <div className="form-group" style={{ marginTop: 12 }}><label className="form-label">Additional Context</label>
                <textarea className="form-input" rows={2} value={form.additional_context} onChange={e => update('additional_context', e.target.value)}
                  placeholder="Strategic context, pricing constraints, win themes..." style={{ resize: 'vertical', minHeight: 40 }} /></div>
            </div>
          )}

          <div style={{ display:'flex', gap:10, justifyContent:'flex-end', marginTop:20 }}>
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting || !form.client_name.trim()}>
              {submitting ? 'Creating...' : 'Create Bid'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}