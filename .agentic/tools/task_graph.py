"""
task_graph.py

Deterministic dependency-graph reasoning over .agentic/tasks.json.

This tool does NOT decide what tasks should exist (that is the Task
Planner's / Copilot's job). It only answers structural questions about a
given task graph so the Engineering Orchestrator can make deterministic
scheduling decisions instead of guessing:

  - Which tasks are READY (all dependencies COMPLETED or APPROVED)?
  - Which tasks are BLOCKED (waiting on incomplete dependencies)?
  - Are there circular dependencies?
  - Which tasks are downstream (transitive dependents) of a given task?
    (used to scope rework to the affected subgraph only)

Usage (CLI):
    python task_graph.py ready
    python task_graph.py blocked
    python task_graph.py validate
    python task_graph.py dependents --task-id TASK-004
    python task_graph.py sync-ready   # writes READY status back into tasks.json

Usage (import):
    from task_graph import compute_ready, compute_blocked, detect_cycles, downstream_of
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parents[1]  # .agentic/
TASKS_PATH = ROOT / "tasks.json"

TERMINAL_SATISFIED_STATUSES = {"COMPLETED", "APPROVED"}


def _load_tasks() -> List[Dict[str, Any]]:
    if not TASKS_PATH.exists():
        return []
    with TASKS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_tasks(tasks: List[Dict[str, Any]]) -> None:
    with TASKS_PATH.open("w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)
        f.write("\n")


def _by_id(tasks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {t["task_id"]: t for t in tasks}


def detect_cycles(tasks: List[Dict[str, Any]]) -> List[List[str]]:
    """Return a list of cycles (each a list of task_ids) found in the graph."""
    graph = {t["task_id"]: t.get("dependencies", []) for t in tasks}
    visited: Set[str] = set()
    stack: List[str] = []
    on_stack: Set[str] = set()
    cycles: List[List[str]] = []

    def dfs(node: str) -> None:
        visited.add(node)
        stack.append(node)
        on_stack.add(node)
        for dep in graph.get(node, []):
            if dep not in graph:
                continue  # dangling dependency handled separately
            if dep in on_stack:
                cycle_start = stack.index(dep)
                cycles.append(stack[cycle_start:] + [dep])
            elif dep not in visited:
                dfs(dep)
        stack.pop()
        on_stack.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node)
    return cycles


def dangling_dependencies(tasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Return {task_id: [missing_dep_ids]} for dependencies referencing unknown tasks."""
    ids = {t["task_id"] for t in tasks}
    result = {}
    for t in tasks:
        missing = [d for d in t.get("dependencies", []) if d not in ids]
        if missing:
            result[t["task_id"]] = missing
    return result


def compute_ready(tasks: List[Dict[str, Any]]) -> List[str]:
    id_map = _by_id(tasks)
    ready = []
    for t in tasks:
        if t.get("status") not in ("PENDING", "READY", "BLOCKED"):
            continue
        deps = t.get("dependencies", [])
        if all(id_map.get(d, {}).get("status") in TERMINAL_SATISFIED_STATUSES for d in deps):
            ready.append(t["task_id"])
    return ready


def compute_blocked(tasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    id_map = _by_id(tasks)
    blocked = {}
    for t in tasks:
        if t.get("status") not in ("PENDING", "READY", "BLOCKED"):
            continue
        deps = t.get("dependencies", [])
        unmet = [d for d in deps if id_map.get(d, {}).get("status") not in TERMINAL_SATISFIED_STATUSES]
        if unmet:
            blocked[t["task_id"]] = unmet
    return blocked


def downstream_of(task_id: str, tasks: List[Dict[str, Any]]) -> List[str]:
    """All tasks that transitively depend on task_id (used to scope rework)."""
    dependents_map: Dict[str, List[str]] = {}
    for t in tasks:
        for dep in t.get("dependencies", []):
            dependents_map.setdefault(dep, []).append(t["task_id"])

    result: Set[str] = set()
    frontier = [task_id]
    while frontier:
        current = frontier.pop()
        for child in dependents_map.get(current, []):
            if child not in result:
                result.add(child)
                frontier.append(child)
    return sorted(result)


def sync_ready_status(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Mutates and returns tasks: PENDING tasks with satisfied deps -> READY;
    PENDING/READY tasks with unmet deps -> BLOCKED."""
    ready_ids = set(compute_ready(tasks))
    blocked_ids = set(compute_blocked(tasks).keys())
    for t in tasks:
        tid = t["task_id"]
        if t.get("status") == "PENDING" and tid in ready_ids:
            t["status"] = "READY"
        elif t.get("status") in ("PENDING", "READY") and tid in blocked_ids:
            t["status"] = "BLOCKED"
    return tasks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Dependency graph reasoning over .agentic/tasks.json")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ready")
    sub.add_parser("blocked")
    sub.add_parser("validate")
    sub.add_parser("sync-ready")
    p = sub.add_parser("dependents")
    p.add_argument("--task-id", required=True)

    args = parser.parse_args(argv)
    tasks = _load_tasks()

    if args.cmd == "ready":
        print(json.dumps({"ready": compute_ready(tasks)}, indent=2))
    elif args.cmd == "blocked":
        print(json.dumps({"blocked": compute_blocked(tasks)}, indent=2))
    elif args.cmd == "validate":
        cycles = detect_cycles(tasks)
        dangling = dangling_dependencies(tasks)
        result = {
            "valid": not cycles and not dangling,
            "cycles": cycles,
            "dangling_dependencies": dangling,
            "task_count": len(tasks),
        }
        print(json.dumps(result, indent=2))
        if not result["valid"]:
            return 1
    elif args.cmd == "dependents":
        print(json.dumps({"task_id": args.task_id, "downstream": downstream_of(args.task_id, tasks)}, indent=2))
    elif args.cmd == "sync-ready":
        updated = sync_ready_status(tasks)
        _save_tasks(updated)
        print(json.dumps({"ready": compute_ready(updated), "blocked": list(compute_blocked(updated).keys())}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

