"""Airflow DAG for the SmartUp ETL.

Dimension pipelines run first (in parallel), a barrier task gates on their
completion, then the fact/transaction pipelines run (in parallel). Each task
is isolated, retried on failure, and reports via Airflow's normal task state —
no more boolean ``and`` chaining (which created *no* real dependencies).
"""
import os
import sys
from datetime import datetime, timedelta

from airflow.decorators import dag, task

# Project is mounted read-only at this path by docker-compose.
sys.path.insert(0, "/opt/airflow/smartup_etl")

ORDERS_BEGIN_DATE = os.getenv("ORDERS_BEGIN_DATE", "01.01.2026")

default_args = {
    "owner": "smartup",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "email_on_failure": False,
}


def _run(module_name: str, **kwargs) -> None:
    """Import a pipeline module and run it (lazy import keeps DAG parsing fast)."""
    from importlib import import_module

    from core.pipeline_utils import ensure_output_dir

    ensure_output_dir()
    import_module(f"pipelines.{module_name}").run(**kwargs)


@dag(
    dag_id="smartup_etl",
    default_args=default_args,
    description="SmartUp ERP - daily ETL for all pipelines",
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["smartup", "etl"],
)
def smartup_etl():

    # ── Dimension / reference pipelines ───────────────────────────────────────
    @task
    def products():        _run("products")

    @task
    def product_group():   _run("product_group")

    @task
    def person_group():    _run("person_group")

    @task
    def natural_person():  _run("natural_person")

    @task
    def legal_person():    _run("legal_person")

    @task
    def inventory_price(): _run("inventory_price")

    @task
    def dimensions_ready():
        """Barrier: all dimension pipelines have completed."""

    # ── Fact / transaction pipelines ──────────────────────────────────────────
    @task
    def visit():               _run("visit")

    @task
    def writeoff():            _run("writeoff")

    @task
    def payments():            _run("payments")

    @task
    def cash_operations():     _run("cash_operations")

    @task
    def returns():             _run("returns")

    @task
    def returns_to_supplier(): _run("returns_to_supplier")

    @task
    def orders():              _run("orders", begin_date=ORDERS_BEGIN_DATE)

    dims = [products(), product_group(), person_group(),
            natural_person(), legal_person(), inventory_price()]
    facts = [visit(), writeoff(), payments(), cash_operations(),
             returns(), returns_to_supplier(), orders()]

    barrier = dimensions_ready()
    for d in dims:
        d >> barrier
    for f in facts:
        barrier >> f


smartup_etl()
