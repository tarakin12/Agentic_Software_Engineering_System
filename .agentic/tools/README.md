# .agentic/tools/

Bounded, dependency-free Python helper scripts used by the Copilot agent
roles defined in `.github/agents/`. These tools perform **no reasoning** —
they only provide deterministic state persistence, dependency-graph
computation, bounded test execution, read-only repository inspection, and
mechanical artifact validation. All semantic reasoning (requirement
analysis, architecture, code generation, etc.) is performed by GitHub
Copilot Agent mode itself, following the instructions in the agent files.

All tools are stdlib-only (no `pip install` required) and are safe to run
directly with `python`.

| Tool | Purpose |
|---|---|
| `state_store.py` | Read/write `workflow.json`, `tasks.json`, `approval.json`, `traceability.json` |
| `task_graph.py` | Compute READY/BLOCKED tasks, detect cycles/dangling deps, find downstream dependents for scoped rework |
| `run_tests.py` | Execute `python -m pytest` and persist real, unfaked results to `.agentic/validation/test-results.json` |
| `inspect_repo.py` | Read-only repository inspection (frameworks, routes, tests, symbols) for brownfield reasoning |
| `validate_artifacts.py` | Mechanical validation: state file shape, task graph integrity, OpenAPI-vs-implementation route diff, schema-vs-model diff |

## Examples

```powershell
python .agentic/tools/state_store.py workflow init --requirement "Build a scalable URL shortener..." --type greenfield
python .agentic/tools/state_store.py workflow set-stage --stage ARCHITECTURE
python .agentic/tools/task_graph.py ready
python .agentic/tools/task_graph.py validate
python .agentic/tools/run_tests.py --path generated/url_shortener/tests
python .agentic/tools/inspect_repo.py --path generated/url_shortener --write
python .agentic/tools/validate_artifacts.py all --openapi artifacts/openapi.yaml --src generated/url_shortener/app --schema artifacts/schema.sql --models generated/url_shortener/app/models
```

These are the only commands agent roles should execute against the shell,
alongside the other explicitly bounded commands listed in
`copilot-instructions.md` (`python -m pytest`, `python -m compileall`,
`git status`, `git diff`).

