import { Inbox, BarChart3, FileText, Link2, Shield, Users, AlertTriangle, DollarSign, Zap } from 'lucide-react'
import { MetricCard, SectionCard, Badge, InfoRow } from './shared'

export function IntakeRenderer({ data }: { data: Record<string, unknown> }) {
  const ef = (data?.extracted_fields || {}) as Record<string, any>
  const g = (k: string) => { const v = ef[k]; return typeof v === 'object' && v?.value !== undefined ? v.value : v || '—' }
  const platforms = (data?.platform_details as Record<string, any>[]) || []
  const integrations = (data?.integration_inventory as Record<string, string>[]) || []
  const slas = (data?.kpi_sla_table as Record<string, string>[]) || []
  const scopes = (data?.scope_sections as Record<string, any>[]) || []
  const index = data?.rfp_index as { section_count: number; overview: string } | undefined
  const ambiguities = (data?.ambiguities as any[]) || []
  const disqualifiers = (data?.disqualifiers as string[]) || []

  const fmtArr = (v: unknown) => Array.isArray(v) ? v.join(', ') : String(v ?? '—')

  // New enriched fields
  const incumbentSignals = g('incumbent_signals')
  const automationRefs = g('automation_references')
  const securityReqs = g('security_requirements')
  const budgetIndicators = g('budget_indicators')
  const stakeholderGroups = g('stakeholder_groups')
  const evalCriteria = g('evaluation_criteria')

  return (<>
    <SectionCard title="Client & Engagement Overview" icon={<Inbox size={16} />} color="#3B82F6">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <MetricCard label="Client" value={g('client_name')} color="#3B82F6" />
        <MetricCard label="Industry" value={g('client_industry')} color="#8B5CF6" />
        <MetricCard label="Contract Type" value={g('contract_type')} color="#10B981" />
        <MetricCard label="Duration" value={g('contract_duration')} color="#F59E0B" />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 12 }}>
        <MetricCard label="Products" value={fmtArr(g('products'))} color="#EC4899" />
        <MetricCard label="Employee Population" value={g('employee_population')} color="#06B6D4" />
        <MetricCard label="Geographies" value={fmtArr(g('geographies'))} color="#14B8A6" />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 12 }}>
        <MetricCard label="Deadline" value={g('submission_deadline')} color="#EF4444" />
        <MetricCard label="Start Date" value={g('contract_start_date')} color="#0EA5E9" />
        <MetricCard label="Est. Contract Value" value={g('estimated_contract_value')} color="#10B981" />
      </div>
    </SectionCard>

    {/* Evaluation Criteria */}
    {evalCriteria && typeof evalCriteria === 'object' && (
      <SectionCard title="Evaluation Criteria" icon={<BarChart3 size={16} />} color="#F59E0B">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {Object.entries(evalCriteria).filter(([k]) => k !== 'other' || evalCriteria[k]).map(([k, v]: [string, any]) => (
            <MetricCard key={k} label={k.charAt(0).toUpperCase() + k.slice(1)} value={v ? `${v}%` : '—'} color="#F59E0B" />
          ))}
        </div>
      </SectionCard>
    )}

    {/* Platform Details — Enhanced */}
    {platforms.length > 0 && (
      <SectionCard title={`Platform Details (${platforms.length})`} icon={<BarChart3 size={16} />} color="#8B5CF6">
        <table className="data-table"><thead><tr>
          <th>Platform</th><th>Hosting</th><th>Users</th><th>Countries</th><th>Environments</th><th>Criticality</th>
        </tr></thead>
          <tbody>{platforms.map((p: Record<string, any>, i: number) => (
            <tr key={i}>
              <td style={{ fontWeight: 600 }}>
                {p.product_name || p.name || p.platform || '—'}
                {p.vendor && <span style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block' }}>{p.vendor} {p.version || ''}</span>}
              </td>
              <td><Badge text={(p.hosting_model || 'N/A').toUpperCase()} color={p.hosting_model === 'SaaS' ? '#10B981' : p.hosting_model === 'cloud' ? '#3B82F6' : '#F59E0B'} /></td>
              <td style={{ fontSize: 12 }}>{p.user_count || '—'}</td>
              <td style={{ fontSize: 12 }}>{p.countries_deployed ? fmtArr(p.countries_deployed) : '—'}</td>
              <td style={{ fontSize: 12 }}>{p.environments || '—'}</td>
              <td><Badge text={(p.criticality || 'standard').toUpperCase()} color={p.criticality === 'business-critical' ? '#DC2626' : p.criticality === 'important' ? '#F59E0B' : '#10B981'} /></td>
            </tr>
          ))}</tbody></table>
      </SectionCard>
    )}

    {/* Integration Inventory */}
    {integrations.length > 0 && (
      <SectionCard title={`Integration Inventory (${integrations.length})`} icon={<Link2 size={16} />} color="#06B6D4">
        <table className="data-table"><thead><tr><th>Source</th><th>Target</th><th>Middleware</th><th>Type</th><th>Frequency</th></tr></thead>
          <tbody>{integrations.map((ig: Record<string, string>, i: number) => (
            <tr key={i}><td style={{ fontWeight: 600 }}>{ig.source || ig.from || '—'}</td>
            <td>{ig.target || ig.to || '—'}</td>
            <td>{ig.middleware || ig.tool || '—'}</td>
            <td><Badge text={(ig.type || 'N/A').toUpperCase()} color="#06B6D4" /></td>
            <td style={{ fontSize: 12 }}>{ig.frequency || '—'}</td></tr>
          ))}</tbody></table>
      </SectionCard>
    )}

    {/* SLA / KPI Table */}
    {slas.length > 0 && (
      <SectionCard title={`SLA / KPI Requirements (${slas.length})`} icon={<Shield size={16} />} color="#10B981">
        <table className="data-table"><thead><tr><th>KPI</th><th>Target</th><th>Measurement</th><th>Penalty</th><th>Section</th></tr></thead>
          <tbody>{slas.map((s: Record<string, string>, i: number) => (
            <tr key={i}><td style={{ fontWeight: 600 }}>{s.kpi_name || '—'}</td>
            <td>{s.target || '—'}</td>
            <td style={{ fontSize: 12 }}>{s.measurement || '—'}</td>
            <td style={{ fontSize: 12 }}>{s.penalty || '—'}</td>
            <td style={{ fontSize: 11 }}>{s.rfp_section || '—'}</td></tr>
          ))}</tbody></table>
      </SectionCard>
    )}

    {/* Strategic Intelligence */}
    <SectionCard title="Strategic Intelligence" icon={<Zap size={16} />} color="#EC4899">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {incumbentSignals && incumbentSignals !== '—' && (
          <InfoRow label="Incumbent Signals" value={fmtArr(incumbentSignals)} color="#EF4444" />
        )}
        {budgetIndicators && budgetIndicators !== '—' && (
          <InfoRow label="Budget Indicators" value={typeof budgetIndicators === 'string' ? budgetIndicators : fmtArr(budgetIndicators)} color="#10B981" />
        )}
        {automationRefs && automationRefs !== '—' && (
          <InfoRow label="Automation References" value={fmtArr(automationRefs)} color="#0EA5E9" />
        )}
        {securityReqs && securityReqs !== '—' && (
          <InfoRow label="Security Requirements" value={fmtArr(securityReqs)} color="#8B5CF6" />
        )}
        {stakeholderGroups && stakeholderGroups !== '—' && (
          <InfoRow label="Stakeholder Groups" value={fmtArr(stakeholderGroups)} color="#F59E0B" />
        )}
      </div>
    </SectionCard>

    {/* Risks & Ambiguities */}
    {(disqualifiers.length > 0 || ambiguities.length > 0) && (
      <SectionCard title="Risks & Ambiguities" icon={<AlertTriangle size={16} />} color="#EF4444">
        {disqualifiers.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#EF4444', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>Potential Disqualifiers</div>
            {disqualifiers.map((d: string, i: number) => (
              <div key={i} style={{ padding: '8px 12px', background: '#FEF2F2', borderRadius: 6, marginBottom: 4, fontSize: 12, color: '#991B1B', borderLeft: '3px solid #EF4444' }}>{typeof d === 'string' ? d : JSON.stringify(d)}</div>
            ))}
          </div>
        )}
        {ambiguities.length > 0 && (
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#F59E0B', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>Ambiguities</div>
            {ambiguities.map((a: any, i: number) => (
              <div key={i} style={{ padding: '8px 12px', background: 'var(--bg-glass)', borderRadius: 6, marginBottom: 4, fontSize: 12, borderLeft: `3px solid ${a?.severity === 'High' ? '#EF4444' : '#F59E0B'}` }}>
                <span style={{ fontWeight: 600 }}>{a?.severity && <Badge text={a.severity} color={a.severity === 'High' ? '#EF4444' : '#F59E0B'} />} </span>
                {typeof a === 'string' ? a : a?.description || JSON.stringify(a)}
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    )}

    {/* Scope Sections */}
    {scopes.length > 0 && (
      <SectionCard title={`RFP Scope Sections (${scopes.length})`} icon={<FileText size={16} />} color="#14B8A6">
        {scopes.map((s: any, i: number) => (
          <div key={i} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 6, marginBottom: 8, border: '1px solid var(--border-subtle)', borderLeft: '3px solid #14B8A6' }}>
            <div style={{ fontSize: 13, fontWeight: 700 }}>{s.section_ref} — {s.title}</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{s.scope_summary}</div>
          </div>
        ))}
      </SectionCard>
    )}

    {index && (
      <SectionCard title={`RFP Section Index (${index.section_count} sections)`} icon={<FileText size={16} />} color="#14B8A6">
        <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', whiteSpace: 'pre-wrap', color: 'var(--text-secondary)', maxHeight: 200, overflow: 'auto' }}>
          {index.overview}
        </div>
      </SectionCard>
    )}
  </>)
}
