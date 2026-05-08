from typing import Optional

from model.sample import Sample
from persistence.sample_repository import SampleRepository


class SampleController:
    def __init__(self, sample_repo: SampleRepository) -> None:
        self._sample_repo = sample_repo

    def register_sample(
        self,
        sample_id: str,
        name: str,
        avg_time: float,
        yield_rate: float,
    ) -> Sample:
        if self._sample_repo.find_by_id(sample_id) is not None:
            raise ValueError(f"이미 존재하는 시료 ID: {sample_id}")
        sample = Sample(sample_id, name, avg_time, yield_rate)
        self._sample_repo.save(sample)
        return sample

    def list_samples(self) -> list[Sample]:
        return self._sample_repo.load_all()

    def search_sample(self, name: str) -> list[Sample]:
        return [s for s in self._sample_repo.load_all() if name in s.name]

    def get_sample(self, sample_id: str) -> Optional[Sample]:
        return self._sample_repo.find_by_id(sample_id)
