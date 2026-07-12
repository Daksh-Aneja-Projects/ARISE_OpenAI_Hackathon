 
import { Cpu, Link2, Server, AlertTriangle, Users, Zap, BarChart3 } from 'lucide-react'
import { MetricCard, SectionCard, Badge } from './shared'

export function AISolutioningRenderer({ data }: { data: any }) {
  // Combined: architecture + automation in one view
  // Architecture paths
  const sd = data?.solution_design || data || {}
  const platforms = sd.platform_architectures || data?.platform_architectures || []
  const integration = sd.integration_architecture || data?.integration_architecture || {}
  const envStrategy = sd.environment_strategy || data?.environment_strategy || {}
  const opModel = sd.operating_model || data?.operating_model || {}
  const risks = sd.technical_risks || data?.technical_risks || []
  const complexity = sd.architecture_complexity || data?.architecture_complexity || '—'
  const dataFlows = integration.data_flows || []
  const middleware = integration.middleware || []

  // Automation paths
  const crossPlatform = data?.cross_platform || []
  const prioTable = data?.prioritisation_table || []
  const breakdown = data?.priority_breakdown || {}
  const total = data?.total_opportunities || prioTable.length

  return (<>
    {/* Architecture + Automation Overview */}
    <SectionCard title="Solution & Automation Overview" icon={<Cpu size={16} />} color="#0EA5E9">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <MetricCard label="Platforms" value={platforms.length || '—'} color="#F59E0B" />
        <MetricCard label="Complexity" value={complexity} color={complexity === 'enterprise' ? '#EF4444' : '#F59E0B'} />
        <MetricCard label="AI Opportunities" value={total} color="#0EA5E9" />
        <MetricCard label="Tech Risks" value={risks.length} color={risks.length > 3 ? '#EF4444' : '#F59E0B'} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 12 }}>
        <MetricCard label="Critical" value={breakdown.critical || 0} color="#DC2626" />
        <MetricCard label="High" value={breakdown.high || 0} color="#F59E0B" />
        <MetricCard label="Data Flows" value={dataFlows.length} color="#3B82F6" />
        <MetricCard label="Middleware" value={middleware.length ? middleware.join(', ') : '—'} color="#8B5CF6" />
      </div>
    </SectionCard>

    {/* Platform Architectures */}
    {platforms.length > 0 && platforms.map((p: any, i: number) => (
      <SectionCard key={i} title={`${p.platform || 'Platform'}`} icon={<Server size={16} />} color={['#3B82F6','#8B5CF6','#10B981','#F59E0B'][i % 4]}>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12, lineHeight: 1.6 }}>{p.technical_approach}</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>Modules in Scope</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {(p.modules_in_scope || []).map((m: any, mi: number) => <Badge key={mi} text={m} color="#3B82F6" />)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>Environments</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {(p.environments || []).map((e: any, ei: number) => <Badge key={ei} text={e} color="#8B5CF6" />)}
            </div>
          </div>
        </div>
        {p.key_considerations && p.key_considerations.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>Key Considerations</div>
            {p.key_considerations.map((c: any, ci: number) => (
              <div key={ci} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '3px 0', display: 'flex', gap: 6 }}>
                <span style={{ color: '#F59E0B' }}>▸</span> {c}
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    ))}

    {/* Target Operating Model */}
    {Object.keys(opModel).length > 0 && (
      <SectionCard title="Target Operating Model" icon={<Users size={16} />} color="#10B981">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
          {Object.entries(opModel).map(([k, v]) => (
            <div key={k} style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{k.replace(/_/g, ' ')}</div>
              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4 }}>{String(v)}</div>
            </div>
          ))}
        </div>
      </SectionCard>
    )}

    {/* Integration Architecture */}
    {(dataFlows.length > 0 || middleware.length > 0) && (
      <SectionCard title="Integration Architecture" icon={<Link2 size={16} />} color="#06B6D4">
        {dataFlows.length > 0 && (
          <table className="data-table">
            <thead><tr><th>Source</th><th>Target</th><th>Pattern</th><th>Frequency</th></tr></thead>
            <tbody>{dataFlows.map((f: any, i: number) => (
              <tr key={i}>
                <td style={{ fontWeight: 600 }}>{f.source}</td>
                <td style={{ fontWeight: 600 }}>{f.target}</td>
                <td><Badge text={f.pattern || '—'} color="#8B5CF6" /></td>
                <td style={{ fontSize: 12 }}>{f.frequency || '—'}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
        {integration.monitoring_approach && (
          <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-secondary)', padding: '8px 12px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)' }}>
            <strong>Monitoring:</strong> {integration.monitoring_approach}
          </div>
        )}
      </SectionCard>
    )}

    {/* Environment Strategy */}
    {Object.keys(envStrategy).length > 0 && (
      <SectionCard title="Environment Strategy" icon={<Server size={16} />} color="#8B5CF6">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
          <MetricCard label="Total Environments" value={envStrategy.total_environments || '—'} color="#8B5CF6" />
          <MetricCard label="Promotion Path" value={envStrategy.promotion_path || '—'} color="#3B82F6" />
        </div>
      </SectionCard>
    )}

    {/* Automation Prioritisation Table */}
    {prioTable.length > 0 && (
      <SectionCard title={`AI & Automation Roadmap (${total} opportunities)`} icon={<Zap size={16} />} color="#0EA5E9">
        <table className="data-table">
          <thead><tr><th>ID</th><th>Opportunity</th><th>Platform</th><th>Priority</th><th>Effort</th><th>Benefit</th></tr></thead>
          <tbody>{prioTable.map((opp: any, i: number) => {
            const pColor = (opp.priority || '').toLowerCase() === 'critical' ? '#DC2626' : (opp.priority || '').toLowerCase() === 'high' ? '#F59E0B' : '#10B981'
            return (
              <tr key={i}>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700 }}>{opp.id || `A-${i+1}`}</td>
                <td style={{ fontWeight: 600 }}>{opp.title || opp.opportunity || opp.name}</td>
                <td style={{ fontSize: 12 }}>{opp.platform || '—'}</td>
                <td><Badge text={(opp.priority || 'MEDIUM').toUpperCase()} color={pColor} /></td>
                <td style={{ fontSize: 12 }}>{opp.effort || '—'}</td>
                <td style={{ fontSize: 12 }}>{opp.benefit || '—'}</td>
              </tr>
            )
          })}</tbody>
        </table>
      </SectionCard>
    )}

    {/* Cross Platform */}
    {crossPlatform.length > 0 && (
      <SectionCard title={`Cross-Platform Initiatives (${crossPlatform.length})`} icon={<BarChart3 size={16} />} color="#8B5CF6">
        {crossPlatform.map((cp: any, i: number) => (
          <div key={i} style={{ padding: '12px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 8, border: '1px solid var(--border-subtle)', borderLeft: '3px solid #8B5CF6' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, fontWeight: 700 }}>{typeof cp === 'string' ? cp : cp.title || cp.name}</span>
              {cp.priority && <Badge text={cp.priority} color={cp.priority === 'CRITICAL' ? '#DC2626' : '#F59E0B'} />}
            </div>
            {cp.description && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{cp.description}</div>}
            {cp.platforms && <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>{(Array.isArray(cp.platforms) ? cp.platforms : [cp.platforms]).map((p: any, pi: number) => <Badge key={pi} text={p} color="#0EA5E9" />)}</div>}
          </div>
        ))}
      </SectionCard>
    )}

    {/* Technical Risks */}
    {risks.length > 0 && (
      <SectionCard title={`Technical Risks (${risks.length})`} icon={<AlertTriangle size={16} />} color="#EF4444">
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
