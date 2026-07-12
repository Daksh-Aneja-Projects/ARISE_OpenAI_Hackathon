
const toText = (obj: any, depth = 0): string => {
  if (!obj) return ''
  if (typeof obj === 'string') return obj
  if (typeof obj === 'number' || typeof obj === 'boolean') return String(obj)
  if (Array.isArray(obj)) return obj.map(item => toText(item, depth)).filter(Boolean).join('\n\n')
  if (typeof obj === 'object') {
    // Unwrap single-key 'content' wrappers
    if (Object.keys(obj).length === 1 && obj.content) return toText(obj.content, depth)
    // Extract 'table' keys directly
    if (obj.table) return Object.values(obj).map(v => toText(v, depth)).filter(Boolean).join('\n\n')
    // Assemble dict keys as subsections
    const parts: string[] = []
    for (const [key, val] of Object.entries(obj)) {
      const text = toText(val, depth + 1)
      if (text) {
        const header = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
        // If text starts with markdown header or table, don't add extra header
        if (text.trimStart().startsWith('#') || text.trimStart().startsWith('|')) {
          parts.push(text)
        } else {
          const hashes = '#'.repeat(Math.min(depth + 3, 5))
          parts.push(`${hashes} ${header}\n\n${text}`)
        }
      }
    }
    return parts.join('\n\n')
  }
  return String(obj)
}

const renderInline = (line: string) => {
  if (typeof line !== 'string') return line
  // Process **bold** first, then *italic*
  const elements: any[] = []
  // Split by **bold** markers
  const boldParts = line.split('**')
  boldParts.forEach((boldPart, bi) => {
    if (bi % 2 === 1) {
      // Bold segment
      elements.push(<strong key={`b${bi}`}>{boldPart}</strong>)
    } else {
      // Check for *italic* within non-bold segments
      if (boldPart.includes('*')) {
        const italicParts = boldPart.split('*')
        italicParts.forEach((ip, ii) => {
          if (ii % 2 === 1) {
            elements.push(<em key={`i${bi}-${ii}`}>{ip}</em>)
          } else if (ip) {
            elements.push(ip)
          }
        })
      } else {
        elements.push(boldPart)
      }
    }
  })
  return elements.length > 0 ? elements : line
}

const FormattedText = ({ text }: { text: any }) => {
  if (!text) return null
  // Defensively convert non-string content to text
  const resolved = typeof text === 'string' ? text : toText(text)
  if (!resolved) return null
  const lines = resolved.split('\n')

  // Parse markdown tables
  const elements: any[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i].trim()

    // Detect markdown table (line starts and ends with |)
    if (line.startsWith('|') && line.endsWith('|') && line.includes('|')) {
      const tableRows: string[][] = []
      let j = i
      while (j < lines.length && lines[j].trim().startsWith('|')) {
        const row = lines[j].trim()
        // Skip separator rows (|---|---|)
        if (/^\|[\s\-:|]+\|$/.test(row)) { j++; continue }
        const cells = row.split('|').slice(1, -1).map(c => c.trim())
        tableRows.push(cells)
        j++
      }
      if (tableRows.length > 0) {
        const headerRow = tableRows[0]
        const bodyRows = tableRows.slice(1)
        elements.push(
          <table key={`tbl-${i}`} className="data-table" style={{ margin: '16px 0', width: '100%' }}>
            <thead>
              <tr>{headerRow.map((h, hi) => <th key={hi} style={{ padding: '10px 14px', borderBottom: '2px solid #CBD5E1', backgroundColor: '#F8FAFC', fontWeight: 600, color: '#475569', textAlign: 'left', fontSize: '10pt', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{renderInline(h)}</th>)}</tr>
            </thead>
            <tbody>
              {bodyRows.map((row, ri) => (
                <tr key={ri}>
                  {row.map((cell, ci) => <td key={ci} style={{ padding: '10px 14px', borderBottom: '1px solid #E2E8F0', color: '#334155', verticalAlign: 'top' }}>{renderInline(cell)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        )
      }
      i = j
      continue
    }

    // Non-table lines
    if (!line) { elements.push(<br key={i} />); i++; continue }
    if (line.startsWith('#### ')) { elements.push(<h4 key={i} style={{ fontSize: '15px', fontWeight: 700, margin: '20px 0 8px 0', color: '#334155' }}>{renderInline(line.replace('#### ', ''))}</h4>); i++; continue }
    if (line.startsWith('### ')) { elements.push(<h3 key={i} style={{ fontSize: '18px', fontWeight: 600, margin: '24px 0 12px 0', color: '#1E293B' }}>{renderInline(line.replace('### ', ''))}</h3>); i++; continue }
    if (line.startsWith('## ')) { elements.push(<h2 key={i} style={{ fontSize: '20px', fontWeight: 700, margin: '32px 0 16px 0', color: '#0F172A' }}>{renderInline(line.replace('## ', ''))}</h2>); i++; continue }
    if (line.startsWith('# ')) { elements.push(<h1 key={i} style={{ fontSize: '24px', fontWeight: 800, margin: '40px 0 20px 0', color: '#0F172A' }}>{renderInline(line.replace('# ', ''))}</h1>); i++; continue }
    if (line.startsWith('- ') || line.startsWith('* ')) { elements.push(<li key={i} style={{ marginLeft: '24px', marginBottom: '8px', listStyleType: 'disc' }}>{renderInline(line.substring(2))}</li>); i++; continue }
    if (line.startsWith('---')) { elements.push(<hr key={i} style={{ margin: '24px 0', border: 'none', borderTop: '1px solid #E2E8F0' }} />); i++; continue }

    if (line.startsWith('**') && !line.includes('####') && !line.includes('###')) {
      elements.push(<p key={i} style={{ margin: '0 0 12px 0', paddingLeft: '16px', borderLeft: '3px solid #E2E8F0' }}>{renderInline(line)}</p>)
      i++; continue
    }

    elements.push(<p key={i} style={{ margin: '0 0 12px 0' }}>{renderInline(line)}</p>)
    i++
  }

  return <>{elements}</>
}

export function ProposalWriterRenderer({ data, manifest = {} }: { data: any, manifest?: any }) {
  const sections = Array.isArray(data?.sections) ? data.sections : []
  const caseStudies = Array.isArray(data?.case_studies) ? data.case_studies : []

  const bidderName = manifest?.bidder_profile?.name || 'Our Organization'
  const clientName = manifest?.client?.name || manifest?.intake_output?.client_name || 'Client'
  const rfpName = manifest?.intake_output?.rfp_name || manifest?.intake_output?.project_name || 'Strategic Partnership Proposal'
  const dateStr = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })

  const fmtCurrency = (v: any) => {
    if (!v) return '—'
    const n = typeof v === 'string' ? parseFloat(v) : v
    if (isNaN(n)) return String(v)
    return n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(0)}K` : `$${n.toLocaleString()}`
  }

  const styles = {
    h1: { fontSize: '36px', color: '#0F172A', margin: '0 0 16px 0', fontWeight: '800', letterSpacing: '-0.02em' },
    h2: { fontSize: '24px', color: '#1E293B', borderBottom: '2px solid #E2E8F0', paddingBottom: '12px', marginBottom: '24px', fontWeight: '700', letterSpacing: '-0.01em' },
    h3: { fontSize: '18px', color: '#334155', margin: '32px 0 16px 0', fontWeight: '600', letterSpacing: '-0.01em' },
    h4: { fontSize: '15px', color: '#475569', margin: '0 0 12px 0', fontWeight: '600' },
    table: { width: '100%', borderCollapse: 'collapse' as const, fontSize: '11pt', backgroundColor: '#ffffff', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginTop: '16px', marginBottom: '32px' },
    th: { padding: '14px 16px', borderBottom: '2px solid #CBD5E1', backgroundColor: '#F8FAFC', fontWeight: '600', color: '#475569', textAlign: 'left' as const, fontSize: '10pt', textTransform: 'uppercase' as const, letterSpacing: '0.05em' },
    td: { padding: '14px 16px', borderBottom: '1px solid #E2E8F0', color: '#334155', verticalAlign: 'top' as const },
    text: { fontSize: '11pt', textAlign: 'left' as const, color: '#334155', lineHeight: 1.7 },
    container: { background: '#ffffff', color: '#0F172A', width: '100%', margin: '0 auto', padding: '80px 100px', boxShadow: '0 20px 40px rgba(0,0,0,0.08)', borderRadius: '12px', fontFamily: '"Calibri", "Inter", "Segoe UI", "Helvetica Neue", sans-serif', boxSizing: 'border-box' as const }
  }

  const Badge = ({ text, color }: { text: string, color: string }) => (
    <span style={{ display: 'inline-flex', alignItems: 'center', padding: '2px 8px', borderRadius: '12px', fontSize: '9pt', fontWeight: 600, backgroundColor: `${color}15`, color: color, border: `1px solid ${color}30` }}>
      {text}
    </span>
  )

  return (
    <div style={styles.container}>
      {/* Formal Document Cover Header */}
      <div style={{ minHeight: '80vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'flex-start', padding: '40px 0', borderBottom: 'none' }}>
        <div style={{ width: '80px', height: '6px', backgroundColor: '#3B82F6', marginBottom: '32px' }} />
        <div style={{ fontSize: '14px', color: '#3B82F6', textTransform: 'uppercase', letterSpacing: '2px', fontWeight: 700, marginBottom: '16px' }}>
          Strategic Proposal
        </div>
        <h1 style={{ ...styles.h1, fontSize: '52px', lineHeight: 1.1, marginBottom: '24px', letterSpacing: '-0.03em' }}>
          {rfpName}
        </h1>
        <h2 style={{ ...styles.h2, fontSize: '26px', color: '#64748B', borderBottom: 'none', fontWeight: '400', marginBottom: '0' }}>
          Prepared exclusively for <strong style={{ color: '#0F172A' }}>{clientName}</strong>
        </h2>

        <div style={{ marginTop: 'auto', paddingTop: '80px', width: '100%' }}>
          <div style={{ fontSize: '13px', color: '#1E293B', textTransform: 'uppercase', letterSpacing: '2px', fontWeight: 700, marginBottom: '12px' }}>
            {dateStr}
          </div>
          <div style={{ fontSize: '10pt', color: '#64748B', lineHeight: 1.5, borderTop: '1px solid #E2E8F0', paddingTop: '16px', maxWidth: '800px' }}>
            <strong>CONFIDENTIALITY NOTICE:</strong> This document and any attachments contain confidential and proprietary information of {bidderName}. It is submitted in confidence for the sole purpose of evaluating a potential partnership with {clientName}. Reproduction, distribution, or disclosure without prior written consent from {bidderName} is strictly prohibited.
          </div>
        </div>
      </div>

      <div style={{ pageBreakBefore: 'always', margin: '64px 0' }} />

      {/* Table of Contents */}
      {sections.length > 0 && (
        <div style={{ marginBottom: '80px', padding: '48px', backgroundColor: '#F8FAFC', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
          <h2 style={{ ...styles.h2, fontSize: '20px', borderBottom: 'none', marginBottom: '32px', color: '#1E293B' }}>Table of Contents</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {sections.map((sec: any, i: number) => (
              <div key={i} style={{ fontSize: '11pt', color: '#334155', fontWeight: 500, display: 'flex', borderBottom: '1px dotted #CBD5E1', paddingBottom: '4px' }}>
                {i + 1}. {sec.title}
              </div>
            ))}
            {caseStudies.length > 0 && (
              <div style={{ fontSize: '11pt', color: '#334155', fontWeight: 500, display: 'flex', borderBottom: '1px dotted #CBD5E1', paddingBottom: '4px' }}>
                {sections.length + 1}. Relevant Credentials
              </div>
            )}
          </div>
        </div>
      )}

      {/* Dynamic Sections */}
      {sections.map((section: any, index: number) => {
        const key = section.id
        const rawData = manifest[key]?.data || manifest[key] || {}

        return (
          <div key={index} style={{ marginBottom: '48px' }}>
            <h2 style={styles.h2}>
              {index + 1}. {section.title}
            </h2>
            <div style={styles.text}>
              <FormattedText text={section.content} />
            </div>

            {key === 'commercial_output' && rawData && (
              <>
                {rawData.pl_model && Object.keys(rawData.pl_model).length > 0 && (
                  <>
                    <h3 style={styles.h3}>Financial Summary</h3>
                    <table style={styles.table}>
                      <thead><tr><th style={styles.th}>Commercial Metric</th><th style={styles.th}>Value</th></tr></thead>
                      <tbody>
                        <tr><td style={styles.td}><strong>Total Contract Value (TCV)</strong></td><td style={styles.td}><span style={{ fontWeight: 700, color: '#10B981' }}>{fmtCurrency(rawData.pl_model.revenue?.total_contract_value || rawData.pl_model.revenue)}</span></td></tr>
                        <tr><td style={styles.td}><strong>Monthly Run Rate</strong></td><td style={styles.td}>{fmtCurrency(rawData.pl_model.revenue?.monthly_price || rawData.pl_model.per_month?.price_to_client || rawData.pl_model.per_month)}</td></tr>
                      </tbody>
                    </table>
                  </>
                )}

                {rawData.resource_loading && rawData.resource_loading.cost_by_location && (
                  <>
                    <h3 style={styles.h3}>Cost Breakdown</h3>
                    <table style={styles.table}>
                      <thead><tr><th style={styles.th}>Cost Category</th><th style={styles.th}>Total Allocated Cost</th></tr></thead>
                      <tbody>
                        <tr><td style={styles.td}><strong>Onshore Operations</strong></td><td style={styles.td}>{fmtCurrency(rawData.resource_loading.cost_by_location.onshore || 0)}</td></tr>
                        <tr><td style={styles.td}><strong>Offshore Operations</strong></td><td style={styles.td}>{fmtCurrency(rawData.resource_loading.cost_by_location.offshore || 0)}</td></tr>
                        <tr><td style={styles.td}><strong>Transition & Setup</strong></td><td style={styles.td}>{fmtCurrency(rawData.pl_model?.costs?.transition_cost || rawData.pl_model?.costs?.transition || 0)}</td></tr>
                      </tbody>
                    </table>
                  </>
                )}

                {(rawData.resource_plan || rawData.pl_model?.resource_plan) && (
                  <>
                    <h3 style={styles.h3}>Detailed Resource & Rate Breakdown</h3>
                    <table style={styles.table}>
                      <thead>
                        <tr>
                          <th style={styles.th}>Role / Designation</th>
                          <th style={styles.th}>Location</th>
                          <th style={{ ...styles.th, textAlign: 'center' }}>FTE Allocation</th>
                          <th style={{ ...styles.th, textAlign: 'right' }}>Monthly Rate ($)</th>
                        </tr>
                      </thead>
                      <tbody>{(rawData.resource_plan || rawData.pl_model?.resource_plan).map((r: any, i: number) => {
                        const loc = (r.location || r.type || 'Blended').toUpperCase()
                        const monthlyRate = r.monthly_cost || r.rate || r.monthly_rate || 0
                        return (
                          <tr key={i}>
                            <td style={styles.td}><strong>{r.role || r.name || r.title}</strong></td>
                            <td style={styles.td}>
                              <Badge text={loc} color={loc === 'ONSHORE' ? '#3B82F6' : '#8B5CF6'} />
                            </td>
                            <td style={{ ...styles.td, textAlign: 'center' }}><strong>{r.fte || r.count || 1}</strong></td>
                            <td style={{ ...styles.td, textAlign: 'right', fontFamily: 'monospace' }}>
                              {monthlyRate ? `$${monthlyRate.toLocaleString()}` : 'Included in TCV'}
                            </td>
                          </tr>
                        )
                      })}</tbody>
                    </table>
                  </>
                )}
              </>
            )}

            {key === 'automation_ai_output' && rawData.prioritisation_table && rawData.prioritisation_table.length > 0 && (
              <>
                <h3 style={styles.h3}>Identified Automation Opportunities</h3>
                <table style={styles.table}>
                  <thead><tr><th style={styles.th}>Opportunity</th><th style={styles.th}>Platform</th><th style={styles.th}>Priority</th><th style={styles.th}>Impact</th></tr></thead>
                  <tbody>{rawData.prioritisation_table.map((opp: any, i: number) => {
                    const priorityColor = (opp.priority || '').toLowerCase() === 'critical' ? '#DC2626' : (opp.priority || '').toLowerCase() === 'high' ? '#F59E0B' : '#10B981'
                    return (
                      <tr key={i}>
                        <td style={styles.td}><strong>{opp.opportunity || opp.name || opp.title}</strong></td>
                        <td style={styles.td}>{opp.platform || opp.product}</td>
                        <td style={styles.td}>
                          <Badge text={(opp.priority || 'Medium').toUpperCase()} color={priorityColor} />
                        </td>
                        <td style={styles.td}>{opp.impact || opp.benefit}</td>
                      </tr>
                    )
                  })}</tbody>
                </table>
              </>
            )}

            {key === 'solution_output' && (rawData.integration_architecture?.data_flows || rawData.solution_design?.integration_architecture?.data_flows) && (
              <>
                <h3 style={styles.h3}>Integration Data Flows</h3>
                <table style={styles.table}>
                  <thead><tr><th style={styles.th}>Source</th><th style={styles.th}>Target</th><th style={styles.th}>Pattern</th><th style={styles.th}>Frequency</th></tr></thead>
                  <tbody>{(rawData.integration_architecture?.data_flows || rawData.solution_design?.integration_architecture?.data_flows).map((f: any, i: number) => (
                    <tr key={i}>
                      <td style={styles.td}><strong>{f.source}</strong></td>
                      <td style={styles.td}><strong>{f.target}</strong></td>
                      <td style={styles.td}><Badge text={f.pattern || 'API'} color="#3B82F6" /></td>
                      <td style={styles.td}>{f.frequency}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </>
            )}

            {key === 'scope_output' && (rawData.scope_by_platform || rawData.scope_package?.scope_by_platform) && (
              <>
                <h3 style={styles.h3}>Detailed Scope by Platform</h3>
                {(rawData.scope_by_platform || rawData.scope_package?.scope_by_platform).map((plat: any, pi: number) => (
                  <div key={pi} style={{ marginBottom: '24px' }}>
                    <h4 style={styles.h4}>{plat.platform || plat.product}</h4>
                    {plat.work_packages && plat.work_packages.length > 0 && (
                      <table style={styles.table}>
                        <thead><tr><th style={styles.th}>Work Package</th><th style={styles.th}>Effort (Days)</th><th style={styles.th}>Phase</th></tr></thead>
                        <tbody>{plat.work_packages.map((wp: any, i: number) => (
                          <tr key={i}>
                            <td style={styles.td}><strong>{wp.name || wp.activity || wp.title}</strong></td>
                            <td style={styles.td}>{wp.effort_days || wp.effort || '—'}</td>
                            <td style={styles.td}>{wp.phase || '—'}</td>
                          </tr>
                        ))}</tbody>
                      </table>
                    )}
                  </div>
                ))}
              </>
            )}

            {key === 'transition_change_output' && (rawData.transition_plan?.phases || rawData.phases) && (
              <>
                <h3 style={styles.h3}>Proposed Transition Phases</h3>
                <table style={styles.table}>
                  <thead><tr><th style={styles.th}>Phase</th><th style={styles.th}>Timeline</th><th style={styles.th}>Key Deliverables</th></tr></thead>
                  <tbody>{(rawData.transition_plan?.phases || rawData.phases).map((phase: any, i: number) => (
                    <tr key={i}>
                      <td style={styles.td}><strong>{phase.phase_name || `Phase ${i + 1}`}</strong></td>
                      <td style={styles.td}>Week {phase.start_week} - {phase.end_week} <span style={{ color: '#6B7280', fontSize: '9pt' }}>({phase.duration_weeks}w)</span></td>
                      <td style={styles.td}>
                        <ul style={{ margin: 0, paddingLeft: 16 }}>
                          {(phase.deliverables || phase.objectives || []).slice(0, 3).map((d: string, di: number) => <li key={di}>{d}</li>)}
                        </ul>
                      </td>
                    </tr>
                  ))}</tbody>
                </table>
              </>
            )}
          </div>
        )
      })}

      {caseStudies.length > 0 && (
        <div style={{ marginBottom: '48px', pageBreakInside: 'avoid' }}>
          <h2 style={styles.h2}>{sections.length + 1}. Relevant Credentials</h2>
          <p style={{ ...styles.text, marginBottom: '32px', color: '#64748B' }}>
            The following case studies demonstrate our proven capability in delivering engagements of similar scale, complexity, and technology stack.
          </p>
          <div style={{ display: 'grid', gap: '32px' }}>
            {caseStudies.map((study: any, i: number) => {
              const accentColors = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444']
              const accent = accentColors[i % accentColors.length]
              const isPlaceholder = study.verified === false || (study.title || '').includes('[To be validated')

              return (
                <div key={i} style={{
                  borderRadius: '12px', overflow: 'hidden',
                  border: '1px solid #E2E8F0',
                  boxShadow: '0 4px 16px rgba(0,0,0,0.06)',
                  background: '#ffffff',
                }}>
                  {/* Header bar */}
                  <div style={{
                    background: `linear-gradient(135deg, ${accent}, ${accent}CC)`,
                    padding: '20px 28px',
                    color: '#ffffff',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: '20px', fontWeight: 700, lineHeight: 1.3, marginBottom: '8px' }}>
                          {(study.title || '').replace(/\[To be validated.*?\]/g, '').trim()}
                        </div>
                        <div style={{ fontSize: '13px', opacity: 0.9 }}>
                          {study.client_type || 'Enterprise'}
                        </div>
                      </div>
                      {isPlaceholder && (
                        <span style={{
                          fontSize: '9px', padding: '3px 8px', borderRadius: '4px',
                          background: 'rgba(255,255,255,0.2)', color: '#fff',
                          fontWeight: 600, letterSpacing: '0.5px', whiteSpace: 'nowrap',
                          textTransform: 'uppercase',
                        }}>
                          Pending Validation
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Metrics bar */}
                  {(study.team_size || study.duration || study.technologies) && (
                    <div style={{
                      display: 'flex', gap: '0', borderBottom: '1px solid #E2E8F0',
                      background: '#F8FAFC',
                    }}>
                      {study.team_size && (
                        <div style={{ flex: 1, padding: '12px 20px', borderRight: '1px solid #E2E8F0' }}>
                          <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '2px' }}>Team</div>
                          <div style={{ fontSize: '14px', fontWeight: 700, color: '#1E293B' }}>{study.team_size}</div>
                        </div>
                      )}
                      {study.duration && (
                        <div style={{ flex: 1, padding: '12px 20px', borderRight: '1px solid #E2E8F0' }}>
                          <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '2px' }}>Duration</div>
                          <div style={{ fontSize: '14px', fontWeight: 700, color: '#1E293B' }}>{study.duration}</div>
                        </div>
                      )}
                      {study.technologies && Array.isArray(study.technologies) && (
                        <div style={{ flex: 2, padding: '12px 20px' }}>
                          <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>Technologies</div>
                          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                            {study.technologies.slice(0, 5).map((t: string, ti: number) => (
                              <span key={ti} style={{
                                fontSize: '10px', padding: '2px 6px', borderRadius: '4px',
                                background: `${accent}12`, color: accent, fontWeight: 600,
                                border: `1px solid ${accent}25`,
                              }}>{t}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Body */}
                  <div style={{ padding: '24px 28px' }}>
                    <div style={{ display: 'grid', gap: '20px' }}>
                      {/* Challenge */}
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                          <div style={{ width: '4px', height: '16px', borderRadius: '2px', background: '#EF4444' }} />
                          <h4 style={{ margin: 0, fontSize: '11px', color: '#EF4444', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700 }}>Challenge</h4>
                        </div>
                        <div style={{ ...styles.text, paddingLeft: '12px' }}><FormattedText text={study.challenge} /></div>
                      </div>

                      {/* Solution */}
                      <div style={{ background: '#F0F9FF', borderRadius: '8px', padding: '16px 20px', borderLeft: `4px solid ${accent}` }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                          <h4 style={{ margin: 0, fontSize: '11px', color: accent, textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700 }}>Solution Delivered</h4>
                        </div>
                        <div style={styles.text}><FormattedText text={study.solution} /></div>
                      </div>

                      {/* Outcome */}
                      <div style={{ background: '#F0FDF4', borderRadius: '8px', padding: '16px 20px', borderLeft: '4px solid #10B981' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                          <h4 style={{ margin: 0, fontSize: '11px', color: '#10B981', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700 }}>Business Outcome</h4>
                        </div>
                        <div style={styles.text}><FormattedText text={study.outcome} /></div>
                      </div>
                    </div>

                    {/* Relevance footer */}
                    {study.relevance && (
                      <div style={{
                        marginTop: '20px', paddingTop: '16px',
                        borderTop: '1px dashed #CBD5E1',
                      }}>
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                          <div style={{
                            width: '20px', height: '20px', borderRadius: '50%',
                            background: `${accent}15`, display: 'flex', alignItems: 'center',
                            justifyContent: 'center', flexShrink: 0, marginTop: '2px',
                          }}>
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke={accent} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M12 2L2 7l10 5 10-5-10-5z M2 17l10 5 10-5" />
                            </svg>
                          </div>
                          <div>
                            <div style={{ fontSize: '11px', color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600, marginBottom: '4px' }}>
                              Strategic Relevance to {clientName}
                            </div>
                            <div style={{ ...styles.text, fontSize: '10pt', color: '#475569' }}>
                              <FormattedText text={study.relevance} />
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}