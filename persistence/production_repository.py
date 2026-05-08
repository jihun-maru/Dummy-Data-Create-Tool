from __future__ import annotations

from typing import Optional

from model.production_line import ProductionJob, ProductionLine
from persistence.base_repository import BaseRepository


class ProductionRepository(BaseRepository):

    # BaseRepository 추상 메서드 최소 구현
    def save_all(self, entities: list) -> None:
        pass

    def load_all(self) -> list:
        return []

    # ── 주요 인터페이스 ──────────────────────────────────────
    def save_state(self, production_line: ProductionLine) -> None:
        """ProductionLine 의 현재 상태를 파일에 저장한다."""
        data = {
            "current_job": (
                self._serialize_job(production_line.current_job)
                if production_line.current_job
                else None
            ),
            "queue": [
                self._serialize_job(job) for job in production_line.queue
            ],
        }
        self._write_json(data)

    def load_state(self) -> Optional[dict]:
        """저장된 상태를 raw dict로 반환한다. 파일이 없으면 None."""
        return self._read_json()

    # ── 직렬화 헬퍼 ──────────────────────────────────────────
    def _serialize_job(self, job: ProductionJob) -> dict:
        # ProductionJob.order: Order, ProductionJob.sample: Sample
        return {
            "order_id": job.order.order_id,
            "sample_id": job.sample.sample_id,
            "actual_qty": job.actual_qty,
            "total_time": job.total_time,
            "produced_qty": job.produced_qty,
        }
