-- Database Schema: URL Shortener
-- Produced by: Code Engineer (TASK-004)
-- Inputs: .agentic/artifacts/architecture.md (Section 6: Persistence Design)
--
-- Two tables:
--   urls            - one row per shortened URL
--   redirect_events - one row per redirect (per-event history for analytics)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS urls (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    short_code       TEXT NOT NULL UNIQUE,
    original_url     TEXT NOT NULL,
    created_at       TEXT NOT NULL,           -- ISO-8601 UTC timestamp
    expires_at       TEXT,                    -- ISO-8601 UTC timestamp, NULL = never expires (ASM-003)
    redirect_count   INTEGER NOT NULL DEFAULT 0,
    last_accessed_at TEXT                     -- ISO-8601 UTC timestamp, NULL until first redirect
);

-- short_code is the hottest read path: every redirect (GET /{short_code}) and
-- every analytics lookup (GET /urls/{short_code}/analytics) keys off it.
-- UNIQUE already creates an implicit index in SQLite, but it is declared
-- explicitly here for clarity and to document intent (architecture.md §6).
CREATE UNIQUE INDEX IF NOT EXISTS idx_urls_short_code ON urls (short_code);

-- original_url is indexed to support the idempotent-creation lookup (AC-003):
-- "does a mapping for this URL already exist?" must not be a full table scan
-- as the table grows.
CREATE INDEX IF NOT EXISTS idx_urls_original_url ON urls (original_url);

CREATE TABLE IF NOT EXISTS redirect_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    short_code  TEXT NOT NULL,
    accessed_at TEXT NOT NULL,               -- ISO-8601 UTC timestamp
    FOREIGN KEY (short_code) REFERENCES urls (short_code)
);

-- Kept separate from urls.redirect_count (rather than counter-only) so that
-- per-event history exists for future trend analytics (e.g. "redirects per
-- day") without a schema migration later — see architecture.md §6/§12
-- (trade-offs). Indexed on short_code since analytics reads are always
-- scoped to a single short code.
CREATE INDEX IF NOT EXISTS idx_redirect_events_short_code ON redirect_events (short_code);

