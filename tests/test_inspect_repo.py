"""
test_inspect_repo.py

Unit tests for .agentic/tools/inspect_repo.py — read-only repository
inspection. Tested against small synthetic directories/files (tmp_path),
never against the real repository, to keep results deterministic and
independent of the repo's evolving contents.
"""

import inspect_repo


def test_detect_routes_finds_fastapi_style_decorators(tmp_path):
    py_file = tmp_path / "routes.py"
    py_file.write_text(
        '@app.get("/{short_code}")\n'
        "def redirect(short_code: str):\n"
        "    pass\n\n"
        '@router.post("/urls")\n'
        "def create():\n"
        "    pass\n",
        encoding="utf-8",
    )
    routes = inspect_repo.detect_routes(py_file)
    assert {"method": "GET", "path": "/{short_code}"} in routes
    assert {"method": "POST", "path": "/urls"} in routes


def test_detect_routes_empty_for_file_with_no_routes(tmp_path):
    py_file = tmp_path / "plain.py"
    py_file.write_text("def helper():\n    return 1\n", encoding="utf-8")
    assert inspect_repo.detect_routes(py_file) == []


def test_detect_python_symbols_finds_classes_and_functions(tmp_path):
    py_file = tmp_path / "module.py"
    py_file.write_text(
        "class Foo:\n"
        "    pass\n\n"
        "class Bar:\n"
        "    pass\n\n"
        "def top_level_fn():\n"
        "    pass\n",
        encoding="utf-8",
    )
    symbols = inspect_repo.detect_python_symbols(py_file)
    assert set(symbols["classes"]) == {"Foo", "Bar"}
    assert "top_level_fn" in symbols["functions"]


def test_detect_python_symbols_handles_syntax_error_gracefully(tmp_path):
    py_file = tmp_path / "broken.py"
    py_file.write_text("def broken(:\n    pass\n", encoding="utf-8")
    symbols = inspect_repo.detect_python_symbols(py_file)
    assert symbols["parse_error"] is True


def test_inspect_reports_expected_shape_for_small_project(tmp_path):
    (tmp_path / "app.py").write_text(
        "from fastapi import FastAPI\n\n"
        "app = FastAPI()\n\n"
        '@app.get("/health")\n'
        "def health():\n"
        "    return {'status': 'ok'}\n",
        encoding="utf-8",
    )
    (tmp_path / "test_app.py").write_text("def test_health():\n    assert True\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")

    result = inspect_repo.inspect(tmp_path)

    assert result["dependency_manifests"] == ["requirements.txt"]
    assert "FastAPI" in result["detected_frameworks"]
    assert "test_app.py" in result["test_files"]
    assert any(r["routes"] for r in result["api_routes"])


def test_inspect_excludes_noise_directories(tmp_path):
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cached.pyc").write_text("junk", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("junk", encoding="utf-8")
    (tmp_path / "real.py").write_text("def f():\n    pass\n", encoding="utf-8")

    result = inspect_repo.inspect(tmp_path)
    assert result["total_files"] == 1
    assert result["python_files"][0]["path"] == "real.py"


