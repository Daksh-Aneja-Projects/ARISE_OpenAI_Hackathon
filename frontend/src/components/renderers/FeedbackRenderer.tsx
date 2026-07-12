 
import { TrendingUp, CheckCircle, AlertTriangle, BookOpen, Zap, Target } from 'lucide-react'
import { MetricCard, SectionCard, Badge } from './shared'

export function FeedbackRenderer({ data }: { data: any }) {
  // Real paths from FeedbackLearningAgent.act():
  // data.analysis.{agent_assessments, reusable_knowledge, process_improvements, estimating_insights, bid_strengths, bid_weaknesses, overall_confidence, kb_updates}
  const analysis = data?.analysis || {}
  const assessments = analysis.agent_assessments || []
  const knowledge = analysis.reusable_knowledge || []
  const improvements = analysis.process_improvements || data?.improvements || data?.lessons || []
  const bidStrengths = analysis.bid_strengths || []
  const bidWeaknesses = analysis.bid_weaknesses || []
  const confidence = analysis.overall_confidence || '—'
  const learningsCaptured = data?.learnings_captured || 0

  const strong = assessments.filter((a: any) => a.quality === 'strong').length
  const adequate = assessments.filter((a: any) => a.quality === 'adequate').length
  const weak = assessments.filter((a: any) => a.quality === 'weak').length
  const confColor = confidence === 'high' ? '#10B981' : confidence === 'medium' ? '#F59E0B' : '#EF4444'

  const health = data?.pipeline_health || {}
  const healthScore = health.score ?? null
  const healthColor = healthScore === null ? '#6B7280' : healthScore >= 80 ? '#10B981' : healthScore >= 60 ? '#F59E0B' : '#EF4444'

  return (<>
    {/* Pipeline Health Score */}
    {healthScore !== null && (
      <SectionCard title="Pipeline Health Score" icon={<Target size={16} />} color={healthColor}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24, padding: '8px 0' }}>
          <div style={{ width: 80, height: 80, borderRadius: '50%', border: `4px solid ${healthColor}`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: healthColor, lineHeight: 1 }}>{healthScore}</div>
            <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>/100</div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8, flex: 1 }}>
            <MetricCard label="Agent Quality (30%)" value={health.agent_quality_score ?? '—'} color="#6366F1" />
            <MetricCard label="Consistency (25%)" value={health.consistency_score ?? '—'} color="#3B82F6" />
            <MetricCard label="Grounding (25%)" value={health.grounding_avg != null ? `${(health.grounding_avg * 100).toFixed(0)}%` : '—'} color="#10B981" />
            <MetricCard label="Identity (20%)" value={health.identity_violations === 0 ? '✓ Clean' : `⚠ ${health.identity_violations} violations`} color={health.identity_violations === 0 ? '#10B981' : '#EF4444'} />
          </div>
        </div>
        {health.contradictions_found > 0 && (
          <div style={{ marginTop: 8, padding: '8px 12px', background: '#FEF2F2', borderRadius: 'var(--radius-md)', border: '1px solid #FECACA', fontSize: 12, color: '#991B1B' }}>
            ⚠️ {health.contradictions_found} cross-agent contradiction{health.contradictions_found > 1 ? 's' : ''} detected — see learning captures below
          </div>
        )}
      </SectionCard>
    )}

    {/* Overview Metrics */}
    <SectionCard title="Feedback & Learning Overview" icon={<TrendingUp size={16} />} color="#6366F1">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <MetricCard label="Overall Confidence" value={confidence} color={confColor} />
        <MetricCard label="Agents Assessed" value={assessments.length} color="#6366F1" />
        <MetricCard label="Knowledge Items" value={knowledge.length} color="#3B82F6" />
        <MetricCard label="Learnings Captured" value={learningsCaptured} color="#10B981" />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 12 }}>
        <MetricCard label="Strong Agents" value={strong} color="#10B981" />
        <MetricCard label="Adequate Agents" value={adequate} color="#F59E0B" />
        <MetricCard label="Weak Agents" value={weak} color={weak > 0 ? '#EF4444' : '#10B981'} />
      </div>
    </SectionCard>

    {/* Agent Assessments */}
    {assessments.length > 0 && (
      <SectionCard title={`Agent Quality Assessments (${assessments.length})`} icon={<CheckCircle size={16} />} color="#8B5CF6">
        <table className="data-table">
          <thead>
            <tr><th>Agent</th><th>Quality</th><th>Strengths</th><th>Gaps</th><th>Improvement</th></tr>
          </thead>
          <tbody>
            {assessments.map((a: any, i: number) => {
              const qColor = a.quality === 'strong' ? '#10B981' : a.quality === 'adequate' ? '#F59E0B' : '#EF4444'
              // Handle strengths/gaps as either arrays or semicolon-delimited strings
              const rawS = a.strengths || []
              const strengths = Array.isArray(rawS) ? rawS : typeof rawS === 'string' ? rawS.split(/[;,]/).map((s: string) => s.trim()).filter(Boolean) : []
              const rawG = a.gaps || []
              const gaps = Array.isArray(rawG) ? rawG : typeof rawG === 'string' ? rawG.split(/[;,]/).map((s: string) => s.trim()).filter(Boolean) : []
              const improvement = typeof a.improvement === 'string' ? a.improvement : typeof a.improvement === 'object' ? (a.improvement?.suggestion || a.improvement?.recommendation || JSON.stringify(a.improvement)) : '—'
              return (
                <tr key={i}>
                  <td style={{ fontWeight: 700, textTransform: 'capitalize' }}>{(a.agent || '').replace(/_/g, ' ')}</td>
                  <td><Badge text={(a.quality || '—').toUpperCase()} color={qColor} /></td>
                  <td style={{ fontSize: 12, maxWidth: 200 }}>{strengths.slice(0, 2).join('; ') || '—'}</td>
                  <td style={{ fontSize: 12, maxWidth: 200, color: '#EF4444' }}>{gaps.slice(0, 2).join('; ') || '—'}</td>
                  <td style={{ fontSize: 12, maxWidth: 200 }}>{improvement}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </SectionCard>
    )}

    {/* Bid Strengths & Weaknesses */}
    {(bidStrengths.length > 0 || bidWeaknesses.length > 0) && (
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {bidStrengths.length > 0 && (
          <SectionCard title={`Bid Strengths (${bidStrengths.length})`} icon={<Target size={16} />} color="#10B981">
            {bidStrengths.map((s: any, i: number) => (
              <div key={i} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 8, border: '1px solid var(--border-subtle)', borderLeft: '3px solid #10B981', fontSize: 13, fontWeight: 600 }}>
                {typeof s === 'string' ? s : s.strength || s.title}
              </div>
            ))}
          </SectionCard>
        )}
        {bidWeaknesses.length > 0 && (
          <SectionCard title={`Bid Weaknesses (${bidWeaknesses.length})`} icon={<AlertTriangle size={16} />} color="#EF4444">
            {bidWeaknesses.map((w: any, i: number) => (
              <div key={i} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 8, border: '1px solid var(--border-subtle)', borderLeft: '3px solid #EF4444', fontSize: 13, fontWeight: 600 }}>
                {typeof w === 'string' ? w : w.weakness || w.title}
              </div>
            ))}
          </SectionCard>
        )}
      </div>
    )}

    {/* Process Improvements */}
    {improvements.length > 0 && (
      <SectionCard title={`Process Improvements (${improvements.length})`} icon={<Zap size={16} />} color="#F59E0B">
        {improvements.map((imp: any, i: number) => (
          <div key={i} style={{ padding: '12px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 8, border: '1px solid var(--border-subtle)', borderLeft: '3px solid #F59E0B' }}>
            <div style={{ fontSize: 13, fontWeight: 700 }}>{typeof imp === 'string' ? imp : imp.area || imp.title}</div>
            {imp.issue && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>Issue: {imp.issue}</div>}
            {imp.recommendation && <div style={{ fontSize: 12, color: '#10B981', marginTop: 4 }}>→ {imp.recommendation}</div>}
          </div>
        ))}
      </SectionCard>
    )}

    {/* Reusable Knowledge */}
    {knowledge.length > 0 && (
      <SectionCard title={`Reusable Knowledge (${knowledge.length})`} icon={<BookOpen size={16} />} color="#3B82F6">
        {knowledge.map((k: any, i: number) => (
          <div key={i} style={{ padding: '12px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 8, border: '1px solid var(--border-subtle)', borderLeft: '3px solid #3B82F6' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
              <span style={{ fontSize: 13, fontWeight: 600, flex: 1 }}>{k.content}</span>
              {k.category && <Badge text={k.category.replace(/_/g, ' ').toUpperCase()} color="#3B82F6" />}
            </div>
            {k.products && k.products.length > 0 && (
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                {k.products.map((p: any, pi: number) => <Badge key={pi} text={p} color="#8B5CF6" />)}
              </div>
            )}
          </div>
        ))}
      </SectionCard>
    )}
  </>)
}
