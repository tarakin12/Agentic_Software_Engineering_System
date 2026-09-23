"""
run_tests.py

Bounded test execution wrapper. This tool actually invokes pytest via the
approved bounded command (`python -m pytest`) and captures the real result.
It never infers or fabricates a PASS/FAIL outcome.

The Test Engineer / Validation Engineer roles must use this tool (or the
equivalent bounded command directly) instead of claiming tests passed
without execution.

Usage (CLI):
    python run_tests.py                       # runs pytest on default target
    python run_tests.py --path generated/url_shortener/tests
    python run_tests.py --path generated/url_shortener/tests -- -k test_redirect

Writes raw evidence to:
    .agentic/validation/test-results.json

Exit code mirrors pytest's exit code.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[1]  # .agentic/
RESULTS_PATH = ROOT / "validation" / "test-results.json"

SUMMARY_RE = re.compile(
    r"(?P<counts>\d+ (passed|failed|error|errors|skipped|xfailed|xpassed))"
)


def _parse_summary(output: str) -> dict:
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    for match in SUMMARY_RE.finditer(output):
        text = match.group("counts")
        number, label = text.split(" ", 1)
        number = int(number)
        if label.startswith("passed"):
            counts["passed"] += number
        elif label.startswith("failed"):
            counts["failed"] += number
        elif label.startswith("error"):
            counts["errors"] += number
        elif label.startswith("skipped"):
            counts["skipped"] += number
    return counts


def run_pytest(path: Optional[str], extra_args: Optional[List[str]] = None) -> dict:
    cmd = [sys.executable, "-m", "pytest"]
    if path:
        cmd.append(path)
    if extra_args:
        cmd.extend(extra_args)

    started_at = datetime.now(timezone.utc).isoformat()
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(ROOT.parent), timeout=600
        )
        executed = True
        returncode = proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
    except FileNotFoundError as e:
        executed = False
        returncode = -1
        stdout, stderr = "", str(e)
    except subprocess.TimeoutExpired as e:
        executed = False
        returncode = -1
        stdout, stderr = e.stdout or "", "Timed out after 600s"

    finished_at = datetime.now(timezone.utc).isoformat()
    summary = _parse_summary(stdout) if executed else {}

    if not executed:
        status = "NOT EXECUTED"
    elif returncode == 5:
        # pytest exit code 5 = no tests were collected at the given path
        status = "NOT EXECUTED"
    elif returncode == 0:
        status = "PASS"
    else:
        status = "FAILED"

    result = {
        "command": cmd,
        "executed": executed,
        "status": status,
        "return_code": returncode,
        "summary": summary,
        "started_at": started_at,
        "finished_at": finished_at,
        "stdout_tail": "\n".join(stdout.splitlines()[-80:]) if stdout else "",
        "stderr_tail": "\n".join(stderr.splitlines()[-80:]) if stderr else "",
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")

    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Bounded pytest execution wrapper")
    parser.add_argument("--path", default=None, help="Path/module to test (defaults to whole repo)")
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER, help="Extra args after --")
    args = parser.parse_args(argv)

    extra = args.pytest_args
    if extra and extra[0] == "--":
        extra = extra[1:]

    result = run_pytest(args.path, extra)
    print(json.dumps(result, indent=2))
    if not result["executed"]:
        return 2
    return result["return_code"]


if __name__ == "__main__":
    sys.exit(main())


