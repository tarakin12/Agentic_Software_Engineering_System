"""
test_state_store.py

Unit tests for .agentic/tools/state_store.py. Uses monkeypatch to redirect
the module's file path constants (WORKFLOW_PATH, TASKS_PATH,
APPROVAL_PATH, TRACEABILITY_PATH) to tmp_path locations, so these tests
NEVER read or write the repository's real, live workflow state
(.agentic/workflow.json etc., which holds the actual APPROVED URL
shortener run) — this isolation is essential given this module's
functions have real side effects (file writes).
"""

import json

import pytest

import state_store


@pytest.fixture(autouse=True)
def isolate_state_files(tmp_path, monkeypatch):
    """Redirect every state file path to an isolated tmp location for
    every test in this module, automatically."""
    monkeypatch.setattr(state_store, "WORKFLOW_PATH", tmp_path / "workflow.json")
    monkeypatch.setattr(state_store, "TASKS_PATH", tmp_path / "tasks.json")
    monkeypatch.setattr(state_store, "APPROVAL_PATH", tmp_path / "approval.json")
    monkeypatch.setattr(state_store, "TRACEABILITY_PATH", tmp_path / "traceability.json")

    # These files must exist for _load_json to succeed, mirroring the real
    # repository's initial state files.
    (tmp_path / "tasks.json").write_text("[]", encoding="utf-8")
    (tmp_path / "approval.json").write_text(
        json.dumps({"status": "PENDING", "approved_by": None, "approved_at": None, "comments": ""}),
        encoding="utf-8",
    )
    (tmp_path / "traceability.json").write_text(json.dumps({"links": []}), encoding="utf-8")
    yield


def test_init_workflow_creates_expected_shape():
    wf = state_store.init_workflow("Test requirement", "greenfield")
    assert wf["requirement_text"] == "Test requirement"
    assert wf["requirement_type"] == "greenfield"
    assert wf["current_stage"] == "REQUIREMENT_ANALYSIS"
    assert wf["stage_history"][0]["stage"] == "INIT"
    assert wf["retry_counts"] == {}
    # Confirm it was actually persisted, not just returned in-memory
    reloaded = state_store.load_workflow()
    assert reloaded["requirement_text"] == "Test requirement"


def test_set_stage_appends_to_history_without_losing_prior_entries():
    state_store.init_workflow("Req", "greenfield")
    state_store.set_stage("ARCHITECTURE", note="moving on")
    state_store.set_stage("TASK_PLANNING", note="planning")

    wf = state_store.load_workflow()
    stages = [entry["stage"] for entry in wf["stage_history"]]
    assert stages == ["INIT", "ARCHITECTURE", "TASK_PLANNING"]
    assert wf["current_stage"] == "TASK_PLANNING"


def test_record_retry_increments_per_task_independently():
    state_store.init_workflow("Req", "greenfield")
    assert state_store.record_retry("TASK-005") == 1
    assert state_store.record_retry("TASK-005") == 2
    assert state_store.record_retry("TASK-006") == 1  # independent counter

    assert state_store.get_retry_count("TASK-005") == 2
    assert state_store.get_retry_count("TASK-006") == 1
    assert state_store.get_retry_count("TASK-999") == 0  # never retried


def test_retry_limit_exceeded_respects_max_of_two():
    state_store.init_workflow("Req", "greenfield")
    state_store.record_retry("TASK-001")  # 1
    assert state_store.retry_limit_exceeded("TASK-001") is False
    state_store.record_retry("TASK-001")  # 2
    assert state_store.retry_limit_exceeded("TASK-001") is False
    state_store.record_retry("TASK-001")  # 3 — exceeds max of 2
    assert state_store.retry_limit_exceeded("TASK-001") is True


def test_set_task_status_updates_only_the_matching_task():
    tasks = [
        {
            "task_id": "TASK-001", "title": "t", "description": "d",
            "assigned_agent": "code-engineer", "dependencies": [],
            "status": "PENDING", "inputs": [], "outputs": [],
            "validation_criteria": [], "retry_count": 0,
        },
        {
            "task_id": "TASK-002", "title": "t2", "description": "d",
            "assigned_agent": "code-engineer", "dependencies": [],
            "status": "PENDING", "inputs": [], "outputs": [],
            "validation_criteria": [], "retry_count": 0,
        },
    ]
    state_store.save_tasks(tasks)

    updated = state_store.set_task_status("TASK-001", "COMPLETED")
    assert updated["status"] == "COMPLETED"

    all_tasks = state_store.load_tasks()
    by_id = {t["task_id"]: t["status"] for t in all_tasks}
    assert by_id["TASK-001"] == "COMPLETED"
    assert by_id["TASK-002"] == "PENDING"  # untouched


def test_set_task_status_rejects_invalid_status():
    state_store.save_tasks([{
        "task_id": "TASK-001", "title": "t", "description": "d",
        "assigned_agent": "code-engineer", "dependencies": [],
        "status": "PENDING", "inputs": [], "outputs": [],
        "validation_criteria": [], "retry_count": 0,
    }])
    with pytest.raises(ValueError):
        state_store.set_task_status("TASK-001", "NOT_A_REAL_STATUS")


def test_set_task_status_unknown_task_raises_keyerror():
    state_store.save_tasks([])
    with pytest.raises(KeyError):
        state_store.set_task_status("TASK-DOES-NOT-EXIST", "COMPLETED")


def test_set_approval_rejects_invalid_status():
    with pytest.raises(ValueError):
        state_store.set_approval("NOT_A_REAL_STATUS")


def test_set_approval_records_approved_at_only_when_approved():
    result = state_store.set_approval("REWORK_REQUESTED", approved_by="X", comments="needs work")
    assert result["approved_at"] is None  # not approved, so no timestamp

    approved = state_store.set_approval("APPROVED", approved_by="Jane", comments="looks good")
    assert approved["approved_at"] is not None
    assert approved["approved_by"] == "Jane"


def test_add_traceability_link_appends_without_losing_prior_links():
    state_store.add_traceability_link(
        "REQ-1", "AC-1", "TASK-001", ["file1.py"], ["test1.py::test_a"], "VAL-1"
    )
    state_store.add_traceability_link(
        "REQ-1", "AC-2", "TASK-002", ["file2.py"], ["test2.py::test_b"], "VAL-2"
    )
    data = state_store.load_traceability()
    assert len(data["links"]) == 2
    assert data["links"][0]["acceptance_criterion_id"] == "AC-1"
    assert data["links"][1]["acceptance_criterion_id"] == "AC-2"

