# Security Rules

## Secrets & Credentials

- **Never commit `.env`** or any file containing a real key, token, or password.
- `.env.template` must contain placeholders only — reviewed before every commit.
- Rotate any key that was ever committed, even briefly, even in a private repo.
- Load secrets from environment variables only. No hardcoded credentials anywhere in `src/`.
- B2 backup credentials have write access — treat them with the same care as DB passwords.

## API Authentication

- Every FastAPI endpoint requires `Depends(get_current_user)` unless explicitly marked public.
- JWT tokens: HS256, `JWT_SECRET` from env, expiry ≤24h for access tokens.
- Passwords stored as bcrypt hashes only. Never log, return, or compare plaintext passwords.
- Single admin user in v1 — no user registration endpoint. Keep attack surface minimal.

## Input Validation & Prompt Injection

- Sanitise all user-supplied text before it reaches any LLM prompt.
- The `guardrails` node runs **before** any LLM call in the graph — do not bypass it.
- Validate with Pydantic at every API boundary. Reject malformed input with 422, not 500.
- Never interpolate raw user input directly into SQL. Use SQLAlchemy parameterised queries only.
- Strip and length-limit topic/content fields before storing or passing downstream.

## Rate Limiting

- All public API routes use `slowapi` rate limiting (configured in `api/middleware.py`).
- Default: 10 requests/minute per IP for agent-trigger endpoints.
- Auth endpoints: 5 attempts/minute per IP to prevent brute-force.

## LinkedIn & ToS

- **No auto-connection-request code** — LinkedIn ToS violation. Reject any PR containing it.
- PostBoost API key is scoped to publish only. Do not request broader OAuth scopes.
- Never store LinkedIn member IDs or profile data beyond what PostBoost returns.

## Dependencies

- Pin all dependencies in `uv.lock`. Do not allow unpinned ranges in `pyproject.toml` for production deps.
- Run `uv audit` before every release to check for known CVEs.
- Do not add dependencies for single-function use cases — implement the small utility instead.

## Database

- DB credentials in `DATABASE_URL` env var only.
- Alembic migrations reviewed manually before applying to production.
- `pg_dump` nightly to Backblaze B2 (configured in Day 10). Verify restore works before relying on it.
- Dev DB (`docker compose`) uses a different password than production. Never share credentials between environments.

## CI / Deployment

- CI runs `pytest tests/security/` on every PR.
- Cloudflare Tunnel is the only public ingress — no ports exposed directly.
- Caddy handles TLS termination. Do not bypass it for "local testing" on the production server.
