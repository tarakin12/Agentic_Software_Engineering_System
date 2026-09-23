# Agentic Software Engineering System

An interview-prototype demonstration of a genuine **agentic software
engineering workflow**: a natural-language requirement is transformed into
a reviewable engineering outcome (architecture, code, tests, docs,
validation, traceability) via GitHub Copilot Agent mode — not a chatbot
that outputs code from a single prompt.

**No external LLM API, no API key, no Docker, no cloud infrastructure is
required.** GitHub Copilot Agent mode itself is the reasoning engine; this
repository supplies the agent role definitions, workflow state model, and
bounded deterministic tools it uses.

## Current Status

The mandatory URL shortener scenario has been run **end to end and
approved**: `.agentic/workflow.json.current_stage == "COMPLETE"`,
`.agentic/approval.json.status == "APPROVED"`. Brownfield and ambiguous
example scenarios have also been run for real (not just described). The
full repository test suite — **74 tests across 3 independent suites** —
passes (`python .agentic/tools/run_tests.py`). See
`artifacts/engineering-summary.md` for the complete final report.

## Repository Layout

```
.github/
  copilot-instructions.md          Global rules (no LLM API, retry limits, traceability, etc.)
  agents/*.agent.md                 8 agent role definitions (orchestrator + 7 specialists)
.agentic/                           Live workflow state for the URL shortener run
  workflow.json, tasks.json, approval.json, traceability.json
  context/, artifacts/, validation/, logs/
  tools/*.py                        Deterministic, dependency-free bookkeeping tools
artifacts/                          Top-level engineering deliverables
  openapi.yaml, schema.sql, engineering-summary.md
generated/url_shortener/            The mandatory scenario's implementation + tests
examples/
  greenfield/                       Documents the completed URL shortener run
  brownfield/sample-url-service/    Real naive-app → inspected → fixed demonstration
  ambiguous/                        Real halt-for-clarification demonstration
docs/                               URL shortener API/setup documentation
tests/                              Framework's OWN test suite (tests the tools, not the app)
requirements.txt, README.md
```

## Objective

Demonstrate requirement understanding, ambiguity detection, architecture
reasoning, dependency-aware task decomposition, brownfield codebase
reasoning, code/test/doc generation, independent validation, bounded
failure recovery, controlled autonomy, and human approval — end to end,
against a real mandatory scenario (URL shortener) plus brownfield and
ambiguous-requirement examples.

## Architecture

```
Evaluator (VS Code + GitHub Copilot Agent mode)
        │
        ▼
Engineering Orchestrator  (.github/agents/engineering-orchestrator.agent.md)
        │
        ├─▶ Requirement Analyst      → .agentic/context/normalized-requirement.json
        ├─▶ Architecture Designer    → .agentic/artifacts/architecture.md
        ├─▶ Task Planner             → .agentic/tasks.json
        ├─▶ Code Engineer            → generated/
        ├─▶ Test Engineer            → generated/*/tests/, .agentic/validation/test-results.*
        ├─▶ Documentation Engineer   → docs/, README.md
        └─▶ Validation Engineer      → .agentic/validation/validation-report.md
        │
        ▼
Human Approval (.agentic/approval.json) → Final Summary (artifacts/engineering-summary.md)
```

Copilot Agent mode performs all semantic reasoning by reading the
`.github/agents/*.agent.md` instruction files. The Python scripts in
`.agentic/tools/` are intentionally **deterministic, dependency-free
bookkeeping only** — state persistence, dependency-graph math, bounded
`pytest` execution, read-only repo inspection, and mechanical artifact
diffing. They never decide *what* to build; they only track and verify
what was built.

## Agent Responsibilities

| Agent | Responsibility | Output |
|---|---|---|
| Requirement Analyst | Intent, FR/NFR, constraints, ambiguity detection, testable acceptance criteria | `normalized-requirement.json` |
| Architecture Designer | Components, data flow, API boundaries, trade-offs, evolution path | `architecture.md` |
| Task Planner | Dependency-aware task graph | `tasks.json` |
| Code Engineer | Layered implementation | `generated/` |
| Test Engineer | Unit/integration/API tests, real execution | `tests/`, `test-results.*` |
| Documentation Engineer | API docs, setup, limitations | `docs/`, `README.md` |
| Validation Engineer | Independent cross-artifact review | `validation-report.md` |

Full definitions: `.github/agents/*.agent.md`.

## Engineering Orchestrator

The single entry point (`.github/agents/engineering-orchestrator.agent.md`).
The evaluator interacts only with it; it delegates to the specialized
roles above and persists their outputs as artifacts rather than relying on
conversational memory.

## Orchestration Model

```
Requirement Analysis → Ambiguity Check → Architecture → Architecture Validation
→ Task Planning → Dependency Analysis → Execution → Testing → Validation
→ (FAIL → Root Cause → Rework Task → Re-execute affected subgraph, max 2 retries)
→ Human Approval → Final Summary
```

## Task State Model

`.agentic/tasks.json` — each task has `task_id, title, description,
assigned_agent, dependencies, status, inputs, outputs,
validation_criteria, retry_count`. Status values: `PENDING, READY,
RUNNING, BLOCKED, FAILED, NEEDS_REWORK, COMPLETED, APPROVED`. Readiness is
computed deterministically by `.agentic/tools/task_graph.py`, not asserted.

## Artifact-Driven Handoff

Every stage reads only the previous stage's **persisted artifact**, never
raw conversation history:

```
Requirement Analyst → .agentic/context/normalized-requirement.json
Architecture Designer → .agentic/artifacts/architecture.md
Task Planner → .agentic/tasks.json
Code Engineer → generated/
Test Engineer → tests/, .agentic/validation/test-results.*
Validation Engineer → .agentic/validation/validation-report.md
```

## Controlled Autonomy

Agents act autonomously for inspection, design, planning, implementation,
testing, and validation. Human approval is required only for: material
requirement ambiguity, high-risk architecture decisions, destructive
changes, exceeding the 2-retry recovery limit, and final approval —
tracked in `.agentic/approval.json`.

## Human Approval

`.agentic/approval.json` starts `PENDING` and is never auto-set to
`APPROVED`. The final engineering summary cannot be marked complete
without an explicit human decision recorded here.

## Validation

Two layers: mechanical (`.agentic/tools/validate_artifacts.py` — JSON
shape checks, dependency-graph integrity, OpenAPI-vs-implementation route
diff, schema-vs-model diff) and independent semantic review (Validation
Engineer → `validation-report.md`), never a self-assessment by the Code
Engineer.

## Error Recovery

Failed validation → root cause → scoped rework task (only the affected
task + its downstream dependents via `task_graph.py dependents`) → retry
(max 2) → re-validate. Exceeding the limit sets `NEEDS_HUMAN_REVIEW`
instead of retrying indefinitely.

## Traceability

`.agentic/traceability.json` links
Requirement → Acceptance Criterion → Task → Artifact → Test → Validation,
built only from artifacts that actually exist.

## Greenfield Example

Mandatory scenario: *"Build a scalable URL shortener service with APIs,
persistence and analytics."* See `examples/greenfield/url-shortener.md`
and the live run artifacts under `.agentic/`.

## Brownfield Example

`examples/brownfield/sample-url-service/` — a genuinely naive pre-existing
service (per-request disk read + O(n) linear scan) was inspected with
`inspect_repo.py` (real tool output, not assumed), the root cause found by
reading the actual code, a minimal in-place fix applied (in-memory dict
index), and both API-contract-compatibility and performance verified by
real tests. **Measured result: a 2.3x speedup** (deterministic
disk-read-count test + corroborating wall-clock measurement). Full
narrative: `examples/brownfield/brownfield-run-summary.md`.

## Ambiguous Example

`examples/ambiguous/requirement.md` — *"Build a better URL platform."*
The same Requirement Analyst process that judged the URL shortener's
ambiguities as non-material judged **these** as material (10 open
questions including business objective and user identity themselves) and
**halted** — producing `clarification-questions.md` and
`proposed-assumptions.json` but deliberately no architecture, tasks, or
code. See `examples/ambiguous/ambiguous-run-summary.md` for the side-by-side
contrast with the greenfield run.

## URL Shortener

Implementation: `generated/url_shortener/` (FastAPI + SQLite, layered:
api/services/repositories/models/analytics). Full docs:
[`docs/url-shortener.md`](docs/url-shortener.md). API contract:
[`artifacts/openapi.yaml`](artifacts/openapi.yaml). Schema:
[`artifacts/schema.sql`](artifacts/schema.sql).

## How to Run

```powershell
pip install -r requirements.txt
cd generated/url_shortener
python -m uvicorn app.main:app --reload
```

## How to Use with GitHub Copilot Agent Mode

> **📄 Full interactive user guide:** [`docs/user-guide.html`](docs/user-guide.html) — open it in a browser for a navigable, styled walkthrough covering setup, features, running the URL shortener, running other use cases, troubleshooting, and FAQ.

1. Open this repository in VS Code.
2. Ensure GitHub Copilot is enabled; select Claude Sonnet or another
   capable model.
3. Open Copilot Agent mode.
4. Say: *"Use the Engineering Orchestrator to process this requirement:
   Build a scalable URL shortener service with APIs, persistence and
   analytics."*
5. Review normalization, architecture, task graph, and validation as the
   orchestrator progresses; approve or request rework when prompted.

## Evaluator Experience

No API key, Docker, cloud account, or external database is needed — only
VS Code, GitHub Copilot, Python 3.11+, and Git.

```powershell
pip install -r requirements.txt
python .agentic/tools/run_tests.py   # 74/74 passing, real execution
```

Then inspect the real artifacts directly: `.agentic/workflow.json`
(`current_stage: COMPLETE`), `.agentic/approval.json`
(`status: APPROVED`), `.agentic/validation/validation-report.md`,
`.agentic/traceability.json`, and `artifacts/engineering-summary.md`.

## Testing

Three separate, independently meaningful test suites exist in this repository:

```powershell
# Whole repository at once (recommended)
python .agentic/tools/run_tests.py

# Or individually:
python -m pytest generated/url_shortener/tests        # the mandatory scenario's own tests
python -m pytest examples/brownfield/sample-url-service/tests  # brownfield contract + perf tests
python -m pytest tests/                                 # the FRAMEWORK's own tests (tools, not the app)
```

| Suite | Count | Tests |
|---|---|---|
| URL shortener (`generated/url_shortener/tests/`) | 23 | Unit (service/analytics) + integration/API tests, including a real persistence-across-restart test |
| Brownfield (`examples/brownfield/.../tests/`) | 4 | Contract-compatibility + deterministic disk-read-count + wall-clock speedup |
| Framework (`tests/`) | 47 | `task_graph.py`, `state_store.py`, `validate_artifacts.py`, `inspect_repo.py`, `run_tests.py` — the deterministic tools themselves, isolated via monkeypatch from the repo's real live state |
| **Total** | **74** | **All passing** — see `.agentic/validation/test-results.md` for the URL shortener's own evidence file |

Two genuine bugs were found and fixed while building this repository (not
staged for effect): a Python module-name collision (`app`) between the
URL shortener and the brownfield sample when the full suite runs together
(fixed via `importlib`-based unique loading), and an `inspect_repo.py`
crash when inspecting directories outside the repo root (fixed with a
graceful fallback). Both are documented in
`examples/brownfield/brownfield-run-summary.md` and this repository's
commit history rather than hidden.

## Limitations

No authentication, no rate limiting, single-node SQLite persistence (
production evolution path documented, not implemented) — see
`docs/url-shortener.md` for the full list.

## Future Enhancements

Redis caching, PostgreSQL, async analytics via message broker, horizontal
scaling, authentication — see `.agentic/artifacts/architecture.md` §13.


