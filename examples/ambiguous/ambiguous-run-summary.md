# Ambiguous Scenario Run Summary

**Requirement:** "Build a better URL platform."

## Workflow Outcome: HALTED at Ambiguity Check (by design)

```
Requirement Analysis → Ambiguity Check → ⛔ MATERIAL AMBIGUITY DETECTED
                                          → clarification-questions.md
                                          → proposed-assumptions.json
                                          → HALT, awaiting human input
```

Unlike the mandatory URL shortener scenario (`examples/greenfield/`),
**no architecture, task plan, or code was produced for this requirement.**
This is intentional and is the correct behavior, not an incomplete run.

## Why This Differs From the Greenfield Run

| | URL Shortener (greenfield) | "Better URL platform" (ambiguous) |
|---|---|---|
| Ambiguities found | 5 (scale, auth, expiration, analytics depth, duplicate handling) | 10 (including business objective and user identity themselves) |
| Materiality | Non-material — narrow implementation details with safe, low-risk defaults | **Material** — the fundamental shape of the product is undefined |
| Action taken | Proceed with clearly labeled ASSUMED defaults | **Halt**; produce questions + proposed assumptions; do not proceed |
| Risk of proceeding anyway | Low (reversible, additive decisions) | High (could build an entirely wrong product) |

This side-by-side is the actual proof point for controlled autonomy: the
same Requirement Analyst process, applied to two different requirements,
produces two genuinely different decisions — not a hardcoded "always
proceed" or "always halt" behavior.

## Artifacts Produced (and what's deliberately absent)

- ✅ `requirement.md` — the raw input
- ✅ `clarification-questions.md` — 10 concrete, answerable questions
- ✅ `proposed-assumptions.json` — explicit, labeled, risk-rated proposed
  defaults, presented **only to make the risk of proceeding visible**,
  not as a silent decision
- ❌ No `normalized-requirement.json` with finalized FR/NFR — cannot be
  responsibly produced yet
- ❌ No `architecture.md`, `tasks.json`, or generated code — correctly
  absent, since building any of these now would mean silently deciding
  the product on the requester's behalf

## Path to Resume

Once a human answers the questions in `clarification-questions.md` (or
explicitly approves some/all of the `proposed-assumptions.json` entries),
the workflow can resume exactly where the URL shortener run's Phase 3
began: Requirement Analysis → normalized-requirement.json → Architecture.
No work is wasted by halting here — nothing downstream had started yet.

