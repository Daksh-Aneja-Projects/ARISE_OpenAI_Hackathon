 
import { Zap, BarChart3, Target, Layers, Clock, TrendingDown } from 'lucide-react'
import { MetricCard, SectionCard, Badge } from './shared'

export function AutomationRenderer({ data }: { data: any }) {
  const platformSections = data?.platform_sections || []
  const crossPlatform = data?.cross_platform || []
  const prioTable = data?.prioritisation_table || []
  const breakdown = data?.priority_breakdown || {}
  const total = data?.total_opportunities || prioTable.length
  const totalFteSaved = data?.total_fte_reduction || prioTable.reduce((sum: number, o: any) => sum + (o.fte_saved || o.estimated_fte_reduction || 0), 0)

  const priorityColor = (p: string) => {
    const pl = (p || '').toLowerCase()
    if (pl === 'critical') return '#DC2626'
    if (pl === 'high') return '#F59E0B'
    if (pl === 'medium') return '#3B82F6'
    return '#10B981'
  }

  return (<>
    <SectionCard title="Automation & AI Overview" icon={<Zap size={16} />} color="#0EA5E9">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
        <MetricCard label="Total Opportunities" value={total} color="#0EA5E9" />
        <MetricCard label="Critical" value={breakdown.critical || 0} color="#DC2626" />
        <MetricCard label="High" value={breakdown.high || 0} color="#F59E0B" />
        <MetricCard label="Medium / Lower" value={(breakdown.medium || 0) + (breakdown.lower || 0)} color="#10B981" />
        <MetricCard label="Est. FTE Reduction" value={totalFteSaved ? `${totalFteSaved.toFixed(1)} FTEs` : '—'} color="#8B5CF6" />
      </div>
    </SectionCard>

    {/* Per-Platform Automation Sections */}
    {platformSections.length > 0 && platformSections.map((section: any, si: number) => {
      const opps = section.opportunities || []
      if (opps.length === 0) return null
      return (
        <SectionCard key={si} title={`${section.platform || section.product || 'Platform'} — ${opps.length} Opportunities`} icon={<Layers size={16} />} color="#8B5CF6">
          {opps.map((opp: any, oi: number) => (
            <div key={oi} style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 10, border: '1px solid var(--border-subtle)', borderLeft: `4px solid ${priorityColor(opp.priority)}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700 }}>{opp.id} — {opp.title}</div>
                  {opp.rfp_trigger && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>RFP: {opp.rfp_trigger}</div>}
                </div>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexShrink: 0 }}>
                  <Badge text={(opp.priority || 'MEDIUM').toUpperCase()} color={priorityColor(opp.priority)} />
                  {opp.estimated_fte_reduction > 0 && <Badge text={`${opp.estimated_fte_reduction} FTE`} color="#8B5CF6" />}
                </div>
              </div>
              {/* What / How / Why — the enriched fields */}
              {opp.what && (
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>What: </span>{opp.what}
                </div>
              )}
              {opp.how && (
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>How: </span>{opp.how}
                </div>
              )}
              {opp.business_justification && (
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, color: '#10B981' }}>Business Impact: </span>{opp.business_justification}
                </div>
              )}
              <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
                {opp.effort && <span><Clock size={11} style={{ marginRight: 3, verticalAlign: 'middle' }} />{opp.effort}</span>}
                {opp.benefit && <span><TrendingDown size={11} style={{ marginRight: 3, verticalAlign: 'middle' }} />{opp.benefit}</span>}
                {opp.horizon && <span>Timeline: {opp.horizon}</span>}
              </div>
              {opp.sub_items && opp.sub_items.length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {opp.sub_items.map((s: string, si2: number) => (
                    <span key={si2} style={{ fontSize: 10, padding: '2px 8px', borderRadius: 4, background: 'var(--bg-glass)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>{s}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </SectionCard>
      )
    })}

    {/* Prioritisation Table */}
    {prioTable.length > 0 && (
      <SectionCard title="Prioritised Automation Roadmap" icon={<Target size={16} />} color="#F59E0B">
        <table className="data-table">
          <thead><tr><th>ID</th><th>Opportunity</th><th>Platform</th><th>Priority</th><th>Effort</th><th>FTE Saved</th><th>Impact</th></tr></thead>
          <tbody>{prioTable.map((opp: any, i: number) => (
            <tr key={i}>
              <td style={{ fontSize: 11, fontFamily: 'var(--font-mono)' }}>{opp.id || `#${i + 1}`}</td>
              <td style={{ fontWeight: 600 }}>{opp.opportunity || opp.name || opp.title}</td>
              <td style={{ fontSize: 12 }}>{opp.platform || opp.product || '—'}</td>
              <td><Badge text={(opp.priority || 'MEDIUM').toUpperCase()} color={priorityColor(opp.priority)} /></td>
              <td style={{ fontSize: 12 }}>{opp.effort || opp.complexity || '—'}</td>
              <td style={{ fontSize: 12, fontWeight: 600, color: '#8B5CF6' }}>{opp.fte_saved || opp.estimated_fte_reduction || '—'}</td>
              <td style={{ fontSize: 12 }}>{opp.impact || opp.benefit || '—'}</td>
            </tr>
          ))}</tbody>
        </table>
      </SectionCard>
    )}

    {/* Cross Platform */}
    {crossPlatform.length > 0 && (
      <SectionCard title={`Cross-Platform Synergies (${crossPlatform.length})`} icon={<BarChart3 size={16} />} color="#8B5CF6">
        {crossPlatform.map((cp: any, i: number) => (
          <div key={i} style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 10, border: '1px solid var(--border-subtle)', borderLeft: '4px solid #8B5CF6' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ fontSize: 14, fontWeight: 700 }}>{typeof cp === 'string' ? cp : cp.id ? `${cp.id} — ` : ''}{cp.title || cp.name || cp.initiative}</div>
              {cp.estimated_fte_reduction > 0 && <Badge text={`${cp.estimated_fte_reduction} FTE`} color="#8B5CF6" />}
            </div>
            {cp.description && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 6 }}>{cp.description}</div>}
            {cp.how && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}><span style={{ fontWeight: 600 }}>How: </span>{cp.how}</div>}
            <div style={{ display: 'flex', gap: 8, marginTop: 8, alignItems: 'center' }}>
              {cp.platforms && (Array.isArray(cp.platforms) ? cp.platforms : [cp.platforms]).map((p: any, pi: number) => <Badge key={pi} text={p} color="#0EA5E9" />)}
              {cp.effort && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{cp.effort}</span>}
              {cp.benefit && <span style={{ fontSize: 11, color: '#10B981' }}>{cp.benefit}</span>}
            </div>
          </div>
        ))}
      </SectionCard>
    )}
  </>)
}
