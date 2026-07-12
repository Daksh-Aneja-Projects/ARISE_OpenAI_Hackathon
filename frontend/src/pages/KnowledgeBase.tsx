import { useState, useEffect, useRef } from 'react'
import { api } from '../api'
import { Upload, Search, Trash2, FileText, Database, Filter } from 'lucide-react'

interface Collection { id: string; name: string; desc: string; count: number }
interface Doc { id: string; collection: string; filename: string; file_type: string; file_size: number; product: string; engagement_type: string; client_industry: string; outcome: string | null; version: number; uploaded_by: string; uploaded_at: string }

export default function KnowledgeBase() {
  const [collections, setCollections] = useState<Collection[]>([])
  const [documents, setDocuments] = useState<Doc[]>([])
  const [activeCollection, setActiveCollection] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [showUpload, setShowUpload] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  const fetchData = async (col?: string) => {
    setLoading(true)
    try {
      const [c, d] = await Promise.all([api.getCollections(), api.getKBDocuments(col || undefined)])
      setCollections(c); setDocuments(d)
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [])

  const selectCollection = (id: string) => {
    const next = activeCollection === id ? '' : id
    setActiveCollection(next)
    fetchData(next || undefined)
  }

  const deleteDoc = async (id: string) => {
    if (!confirm('Delete this document?')) return
    try { await api.deleteKBDocument(id); fetchData(activeCollection || undefined) } catch (e) { console.error(e) }
  }

  const filtered = documents.filter(d => !searchTerm || d.filename.toLowerCase().includes(searchTerm.toLowerCase()) || d.product?.toLowerCase().includes(searchTerm.toLowerCase()))

  return (
    <div>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:24 }}>
        <div>
          <h2 style={{ fontSize:24, fontWeight:800 }}>Knowledge Base</h2>
          <p style={{ color:'var(--text-muted)', fontSize:13, marginTop:4 }}>14 collections  {documents.length} documents  RAG-enabled semantic search</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowUpload(true)}><Upload size={14} /> Upload Document</button>
      </div>

      {/* Collections grid */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(200px, 1fr))', gap:10, marginBottom:24 }}>
        {collections.map(c => (
          <button key={c.id} onClick={() => selectCollection(c.id)}
            style={{ textAlign:'left', padding:'14px 16px', background: activeCollection === c.id ? 'rgba(0,102,255,0.1)' : 'var(--bg-card)',
              border: `1px solid ${activeCollection === c.id ? 'var(--border-accent)' : 'var(--border-subtle)'}`,
              borderRadius:'var(--radius-md)', cursor:'pointer', transition:'all 150ms', color:'var(--text-primary)' }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
              <span style={{ fontSize:13, fontWeight:600 }}>{c.name}</span>
              <span style={{ fontSize:11, color:'var(--text-muted)', fontFamily:'var(--font-mono)' }}>{c.count}</span>
            </div>
            <div style={{ fontSize:11, color:'var(--text-muted)', marginTop:4 }}>{c.desc}</div>
          </button>
        ))}
      </div>

      {/* Search */}
      <div style={{ position:'relative', marginBottom:16 }}>
        <Search size={16} style={{ position:'absolute', left:12, top:11, color:'var(--text-muted)' }} />
        <input className="form-input" style={{ paddingLeft:36 }} value={searchTerm} onChange={e => setSearchTerm(e.target.value)} placeholder="Search documents..." />
      </div>

      {/* Documents table */}
      {loading ? <div className="loading-page"><div className="loading-spinner" /></div> : (
        <div className="glass-card" style={{ padding:0, overflow:'hidden' }}>
          <table className="data-table">
            <thead>
              <tr><th>Document</th><th>Collection</th><th>Product</th><th>Type</th><th>Outcome</th><th>Uploaded</th><th></th></tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={7} style={{ textAlign:'center', padding:40, color:'var(--text-muted)' }}>No documents found</td></tr>
              ) : filtered.map(d => (
                <tr key={d.id}>
                  <td><div style={{ display:'flex', alignItems:'center', gap:8 }}><FileText size={14} style={{ color:'var(--text-accent)', flexShrink:0 }} /><span style={{ fontWeight:500 }}>{d.filename}</span></div></td>
                  <td><span className="bid-tag type">{d.collection}</span></td>
                  <td style={{ color:'var(--text-secondary)' }}>{d.product || ''}</td>
                  <td style={{ color:'var(--text-muted)' }}>{d.engagement_type || ''}</td>
                  <td>{d.outcome ? <span className={`status-badge ${d.outcome === 'Won' ? 'low' : d.outcome === 'Lost' ? 'high' : 'medium'}`}>{d.outcome}</span> : ''}</td>
                  <td style={{ fontSize:12, color:'var(--text-muted)' }}>{d.uploaded_by}</td>
                  <td><button onClick={() => deleteDoc(d.id)} style={{ background:'none', border:'none', color:'var(--text-muted)', cursor:'pointer', padding:4 }}><Trash2 size={14} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} onUploaded={() => { setShowUpload(false); fetchData(activeCollection || undefined) }} collections={collections} />}
    </div>
  )
}

function UploadModal({ onClose, onUploaded, collections }: { onClose: () => void; onUploaded: () => void; collections: Collection[] }) {
  const [file, setFile] = useState<File | null>(null)
  const [collection, setCollection] = useState('')
  const [product, setProduct] = useState('')
  const [engType, setEngType] = useState('')
  const [industry, setIndustry] = useState('')
  const [outcome, setOutcome] = useState('')
  const [uploading, setUploading] = useState(false)
  const [dragover, setDragover] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  // Embedding progress state
  const [embedStatus, setEmbedStatus] = useState<string>('')
  const [embedTotal, setEmbedTotal] = useState(0)
  const [embedProcessed, setEmbedProcessed] = useState(0)

  const handleDrop = (e: React.DragEvent) => { e.preventDefault(); setDragover(false); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]) }

  const trackEmbeddingProgress = (jobId: string) => {
    setEmbedStatus('connecting')
    const token = localStorage.getItem('token')
    const url = `/api/knowledge/embed/progress/${jobId}`
    const eventSource = new EventSource(url)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setEmbedStatus(data.status || 'unknown')
        setEmbedTotal(data.total || 0)
        setEmbedProcessed(data.processed || 0)

        if (['completed', 'failed', 'skipped', 'not_found'].includes(data.status)) {
          eventSource.close()
          if (data.status === 'completed') {
            setTimeout(() => onUploaded(), 1200)
          }
        }
      } catch (err) {
        console.error('SSE parse error:', err)
      }
    }

    eventSource.onerror = () => {
      setEmbedStatus('connection_error')
      eventSource.close()
    }
  }

  const submit = async () => {
    if (!file || !collection) return
    setUploading(true)
    setEmbedStatus('')
    try {
      const fd = new FormData()
      fd.append('file', file); fd.append('collection', collection)
      fd.append('product', product); fd.append('engagement_type', engType)
      fd.append('client_industry', industry); fd.append('outcome', outcome)
      const token = localStorage.getItem('token')
      const resp = await fetch('/api/knowledge/upload', { method: 'POST', body: fd, headers: token ? { 'Authorization': `Bearer ${token}` } : {} })
      const result = await resp.json()

      if (result.embedding_job_id) {
        trackEmbeddingProgress(result.embedding_job_id)
      } else {
        onUploaded()
      }
    } catch (e) { console.error(e); setUploading(false) }
  }

  const embedProgress = embedTotal > 0 ? Math.round((embedProcessed / embedTotal) * 100) : 0

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth:520 }}>
        <div className="modal-header"><h2 className="modal-title">Upload to Knowledge Base</h2><button className="modal-close" onClick={onClose}>-</button></div>
        <div className={`upload-zone ${dragover ? 'dragover' : ''}`}
          onClick={() => fileRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setDragover(true) }}
          onDragLeave={() => setDragover(false)}
          onDrop={handleDrop}>
          <input ref={fileRef} type="file" hidden onChange={e => { if (e.target.files?.[0]) setFile(e.target.files[0]) }} />
          {file ? <div style={{ fontSize:14 }}> {file.name} <span style={{ color:'var(--text-muted)' }}>({(file.size/1024).toFixed(0)} KB)</span></div>
            : <><div className="upload-icon"></div><div className="upload-text">Drop file here or click to browse</div><div className="upload-hint">PDF, DOCX, XLSX, MD, CSV</div></>}
        </div>
        <div className="form-group" style={{ marginTop:16 }}>
          <label className="form-label">Collection *</label>
          <select className="form-select" value={collection} onChange={e => setCollection(e.target.value)}>
            <option value="">Select collection</option>
            {collections.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 }}>
          <div className="form-group"><label className="form-label">Product</label><input className="form-input" value={product} onChange={e => setProduct(e.target.value)} placeholder="e.g. SAP, Workday, AWS" /></div>
          <div className="form-group"><label className="form-label">Engagement Type</label>
            <select className="form-select" value={engType} onChange={e => setEngType(e.target.value)}><option value="">Select</option><option value="AMS">AMS</option><option value="Implementation">Implementation</option><option value="Hybrid">Hybrid</option></select>
          </div>
          <div className="form-group"><label className="form-label">Industry</label><input className="form-input" value={industry} onChange={e => setIndustry(e.target.value)} placeholder="e.g. Financial Services" /></div>
          <div className="form-group"><label className="form-label">Outcome</label>
            <select className="form-select" value={outcome} onChange={e => setOutcome(e.target.value)}><option value="">N/A</option><option value="Won">Won</option><option value="Lost">Lost</option><option value="Pending">Pending</option></select>
          </div>
        </div>

        {/* Live Embedding Progress */}
        {embedStatus && embedStatus !== '' && (
          <div style={{ marginTop:16, padding:'12px 16px', background:'rgba(0,102,255,0.06)', borderRadius:'var(--radius-md)', border:'1px solid var(--border-subtle)' }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8 }}>
              <span style={{ fontSize:12, fontWeight:600, color:'var(--text-primary)' }}>
                {embedStatus === 'pending' && ' Queued for vectorization...'}
                {embedStatus === 'connecting' && '- Connecting to embedding engine...'}
                {embedStatus === 'processing' && ` Vectorizing chunks: ${embedProcessed}/${embedTotal}`}
                {embedStatus === 'completed' && ` Vectorization complete  ${embedTotal} chunks indexed`}
                {embedStatus === 'failed' && ' Embedding failed'}
                {embedStatus === 'skipped' && ' No text content to vectorize'}
                {embedStatus === 'connection_error' && ' Lost connection to embedding engine'}
              </span>
              {embedStatus === 'processing' && (
                <span style={{ fontSize:11, fontFamily:'var(--font-mono)', color:'var(--text-muted)' }}>{embedProgress}%</span>
              )}
            </div>
            {(embedStatus === 'processing' || embedStatus === 'completed') && (
              <div style={{ width:'100%', height:6, background:'rgba(0,0,0,0.08)', borderRadius:3, overflow:'hidden' }}>
                <div style={{
                  width: `${embedStatus === 'completed' ? 100 : embedProgress}%`,
                  height:'100%',
                  background: embedStatus === 'completed' ? '#34C759' : 'var(--text-accent)',
                  borderRadius:3,
                  transition:'width 300ms ease'
                }} />
              </div>
            )}
          </div>
        )}

        <div style={{ display:'flex', gap:10, justifyContent:'flex-end', marginTop:16 }}>
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" disabled={!file || !collection || uploading} onClick={submit}>{uploading ? (embedStatus === 'processing' ? 'Vectorizing...' : 'Uploading...') : 'Upload'}</button>
        </div>
      </div>
    </div>
  )
}
