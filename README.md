<div align="center">
  <img src="./frontend/public/arise-logo.svg?v=swarm-colors" alt="ARISE" width="320" />
  <h3>Autonomous RFP Intelligence and Sales Engine</h3>
  <p>Transform weeks of pre-sales work into hours with a swarm of 17 specialized AI agents</p>

  ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi)
  ![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react)
  ![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python)
  ![License](https://img.shields.io/badge/License-Proprietary-red?style=flat)
</div>

---

## What ARISE Does

**ARISE** deploys a swarm of 17 specialized AI agents that autonomously read, analyse, scope, price, and draft a complete bid response to any RFP — from raw document to submission-ready proposal.

| Without ARISE | With ARISE |
|---|---|
| 3–6 weeks of manual coordination | 2–8 hours, fully automated |
| Siloed knowledge, lost insights | Institutional memory via RAG |
| Inconsistent pricing and proposals | Rate-card-grounded, validated outputs |
| Manual HITL handoffs | Structured gate approvals with SLA tracking |
| One bid at a time | Parallel pipeline, horizontally scalable |

ARISE is **100% application-agnostic**: bidder identity, rate cards, org structure, and competitor intelligence are injected at runtime — nothing vendor-specific is hardcoded.

---

## Platform Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                           ARISE Platform                              │
│                                                                        │
│  React Frontend (TypeScript + Vite)                                   │
│  ├─ Executive Dashboard    — portfolio metrics, win rate, TCV trend    │
│  ├─ Bid Workspace          — per-bid OODA loop visualizer              │
│  ├─ HITL Gates             — human-in-the-loop approval queue          │
│  ├─ Knowledge Base         — 15-collection RAG-indexed document store  │
│  ├─ Org View               — live org hierarchy with bid metrics       │
│  ├─ Live Telemetry Panel   — real-time agent + LLM performance         │
│  └─ Settings               — rate card, BYOK, org config               │
│                                                                        │
│  FastAPI Backend (Python 3.11+)                                       │
│  ├─ Pipeline Orchestration Engine  — sequential 17-agent swarm         │
│  ├─ HITL Gate Manager             — gate approval, SLA enforcement     │
│  ├─ Strategic LLM Router          — tier-based round-robin pool        │
│  ├─ RAG Pipeline                  — pgvector (prod) / file-cache (dev) │
│  ├─ WebSocket Streaming           — live agent progress + telemetry    │
│  └─ Audit Trail                   — every decision logged and traceable│
│                                                                        │
│  17-Agent Swarm (OODA Loop Architecture)                              │
│  ├─ 01. RFP Intake               ├─ 10. Commercial & Pricing           │
│  ├─ 02. Data Intelligence         ├─ 11. Risk & Compliance             │
│  ├─ 03. Client Intelligence       ├─ 12. Proposal Writer               │
│  ├─ 04. Competitive Intelligence  ├─ 13. Discovery & Clarifications    │
│  ├─ 05. Bid / No-Bid Decision     ├─ 14. Solution Architecture         │
│  ├─ 06. Scope & WBS Builder       ├─ 15. Transition & Change Mgmt      │
│  ├─ 07. AI & Automation Advisory  ├─ 16. QA & Validation               │
│  ├─ 08. Output Generator          └─ 17. Learning & Feedback           │
│  └─ 09. Orchestrator                                                   │
│                                                                        │
│  Data Layer                                                            │
│  ├─ SQLite (dev) / PostgreSQL + pgvector (prod)                       │
│  ├─ Dual-backend RAG Pipeline (auto-selects pgvector when available)  │
│  └─ Institutional Learning Store (cross-bid, cross-agent memory)      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Agent Intelligence Model

Every agent implements an **OODA Loop** (Observe → Orient → Decide → Act):

| Phase | What Happens |
|---|---|
| **Observe** | Reads targeted RFP sections (via semantic indexer), upstream agent outputs, and RAG-retrieved KB context |
| **Orient** | Applies domain reasoning: win themes, risk flags, rate logic, competitive positioning |
| **Decide** | Structured LLM call with JSON output, auto-repair, and hallucination grounding checks |
| **Act** | Persists result to DB; triggers HITL gate if required; captures institutional learnings |

### OODA Inter-Agent Communication

Agents share state through the **bid manifest** — a live document that grows as each agent completes. Downstream agents always read the latest upstream outputs, creating a self-consistent chain of reasoning across the full pipeline.

---

## Strategic LLM Routing

ARISE uses a **tier-based round-robin** pool that supports any OpenAI-compatible API endpoint. Agents declare a cognitive tier — the router distributes load, rotates providers, and auto-fails over on rate limits:

| Tier | Strategy | Assigned Agents |
|---|---|---|
| **critical** | Multi-provider fallback, highest-capability models | BidNoBid, ClientIntel, Commercial, SolutionArch, Proposal, Transition |
| **analytical** | Balanced throughput and reasoning depth | DataAnalyst, CompetitiveIntel, Compliance, QA, Orchestrator |
| **volume** | High-throughput, low-latency endpoints | Intake, ScopeBuilder, AutomationAI, FeedbackLearning |
| **lightweight** | Fast-inference, minimal context | Discovery, OutputGenerator |

**BYOK**: Add your own API keys to `backend/.env`. ARISE automatically discovers configured providers and builds the routing pool at startup. No code changes required.

---

## Knowledge Base & RAG

ARISE maintains a **15-collection Knowledge Base** used for RAG-grounded agent responses:

| Collection | Contents | Purpose |
|---|---|---|
| `rfps/` | Client RFPs | Primary input — never committed to Git |
| `rate_cards/` | Pricing templates | Commercial agent grounding |
| `scope_templates/` | SOW / WBS templates | Scope agent acceleration |
| `clause_library/` | T&C and legal clauses | Compliance agent reference |
| `commercial_models/` | Pricing frameworks | Commercial benchmarking |
| `solution_templates/` | Architecture blueprints | Solution agent starting points |
| `client_profiles/` | Client intelligence | Sensitivity analysis and strategy |
| `brand/` | Brand guidelines | Proposal tone and style |
| `past_bids/` | Won/lost bid archive | Outcome-weighted retrieval (won=1.5x) |

RAG retrieval applies **outcome weighting** (won bids preferred), **recency boost** (+3% for recent docs), and **collection filtering** per agent.

---

## HITL Gates

Five human approval gates interrupt the pipeline at high-stakes decision points:

| Gate | Triggered By | SLA |
|---|---|---|
| `bid_decision` | Bid/No-Bid agent — Go/No-Go recommendation | 24 hours |
| `scope_review` | Scope Builder — WBS, team model, effort | 24 hours |
| `commercial_review` | Commercial agent — rate card, P&L, TCV | 24 hours |
| `legal_compliance` | Compliance agent — risk register, T&C | 48 hours |
| `output_review` | Proposal Writer — full draft proposal | 8 hours |

Approvers receive in-app notifications. Overdue gates are flagged on the dashboard.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- At least one OpenAI-compatible LLM API key (add to `backend/.env`)

### 1. Clone

```bash
git clone https://github.com/Daksh-Aneja-Projects/ARISE_OpenAI_Hackathon.git
cd ARISE_OpenAI_Hackathon
```

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

# Copy and edit your environment file
cp ../.env.example .env
# Edit .env with your API keys and JWT secret

# Create first admin user
python create_user.py

# Start API server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 4. Docker (Full Stack)

```bash
# Full production stack: API + UI + PostgreSQL + Redis + Celery
docker-compose up -d
```

---

## Configuration

Copy `.env.example` to `backend/.env` and configure your environment.

```env
# REQUIRED
JWT_SECRET=<generate: python -c "import secrets; print(secrets.token_hex(32))">

# Add at least one LLM provider API key — see .env.example for all options
```

### Rate Card Defaults

```env
DEFAULT_RATE_ONSHORE_USD=120      # $/hr — overridden by KB upload or user_context
DEFAULT_RATE_NEARSHORE_USD=90
DEFAULT_RATE_OFFSHORE_USD=30
```

**Override priority**: KB uploaded rate card → `user_context` in bid manifest → `.env` defaults.

### Org Chart

```env
# Optional: point to a JSON file to use your own org structure
ORG_CONFIG_FILE=../knowledge_base/org_config.json
```

Copy `knowledge_base/org_config.json.example` → `org_config.json` and edit to match your org.

---

## Pipeline Flow

```
RFP Upload
    │
    ▼
01 RFP Intake ──────────────── extracts fields, sections, deadlines, integrations
    │
    ▼
02 Data Intelligence ────────── user counts, platforms, ERP/CRM inventory
    │
    ▼
03 Client Intelligence ──────── market position, stakeholder map, win strategy
    │
    ▼
04 Competitive Intelligence ─── threat matrix, differentiators, counter-positioning
    │
    ▼
05 Bid / No-Bid Decision ──────  Go/No-Go score, risk-adjusted confidence
    │   [HITL Gate: bid_decision — 24hr SLA]
    ▼
06 Scope & WBS Builder ─────── architecture, effort, resource model, timeline
    │   [HITL Gate: scope_review — 24hr SLA]
    ▼
07 AI & Automation Advisory ─── automation roadmap, ROI, quick wins
    │
    ▼
08 Solution Architecture ─────── AMS/impl design, technology mapping
    │
    ▼
09 Transition & Change Mgmt ─── phases, KT plans, RACI, stakeholder management
    │
    ▼
10 Commercial & Pricing ──────── rate card, P&L model, TCV, risk-adjusted pricing
    │   [HITL Gate: commercial_review — 24hr SLA]
    ▼
11 Risk & Compliance ────────── risk register, T&C scoring, negotiation matrix
    │   [HITL Gate: legal_compliance — 48hr SLA]
    ▼
12 Proposal Writer ───────────── full executive proposal, SOW, cover letter
    │   [HITL Gate: output_review — 8hr SLA]
    ▼
13 Discovery & Clarifications ── gap analysis, client question list
    │
    ▼
14 QA & Validation ───────────── consistency checks, grounding validation
    │
    ▼
15 Output Generator ─────────── DOCX, PPTX, XLSX export package
    │
    ▼
16 Orchestrator ──────────────── swarm coordination, conflict resolution
    │
    ▼
17 Learning & Feedback ─────── institutional knowledge capture, win/loss calibration
    │
    ▼
  SUBMITTED
```

---

## API Reference

Swagger UI: `http://localhost:8000/docs`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/login` | JWT login |
| `GET` | `/api/auth/me` | Current user profile |
| `POST` | `/api/bids/` | Create bid + upload RFP |
| `GET` | `/api/bids/` | List bids (filter, sort, search) |
| `GET` | `/api/bids/{id}` | Full bid with all agent outputs |
| `POST` | `/api/pipeline/{bid_id}/run` | Start 17-agent pipeline |
| `GET` | `/api/pipeline/{bid_id}/status` | Pipeline progress |
| `POST` | `/api/pipeline/{bid_id}/cancel` | Cancel running pipeline |
| `POST` | `/api/knowledge/upload` | Upload KB document |
| `GET` | `/api/knowledge/documents` | List KB documents |
| `GET` | `/api/hitl/` | List HITL gates (filter by status) |
| `POST` | `/api/hitl/{id}/decide` | Approve / reject gate |
| `GET` | `/api/dashboard/exec` | Executive metrics |
| `GET` | `/api/org/tree` | Live org hierarchy |
| `GET` | `/api/health` | System health |
| `GET` | `/api/health/llm` | LLM pool + tier status |
| `WS` | `/api/ws/pipeline/{bid_id}` | Real-time pipeline stream |
| `WS` | `/api/ws/telemetry` | Live backend telemetry (1s) |

---

## Project Structure

```
ARISE/
├── backend/
│   ├── app/
│   │   ├── agents/          # 17 specialized agents (OODA loop each)
│   │   ├── api/             # FastAPI route modules + health + WS
│   │   ├── document_gen/    # DOCX, PPTX, XLSX generators
│   │   ├── knowledge/       # RAG pipeline, embeddings, indexer
│   │   ├── orchestration/   # Pipeline engine, HITL manager
│   │   ├── services/        # Auth, LLM tier router, bid repository
│   │   └── tasks/           # Celery agent tasks (horizontal scaling)
│   ├── alembic/             # Database migrations
│   └── .env                 # ← NOT committed to Git
│
├── frontend/
│   ├── src/
│   │   ├── components/      # Agent output renderers, TelemetryPanel
│   │   ├── hooks/           # useReliableWebSocket (backoff + keepalive)
│   │   └── pages/           # Dashboard, BidDetail, KB, HITL, Org
│   └── public/
│       ├── arise-logo.svg   # ARISE brand logo
│       └── arise-mark.svg   # Icon mark (favicon)
│
├── knowledge_base/          # ← NOT committed to Git (client data)
│   ├── rfps/                #   Client RFP documents
│   ├── outputs/             #   Generated proposals
│   └── org_config.json.example
│
├── .github/
│   ├── workflows/           # CI (lint, test) + Security (Trivy, CodeQL)
│   ├── ISSUE_TEMPLATE/      # Bug report + feature request templates
│   └── PULL_REQUEST_TEMPLATE.md
│
├── docker-compose.yml       # Full stack: API + UI + PostgreSQL + Redis
├── CONTRIBUTING.md
├── SECURITY.md
├── .env.example             # Safe template — commit this, not .env
└── README.md
```

---

## Security

- **JWT Auth** — bcrypt hashing, configurable expiry (default 24hr)
- **RBAC** — 9 roles with scoped permissions across the bid lifecycle
- **Data isolation** — all RFPs and outputs are local-only, never in Git
- **Zero hardcoded secrets** — all credentials via `.env`, blocked by `.gitignore`
- **Admin-only destructive ops** — `DELETE /api/bids/clear-all` requires `admin` role
- **Audit trail** — every agent completion, HITL decision, and login is logged

See [SECURITY.md](SECURITY.md) for responsible disclosure and full security architecture.

---

## Adding a New Agent

1. Create `backend/app/agents/my_agent.py` extending `BaseAgent`
2. Set `agent_tier = "critical" | "analytical" | "volume" | "lightweight"`
3. Implement `observe()`, `orient()`, `decide()`, `act()` (OODA loop)
4. Register in `backend/app/api/pipeline.py` → `PIPELINE_STAGES`
5. Add agent runner in `backend/app/api/bids.py` → `_execute_agent()`
6. Add renderer in `frontend/src/components/AgentRenderers.tsx`

---

## Roadmap

- [x] WebSocket streaming for real-time agent progress
- [x] pgvector integration for persistent RAG embeddings
- [x] Celery worker integration for horizontal agent scaling
- [x] Server-side WS keepalive (prevents silent NAT drops)
- [x] Strategic tier-based round-robin LLM routing
- [x] Institutional learning store (cross-bid memory)
- [x] HITL gate manager with SLA enforcement
- [x] Export hub: DOCX / PPTX / XLSX
- [x] Live telemetry dashboard (WebSocket, 1s granularity)
- [ ] Salesforce CRM sync
- [ ] SharePoint document library connector
- [ ] Multi-tenant organization support
- [ ] Win/loss auto-calibration feedback loop

---

## License

Proprietary — All rights reserved.

Built for the **OpenAI Hackathon** · © 2026 ARISE Project
