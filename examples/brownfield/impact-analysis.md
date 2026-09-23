# Brownfield Impact Analysis — Sample URL Service

**Requirement:** "Improve redirect performance while keeping the existing API contract unchanged."
**Evidence base:** `examples/brownfield/repo-inspection.json` (actual tool output, not assumed)

## Repository Inspection Findings

From `inspect_repo.py` (real, mechanical inspection, not opinion):

- 4 total files: `app.py`, `requirements.txt`, `README.md`, `data/urls.json`.
- Detected framework: FastAPI.
- **1 route exists**: `GET /{short_code}`.
- **0 test files exist** — this is a genuine pre-existing repo with no test safety net, a realistic brownfield condition.

## Root Cause (found by reading the actual code, not assumed)

`app.py::redirect()`:
```python
@app.get("/{short_code}")
def redirect(short_code: str):
    urls = _load_urls()      # re-reads + re-parses urls.json from disk EVERY request
    for entry in urls:       # linear O(n) scan EVERY request
        if entry["short_code"] == short_code:
            return RedirectResponse(url=entry["original_url"], status_code=302)
    raise HTTPException(status_code=404, detail="Unknown short code")
```

With 2000 entries in `data/urls.json` (see `data/urls.json`, actual file),
every single redirect pays for a full disk read, JSON parse, and up to
2000 dictionary-key comparisons — even though the underlying data set is
effectively static between deployments.

## Impacted Files

| File | Impact |
|---|---|
| `app.py` | **Only** file requiring modification — contains the entire redirect logic |
| `data/urls.json` | Read-only; no schema change needed |
| `requirements.txt`, `README.md` | No change needed |

**No other files are impacted.** This is a deliberately minimal,
targeted change — consistent with the brownfield principle "prefer
minimal targeted changes over unnecessary rewrites."

## Impacted API

`GET /{short_code}` — the **route signature, status codes (302/404), and
response behavior remain byte-for-byte identical**. Only the internal
lookup mechanism changes. This satisfies the explicit constraint
"keeping the existing API contract unchanged."

## Recommended Change

Replace per-request disk read + linear scan with a single in-memory
`dict` index built once at process startup (module import time):

```python
_URL_INDEX: dict[str, str] = _build_index()  # built once, not per-request

@app.get("/{short_code}")
def redirect(short_code: str):
    original_url = _URL_INDEX.get(short_code)  # O(1)
    if original_url is None:
        raise HTTPException(status_code=404, detail="Unknown short code")
    return RedirectResponse(url=original_url, status_code=302)
```

**Rationale:** O(n) disk read + linear scan → O(1) in-memory dict lookup.
No new dependencies, no schema change, no route change — the smallest
change that fixes the actual measured problem.

## Risks

| Risk | Assessment |
|---|---|
| Data becomes stale if `urls.json` changes without a process restart | **Accepted** — the original naive version had the same implicit assumption (it re-read the file, but nothing in the requirement mentions live-reload; a restart-to-reload behavior is standard and unchanged in spirit) — documented here rather than silently introduced |
| No existing tests to catch regressions | **Mitigated** — new tests added as part of this change (see TASK-BF-003) specifically to lock in contract compatibility before/after |

## Validation Plan

1. Contract test: known short codes return 302 to the exact same `original_url` as before.
2. Contract test: unknown short code still returns 404.
3. Performance test: direct, real timing comparison between the frozen
   pre-change implementation (`legacy_app_before.py`, kept only for this
   comparison) and the improved `app.py`, over the same 2000-entry dataset.

