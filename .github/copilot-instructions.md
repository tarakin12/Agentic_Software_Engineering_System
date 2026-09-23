# Agentic Software Engineering System

This repository implements an agentic software engineering workflow.

## Global Rules

GitHub Copilot Agent mode is the reasoning and execution environment.

Never call an external LLM API.

Never require an API key.

Never invent a Copilot API.

The Engineering Orchestrator is the primary entry point.

Specialized agents operate according to their defined responsibilities.

Agents communicate primarily through persisted artifacts.

Do not rely exclusively on conversational context.

Never claim an operation succeeded unless it was actually performed.

Never claim tests passed unless they actually executed successfully.

Do not silently convert assumptions into requirements.

Material ambiguity requires human clarification or approval.

Maximum automatic retry count is 2.

Do not execute unrestricted shell commands.

Prefer bounded commands such as:

python -m pytest
python -m compileall
git status
git diff

Do not hard-code the URL shortener workflow.

The URL shortener is a mandatory demonstration scenario, not a special-case implementation.

All engineering changes must maintain traceability:

Requirement
→ Acceptance Criterion
→ Task
→ Artifact
→ Test
→ Validation

Final approval must remain human-controlled.

## Repository Layout

```
.github/agents/          Specialized agent role definitions
.agentic/                Workflow state, task graph, context, artifacts, validation, logs
artifacts/                Top-level engineering deliverables (OpenAPI, schema, summary)
generated/                Generated application source code
examples/                 Greenfield, brownfield and ambiguous demonstration scenarios
docs/                     Supplementary documentation
tests/                    Framework's own test suite (validates .agentic/tools/, not generated apps)
```

## Entry Point

Evaluators should say:

"Use the Engineering Orchestrator to process this requirement: <requirement text>"

See `.github/agents/engineering-orchestrator.agent.md`.


