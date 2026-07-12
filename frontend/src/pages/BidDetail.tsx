import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../api'
import { ArrowLeft, Play, Upload, FileText, CheckCircle, Clock, XCircle, AlertTriangle, Eye, Copy, Download, Loader2, FolderOpen, Bot, Pencil, Zap, Square, ExternalLink, Presentation, LineChart } from 'lucide-react'
import { useReliableWebSocket, buildWsUrl } from '../hooks/useReliableWebSocket'

const STATUS_LABELS: Record<string, string> = {
  created: 'Created', intake_processing: 'Intake Processing', intake_review: 'Intake Review',
  bid_no_bid: 'Bid/No-Bid', scope_building: 'Scope Building', scope_review: 'Scope Review',
  solution_design: 'Solution Design', solution_review: 'Solution Review',
  strategy_alignment: 'Strategy Alignment', commercial_modeling: 'Commercial Modeling',
  commercial_approval: 'Commercial Approval', compliance_review: 'Compliance Review',
  legal_sign_off: 'Legal Sign-off', output_generation: 'Output Gen',
  qa_review: 'QA Review', final_review: 'Final Review', submitted: 'Submitted',
}

const PIPELINE_STAGES = [
  'created', 'intake_review', 'data_analysis', 'client_intel_review',
  'strategy_alignment', 'solution_review', 'commercial_approval',
  'legal_sign_off', 'final_review', 'submitted',
]

// Premium SVG agent icon — circular badge with refined SVG path
const AgentIcon = ({ color, path }: { color: string; path: string }) => (
  <div style={{ width: 36, height: 36, borderRadius: 10, background: `linear-gradient(135deg, ${color}18, ${color}30)`, border: `1px solid ${color}25`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d={path} />
    </svg>
  </div>
)

const AGENT_ICONS: Record<string, string> = {
  intake: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4 M7 10l5 5 5-5 M12 15V3',
  data_analyst: 'M18 20V10 M12 20V4 M6 20v-6 M3 20h18',
  client_intelligence: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z',
  strategic_assessment: 'M12 2L2 7l10 5 10-5-10-5z M2 17l10 5 10-5 M2 12l10 5 10-5',
  solution_scope: 'M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z',
  automation_ai: 'M12 2a4 4 0 0 0-4 4v2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2h-2V6a4 4 0 0 0-4-4z M9 15l2 2 4-4',
  transition_change: 'M5 12h14 M12 5l7 7-7 7 M3 3v18h18',
  commercial_model: 'M12 1v22 M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6',
  compliance_risk: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
  proposal_generator: 'M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z',
  discovery: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z M21 21l-4.35-4.35',
  feedback_learning: 'M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z M4 22v-7',
}

const AGENTS = [
  { key: 'intake', label: 'RFP Intake', color: '#3B82F6', desc: 'Parses RFP documents and extracts all structured fields' },
  { key: 'data_analyst', label: 'Data Intelligence', color: '#7C3AED', desc: 'Comprehensive data extraction — users, countries, configs, integrations' },
  { key: 'client_intelligence', label: 'Client Intelligence', color: '#0D9488', desc: 'Web-powered client research, market position & win strategy' },
  { key: 'strategic_assessment', label: 'Strategic Assessment', color: '#10B981', desc: 'Go/No-Go decision, competitive landscape & win themes' },
  { key: 'solution_scope', label: 'Solution Design & Scoping', color: '#8B5CF6', desc: 'Architecture, WBS, effort estimation & team model' },
  { key: 'automation_ai', label: 'AI & Automation Advisory', color: '#0EA5E9', desc: 'AI/automation opportunities, ROI analysis & roadmap' },
  { key: 'transition_change', label: 'Transition & Change Management', color: '#F97316', desc: 'Transition phases, KT plans, stakeholder change management & rollout roadmap' },
  { key: 'commercial_model', label: 'Commercial & Pricing', color: '#06B6D4', desc: 'Rate card, resource plan, P&L, margin guardrails' },
  { key: 'compliance_risk', label: 'Risk & Compliance', color: '#EF4444', desc: 'Risk register, T&C scoring & negotiation matrix' },
  { key: 'proposal_generator', label: 'Proposal Generator', color: '#D946EF', desc: 'Full proposal writing, document assembly & quality validation' },
  { key: 'discovery', label: 'Discovery & Clarifications', color: '#F97316', desc: 'Gap analysis & client clarification questions' },
  { key: 'feedback_learning', label: 'Learning & Feedback', color: '#6366F1', desc: 'Institutional learning capture & model calibration' },
]

const INDUSTRIES = ['Financial Services','Healthcare','Retail','Manufacturing','Technology','Energy','Government','Telecom','Education']

export default function BidDetail() {
  const { bidId } = useParams<{ bidId: string }>()
  const navigate = useNavigate()
  const [bid, setBid] = useState<any>(null)
  const [agentOutputs, setAgentOutputs] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [runningAgent, setRunningAgent] = useState<string | null>(null)
  const [generatingDoc, setGeneratingDoc] = useState(false)
  const [toast, setToast] = useState<{msg:string,type:string}|null>(null)
  const [showEdit, setShowEdit] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editForm, setEditForm] = useState<any>({})
  const [orgNodes, setOrgNodes] = useState<any[]>([])
  const fileRef = useRef<HTMLInputElement>(null)
  const showToast = (msg:string,type='info') => { setToast({msg,type}); setTimeout(()=>setToast(null),4000) }

  // ── Pipeline WebSocket state ───────────────────────────────────────────
  const [pipelineRun, setPipelineRun] = useState<any>(null)
  const [pipelineRunning, setPipelineRunning] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [exportLoading, setExportLoading] = useState<string | null>(null)

  // Build WS URL — null until bidId is known, disabling the hook
  const token = localStorage.getItem('token') || ''
  const wsUrl = bidId
    ? buildWsUrl(`/api/ws/pipeline/${bidId}?token=${token}`)
    : null

  const fetchBid = useCallback(async () => {
    if (!bidId) return
    try {
      const [b, outputs] = await Promise.all([api.getBid(bidId), api.getAgentOutputs(bidId)])
      setBid(b); setAgentOutputs(outputs || {})
    } catch (e) { console.error(e) }
    setLoading(false)
  }, [bidId])

  // Handle incoming WS messages
  const handleWsMessage = useCallback((data: unknown) => {
    const msg = data as any
    if (!msg?.type) return
    if (msg.type === 'state_snapshot' || msg.type === 'progress') {
      setPipelineRun(msg)
      setPipelineRunning(msg.status === 'running' || msg.status === 'waiting_on_hitl')
    } else if (msg.type === 'pipeline_done') {
      setPipelineRunning(false)
      fetchBid()
    } else if (msg.type === 'no_run') {
      setPipelineRun(null)
      setPipelineRunning(false)
    }
  }, [fetchBid])

  // Reliable WS with auto-reconnect, keepalive, and visibility reconnect
  useReliableWebSocket(wsUrl, handleWsMessage, { maxRetries: 10, baseDelayMs: 1000 })

  useEffect(() => { fetchBid() }, [fetchBid])
  useEffect(() => { api.getOrgNodes().then(setOrgNodes).catch(() => {}) }, [])


  const openEdit = () => {
    if (!bid) return
    const uc = bid.user_context || {}
    setEditForm({
      client_name: bid.client_name || '', client_industry: bid.client_industry || '',
      contract_type: bid.contract_type || 'ams', products: (bid.products || []).join(', '),
      org_unit_id: bid.org_unit_id || '',
      estimated_tcv: bid.estimated_tcv || '',
      win_probability: bid.win_probability || 0,
      status: bid.status || 'created',
      known_competitors: (uc.known_competitors || []).join(', '), incumbent_vendor: uc.incumbent_vendor || '',
      rate_onshore: uc.rate_onshore_usd || '', rate_offshore: uc.rate_offshore_usd || '', rate_nearshore: uc.rate_nearshore_usd || '',
      deal_size_estimate: uc.deal_size_estimate || '', past_relationship: uc.past_relationship || '',
      additional_context: uc.additional_context || '',
    })
    setShowEdit(true)
  }

  const saveEdit = async () => {
    if (!bidId) return
    setSaving(true)
    try {
      const payload: any = { 
        client_name: editForm.client_name, 
        client_industry: editForm.client_industry, 
        contract_type: editForm.contract_type, 
        products: editForm.products.split(',').map((p:string) => p.trim()).filter(Boolean),
        estimated_tcv: editForm.estimated_tcv || 0,
        win_probability: editForm.win_probability || 0,
        status: editForm.status
      }
      if (editForm.org_unit_id) { payload.org_unit_id = editForm.org_unit_id; const n = orgNodes.find((o:any) => o.id === editForm.org_unit_id); payload.org_unit_label = n?.label || '' }
      if (editForm.known_competitors.trim()) payload.known_competitors = editForm.known_competitors.split(',').map((c:string) => c.trim())
      if (editForm.incumbent_vendor.trim()) payload.incumbent_vendor = editForm.incumbent_vendor
      if (editForm.rate_onshore) payload.rate_onshore_usd = parseFloat(editForm.rate_onshore)
      if (editForm.rate_offshore) payload.rate_offshore_usd = parseFloat(editForm.rate_offshore)
      if (editForm.rate_nearshore) payload.rate_nearshore_usd = parseFloat(editForm.rate_nearshore)
      if (editForm.deal_size_estimate) payload.deal_size_estimate = editForm.deal_size_estimate
      if (editForm.past_relationship) payload.past_relationship = editForm.past_relationship
      if (editForm.additional_context.trim()) payload.additional_context = editForm.additional_context
      await api.updateBid(bidId, payload)
      showToast('Bid updated', 'success'); setShowEdit(false); await fetchBid()
    } catch (e: any) { showToast('Update failed: ' + e.message, 'error') }
    setSaving(false)
  }

  const cloneBid = async () => {
    if (!bidId) return
    try { const c = await api.cloneBid(bidId); showToast('Bid cloned','success'); navigate('/bids/'+c.id) }
    catch(e:any) { showToast('Clone failed: '+e.message,'error') }
  }

  const runAgent = async (agentName: string) => {
    if (!bidId || runningAgent) return
    setRunningAgent(agentName)
    try { await api.runAgent(bidId, agentName); showToast('Agent completed','success'); await fetchBid() }
    catch (e: any) { showToast('Agent failed: '+e.message,'error'); await fetchBid() }
    setRunningAgent(null)
  }

  const uploadDocs = async (files: FileList) => {
    if (!bidId || files.length === 0) return
    setUploading(true)
    try {
      const token = localStorage.getItem('token')
      const fd = new FormData()
      for (let i = 0; i < files.length; i++) {
        fd.append('files', files[i])
      }
      fd.append('document_type', 'rfp')
      const headers: Record<string, string> = {}
      if (token) headers['Authorization'] = `Bearer ${token}`
      await fetch(`/api/bids/${bidId}/documents`, { method: 'POST', body: fd, headers })
      await fetchBid()
      showToast(`${files.length} document${files.length > 1 ? 's' : ''} uploaded`, 'success')
    } catch (e) { console.error(e); showToast('Upload failed', 'error') }
    setUploading(false)
  }

  const runFullPipeline = async () => {
    if (!bidId || pipelineRunning) return
    try {
      await api.startPipeline(bidId)
      setPipelineRunning(true)
      showToast('Pipeline started — 12 agents running', 'success')
    } catch (e: any) { showToast('Failed to start pipeline: ' + e.message, 'error') }
  }

  const cancelPipeline = async () => {
    if (!bidId) return
    setCancelling(true)
    try {
      await api.cancelPipeline(bidId)
      setPipelineRunning(false)
      showToast('Pipeline cancelled', 'info')
    } catch (e: any) { showToast('Cancel failed: ' + e.message, 'error') }
    setCancelling(false)
  }

  const exportDoc = async (type: 'sow' | 'ppt' | 'excel') => {
    if (!bidId) return
    setExportLoading(type)
    try {
      let result: any
      if (type === 'sow') result = await api.generateSOW(bidId)
      else if (type === 'ppt') result = await api.generatePPT(bidId)
      else result = await api.generateExcel(bidId)
      if (result?.doc_id) window.open(api.getDownloadUrl(result.doc_id), '_blank')
      showToast(`${type.toUpperCase()} generated`, 'success')
    } catch (e: any) { showToast(`${type} generation failed: ` + e.message, 'error') }
    setExportLoading(null)
  }

  const generateDoc = async () => {
    if (!bidId) return
    setGeneratingDoc(true)
    try {
      const result = await api.generateSOW(bidId)
      if (result.doc_id) window.open(api.getDownloadUrl(result.doc_id), '_blank')
      showToast('Document generated', 'success')
    } catch (e: any) { showToast('Generation failed: ' + e.message, 'error') }
    setGeneratingDoc(false)
  }

  if (loading) return <div className="loading-page"><div className="loading-spinner" /></div>
  if (!bid) return <div className="empty-state"><div className="empty-title">Bid not found</div></div>

  const currentIdx = PIPELINE_STAGES.indexOf(bid.status)
  const completedAgents = Object.keys(agentOutputs).filter(k => agentOutputs[k]?.status !== 'failed').length

  return (
    <div>
      {/* Toast */}
      {toast && <div style={{ position:'fixed',top:20,right:20,zIndex:9999,padding:'12px 20px',borderRadius:'var(--radius-md)',background:toast.type==='success'?'rgba(16,185,129,0.95)':toast.type==='error'?'rgba(239,68,68,0.95)':'rgba(59,130,246,0.95)',color:'#fff',fontSize:13,fontWeight:600,maxWidth:400,boxShadow:'0 8px 32px rgba(0,0,0,0.3)' }}>{toast.msg}</div>}

      <div style={{ display:'flex',gap:8,marginBottom:16 }}>
        <button className="btn btn-ghost" onClick={() => navigate('/bids')} style={{ fontSize: 13, gap: 6 }}>
          <ArrowLeft size={14} /> Back to Bids
        </button>
        <button className="btn btn-primary" onClick={openEdit} style={{ fontSize:13,gap:6,marginLeft:'auto' }}>
          <Pencil size={14} /> Edit Bid
        </button>
        <button className="btn btn-ghost" onClick={cloneBid} style={{ fontSize:13,gap:6 }}>
          <Copy size={14} /> Clone
        </button>
        {/* ── Full pipeline run / cancel ── */}
        {pipelineRunning ? (
          <button className="btn btn-ghost" style={{ fontSize:13, gap:6, color:'var(--status-danger)' }}
            onClick={cancelPipeline} disabled={cancelling}>
            <Square size={13} /> {cancelling ? 'Cancelling…' : 'Cancel Pipeline'}
          </button>
        ) : (
          <button className="btn btn-primary" style={{ fontSize:13, gap:6, background:'linear-gradient(135deg,#2862E9,#00D4FF)' }}
            onClick={runFullPipeline}>
            <Zap size={13} /> Run Full Pipeline
          </button>
        )}
      </div>

      {/* Bid Header */}
      <div className="glass-card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 800 }}>{bid.client_name}</h2>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 4 }}>
              {bid.bid_reference} · {bid.contract_type?.toUpperCase()} · {bid.client_industry}
              {bid.org_unit_label && <span> · {bid.org_unit_label}</span>}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {bid.bid_recommendation && (
              <span className={`status-badge ${bid.bid_recommendation === 'Go' ? 'low' : bid.bid_recommendation === 'No-Go' ? 'high' : 'medium'}`}>
                {bid.bid_recommendation}
              </span>
            )}
            <span className={`status-badge ${bid.deadline_risk}`}>{bid.deadline_risk} risk</span>
          </div>
        </div>

        {/* Pipeline Progress */}
        <div style={{ display: 'flex', gap: 3, marginTop: 20 }}>
          {PIPELINE_STAGES.map((stage, i) => (
            <div key={stage} style={{ flex: 1, textAlign: 'center' }}>
              <div style={{
                height: 5, borderRadius: 3, transition: 'all 300ms',
                background: i < currentIdx ? 'var(--status-success)' : i === currentIdx ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
              }} />
              <div style={{ fontSize: 9, marginTop: 5, fontWeight: i === currentIdx ? 700 : 400, color: i === currentIdx ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                {STATUS_LABELS[stage] || stage}
              </div>
            </div>
          ))}
        </div>

        {/* Quick Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 20 }}>
          {[
            { label: 'Win Probability', value: bid.win_probability !== undefined ? `${(bid.win_probability <= 1 ? bid.win_probability * 100 : bid.win_probability).toFixed(0)}%` : '—' },
            { label: 'Estimated TCV', value: bid.estimated_tcv ? (bid.estimated_tcv >= 1e6 ? `$${(bid.estimated_tcv / 1e6).toFixed(1)}M` : bid.estimated_tcv >= 1e3 ? `$${(bid.estimated_tcv / 1e3).toFixed(0)}K` : `$${bid.estimated_tcv.toFixed(0)}`) : '—' },
            { label: 'Stage', value: STATUS_LABELS[bid.status] || bid.status },
            { label: 'Agents Completed', value: `${completedAgents} / ${AGENTS.length}` },
          ].map(s => (
            <div key={s.label} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.label}</div>
              <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2 }}>{s.value}</div>
            </div>
          ))}
        </div>
      </div>


      {/* Documents */}
      <div className="glass-card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}><FolderOpen size={16} style={{ color: 'var(--text-accent)' }} /> Documents ({bid.documents?.length || 0})</h3>
          <button className="btn btn-primary" style={{ fontSize: 12 }} onClick={() => fileRef.current?.click()} disabled={uploading}>
            <Upload size={12} /> {uploading ? 'Uploading...' : 'Upload RFP'}
          </button>
          <input ref={fileRef} type="file" hidden multiple accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md,.pptx,.ppt" onChange={e => { if (e.target.files?.length) uploadDocs(e.target.files); e.target.value = '' }} />
        </div>
        {bid.documents?.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {bid.documents.map((doc: any) => (
              <div key={doc.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <FileText size={16} style={{ color: 'var(--text-accent)', flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>{doc.filename}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{(doc.file_size / 1024).toFixed(0)} KB · {doc.document_type}</div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="upload-zone" onClick={() => fileRef.current?.click()} style={{ padding: 30 }}>
            <div className="upload-icon" style={{ fontSize: 28 }}><FileText size={28} style={{ color: 'var(--text-muted)' }} /></div>
            <div className="upload-text" style={{ fontSize: 14 }}>Upload RFP documents to begin</div>
            <div className="upload-hint" style={{ fontSize: 12 }}>PDF, DOCX, XLSX, TXT, CSV — Multiple files supported</div>
          </div>
        )}
      </div>

      {/* ── Live Pipeline Stream Panel ── */}
      {pipelineRun && pipelineRun.stages && (
        <div className="glass-card" style={{ marginBottom: 20, borderLeft: '3px solid var(--accent-primary)' }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
            <h3 style={{ fontSize:14, fontWeight:700, display:'flex', alignItems:'center', gap:8 }}>
              <Zap size={15} style={{ color:'var(--accent-primary)' }} />
              Pipeline Execution
              {pipelineRunning && <span style={{ fontSize:11, color:'var(--accent-primary)', fontWeight:500 }}>— Live</span>}
            </h3>
            <span style={{ fontSize:11, color:'var(--text-muted)' }}>
              {pipelineRun.completed_stages || 0} / {pipelineRun.total_stages || 12} stages
            </span>
          </div>
          <div style={{ display:'flex', flexDirection:'column', gap:4 }}>
            {(pipelineRun.stages || []).map((s: any, i: number) => {
              const isRunning = s.status === 'running'
              const isDone = s.status === 'completed'
              const isFailed = s.status === 'failed'
              const isSkipped = s.status === 'skipped'
              const color = isDone ? 'var(--status-success)' : isFailed ? 'var(--status-danger)' : isRunning ? 'var(--accent-primary)' : 'var(--bg-tertiary)'
              return (
                <div key={i} style={{ display:'flex', alignItems:'center', gap:10 }}>
                  <div style={{ width:18, display:'flex', justifyContent:'center', flexShrink:0 }}>
                    {isDone && <CheckCircle size={14} style={{ color:'var(--status-success)' }} />}
                    {isFailed && <XCircle size={14} style={{ color:'var(--status-danger)' }} />}
                    {isRunning && <div className="loading-spinner" style={{ width:14, height:14, borderWidth:2 }} />}
                    {!isDone && !isFailed && !isRunning && <Clock size={14} style={{ color:'var(--text-muted)', opacity: isSkipped ? 0.3 : 1 }} />}
                  </div>
                  <div style={{ flex:1 }}>
                    <div style={{ display:'flex', alignItems:'center', gap:6 }}>
                      <span style={{ fontSize:12, fontWeight: isRunning ? 700 : 500, color: isRunning ? 'var(--text-primary)' : isDone ? 'var(--text-secondary)' : 'var(--text-muted)', opacity: isSkipped ? 0.4 : 1 }}>
                        {s.label || s.name}
                      </span>
                      {isFailed && s.error && <span style={{ fontSize:10, color:'var(--status-danger)' }}>{s.error.substring(0, 60)}</span>}
                    </div>
                    <div style={{ height:3, borderRadius:2, marginTop:3, background:'var(--bg-tertiary)', overflow:'hidden' }}>
                      <div style={{ height:'100%', borderRadius:2, transition:'width 0.5s ease', background:color, width: isDone ? '100%' : isRunning ? '60%' : '0%',
                        ...(isRunning ? { animation:'pulse 1.5s ease-in-out infinite' } : {}) }} />
                    </div>
                  </div>
                  <div style={{ fontSize:10, color:'var(--text-muted)', width:60, textAlign:'right', flexShrink:0 }}>
                    {s.status}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Export Hub ── */}
      <div className="glass-card" style={{ marginBottom: 20 }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
          <h3 style={{ fontSize:14, fontWeight:700, display:'flex', alignItems:'center', gap:8 }}>
            <Download size={15} style={{ color:'var(--text-accent)' }} /> Export Hub
          </h3>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:10 }}>
          {[
            { type:'sow' as const, label:'Statement of Work', ext:'DOCX', icon:<FileText size={18} color="var(--text-accent)" />, desc:'Full proposal + SOW document' },
            { type:'ppt' as const, label:'Executive Presentation', ext:'PPTX', icon:<Presentation size={18} color="var(--text-accent)" />, desc:'C-Suite ready slide deck' },
            { type:'excel' as const, label:'Commercial Model', ext:'XLSX', icon:<LineChart size={18} color="var(--text-accent)" />, desc:'Resource plan + P&L workbook' },
          ].map(d => (
            <button key={d.type}
              className="btn btn-ghost"
              style={{ flexDirection:'column', alignItems:'flex-start', padding:'12px 14px', height:'auto', gap:4, textAlign:'left', opacity: exportLoading && exportLoading !== d.type ? 0.5 : 1 }}
              onClick={() => exportDoc(d.type)}
              disabled={!!exportLoading}
            >
              <div style={{ fontSize:20, marginBottom:2 }}>{exportLoading === d.type ? '⏳' : d.icon}</div>
              <div style={{ fontSize:12, fontWeight:700 }}>{d.label}</div>
              <div style={{ fontSize:10, color:'var(--text-muted)' }}>{d.ext} · {d.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Agent Pipeline Cards */}
      <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}><Bot size={18} style={{ color: 'var(--accent-primary)' }} /> Agent Pipeline</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 14, marginBottom: 20 }}>
        {AGENTS.map(agent => {
          const hasOutput = !!agentOutputs[agent.key]
          const isFailed = agentOutputs[agent.key]?.status === 'failed'
          const isRunning = runningAgent === agent.key
          const summary = agentOutputs[agent.key]?.result?.hitl_summary || agentOutputs[agent.key]?.result?.executive_summary

          const isStale = agentOutputs[agent.key]?.stale === true;

          return (
            <div className="glass-card" key={agent.key} style={{
              padding: 16, borderLeft: `3px solid ${isStale ? '#f59e0b' : hasOutput && !isFailed ? agent.color : isFailed ? 'var(--status-danger)' : 'var(--border-subtle)'}`,
              transition: 'all 200ms', cursor: 'pointer', position: 'relative',
              opacity: isStale ? 0.85 : 1,
              display: 'flex', flexDirection: 'column', minHeight: 180,
            }}
            onClick={() => navigate(`/bids/${bidId}/agent/${agent.key}`)}
            >
              {isStale && (
                  <div style={{ fontSize: 10, color: '#f59e0b', fontWeight: 600, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <AlertTriangle size={12} /> STALE — upstream agent re-run, consider re-running
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', minHeight: 70 }}>
                <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                  <AgentIcon color={agent.color} path={AGENT_ICONS[agent.key]} />
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700 }}>{agent.label}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{agent.desc}</div>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                  {hasOutput && !isFailed && <CheckCircle size={18} style={{ color: 'var(--status-success)' }} />}
                  {isFailed && <XCircle size={18} style={{ color: 'var(--status-danger)' }} />}
                  {!hasOutput && !isRunning && <Clock size={18} style={{ color: 'var(--text-muted)' }} />}
                  {isRunning && <div className="loading-spinner" style={{ width: 18, height: 18, borderWidth: 2 }} />}
                </div>
              </div>

              {/* Summary text — flex grow to push buttons down */}
              <div style={{ flex: 1, marginTop: 6 }}>
                {summary && (
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    {summary.substring(0, 200)}{summary.length > 200 ? '...' : ''}
                  </div>
                )}
                {isRunning && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: agent.color, marginBottom: 4 }}>Running...</div>
                    <div style={{ height: 4, borderRadius: 2, background: 'var(--bg-tertiary)', overflow: 'hidden' }}>
                      <div style={{ height: '100%', borderRadius: 2, background: `linear-gradient(90deg, ${agent.color}, ${agent.color}88)`, animation: 'pulse 1.5s ease-in-out infinite', width: '60%' }} />
                    </div>
                  </div>
                )}
              </div>

              {/* Buttons — always at bottom, aligned across cards */}
              <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
                <button className={`btn ${hasOutput ? 'btn-ghost' : 'btn-primary'}`}
                  style={{ fontSize: 11, padding: '5px 12px', flex: 1 }}
                  disabled={isRunning || !!runningAgent}
                  onClick={e => { e.stopPropagation(); runAgent(agent.key) }}>
                  {isRunning ? 'Running...' : <><Play size={11} /> {hasOutput ? 'Re-run' : 'Run'}</>}
                </button>
                {hasOutput && (
                  <Link to={`/bids/${bidId}/agent/${agent.key}`}
                    className="btn btn-ghost"
                    style={{ fontSize: 11, padding: '5px 12px', textDecoration: 'none', flex: 1, textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}
                    onClick={e => e.stopPropagation()}>
                    <Eye size={11} /> View Output
                  </Link>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Edit Bid Modal */}
      {showEdit && (
        <div style={{ position:'fixed',inset:0,background:'rgba(0,0,0,0.5)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:1000 }} onClick={()=>setShowEdit(false)}>
          <div className="glass-card" style={{ width:600,maxWidth:'90vw',maxHeight:'85vh',overflow:'auto' }} onClick={e=>e.stopPropagation()}>
            <h3 style={{ fontSize:18,fontWeight:700,marginBottom:20 }}>Edit Bid Details</h3>
            <div className="form-group"><label className="form-label">Client Name</label>
              <input className="form-input" value={editForm.client_name} onChange={e=>setEditForm((f:any)=>({...f,client_name:e.target.value}))} />
            </div>
            <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:12 }}>
              <div className="form-group"><label className="form-label">Industry</label>
                <select className="form-input" value={editForm.client_industry} onChange={e=>setEditForm((f:any)=>({...f,client_industry:e.target.value}))}>
                  <option value="">Select...</option>{INDUSTRIES.map(i=><option key={i}>{i}</option>)}
                </select>
              </div>
              <div className="form-group"><label className="form-label">Contract Type</label>
                <select className="form-input" value={editForm.contract_type} onChange={e=>setEditForm((f:any)=>({...f,contract_type:e.target.value}))}>
                  <option value="ams">AMS</option><option value="implementation">Implementation</option>
                  <option value="advisory">Advisory</option><option value="staff_aug">Staff Augmentation</option>
                </select>
              </div>
            </div>
            <div className="form-group"><label className="form-label">Products (comma-separated)</label>
              <input className="form-input" value={editForm.products} onChange={e=>setEditForm((f:any)=>({...f,products:e.target.value}))} />
            </div>
            <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:12 }}>
              <div className="form-group"><label className="form-label">Est. TCV ($)</label>
                <input className="form-input" type="number" value={editForm.estimated_tcv || ''} onChange={e=>setEditForm((f:any)=>({...f,estimated_tcv: Number(e.target.value)}))} />
              </div>
              <div className="form-group"><label className="form-label">Win Prob (%)</label>
                <input className="form-input" type="number" value={editForm.win_probability ? Math.round(editForm.win_probability * 100) : ''} onChange={e=>setEditForm((f:any)=>({...f,win_probability: e.target.value ? Number(e.target.value)/100 : 0}))} max="100" />
              </div>
              <div className="form-group"><label className="form-label">Status</label>
                <select className="form-input" value={editForm.status} onChange={e=>setEditForm((f:any)=>({...f,status:e.target.value}))}>
                  {PIPELINE_STAGES.map(s => <option key={s} value={s}>{STATUS_LABELS[s] || s}</option>)}
                  <option value="won">Won</option>
                  <option value="lost">Lost</option>
                  <option value="abandoned">Abandoned</option>
                  <option value="no_bid">No-Bid</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 14 }}>🏢</span> Organization Unit
              </label>
              <select
                className="form-input"
                value={editForm.org_unit_id}
                onChange={e=>setEditForm((f:any)=>({...f,org_unit_id:e.target.value}))}
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
                <option value="">— Select Organization Unit —</option>
                {orgNodes.map((n:any)=>(<option key={n.id} value={n.id}>{'    '.repeat(Math.max(0,n.level-1))}{n.level>1?'└─ ':'�-� '}{n.role} — {n.practice}</option>))}
              </select>
            </div>
            <div style={{ marginTop:8,padding:14,background:'var(--bg-glass)',borderRadius:'var(--radius-md)',border:'1px solid var(--border-subtle)' }}>
              <div style={{ fontSize:11,color:'var(--text-muted)',marginBottom:10,textTransform:'uppercase',letterSpacing:0.5 }}>Strategic Inputs</div>
              <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:12 }}>
                <div className="form-group"><label className="form-label">Known Competitors</label>
                  <input className="form-input" value={editForm.known_competitors} onChange={e=>setEditForm((f:any)=>({...f,known_competitors:e.target.value}))} placeholder="e.g. Infosys, Accenture" />
                </div>
                <div className="form-group"><label className="form-label">Incumbent Vendor</label>
                  <input className="form-input" value={editForm.incumbent_vendor} onChange={e=>setEditForm((f:any)=>({...f,incumbent_vendor:e.target.value}))} />
                </div>
              </div>
              <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:12 }}>
                <div className="form-group"><label className="form-label">Onshore $/hr</label>
                  <input className="form-input" type="number" value={editForm.rate_onshore} onChange={e=>setEditForm((f:any)=>({...f,rate_onshore:e.target.value}))} />
                </div>
                <div className="form-group"><label className="form-label">Nearshore $/hr</label>
                  <input className="form-input" type="number" value={editForm.rate_nearshore} onChange={e=>setEditForm((f:any)=>({...f,rate_nearshore:e.target.value}))} />
                </div>
                <div className="form-group"><label className="form-label">Offshore $/hr</label>
                  <input className="form-input" type="number" value={editForm.rate_offshore} onChange={e=>setEditForm((f:any)=>({...f,rate_offshore:e.target.value}))} />
                </div>
              </div>
              <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:12 }}>
                <div className="form-group"><label className="form-label">Deal Size</label>
                  <select className="form-input" value={editForm.deal_size_estimate} onChange={e=>setEditForm((f:any)=>({...f,deal_size_estimate:e.target.value}))}>
                    <option value="">Select...</option><option value="small">Small (&lt;$500K)</option>
                    <option value="mid">Mid ($500K–$2M)</option><option value="large">Large ($2M–$10M)</option>
                    <option value="enterprise">Enterprise ($10M+)</option>
                  </select>
                </div>
                <div className="form-group"><label className="form-label">Client Relationship</label>
                  <select className="form-input" value={editForm.past_relationship} onChange={e=>setEditForm((f:any)=>({...f,past_relationship:e.target.value}))}>
                    <option value="">Select...</option><option value="new">New Client</option>
                    <option value="existing">Existing Client</option><option value="renewal">Renewal</option>
                  </select>
                </div>
              </div>
              <div className="form-group"><label className="form-label">Additional Context</label>
                <textarea className="form-input" rows={2} value={editForm.additional_context} onChange={e=>setEditForm((f:any)=>({...f,additional_context:e.target.value}))} style={{ resize:'vertical',minHeight:40 }} />
              </div>
            </div>
            <div style={{ display:'flex',gap:8,marginTop:20,justifyContent:'space-between' }}>
              <button className="btn btn-ghost" style={{color: 'var(--status-danger)'}} onClick={async () => {
                if (window.confirm('Are you sure you want to delete this bid? This cannot be undone.')) {
                  try {
                    await api.deleteBid(bidId!);
                    navigate('/');
                  } catch (e: any) {
                    showToast('Delete failed: ' + e.message, 'error');
                  }
                }
              }}>Delete Bid</button>
              <div style={{ display:'flex',gap:8 }}>
                <button className="btn btn-ghost" onClick={()=>setShowEdit(false)}>Cancel</button>
                <button className="btn btn-primary" onClick={saveEdit} disabled={saving}>{saving?'Saving...':'Save Changes'}</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
