"""
test_task_graph.py

Unit tests for .agentic/tools/task_graph.py — pure functions operating on
in-memory task lists (no file I/O needed for most of these, since
detect_cycles/compute_ready/downstream_of/sync_ready_status all accept a
tasks list directly).
"""

import task_graph


def _task(task_id, deps=None, status="PENDING"):
    return {
        "task_id": task_id,
        "title": task_id,
        "description": "",
        "assigned_agent": "code-engineer",
        "dependencies": deps or [],
        "status": status,
        "inputs": [],
        "outputs": [],
        "validation_criteria": [],
        "retry_count": 0,
    }


def test_detect_cycles_finds_a_real_cycle():
    tasks = [
        _task("A", deps=["B"]),
        _task("B", deps=["C"]),
        _task("C", deps=["A"]),  # closes the cycle A -> B -> C -> A
    ]
    cycles = task_graph.detect_cycles(tasks)
    assert cycles, "Expected at least one cycle to be detected"
    assert any("A" in cycle for cycle in cycles)


def test_detect_cycles_no_cycle_on_valid_dag():
    tasks = [
        _task("A"),
        _task("B", deps=["A"]),
        _task("C", deps=["A"]),
        _task("D", deps=["B", "C"]),
    ]
    assert task_graph.detect_cycles(tasks) == []


def test_dangling_dependencies_detected():
    tasks = [
        _task("A", deps=["DOES-NOT-EXIST"]),
        _task("B"),
    ]
    dangling = task_graph.dangling_dependencies(tasks)
    assert dangling == {"A": ["DOES-NOT-EXIST"]}


def test_dangling_dependencies_empty_when_all_valid():
    tasks = [_task("A"), _task("B", deps=["A"])]
    assert task_graph.dangling_dependencies(tasks) == {}


def test_compute_ready_only_when_all_dependencies_completed():
    tasks = [
        _task("A", status="COMPLETED"),
        _task("B", deps=["A"], status="PENDING"),
        _task("C", deps=["A", "B"], status="PENDING"),
    ]
    ready = task_graph.compute_ready(tasks)
    assert ready == ["B"]  # C is not ready because B is not yet COMPLETED


def test_compute_ready_treats_approved_as_satisfied():
    tasks = [
        _task("A", status="APPROVED"),
        _task("B", deps=["A"], status="PENDING"),
    ]
    assert task_graph.compute_ready(tasks) == ["B"]


def test_compute_blocked_lists_unmet_dependencies():
    tasks = [
        _task("A", status="PENDING"),
        _task("B", deps=["A"], status="PENDING"),
    ]
    blocked = task_graph.compute_blocked(tasks)
    assert blocked == {"B": ["A"]}


def test_independent_tasks_become_ready_simultaneously():
    """Mirrors the real URL shortener run: two tasks with the same single
    completed dependency should both be READY at once (parallelizable)."""
    tasks = [
        _task("ARCH", status="COMPLETED"),
        _task("API", deps=["ARCH"], status="PENDING"),
        _task("DB", deps=["ARCH"], status="PENDING"),
    ]
    ready = task_graph.compute_ready(tasks)
    assert set(ready) == {"API", "DB"}


def test_downstream_of_finds_transitive_dependents():
    tasks = [
        _task("A"),
        _task("B", deps=["A"]),
        _task("C", deps=["B"]),
        _task("D", deps=["C"]),
        _task("E"),  # unrelated
    ]
    assert task_graph.downstream_of("A", tasks) == ["B", "C", "D"]


def test_downstream_of_leaf_task_is_empty():
    tasks = [_task("A"), _task("B", deps=["A"])]
    assert task_graph.downstream_of("B", tasks) == []


def test_sync_ready_status_transitions_pending_to_ready_and_blocked():
    tasks = [
        _task("A", status="COMPLETED"),
        _task("B", deps=["A"], status="PENDING"),
        _task("C", deps=["B"], status="PENDING"),
    ]
    updated = task_graph.sync_ready_status(tasks)
    by_id = {t["task_id"]: t["status"] for t in updated}
    assert by_id["B"] == "READY"
    assert by_id["C"] == "BLOCKED"
    assert by_id["A"] == "COMPLETED"  # unaffected, not PENDING/READY

