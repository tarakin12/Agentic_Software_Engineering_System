# Task Plan — URL Shortener

**Run:** RUN-20260922175531
**Input:** `.agentic/context/normalized-requirement.json`, `.agentic/artifacts/architecture.md`

## Dependency Graph

```
TASK-001 Requirement Analysis  [COMPLETED]
        |
        v
TASK-002 Architecture          [COMPLETED]
        |
        +-----------------+-----------------+
        |                 |                 |
        v                 v                 v
TASK-003 API         TASK-004 DB       (TASK-007 also
Contract             Schema            depends only on
        |                 |             TASK-004 below)
        +--------+--------+
                 |
        +--------+--------+
        |                 |
        v                 v
TASK-005 URL         TASK-006 Redirect
Creation Svc         Service
        |                 |
        +--------+--------+-----+
                 |              |
                 |              v
                 |         TASK-007 Analytics
                 |         (dep: TASK-004 only)
                 |              |
        +--------+--------------+
        |
        v
TASK-008 Unit Tests  ---+
        |               |
        v               v
TASK-009 Integration/API Tests
        |
        v
TASK-010 Documentation
        |
        v
TASK-011 Independent Validation
```

## Independently Executable Tasks

Once TASK-002 (Architecture) is COMPLETED, the following become READY
**simultaneously** and can be executed in any order (verified structurally
by `.agentic/tools/task_graph.py`, not asserted by opinion):

- **TASK-003** (API Contract) — depends only on TASK-002
- **TASK-004** (Database Schema) — depends only on TASK-002

TASK-007 (Analytics) depends only on TASK-004, so it becomes READY as soon
as TASK-004 completes, in parallel with TASK-005/TASK-006 becoming READY
(which need both TASK-003 and TASK-004).

TASK-005 (URL Creation Service) and TASK-006 (Redirect Service) are
**not** independent of each other in the sense of shared output
(`url_service.py` is touched by both) — the Code Engineer must sequence
these two carefully or merge them into one coherent service edit — but
neither blocks the other's *readiness*, since both only depend on
TASK-003 + TASK-004.

TASK-008 and TASK-009 (tests) both depend on TASK-005, TASK-006, TASK-007
and can be produced in either order once all three are COMPLETED.

## Requirement Coverage Check

| Acceptance Criterion | Covered By |
|---|---|
| AC-001, AC-002, AC-003 | TASK-005, TASK-008, TASK-009 |
| AC-004, AC-005, AC-006 | TASK-006, TASK-008, TASK-009 |
| AC-007, AC-008 | TASK-007, TASK-008, TASK-009 |
| AC-009 (layered code) | TASK-005/006/007 (directory structure itself) |
| AC-010 (suite passes) | TASK-008, TASK-009, TASK-011 |

No acceptance criterion is left without an owning task.

## Validation

- No circular dependencies (verified via `task_graph.py validate`).
- No dangling dependency references (verified via `task_graph.py validate`).
- Every task has exactly one owning agent.
- Every task has at least one validation criterion.

