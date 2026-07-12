 
import { CheckCircle, AlertTriangle, Shield, BarChart3, FileText, BookOpen } from 'lucide-react'
import { MetricCard, SectionCard, Badge } from './shared'

export function QARenderer({ data }: { data: any }) {
  // QAAgent.act() returns: {qa_scores, structural_checks, readability_scores, narrative, hitl_summary}
  const qaScores = data?.qa_scores || data || {}
  const structuralChecks = data?.structural_checks || []
  const readabilityScores = data?.readability_scores || {}
  const qualityDims = qaScores.quality_scores || {}
  const coverage = qaScores.rfp_requirements_coverage || []
  const consistencyChecks = qaScores.consistency_checks || []
  const criticalFixes = qaScores.critical_fixes || []
  const improvements = qaScores.improvements || []
  const brandCheck = qaScores.brand_check || {}
  const readiness = qaScores.overall_readiness || 'Unknown'

  const overallScore = qualityDims.overall || 0
  const scoreColor = overallScore >= 80 ? '#10B981' : overallScore >= 60 ? '#F59E0B' : '#EF4444'
  const readinessColor = readiness === 'Ready' ? '#10B981' : readiness === 'Needs Work' ? '#F59E0B' : '#EF4444'

  // Coverage stats
  const covered = coverage.filter((c: any) => c.status === 'covered').length
  const partial = coverage.filter((c: any) => c.status === 'partial').length
  const missing = coverage.filter((c: any) => c.status === 'missing').length

  return (<>
    {/* Quality Overview */}
    <SectionCard title="Quality Assessment Overview" icon={<Shield size={16} />} color="#A855F7">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
        <div style={{ padding: '16px 18px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Overall Score</div>
          <div style={{ fontSize: 36, fontWeight: 900, marginTop: 4, color: scoreColor }}>{overallScore}</div>
          {overallScore > 0 && (
            <div style={{ width: '100%', height: 6, background: 'var(--bg-tertiary)', borderRadius: 3, marginTop: 8 }}>
              <div style={{ width: `${Math.min(overallScore, 100)}%`, height: '100%', background: scoreColor, borderRadius: 3, transition: 'width 1s ease' }} />
            </div>
          )}
        </div>
        <MetricCard label="Readiness" value={readiness} color={readinessColor} />
        <MetricCard label="RFP Covered" value={`${covered}/${covered + partial + missing}`} color="#10B981" />
        <MetricCard label="Critical Fixes" value={criticalFixes.length} color={criticalFixes.length > 0 ? '#EF4444' : '#10B981'} />
        <MetricCard label="Brand Check" value={brandCheck.pass ? 'PASS' : 'FAIL'} color={brandCheck.pass ? '#10B981' : '#EF4444'} />
      </div>
    </SectionCard>

    {/* Quality Dimension Scores */}
    {Object.keys(qualityDims).length > 1 && (
      <SectionCard title="Quality Dimensions" icon={<BarChart3 size={16} />} color="#8B5CF6">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
          {['completeness', 'consistency', 'accuracy', 'compliance', 'quality'].map(dim => {
            const val = qualityDims[dim] || 0
            const dColor = val >= 80 ? '#10B981' : val >= 60 ? '#F59E0B' : '#EF4444'
            return (
              <div key={dim} style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{dim}</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: dColor, marginTop: 4 }}>{val}</div>
                <div style={{ width: '100%', height: 4, background: 'var(--bg-tertiary)', borderRadius: 2, marginTop: 6 }}>
                  <div style={{ width: `${Math.min(val, 100)}%`, height: '100%', background: dColor, borderRadius: 2 }} />
                </div>
              </div>
            )
          })}
        </div>
      </SectionCard>
    )}

    {/* Structural Checks */}
    {structuralChecks.length > 0 && (
      <SectionCard title={`Structural Checks (${structuralChecks.filter((c: any) => c.status === 'pass').length}/${structuralChecks.length})`} icon={<CheckCircle size={16} />} color="#3B82F6">
        <table className="data-table">
          <thead><tr><th>Check</th><th>Status</th><th>Details</th></tr></thead>
          <tbody>
            {structuralChecks.map((c: any, i: number) => {
              const status = c.status || 'unknown'
              const sColor = status === 'pass' ? '#10B981' : status === 'fail' ? '#EF4444' : '#F59E0B'
              return (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{c.check}</td>
                  <td><Badge text={status.toUpperCase()} color={sColor} /></td>
                  <td style={{ fontSize: 12, color: 'var(--text-secondary)', maxWidth: 400 }}>{c.detail || '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </SectionCard>
    )}

    {/* RFP Requirements Coverage */}
    {coverage.length > 0 && (
      <SectionCard title={`RFP Requirements Coverage (${covered} covered, ${partial} partial, ${missing} missing)`} icon={<FileText size={16} />} color="#06B6D4">
        <table className="data-table">
          <thead><tr><th>Requirement</th><th>Section</th><th>Status</th><th>Covered By</th></tr></thead>
          <tbody>
            {coverage.map((r: any, i: number) => {
              const sColor = r.status === 'covered' ? '#10B981' : r.status === 'partial' ? '#F59E0B' : '#EF4444'
              return (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{r.requirement}</td>
                  <td style={{ fontSize: 11 }}>{r.rfp_section || '—'}</td>
                  <td><Badge text={(r.status || '—').toUpperCase()} color={sColor} /></td>
                  <td style={{ fontSize: 12 }}>{r.covered_by || '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </SectionCard>
    )}

    {/* Readability Scores */}
    {Object.keys(readabilityScores).length > 0 && (
      <SectionCard title="Narrative Readability" icon={<BookOpen size={16} />} color="#14B8A6">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          {Object.entries(readabilityScores).map(([agent, score]: [string, any]) => {
            const rColor = score >= 65 ? '#10B981' : score >= 50 ? '#F59E0B' : '#EF4444'
            const label = score >= 65 ? 'Good' : score >= 50 ? 'Needs Work' : 'Too Complex'
            return (
              <div key={agent} style={{ padding: '12px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', borderLeft: `3px solid ${rColor}` }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{agent.replace('_output', '').replace(/_/g, ' ')}</div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 4 }}>
                  <span style={{ fontSize: 20, fontWeight: 800, color: rColor }}>{score}</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>/100</span>
                  <Badge text={label} color={rColor} />
                </div>
              </div>
            )
          })}
        </div>
      </SectionCard>
    )}

    {/* Critical Fixes */}
    {criticalFixes.length > 0 && (
      <SectionCard title={`Critical Fixes (${criticalFixes.length})`} icon={<AlertTriangle size={16} />} color="#EF4444">
        {criticalFixes.map((fix: any, i: number) => (
          <div key={i} style={{ padding: '10px 14px', background: '#FEF2F2', borderRadius: 6, marginBottom: 6, borderLeft: '3px solid #EF4444', fontSize: 13, fontWeight: 600, color: '#991B1B' }}>
            {typeof fix === 'string' ? fix : fix.fix || fix.title || JSON.stringify(fix)}
          </div>
        ))}
      </SectionCard>
    )}

    {/* Improvements */}
    {improvements.length > 0 && (
      <SectionCard title={`Improvements (${improvements.length})`} icon={<CheckCircle size={16} />} color="#10B981">
        {improvements.map((r: any, i: number) => (
          <div key={i} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 6, marginBottom: 6, border: '1px solid var(--border-subtle)', borderLeft: '3px solid #10B981', fontSize: 13 }}>
            {typeof r === 'string' ? r : r.recommendation || r.action || r.title}
          </div>
        ))}
      </SectionCard>
    )}
  </>)
}

