import { useState, useEffect } from 'react'
import { useAuth } from '../App'
import { Lock, Mail, ArrowRight } from 'lucide-react'

export default function Login() {
  const { login } = useAuth()
  const [email, setEmail] = useState('bid.manager@arise.dev')
  const [password, setPassword] = useState('demo123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => { requestAnimationFrame(() => setMounted(true)) }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(''); setLoading(true)
    try { await login(email, password) } catch (err: unknown) { setError((err as Error).message || 'Login failed') }
    setLoading(false)
  }

  return (
    <>
      <style>{css}</style>
      <div className="lg-page">
        {/* Animated gradient mesh blobs */}
        <div className="lg-mesh">
          <div className="lg-blob lg-blob-1" />
          <div className="lg-blob lg-blob-2" />
          <div className="lg-blob lg-blob-3" />
          <div className="lg-blob lg-blob-4" />
          <div className="lg-blob lg-blob-5" />
        </div>
        <div className="lg-noise" />

        <div className="lg-wrapper" style={{ opacity: mounted ? 1 : 0, transform: mounted ? 'scale(1)' : 'scale(0.97)' }}>
          {/* Brand */}
          <div className="lg-brand-row">
            <img src="/arise-mark.svg" alt="" className="lg-mark" />
            <div className="lg-brand-text">
              <span className="lg-brand-name">ARISE</span>
              <span className="lg-brand-tag">Autonomous RFP Intelligence</span>
            </div>
          </div>

          {/* Card */}
          <div className="lg-card">
            <div className="lg-card-inner">
              <h1 className="lg-h1">Welcome back</h1>
              <p className="lg-p">Sign in to continue to your workspace</p>

              <form onSubmit={handleSubmit} className="lg-form">
                <label className="lg-label">Email</label>
                <div className="lg-input-group">
                  <Mail size={16} className="lg-input-icon" />
                  <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@company.com" className="lg-input" />
                </div>

                <label className="lg-label">Password</label>
                <div className="lg-input-group">
                  <Lock size={16} className="lg-input-icon" />
                  <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter your password" className="lg-input" />
                </div>

                {error && <div className="lg-err">{error}</div>}

                <button type="submit" disabled={loading} className="lg-submit">
                  {loading
                    ? <div className="loading-spinner" style={{ width:18, height:18, borderWidth:2 }} />
                    : <>Sign In <ArrowRight size={16} /></>
                  }
                </button>
              </form>
            </div>

            {/* Bottom stripe */}
            <div className="lg-card-stripe" />
          </div>

          <p className="lg-footer">Enterprise AI Platform for Pre-Sales Teams</p>
        </div>
      </div>
    </>
  )
}

const css = `
@keyframes blob1 { 0%,100%{transform:translate(0,0) scale(1)} 25%{transform:translate(80px,-60px) scale(1.15)} 50%{transform:translate(-30px,80px) scale(0.9)} 75%{transform:translate(50px,30px) scale(1.1)} }
@keyframes blob2 { 0%,100%{transform:translate(0,0) scale(1)} 33%{transform:translate(-90px,50px) scale(1.2)} 66%{transform:translate(60px,-40px) scale(0.85)} }
@keyframes blob3 { 0%,100%{transform:translate(0,0) scale(1)} 20%{transform:translate(40px,70px) scale(1.1)} 60%{transform:translate(-70px,-30px) scale(0.95)} 80%{transform:translate(20px,-60px) scale(1.05)} }
@keyframes blob4 { 0%,100%{transform:translate(0,0) scale(1)} 40%{transform:translate(-50px,-70px) scale(1.15)} 70%{transform:translate(70px,40px) scale(0.9)} }
@keyframes blob5 { 0%,100%{transform:translate(0,0) scale(1)} 30%{transform:translate(60px,50px) scale(0.9)} 60%{transform:translate(-40px,-60px) scale(1.1)} }
@keyframes shimmer { 0%{background-position:-200% 0} 100%{background-position:200% 0} }

.lg-page {
  min-height:100vh; display:flex; align-items:center; justify-content:center;
  background:#F5F7FF; position:relative; overflow:hidden;
  font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
}

/* Gradient mesh - vivid animated blobs */
.lg-mesh { position:absolute; inset:0; overflow:hidden; filter:blur(80px); }
.lg-blob { position:absolute; border-radius:50%; }
.lg-blob-1 { width:45vw; height:45vw; top:-10%; left:-5%; background:radial-gradient(circle,rgba(99,102,241,0.35),transparent 70%); animation:blob1 18s ease-in-out infinite; }
.lg-blob-2 { width:40vw; height:40vw; top:10%; right:-8%; background:radial-gradient(circle,rgba(0,153,255,0.3),transparent 70%); animation:blob2 22s ease-in-out infinite; }
.lg-blob-3 { width:35vw; height:35vw; bottom:-5%; left:20%; background:radial-gradient(circle,rgba(6,182,212,0.25),transparent 70%); animation:blob3 20s ease-in-out infinite; }
.lg-blob-4 { width:30vw; height:30vw; top:40%; left:50%; background:radial-gradient(circle,rgba(168,85,247,0.2),transparent 70%); animation:blob4 24s ease-in-out infinite; }
.lg-blob-5 { width:25vw; height:25vw; bottom:20%; right:15%; background:radial-gradient(circle,rgba(59,130,246,0.2),transparent 70%); animation:blob5 16s ease-in-out infinite; }

/* Subtle noise texture */
.lg-noise {
  position:absolute; inset:0; z-index:1;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events:none;
}

.lg-wrapper {
  position:relative; z-index:2;
  display:flex; flex-direction:column; align-items:center;
  width:100%; max-width:400px;
  transition:opacity 0.8s cubic-bezier(0.16,1,0.3,1), transform 0.8s cubic-bezier(0.16,1,0.3,1);
}

/* Brand */
.lg-brand-row { display:flex; align-items:center; gap:12px; margin-bottom:28px; }
.lg-mark { height:38px; width:38px; }
.lg-brand-text { display:flex; flex-direction:column; }
.lg-brand-name { font-size:26px; font-weight:900; letter-spacing:3px; line-height:1; background:linear-gradient(90deg,#06B6D4,#3B82F6,#8B5CF6); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.lg-brand-tag { font-size:10px; letter-spacing:1px; text-transform:uppercase; color:#3B82F6; margin-top:2px; font-weight:700; }

/* Card */
.lg-card {
  width:100%; border-radius:20px; overflow:hidden;
  background:rgba(255,255,255,0.72);
  backdrop-filter:blur(40px) saturate(180%); -webkit-backdrop-filter:blur(40px) saturate(180%);
  border:1px solid rgba(255,255,255,0.5);
  box-shadow:
    0 0 0 1px rgba(0,0,0,0.03),
    0 4px 6px rgba(0,0,0,0.02),
    0 12px 24px rgba(0,0,0,0.04),
    0 24px 48px rgba(0,0,0,0.04);
}
.lg-card-inner { padding:32px 28px 24px; }
.lg-card-stripe {
  height:3px;
  background:linear-gradient(90deg,#6366F1,#0066FF,#06B6D4,#8B5CF6);
  background-size:200% 100%;
  animation:shimmer 4s linear infinite;
}

.lg-h1 { font-size:22px; font-weight:800; color:#0F172A; margin:0 0 4px; }
.lg-p  { font-size:14px; color:#64748B; margin:0 0 24px; }

.lg-form { display:flex; flex-direction:column; }

.lg-label { font-size:12px; font-weight:600; color:#475569; margin-bottom:5px; margin-top:14px; }
.lg-label:first-of-type { margin-top:0; }

.lg-input-group { position:relative; display:flex; align-items:center; }
.lg-input-icon { position:absolute; left:13px; color:#94A3B8; pointer-events:none; }
.lg-input {
  width:100%; padding:12px 13px 12px 40px;
  font-size:14px; font-family:inherit;
  background:rgba(248,250,252,0.8); border:1.5px solid #E2E8F0;
  border-radius:10px; color:#0F172A; outline:none;
  transition:border-color 0.2s, box-shadow 0.2s, background 0.2s;
}
.lg-input::placeholder { color:#B0B8C4; }
.lg-input:focus {
  border-color:#0066FF; background:#fff;
  box-shadow:0 0 0 3px rgba(0,102,255,0.1), 0 1px 2px rgba(0,0,0,0.04);
}

.lg-err {
  margin-top:14px; color:#DC2626; font-size:13px;
  padding:9px 13px; background:#FEF2F2;
  border:1px solid #FECACA; border-radius:8px;
}

.lg-submit {
  width:100%; padding:13px; margin-top:20px;
  font-size:14px; font-weight:700; font-family:inherit;
  color:#fff; border:none; border-radius:10px; cursor:pointer;
  display:flex; align-items:center; justify-content:center; gap:6px;
  background:linear-gradient(135deg,#4F46E5 0%,#0066FF 50%,#0EA5E9 100%);
  background-size:200% 200%; animation:shimmer 6s linear infinite;
  box-shadow:0 2px 12px rgba(0,102,255,0.25), 0 0 0 1px rgba(0,0,0,0.04);
  transition:transform 0.15s, box-shadow 0.2s;
}
.lg-submit:hover:not(:disabled) {
  transform:translateY(-1px);
  box-shadow:0 4px 20px rgba(79,70,229,0.35), 0 0 0 1px rgba(0,0,0,0.04);
}
.lg-submit:active { transform:translateY(0); }

.lg-footer { font-size:11px; color:#94A3B8; margin-top:24px; letter-spacing:0.3px; }

@media (max-width:480px) {
  .lg-wrapper { padding:0 20px; }
  .lg-card-inner { padding:28px 22px 20px; }
}
`
