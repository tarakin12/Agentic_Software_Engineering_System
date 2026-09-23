# Architecture — URL Shortener Service

**Run:** RUN-20260922175531
**Input:** `.agentic/context/normalized-requirement.json`
**Status:** DRAFT → see `## Architecture Validation` at bottom for gate result.

---

## 1. Architecture Overview

A layered, single-process FastAPI application backed by SQLite, structured
so that each layer can be independently replaced during production
evolution without touching the others.

```
Client
  │  HTTP
  ▼
FastAPI API layer            (generated/url_shortener/app/api/)
  │  calls
  ▼
URL Service (business logic) (generated/url_shortener/app/services/)
  │  calls
  ▼
Repository (persistence I/O) (generated/url_shortener/app/repositories/)
  │  reads/writes
  ▼
SQLite database               (generated/url_shortener/data/url_shortener.db)

Redirect event
  │
  ▼
Analytics component            (generated/url_shortener/app/analytics/)
  │  writes via Repository
  ▼
SQLite (redirect_events table)
```

**Rationale for FastAPI + SQLite (not a "fashionable" choice):** FastAPI
gives typed request/response validation (directly satisfies AC-002's 422
error requirement) with minimal boilerplate; SQLite requires zero external
infrastructure, satisfying the "no external database" constraint while
still being a real, durable, file-backed relational store — appropriate
for a ~20-hour prototype whose job is to *demonstrate* sound architecture,
not to *be* a production deployment.

---

## 2. Components

| Component | Responsibility |
|---|---|
| `api/urls.py` | HTTP routing, request validation, status-code mapping. No business logic. |
| `api/redirect.py` | Redirect route (`GET /{short_code}`). |
| `services/url_service.py` | Idempotent creation logic, short-code generation, expiration checks. |
| `repositories/url_repository.py` | All SQL for the `urls` table. |
| `repositories/analytics_repository.py` | All SQL for the `redirect_events` table and aggregate reads. |
| `models/url.py` | Pydantic request/response schemas + internal dataclass/row mapping. |
| `analytics/analytics_service.py` | Records a redirect event and computes aggregate analytics. |
| `main.py` | FastAPI app assembly, dependency wiring, DB initialization. |

This separation directly satisfies AC-009 (layered code) and NFR-002.

---

## 3. Request Flow

### Create short URL — `POST /urls`
1. API layer validates `url` is a well-formed http(s) URL (Pydantic `AnyHttpUrl`) → else 422 (AC-002).
2. Service checks repository for an existing, non-expired mapping for that `original_url` (ASM-005) → if found, return existing code with 200 (AC-003).
3. Otherwise, service generates a random 7-char base62 `short_code`, retries generation on the rare collision (checked via repository uniqueness), and asks repository to insert a new row.
4. API layer returns 201 with `{short_code, short_url}` (AC-001).

### Redirect — `GET /{short_code}`
1. API layer asks service to resolve the code.
2. Service asks repository for the row → not found → 404 (AC-005).
3. If found and `expires_at` is in the past → 410 Gone (AC-006), no redirect performed.
4. Otherwise: service asks Analytics component to record the redirect event
   and increment `redirect_count` / update `last_accessed_at`
   (AC-008), then API layer issues a 302 redirect to `original_url` (AC-004).

### Analytics — `GET /urls/{short_code}/analytics`
1. API layer asks service/repository for the row → not found → 404.
2. Otherwise returns `{short_code, original_url, created_at, redirect_count, last_accessed_at}` (AC-007).

---

## 4. Data Flow

```
POST /urls ──▶ url_service.create_short_url() ──▶ url_repository.find_by_original_url()
                                               └─▶ url_repository.insert()

GET /{code} ──▶ url_service.resolve() ──▶ url_repository.find_by_code()
                                       └─▶ analytics_service.record_redirect()
                                              └─▶ analytics_repository.increment_and_log()

GET /urls/{code}/analytics ──▶ url_service.get_analytics() ──▶ url_repository.find_by_code()
```

---

## 5. API Boundaries

| Method | Path | Purpose | Success | Failure |
|---|---|---|---|---|
| POST | `/urls` | Create (or reuse) a short URL | 201 / 200 | 422 invalid URL |
| GET | `/{short_code}` | Redirect to original URL | 302 | 404 unknown, 410 expired |
| GET | `/urls/{short_code}/analytics` | Retrieve analytics | 200 | 404 unknown |

This is the full and exact surface implemented — see `artifacts/openapi.yaml`
(Phase 5), which must match this table exactly (validated mechanically by
`.agentic/tools/validate_artifacts.py openapi`).

---

## 6. Persistence Design

Two tables (see `artifacts/schema.sql`, Phase 5):

- **`urls`**: `id, short_code (UNIQUE, indexed), original_url (indexed), created_at, expires_at (nullable), redirect_count, last_accessed_at`.
  - `short_code` is indexed (and UNIQUE) because every redirect and
    analytics lookup keys off it — this is the hottest read path.
  - `original_url` is indexed to support the idempotent-creation lookup
    (AC-003) in O(log n) rather than a full scan.
- **`redirect_events`**: `id, short_code (indexed, FK-by-value), accessed_at`.
  - Kept separate from `urls` (rather than only an in-row counter) so that
    per-event history exists for future trend analytics (e.g., redirects
    per day) without redesigning the schema later — a deliberate trade-off
    of slightly more write volume for materially better analytics
    extensibility.

---

## 7. Scalability

**Prototype reality:** single SQLite file, single process — this is a
**documented, deliberate scope limit**, not an oversight (see NFR-004).

**Evolution path (not implemented in this prototype):**

```
Client
  ▼
Load Balancer
  ▼
Stateless FastAPI instances (N replicas, no local state)
  ▼
Redis (short_code → original_url cache, absorbs read-hot-path load)
  ▼
PostgreSQL (replaces SQLite; supports concurrent writers, replicas)

Redirect event
  ▼
Message broker (e.g., Kafka/SQS)
  ▼
Asynchronous analytics workers (batch aggregation, decoupled from redirect latency)
```

Rationale: the redirect path is overwhelmingly read-heavy and latency
sensitive; caching + read replicas address that. Analytics writes are
not latency-sensitive to the client, so they are the natural candidate to
move off the synchronous request path first via a broker.

---

## 8. Reliability

- All repository calls are wrapped so DB errors surface as 500 with a
  generic error body (never leak SQL/internals).
- SQLite `PRAGMA foreign_keys` and WAL journal mode enabled for safer
  concurrent read/write within a single process.
- Short-code collision handled by regeneration-with-retry (bounded to a
  small number of attempts) rather than crashing.

---

## 9. Security

- Input URLs are validated as well-formed http(s) URLs by Pydantic before
  any string is used in a query (parameterized SQL throughout — no string
  interpolation into SQL — mitigates injection).
- Redirects only ever target the exact `original_url` stored at creation
  time (no open-redirect-via-user-supplied-target-at-redirect-time risk,
  since the redirect target is not a query parameter at redirect time).
- No authentication is implemented (ASM-002) — flagged as a known
  limitation, not silently ignored.
- No secrets/credentials are used anywhere (no external LLM API, no API
  keys), consistent with the global constraint.

---

## 10. Observability

- Structured application logging (Python `logging`) at INFO for each
  create/redirect/analytics call, WARNING for 404/410 outcomes, ERROR for
  unexpected exceptions.
- `redirect_events` table doubles as a minimal, queryable audit trail.
- Explicitly out of scope for the prototype: metrics export, tracing,
  dashboards (documented as future evolution, not fabricated).

---

## 11. Failure Scenarios

| Scenario | Behavior |
|---|---|
| Unknown short code redirected to | 404, no DB mutation |
| Expired short code redirected to | 410, no redirect, no DB mutation |
| Malformed URL submitted | 422, no DB row created |
| Short-code collision on insert | Transparent regeneration + retry (bounded), never surfaces to client |
| SQLite file locked/unavailable | 500 with generic error, logged with stack trace server-side only |

---

## 12. Trade-offs

| Decision | Trade-off | Rationale |
|---|---|---|
| SQLite over Postgres | Simplicity, zero infra vs. limited concurrent-writer scalability | Matches "no external database" constraint and prototype scope; evolution path documented |
| Idempotent creation (return existing code) | Slightly more complex creation logic vs. avoiding unbounded duplicate rows | Directly resolves AMB-005 in a way that keeps the dataset clean |
| Separate `redirect_events` table vs. counter-only | More writes vs. richer future analytics | Counter alone would block future "redirects over time" features without a migration |
| No auth in prototype | Faster to build, but a real gap for production | Explicitly flagged as ASSUMED + limitation, not hidden |

---

## 13. Future Evolution

1. Add Redis-backed cache in front of `url_repository.find_by_code`.
2. Swap SQLite → PostgreSQL behind the same repository interface (no
   service/API changes required — this is the point of the layering).
3. Move analytics recording to an async queue/broker consumer.
4. Add authentication/authorization at the API layer only.
5. Add per-short-code rate limiting.
6. Add horizontal scaling behind a load balancer once persistence is
   moved off local SQLite (a local file cannot be safely shared across
   replicas).

---

## Architecture Validation

Checked against `.agentic/context/normalized-requirement.json`:

| Check | Result |
|---|---|
| Every functional requirement (FR-001..FR-008) has a corresponding component/flow | ✅ PASS |
| Every acceptance criterion (AC-001..AC-010) is realizable by a specific, named flow above | ✅ PASS |
| Constraints (C-001..C-003: Python/FastAPI/SQLite/pytest, no Docker/cloud/external DB/LLM, small scope) honored | ✅ PASS |
| Scalability (NFR-001) addressed via explicit, non-implemented evolution path rather than ignored | ✅ PASS |
| Analytics (FR-003) represented by a dedicated component + table, not bolted on | ✅ PASS |
| No unnecessary infrastructure introduced (no Docker/Redis/Kafka in the actual prototype) | ✅ PASS |

**Verdict: PASS.** No rework required. Proceeding to Task Planning.

