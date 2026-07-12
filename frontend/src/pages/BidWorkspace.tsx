import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { Plus, ChevronRight, Download, Loader2, Search, SlidersHorizontal, ArrowUpDown, X, LayoutGrid, List } from 'lucide-react'

interface Bid {
  id: string; bid_reference: string; client_name: string; client_industry: string;
  contract_type: string; products: string[]; status: string; deadline_risk: string;
  win_probability: number; estimated_tcv: number; current_agent: string;
  bid_recommendation: string; created_at: string; documents: any[];
  org_unit_id?: string; org_unit_label?: string;
}

interface OrgNodeOption {
  id: string; role: string; practice: string; level: number; label: string;
}

const STATUS_LABELS: Record<string, string> = {
  created: 'Created', intake_processing: 'Intake', intake_review: 'Intake Review',
  bid_no_bid: 'Bid/No-Bid', scope_building: 'Scope', scope_review: 'Scope Review',
  solution_design: 'Solution', solution_review: 'Solution Review',
  strategy_alignment: 'Strategy', commercial_modeling: 'Commercial',
  commercial_approval: 'Commercial Approval', compliance_review: 'Compliance',
  legal_sign_off: 'Legal', output_generation: 'Output Gen',
  qa_review: 'QA', final_review: 'Final Review', submitted: 'Submitted',
}


const INDUSTRIES = ['Financial Services','Healthcare','Retail','Manufacturing','Technology','Energy','Government','Telecom','Education']
const SORT_OPTIONS = [
  { value: 'created_at', label: 'Date Created' },
  { value: 'client_name', label: 'Client Name' },
  { value: 'deadline', label: 'Deadline' },
  { value: 'win_probability', label: 'Win Probability' },
  { value: 'tcv', label: 'TCV Value' },
]

export default function BidWorkspace() {
  const navigate = useNavigate()
  const [bids, setBids] = useState<Bid[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)
  const [generating, setGenerating] = useState<Record<string, boolean>>({})
  const [form, setForm] = useState({
    client_name: '', client_industry: '', contract_type: 'ams', products: '',
    known_competitors: '', incumbent_vendor: '', rate_onshore: '', rate_offshore: '', rate_nearshore: '',
    deal_size_estimate: '', past_relationship: '', additional_context: '', org_unit_id: '',
  })
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [orgNodes, setOrgNodes] = useState<OrgNodeOption[]>([])

  // Search / Filter / Sort state
  const [searchQ, setSearchQ] = useState('')
  const [filterIndustry, setFilterIndustry] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState<'asc'|'desc'>('desc')
  const [showFilters, setShowFilters] = useState(false)
  const [viewMode, setViewMode] = useState<'list'|'kanban'>('list')
  // TCV range filter (in $M)
  const [tcvMin, setTcvMin] = useState('')
  const [tcvMax, setTcvMax] = useState('')
  // Drag state for Kanban
  const dragBid = useRef<string | null>(null)

  const fetchBids = useCallback(async () => {
    try {
      const params: any = {}
      if (searchQ.trim()) params.search = searchQ.trim()
      if (filterIndustry) params.industry = filterIndustry
      if (filterStatus) params.status = filterStatus
      params.sort_by = sortBy
      params.sort_order = sortOrder
      let results = await api.getBids(params)
      // Client-side TCV range filter
      if (tcvMin) results = results.filter((b: Bid) => (b.estimated_tcv || 0) >= Number(tcvMin) * 1e6)
      if (tcvMax) results = results.filter((b: Bid) => (b.estimated_tcv || 0) <= Number(tcvMax) * 1e6)
      setBids(results)
    } catch (e) { console.error(e) }
    setLoading(false)
  }, [searchQ, filterIndustry, filterStatus, sortBy, sortOrder, tcvMin, tcvMax])

  useEffect(() => { fetchBids() }, [fetchBids])
  useEffect(() => {
    api.getOrgNodes().then(setOrgNodes).catch(() => {})
  }, [])

  const createBid = async () => {
    if (!form.client_name.trim()) return
    setCreating(true)
    try {
      const payload: any = {
        client_name: form.client_name, client_industry: form.client_industry,
        contract_type: form.contract_type, products: form.products.split(',').map(p => p.trim()),
      }
      // Org unit linkage
      if (form.org_unit_id) {
        payload.org_unit_id = form.org_unit_id
        const selectedNode = orgNodes.find(n => n.id === form.org_unit_id)
        payload.org_unit_label = selectedNode?.label || ''
      }
      // Optional strategic inputs
      if (form.known_competitors.trim()) payload.known_competitors = form.known_competitors.split(',').map((c: string) => c.trim())
      if (form.incumbent_vendor.trim()) payload.incumbent_vendor = form.incumbent_vendor.trim()
      if (form.rate_onshore) payload.rate_onshore_usd = parseFloat(form.rate_onshore)
      if (form.rate_offshore) payload.rate_offshore_usd = parseFloat(form.rate_offshore)
      if (form.rate_nearshore) payload.rate_nearshore_usd = parseFloat(form.rate_nearshore)
      if (form.deal_size_estimate) payload.deal_size_estimate = form.deal_size_estimate
      if (form.past_relationship) payload.past_relationship = form.past_relationship
      if (form.additional_context.trim()) payload.additional_context = form.additional_context.trim()
      const bid = await api.createBid(payload)
      setShowCreate(false)
      setForm({ client_name: '', client_industry: '', contract_type: 'ams', products: '',
        known_competitors: '', incumbent_vendor: '', rate_onshore: '', rate_offshore: '', rate_nearshore: '',
        deal_size_estimate: '', past_relationship: '', additional_context: '', org_unit_id: '' })
      navigate(`/bids/${bid.id}`)
    } catch (e) { console.error(e) }
    setCreating(false)
  }

  const generateDoc = async (bidId: string) => {
    setGenerating(p => ({ ...p, [bidId]: true }))
    try {
      const result = await api.generateSOW(bidId)
      if (result.doc_id) window.open(api.getDownloadUrl(result.doc_id), '_blank')
    } catch (e: any) {
      alert(`Generation failed: ${e.message}`)
    }
    setGenerating(p => ({ ...p, [bidId]: false }))
  }

  const clearFilters = () => { setSearchQ(''); setFilterIndustry(''); setFilterStatus(''); setSortBy('created_at'); setSortOrder('desc'); setTcvMin(''); setTcvMax('') }
  const hasActiveFilters = searchQ || filterIndustry || filterStatus || sortBy !== 'created_at' || tcvMin || tcvMax

  // â”€â”€ Kanban helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const KANBAN_COLUMNS = [
    { id: 'active',     label: 'Active',      statuses: ['created','intake_processing','intake_review','bid_no_bid'],      color: '#3B82F6' },
    { id: 'strategy',  label: 'Strategy',    statuses: ['scope_building','scope_review','solution_design','strategy_alignment'], color: '#8B5CF6' },
    { id: 'commercial',label: 'Commercial',  statuses: ['commercial_modeling','commercial_approval'],                     color: '#06B6D4' },
    { id: 'legal',     label: 'Legal',       statuses: ['compliance_review','legal_sign_off'],                           color: '#F97316' },
    { id: 'final',     label: 'Final',       statuses: ['output_generation','qa_review','final_review','submitted'],      color: '#10B981' },
    { id: 'outcome',   label: 'Outcome',     statuses: ['won','lost','abandoned','no_bid'],                              color: '#6B7280' },
  ]

  const getBidsInColumn = (col: typeof KANBAN_COLUMNS[0]) =>
    bids.filter(b => col.statuses.includes(b.status))

  const handleDrop = async (e: React.DragEvent, targetColumnId: string) => {
    e.preventDefault()
    const bidId = dragBid.current
    if (!bidId) return
    const col = KANBAN_COLUMNS.find(c => c.id === targetColumnId)
    if (!col) return
    // Move to first status of target column
    const newStatus = col.statuses[0]
    try {
      await api.updateBidStatus(bidId, newStatus)
      await fetchBids()
    } catch (e) { console.error(e) }
    dragBid.current = null
  }

  if (loading) return <div className="loading-page"><div className="loading-spinner" /></div>

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 24, fontWeight: 800 }}>Bid Workspace</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>{bids.length} bids in pipeline</p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* View toggle */}
          <div style={{ display:'flex', borderRadius:'var(--radius-md)', border:'1px solid var(--border-default)', overflow:'hidden' }}>
            <button
              style={{ padding:'6px 10px', border:'none', cursor:'pointer', fontSize:12,
                background: viewMode==='list' ? 'var(--accent-primary,#0066FF)' : 'transparent',
                color: viewMode==='list' ? '#fff' : 'var(--text-muted)',
                display:'flex', alignItems:'center', gap:4, transition:'all 150ms' }}
              onClick={() => setViewMode('list')}>
              <List size={14} /> List
            </button>
            <button
              style={{ padding:'6px 10px', border:'none', cursor:'pointer', fontSize:12,
                background: viewMode==='kanban' ? 'var(--accent-primary,#0066FF)' : 'transparent',
                color: viewMode==='kanban' ? '#fff' : 'var(--text-muted)',
                display:'flex', alignItems:'center', gap:4, transition:'all 150ms' }}
              onClick={() => setViewMode('kanban')}>
              <LayoutGrid size={14} /> Kanban
            </button>
          </div>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}><Plus size={16} /> New Bid</button>
        </div>
      </div>

      {/* Search / Filter / Sort Bar */}
      <div className="glass-card" style={{ marginBottom: 16, padding: '12px 16px' }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input className="form-input" placeholder="Search bids by name, reference, or industry..."
              value={searchQ} onChange={e => setSearchQ(e.target.value)}
              style={{ paddingLeft: 32, fontSize: 13, height: 36 }} />
          </div>
          <button className={`btn ${showFilters ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setShowFilters(!showFilters)}
            style={{ fontSize: 12, padding: '6px 12px', gap: 4 }}>
            <SlidersHorizontal size={14} /> Filters
          </button>
          {hasActiveFilters && (
            <button className="btn btn-ghost" onClick={clearFilters} style={{ fontSize: 11, padding: '6px 10px', gap: 4, color: 'var(--status-danger)' }}>
              <X size={12} /> Clear
            </button>
          )}
        </div>
        {showFilters && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border-subtle)' }}>
            <div>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>Industry</label>
              <select className="form-input" value={filterIndustry} onChange={e => setFilterIndustry(e.target.value)} style={{ fontSize: 12 }}>
                <option value="">All Industries</option>
                {INDUSTRIES.map(i => <option key={i}>{i}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>Status</label>
              <select className="form-input" value={filterStatus} onChange={e => setFilterStatus(e.target.value)} style={{ fontSize: 12 }}>
                <option value="">All Statuses</option>
                {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>TCV Range ($M)</label>
              <div style={{ display:'flex', gap:4, alignItems:'center' }}>
                <input className="form-input" type="number" placeholder="Min" value={tcvMin}
                  onChange={e => setTcvMin(e.target.value)} style={{ fontSize:11, flex:1 }} />
                <span style={{ fontSize:11, color:'var(--text-muted)' }}>â€”</span>
                <input className="form-input" type="number" placeholder="Max" value={tcvMax}
                  onChange={e => setTcvMax(e.target.value)} style={{ fontSize:11, flex:1 }} />
              </div>
            </div>
            <div>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>Sort By</label>
              <div style={{ display: 'flex', gap: 4 }}>
                <select className="form-input" value={sortBy} onChange={e => setSortBy(e.target.value)} style={{ fontSize: 12, flex: 1 }}>
                  {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <button className="btn btn-ghost" onClick={() => setSortOrder(o => o === 'asc' ? 'desc' : 'asc')}
                  style={{ fontSize: 11, padding: '4px 8px' }} title={sortOrder === 'asc' ? 'Ascending' : 'Descending'}>
                  <ArrowUpDown size={13} /> {sortOrder === 'asc' ? 'â†‘' : 'â†“'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Create Bid Modal */}
      {showCreate && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
          onClick={() => setShowCreate(false)}>
          <div className="glass-card" style={{ width: 560, maxWidth: '90vw', maxHeight: '85vh', overflow: 'auto' }} onClick={e => e.stopPropagation()}>
            <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20 }}>Create New Bid</h3>
            <div className="form-group">
              <label className="form-label">Client Name *</label>
              <input className="form-input" value={form.client_name} onChange={e => setForm(f => ({ ...f, client_name: e.target.value }))} placeholder="e.g. Barclays PLC" autoFocus />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label className="form-label">Industry</label>
                <select className="form-input" value={form.client_industry} onChange={e => setForm(f => ({ ...f, client_industry: e.target.value }))}>
                  <option value="">Select...</option>
                  <option>Financial Services</option><option>Healthcare</option><option>Retail</option>
                  <option>Manufacturing</option><option>Technology</option><option>Energy</option>
                  <option>Government</option><option>Telecom</option><option>Education</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Contract Type</label>
                <select className="form-input" value={form.contract_type} onChange={e => setForm(f => ({ ...f, contract_type: e.target.value }))}>
                  <option value="ams">AMS</option><option value="implementation">Implementation</option>
                  <option value="advisory">Advisory</option><option value="staff_aug">Staff Augmentation</option>
                </select>
              </div>
            </div>
            <div className="form-group" style={{ marginTop: 12 }}>
              <label className="form-label">Products (comma-separated)</label>
              <input className="form-input" value={form.products} onChange={e => setForm(f => ({ ...f, products: e.target.value }))} />
            </div>

            {/* Org Unit Selection */}
            <div className="form-group" style={{ marginTop: 12 }}>
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 14 }}>ðŸ¢</span> Organization Unit
              </label>
              <div style={{ position: 'relative' }}>
                <select
                  className="form-input"
                  value={form.org_unit_id}
                  onChange={e => setForm(f => ({ ...f, org_unit_id: e.target.value }))}
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
                  {orgNodes.map(n => (
                    <option key={n.id} value={n.id}>
                      {'    '.repeat(Math.max(0, n.level - 1))}{n.level > 1 ? 'â””â”€ ' : 'â- '}{n.role} â€” {n.practice}
                    </option>
                  ))}
                </select>
              </div>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4, display: 'block' }}>Links this bid to the organizational hierarchy for pipeline reporting</span>
            </div>

            {/* Toggle for Advanced/Optional Inputs */}
            <button className="btn btn-ghost" onClick={() => setShowAdvanced(!showAdvanced)}
              style={{ fontSize: 12, marginTop: 16, gap: 6, color: 'var(--text-accent)', padding: '6px 0' }}>
              {showAdvanced ? 'â–¾ Hide Strategic Inputs' : 'â–¸ Add Strategic Inputs (Optional)'}
            </button>

            {showAdvanced && (
              <div style={{ marginTop: 12, padding: '16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 0.5 }}>These inputs become the foundation for ALL agent analysis</div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div className="form-group">
                    <label className="form-label">Known Competitors (comma-separated)</label>
                    <input className="form-input" value={form.known_competitors} onChange={e => setForm(f => ({ ...f, known_competitors: e.target.value }))} placeholder="e.g. Infosys, Accenture, TCS" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Incumbent Vendor</label>
                    <input className="form-input" value={form.incumbent_vendor} onChange={e => setForm(f => ({ ...f, incumbent_vendor: e.target.value }))} placeholder="Current vendor if any" />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label className="form-label">Onshore Rate ($/hr)</label>
                    <input className="form-input" type="number" step="5" value={form.rate_onshore} onChange={e => setForm(f => ({ ...f, rate_onshore: e.target.value }))} placeholder="e.g. 150" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Nearshore Rate ($/hr)</label>
                    <input className="form-input" type="number" step="5" value={form.rate_nearshore} onChange={e => setForm(f => ({ ...f, rate_nearshore: e.target.value }))} placeholder="e.g. 85" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Offshore Rate ($/hr)</label>
                    <input className="form-input" type="number" step="5" value={form.rate_offshore} onChange={e => setForm(f => ({ ...f, rate_offshore: e.target.value }))} placeholder="e.g. 45" />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label className="form-label">Deal Size Estimate</label>
                    <select className="form-input" value={form.deal_size_estimate} onChange={e => setForm(f => ({ ...f, deal_size_estimate: e.target.value }))}>
                      <option value="">Select...</option>
                      <option value="small">Small (&lt;$500K)</option>
                      <option value="mid">Mid ($500Kâ€“$2M)</option>
                      <option value="large">Large ($2Mâ€“$10M)</option>
                      <option value="enterprise">Enterprise ($10M+)</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Client Relationship</label>
                    <select className="form-input" value={form.past_relationship} onChange={e => setForm(f => ({ ...f, past_relationship: e.target.value }))}>
                      <option value="">Select...</option>
                      <option value="new">New Client</option>
                      <option value="existing">Existing Client</option>
                      <option value="renewal">Contract Renewal</option>
                    </select>
                  </div>
                </div>

                <div className="form-group" style={{ marginTop: 12 }}>
                  <label className="form-label">Additional Context (free text)</label>
                  <textarea className="form-input" rows={3} value={form.additional_context} onChange={e => setForm(f => ({ ...f, additional_context: e.target.value }))}
                    placeholder="Any strategic context, internal notes, pricing constraints, win themes, etc. This becomes the bible for all agent analysis." style={{ resize: 'vertical', minHeight: 60 }} />
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: 8, marginTop: 20, justifyContent: 'flex-end' }}>
              <button className="btn btn-ghost" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={createBid} disabled={creating || !form.client_name.trim()}>
                {creating ? 'Creating...' : 'Create Bid'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* â”€â”€ Kanban View â”€â”€ */}
      {viewMode === 'kanban' && (
        <div style={{ display:'flex', gap:12, overflowX:'auto', paddingBottom:8 }}>
          {KANBAN_COLUMNS.map(col => {
            const colBids = getBidsInColumn(col)
            return (
              <div key={col.id}
                style={{ minWidth:240, maxWidth:280, flex:'0 0 auto' }}
                onDragOver={e => e.preventDefault()}
                onDrop={e => handleDrop(e, col.id)}
              >
                {/* Column header */}
                <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:8, padding:'6px 10px',
                  background:`${col.color}12`, borderRadius:'var(--radius-md)', border:`1px solid ${col.color}25` }}>
                  <div style={{ width:8, height:8, borderRadius:4, background:col.color, flexShrink:0 }} />
                  <span style={{ fontSize:12, fontWeight:700, color:col.color }}>{col.label}</span>
                  <span style={{ marginLeft:'auto', fontSize:11, color:'var(--text-muted)',
                    background:'var(--bg-tertiary)', borderRadius:10, padding:'1px 7px' }}>{colBids.length}</span>
                </div>

                {/* Cards */}
                <div style={{ display:'flex', flexDirection:'column', gap:8, minHeight:120,
                  background:'var(--bg-glass)', borderRadius:'var(--radius-md)', padding:8,
                  border:'2px dashed var(--border-subtle)' }}>
                  {colBids.map(bid => (
                    <div key={bid.id}
                      draggable
                      onDragStart={() => { dragBid.current = bid.id }}
                      onClick={() => navigate(`/bids/${bid.id}`)}
                      style={{ background:'var(--bg-card)', borderRadius:'var(--radius-md)',
                        padding:'10px 12px', cursor:'grab', boxShadow:'var(--shadow-sm)',
                        border:`1px solid var(--border-subtle)`, transition:'all 150ms',
                        borderLeft:`3px solid ${col.color}` }}
                    >
                      <div style={{ fontSize:12, fontWeight:700, marginBottom:3, lineHeight:1.3 }}>{bid.client_name}</div>
                      <div style={{ fontSize:10, color:'var(--text-muted)', fontFamily:'var(--font-mono)', marginBottom:6 }}>{bid.bid_reference}</div>
                      <div style={{ display:'flex', gap:5, flexWrap:'wrap', alignItems:'center' }}>
                        {bid.bid_recommendation && (
                          <span style={{ fontSize:9, padding:'1px 5px', borderRadius:4, fontWeight:700,
                            background: bid.bid_recommendation==='Go' ? '#dcfce7' : '#fee2e2',
                            color: bid.bid_recommendation==='Go' ? '#059669' : '#dc2626' }}>
                            {bid.bid_recommendation}
                          </span>
                        )}
                        {bid.win_probability !== undefined && bid.win_probability !== null && (
                          <span style={{ fontSize:9, color:'var(--text-muted)' }}>
                            {(bid.win_probability <= 1 ? bid.win_probability * 100 : bid.win_probability).toFixed(0)}% win
                          </span>
                        )}
                        {bid.estimated_tcv ? (
                          <span style={{ fontSize:9, color:'var(--text-muted)', marginLeft:'auto' }}>
                            {bid.estimated_tcv >= 1e6 ? `$${(bid.estimated_tcv/1e6).toFixed(1)}M` : `$${(bid.estimated_tcv/1e3).toFixed(0)}K`}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  ))}
                  {colBids.length === 0 && (
                    <div style={{ padding:'20px 10px', textAlign:'center', fontSize:11, color:'var(--text-muted)' }}>Drop here</div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* â”€â”€ List View â”€â”€ */}
      {viewMode === 'list' && (
        bids.length === 0 ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>ðŸ“‹</div>
          <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>No bids yet</div>
          <div style={{ color: 'var(--text-muted)', marginBottom: 20 }}>Create your first bid to get started</div>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}><Plus size={16} /> Create First Bid</button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {bids.map(bid => (
            <div className="glass-card" key={bid.id} style={{ cursor: 'pointer', transition: 'all 200ms' }}
              onClick={() => navigate(`/bids/${bid.id}`)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <h3 style={{ fontSize: 16, fontWeight: 700 }}>{bid.client_name}</h3>
                    {bid.bid_recommendation && (
                      <span className={`status-badge ${bid.bid_recommendation === 'Go' ? 'low' : 'high'}`} style={{ fontSize: 10 }}>
                        {bid.bid_recommendation}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 4 }}>
                    {bid.bid_reference} Â· {bid.contract_type?.toUpperCase()} Â· {bid.client_industry || 'N/A'}
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                    <span className="stage-badge">{STATUS_LABELS[bid.status] || bid.status}</span>
                    <span className={`status-badge ${bid.deadline_risk}`}>{bid.deadline_risk} risk</span>
                    {bid.win_probability !== undefined && bid.win_probability !== null && (
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        Win: {(bid.win_probability <= 1 ? bid.win_probability * 100 : bid.win_probability).toFixed(0)}%
                      </span>
                    )}
                    {bid.estimated_tcv ? (
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        TCV: {bid.estimated_tcv >= 1e6 ? `$${(bid.estimated_tcv / 1e6).toFixed(1)}M` : bid.estimated_tcv >= 1e3 ? `$${(bid.estimated_tcv / 1e3).toFixed(0)}K` : `$${bid.estimated_tcv.toFixed(0)}`}
                      </span>
                    ) : null}
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      ðŸ“„ {bid.documents?.length || 0} docs
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <button className="btn btn-primary" title="Generate Bid Response (Word)" style={{ fontSize: 10, padding: '4px 10px' }}
                    onClick={e => { e.stopPropagation(); generateDoc(bid.id) }}
                    disabled={generating[bid.id]}>
                    {generating[bid.id] ? <Loader2 size={12} className="spin" /> : <><Download size={12} /> Word Doc</>}
                  </button>

                  <ChevronRight size={18} style={{ color: 'var(--text-muted)', marginLeft: 8 }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )
      )}
    </div>
  )
}