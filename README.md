# SmartUp ETL

ETL pipeline that pulls data from the SmartUp ERP API, transforms it with
pandas, and loads it into PostgreSQL (and optional Excel exports). Runs
stand-alone (`python main.py`) or on a schedule via Apache Airflow.

---

## Architecture

```
SmartUp API ──> core/client.py ──> pipelines/*.py ──> core.pipeline_utils.emit() ──> core/loader.py ──> PostgreSQL
                (fetch,             (transform,          (validate +                   (idempotent
                 retry)              explode)             Excel + load)                 merge)
```

Reusable building blocks live in the **`core/`** package; one pipeline per SmartUp
entity lives in **`pipelines/`** and imports from `core.*`.

| Module | Role |
| --- | --- |
| [core/config.py](core/config.py) | Env-driven config: endpoints, DB URL, auth, retry/load settings. No secrets in source. |
| [core/client.py](core/client.py) | `fetch` / `fetch_post` — pooled `requests.Session` with retry/backoff; raises `FetchError`. |
| [core/transforms.py](core/transforms.py) | Vectorised helpers: `explode_records`, `to_int64`, `to_numeric`, `select`. |
| [core/validation.py](core/validation.py) | Pre-load data-quality checks (null/duplicate keys); warn or strict. |
| [core/loader.py](core/loader.py) | `save_to_db` — engine singleton, transactional, idempotent merge (or legacy replace). |
| [core/pipeline_utils.py](core/pipeline_utils.py) | `emit` — validate + optional Excel + load, in one call. |
| [core/logging_config.py](core/logging_config.py) | Central logging (text or JSON, env-driven level); `core/exceptions.py` — typed errors. |
| [main.py](main.py) | Entry point — runs every pipeline with per-pipeline failure isolation. |
| [dags/smartup_etl_dag.py](dags/smartup_etl_dag.py) | Airflow DAG (dimensions → barrier → facts). |

---

## Quick start

```bash
python -m venv .venv && . .venv/Scripts/activate
pip install -r requirements.txt          # prod   (or requirements-dev.txt for tests)

cp .env.example .env                      # then fill in credentials
#   SMARTUP_USERNAME / SMARTUP_PASSWORD   (or create auth.json)
#   DB_PASSWORD (or full DB_URL)

python main.py
```

### Configuration (environment variables)

| Variable | Default | Purpose |
| --- | --- | --- |
| `SMARTUP_USERNAME` / `SMARTUP_PASSWORD` | — | API credentials (fallback: `auth.json`) |
| `DB_URL` *or* `DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`/`DB_NAME` | localhost/smartup | Target database |
| `LOAD_STRATEGY` | `upsert` | `upsert` (idempotent merge) or `replace` (legacy) |
| `WRITE_EXCEL` | `true` | Also export each table to `CleanedData/*.xlsx` |
| `ORDERS_BEGIN_DATE` | `01.01.2026` | Start date for the orders backfill |
| `VALIDATION_STRICT` | `false` | Raise (vs warn) on data-quality failures |
| `LOG_LEVEL` / `LOG_JSON` | `INFO` / `false` | Logging verbosity / structured output |

A local `.env` is loaded automatically; real environment variables always win.

---

## Load strategy & idempotency

Every table refreshes by a **single parent-entity id** — a dimension by its own
id, a child/bridge table by its parent id. The default `upsert` strategy, inside
one transaction, deletes the rows whose key appears in the incoming batch and
re-inserts them. This means:

- **Idempotent** — re-running a load produces the same result, no duplicates.
- **History-preserving** — entities not in the batch are left untouched (the
  table and its indexes are never dropped).
- **Atomic** — a mid-run failure rolls back instead of leaving a torn table.

Set `LOAD_STRATEGY=replace` to fall back to the legacy drop-and-recreate.

---

## Pipelines and tables

| Pipeline | Tables |
| --- | --- |
| `products` | `products`, `product_group`, `product_inventory_kind`, `product_sector` |
| `orders` | `orders`, `order_products`, `order_gifts`, `order_actions`, `order_consignments` |
| `natural_person` | `natural_persons`, `natural_person_group`, `natural_person_room` |
| `legal_person` | `legal_persons`, `legal_person_group`, `legal_person_bank_account`, `legal_person_room` |
| `visit` | `visits`, `visit_person_types`, `visit_comments` |
| `writeoff` | `writeoffs`, `writeoff_items` |
| `payments` | `payments` |
| `cash_operations` | `cash_operations`, `cash_operation_refs` |
| `product_group` | `product_groups`, `product_group_types` |
| `inventory_price` | `inventory_prices` |
| `person_group` | `person_groups`, `person_group_types` |
| `returns` | `returns`, `return_products` |
| `returns_to_supplier` | `supplier_returns`, `supplier_return_items` |

---

## Adding a new pipeline

1. Add the endpoint to `ENDPOINTS` in [core/config.py](core/config.py).
2. Create `pipelines/<name>.py`:

```python
from core.client import fetch
from core.config import ENDPOINTS, get_headers
from core.pipeline_utils import emit
from core.transforms import select, to_int64

def build_entity(raw):
    df = select(raw, ["entity_id", "name", ...])
    to_int64(df, ["entity_id"])
    return df.drop_duplicates(subset=["entity_id"]).reset_index(drop=True)

def run():
    raw = fetch(ENDPOINTS["entity"], get_headers(), key="entity")
    if raw.empty:
        return
    emit(build_entity(raw), excel_name="entity.xlsx", table="entity",
         key="entity_id", unique=True)
```

3. Register it in `PIPELINES` in [main.py](main.py) and as a task in the DAG.

---

## Running on Airflow

```bash
docker compose build       # builds the custom image (deps baked in)
docker compose up -d
```

The DAG `smartup_etl` runs daily at 02:00: dimension pipelines in parallel, a
barrier, then the fact pipelines in parallel. Each task retries with backoff.
The ETL writes to the warehouse DB configured via `DB_URL`/`DB_*` env vars (not
the Airflow metadata database).

---

## Testing & linting

```bash
pip install -r requirements-dev.txt
pytest          # unit + integration (loader on SQLite, client mocked)
ruff check .
```

---

## Security

See [SECURITY.md](SECURITY.md). In short: secrets live in `.env` / `auth.json`
(both gitignored); rotate the previously committed Airflow `FERNET_KEY`.
