 
import { BarChart3, AlertTriangle, Users, Zap, TrendingUp, Activity, Database, PieChart } from 'lucide-react'
import { MetricCard, SectionCard, Badge } from './shared'

export function DataAnalystRenderer({ data }: { data: any }) {
  // Real paths from DataAnalystAgent.act():
  // data.data_analysis.{application_analysis, volume_summary, staffing_indicators, automation_opportunities, risk_indicators, sla_performance_baseline}
  // data.data_structure.{data_type, applications_found, total_rows_estimated, date_range, data_quality}
  const analysis = data?.data_analysis || {}
  const structure = data?.data_structure || {}
  const apps = analysis.application_analysis || []
  const vol = analysis.volume_summary || {}
  const staff = analysis.staffing_indicators || {}
  const autos = analysis.automation_opportunities || []
  const risks = analysis.risk_indicators || []
  const sla = analysis.sla_performance_baseline || {}

  // RFP narrative fallback data (when no structured data uploaded)
  const volumesFound = analysis.volumes_found || []
  const appsRef = analysis.applications_referenced || []
  const currentState = analysis.current_state_indicators || []

  const dataType = (structure.data_type || 'unknown').replace(/_/g, ' ')
  const totalTickets = vol.total_tickets || 0
  const monthlyAvg = vol.monthly_average || 0
  const trend = vol.trend || 'unknown'
  const fte = staff.estimated_fte_needed || 0
  const quality = structure.data_quality || '—'

  const trendColor = trend === 'increasing' ? '#EF4444' : trend === 'decreasing' ? '#10B981' : '#F59E0B'

  // If we have no real analysis data, show RFP narrative insights
  const hasRealData = apps.length > 0 || totalTickets > 0 || volumesFound.length > 0

  if (!hasRealData) {
    return (
      <SectionCard title="Data Analysis Summary" icon={<Database size={16} />} color="#7C3AED">
        <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>
          <Database size={32} style={{ marginBottom: 12, opacity: 0.5 }} />
          <div style={{ fontWeight: 600, marginBottom: 8, color: 'var(--text-primary)' }}>No Structured Data Uploaded</div>
          <div style={{ maxWidth: 500, margin: '0 auto', lineHeight: 1.7 }}>
            Upload ticket dumps (CSV/Excel), volume reports, or SLA dashboards alongside the RFP to enable deep operational analysis. The Data Analyst will extract application-wise volumes, priority distributions, staffing indicators, and automation opportunities.
          </div>
        </div>
      </SectionCard>
    )
  }

  return (<>
    {/* Executive Overview Metrics */}
    <SectionCard title="Operational Intelligence Overview" icon={<BarChart3 size={16} />} color="#7C3AED">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <MetricCard label="Data Source" value={dataType} color="#7C3AED" />
        <MetricCard label="Total Tickets" value={totalTickets.toLocaleString()} color="#3B82F6" />
        <MetricCard label="Monthly Avg" value={monthlyAvg.toLocaleString()} color="#10B981" />
        <MetricCard label="Trend" value={trend} color={trendColor} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 12 }}>
        <MetricCard label="Applications" value={apps.length || appsRef.length} color="#8B5CF6" />
        <MetricCard label="Est. FTEs" value={fte} color="#EC4899" />
        <MetricCard label="Automation Opps" value={autos.length} color="#06B6D4" />
        <MetricCard label="Data Quality" value={quality} color={quality === 'high' ? '#10B981' : quality === 'medium' ? '#F59E0B' : '#EF4444'} />
      </div>
    </SectionCard>

    {/* Volume Breakdown */}
    {(vol.by_priority || vol.by_type) && (
      <SectionCard title="Volume Distribution" icon={<PieChart size={16} />} color="#3B82F6">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
          {vol.by_priority && (
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 10 }}>By Priority</div>
              {Object.entries(vol.by_priority).map(([k, v]) => {
                const pColor = k === 'critical' ? '#DC2626' : k === 'high' ? '#F59E0B' : k === 'medium' ? '#3B82F6' : '#10B981'
                const pct = totalTickets > 0 ? Math.round((v as number) / totalTickets * 100) : 0
                return (
                  <div key={k} style={{ marginBottom: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'capitalize' }}>{k}</span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: pColor }}>{(v as number).toLocaleString()} ({pct}%)</span>
                    </div>
                    <div style={{ width: '100%', height: 6, background: 'var(--bg-tertiary)', borderRadius: 3 }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: pColor, borderRadius: 3, transition: 'width 0.8s ease' }} />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
          {vol.by_type && (
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 10 }}>By Type</div>
              {Object.entries(vol.by_type).filter(([, v]) => (v as number) > 0).map(([k, v]) => {
                const pct = totalTickets > 0 ? Math.round((v as number) / totalTickets * 100) : 0
                return (
                  <div key={k} style={{ marginBottom: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'capitalize' }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{ fontSize: 12, fontWeight: 700 }}>{(v as number).toLocaleString()} ({pct}%)</span>
                    </div>
                    <div style={{ width: '100%', height: 6, background: 'var(--bg-tertiary)', borderRadius: 3 }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: '#8B5CF6', borderRadius: 3, transition: 'width 0.8s ease' }} />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
        {vol.peak_month && (
          <div style={{ marginTop: 16, padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: 12 }}>
            <strong>Peak:</strong> {vol.peak_month} with {vol.peak_volume?.toLocaleString()} tickets
          </div>
        )}
      </SectionCard>
    )}

    {/* Application Analysis Table */}
    {apps.length > 0 && (
      <SectionCard title={`Application Analysis (${apps.length})`} icon={<Activity size={16} />} color="#8B5CF6">
        <table className="data-table">
          <thead>
            <tr>
              <th>Application</th>
              <th>Tickets</th>
              <th>% of Total</th>
              <th>Complexity</th>
              <th>Automation</th>
              <th>Key Insights</th>
            </tr>
          </thead>
          <tbody>
            {apps.map((app: any, i: number) => {
              const compColor = app.complexity_rating === 'high' ? '#DC2626' : app.complexity_rating === 'medium' ? '#F59E0B' : '#10B981'
              const autoColor = app.automation_potential === 'high' ? '#10B981' : app.automation_potential === 'medium' ? '#F59E0B' : '#6B7280'
              return (
                <tr key={i}>
                  <td style={{ fontWeight: 700 }}>{app.application}</td>
                  <td style={{ fontWeight: 600 }}>{(app.ticket_count || 0).toLocaleString()}</td>
                  <td>{app.percentage_of_total ? `${app.percentage_of_total}%` : '—'}</td>
                  <td><Badge text={(app.complexity_rating || '—').toUpperCase()} color={compColor} /></td>
                  <td><Badge text={(app.automation_potential || '—').toUpperCase()} color={autoColor} /></td>
                  <td style={{ fontSize: 12, maxWidth: 260, color: 'var(--text-secondary)' }}>
                    {(app.key_insights || []).slice(0, 2).join('; ') || '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </SectionCard>
    )}

    {/* Staffing Indicators */}
    {(fte > 0 || staff.rationale) && (
      <SectionCard title="Staffing Indicators" icon={<Users size={16} />} color="#EC4899">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
          <MetricCard label="Estimated FTEs" value={fte} color="#EC4899" />
          <MetricCard label="Peak Staffing" value={staff.peak_staffing || '—'} color="#F59E0B" />
          <MetricCard label="Shift Model" value={staff.recommended_shift_model || '—'} color="#3B82F6" />
        </div>
        {staff.rationale && (
          <div style={{ padding: '12px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
            <strong style={{ color: 'var(--text-primary)' }}>Rationale:</strong> {staff.rationale}
          </div>
        )}
      </SectionCard>
    )}

    {/* Automation Opportunities */}
    {autos.length > 0 && (
      <SectionCard title={`Automation Opportunities (${autos.length})`} icon={<Zap size={16} />} color="#06B6D4">
        <table className="data-table">
          <thead>
            <tr>
              <th>Area</th>
              <th>Volume Impact</th>
              <th>Reduction</th>
              <th>Complexity</th>
              <th>Justification</th>
            </tr>
          </thead>
          <tbody>
            {autos.map((a: any, i: number) => {
              const cColor = a.complexity === 'low' ? '#10B981' : a.complexity === 'medium' ? '#F59E0B' : '#EF4444'
              return (
                <tr key={i}>
                  <td style={{ fontWeight: 600, maxWidth: 200 }}>{a.area}</td>
                  <td style={{ fontWeight: 700 }}>{(a.ticket_volume_impact || 0).toLocaleString()}</td>
                  <td><Badge text={a.percentage_reduction ? `${a.percentage_reduction}%` : '—'} color="#10B981" /></td>
                  <td><Badge text={(a.complexity || '—').toUpperCase()} color={cColor} /></td>
                  <td style={{ fontSize: 12, maxWidth: 300, color: 'var(--text-secondary)' }}>{a.justification || '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </SectionCard>
    )}

    {/* SLA Performance Baseline */}
    {Object.keys(sla).length > 0 && (
      <SectionCard title="SLA Performance Baseline" icon={<TrendingUp size={16} />} color="#10B981">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 12 }}>
          <MetricCard label="Resolution Adherence" value={sla.current_resolution_adherence || '—'} color="#10B981" />
          <MetricCard label="Avg Response Time" value={sla.response_time_avg || '—'} color="#3B82F6" />
          <MetricCard label="MTTR" value={sla.mttr || '—'} color="#F59E0B" />
        </div>
        {sla.recurring_issues && sla.recurring_issues.length > 0 && (
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Recurring Issues</div>
            {sla.recurring_issues.map((issue: any, i: number) => (
              <div key={i} style={{ padding: '8px 12px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 6, border: '1px solid var(--border-subtle)', borderLeft: '3px solid #F59E0B', fontSize: 13 }}>
                {typeof issue === 'string' ? issue : issue.issue || issue.description}
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    )}

    {/* Risk Indicators */}
    {risks.length > 0 && (
      <SectionCard title={`Risk Indicators (${risks.length})`} icon={<AlertTriangle size={16} />} color="#EF4444">
        {risks.map((r: any, i: number) => {
          const iColor = (r.impact || '').toLowerCase().includes('high') ? '#DC2626' : '#F59E0B'
          return (
            <div key={i} style={{ padding: '12px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 10, border: '1px solid var(--border-subtle)', borderLeft: `4px solid ${iColor}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                <span style={{ fontSize: 14, fontWeight: 700 }}>{typeof r === 'string' ? r : r.risk || r.title}</span>
                {r.impact && <Badge text={r.impact.toUpperCase()} color={iColor} />}
              </div>
              {r.evidence && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}><strong>Evidence:</strong> {r.evidence}</div>}
              {r.recommendation && <div style={{ fontSize: 12, color: '#10B981', marginTop: 4 }}>→ {r.recommendation}</div>}
            </div>
          )
        })}
      </SectionCard>
    )}

    {/* RFP Narrative Volumes (fallback when no structured data) */}
    {volumesFound.length > 0 && (
      <SectionCard title={`Volume Data from RFP (${volumesFound.length} metrics)`} icon={<Database size={16} />} color="#14B8A6">
        <table className="data-table">
          <thead>
            <tr><th>Metric</th><th>Value</th><th>Source</th><th>Confidence</th></tr>
          </thead>
          <tbody>
            {volumesFound.map((v: any, i: number) => (
              <tr key={i}>
                <td style={{ fontWeight: 600 }}>{v.metric}</td>
                <td style={{ fontWeight: 700 }}>{v.value}</td>
                <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{v.source || '—'}</td>
                <td><Badge text={(v.confidence || 'medium').toUpperCase()} color={v.confidence === 'high' ? '#10B981' : v.confidence === 'low' ? '#EF4444' : '#F59E0B'} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </SectionCard>
    )}
  </>)
}
