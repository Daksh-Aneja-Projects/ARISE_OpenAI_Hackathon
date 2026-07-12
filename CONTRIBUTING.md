## Contributing to ARISE

Thank you for your interest in contributing to **ARISE — Autonomous RFP Intelligence and Sales Engine**.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Branch Strategy](#branch-strategy)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Security Requirements](#security-requirements)
- [Adding or Modifying Agents](#adding-or-modifying-agents)
- [Testing](#testing)

---

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). All contributors must adhere to it.

---

## Getting Started

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/YOUR_ORG/arise.git`
3. Set up the development environment (see below)
4. **Create a feature branch** from `develop`
5. Make your changes and open a Pull Request

---

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose
- PostgreSQL 16 (or use `docker compose up postgres`)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copy example env and fill in your API keys
cp ../.env.example .env
# Edit .env with your API keys

# Run database migrations
alembic upgrade head

# Start the API
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Full Stack (Docker)

```bash
docker compose up -d
```

---

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code only. Protected. |
| `develop` | Integration branch — all PRs merge here first |
| `feat/xxx` | New features |
| `fix/xxx` | Bug fixes |
| `hotfix/xxx` | Production emergency fixes |
| `chore/xxx` | Maintenance, deps, refactor |

**Never commit directly to `main` or `develop`.**

---

## Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

**Types:** `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`, `perf`, `security`

**Examples:**
```
feat(agents): add vision analysis to intake agent
fix(pipeline): handle WebSocket disconnect during stage 3
security(auth): rotate JWT secret rotation support
docs(readme): update architecture diagram
```

---

## Pull Request Process

1. Ensure CI passes (TypeScript, ESLint, pytest)
2. Fill out the [PR template](.github/PULL_REQUEST_TEMPLATE.md) completely
3. Request review from at least **one** code owner
4. PRs must be reviewed and approved before merging
5. Squash-merge into `develop`; rebase-merge `develop` → `main` for releases

---

## Security Requirements

> **These are non-negotiable for every contribution.**

- ❌ **No API keys, tokens, or credentials** in code or commits
- ❌ **No client RFP documents, proposals, or PII** in any file
- ❌ **No hardcoded client names or bid data** in tests
- ✅ Use `.env` for all secrets — see `.env.example` for the template
- ✅ Add any new secrets to `.gitignore` before using them
- ✅ Run `gitleaks detect` before pushing if you handle credentials

If you discover a security vulnerability, see [SECURITY.md](SECURITY.md).

---

## Adding or Modifying Agents

ARISE uses a 12-stage OODA pipeline. Agents live in `backend/app/agents/`.

### Agent Contract

Every agent must:
1. Inherit from `BaseAgent` (`backend/app/agents/base.py`)
2. Implement `async def run(self) -> dict`
3. Return a dict with at minimum: `{"status": "success"|"error", "result": {...}}`
4. Use `self.llm.generate_structured(...)` for JSON outputs
5. Document the `provider` preference in the docstring

### HITL Gate

To add a HITL gate after a stage, set `"gate": True` in the stage definition inside `pipeline.py` and implement `build_gate_payload()` for it.

---

## Testing

```bash
# Backend
cd backend
pytest tests/ -v

# Frontend (TypeScript)
cd frontend
npx tsc --noEmit

# Frontend (ESLint)
npx eslint src/
```

Add tests for:
- New API endpoints: `backend/tests/api/`
- New agent logic: `backend/tests/agents/`
- New frontend components: use Vitest (component tests)
