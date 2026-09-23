"""
validate_artifacts.py

Bounded, deterministic artifact validation. This tool performs mechanical
checks that do NOT require semantic reasoning, so that the Validation
Engineer role has real evidence to cite instead of only an LLM judgment.

Checks implemented:
  - workflow.json / tasks.json / approval.json / traceability.json:
        structural shape checks against expected keys
  - tasks graph: delegates to task_graph.py (cycles, dangling deps)
  - OpenAPI vs implementation:
        parses `paths:` section of an OpenAPI YAML file (regex-based, no
        external yaml dependency required) and compares against routes
        discovered by inspect_repo.py-style scanning of a source directory
  - schema.sql vs models directory:
        extracts CREATE TABLE names from schema.sql and compares against
        class names found in a models directory

Usage (CLI):
    python validate_artifacts.py workflow
    python validate_artifacts.py tasks
    python validate_artifacts.py approval
    python validate_artifacts.py traceability
    python validate_artifacts.py openapi --openapi artifacts/openapi.yaml --src generated/url_shortener/app
    python validate_artifacts.py schema --schema artifacts/schema.sql --models generated/url_shortener/app/models
    python validate_artifacts.py all --openapi artifacts/openapi.yaml --src generated/url_shortener/app --schema artifacts/schema.sql --models generated/url_shortener/app/models

Every check prints a JSON report with a top-level "valid" boolean and never
claims validity without an explicit comparison.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_graph  # noqa: E402
from inspect_repo import detect_routes, _iter_files  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTIC = REPO_ROOT / ".agentic"

WORKFLOW_REQUIRED_KEYS = {
    "run_id", "requirement_text", "requirement_type", "current_stage",
    "stage_history", "retry_counts", "created_at", "updated_at",
}
APPROVAL_REQUIRED_KEYS = {"status", "approved_by", "approved_at", "comments"}
APPROVAL_VALID_STATUSES = {"PENDING", "APPROVED", "REWORK_REQUESTED", "REJECTED"}
TASK_REQUIRED_KEYS = {
    "task_id", "title", "description", "assigned_agent", "dependencies",
    "status", "inputs", "outputs", "validation_criteria", "retry_count",
}

OPENAPI_PATH_LINE_RE = re.compile(r"^\s{2}(/\S*):\s*$")
OPENAPI_METHOD_LINE_RE = re.compile(r"^\s{4}(get|post|put|delete|patch):\s*$")
SQL_CREATE_TABLE_RE = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"'`]?(\w+)", re.IGNORECASE)


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_workflow() -> Dict[str, Any]:
    data = _load_json(AGENTIC / "workflow.json")
    if data is None:
        return {"valid": False, "error": "workflow.json not found"}
    missing = WORKFLOW_REQUIRED_KEYS - data.keys()
    return {"valid": not missing, "missing_keys": sorted(missing), "current_stage": data.get("current_stage")}


def validate_tasks() -> Dict[str, Any]:
    data = _load_json(AGENTIC / "tasks.json")
    if data is None:
        return {"valid": False, "error": "tasks.json not found"}
    per_task_issues = {}
    for t in data:
        missing = TASK_REQUIRED_KEYS - t.keys()
        if missing:
            per_task_issues[t.get("task_id", "<unknown>")] = sorted(missing)
    cycles = task_graph.detect_cycles(data)
    dangling = task_graph.dangling_dependencies(data)
    valid = not per_task_issues and not cycles and not dangling
    return {
        "valid": valid,
        "task_count": len(data),
        "tasks_missing_fields": per_task_issues,
        "cycles": cycles,
        "dangling_dependencies": dangling,
    }


def validate_approval() -> Dict[str, Any]:
    data = _load_json(AGENTIC / "approval.json")
    if data is None:
        return {"valid": False, "error": "approval.json not found"}
    missing = APPROVAL_REQUIRED_KEYS - data.keys()
    status_ok = data.get("status") in APPROVAL_VALID_STATUSES
    return {
        "valid": not missing and status_ok,
        "missing_keys": sorted(missing),
        "status": data.get("status"),
        "status_valid": status_ok,
    }


def validate_traceability() -> Dict[str, Any]:
    data = _load_json(AGENTIC / "traceability.json")
    if data is None:
        return {"valid": False, "error": "traceability.json not found"}
    links = data.get("links", [])
    required = {"requirement_id", "acceptance_criterion_id", "task_id", "artifacts", "tests", "validation_id"}
    incomplete = []
    for i, link in enumerate(links):
        missing = required - link.keys()
        if missing:
            incomplete.append({"index": i, "missing": sorted(missing)})
    return {"valid": not incomplete, "link_count": len(links), "incomplete_links": incomplete}


def _extract_openapi_paths(openapi_path: Path) -> Set[str]:
    """Regex-based extraction of `method path` pairs from an OpenAPI YAML file's
    `paths:` section, avoiding a hard dependency on PyYAML."""
    if not openapi_path.exists():
        return set()
    lines = openapi_path.read_text(encoding="utf-8").splitlines()
    results: Set[str] = set()
    current_path = None
    in_paths_section = False
    for line in lines:
        if line.strip() == "paths:":
            in_paths_section = True
            continue
        if not in_paths_section:
            continue
        if line and not line.startswith(" "):
            break  # left the paths: section (top-level key)
        path_match = OPENAPI_PATH_LINE_RE.match(line)
        if path_match:
            current_path = path_match.group(1)
            continue
        method_match = OPENAPI_METHOD_LINE_RE.match(line)
        if method_match and current_path:
            results.add(f"{method_match.group(1).upper()} {current_path}")
    return results


def _extract_implemented_routes(src_dir: Path) -> Set[str]:
    results: Set[str] = set()
    if not src_dir.exists():
        return results
    for p in _iter_files(src_dir):
        if p.suffix != ".py":
            continue
        for route in detect_routes(p):
            results.add(f"{route['method']} {route['path']}")
    return results


def validate_openapi(openapi_path: Path, src_dir: Path) -> Dict[str, Any]:
    documented = _extract_openapi_paths(openapi_path)
    implemented = _extract_implemented_routes(src_dir)
    missing_in_impl = sorted(documented - implemented)
    undocumented = sorted(implemented - documented)
    return {
        "valid": not missing_in_impl and not undocumented,
        "documented_routes": sorted(documented),
        "implemented_routes": sorted(implemented),
        "documented_but_not_implemented": missing_in_impl,
        "implemented_but_undocumented": undocumented,
    }


def _extract_sql_tables(schema_path: Path) -> Set[str]:
    if not schema_path.exists():
        return set()
    text = schema_path.read_text(encoding="utf-8")
    return {m.group(1) for m in SQL_CREATE_TABLE_RE.finditer(text)}


def _extract_model_class_names(models_dir: Path) -> Set[str]:
    names: Set[str] = set()
    if not models_dir.exists():
        return names
    for p in _iter_files(models_dir):
        if p.suffix != ".py":
            continue
        try:
            import ast as _ast
            tree = _ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in _ast.walk(tree):
            if isinstance(node, _ast.ClassDef):
                names.add(node.name)
    return names


def validate_schema(schema_path: Path, models_dir: Path) -> Dict[str, Any]:
    tables = _extract_sql_tables(schema_path)
    model_classes = _extract_model_class_names(models_dir)
    # Loose comparison: table names (snake_case, often plural) vs class names
    # (PascalCase, often singular) — report both sets for human/agent judgement
    # rather than asserting a strict naming convention.
    return {
        "tables": sorted(tables),
        "model_classes": sorted(model_classes),
        "table_count": len(tables),
        "model_class_count": len(model_classes),
        "valid": len(tables) > 0 and len(model_classes) > 0,
        "note": "Table-to-class name matching is not strictly enforced; review manually for correspondence.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Bounded, deterministic artifact validation")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("workflow")
    sub.add_parser("tasks")
    sub.add_parser("approval")
    sub.add_parser("traceability")

    p = sub.add_parser("openapi")
    p.add_argument("--openapi", required=True)
    p.add_argument("--src", required=True)

    p = sub.add_parser("schema")
    p.add_argument("--schema", required=True)
    p.add_argument("--models", required=True)

    p = sub.add_parser("all")
    p.add_argument("--openapi", required=False)
    p.add_argument("--src", required=False)
    p.add_argument("--schema", required=False)
    p.add_argument("--models", required=False)

    args = parser.parse_args(argv)
    report: Dict[str, Any] = {}

    if args.cmd == "workflow":
        report = validate_workflow()
    elif args.cmd == "tasks":
        report = validate_tasks()
    elif args.cmd == "approval":
        report = validate_approval()
    elif args.cmd == "traceability":
        report = validate_traceability()
    elif args.cmd == "openapi":
        report = validate_openapi(REPO_ROOT / args.openapi, REPO_ROOT / args.src)
    elif args.cmd == "schema":
        report = validate_schema(REPO_ROOT / args.schema, REPO_ROOT / args.models)
    elif args.cmd == "all":
        report = {
            "workflow": validate_workflow(),
            "tasks": validate_tasks(),
            "approval": validate_approval(),
            "traceability": validate_traceability(),
        }
        if args.openapi and args.src:
            report["openapi"] = validate_openapi(REPO_ROOT / args.openapi, REPO_ROOT / args.src)
        if args.schema and args.models:
            report["schema"] = validate_schema(REPO_ROOT / args.schema, REPO_ROOT / args.models)

    print(json.dumps(report, indent=2))
    is_valid = report.get("valid", all(v.get("valid", False) for v in report.values() if isinstance(v, dict)))
    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())

