"""
tests/conftest.py

Makes .agentic/tools/*.py importable as top-level modules (state_store,
task_graph, validate_artifacts, inspect_repo, run_tests) for the
framework's own test suite. These module names are unique within the
repository (no collision with generated/url_shortener's `app` package or
examples/brownfield's `app.py`), so a simple sys.path insertion is safe
here — unlike the brownfield tests, which had to use importlib with
unique aliases specifically because of an `app` naming collision.
"""

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / ".agentic" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

