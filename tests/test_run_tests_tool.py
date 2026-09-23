"""
test_run_tests_tool.py

Unit + real-execution tests for .agentic/tools/run_tests.py. The summary
parser is tested directly against synthetic pytest output strings. The
actual run_pytest() function is also exercised for real against small,
throwaway pytest projects under tmp_path — a genuine subprocess pytest
invocation, not mocked — to prove the tool correctly distinguishes
PASS / FAILED / NOT EXECUTED from real outcomes.
"""

import run_tests as run_tests_tool


def test_parse_summary_counts_passed_and_failed():
    output = (
        "collected 5 items\n"
        "..F..\n"
        "======================= 4 passed, 1 failed in 0.12s ======================="
    )
    summary = run_tests_tool._parse_summary(output)
    assert summary["passed"] == 4
    assert summary["failed"] == 1
    assert summary["errors"] == 0
    assert summary["skipped"] == 0


def test_parse_summary_handles_skipped_and_errors():
    output = "=== 2 passed, 1 skipped, 3 errors in 1.0s ==="
    summary = run_tests_tool._parse_summary(output)
    assert summary["passed"] == 2
    assert summary["skipped"] == 1
    assert summary["errors"] == 3


def test_parse_summary_empty_when_no_recognizable_output():
    summary = run_tests_tool._parse_summary("nothing recognizable here")
    assert summary == {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}


def test_run_pytest_real_execution_reports_pass(tmp_path, monkeypatch):
    """Real subprocess execution against a genuinely passing test file."""
    monkeypatch.setattr(run_tests_tool, "RESULTS_PATH", tmp_path / "results.json")
    project = tmp_path / "proj"
    project.mkdir()
    (project / "test_ok.py").write_text("def test_ok():\n    assert 1 + 1 == 2\n", encoding="utf-8")

    result = run_tests_tool.run_pytest(str(project))

    assert result["executed"] is True
    assert result["status"] == "PASS"
    assert result["return_code"] == 0
    assert result["summary"]["passed"] == 1
    assert (tmp_path / "results.json").exists()  # evidence file actually written


def test_run_pytest_real_execution_reports_failed(tmp_path, monkeypatch):
    """Real subprocess execution against a genuinely failing test file."""
    monkeypatch.setattr(run_tests_tool, "RESULTS_PATH", tmp_path / "results.json")
    project = tmp_path / "proj"
    project.mkdir()
    (project / "test_bad.py").write_text("def test_bad():\n    assert 1 == 2\n", encoding="utf-8")

    result = run_tests_tool.run_pytest(str(project))

    assert result["executed"] is True
    assert result["status"] == "FAILED"
    assert result["return_code"] != 0
    assert result["summary"]["failed"] == 1


def test_run_pytest_reports_not_executed_when_no_tests_collected(tmp_path, monkeypatch):
    """Real subprocess execution against a directory with zero test files —
    pytest's own exit code 5 ('no tests collected') must map to NOT EXECUTED,
    not be misreported as FAILED."""
    monkeypatch.setattr(run_tests_tool, "RESULTS_PATH", tmp_path / "results.json")
    empty_project = tmp_path / "empty"
    empty_project.mkdir()
    (empty_project / "not_a_test_file.py").write_text("x = 1\n", encoding="utf-8")

    result = run_tests_tool.run_pytest(str(empty_project))

    assert result["executed"] is True
    assert result["status"] == "NOT EXECUTED"
    assert result["return_code"] == 5

