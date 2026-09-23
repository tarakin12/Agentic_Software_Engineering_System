# Greenfield Example — URL Shortener

This example documents an actual completed run of the Engineering
Orchestrator (not a hypothetical). All linked artifacts are real, on disk,
and were produced by working through the full pipeline in this repository.

## Input

> Build a scalable URL shortener service with APIs, persistence and analytics.

## Pipeline Executed

```
Requirement Analysis → Ambiguity Check (non-material, proceeded with
documented assumptions) → Architecture → Architecture Validation (PASS) →
Task Planning → Dependency Analysis → Execution (11 tasks) → Testing →
Validation (PASS) → Human Approval (APPROVED) → Final Summary
```

## Real Artifacts Produced

| Stage | Artifact |
|---|---|
| Requirement Analysis | `.agentic/context/normalized-requirement.json`, `requirement-analysis.md` |
| Architecture | `.agentic/artifacts/architecture.md` |
| Task Planning | `.agentic/tasks.json`, `.agentic/artifacts/task-plan.md` |
| Implementation | `generated/url_shortener/app/` (layered: api/services/repositories/models/analytics) |
| API Contract | `artifacts/openapi.yaml` |
| Schema | `artifacts/schema.sql` |
| Tests | `generated/url_shortener/tests/` (23 tests) |
| Test Evidence | `.agentic/validation/test-results.json`, `test-results.md` |
| Documentation | `docs/url-shortener.md`, `README.md` |
| Validation | `.agentic/validation/validation-report.md` |
| Traceability | `.agentic/traceability.json` (10 links) |
| Approval | `.agentic/approval.json` (APPROVED) |
| Summary | `artifacts/engineering-summary.md` |

## Key Demonstrated Behaviors

- **Ambiguity was detected but judged non-material** (scale target, auth,
  expiration policy, analytics depth, duplicate handling) — each resolved
  via a clearly labeled ASSUMED default rather than silently invented.
  Contrast this with `examples/ambiguous/` where ambiguity *is* material
  and the workflow halts instead.
- **Real parallel task execution**, mechanically verified: `task_graph.py
  sync-ready` showed TASK-003 (API Contract) and TASK-004 (Database
  Schema) becoming READY simultaneously, and TASK-005/006/007 becoming
  READY simultaneously once their shared dependency completed.
- **Real test execution**, not a claimed result: `.agentic/validation/test-results.json`
  contains the actual pytest command, exit code, and stdout.
- **Self-correction, not scripted rework**: a genuine coverage gap
  (AC-006 untested at the HTTP layer) was found while writing the test
  report, fixed immediately, and the suite re-run (22→23 passed) — see
  the "Process Note" in `.agentic/validation/test-results.md`.
- **Human approval was not automatic**: `.agentic/approval.json` remained
  `PENDING` until an explicit approval action was recorded.

## Final Outcome

`.agentic/workflow.json.current_stage == "COMPLETE"`,
`.agentic/approval.json.status == "APPROVED"`. Full narrative:
`artifacts/engineering-summary.md`.

