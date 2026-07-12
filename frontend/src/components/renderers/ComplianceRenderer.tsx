 
import { Shield, AlertTriangle, Scale, FileText } from 'lucide-react'
import { MetricCard, SectionCard, Badge } from './shared'

export function ComplianceRenderer({ data }: { data: any }) {
  // Real path: data.risk_register.{contractual_risks, sla_risks, showstoppers, overall_risk_rating, penalty_exposure, data_protection, negotiation_summary}
  const rr = data?.risk_register || data || {}
  const rating = rr.overall_risk_rating || data?.overall_rating || '—'
  const contractRisks = rr.contractual_risks || data?.contractual_risks || []
  const slaRisks = rr.sla_risks || data?.sla_risks || []
  const showstoppers = rr.showstoppers || data?.showstoppers || []
  const penalties = Array.isArray(rr.penalty_exposure) ? rr.penalty_exposure : (rr.penalty_exposure ? [rr.penalty_exposure] : [])
  const dataProtection = Array.isArray(rr.data_protection) ? rr.data_protection : (rr.data_protection ? [rr.data_protection] : [])
  const ipRights = rr.ip_data_rights || {}
  const exitTransition = rr.exit_transition || {}
  const negotiation = rr.negotiation_summary || {}
  const insurance = rr.insurance_indemnity || {}
  const rColor = rating.toString().toUpperCase().includes('HIGH') ? '#DC2626' : rating.toString().toUpperCase().includes('MEDIUM') ? '#F59E0B' : rating.toString().toUpperCase() === '—' ? '#6B7280' : '#10B981'

  return (<>
    {/* Risk Overview */}
    <SectionCard title="Risk Overview" icon={<Shield size={16} />} color={rColor}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <MetricCard label="Overall Rating" value={rating} color={rColor} />
        <MetricCard label="Contractual Risks" value={contractRisks.length} color="#EF4444" />
        <MetricCard label="SLA Risks" value={slaRisks.length} color="#F59E0B" />
        <MetricCard label="Showstoppers" value={showstoppers.length} color={showstoppers.length > 0 ? '#DC2626' : '#10B981'} />
      </div>
    </SectionCard>

    {/* Showstoppers */}
    {showstoppers.length > 0 && (
      <SectionCard title={`Showstoppers (${showstoppers.length})`} icon={<AlertTriangle size={16} />} color="#DC2626">
        {showstoppers.map((s: any, i: number) => (
          <div key={i} style={{ padding: '14px 16px', background: 'rgba(220,38,38,0.06)', borderRadius: 'var(--radius-md)', marginBottom: 10, border: '1px solid rgba(220,38,38,0.15)', borderLeft: '4px solid #DC2626' }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#DC2626' }}>{typeof s === 'string' ? s : s.title || s.issue || s.clause}</div>
            {s.impact && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 6 }}><strong>Impact:</strong> {s.impact}</div>}
            {s.recommendation && <div style={{ fontSize: 12, color: '#10B981', marginTop: 4 }}>→ {s.recommendation}</div>}
          </div>
        ))}
      </SectionCard>
    )}

    {/* Contractual Risks */}
    {contractRisks.length > 0 && (
      <SectionCard title={`Contractual Risks (${contractRisks.length})`} icon={<Scale size={16} />} color="#EF4444">
        <table className="data-table">
          <thead><tr><th>Risk / Clause</th><th>Severity</th><th>Mitigation</th></tr></thead>
          <tbody>{contractRisks.map((r: any, i: number) => (
            <tr key={i}>
              <td style={{ fontWeight: 600, maxWidth: 300 }}>{typeof r === 'string' ? r : r.risk || r.clause || r.title || r.description}</td>
              <td><Badge text={(r.severity || r.impact || r.risk_level || 'MEDIUM').toUpperCase()} color={
                (r.severity || '').toLowerCase().includes('high') ? '#DC2626' : (r.severity || '').toLowerCase().includes('medium') ? '#F59E0B' : '#10B981'
              } /></td>
              <td style={{ fontSize: 12, maxWidth: 300 }}>{r.mitigation || r.recommendation || r.action || '—'}</td>
            </tr>
          ))}</tbody>
        </table>
      </SectionCard>
    )}

    {/* SLA Risks */}
    {slaRisks.length > 0 && (
      <SectionCard title={`SLA Risks (${slaRisks.length})`} icon={<AlertTriangle size={16} />} color="#F59E0B">
        <table className="data-table">
          <thead><tr><th>SLA / Metric</th><th>Severity</th><th>Recommendation</th></tr></thead>
          <tbody>{slaRisks.map((r: any, i: number) => (
            <tr key={i}>
              <td style={{ fontWeight: 600 }}>{typeof r === 'string' ? r : r.sla || r.metric || r.title || r.risk}</td>
              <td><Badge text={(r.severity || r.risk_level || 'MEDIUM').toUpperCase()} color={
                (r.severity || '').toLowerCase().includes('high') ? '#DC2626' : '#F59E0B'
              } /></td>
              <td style={{ fontSize: 12 }}>{r.recommendation || r.mitigation || '—'}</td>
            </tr>
          ))}</tbody>
        </table>
      </SectionCard>
    )}

    {/* Penalty Exposure */}
    {penalties.length > 0 && (
      <SectionCard title={`Penalty Exposure (${penalties.length})`} icon={<AlertTriangle size={16} />} color="#DC2626">
        {penalties.map((p: any, i: number) => {
          const expColor = (p.exposure_level || '').toLowerCase() === 'high' ? '#DC2626' : (p.exposure_level || '').toLowerCase() === 'medium' ? '#F59E0B' : '#10B981'
          return (
            <div key={i} style={{ padding: '12px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 10, border: '1px solid var(--border-subtle)', borderLeft: `4px solid ${expColor}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 14, fontWeight: 700 }}>{p.penalty_type || p.type || 'Penalty'}</span>
                <Badge text={(p.exposure_level || 'medium').toUpperCase()} color={expColor} />
              </div>
              {p.rfp_section && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>RFP: {p.rfp_section}</div>}
              {p.description && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{p.description}</div>}
              {p.cap_analysis && <div style={{ fontSize: 12, color: '#3B82F6', fontStyle: 'italic' }}>Cap: {p.cap_analysis}</div>}
            </div>
          )
        })}
      </SectionCard>
    )}

    {/* Data Protection */}
    {dataProtection.length > 0 && (
      <SectionCard title={`Data Protection (${dataProtection.length} jurisdictions)`} icon={<Shield size={16} />} color="#06B6D4">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
          {dataProtection.map((dp: any, i: number) => {
            const statusColor = (dp.compliance_status || '').toLowerCase() === 'compliant' ? '#10B981' : (dp.compliance_status || '').toLowerCase() === 'gap' ? '#DC2626' : '#F59E0B'
            return (
              <div key={i} style={{ padding: '12px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 700 }}>{dp.jurisdiction || dp.region || 'Global'}</span>
                  <Badge text={(dp.compliance_status || 'partial').toUpperCase()} color={statusColor} />
                </div>
                <div style={{ fontSize: 12, color: '#3B82F6', marginBottom: 4 }}>{dp.regulation || 'N/A'}</div>
                {dp.action_needed && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>→ {dp.action_needed}</div>}
              </div>
            )
          })}
        </div>
      </SectionCard>
    )}

    {/* IP & Data Rights */}
    {ipRights && Object.keys(ipRights).length > 0 && (
      <SectionCard title="IP & Data Rights" icon={<FileText size={16} />} color="#8B5CF6">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
          {Object.entries(ipRights).filter(([k]) => k !== 'concerns').map(([k, v]) => (
            <div key={k} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{k.replace(/_/g, ' ')}</div>
              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4 }}>{String(v)}</div>
            </div>
          ))}
        </div>
        {Array.isArray(ipRights.concerns) && ipRights.concerns.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 11, color: '#EF4444', fontWeight: 700, textTransform: 'uppercase', marginBottom: 6 }}>Concerns</div>
            {ipRights.concerns.map((c: string, i: number) => (
              <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '2px 0' }}>⚠ {c}</div>
            ))}
          </div>
        )}
      </SectionCard>
    )}

    {/* Exit & Transition */}
    {exitTransition && Object.keys(exitTransition).length > 0 && (
      <SectionCard title="Exit & Transition Obligations" icon={<FileText size={16} />} color="#F97316">
        {exitTransition.transition_assistance_period && (
          <div style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', marginBottom: 10 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Transition Assistance Period</div>
            <div style={{ fontSize: 15, fontWeight: 700, marginTop: 4 }}>{exitTransition.transition_assistance_period}</div>
          </div>
        )}
        {Array.isArray(exitTransition.exit_obligations) && exitTransition.exit_obligations.length > 0 && (
          <ul style={{ paddingLeft: 20, fontSize: 13, color: 'var(--text-secondary)' }}>
            {exitTransition.exit_obligations.map((o: string, i: number) => <li key={i} style={{ marginBottom: 4 }}>{o}</li>)}
          </ul>
        )}
        {Array.isArray(exitTransition.risks) && exitTransition.risks.length > 0 && (
          <div style={{ marginTop: 8 }}>
            {exitTransition.risks.map((r: string, i: number) => (
              <div key={i} style={{ fontSize: 12, color: '#EF4444', padding: '2px 0' }}>⚠ {r}</div>
            ))}
          </div>
        )}
      </SectionCard>
    )}

    {/* Insurance & Indemnity */}
    {insurance && Object.keys(insurance).length > 0 && (
      <SectionCard title="Insurance & Indemnity" icon={<Shield size={16} />} color="#6366F1">
        <div style={{ display: 'grid', gap: 10 }}>
          {insurance.insurance_requirements && Array.isArray(insurance.insurance_requirements) && (
            <div style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>Insurance Requirements</div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: 'var(--text-secondary)' }}>
                {insurance.insurance_requirements.map((r: string, i: number) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}
          {insurance.indemnity_scope && (
            <div style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Indemnity Scope</div>
              <div style={{ fontSize: 13, marginTop: 4 }}>{insurance.indemnity_scope}</div>
            </div>
          )}
          {insurance.unlimited_liability_clauses && Array.isArray(insurance.unlimited_liability_clauses) && insurance.unlimited_liability_clauses.length > 0 && (
            <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,0.06)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(239,68,68,0.15)' }}>
              <div style={{ fontSize: 11, color: '#EF4444', fontWeight: 700, textTransform: 'uppercase', marginBottom: 6 }}>Unlimited Liability Clauses</div>
              {insurance.unlimited_liability_clauses.map((c: string, i: number) => (
                <div key={i} style={{ fontSize: 12, color: '#EF4444' }}>🛑 {c}</div>
              ))}
            </div>
          )}
          {insurance.recommendation && (
            <div style={{ fontSize: 13, color: '#10B981', fontStyle: 'italic', padding: '6px 0' }}>→ {insurance.recommendation}</div>
          )}
        </div>
      </SectionCard>
    )}

    {/* Negotiation Summary */}
    {negotiation && typeof negotiation === 'object' && Object.keys(negotiation).length > 0 && (
      <SectionCard title="Negotiation Summary" icon={<FileText size={16} />} color="#8B5CF6">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
          {Object.entries(negotiation).map(([k, v]) => (
            <div key={k} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{k.replace(/_/g, ' ')}</div>
              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4 }}>{Array.isArray(v) ? (v as any[]).join(', ') : String(v)}</div>
            </div>
          ))}
        </div>
      </SectionCard>
    )}
  </>)
}
