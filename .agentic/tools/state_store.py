"""
state_store.py

Bounded, dependency-free helper for reading/writing the Agentic Software
Engineering System's workflow state files:

    .agentic/workflow.json
    .agentic/tasks.json
    .agentic/approval.json
    .agentic/traceability.json

This tool performs NO reasoning. It only persists and retrieves structured
state so that specialized agent roles (invoked via GitHub Copilot Agent mode)
can coordinate through artifacts instead of relying solely on conversational
context.

Usage (CLI):
    python state_store.py workflow show
    python state_store.py workflow init --requirement "..." --type greenfield
    python state_store.py workflow set-stage --stage ARCHITECTURE
    python state_store.py workflow retry --task-id TASK-005

    python state_store.py tasks show
    python state_store.py tasks set-status --task-id TASK-005 --status COMPLETED

    python state_store.py approval show
    python state_store.py approval set --status APPROVED --approved-by "Jane Doe" --comments "LGTM"

    python state_store.py traceability show
    python state_store.py traceability add --requirement REQ-001 --acceptance-criterion AC-001 \
        --task TASK-005 --artifact generated/url_shortener/app/services/url_service.py \
        --test tests/test_url_service.py --validation VAL-003

Usage (import):
    from state_store import load_workflow, save_workflow, ...
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]  # .agentic/
WORKFLOW_PATH = ROOT / "workflow.json"
TASKS_PATH = ROOT / "tasks.json"
APPROVAL_PATH = ROOT / "approval.json"
TRACEABILITY_PATH = ROOT / "traceability.json"

VALID_TASK_STATUSES = {
    "PENDING", "READY", "RUNNING", "BLOCKED", "FAILED",
    "NEEDS_REWORK", "COMPLETED", "APPROVED",
}
VALID_APPROVAL_STATUSES = {"PENDING", "APPROVED", "REWORK_REQUESTED", "REJECTED"}
MAX_RETRY_COUNT = 2


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"State file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# workflow.json
# ---------------------------------------------------------------------------

def load_workflow() -> Dict[str, Any]:
    return _load_json(WORKFLOW_PATH)


def save_workflow(data: Dict[str, Any]) -> None:
    data["updated_at"] = _now()
    _save_json(WORKFLOW_PATH, data)


def init_workflow(requirement_text: str, requirement_type: str, run_id: Optional[str] = None) -> Dict[str, Any]:
    wf = {
        "run_id": run_id or datetime.now(timezone.utc).strftime("RUN-%Y%m%d%H%M%S"),
        "requirement_text": requirement_text,
        "requirement_type": requirement_type,
        "current_stage": "REQUIREMENT_ANALYSIS",
        "stage_history": [
            {"stage": "INIT", "at": _now(), "note": "workflow initialized"}
        ],
        "retry_counts": {},
        "created_at": _now(),
        "updated_at": _now(),
    }
    save_workflow(wf)
    return wf


def set_stage(stage: str, note: str = "") -> Dict[str, Any]:
    wf = load_workflow()
    wf["current_stage"] = stage
    wf.setdefault("stage_history", []).append({"stage": stage, "at": _now(), "note": note})
    save_workflow(wf)
    return wf


def record_retry(task_id: str) -> int:
    wf = load_workflow()
    counts = wf.setdefault("retry_counts", {})
    counts[task_id] = counts.get(task_id, 0) + 1
    save_workflow(wf)
    return counts[task_id]


def get_retry_count(task_id: str) -> int:
    wf = load_workflow()
    return wf.get("retry_counts", {}).get(task_id, 0)


def retry_limit_exceeded(task_id: str) -> bool:
    return get_retry_count(task_id) > MAX_RETRY_COUNT


# ---------------------------------------------------------------------------
# tasks.json
# ---------------------------------------------------------------------------

def load_tasks() -> List[Dict[str, Any]]:
    return _load_json(TASKS_PATH)


def save_tasks(tasks: List[Dict[str, Any]]) -> None:
    _save_json(TASKS_PATH, tasks)


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    for t in load_tasks():
        if t.get("task_id") == task_id:
            return t
    return None


def set_task_status(task_id: str, status: str) -> Dict[str, Any]:
    if status not in VALID_TASK_STATUSES:
        raise ValueError(f"Invalid task status: {status}. Allowed: {sorted(VALID_TASK_STATUSES)}")
    tasks = load_tasks()
    updated = None
    for t in tasks:
        if t.get("task_id") == task_id:
            t["status"] = status
            updated = t
            break
    if updated is None:
        raise KeyError(f"Task not found: {task_id}")
    save_tasks(tasks)
    return updated


# ---------------------------------------------------------------------------
# approval.json
# ---------------------------------------------------------------------------

def load_approval() -> Dict[str, Any]:
    return _load_json(APPROVAL_PATH)


def set_approval(status: str, approved_by: Optional[str] = None, comments: str = "") -> Dict[str, Any]:
    if status not in VALID_APPROVAL_STATUSES:
        raise ValueError(f"Invalid approval status: {status}. Allowed: {sorted(VALID_APPROVAL_STATUSES)}")
    data = {
        "status": status,
        "approved_by": approved_by,
        "approved_at": _now() if status == "APPROVED" else None,
        "comments": comments,
    }
    _save_json(APPROVAL_PATH, data)
    return data


# ---------------------------------------------------------------------------
# traceability.json
# ---------------------------------------------------------------------------

def load_traceability() -> Dict[str, Any]:
    return _load_json(TRACEABILITY_PATH)


def add_traceability_link(requirement_id: str, acceptance_criterion_id: str, task_id: str,
                           artifacts: List[str], tests: List[str], validation_id: str) -> Dict[str, Any]:
    data = load_traceability()
    link = {
        "requirement_id": requirement_id,
        "acceptance_criterion_id": acceptance_criterion_id,
        "task_id": task_id,
        "artifacts": artifacts,
        "tests": tests,
        "validation_id": validation_id,
        "recorded_at": _now(),
    }
    data.setdefault("links", []).append(link)
    _save_json(TRACEABILITY_PATH, data)
    return link


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Workflow state store for the Agentic Software Engineering System")
    sub = parser.add_subparsers(dest="entity", required=True)

    wf_p = sub.add_parser("workflow")
    wf_sub = wf_p.add_subparsers(dest="action", required=True)
    wf_sub.add_parser("show")
    p = wf_sub.add_parser("init")
    p.add_argument("--requirement", required=True)
    p.add_argument("--type", required=True, dest="requirement_type")
    p = wf_sub.add_parser("set-stage")
    p.add_argument("--stage", required=True)
    p.add_argument("--note", default="")
    p = wf_sub.add_parser("retry")
    p.add_argument("--task-id", required=True)

    tasks_p = sub.add_parser("tasks")
    tasks_sub = tasks_p.add_subparsers(dest="action", required=True)
    tasks_sub.add_parser("show")
    p = tasks_sub.add_parser("set-status")
    p.add_argument("--task-id", required=True)
    p.add_argument("--status", required=True)

    appr_p = sub.add_parser("approval")
    appr_sub = appr_p.add_subparsers(dest="action", required=True)
    appr_sub.add_parser("show")
    p = appr_sub.add_parser("set")
    p.add_argument("--status", required=True)
    p.add_argument("--approved-by", default=None)
    p.add_argument("--comments", default="")

    trace_p = sub.add_parser("traceability")
    trace_sub = trace_p.add_subparsers(dest="action", required=True)
    trace_sub.add_parser("show")
    p = trace_sub.add_parser("add")
    p.add_argument("--requirement", required=True)
    p.add_argument("--acceptance-criterion", required=True)
    p.add_argument("--task", required=True)
    p.add_argument("--artifact", action="append", default=[])
    p.add_argument("--test", action="append", default=[])
    p.add_argument("--validation", required=True)

    args = parser.parse_args(argv)

    if args.entity == "workflow":
        if args.action == "show":
            _print(load_workflow())
        elif args.action == "init":
            _print(init_workflow(args.requirement, args.requirement_type))
        elif args.action == "set-stage":
            _print(set_stage(args.stage, args.note))
        elif args.action == "retry":
            count = record_retry(args.task_id)
            _print({"task_id": args.task_id, "retry_count": count, "exceeded": count > MAX_RETRY_COUNT})
    elif args.entity == "tasks":
        if args.action == "show":
            _print(load_tasks())
        elif args.action == "set-status":
            _print(set_task_status(args.task_id, args.status))
    elif args.entity == "approval":
        if args.action == "show":
            _print(load_approval())
        elif args.action == "set":
            _print(set_approval(args.status, args.approved_by, args.comments))
    elif args.entity == "traceability":
        if args.action == "show":
            _print(load_traceability())
        elif args.action == "add":
            _print(add_traceability_link(
                args.requirement, args.acceptance_criterion, args.task,
                args.artifact, args.test, args.validation,
            ))
    return 0


if __name__ == "__main__":
    sys.exit(main())

