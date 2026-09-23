"""
test_validate_artifacts.py

Unit tests for .agentic/tools/validate_artifacts.py. State-file-reading
functions (validate_workflow/tasks/approval/traceability) are tested via
monkeypatching the module's AGENTIC path constant to an isolated tmp_path,
so these tests never touch the repository's real, live state. The
OpenAPI/schema comparison functions take explicit file paths and are
tested directly against small synthetic files.
"""

import json

import pytest

import validate_artifacts as va


@pytest.fixture(autouse=True)
def isolate_agentic_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(va, "AGENTIC", tmp_path)
    yield


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")


def test_validate_workflow_missing_file_is_invalid(tmp_path):
    result = va.validate_workflow()
    assert result["valid"] is False
    assert "not found" in result["error"]


def test_validate_workflow_detects_missing_keys(tmp_path):
    _write(tmp_path / "workflow.json", {"run_id": "x"})  # missing most keys
    result = va.validate_workflow()
    assert result["valid"] is False
    assert "current_stage" in result["missing_keys"]


def test_validate_workflow_valid_when_all_keys_present(tmp_path):
    _write(tmp_path / "workflow.json", {
        "run_id": "x", "requirement_text": "t", "requirement_type": "greenfield",
        "current_stage": "INIT", "stage_history": [], "retry_counts": {},
        "created_at": "t", "updated_at": "t",
    })
    result = va.validate_workflow()
    assert result["valid"] is True
    assert result["missing_keys"] == []


def _valid_task(task_id, deps=None):
    return {
        "task_id": task_id, "title": "t", "description": "d",
        "assigned_agent": "code-engineer", "dependencies": deps or [],
        "status": "PENDING", "inputs": [], "outputs": [],
        "validation_criteria": [], "retry_count": 0,
    }


def test_validate_tasks_detects_missing_fields(tmp_path):
    incomplete = {"task_id": "TASK-001"}  # missing everything else
    _write(tmp_path / "tasks.json", [incomplete])
    result = va.validate_tasks()
    assert result["valid"] is False
    assert "TASK-001" in result["tasks_missing_fields"]


def test_validate_tasks_detects_cycle(tmp_path):
    tasks = [_valid_task("A", deps=["B"]), _valid_task("B", deps=["A"])]
    _write(tmp_path / "tasks.json", tasks)
    result = va.validate_tasks()
    assert result["valid"] is False
    assert result["cycles"]


def test_validate_tasks_valid_dag(tmp_path):
    tasks = [_valid_task("A"), _valid_task("B", deps=["A"])]
    _write(tmp_path / "tasks.json", tasks)
    result = va.validate_tasks()
    assert result["valid"] is True
    assert result["task_count"] == 2


def test_validate_approval_rejects_invalid_status(tmp_path):
    _write(tmp_path / "approval.json", {
        "status": "NOT_REAL", "approved_by": None, "approved_at": None, "comments": "",
    })
    result = va.validate_approval()
    assert result["valid"] is False
    assert result["status_valid"] is False


def test_validate_approval_valid_when_status_recognized(tmp_path):
    _write(tmp_path / "approval.json", {
        "status": "APPROVED", "approved_by": "X", "approved_at": "t", "comments": "",
    })
    result = va.validate_approval()
    assert result["valid"] is True


def test_validate_traceability_detects_incomplete_link(tmp_path):
    _write(tmp_path / "traceability.json", {"links": [{"requirement_id": "REQ-1"}]})
    result = va.validate_traceability()
    assert result["valid"] is False
    assert result["incomplete_links"][0]["index"] == 0


def test_validate_traceability_valid_when_all_links_complete(tmp_path):
    _write(tmp_path / "traceability.json", {"links": [{
        "requirement_id": "REQ-1", "acceptance_criterion_id": "AC-1",
        "task_id": "TASK-001", "artifacts": [], "tests": [], "validation_id": "VAL-1",
    }]})
    result = va.validate_traceability()
    assert result["valid"] is True
    assert result["link_count"] == 1


def test_extract_openapi_paths_parses_paths_section(tmp_path):
    openapi_file = tmp_path / "openapi.yaml"
    openapi_file.write_text(
        "openapi: 3.0.3\n"
        "paths:\n"
        "  /urls:\n"
        "    post:\n"
        "      summary: x\n"
        "  /{short_code}:\n"
        "    get:\n"
        "      summary: y\n"
        "components:\n"
        "  schemas: {}\n",
        encoding="utf-8",
    )
    paths = va._extract_openapi_paths(openapi_file)
    assert paths == {"POST /urls", "GET /{short_code}"}


def test_extract_sql_tables_finds_create_table_statements(tmp_path):
    schema_file = tmp_path / "schema.sql"
    schema_file.write_text(
        "CREATE TABLE IF NOT EXISTS urls (id INTEGER PRIMARY KEY);\n"
        "CREATE TABLE redirect_events (id INTEGER);\n",
        encoding="utf-8",
    )
    tables = va._extract_sql_tables(schema_file)
    assert tables == {"urls", "redirect_events"}


def test_validate_openapi_detects_mismatch(tmp_path):
    openapi_file = tmp_path / "openapi.yaml"
    openapi_file.write_text(
        "paths:\n"
        "  /urls:\n"
        "    post:\n"
        "      summary: x\n"
        "  /only-in-docs:\n"
        "    get:\n"
        "      summary: x\n",
        encoding="utf-8",
    )
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "routes.py").write_text(
        '@app.post("/urls")\n'
        "def create():\n"
        "    pass\n\n"
        '@app.get("/only-in-impl")\n'
        "def unexpected():\n"
        "    pass\n",
        encoding="utf-8",
    )
    result = va.validate_openapi(openapi_file, src_dir)
    assert result["valid"] is False
    assert "GET /only-in-docs" in result["documented_but_not_implemented"]
    assert "GET /only-in-impl" in result["implemented_but_undocumented"]


def test_validate_openapi_valid_when_exact_match(tmp_path):
    openapi_file = tmp_path / "openapi.yaml"
    openapi_file.write_text("paths:\n  /urls:\n    post:\n      summary: x\n", encoding="utf-8")
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "routes.py").write_text('@app.post("/urls")\ndef create():\n    pass\n', encoding="utf-8")

    result = va.validate_openapi(openapi_file, src_dir)
    assert result["valid"] is True
    assert result["documented_but_not_implemented"] == []
    assert result["implemented_but_undocumented"] == []

