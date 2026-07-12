 
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { HelpCircle, FileText, MessageSquare, Save, RefreshCw, CheckCircle, AlertTriangle, ChevronDown } from 'lucide-react'
import { MetricCard, SectionCard, Badge } from './shared'
import { api } from '../../api'

interface DiscoveryRendererProps {
  data: any
  bidId?: string
}

export function DiscoveryRenderer({ data, bidId }: DiscoveryRendererProps) {
  const navigate = useNavigate()
  const analysis = data?.discovery_analysis || data || {}
  const categories = analysis.discovery_categories || []
  const preMeeting = analysis.pre_meeting_requests || []
  const totalQ = analysis.total_questions || categories.reduce((s: number, c: any) => s + (c.questions?.length || 0), 0)
  const mustAsk = analysis.must_ask_count || categories.reduce((s: number, c: any) => s + (c.questions?.filter((q: any) => q.priority === 'must-ask')?.length || 0), 0)

  const [answerMode, setAnswerMode] = useState(false)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState<any>(null)
  const [savedAnswers, setSavedAnswers] = useState<any[]>([])
  const [expandedCats, setExpandedCats] = useState<Record<number, boolean>>({})

  // Load saved answers on mount
  useEffect(() => {
    if (bidId) {
      api.getDiscoveryAnswers(bidId).then(res => {
        const saved = res.answers || []
        if (saved.length > 0) {
          const map: Record<string, string> = {}
          saved.forEach((a: any) => { if (a.answer) map[a.question] = a.answer })
          setAnswers(map)
          setSavedAnswers(saved)
        }
      }).catch(() => {})
    }
  }, [bidId])

  const answerCount = Object.values(answers).filter(v => v.trim()).length

  const handleSave = async () => {
    if (!bidId || answerCount === 0) return
    setSaving(true)
    try {
      // Build answers array from all questions
      const allAnswers: any[] = []
      categories.forEach((cat: any) => {
        (cat.questions || []).forEach((q: any) => {
          const answer = answers[q.question] || ''
          if (answer.trim()) {
            allAnswers.push({ question: q.question, category: cat.category, answer: answer.trim() })
          }
        })
      })
      const result = await api.saveDiscoveryAnswers(bidId, allAnswers)
      setSaveResult(result)
      setSavedAnswers(allAnswers)
    } catch (e: any) {
      setSaveResult({ error: e.message })
    }
    setSaving(false)
  }

  const toggleCat = (idx: number) => setExpandedCats(prev => ({ ...prev, [idx]: !prev[idx] }))

  return (<>
    <SectionCard title="Discovery Overview" icon={<HelpCircle size={16} />} color="#F97316">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
        <MetricCard label="Total Questions" value={totalQ} color="#F97316" />
        <MetricCard label="Must-Ask" value={mustAsk} color="#DC2626" />
        <MetricCard label="Categories" value={categories.length} color="#8B5CF6" />
        <MetricCard label="Doc Requests" value={preMeeting.length} color="#06B6D4" />
        <MetricCard label="Answers Saved" value={savedAnswers.length} color="#10B981" />
      </div>
    </SectionCard>

    {/* Client Response Mode Toggle */}
    {bidId && (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 16px', background: answerMode ? 'rgba(16,185,129,0.06)' : 'var(--bg-glass)',
        borderRadius: 12, border: `1px solid ${answerMode ? 'rgba(16,185,129,0.2)' : 'var(--border-subtle)'}`,
        marginBottom: 16, transition: 'all 0.2s',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <MessageSquare size={16} style={{ color: answerMode ? '#10B981' : 'var(--text-muted)' }} />
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: answerMode ? '#10B981' : 'var(--text-primary)' }}>
              Client Response Mode
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              Paste client answers to discovery questions. Affected agents will be flagged for re-run.
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {answerMode && answerCount > 0 && (
            <button
              onClick={handleSave}
              disabled={saving}
              style={{
                all: 'unset', cursor: saving ? 'wait' : 'pointer',
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '7px 16px', borderRadius: 8,
                background: 'linear-gradient(135deg, #10B981, #059669)',
                color: '#fff', fontSize: 12, fontWeight: 700,
                opacity: saving ? 0.6 : 1,
              }}
            >
              <Save size={13} /> {saving ? 'Saving...' : `Save ${answerCount} Answer${answerCount !== 1 ? 's' : ''}`}
            </button>
          )}
          <button
            onClick={() => setAnswerMode(!answerMode)}
            style={{
              all: 'unset', cursor: 'pointer',
              padding: '7px 14px', borderRadius: 8,
              background: answerMode ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.08)',
              color: answerMode ? '#EF4444' : '#10B981',
              fontSize: 12, fontWeight: 700, border: `1px solid ${answerMode ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)'}`,
            }}
          >
            {answerMode ? '✕ Close' : '✎ Enter Answers'}
          </button>
        </div>
      </div>
    )}

    {/* Save Result — Re-run Prompt */}
    {saveResult && !saveResult.error && (
      <div style={{
        padding: '16px 20px', background: 'rgba(16,185,129,0.06)', borderRadius: 12,
        border: '1px solid rgba(16,185,129,0.2)', marginBottom: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <CheckCircle size={16} style={{ color: '#10B981' }} />
          <span style={{ fontSize: 14, fontWeight: 700, color: '#10B981' }}>{saveResult.message}</span>
        </div>
        {saveResult.affected_agents?.length > 0 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
              <AlertTriangle size={14} style={{ color: '#F59E0B' }} />
              <span style={{ fontSize: 12, fontWeight: 700, color: '#F59E0B' }}>
                The following agents should be re-run to incorporate client answers:
              </span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {saveResult.affected_agents.map((agent: any) => (
                <button
                  key={agent.key}
                  onClick={() => navigate(`/bids/${bidId}/agent/${agent.key}`)}
                  style={{
                    all: 'unset', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '8px 14px', borderRadius: 8,
                    background: 'var(--bg-glass)', border: '1px solid rgba(245,158,11,0.2)',
                    fontSize: 12, fontWeight: 600, color: 'var(--text-primary)',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = '#F59E0B'; e.currentTarget.style.background = 'rgba(245,158,11,0.06)' }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(245,158,11,0.2)'; e.currentTarget.style.background = 'var(--bg-glass)' }}
                >
                  <RefreshCw size={12} style={{ color: '#F59E0B' }} />
                  {agent.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    )}

    {/* Questions by Category */}
    {categories.map((cat: any, ci: number) => {
      const catColor = ['#3B82F6','#10B981','#8B5CF6','#F59E0B','#EC4899','#06B6D4'][ci % 6]
      const questions = cat.questions || []
      const answeredInCat = questions.filter((q: any) => answers[q.question]?.trim()).length
      const isExpanded = expandedCats[ci] !== false // default open

      return (
        <SectionCard key={ci} title={`${cat.category} (${questions.length} questions${answeredInCat > 0 ? ` · ${answeredInCat} answered` : ''})`} icon={<HelpCircle size={16} />} color={catColor}>
          {/* Collapse toggle for large categories */}
          {questions.length > 5 && (
            <button onClick={() => toggleCat(ci)} style={{
              all: 'unset', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
              fontSize: 11, color: catColor, fontWeight: 600, marginBottom: 8,
            }}>
              <ChevronDown size={12} style={{ transform: isExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
              {isExpanded ? 'Collapse' : `Show all ${questions.length}`}
            </button>
          )}

          {(isExpanded ? questions : questions.slice(0, 5)).map((q: any, qi: number) => {
            const pColor = q.priority === 'must-ask' ? '#DC2626' : q.priority === 'should-ask' ? '#F59E0B' : '#6B7280'
            const hasAnswer = answers[q.question]?.trim()
            const hasSavedAnswer = savedAnswers.some((sa: any) => sa.question === q.question && sa.answer)

            return (
              <div key={qi} style={{
                padding: '12px 14px', background: hasAnswer ? 'rgba(16,185,129,0.03)' : 'var(--bg-glass)',
                borderRadius: 'var(--radius-md)', marginBottom: 8,
                border: `1px solid ${hasAnswer ? 'rgba(16,185,129,0.15)' : 'var(--border-subtle)'}`,
                borderLeft: `3px solid ${hasAnswer ? '#10B981' : pColor}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, flex: 1 }}>{q.question}</span>
                  <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                    {hasSavedAnswer && <Badge text="SAVED" color="#10B981" />}
                    <Badge text={(q.priority || 'medium').toUpperCase()} color={pColor} />
                  </div>
                </div>
                {q.rfp_trigger && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, fontStyle: 'italic' }}>RFP: {q.rfp_trigger}</div>}
                {q.why_important && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{q.why_important}</div>}

                {/* Answer Input (only in answer mode) */}
                {answerMode && (
                  <div style={{ marginTop: 10 }}>
                    <textarea
                      placeholder="Paste client's answer here..."
                      value={answers[q.question] || ''}
                      onChange={e => setAnswers(prev => ({ ...prev, [q.question]: e.target.value }))}
                      style={{
                        width: '100%', minHeight: 60, padding: '10px 12px',
                        background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)',
                        borderRadius: 8, color: 'var(--text-primary)', fontSize: 12,
                        fontFamily: 'inherit', resize: 'vertical', lineHeight: 1.6,
                        outline: 'none', transition: 'border-color 0.2s',
                      }}
                      onFocus={e => e.target.style.borderColor = '#10B981'}
                      onBlur={e => e.target.style.borderColor = 'var(--border-subtle)'}
                    />
                  </div>
                )}

                {/* Show saved answer when NOT in answer mode */}
                {!answerMode && hasAnswer && (
                  <div style={{
                    marginTop: 8, padding: '8px 12px', background: 'rgba(16,185,129,0.04)',
                    borderRadius: 8, border: '1px solid rgba(16,185,129,0.1)',
                  }}>
                    <div style={{ fontSize: 10, color: '#10B981', fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>Client Answer</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{answers[q.question]}</div>
                  </div>
                )}
              </div>
            )
          })}
        </SectionCard>
      )
    })}

    {preMeeting.length > 0 && (
      <SectionCard title="Pre-Meeting Document Requests" icon={<FileText size={16} />} color="#14B8A6">
        {preMeeting.map((p: any, i: number) => (
          <div key={i} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 8, border: '1px solid var(--border-subtle)', borderLeft: '3px solid #14B8A6' }}>
            <span style={{ fontSize: 13, fontWeight: 700 }}>{p.document || p.title || (typeof p === 'string' ? p : '')}</span>
            {p.reason && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{p.reason}</div>}
          </div>
        ))}
      </SectionCard>
    )}
  </>)
}
