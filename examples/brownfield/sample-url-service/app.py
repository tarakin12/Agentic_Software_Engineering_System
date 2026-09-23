"""
app.py — Sample URL Redirect Service

BROWNFIELD CHANGE APPLIED (see examples/brownfield/impact-analysis.md):
Replaced the original per-request disk read + O(n) linear scan with a
single in-memory dict index built once at process startup (module import
time). The API contract is unchanged: same route (`GET /{short_code}`),
same status codes (302/404), same response behavior — only the internal
lookup mechanism changed, per the requirement's explicit constraint.

Original (pre-change) implementation is preserved unmodified at
legacy_app_before.py solely for the before/after performance test.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

DATA_PATH = Path(__file__).resolve().parent / "data" / "urls.json"

app = FastAPI(title="Sample URL Service (improved)")


def _build_index() -> Dict[str, str]:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        urls = json.load(f)
    return {entry["short_code"]: entry["original_url"] for entry in urls}


# Built once at startup, not on every request — this is the performance fix.
_URL_INDEX: Dict[str, str] = _build_index()


@app.get("/{short_code}")
def redirect(short_code: str):
    original_url = _URL_INDEX.get(short_code)  # O(1) dict lookup
    if original_url is None:
        raise HTTPException(status_code=404, detail="Unknown short code")
    return RedirectResponse(url=original_url, status_code=302)



