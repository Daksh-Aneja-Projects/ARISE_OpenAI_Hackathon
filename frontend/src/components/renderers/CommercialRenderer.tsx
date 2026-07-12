 
import { DollarSign, Users, AlertTriangle, BarChart3, TrendingDown, Zap, ArrowDownRight } from 'lucide-react'
import { MetricCard, SectionCard, Badge } from './shared'

export function CommercialRenderer({ data }: { data: any }) {
  // Real paths: data.{resource_plan, resource_loading, pl_model, scenarios, margin_guardrail, contract_params, cost_breakdown_detail, automation_yoy, automation_opportunity_breakdown, efficiency_targets, commercial_risks}
  const plan = data?.resource_plan || data?.resources || []
  const pl = data?.pl_model || {}
  const scenarios = data?.scenarios || {}
  const guardrail = data?.margin_guardrail || {}
  const risks = data?.commercial_risks || []
  const costDetail = data?.cost_breakdown_detail || {}
  const automationYoy = data?.automation_yoy || []
  const automationBreakdown = data?.automation_opportunity_breakdown || []
  const automationSavingsAnnual = data?.automation_savings_annual || 0
  const params = data?.contract_params || {}

  const fmtCurrency = (v: any) => {
    if (!v && v !== 0) return '—'
    const n = typeof v === 'string' ? parseFloat(v) : v
    if (isNaN(n)) return String(v)
    if (n === 0) return '$0'
    return n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(0)}K` : `$${n.toFixed(0)}`
  }

  return (<>
    {/* P&L Summary */}
    {Object.keys(pl).length > 0 && (
      <SectionCard title="P&L Model" icon={<DollarSign size={16} />} color="#06B6D4">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          <MetricCard label="Total Revenue (TCV)" value={fmtCurrency(pl.revenue?.total_contract_value || pl.revenue)} color="#10B981" />
          <MetricCard label="Total Cost" value={fmtCurrency(pl.costs?.total_cogs || pl.costs)} color="#EF4444" />
          <MetricCard label="Gross Margin" value={pl.profitability?.margin_percent ? `${pl.profitability.margin_percent}%` : '—'} color={parseFloat(pl.profitability?.margin_percent) >= 20 ? '#10B981' : '#F59E0B'} />
          <MetricCard label="Monthly Run Rate" value={fmtCurrency(pl.revenue?.monthly_price || pl.per_month?.price_to_client || pl.per_month)} color="#3B82F6" />
        </div>
      </SectionCard>
    )}

    {/* Cost Breakdown Detail */}
    {(costDetail.transition_cost > 0 || costDetail.change_management_cost > 0 || costDetail.tools_monthly > 0 || costDetail.travel_annual > 0) && (
      <SectionCard title="Cost Breakdown" icon={<BarChart3 size={16} />} color="#8B5CF6">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
          <div style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Transition Cost</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#F59E0B', marginTop: 4 }}>{fmtCurrency(costDetail.transition_cost)}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>Team x {params.transition_months || '?'}mo x 50% ramp</div>
          </div>
          <div style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Change Management</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#A855F7', marginTop: 4 }}>{fmtCurrency(costDetail.change_management_cost)}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>Training + Stakeholder + Comms</div>
          </div>
          <div style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Tools & Infra (Monthly)</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#3B82F6', marginTop: 4 }}>{fmtCurrency(costDetail.tools_monthly)}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>Per month across all platforms</div>
          </div>
          <div style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Travel (Annual)</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#06B6D4', marginTop: 4 }}>{fmtCurrency(costDetail.travel_annual)}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>Client-site visits & workshops</div>
          </div>
        </div>
      </SectionCard>
    )}

    {/* Margin Guardrail */}
    {guardrail.status && (
      <div style={{ padding: '12px 16px', background: guardrail.status === 'PASS' ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)', borderRadius: 'var(--radius-md)', border: `1px solid ${guardrail.status === 'PASS' ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`, marginBottom: 20, display: 'flex', gap: 12, alignItems: 'center' }}>
        <Badge text={guardrail.status} color={guardrail.status === 'PASS' ? '#10B981' : '#EF4444'} />
        <span style={{ fontSize: 13, fontWeight: 600 }}>{guardrail.message || `Margin ${guardrail.level}`}</span>
        {guardrail.approver_required && <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>Approver: {guardrail.approver_required}</span>}
      </div>
    )}

    {/* Resource Plan */}
    {plan.length > 0 && (
      <SectionCard title={`Resource Plan (${plan.length} roles)`} icon={<Users size={16} />} color="#8B5CF6">
        <table className="data-table">
          <thead><tr><th>Role</th><th>FTE</th><th>Location</th><th>Monthly Cost</th><th>Annual Cost</th></tr></thead>
          <tbody>{plan.map((r: any, i: number) => (
            <tr key={i}>
              <td style={{ fontWeight: 600 }}>{r.role || r.title}</td>
              <td style={{ fontWeight: 700 }}>{r.fte || r.count || 1}</td>
              <td><Badge text={r.location || '—'} color={r.location === 'onshore' ? '#3B82F6' : r.location === 'offshore' ? '#10B981' : '#F59E0B'} /></td>
              <td style={{ fontSize: 12 }}>{fmtCurrency(r.monthly_cost || r.cost_per_month)}</td>
              <td style={{ fontSize: 12 }}>{fmtCurrency(r.annual_cost || (r.monthly_cost ? r.monthly_cost * 12 : null))}</td>
            </tr>
          ))}</tbody>
        </table>
      </SectionCard>
    )}

    {/* Automation YOY Optimization */}
    {automationYoy.length > 0 && (
      <SectionCard title="YOY Cost Optimization (Automation)" icon={<TrendingDown size={16} />} color="#10B981">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, padding: '12px 16px', background: 'rgba(16,185,129,0.06)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(16,185,129,0.15)' }}>
          <ArrowDownRight size={20} color="#10B981" />
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#10B981' }}>{fmtCurrency(automationSavingsAnnual)} <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--text-muted)' }}>annual savings potential</span></div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>From {automationBreakdown.length} automation opportunities across the engagement</div>
          </div>
        </div>
        <table className="data-table">
          <thead><tr><th>Year</th><th>Realization</th><th>Annual Savings</th><th>Cumulative</th></tr></thead>
          <tbody>{automationYoy.map((y: any, i: number) => (
            <tr key={i}>
              <td style={{ fontWeight: 700 }}>Y{y.year}</td>
              <td><Badge text={`${y.realization_pct}%`} color={y.realization_pct >= 100 ? '#10B981' : y.realization_pct >= 50 ? '#3B82F6' : '#F59E0B'} /></td>
              <td style={{ fontWeight: 600, color: '#10B981' }}>{fmtCurrency(y.automation_savings)}</td>
              <td style={{ fontSize: 12 }}>{fmtCurrency(y.cumulative_savings)}</td>
            </tr>
          ))}</tbody>
        </table>
      </SectionCard>
    )}

    {/* Per-Opportunity Automation Breakdown */}
    {automationBreakdown.length > 0 && (
      <SectionCard title={`Automation Savings Breakdown (${automationBreakdown.length})`} icon={<Zap size={16} />} color="#F59E0B">
        <table className="data-table">
          <thead><tr><th>Automation</th><th>Platform</th><th>Priority</th><th>FTE Saved</th><th>Annual Saving</th></tr></thead>
          <tbody>{automationBreakdown.map((opp: any, i: number) => (
            <tr key={i}>
              <td>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{opp.title}</div>
                {opp.benefit && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{opp.benefit}</div>}
              </td>
              <td style={{ fontSize: 12 }}>{opp.platform}</td>
              <td><Badge text={opp.priority} color={opp.priority === 'CRITICAL' ? '#EF4444' : opp.priority === 'HIGH' ? '#F59E0B' : '#3B82F6'} /></td>
              <td style={{ fontWeight: 700, textAlign: 'center' }}>{opp.estimated_fte_reduction}</td>
              <td style={{ fontWeight: 700, color: '#10B981' }}>{fmtCurrency(opp.annual_saving_usd)}</td>
            </tr>
          ))}</tbody>
        </table>
      </SectionCard>
    )}

    {/* Scenarios */}
    {scenarios.comparison && (
      <SectionCard title="Pricing Scenarios" icon={<BarChart3 size={16} />} color="#F59E0B">
        <table className="data-table">
          <thead><tr><th>Scenario</th><th>TCV</th><th>Monthly</th><th>Margin</th></tr></thead>
          <tbody>{(Array.isArray(scenarios.comparison) ? scenarios.comparison : Object.entries(scenarios).filter(([k]) => k !== 'comparison').map(([k, v]: any) => ({ scenario: k, ...v }))).map((s: any, i: number) => (
            <tr key={i}>
              <td style={{ fontWeight: 600, textTransform: 'capitalize' }}>{s.scenario || s.name || s.label}</td>
              <td style={{ fontWeight: 700 }}>{fmtCurrency(s.tcv || s.total)}</td>
              <td>{fmtCurrency(s.monthly || s.per_month)}</td>
              <td><Badge text={s.margin ? `${s.margin}%` : '—'} color={parseFloat(s.margin) >= 20 ? '#10B981' : '#F59E0B'} /></td>
            </tr>
          ))}</tbody>
        </table>
      </SectionCard>
    )}

    {/* Commercial Risks */}
    {risks.length > 0 && (
      <SectionCard title={`Commercial Risks (${risks.length})`} icon={<AlertTriangle size={16} />} color="#EF4444">
        {risks.map((r: any, i: number) => (
          <div key={i} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 8, border: '1px solid var(--border-subtle)', borderLeft: '3px solid #EF4444' }}>
            <div style={{ fontSize: 13, fontWeight: 600 }}>{typeof r === 'string' ? r : r.risk || r.title}</div>
            {r.mitigation && <div style={{ fontSize: 12, color: '#10B981', marginTop: 4 }}>→ {r.mitigation}</div>}
          </div>
        ))}
      </SectionCard>
    )}
  </>)
}
