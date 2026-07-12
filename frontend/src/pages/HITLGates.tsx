import { useState, useEffect } from 'react'
import { api } from '../api'
import { Clock, CheckCircle, AlertTriangle, Send, XCircle, ArrowUpRight } from 'lucide-react'

interface Gate { id: string; bid_id: string; bid_reference: string; client_name: string; gate_type: string; status: string; agent_summary: string; assigned_reviewer: string; sla_hours: number; sla_remaining_hours: number; decision: string | null; decided_by: string | null; comments: string | null; created_at: string }

const GATE_LABELS: Record<string, string> = {
  bid_initiation: 'Bid Initiation', intake_review: 'Intake Review', bid_no_bid: 'Bid / No-Bid Decision',
  scope_review: 'Scope Review', solution_review: 'Solution Review', strategy_alignment: 'Strategy Alignment',
  commercial_approval: 'Commercial Approval', legal_compliance: 'Legal & Compliance',
  clarification_submission: 'Clarification Submission', final_review: 'Final Review',
}

export default function HITLGates() {
  const [gates, setGates] = useState<Gate[]>([])
  const [filter, setFilter] = useState('pending')
  const [loading, setLoading] = useState(true)

  const fetchGates = async () => {
    setLoading(true)
    try {
      const data = filter === 'all' ? await api.getGates() : await api.getGates(filter)
      setGates(data)
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  useEffect(() => { fetchGates() }, [filter])

  return (
    <div>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:24 }}>
        <div>
          <h2 style={{ fontSize:24, fontWeight:800 }}>HITL Review Gates</h2>
          <p style={{ color:'var(--text-muted)', fontSize:13, marginTop:4 }}>Human-in-the-Loop review gates — all decisions are mandatory and immutable</p>
        </div>
      </div>
      <div className="tabs">
        {['pending','completed','all'].map(t => (
          <button key={t} className={`tab ${filter === t ? 'active' : ''}`} onClick={() => setFilter(t)}>{t === 'pending' ? `Pending (${gates.length})` : t.charAt(0).toUpperCase() + t.slice(1)}</button>
        ))}
      </div>
      {loading ? <div className="loading-page"><div className="loading-spinner" /></div> :
        gates.length === 0 ? <div className="empty-state"><div className="empty-icon">✅</div><div className="empty-title">No {filter} gates</div><div className="empty-desc">All review gates have been addressed</div></div> :
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          {gates.map(gate => <GateCard key={gate.id} gate={gate} onDecided={fetchGates} />)}
        </div>
      }
    </div>
  )
}

function GateCard({ gate, onDecided }: { gate: Gate; onDecided: () => void }) {
  const [comments, setComments] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const remaining = gate.sla_remaining_hours ?? gate.sla_hours
  const slaClass = remaining <= 2 ? 'urgent' : remaining <= 8 ? 'normal' : 'safe'

  const handleDecision = async (decision: string) => {
    if (!comments.trim()) { alert('Comments are required for all HITL decisions'); return }
    setSubmitting(true)
    try { await api.decideGate(gate.id, decision, comments); onDecided() } catch (e: any) { alert(e.message) }
    setSubmitting(false)
  }

  return (
    <div className="gate-card">
      <div className="gate-header">
        <div>
          <div className="gate-type">{GATE_LABELS[gate.gate_type] || gate.gate_type}</div>
          <div style={{ fontSize:14, fontWeight:600, marginTop:4 }}>{gate.client_name} — {gate.bid_reference}</div>
        </div>
        <div>
          {gate.status === 'pending' ? (
            <div className={`gate-sla ${slaClass}`}>
              <Clock size={14} />
              {remaining.toFixed(1)}h remaining
            </div>
          ) : (
            <span style={{ fontSize:12, color:'var(--status-success)', display:'flex', alignItems:'center', gap:4 }}>
              <CheckCircle size={14} /> {gate.decision}
            </span>
          )}
        </div>
      </div>
      <div className="gate-summary">{gate.agent_summary}</div>
      <div className="gate-meta">
        <span>Reviewer: <strong>{gate.assigned_reviewer}</strong></span>
        <span>SLA: {gate.sla_hours}h</span>
        {gate.decided_by && <span>Decided by: <strong>{gate.decided_by}</strong></span>}
      </div>
      {gate.status === 'pending' && (
        <>
          <div className="gate-comment">
            <textarea value={comments} onChange={e => setComments(e.target.value)} placeholder="Enter your review comments (required)..." />
          </div>
          <div className="gate-actions">
            <button className="btn btn-success" disabled={submitting} onClick={() => handleDecision('approved')}><CheckCircle size={14} /> Approve</button>
            <button className="btn btn-warning" disabled={submitting} onClick={() => handleDecision('approved_with_comments')}><Send size={14} /> Approve w/ Comments</button>
            <button className="btn btn-ghost" disabled={submitting} onClick={() => handleDecision('request_changes')}><ArrowUpRight size={14} /> Request Changes</button>
            <button className="btn btn-danger" disabled={submitting} onClick={() => handleDecision('rejected')}><XCircle size={14} /> Reject</button>
          </div>
        </>
      )}
      {gate.status === 'completed' && gate.comments && (
        <div style={{ marginTop:12, padding:12, background:'var(--bg-glass)', borderRadius:'var(--radius-md)', fontSize:13, color:'var(--text-secondary)' }}>
          <strong>Decision Comments:</strong> {gate.comments}
        </div>
      )}
    </div>
  )
}
