# Changelog

## [Unreleased] — Production-readiness hardening

A broad refactor turning the working prototype into a more production-grade ETL.
Public entry points (`python main.py`, each pipeline's `run()`, `fetch`/
`fetch_post`, `save_to_db`) keep working; behaviour of the transforms is
preserved (verified by tests).

### Security (P0)
- Removed the hardcoded database password from `config.py`; DB connection is now
  built from env vars (`DB_URL` or `DB_*`), no secrets in source.
- `.gitignore` now excludes `.env`, `*.cfg`, `config/airflow.cfg`, `logs/`, etc.
- Added `.env.example` and `SECURITY.md` (incl. instructions to rotate the
  previously committed Airflow `FERNET_KEY`).
- API error bodies are no longer dumped verbatim to logs (truncated, sanitized).
- docker-compose: disabled `LOAD_EXAMPLES`; deps baked into a custom image
  instead of installed at container start.

### Reliability (P0)
- `client.py` rewritten: pooled `requests.Session` with retry/backoff on
  429/5xx and connection errors; raises `FetchError` instead of `sys.exit(1)`.
- `loader.py` rewritten: engine singleton, transactional, idempotent **merge**
  (delete-by-key + insert) as the default `LOAD_STRATEGY=upsert`; legacy
  `replace` still available. Chunked multi-row inserts.
- Airflow DAG dependency bug fixed: the boolean `and` chain (which created **no**
  dependencies) replaced with real edges — dimensions → barrier → facts.
- `main.py` isolates per-pipeline failures and exits non-zero if any failed.

### Observability (P1)
- Central `logging_config.py` (text or JSON, env-driven level); all `print`
  calls replaced with structured logging.

### Data quality (P1)
- New `validation.py`: null/duplicate-key and required-column checks run before
  every load (warn by default, strict via `VALIDATION_STRICT`).

### Performance (P2)
- `transforms.explode_records` replaces per-row `DataFrame.iterrows()` loops in
  every pipeline with vectorised `explode` (large-frame speedups).

### Maintainability (P2)
- Shared helpers (`transforms.py`, `pipeline_utils.py`) remove duplicated ETL
  boilerplate across the 14 pipelines.
- Config is fully env-driven; `auth.json`/headers cached (read once).

### Tooling / deployment (P1)
- Split dependencies: `requirements.txt` (prod, pinned) and
  `requirements-dev.txt`. Removed the legacy misspelled `requerements.txt`.
- Added `Dockerfile` (custom Airflow image), `ruff.toml`, `pytest.ini`,
  `.dockerignore`.
- Added a test suite (`tests/`): transforms, loader (SQLite), client (mocked),
  validation, and pipeline transform behaviour.

### Known follow-ups (P3)
- API pagination for non-date-chunked endpoints.
- Real DDL migrations (PK/FK/indexes) instead of inferred `to_sql` schemas.
- Metrics/alerting integration (e.g. Slack on failure, freshness SLAs).
- Normalise `ENDPOINTS` key casing.
