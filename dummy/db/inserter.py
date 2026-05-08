from __future__ import annotations

from dummy.db.connection import get_connection, DEFAULT_DB_PATH
from dummy.db.schema import create_tables


class DummyInserter:
    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        with get_connection(self._db_path) as conn:
            create_tables(conn)

    def reset(self) -> None:
        """모든 테이블 데이터를 삭제한다. 테이블 구조는 유지한다."""
        with get_connection(self._db_path) as conn:
            # 외래 키 순서를 고려해 production_jobs → orders → samples 순으로 삭제
            conn.execute("DELETE FROM production_jobs")
            conn.execute("DELETE FROM orders")
            conn.execute("DELETE FROM samples")

    def insert_samples(self, samples: list) -> int:
        """
        Sample 객체 목록을 DB에 삽입한다.
        이미 존재하는 sample_id는 덮어쓴다 (INSERT OR REPLACE).
        삽입된 건수를 반환한다.
        """
        rows = [
            (s.sample_id, s.name, s.avg_production_time, s.yield_rate, s.stock)
            for s in samples
        ]
        with get_connection(self._db_path) as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO samples "
                "(sample_id, name, avg_production_time, yield_rate, stock) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )
        return len(rows)

    def insert_orders(self, orders: list) -> int:
        """
        Order 객체 목록을 DB에 삽입한다.
        status는 OrderStatus.value (문자열) 로 저장한다.
        삽입된 건수를 반환한다.
        """
        rows = [
            (
                o.order_id,
                o.sample_id,
                o.customer,
                o.quantity,
                o.status.value if hasattr(o.status, "value") else str(o.status),
            )
            for o in orders
        ]
        with get_connection(self._db_path) as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO orders "
                "(order_id, sample_id, customer, quantity, status) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )
        return len(rows)

    def insert_production_jobs(self, jobs: list) -> int:
        """
        생산 작업 dict 목록을 DB에 삽입한다.
        각 dict는 production_jobs 테이블 컬럼과 동일한 키를 가진다.
        삽입된 건수를 반환한다.
        """
        rows = [
            (
                job["order_id"],
                job["sample_id"],
                job["actual_qty"],
                job["total_time"],
                job.get("produced_qty", 0),
                job.get("is_current", 0),
            )
            for job in jobs
        ]
        with get_connection(self._db_path) as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO production_jobs "
                "(order_id, sample_id, actual_qty, total_time, produced_qty, is_current) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
        return len(rows)
