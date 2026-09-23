"""
legacy_app_before.py

FROZEN SNAPSHOT of app.py exactly as it existed BEFORE the brownfield
performance fix (see examples/brownfield/impact-analysis.md).

This file exists ONLY so that tests/test_contract_and_performance.py can
demonstrate a genuine, measured before/after performance comparison. It is
not part of the production service and is not imported by app.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

DATA_PATH = Path(__file__).resolve().parent / "data" / "urls.json"

app = FastAPI(title="Sample URL Service (legacy, frozen for comparison)")


def _load_urls() -> list[dict]:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/{short_code}")
def redirect(short_code: str):
    urls = _load_urls()
    for entry in urls:
        if entry["short_code"] == short_code:
            return RedirectResponse(url=entry["original_url"], status_code=302)
    raise HTTPException(status_code=404, detail="Unknown short code")

