# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x (latest) | ✅ Active support |
| < 1.0 | ❌ No longer supported |

---

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through GitHub Issues.**

### Responsible Disclosure

If you discover a security vulnerability in ARISE, please report it privately:

1. **Email:** security@arise.internal *(replace with your org's security email)*
2. **Subject line:** `[ARISE SECURITY] <brief description>`
3. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Any suggested mitigations

We will acknowledge receipt within **48 hours** and provide a timeline for remediation within **5 business days**.

### What to Report

- Authentication/authorization bypasses
- API key or secret exposure
- SQL injection or data exfiltration risks
- Cross-site scripting (XSS) in the frontend
- Insecure deserialization
- Privilege escalation via RBAC bypass
- WebSocket stream hijacking
- Agent prompt injection leading to data leakage

### What NOT to Report

- Theoretical attacks with no practical exploit path
- Issues in dependencies that have already been patched upstream
- Social engineering attacks

---

## Security Architecture

ARISE implements the following security controls:

| Control | Implementation |
|---------|---------------|
| **Authentication** | JWT (RS256 configurable), bcrypt password hashing |
| **Authorization** | RBAC with 9 roles, per-endpoint enforcement |
| **Secrets Management** | All keys via `.env`, blocked by `.gitignore`, never logged |
| **Data Isolation** | Client RFP data is local-only, never committed to Git |
| **Rate Limiting** | Per-user API rate limiter on pipeline endpoints |
| **Input Validation** | Pydantic v2 schemas on all API inputs |
| **Audit Logging** | Full audit trail of all pipeline and HITL actions |
| **TLS** | All external LLM provider calls use HTTPS |
| **Container Security** | Non-root user in all Docker images |
| **Dependency Scanning** | Automated via GitHub Actions (weekly) |

---

## Known Limitations (Current Version)

- JWT secret is symmetric (HMAC-SHA256) — rotate via `JWT_SECRET_KEY` in `.env`
- SQLite mode (dev) does not enforce row-level security — use PostgreSQL for production
- LLM prompt injection is mitigated by structured output validation but not fully prevented
