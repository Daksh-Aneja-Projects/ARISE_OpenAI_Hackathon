 
import { Cpu, Link2, Server, AlertTriangle, Users } from 'lucide-react'
import { MetricCard, SectionCard, Badge } from './shared'

export function SolutionRenderer({ data }: { data: any }) {
  // Real path: data.solution_design.{platform_architectures, integration_architecture, environment_strategy, operating_model, technical_risks}
  // OR flattened at top level after fix
  const sd = data?.solution_design || data || {}
  const platforms = sd.platform_architectures || data?.platform_architectures || []
  const integration = sd.integration_architecture || data?.integration_architecture || {}
  const envStrategy = sd.environment_strategy || data?.environment_strategy || {}
  const opModel = sd.operating_model || data?.operating_model || {}
  const risks = sd.technical_risks || data?.technical_risks || []

  const complexity = sd.architecture_complexity || data?.architecture_complexity || '—'
  const dataFlows = integration.data_flows || []
  const middleware = integration.middleware || []

  return (<>
    {/* Architecture Overview */}
    <SectionCard title="Architecture Overview" icon={<Cpu size={16} />} color="#F59E0B">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <MetricCard label="Platforms" value={platforms.length} color="#F59E0B" />
        <MetricCard label="Complexity" value={complexity} color={complexity === 'enterprise' ? '#EF4444' : complexity === 'complex' ? '#F59E0B' : '#10B981'} />
        <MetricCard label="Data Flows" value={dataFlows.length} color="#3B82F6" />
        <MetricCard label="Risks" value={risks.length} color={risks.length > 3 ? '#EF4444' : '#F59E0B'} />
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

    {/* Integration Architecture */}
    {(dataFlows.length > 0 || middleware.length > 0) && (
      <SectionCard title="Integration Architecture" icon={<Link2 size={16} />} color="#06B6D4">
        {middleware.length > 0 && (
          <div style={{ marginBottom: 12, display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Middleware:</span>
            {middleware.map((m: any, i: number) => <Badge key={i} text={m} color="#06B6D4" />)}
          </div>
        )}
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
        {envStrategy.data_masking && (
          <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-secondary)', padding: '8px 12px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)' }}>
            <strong>Data Masking:</strong> {envStrategy.data_masking}
          </div>
        )}
      </SectionCard>
    )}

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
