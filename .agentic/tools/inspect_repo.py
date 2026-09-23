"""
inspect_repo.py

Bounded, read-only repository inspection tool. Used by the Engineering
Orchestrator / Requirement Analyst / Architecture Designer / Code Engineer
for brownfield reasoning so that impacted-module claims are backed by
actual repository inspection rather than assumption.

This tool performs NO modification. It only reads and reports.

Usage (CLI):
    python inspect_repo.py                       # inspect whole repo
    python inspect_repo.py --path generated/url_shortener
    python inspect_repo.py --write               # also persist to
                                                    .agentic/context/repo-inspection.json

Reports:
    - directory tree summary (excluding noise dirs)
    - detected languages / frameworks (via marker files)
    - Python source files and their top-level defs/classes (via ast)
    - detected API route declarations (FastAPI/Flask-style decorators)
    - detected test files
    - dependency manifests found (requirements.txt, pyproject.toml, package.json)
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / ".agentic" / "context" / "repo-inspection.json"

EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache", ".mypy_cache"}
DEPENDENCY_MANIFESTS = {"requirements.txt", "pyproject.toml", "package.json", "Pipfile"}
ROUTE_DECORATOR_RE = re.compile(
    r"@(?:app|router)\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']"
)
TEST_FILE_RE = re.compile(r"(^test_.*\.py$)|(.*_test\.py$)")


def _iter_files(root: Path):
    for p in root.rglob("*"):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if p.is_file():
            yield p


def detect_dependency_manifests(root: Path) -> List[str]:
    found = []
    for p in _iter_files(root):
        if p.name in DEPENDENCY_MANIFESTS:
            found.append(str(p.relative_to(root)))
    return found


def detect_python_symbols(path: Path) -> Dict[str, List[str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return {"classes": [], "functions": [], "parse_error": True}
    classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    functions = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return {"classes": classes, "functions": functions}


def detect_routes(path: Path) -> List[Dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    return [{"method": m.upper(), "path": p} for m, p in ROUTE_DECORATOR_RE.findall(text)]


def _describe_root(root: Path) -> str:
    """Human-readable identifier for the inspected root. Falls back to an
    absolute path string when `root` is not inside REPO_ROOT (e.g. when
    this tool is used — including by its own test suite — against an
    arbitrary directory such as a pytest tmp_path), rather than raising."""
    if root == REPO_ROOT:
        return "."
    try:
        return str(root.relative_to(REPO_ROOT))
    except ValueError:
        return str(root)


def inspect(root: Path) -> Dict[str, Any]:
    py_files = []
    test_files = []
    routes = []
    all_files = []

    for p in _iter_files(root):
        rel = str(p.relative_to(root))
        all_files.append(rel)
        if p.suffix == ".py":
            entry = {"path": rel, **detect_python_symbols(p)}
            py_files.append(entry)
            file_routes = detect_routes(p)
            if file_routes:
                routes.append({"file": rel, "routes": file_routes})
            if TEST_FILE_RE.match(p.name):
                test_files.append(rel)

    manifests = detect_dependency_manifests(root)

    frameworks = set()
    # Lightweight framework detection via source-file content scan
    for p in _iter_files(root):
        if p.suffix == ".py":
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if "fastapi" in text.lower():
                frameworks.add("FastAPI")
            if "flask" in text.lower():
                frameworks.add("Flask")
            if "sqlite3" in text.lower() or "sqlite" in text.lower():
                frameworks.add("SQLite")
            if "sqlalchemy" in text.lower():
                frameworks.add("SQLAlchemy")

    result = {
        "inspected_root": _describe_root(root),
        "total_files": len(all_files),
        "dependency_manifests": manifests,
        "detected_frameworks": sorted(frameworks),
        "python_files": py_files,
        "test_files": test_files,
        "api_routes": routes,
    }
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read-only repository inspection tool")
    parser.add_argument("--path", default=".", help="Path (relative to repo root) to inspect")
    parser.add_argument("--write", action="store_true", help="Persist result to .agentic/context/repo-inspection.json")
    args = parser.parse_args(argv)

    target = (REPO_ROOT / args.path).resolve()
    if not target.exists():
        print(json.dumps({"error": f"Path does not exist: {args.path}"}, indent=2))
        return 1

    result = inspect(target)

    if args.write:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT_PATH.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())




