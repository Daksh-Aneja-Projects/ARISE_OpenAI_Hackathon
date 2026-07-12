 
import { Shield, Target, TrendingUp, DollarSign, AlertTriangle, Crosshair } from 'lucide-react'
import { SectionCard, Badge, MetricCard } from './shared'

export function CompetitiveRenderer({ data }: { data: any }) {
  // Real path: data.competitive_landscape.{competitors, incumbent, win_themes, differentiators, vulnerabilities, pricing_strategy}
  const cl = data?.competitive_landscape || data || {}
  const competitors = cl.competitors || data?.competitors || data?.ranked_competitors || []
  const winThemes = cl.win_themes || data?.win_themes || []
  const diffs = cl.differentiators || data?.differentiators || []
  const pricing = cl.pricing_strategy || data?.pricing_strategy || {}
  const dealStrategy = cl.deal_strategy || data?.deal_strategy || {}
  const vulns = cl.vulnerabilities || data?.vulnerabilities || []

  return (<>
    {/* Competitor Cards */}
    {competitors.length > 0 && (
      <SectionCard title={`Competitive Landscape (${competitors.length} competitors)`} icon={<Shield size={16} />} color="#EC4899">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
          {competitors.slice(0, 8).map((c: any, i: number) => {
            const threat = (c.threat_level || c.threat || c.relevance || 'medium').toLowerCase()
            const tColor = threat.includes('high') || threat.includes('primary') ? '#DC2626' : threat.includes('medium') || threat.includes('secondary') ? '#F59E0B' : '#10B981'
            const strengths = Array.isArray(c.strengths) ? c.strengths : c.strength ? [c.strength] : []
            const weaknesses = Array.isArray(c.weaknesses) ? c.weaknesses : c.weakness ? [c.weakness] : []
            const counterStrategy = c.counter_strategy || c.counter || ''
            return (
              <div key={i} style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', borderLeft: `4px solid ${tColor}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: 15, fontWeight: 700 }}>{c.name || c.competitor}</span>
                  <Badge text={threat.toUpperCase()} color={tColor} />
                </div>
                {strengths.length > 0 && (
                  <div style={{ marginBottom: 6 }}>
                    <div style={{ fontSize: 10, color: '#10B981', fontWeight: 700, textTransform: 'uppercase', marginBottom: 3 }}>Strengths</div>
                    {strengths.slice(0, 3).map((s: any, si: number) => (
                      <div key={si} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '1px 0' }}>+ {s}</div>
                    ))}
                  </div>
                )}
                {weaknesses.length > 0 && (
                  <div>
                    <div style={{ fontSize: 10, color: '#EF4444', fontWeight: 700, textTransform: 'uppercase', marginBottom: 3 }}>Weaknesses</div>
                    {weaknesses.slice(0, 3).map((w: any, wi: number) => (
                      <div key={wi} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '1px 0' }}>− {w}</div>
                    ))}
                  </div>
                )}
                {counterStrategy && <div style={{ fontSize: 12, color: '#3B82F6', marginTop: 6, fontStyle: 'italic' }}>Strategy: {counterStrategy}</div>}
              </div>
            )
          })}
        </div>
      </SectionCard>
    )}

    {/* Win Themes */}
    {winThemes.length > 0 && (
      <SectionCard title={`Win Themes (${winThemes.length})`} icon={<Target size={16} />} color="#10B981">
        {winThemes.map((w: any, i: number) => (
          <div key={i} style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 10, border: '1px solid var(--border-subtle)', borderLeft: '4px solid #10B981' }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#10B981' }}>{typeof w === 'string' ? w : w.theme || w.title}</div>
            {w.rfp_criteria && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Criteria: {w.rfp_criteria}</div>}
            {w.differentiator && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}><strong>Differentiator:</strong> {w.differentiator}</div>}
            {w.evidence && <div style={{ fontSize: 12, color: '#3B82F6', marginTop: 4 }}>Evidence: {w.evidence}</div>}
            {w.impact && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4, fontStyle: 'italic' }}>→ {w.impact}</div>}
            {w.messaging && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, fontStyle: 'italic' }}>→ {w.messaging}</div>}
          </div>
        ))}
      </SectionCard>
    )}

    {/* Differentiators */}
    {diffs.length > 0 && (
      <SectionCard title={`Differentiators (${diffs.length})`} icon={<TrendingUp size={16} />} color="#8B5CF6">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
          {diffs.map((d: any, i: number) => {
            let label = ''
            let detail = ''
            if (typeof d === 'string') {
              label = d
            } else {
              // Try common key names for the differentiator title
              label = d.differentiator || d.what || d.title || d.name || d.area || d.capability || d.theme || ''
              // Try common key names for detail/description
              detail = d.proof_point || d.why_unique || d.description || d.evidence || d.rationale || d.detail || d.value || ''
              // Also show RFP requirement if present
              const rfpReq = d.rfp_req || d.rfp_requirement || d.mapped_to || ''
              if (rfpReq) detail = (detail ? detail + ' ' : '') + `(Maps to: ${rfpReq})`
              // If still no label, pick the first string value from the object
              if (!label) {
                const vals = Object.values(d).filter(v => typeof v === 'string' && (v as string).length > 3)
                label = (vals[0] as string) || JSON.stringify(d)
                if (vals.length > 1) detail = detail || (vals.slice(1).join(' — '))
              }
            }
            return (
              <div key={i} style={{ padding: '12px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', borderLeft: '3px solid #8B5CF6' }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>{label}</div>
                {detail && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.5 }}>{detail}</div>}
              </div>
            )
          })}
        </div>
      </SectionCard>
    )}

    {/* Pricing Strategy */}
    {Object.keys(pricing).length > 0 && (
      <SectionCard title="Pricing Strategy" icon={<DollarSign size={16} />} color="#06B6D4">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
          {Object.entries(pricing).map(([k, v]) => (
            <div key={k} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{k.replace(/_/g, ' ')}</div>
              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4 }}>{typeof v === 'string' ? v : Array.isArray(v) ? v.join(', ') : JSON.stringify(v)}</div>
            </div>
          ))}
        </div>
      </SectionCard>
    )}

    {/* Vulnerabilities */}
    {vulns.length > 0 && (
      <SectionCard title={`Vulnerabilities (${vulns.length})`} icon={<AlertTriangle size={16} />} color="#EF4444">
        {vulns.map((v: any, i: number) => {
          const sev = (v.severity || 'medium').toLowerCase()
          const sColor = sev === 'high' ? '#DC2626' : sev === 'medium' ? '#F59E0B' : '#10B981'
          return (
            <div key={i} style={{ padding: '12px 14px', background: 'var(--bg-glass)', borderRadius: 6, marginBottom: 8, borderLeft: `3px solid ${sColor}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: 13, fontWeight: 700 }}>{v.gap || v.vulnerability || v.weakness}</div>
                <Badge text={sev.toUpperCase()} color={sColor} />
              </div>
              {v.rfp_req && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>RFP: {v.rfp_req}</div>}
              {v.mitigation && <div style={{ fontSize: 12, color: '#3B82F6', marginTop: 4 }}>Mitigation: {v.mitigation}</div>}
            </div>
          )
        })}
      </SectionCard>
    )}

    {/* Deal Strategy */}
    {Object.keys(dealStrategy).length > 0 && (
      <SectionCard title="Deal Strategy" icon={<Crosshair size={16} />} color="#3B82F6">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          {dealStrategy.overall_approach && <MetricCard label="Approach" value={dealStrategy.overall_approach} color="#3B82F6" />}
          {dealStrategy.key_message && (
            <div style={{ gridColumn: 'span 2', padding: '14px 18px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', borderLeft: '3px solid #10B981' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Key Message</div>
              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4 }}>{dealStrategy.key_message}</div>
            </div>
          )}
        </div>
        {dealStrategy.risk_to_win && (
          <div style={{ marginTop: 12, padding: '10px 14px', background: '#FEF2F2', borderRadius: 6, borderLeft: '3px solid #EF4444', fontSize: 12 }}>
            <span style={{ fontWeight: 700, color: '#EF4444' }}>Risk to Win: </span>{dealStrategy.risk_to_win}
          </div>
        )}
      </SectionCard>
    )}
  </>)
}
