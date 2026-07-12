const API_BASE = '/api';

const MAX_RETRIES = 3;
const RETRY_STATUS_CODES = [429, 503];

async function request(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = { ...(options.headers as Record<string, string> || {}) };
  if (!options.body || !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let lastError: Error | null = null;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

      if (res.ok) return res.json();

      // Retry on transient errors (429, 503)
      if (RETRY_STATUS_CODES.includes(res.status) && attempt < MAX_RETRIES) {
        const delay = Math.pow(2, attempt) * 1000; // 1s, 2s, 4s
        await new Promise(r => setTimeout(r, delay));
        continue;
      }

      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Request failed');
    } catch (e) {
      lastError = e as Error;
      if (attempt < MAX_RETRIES && !(e as Error).message?.includes('Request failed')) {
        const delay = Math.pow(2, attempt) * 1000;
        await new Promise(r => setTimeout(r, delay));
        continue;
      }
      throw e;
    }
  }
  throw lastError || new Error('Request failed after retries');
}

export const api = {
  // Generic helper used by components
  post: (path: string, body?: unknown) =>
    request(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  // Auth
  login: (email: string, password: string) => request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  getMe: () => request('/auth/me'),
  getUsers: () => request('/auth/users'),

  // Bids
  getBids: (params?: { status?: string; search?: string; industry?: string; contract_type?: string; sort_by?: string; sort_order?: string }) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => { if (v) sp.set(k, v); });
    }
    const qs = sp.toString();
    return request(`/bids/${qs ? `?${qs}` : ''}`);
  },
  getBidStats: () => request('/bids/stats'),
  getBid: (id: string) => request(`/bids/${id}`),
  createBid: (data: Record<string, unknown>) => request('/bids/', { method: 'POST', body: JSON.stringify(data) }),
  updateBid: (id: string, data: Record<string, unknown>) => request(`/bids/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  updateBidStatus: (id: string, status: string) => request(`/bids/${id}/status?status=${status}`, { method: 'PATCH' }),
  cloneBid: (id: string) => request(`/bids/${id}/clone`, { method: 'POST' }),
  deleteBid: (id: string) => request(`/bids/${id}`, { method: 'DELETE' }),
  clearAllBids: () => request('/bids/clear-all', { method: 'DELETE' }),
  runAgent: (bidId: string, agentName: string) => request(`/bids/${bidId}/run-agent/${agentName}`, { method: 'POST' }),
  getAgentOutputs: (bidId: string) => request(`/bids/${bidId}/agent-outputs`),
  getAgentOutput: (bidId: string, agentName: string) => request(`/bids/${bidId}/agent-output/${agentName}`),
  saveDiscoveryAnswers: (bidId: string, answers: Array<{question: string; category: string; answer: string}>) => request(`/bids/${bidId}/discovery-answers`, { method: 'POST', body: JSON.stringify({ answers }) }),
  getDiscoveryAnswers: (bidId: string) => request(`/bids/${bidId}/discovery-answers`),

  getPendingGates: () => {
    const sp = new URLSearchParams()
    sp.set('status', 'pending')
    return request(`/hitl/?${sp.toString()}`)
  },
  // HITL Gates
  getGates: (status?: string, bidId?: string) => {
    const sp = new URLSearchParams();
    if (status && status !== 'all') sp.set('status', status);
    if (bidId) sp.set('bid_id', bidId);
    const qs = sp.toString();
    return request(`/hitl/${qs ? `?${qs}` : ''}`);
  },
  decideGate: (gateId: string, decision: string, comments: string) =>
    request(`/hitl/${gateId}/decide`, { method: 'POST', body: JSON.stringify({ decision, comments }) }),
  createGate: (data: Record<string, unknown>) => request('/hitl/', { method: 'POST', body: JSON.stringify(data) }),

  // Documents
  uploadBidDocument: async (bidId: string, file: File, documentType: string = 'rfp') => {
    const fd = new FormData();
    fd.append('files', file);
    fd.append('document_type', documentType);
    const token = localStorage.getItem('token');
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}/bids/${bidId}/documents`, { method: 'POST', body: fd, headers });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  },
  getDocuments: (bidId?: string) => request(`/documents/${bidId ? `?bid_id=${bidId}` : ''}`),

  // Knowledge Base
  getCollections: () => request('/knowledge/collections'),
  getKBDocuments: (collection?: string) => request(`/knowledge/documents${collection ? `?collection=${collection}` : ''}`),
  deleteKBDocument: (id: string) => request(`/knowledge/${id}`, { method: 'DELETE' }),
  uploadKBDocument: async (file: File, collection: string, metadata: Record<string, string> = {}) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('collection', collection);
    Object.entries(metadata).forEach(([k, v]) => fd.append(k, v));
    const token = localStorage.getItem('token');
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}/knowledge/upload`, { method: 'POST', body: fd, headers });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  },

  // Executive Dashboard
  getExecutiveDashboard: () => request('/dashboard/executive'),
  getTimeline: (bidId?: string) => request(`/dashboard/timeline${bidId ? `?bid_id=${bidId}` : ''}`),

  // Audit Trail
  getAuditLogs: (params?: { bid_id?: string; event_type?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => { if (v !== undefined) sp.set(k, String(v)); });
    }
    const qs = sp.toString();
    return request(`/audit/${qs ? `?${qs}` : ''}`);
  },
  getBidAuditTrail: (bidId: string) => request(`/audit/${bidId}`),

  // Document Generation — Word, PPT, Excel
  generateSOW: (bidId: string) => request(`/generate/${bidId}/sow`, { method: 'POST' }),
  generatePPT: (bidId: string) => request(`/generate/${bidId}/ppt`, { method: 'POST' }),
  generateExcel: (bidId: string) => request(`/generate/${bidId}/excel`, { method: 'POST' }),
  getGeneratedDocs: (bidId: string) => request(`/generate/${bidId}/generated`),
  getDownloadUrl: (docId: string) => `/api/generate/download/${docId}`,

  // Pipeline
  startPipeline: (bidId: string) => request(`/pipeline/${bidId}/run`, { method: 'POST' }),
  cancelPipeline: (bidId: string) => request(`/pipeline/${bidId}/cancel`, { method: 'POST' }),
  getPipelineStatus: (bidId: string) => request(`/pipeline/${bidId}/status`),

  // Org Structure
  getOrgTree: () => request('/org/tree'),
  getOrgNodes: () => request('/org/nodes'),
  getOrgMetrics: (nodeId: string) => request(`/org/${nodeId}/metrics`),

  // AI Engine Pool — sanitized, no model/provider names
  getLLMStatus: () => request('/health/llm'),
  setBYOK: (data: { openai_api_key?: string; }) =>
    request('/settings/byok', { method: 'POST', body: JSON.stringify(data) }),
  clearBYOK: () => request('/settings/byok/clear', { method: 'POST' }),
  testLLM: () => request('/settings/byok/test', { method: 'POST' }),

  // Knowledge Base / RAG stats
  getKnowledgeStats: () => request('/knowledge/stats'),
};
