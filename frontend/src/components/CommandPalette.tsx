/**
 * CommandPalette — Global Ctrl+K / Cmd+K search overlay
 *
 * Features:
 *   - Full-text fuzzy search across all bids (client name, reference, industry, status)
 *   - Keyboard navigation: ↑↓ to move, Enter to open, Escape to close
 *   - Instant results (debounced 150ms)
 *   - Recent searches persisted in localStorage
 *   - Quick actions: New Bid, HITL Gates, Executive View
 *   - Win probability + TCV shown inline on each result
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { Search, ArrowRight, Plus, ShieldCheck, BarChart3, Clock, X } from 'lucide-react'

interface Bid {
  id: string
  bid_reference: string
  client_name: string
  client_industry: string
  status: string
  win_probability: number
  estimated_tcv: number
  bid_recommendation: string
}

const STATUS_LABELS: Record<string, string> = {
  created: 'Created', intake_processing: 'Intake', intake_review: 'Intake Review',
  bid_no_bid: 'Bid/No-Bid', scope_building: 'Scope', solution_design: 'Solution',
  commercial_modeling: 'Commercial', compliance_review: 'Compliance',
  final_review: 'Final', submitted: 'Submitted', won: 'Won', lost: 'Lost',
}

const RECENT_KEY = 'arise_recent_searches'

function getRecent(): string[] {
  try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]') } catch { return [] }
}
function pushRecent(q: string) {
  if (!q.trim()) return
  const prev = getRecent().filter(r => r !== q)
  localStorage.setItem(RECENT_KEY, JSON.stringify([q, ...prev].slice(0, 6)))
}

const QUICK_ACTIONS = [
  { label: 'New Bid', icon: Plus, path: '/bids', action: 'new', color: '#0066FF' },
  { label: 'HITL Gates', icon: ShieldCheck, path: '/hitl', color: '#8B5CF6' },
  { label: 'Executive View', icon: BarChart3, path: '/executive', color: '#06B6D4' },
]

export default function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Bid[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState(0)
  const [recent, setRecent] = useState<string[]>(getRecent())
  const inputRef = useRef<HTMLInputElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery('')
      setResults([])
      setSelected(0)
      setRecent(getRecent())
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  // Search with debounce
  const search = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); setLoading(false); return }
    setLoading(true)
    try {
      const r = await api.getBids({ search: q.trim(), sort_by: 'created_at', sort_order: 'desc' })
      setResults((r || []).slice(0, 8))
    } catch { setResults([]) }
    setLoading(false)
  }, [])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => search(query), 150)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [query, search])

  // Total items for keyboard nav
  const totalItems = query.trim()
    ? results.length + QUICK_ACTIONS.length
    : QUICK_ACTIONS.length + recent.length

  const goTo = useCallback((path: string, q?: string) => {
    if (q) pushRecent(q)
    onClose()
    navigate(path)
  }, [navigate, onClose])

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') { onClose(); return }
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelected(s => Math.min(s + 1, totalItems - 1)) }
    if (e.key === 'ArrowUp') { e.preventDefault(); setSelected(s => Math.max(s - 1, 0)) }
    if (e.key === 'Enter') {
      e.preventDefault()
      // Quick actions first
      const qaCount = QUICK_ACTIONS.length
      if (selected < qaCount) {
        const a = QUICK_ACTIONS[selected]
        if (a.action === 'new') { onClose(); navigate('/bids') }
        else goTo(a.path)
      } else if (query.trim()) {
        const bidIdx = selected - qaCount
        if (results[bidIdx]) goTo(`/bids/${results[bidIdx].id}`, query)
      } else {
        const recentIdx = selected - qaCount
        if (recent[recentIdx]) setQuery(recent[recentIdx])
      }
    }
  }

  if (!open) return null

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
        paddingTop: '12vh',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: 620, maxWidth: '92vw',
          background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-xl)', border: '1px solid var(--border-subtle)',
          overflow: 'hidden',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Search input */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 18px', borderBottom: '1px solid var(--border-subtle)' }}>
          <Search size={18} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
          <input
            ref={inputRef}
            value={query}
            onChange={e => { setQuery(e.target.value); setSelected(0) }}
            onKeyDown={handleKey}
            placeholder="Search bids, clients, references…"
            style={{
              flex: 1, border: 'none', outline: 'none', fontSize: 15,
              background: 'transparent', color: 'var(--text-primary)',
              fontFamily: 'var(--font-sans)',
            }}
          />
          {query && (
            <button onClick={() => { setQuery(''); setResults([]) }}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: 'var(--text-muted)' }}>
              <X size={14} />
            </button>
          )}
          <kbd style={{
            fontSize: 10, padding: '2px 7px', borderRadius: 5, color: 'var(--text-muted)',
            background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)',
            fontFamily: 'var(--font-mono)', flexShrink: 0
          }}>Esc</kbd>
        </div>

        {/* Results body */}
        <div style={{ maxHeight: 420, overflowY: 'auto' }}>

          {/* Quick Actions */}
          <div style={{ padding: '8px 14px 4px', fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
            Quick Actions
          </div>
          {QUICK_ACTIONS.map((a, i) => (
            <div key={a.label}
              style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '9px 18px',
                cursor: 'pointer', transition: 'background 100ms',
                background: selected === i ? 'var(--bg-tertiary)' : 'transparent',
              }}
              onClick={() => { if (a.action === 'new') { onClose(); navigate('/bids') } else goTo(a.path) }}
              onMouseEnter={() => setSelected(i)}
            >
              <div style={{ width: 28, height: 28, borderRadius: 8, background: `${a.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <a.icon size={14} style={{ color: a.color }} />
              </div>
              <span style={{ fontSize: 13, fontWeight: 500 }}>{a.label}</span>
              <ArrowRight size={12} style={{ marginLeft: 'auto', color: 'var(--text-muted)', opacity: selected === i ? 1 : 0 }} />
            </div>
          ))}

          {/* Recent searches (when no query) */}
          {!query.trim() && recent.length > 0 && (
            <>
              <div style={{ padding: '10px 14px 4px', fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                Recent
              </div>
              {recent.map((r, i) => {
                const idx = QUICK_ACTIONS.length + i
                return (
                  <div key={r}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 12, padding: '9px 18px',
                      cursor: 'pointer', background: selected === idx ? 'var(--bg-tertiary)' : 'transparent',
                    }}
                    onClick={() => setQuery(r)}
                    onMouseEnter={() => setSelected(idx)}
                  >
                    <Clock size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                    <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{r}</span>
                  </div>
                )
              })}
            </>
          )}

          {/* Search results */}
          {query.trim() && (
            <>
              <div style={{ padding: '10px 14px 4px', fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                {loading ? 'Searching…' : `${results.length} result${results.length !== 1 ? 's' : ''}`}
              </div>
              {results.length === 0 && !loading && (
                <div style={{ padding: '20px 18px', fontSize: 13, color: 'var(--text-muted)', textAlign: 'center' }}>
                  No bids found for "{query}"
                </div>
              )}
              {results.map((bid, i) => {
                const idx = QUICK_ACTIONS.length + i
                const winPct = bid.win_probability !== undefined
                  ? (bid.win_probability <= 1 ? bid.win_probability * 100 : bid.win_probability).toFixed(0)
                  : null
                const tcv = bid.estimated_tcv
                  ? bid.estimated_tcv >= 1e6 ? `$${(bid.estimated_tcv / 1e6).toFixed(1)}M`
                  : `$${(bid.estimated_tcv / 1e3).toFixed(0)}K`
                  : null
                return (
                  <div key={bid.id}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 12, padding: '10px 18px',
                      cursor: 'pointer', transition: 'background 100ms',
                      background: selected === idx ? 'var(--bg-tertiary)' : 'transparent',
                      borderTop: i === 0 ? '1px solid var(--border-subtle)' : 'none',
                    }}
                    onClick={() => goTo(`/bids/${bid.id}`, query)}
                    onMouseEnter={() => setSelected(idx)}
                  >
                    <div style={{
                      width: 32, height: 32, borderRadius: 10, flexShrink: 0,
                      background: bid.bid_recommendation === 'Go' ? 'rgba(5,150,105,0.1)' : 'rgba(0,102,255,0.08)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 13, fontWeight: 800,
                      color: bid.bid_recommendation === 'Go' ? '#059669' : '#0066FF',
                    }}>
                      {bid.client_name.charAt(0).toUpperCase()}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {bid.client_name}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1, display: 'flex', gap: 8 }}>
                        <span style={{ fontFamily: 'var(--font-mono)' }}>{bid.bid_reference}</span>
                        <span>{STATUS_LABELS[bid.status] || bid.status}</span>
                        {bid.client_industry && <span>{bid.client_industry}</span>}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 8, flexShrink: 0, alignItems: 'center' }}>
                      {winPct && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{winPct}% win</span>}
                      {tcv && <span style={{ fontSize: 11, fontWeight: 600, color: '#0066FF' }}>{tcv}</span>}
                      <ArrowRight size={12} style={{ color: 'var(--text-muted)', opacity: selected === idx ? 1 : 0 }} />
                    </div>
                  </div>
                )
              })}
            </>
          )}
        </div>

        {/* Footer hint */}
        <div style={{ padding: '8px 18px', borderTop: '1px solid var(--border-subtle)', display: 'flex', gap: 16, alignItems: 'center' }}>
          {[['↑↓', 'navigate'], ['↵', 'open'], ['Esc', 'close']].map(([key, label]) => (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <kbd style={{ fontSize: 9, padding: '2px 5px', borderRadius: 4, background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', fontFamily: 'var(--font-mono)' }}>{key}</kbd>
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{label}</span>
            </div>
          ))}
          <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-muted)' }}>ARISE Search</span>
        </div>
      </div>
    </div>
  )
}
