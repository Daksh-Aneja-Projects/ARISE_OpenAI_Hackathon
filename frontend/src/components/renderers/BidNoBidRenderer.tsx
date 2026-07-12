 
import { Target, AlertTriangle, ShieldCheck } from 'lucide-react'
import { SectionCard } from './shared'

export function BidNoBidRenderer({ data }: { data: any }) {
  // Real path: data.score_card.{dimensions, capability_gaps, key_risks, win_probability, recommendation, conditions, deal_characteristics}
  const sc = data?.score_card || {}
  const rec = sc.recommendation || data?.recommendation || '—'
  const wp = sc.win_probability || data?.win_probability || 0
  const dims = sc.dimensions || []
  const gaps = sc.capability_gaps || []
  const risks = sc.key_risks || []
  const conditions = sc.conditions || []
  const recColor = rec.toLowerCase().includes('go') && !rec.toLowerCase().includes('no') ? '#10B981' : rec.toLowerCase().includes('no') ? '#EF4444' : '#F59E0B'
  const wpPct = typeof wp === 'number' ? (wp <= 1 ? wp * 100 : wp) : 50

  return (<>
    {/* Decision Banner */}
    <SectionCard title="Strategic Recommendation" icon={<Target size={16} />} color={recColor}>
      <div style={{ display: 'flex', gap: 32, alignItems: 'center', marginBottom: 24 }}>
        <div style={{ padding: '20px 32px', borderRadius: 16, background: `${recColor}12`, border: `3px solid ${recColor}`, textAlign: 'center', minWidth: 160 }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>Decision</div>
          <div style={{ fontSize: 28, fontWeight: 900, color: recColor }}>{rec}</div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Win Probability</div>
          <div style={{ fontSize: 48, fontWeight: 900, color: 'var(--text-primary)', lineHeight: 1.1 }}>{wpPct.toFixed(0)}%</div>
          <div style={{ width: 240, height: 10, background: 'var(--bg-tertiary)', borderRadius: 5, marginTop: 10 }}>
            <div style={{ width: `${wpPct}%`, height: '100%', background: `linear-gradient(90deg, ${recColor}, ${recColor}aa)`, borderRadius: 5, transition: 'width 1s ease' }} />
          </div>
        </div>
      </div>

      {/* Conditions */}
      {conditions.length > 0 && (
        <div style={{ marginTop: 16, padding: '14px 16px', background: `${recColor}08`, borderRadius: 'var(--radius-md)', border: `1px solid ${recColor}20` }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: recColor, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>Conditions for Proceeding</div>
          {conditions.map((c: any, i: number) => (
            <div key={i} style={{ fontSize: 13, color: 'var(--text-secondary)', padding: '4px 0', display: 'flex', gap: 8 }}>
              <span style={{ color: recColor, fontWeight: 700 }}>→</span>
              <span>{typeof c === 'string' ? c : c.condition || c.description || JSON.stringify(c)}</span>
            </div>
          ))}
        </div>
      )}
    </SectionCard>

    {/* Scoring Dimensions */}
    {dims.length > 0 && (
      <SectionCard title="Scoring Dimensions" icon={<ShieldCheck size={16} />} color="#3B82F6">
        <table className="data-table">
          <thead><tr><th>Dimension</th><th>Score</th><th style={{ width: '50%' }}>Assessment</th></tr></thead>
          <tbody>{dims.map((d: any, i: number) => {
            const rawScore = d.score || d.value || 0
            const rawNum = typeof rawScore === 'string' ? parseFloat(rawScore) : rawScore
            // Normalize: if score is 0-1 range (e.g. 0.9), convert to percentage (90)
            const scoreNum = rawNum > 0 && rawNum <= 1 ? Math.round(rawNum * 100) : Math.round(rawNum)
            const sColor = scoreNum >= 80 ? '#10B981' : scoreNum >= 60 ? '#F59E0B' : '#EF4444'
            return (
              <tr key={i}>
                <td style={{ fontWeight: 600, textTransform: 'capitalize' }}>{d.dimension || d.name || d.criterion}</td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 60, height: 6, background: 'var(--bg-tertiary)', borderRadius: 3 }}>
                      <div style={{ width: `${scoreNum}%`, height: '100%', background: sColor, borderRadius: 3 }} />
                    </div>
                    <span style={{ fontWeight: 700, color: sColor, fontSize: 13 }}>{scoreNum}%</span>
                  </div>
                </td>
                <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{d.rationale || d.assessment || d.notes || '—'}</td>
              </tr>
            )
          })}</tbody>
        </table>
      </SectionCard>
    )}

    {/* Key Risks & Capability Gaps */}
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
      {risks.length > 0 && (
        <SectionCard title={`Key Risks (${risks.length})`} icon={<AlertTriangle size={16} />} color="#EF4444">
          {risks.map((r: any, i: number) => (
            <div key={i} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 8, border: '1px solid var(--border-subtle)', borderLeft: '3px solid #EF4444' }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{typeof r === 'string' ? r : r.risk || r.title || r.description}</div>
              {r.mitigation && <div style={{ fontSize: 12, color: '#10B981', marginTop: 4 }}>→ {r.mitigation}</div>}
            </div>
          ))}
        </SectionCard>
      )}
      {gaps.length > 0 && (
        <SectionCard title={`Capability Gaps (${gaps.length})`} icon={<AlertTriangle size={16} />} color="#F59E0B">
          {gaps.map((g: any, i: number) => (
            <div key={i} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 8, border: '1px solid var(--border-subtle)', borderLeft: '3px solid #F59E0B' }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{typeof g === 'string' ? g : g.gap || g.title || g.area}</div>
              {g.mitigation && <div style={{ fontSize: 12, color: '#10B981', marginTop: 4 }}>→ {g.mitigation}</div>}
            </div>
          ))}
        </SectionCard>
      )}
    </div>
  </>)
}
