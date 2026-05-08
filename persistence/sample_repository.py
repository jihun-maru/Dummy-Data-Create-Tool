from __future__ import annotations

from typing import Optional

from model.sample import Sample
from persistence.base_repository import BaseRepository


class SampleRepository(BaseRepository):

    def save_all(self, samples: list[Sample]) -> None:
        self._write_json([self._serialize(s) for s in samples])

    def load_all(self) -> list[Sample]:
        raw = self._read_json()
        if not raw:
            return []
        return [self._deserialize(d) for d in raw]

    def find_by_id(self, sample_id: str) -> Optional[Sample]:
        for s in self.load_all():
            if s.sample_id == sample_id:
                return s
        return None

    def save(self, sample: Sample) -> None:
        """신규면 추가, 기존 ID면 덮어씌운다 (upsert)."""
        samples = self.load_all()
        for i, s in enumerate(samples):
            if s.sample_id == sample.sample_id:
                samples[i] = sample
                self.save_all(samples)
                return
        samples.append(sample)
        self.save_all(samples)

    def delete(self, sample_id: str) -> None:
        self.save_all([s for s in self.load_all() if s.sample_id != sample_id])

    # ── 직렬화 헬퍼 ──────────────────────────────────────────
    def _serialize(self, sample: Sample) -> dict:
        return {
            "sample_id": sample.sample_id,
            "name": sample.name,
            "avg_production_time": sample.avg_production_time,
            "yield_rate": sample.yield_rate,
            "stock": sample.stock,
        }

    def _deserialize(self, data: dict) -> Sample:
        # Sample.__init__(sample_id, name, avg_production_time, yield_rate)
        # stock은 생성자 외부에서 할당 (기본값 0으로 초기화됨)
        s = Sample(
            data["sample_id"],
            data["name"],
            data["avg_production_time"],
            data["yield_rate"],
        )
        s.stock = data["stock"]
        return s
