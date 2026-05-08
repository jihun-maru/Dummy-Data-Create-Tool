from __future__ import annotations

import sqlite3

DDL_SAMPLES = """
CREATE TABLE IF NOT EXISTS samples (
    sample_id            TEXT PRIMARY KEY,
    name                 TEXT    NOT NULL,
    avg_production_time  REAL    NOT NULL,
    yield_rate           REAL    NOT NULL,
    stock                INTEGER NOT NULL
)
"""

DDL_ORDERS = """
CREATE TABLE IF NOT EXISTS orders (
    order_id   TEXT PRIMARY KEY,
    sample_id  TEXT    NOT NULL,
    customer   TEXT    NOT NULL,
    quantity   INTEGER NOT NULL,
    status     TEXT    NOT NULL,
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id)
)
"""

DDL_PRODUCTION_JOBS = """
CREATE TABLE IF NOT EXISTS production_jobs (
    order_id     TEXT PRIMARY KEY,
    sample_id    TEXT    NOT NULL,
    actual_qty   INTEGER NOT NULL,
    total_time   REAL    NOT NULL,
    produced_qty INTEGER NOT NULL DEFAULT 0,
    is_current   INTEGER NOT NULL DEFAULT 0
)
"""


def create_tables(conn: sqlite3.Connection) -> None:
    conn.execute(DDL_SAMPLES)
    conn.execute(DDL_ORDERS)
    conn.execute(DDL_PRODUCTION_JOBS)
