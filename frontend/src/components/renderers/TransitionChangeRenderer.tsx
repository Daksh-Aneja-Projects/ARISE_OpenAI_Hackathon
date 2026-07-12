 
import { ArrowRight, Users, BookOpen, Shield, BarChart3, AlertTriangle, CheckCircle, Target, Clock } from 'lucide-react'
import { MetricCard, SectionCard, Badge } from './shared'

export function TransitionChangeRenderer({ data }: { data: any }) {
  const tp = data?.transition_plan || {}
  const cm = data?.change_management || {}
  const gov = data?.governance_model || {}
  const waves = data?.wave_rollout || []
  const risks = data?.transition_risks || []

  const phases = tp.phases || []
  const kt = tp.knowledge_transfer || {}
  const parallel = tp.parallel_run || {}
  const cutover = tp.cutover_plan || {}
  const stakeholders = cm.stakeholder_groups || []
  const commPlan = cm.communication_plan || []
  const training = cm.training_plan || []
  const successMetrics = cm.success_metrics || []
  const raci = gov.raci_matrix || []
  const milestones = gov.milestone_checkpoints || []
  const escalation = gov.escalation_matrix || []
  const steering = gov.steering_committee || {}

  const phaseColors = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EC4899', '#06B6D4', '#EF4444', '#6366F1']

  return (<>
    {/* Transition Overview */}
    <SectionCard title="Transition Overview" icon={<ArrowRight size={16} />} color="#3B82F6">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
        <MetricCard label="Total Duration" value={`${tp.total_duration_weeks || 0} weeks`} color="#3B82F6" />
        <MetricCard label="Phases" value={phases.length} color="#8B5CF6" />
        <MetricCard label="KT Waves" value={kt.kt_waves || 0} color="#10B981" />
        <MetricCard label="Parallel Run" value={`${parallel.duration_weeks || 0} weeks`} color="#F59E0B" />
      </div>
      {tp.approach && (
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, padding: '12px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
          {tp.approach}
        </div>
      )}
    </SectionCard>

    {/* Phase Timeline — Visual Gantt-style */}
    {phases.length > 0 && (
      <SectionCard title={`Transition Phases (${phases.length})`} icon={<Clock size={16} />} color="#8B5CF6">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0, marginBottom: 16 }}>
          {phases.map((phase: any, i: number) => {
            const color = phaseColors[i % phaseColors.length]
            const totalWeeks = tp.total_duration_weeks || phases[phases.length - 1]?.end_week || 1
            const startPct = ((phase.start_week - 1) / totalWeeks) * 100
            const widthPct = Math.max((phase.duration_weeks / totalWeeks) * 100, 8)
            return (
              <div key={i} style={{ marginBottom: 16 }}>
                {/* Gantt bar */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                  <div style={{ width: 180, fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', flexShrink: 0 }}>
                    <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginRight: 6 }}>P{phase.phase_number || i + 1}</span>
                    {phase.phase_name}
                  </div>
                  <div style={{ flex: 1, position: 'relative', height: 28, background: 'var(--bg-tertiary)', borderRadius: 6 }}>
                    <div style={{
                      position: 'absolute', left: `${startPct}%`, width: `${widthPct}%`,
                      height: '100%', background: `linear-gradient(90deg, ${color}, ${color}cc)`,
                      borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 11, fontWeight: 700, color: '#fff', minWidth: 60,
                    }}>
                      W{phase.start_week}–W{phase.end_week} ({phase.duration_weeks}w)
                    </div>
                  </div>
                </div>
                {/* Phase details */}
                <div style={{ marginLeft: 192, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  {phase.objectives && phase.objectives.length > 0 && (
                    <div style={{ padding: '8px 12px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: 10, color: color, fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>Objectives</div>
                      {phase.objectives.slice(0, 3).map((o: string, j: number) => (
                        <div key={j} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '1px 0' }}>• {o}</div>
                      ))}
                    </div>
                  )}
                  {phase.deliverables && phase.deliverables.length > 0 && (
                    <div style={{ padding: '8px 12px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: 10, color: '#10B981', fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>Deliverables</div>
                      {phase.deliverables.slice(0, 3).map((d: string, j: number) => (
                        <div key={j} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '1px 0' }}>✓ {d}</div>
                      ))}
                    </div>
                  )}
                  {phase.exit_criteria && phase.exit_criteria.length > 0 && (
                    <div style={{ padding: '8px 12px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: 10, color: '#F59E0B', fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>Exit Criteria</div>
                      {phase.exit_criteria.slice(0, 3).map((c: string, j: number) => (
                        <div key={j} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '1px 0' }}>→ {c}</div>
                      ))}
                    </div>
                  )}
                  {phase.risks && phase.risks.length > 0 && (
                    <div style={{ padding: '8px 12px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: 10, color: '#EF4444', fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>Risks</div>
                      {phase.risks.slice(0, 2).map((r: string, j: number) => (
                        <div key={j} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '1px 0' }}>⚠ {r}</div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </SectionCard>
    )}

    {/* Knowledge Transfer & Cutover */}
    {(Object.keys(kt).length > 0 || Object.keys(cutover).length > 0) && (
      <SectionCard title="Knowledge Transfer & Cutover" icon={<BookOpen size={16} />} color="#10B981">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {Object.keys(kt).length > 0 && (
            <div style={{ minWidth: 0, padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#10B981', marginBottom: 10 }}>Knowledge Transfer</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div><span style={{ fontSize: 11, color: 'var(--text-muted)' }}>KT Waves</span><div style={{ fontSize: 18, fontWeight: 800 }}>{kt.kt_waves || 0}</div></div>
                <div><span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Shadow Period</span><div style={{ fontSize: 18, fontWeight: 800 }}>{kt.shadow_period_weeks || 0}w</div></div>
                <div><span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Reverse KT</span><div style={{ fontSize: 18, fontWeight: 800 }}>{kt.reverse_kt_weeks || 0}w</div></div>
              </div>
              {kt.approach && <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{kt.approach}</div>}
              {kt.kt_topics && kt.kt_topics.length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {kt.kt_topics.map((t: string, i: number) => (
                    <div key={i} style={{ fontSize: 11, fontWeight: 600, color: '#10B981', background: '#10B98115', padding: '6px 10px', borderRadius: 6, lineHeight: 1.4, wordBreak: 'break-word' }}>
                      {t}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {Object.keys(parallel).length > 0 && (
              <div style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#F59E0B', marginBottom: 8 }}>Parallel Run</div>
                <div style={{ fontSize: 24, fontWeight: 800, marginBottom: 4 }}>{parallel.duration_weeks || 0} weeks</div>
                {parallel.sla_grace_period && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>SLA Grace: {parallel.sla_grace_period}</div>}
                {parallel.go_live_criteria && parallel.go_live_criteria.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#F59E0B', textTransform: 'uppercase', marginBottom: 4 }}>Go-Live Criteria</div>
                    {parallel.go_live_criteria.map((c: string, i: number) => (
                      <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '2px 0' }}>✓ {c}</div>
                    ))}
                  </div>
                )}
              </div>
            )}
            {Object.keys(cutover).length > 0 && (
              <div style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#EC4899', marginBottom: 8 }}>Cutover Strategy</div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 8 }}>{cutover.approach || 'Phased'}</div>
                {cutover.rollback_plan && <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: 6 }}><strong>↩ Rollback:</strong> {cutover.rollback_plan}</div>}
                {cutover.service_continuity_measures && cutover.service_continuity_measures.length > 0 && (
                  <div style={{ marginTop: 6 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#10B981', textTransform: 'uppercase', marginBottom: 4 }}>Continuity Measures</div>
                    {cutover.service_continuity_measures.map((m: string, i: number) => (
                      <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '2px 0', lineHeight: 1.4 }}>🛡 {m}</div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </SectionCard>
    )}

    {/* Stakeholder Change Management */}
    {stakeholders.length > 0 && (
      <SectionCard title={`Stakeholder Analysis (${stakeholders.length} groups)`} icon={<Users size={16} />} color="#8B5CF6">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
          {stakeholders.map((s: any, i: number) => {
            const impactColor = s.impact_level === 'high' ? '#DC2626' : s.impact_level === 'medium' ? '#F59E0B' : '#10B981'
            const readinessColor = s.change_readiness === 'resistant' ? '#DC2626' : s.change_readiness === 'needs_support' ? '#F59E0B' : '#10B981'
            return (
              <div key={i} style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', borderLeft: `4px solid ${impactColor}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: 14, fontWeight: 700 }}>{s.group}</span>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Badge text={`Impact: ${(s.impact_level || 'medium').toUpperCase()}`} color={impactColor} />
                    <Badge text={(s.change_readiness || 'needs_support').replace(/_/g, ' ').toUpperCase()} color={readinessColor} />
                  </div>
                </div>
                {s.engagement_approach && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6, lineHeight: 1.5 }}>{s.engagement_approach}</div>}
                {s.key_concerns && s.key_concerns.length > 0 && (
                  <div style={{ marginBottom: 6 }}>
                    <span style={{ fontSize: 10, color: '#EF4444', fontWeight: 700, textTransform: 'uppercase' }}>Concerns: </span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{s.key_concerns.join(' · ')}</span>
                  </div>
                )}
                {s.key_messages && s.key_messages.length > 0 && (
                  <div>
                    <span style={{ fontSize: 10, color: '#10B981', fontWeight: 700, textTransform: 'uppercase' }}>Messages: </span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{s.key_messages.join(' · ')}</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </SectionCard>
    )}

    {/* Training Plan */}
    {training.length > 0 && (
      <SectionCard title={`Training Plan (${training.length} programs)`} icon={<BookOpen size={16} />} color="#06B6D4">
        <table className="data-table">
          <thead><tr><th>Topic</th><th>Audience</th><th>Method</th><th>Duration</th><th>Timing</th></tr></thead>
          <tbody>{training.map((t: any, i: number) => (
            <tr key={i}>
              <td style={{ fontWeight: 600 }}>{t.training_topic || t.topic}</td>
              <td style={{ fontSize: 12 }}>{t.target_audience}</td>
              <td><Badge text={(t.delivery_method || 'virtual').toUpperCase()} color="#06B6D4" /></td>
              <td style={{ fontSize: 12 }}>{t.duration}</td>
              <td style={{ fontSize: 12 }}>{t.timing}</td>
            </tr>
          ))}</tbody>
        </table>
      </SectionCard>
    )}

    {/* Communication Plan */}
    {commPlan.length > 0 && (
      <SectionCard title={`Communication Plan (${commPlan.length})`} icon={<Target size={16} />} color="#F59E0B">
        <table className="data-table">
          <thead><tr><th>Audience</th><th>Channel</th><th>Frequency</th><th>Owner</th><th>Focus</th></tr></thead>
          <tbody>{commPlan.map((c: any, i: number) => (
            <tr key={i}>
              <td style={{ fontWeight: 600 }}>{c.audience}</td>
              <td><Badge text={(c.channel || '—').toUpperCase()} color="#F59E0B" /></td>
              <td style={{ fontSize: 12 }}>{c.frequency}</td>
              <td style={{ fontSize: 12 }}>{c.owner}</td>
              <td style={{ fontSize: 12 }}>{c.content_focus}</td>
            </tr>
          ))}</tbody>
        </table>
      </SectionCard>
    )}

    {/* Wave Rollout */}
    {waves.length > 0 && (
      <SectionCard title={`Wave Rollout (${waves.length} waves)`} icon={<BarChart3 size={16} />} color="#EC4899">
        <div style={{ display: 'grid', gap: 10 }}>
          {waves.map((w: any, i: number) => (
            <div key={i} style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', borderLeft: `4px solid ${phaseColors[i % phaseColors.length]}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 15, fontWeight: 800, color: phaseColors[i % phaseColors.length] }}>Wave {w.wave || i + 1}</span>
                <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>W{w.start_week}–W{w.end_week}</span>
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 6 }}>{w.scope}</div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {(w.geographies || []).map((g: string, j: number) => <Badge key={`g${j}`} text={g} color="#3B82F6" />)}
                {(w.platforms || []).map((p: string, j: number) => <Badge key={`p${j}`} text={p} color="#8B5CF6" />)}
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    )}

    {/* RACI Matrix */}
    {raci.length > 0 && (
      <SectionCard title={`RACI Matrix (${raci.length} activities)`} icon={<CheckCircle size={16} />} color="#10B981">
        <table className="data-table">
          <thead><tr><th>Activity</th><th style={{ textAlign: 'center' }}>R</th><th style={{ textAlign: 'center' }}>A</th><th style={{ textAlign: 'center' }}>C</th><th style={{ textAlign: 'center' }}>I</th></tr></thead>
          <tbody>{raci.map((r: any, i: number) => (
            <tr key={i}>
              <td style={{ fontWeight: 600, maxWidth: 240 }}>{r.activity}</td>
              <td style={{ textAlign: 'center', fontSize: 12, color: '#DC2626', fontWeight: 700 }}>{r.responsible}</td>
              <td style={{ textAlign: 'center', fontSize: 12, color: '#3B82F6', fontWeight: 700 }}>{r.accountable}</td>
              <td style={{ textAlign: 'center', fontSize: 12, color: '#F59E0B' }}>{r.consulted}</td>
              <td style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)' }}>{r.informed}</td>
            </tr>
          ))}</tbody>
        </table>
      </SectionCard>
    )}

    {/* Milestone Checkpoints */}
    {milestones.length > 0 && (
      <SectionCard title={`Milestone Checkpoints (${milestones.length})`} icon={<Target size={16} />} color="#3B82F6">
        <div style={{ display: 'grid', gap: 8 }}>
          {milestones.map((m: any, i: number) => (
            <div key={i} style={{ padding: '12px 16px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: 16 }}>
              <div style={{ width: 48, height: 48, borderRadius: '50%', background: m.go_no_go ? 'rgba(59,130,246,0.1)' : 'rgba(107,114,128,0.1)', border: `2px solid ${m.go_no_go ? '#3B82F6' : '#6B7280'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <span style={{ fontSize: 13, fontWeight: 800, color: m.go_no_go ? '#3B82F6' : '#6B7280' }}>W{m.target_week}</span>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>
                  {m.milestone}
                  {m.go_no_go && <span style={{ fontSize: 10, color: '#DC2626', fontWeight: 700, marginLeft: 8, background: 'rgba(220,38,38,0.08)', padding: '2px 8px', borderRadius: 4 }}>GO/NO-GO</span>}
                </div>
                {m.criteria && m.criteria.length > 0 && (
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{m.criteria.join(' · ')}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    )}

    {/* Transition Risks */}
    {risks.length > 0 && (
      <SectionCard title={`Transition Risks (${risks.length})`} icon={<AlertTriangle size={16} />} color="#EF4444">
        <table className="data-table">
          <thead><tr><th>Risk</th><th>Likelihood</th><th>Impact</th><th>Mitigation</th><th>Owner</th></tr></thead>
          <tbody>{risks.map((r: any, i: number) => {
            const lColor = r.likelihood === 'high' ? '#DC2626' : r.likelihood === 'medium' ? '#F59E0B' : '#10B981'
            const iColor = r.impact === 'high' ? '#DC2626' : r.impact === 'medium' ? '#F59E0B' : '#10B981'
            return (
              <tr key={i}>
                <td style={{ fontWeight: 600, maxWidth: 280 }}>{r.risk}</td>
                <td><Badge text={(r.likelihood || 'medium').toUpperCase()} color={lColor} /></td>
                <td><Badge text={(r.impact || 'medium').toUpperCase()} color={iColor} /></td>
                <td style={{ fontSize: 12, maxWidth: 280 }}>{r.mitigation || '—'}</td>
                <td style={{ fontSize: 12 }}>{r.owner || '—'}</td>
              </tr>
            )
          })}</tbody>
        </table>
      </SectionCard>
    )}

    {/* Success Metrics */}
    {successMetrics.length > 0 && (
      <SectionCard title={`Success Metrics (${successMetrics.length})`} icon={<CheckCircle size={16} />} color="#10B981">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
          {successMetrics.map((m: any, i: number) => (
            <div key={i} style={{ padding: '12px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', borderLeft: '3px solid #10B981' }}>
              <div style={{ fontSize: 13, fontWeight: 700 }}>{m.metric}</div>
              <div style={{ fontSize: 12, color: '#10B981', marginTop: 4 }}>Target: {m.target}</div>
              {m.measurement_method && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{m.measurement_method}</div>}
            </div>
          ))}
        </div>
      </SectionCard>
    )}
  </>)
}
