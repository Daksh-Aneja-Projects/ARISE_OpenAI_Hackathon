 
import { FileText, CheckCircle, AlertTriangle, BarChart3 } from 'lucide-react'
import { MetricCard, SectionCard, Badge } from './shared'

/** Renders markdown-like text: **bold**, line breaks, bullet/numbered lists */
function RichText({ text }: { text: string }) {
  if (!text) return null
  const paragraphs = text.split('\n\n').filter(Boolean)
  return (
    <div style={{ fontSize: 14, lineHeight: 1.8, color: 'var(--text-secondary)' }}>
      {paragraphs.map((p, i) => {
        const trimmed = p.trim()
        // Headings
        if (trimmed.startsWith('### ')) return <h4 key={i} style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', margin: '16px 0 6px' }}>{trimmed.slice(4)}</h4>
        if (trimmed.startsWith('## ')) return <h3 key={i} style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-primary)', margin: '20px 0 8px' }}>{trimmed.slice(3)}</h3>

        // Bullet/numbered lists
        const lines = trimmed.split('\n')
        const isList = lines.every(l => /^[\d]+\.|^[-•*]/.test(l.trim()))
        if (isList) {
          return (
            <ul key={i} style={{ margin: '8px 0', paddingLeft: 24 }}>
              {lines.map((l, j) => (
                <li key={j} style={{ marginBottom: 6 }}>
                  {parseBold(l.replace(/^[\d]+\.\s*|^[-•*]\s*/, ''))}
                </li>
              ))}
            </ul>
          )
        }

        // Regular paragraph
        return <p key={i} style={{ marginBottom: 12 }}>{parseBold(trimmed)}</p>
      })}
    </div>
  )
}

/** Parse **bold** markers into <strong> elements */
function parseBold(text: string) {
  const parts = text.split('**')
  if (parts.length <= 1) return text
  return parts.map((part, k) =>
    k % 2 === 1 ? <strong key={k} style={{ color: 'var(--text-primary)' }}>{part}</strong> : part
  )
}

export function OutputRenderer({ data }: { data: any }) {
  // The output_generator returns executive_summary and sow_outline at top level
  const execSummary = data?.executive_summary || data?.proposal_writer?.executive_summary || ''
  const sowOutline = data?.sow_outline || data?.proposal_writer?.sow_outline || ''
  const sectionsAvailable = data?.sections_available || 0
  const missingSections = data?.missing_sections || []

  // Also check for nested proposal_writer structure
  const pw = data?.proposal_writer || {}
  const methodology = pw.methodology || ''
  const teamOverview = pw.team_overview || ''
  const valueProp = pw.value_proposition || ''
  const caseStudies = pw.case_studies || []
  const quality = pw.quality_checks || []

  return (<>
    {/* Pipeline Status */}
    <SectionCard title="Proposal Assembly Status" icon={<BarChart3 size={16} />} color="#14B8A6">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        <MetricCard label="Sections Assembled" value={sectionsAvailable} color="#10B981" />
        <MetricCard label="Missing Sections" value={missingSections.length} color={missingSections.length > 0 ? '#EF4444' : '#10B981'} />
        <MetricCard label="Status" value={missingSections.length === 0 ? 'Complete' : 'Partial'} color={missingSections.length === 0 ? '#10B981' : '#F59E0B'} />
      </div>
      {missingSections.length > 0 && (
        <div style={{ marginTop: 12, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {missingSections.map((s: string, i: number) => <Badge key={i} text={s} color="#EF4444" />)}
        </div>
      )}
    </SectionCard>

    {/* Executive Summary */}
    {execSummary && (
      <SectionCard title="Executive Summary" icon={<FileText size={16} />} color="#14B8A6">
        <div style={{ padding: '20px 24px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', borderLeft: '4px solid #14B8A6' }}>
          <RichText text={execSummary} />
        </div>
      </SectionCard>
    )}

    {/* SOW Outline */}
    {sowOutline && (
      <SectionCard title="Statement of Work Outline" icon={<FileText size={16} />} color="#8B5CF6">
        <div style={{ padding: '20px 24px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', borderLeft: '4px solid #8B5CF6' }}>
          {typeof sowOutline === 'string' ? (
            <RichText text={sowOutline} />
          ) : sowOutline.sections ? (
            <>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Sections</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>{sowOutline.sections.map((s: string, i: number) => <Badge key={i} text={s} color="#8B5CF6" />)}</div>
              {sowOutline.key_deliverables && (
                <>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Key Deliverables</div>
                  <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: 'var(--text-secondary)' }}>
                    {sowOutline.key_deliverables.map((d: string, i: number) => <li key={i}>{d}</li>)}
                  </ul>
                </>
              )}
            </>
          ) : (
            <RichText text={JSON.stringify(sowOutline)} />
          )}
        </div>
      </SectionCard>
    )}

    {methodology && <SectionCard title="Methodology & Approach" icon={<FileText size={16} />} color="#3B82F6"><RichText text={methodology} /></SectionCard>}
    {teamOverview && <SectionCard title="Team Overview" icon={<FileText size={16} />} color="#8B5CF6"><RichText text={teamOverview} /></SectionCard>}
    {valueProp && <SectionCard title="Value Proposition" icon={<FileText size={16} />} color="#F59E0B"><RichText text={valueProp} /></SectionCard>}

    {caseStudies.length > 0 && (
      <SectionCard title={`Case Studies (${caseStudies.length})`} icon={<FileText size={16} />} color="#EC4899">
        <div style={{ display: 'grid', gap: 12 }}>
          {caseStudies.map((cs: any, i: number) => (
            <div key={i} style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', borderLeft: '4px solid #EC4899' }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#EC4899' }}>{cs.title}</div>
              {cs.client_type && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>{cs.client_type}</div>}
              {cs.challenge && <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 4 }}><strong>Challenge:</strong> {cs.challenge}</div>}
              {cs.solution && <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 4 }}><strong>Solution:</strong> {cs.solution}</div>}
              {cs.outcome && <div style={{ fontSize: 13, color: '#10B981' }}><strong>Outcome:</strong> {cs.outcome}</div>}
            </div>
          ))}
        </div>
      </SectionCard>
    )}

    {quality.length > 0 && (
      <SectionCard title="Quality Checks" icon={<CheckCircle size={16} />} color="#10B981">
        <table className="data-table">
          <thead><tr><th>Check</th><th>Status</th><th>Note</th></tr></thead>
          <tbody>
            {quality.map((q: any, i: number) => (
              <tr key={i}>
                <td style={{ fontWeight: 500 }}>{q.check}</td>
                <td><Badge text={q.status} color={q.status === 'pass' ? '#10B981' : '#EF4444'} /></td>
                <td style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{q.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </SectionCard>
    )}
  </>)
}
