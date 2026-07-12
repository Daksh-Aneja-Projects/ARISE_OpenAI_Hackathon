 
import { Building2, TrendingUp, ShoppingCart, Shield, Target } from 'lucide-react'
import { MetricCard, SectionCard, Badge } from './shared'

export function ClientIntelRenderer({ data }: { data: any }) {
  const profile = data?.company_profile || {}
  const tech = data?.technology_landscape || {}
  const procurement = data?.procurement_signals || {}

  const relationship = data?.relationship_context || {}
  const winInputs = data?.win_strategy_inputs || {}
  const risks = data?.risk_factors || []

  return (<>
    {/* Company Profile */}
    <SectionCard title="Company Profile" icon={<Building2 size={16} />} color="#3B82F6">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <MetricCard label="Industry" value={profile.industry || '—'} color="#3B82F6" />
        <MetricCard label="Est. Size" value={profile.estimated_size || '—'} color="#8B5CF6" />
        <MetricCard label="Tech Maturity" value={profile.technology_maturity || '—'} color="#10B981" />
        <MetricCard label="Relationship" value={relationship.relationship_status || '—'} color="#F59E0B" />
      </div>
    </SectionCard>

    {/* Technology Landscape */}
    {Object.keys(tech).length > 0 && (
      <SectionCard title="Technology Landscape" icon={<TrendingUp size={16} />} color="#06B6D4">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 12 }}>
          <MetricCard label="Integration Complexity" value={tech.integration_complexity || '—'} color={tech.integration_complexity === 'very-high' ? '#DC2626' : '#06B6D4'} />
          <MetricCard label="Digital Maturity" value={tech.digital_maturity || '—'} color="#8B5CF6" />
          <MetricCard label="Cloud Adoption" value={tech.cloud_adoption || '—'} color="#3B82F6" />
        </div>
        {tech.current_platforms && (
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>Current Platforms</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>{tech.current_platforms.map((p: any, i: number) => <Badge key={i} text={p} color="#06B6D4" />)}</div>
          </div>
        )}
        {tech.pain_points && tech.pain_points.length > 0 && (
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>Pain Points</div>
            {tech.pain_points.map((p: any, i: number) => (
              <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '3px 0' }}>▸ {p}</div>
            ))}
          </div>
        )}
      </SectionCard>
    )}

    {/* Procurement Signals */}
    <SectionCard title="Procurement Behavior" icon={<ShoppingCart size={16} />} color="#F59E0B">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 12 }}>
        <MetricCard label="Buying Style" value={procurement.buying_style || '—'} color="#F59E0B" />
        <MetricCard label="Procurement Maturity" value={(procurement.procurement_maturity || '—').replace(/-/g, ' ')} color="#8B5CF6" />
        <MetricCard label="Risk Appetite" value={procurement.risk_appetite || '—'} color={procurement.risk_appetite === 'conservative' ? '#EF4444' : '#10B981'} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 12 }}>
        <MetricCard label="Decision Orientation" value={(procurement.decision_maker_orientation || '—').replace(/-/g, ' ')} color="#06B6D4" />
        <MetricCard label="Timeline Pressure" value={procurement.timeline_pressure || '—'} color={procurement.timeline_pressure === 'urgent' ? '#EF4444' : '#10B981'} />
        <MetricCard label="Pricing Sensitivity" value={winInputs.pricing_sensitivity || procurement.budget_signals || '—'} color="#F59E0B" />
      </div>
      {procurement.decision_factors && (
        <div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>Decision Factors</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>{procurement.decision_factors.map((f: any, i: number) => <Badge key={i} text={f} color="#F59E0B" />)}</div>
        </div>
      )}
    </SectionCard>

    {/* Win Strategy */}
    {winInputs.client_hot_buttons && winInputs.client_hot_buttons.length > 0 && (
      <SectionCard title="Win Strategy Inputs" icon={<Target size={16} />} color="#10B981">
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>Client Hot Buttons</div>
          {winInputs.client_hot_buttons.map((b: any, i: number) => (
            <div key={i} style={{ padding: '8px 12px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 6, border: '1px solid var(--border-subtle)', borderLeft: '3px solid #10B981', fontSize: 13, fontWeight: 600 }}>{b}</div>
          ))}
        </div>
        {winInputs.differentiators_needed && (
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>Differentiators Needed</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>{winInputs.differentiators_needed.map((d: any, i: number) => <Badge key={i} text={d} color="#8B5CF6" />)}</div>
          </div>
        )}
      </SectionCard>
    )}

    {/* Risks */}
    {risks.length > 0 && (
      <SectionCard title={`Client Risk Factors (${risks.length})`} icon={<Shield size={16} />} color="#EF4444">
        {risks.map((r: any, i: number) => (
          <div key={i} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 8, border: '1px solid var(--border-subtle)', borderLeft: '3px solid #EF4444' }}>
            <div style={{ fontSize: 13, fontWeight: 600 }}>{typeof r === 'string' ? r : r.risk}</div>
            {r.impact && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>Impact: {r.impact}</div>}
            {r.mitigation && <div style={{ fontSize: 12, color: '#10B981', marginTop: 4 }}>→ {r.mitigation}</div>}
          </div>
        ))}
      </SectionCard>
    )}
  </>)
}
