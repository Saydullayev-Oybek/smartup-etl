"""Entry point: run every SmartUp ETL pipeline sequentially.

Each pipeline is isolated — a failure in one is logged and recorded but does
not stop the others. The process exits non-zero if any pipeline failed, so
schedulers and CI detect the failure.
"""
from __future__ import annotations

import os
import sys

from core.logging_config import configure_logging, get_logger
from core.pipeline_utils import ensure_output_dir
from pipelines import (
    bank_statements,
    cash_operations,
    inventory_price,
    legal_person,
    natural_person,
    orders,
    payments,
    person_group,
    product_group,
    products,
    returns,
    returns_to_supplier,
    visit,
    writeoff,
)

configure_logging()
log = get_logger(__name__)

ORDERS_BEGIN_DATE = os.getenv("ORDERS_BEGIN_DATE", "01.01.2026")

# (name, callable) — order matters: dimensions before facts.
PIPELINES = [
    ("products",            products.run),
    ("product_group",       product_group.run),
    ("person_group",        person_group.run),
    ("natural_person",      natural_person.run),
    ("legal_person",        legal_person.run),
    ("inventory_price",     inventory_price.run),
    ("visit",               visit.run),
    ("writeoff",            writeoff.run),
    ("payments",            payments.run),
    ("cash_operations",     cash_operations.run),
    ("returns",             returns.run),
    ("returns_to_supplier", returns_to_supplier.run),
    ("bank_statements",     bank_statements.run),
    ("orders",              lambda: orders.run(begin_date=ORDERS_BEGIN_DATE)),
]


def main() -> int:
    ensure_output_dir()
    failures: list[str] = []

    for name, runner in PIPELINES:
        try:
            runner()
        except Exception:  # noqa: BLE001 — isolate one pipeline's failure
            log.exception("Pipeline '%s' failed", name)
            failures.append(name)

    if failures:
        log.error("ETL finished with %d failure(s): %s", len(failures), ", ".join(failures))
        return 1

    log.info("ETL finished successfully (%d pipelines).", len(PIPELINES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
