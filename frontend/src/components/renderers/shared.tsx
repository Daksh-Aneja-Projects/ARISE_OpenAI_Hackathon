 
export const MetricCard = ({ label, value, color }: { label: string; value: any; color?: string }) => (
  <div style={{ padding: '14px 18px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', borderLeft: `3px solid ${color || 'var(--accent-primary)'}` }}>
    <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</div>
    <div style={{ fontSize: 20, fontWeight: 800, marginTop: 4, color: color || 'var(--text-primary)', wordBreak: 'break-word' }}>{String(value ?? '—')}</div>
  </div>
)

export const SectionCard = ({ title, icon, children, color }: { title: string; icon?: any; children: any; color?: string }) => (
  <div className="glass-card" style={{ marginBottom: 20, borderLeft: `4px solid ${color || 'var(--accent-primary)'}` }}>
    <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
      {icon} {title}
    </h3>
    {children}
  </div>
)

export const Badge = ({ text, color }: { text: string; color: string }) => (
  <span style={{ fontSize: 10, fontWeight: 700, color, background: `${color}15`, padding: '2px 8px', borderRadius: 4, whiteSpace: 'nowrap' }}>{text}</span>
)

export const InfoRow = ({ label, value, color }: { label: string; value: any; color?: string }) => (
  <div style={{ padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', marginBottom: 8, border: '1px solid var(--border-subtle)', borderLeft: color ? `3px solid ${color}` : undefined }}>
    <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</div>
    <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4, color: 'var(--text-primary)' }}>{typeof value === 'string' ? value : JSON.stringify(value)}</div>
  </div>
)
