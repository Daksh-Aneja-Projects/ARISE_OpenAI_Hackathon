 
import { Layers, Users, Clock, Package, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import { MetricCard, SectionCard, Badge } from './shared'

export function ScopeRenderer({ data }: { data: any }) {
  const sp = data?.scope_package || data || {}
  const products = sp.products_in_scope || []
  const byPlatform = sp.scope_by_platform || []
  const team = sp.team_model || []
  const phases = sp.transition_phases || []
  const effort = sp.total_effort_days || 0
  const timeline = sp.timeline_months || 0
  const confidence = sp.effort_confidence || '—'
  const transWeeks = sp.transition_weeks || 0
  const contractType = sp.contract_type || '—'
  const contractMonths = sp.contract_months || 0
  const inScope = sp.in_scope || []
  const outScope = sp.out_of_scope || []
  const assumptions = sp.assumptions || []
  const dependencies = sp.dependencies || []
  const crossPlatform = sp.cross_platform_scope || []
  const totalFte = team.reduce((s: number, t: any) => s + (t.count || t.fte || 1), 0)

  return (<>
    {/* Summary Metrics */}
    <SectionCard title="Scope Summary" icon={<Layers size={16} />} color="#8B5CF6">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
        <MetricCard label="Products" value={products.length || '—'} color="#8B5CF6" />
        <MetricCard label="Total Effort" value={`${effort} days`} color="#3B82F6" />
        <MetricCard label="Timeline" value={`${timeline} months`} color="#10B981" />
        <MetricCard label="Contract Type" value={contractType} color="#EC4899" />
        <MetricCard label="Confidence" value={confidence} color="#F59E0B" />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 12 }}>
        <MetricCard label="Total FTEs" value={totalFte} color="#3B82F6" />
        <MetricCard label="Team Roles" value={team.length} color="#EC4899" />
        <MetricCard label="Transition" value={`${transWeeks} weeks`} color="#06B6D4" />
        <MetricCard label="Contract Duration" value={contractMonths ? `${contractMonths} months` : '—'} color="#14B8A6" />
      </div>
      {products.length > 0 && (
        <div style={{ display: 'flex', gap: 6, marginTop: 12, flexWrap: 'wrap' }}>
          {products.map((p: string, i: number) => <Badge key={i} text={p} color="#8B5CF6" />)}
        </div>
      )}
    </SectionCard>

    {/* Scope by Platform — Enhanced */}
    {byPlatform.length > 0 && byPlatform.map((plat: any, pi: number) => {
      const color = ['#3B82F6','#8B5CF6','#10B981','#F59E0B'][pi % 4]
      return (
        <SectionCard key={pi} title={`${plat.platform || plat.product || 'Platform'} — ${plat.platform_effort_days || 0} Days`} icon={<Package size={16} />} color={color}>
          {plat.scope_summary && (
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12, padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 6, borderLeft: `3px solid ${color}` }}>{plat.scope_summary}</div>
          )}
          {plat.work_packages && plat.work_packages.length > 0 && (
            <table className="data-table">
              <thead><tr><th>Work Package</th><th>Effort</th><th>Roles</th><th>Deliverables</th></tr></thead>
              <tbody>{plat.work_packages.map((wp: any, i: number) => (
                <tr key={i}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{wp.name || wp.activity || wp.title}</div>
                    {wp.description && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{wp.description}</div>}
                    {wp.rfp_ref && <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Ref: {wp.rfp_ref}</div>}
                  </td>
                  <td style={{ fontWeight: 600 }}>{wp.effort_days || wp.effort || '—'} days</td>
                  <td style={{ fontSize: 11 }}>{Array.isArray(wp.roles) ? wp.roles.join(', ') : wp.roles || '—'}</td>
                  <td style={{ fontSize: 11 }}>{Array.isArray(wp.deliverables) ? wp.deliverables.join(', ') : '—'}</td>
                </tr>
              ))}</tbody>
            </table>
          )}
          {plat.support_activities && plat.support_activities.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Support Activities</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {plat.support_activities.map((a: string, ai: number) => <Badge key={ai} text={a} color={color} />)}
              </div>
            </div>
          )}
        </SectionCard>
      )
    })}

    {/* Cross-Platform Scope */}
    {crossPlatform.length > 0 && (
      <SectionCard title={`Cross-Platform Scope (${crossPlatform.length})`} icon={<Layers size={16} />} color="#06B6D4">
        <table className="data-table">
          <thead><tr><th>Activity</th><th>Effort</th><th>Roles</th><th>Deliverables</th></tr></thead>
          <tbody>{crossPlatform.map((cp: any, i: number) => (
            <tr key={i}>
              <td>
                <div style={{ fontWeight: 600 }}>{cp.name || cp.title}</div>
                {cp.description && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{cp.description}</div>}
              </td>
              <td style={{ fontWeight: 600 }}>{cp.effort_days || '—'} days</td>
              <td style={{ fontSize: 11 }}>{Array.isArray(cp.roles) ? cp.roles.join(', ') : '—'}</td>
              <td style={{ fontSize: 11 }}>{Array.isArray(cp.deliverables) ? cp.deliverables.join(', ') : '—'}</td>
            </tr>
          ))}</tbody>
        </table>
      </SectionCard>
    )}

    {/* Team Model — Enhanced */}
    {team.length > 0 && (
      <SectionCard title={`Team Model (${totalFte} FTEs across ${team.length} roles)`} icon={<Users size={16} />} color="#10B981">
        <table className="data-table">
          <thead><tr><th>Role</th><th>FTE</th><th>Location</th><th>Platform</th><th>Responsibilities</th></tr></thead>
          <tbody>{team.map((t: any, i: number) => (
            <tr key={i}>
              <td style={{ fontWeight: 600 }}>{t.role || t.title}</td>
              <td style={{ fontWeight: 700, fontSize: 15 }}>{t.fte || t.count || 1}</td>
              <td><Badge text={(t.location || '—').toUpperCase()} color={t.location === 'onshore' ? '#3B82F6' : t.location === 'offshore' ? '#10B981' : '#F59E0B'} /></td>
              <td style={{ fontSize: 12 }}>{t.platform || '—'}</td>
              <td style={{ fontSize: 11, maxWidth: 300, color: 'var(--text-secondary)' }}>{t.key_responsibilities || '—'}</td>
            </tr>
          ))}</tbody>
        </table>
      </SectionCard>
    )}

    {/* In Scope / Out of Scope */}
    {(inScope.length > 0 || outScope.length > 0) && (
      <SectionCard title="Scope Boundaries" icon={<CheckCircle size={16} />} color="#10B981">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#10B981', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>In Scope</div>
            {inScope.map((item: string, i: number) => (
              <div key={i} style={{ padding: '6px 10px', fontSize: 12, borderLeft: '3px solid #10B981', background: 'var(--bg-glass)', borderRadius: 4, marginBottom: 4 }}>{item}</div>
            ))}
          </div>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#EF4444', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>Out of Scope</div>
            {outScope.map((item: string, i: number) => (
              <div key={i} style={{ padding: '6px 10px', fontSize: 12, borderLeft: '3px solid #EF4444', background: 'var(--bg-glass)', borderRadius: 4, marginBottom: 4 }}>{item}</div>
            ))}
          </div>
        </div>
      </SectionCard>
    )}

    {/* Assumptions & Dependencies */}
    {(assumptions.length > 0 || dependencies.length > 0) && (
      <SectionCard title="Assumptions & Dependencies" icon={<AlertTriangle size={16} />} color="#F59E0B">
        {assumptions.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#F59E0B', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>Assumptions</div>
            {assumptions.map((a: any, i: number) => (
              <div key={i} style={{ padding: '8px 12px', background: 'var(--bg-glass)', borderRadius: 6, marginBottom: 4, borderLeft: '3px solid #F59E0B' }}>
                <div style={{ fontSize: 12, fontWeight: 600 }}>{typeof a === 'string' ? a : a.assumption || JSON.stringify(a)}</div>
                {a.impact_if_violated && <div style={{ fontSize: 11, color: '#EF4444', marginTop: 2 }}>Impact: {a.impact_if_violated}</div>}
              </div>
            ))}
          </div>
        )}
        {dependencies.length > 0 && (
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#06B6D4', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>Dependencies</div>
            {dependencies.map((d: any, i: number) => (
              <div key={i} style={{ padding: '8px 12px', background: 'var(--bg-glass)', borderRadius: 6, marginBottom: 4, borderLeft: '3px solid #06B6D4' }}>
                <div style={{ fontSize: 12, fontWeight: 600 }}>{typeof d === 'string' ? d : d.dependency || JSON.stringify(d)}</div>
                {d.timing && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Due: {d.timing}</span>}
                {d.impact_if_delayed && <div style={{ fontSize: 11, color: '#EF4444', marginTop: 2 }}>Impact: {d.impact_if_delayed}</div>}
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    )}

    {/* Transition Phases */}
    {phases.length > 0 && (
      <SectionCard title="Transition Plan" icon={<Clock size={16} />} color="#06B6D4">
        <div style={{ display: 'flex', gap: 12 }}>
          {phases.map((ph: any, i: number) => (
            <div key={i} style={{ flex: 1, padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', borderTop: `3px solid ${['#3B82F6','#8B5CF6','#10B981','#F59E0B'][i % 4]}`, textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Phase {i + 1}</div>
              <div style={{ fontSize: 14, fontWeight: 700, marginTop: 4 }}>{ph.name || ph.phase || `Phase ${i+1}`}</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{ph.duration || ph.weeks ? `${ph.weeks || ph.duration} weeks` : ''}</div>
            </div>
          ))}
        </div>
      </SectionCard>
    )}
  </>)
}
