from __future__ import annotations

import random

from model.sample import Sample

# 반도체 소재 기반 시료 후보 풀: (이름, 평균생산시간(h), 수율)
SAMPLE_POOL: list[tuple[str, float, float]] = [
    ("GaN 웨이퍼",     2.5, 0.90),
    ("SiC 웨이퍼",     3.0, 0.85),
    ("InP 웨이퍼",     4.0, 0.80),
    ("GaAs 웨이퍼",    2.0, 0.88),
    ("Si 웨이퍼",      1.5, 0.95),
    ("Ge 웨이퍼",      2.8, 0.82),
    ("AlN 웨이퍼",     3.5, 0.78),
    ("ZnO 웨이퍼",     2.2, 0.87),
    ("InGaAs 웨이퍼",  4.5, 0.75),
    ("AlGaN 웨이퍼",   3.8, 0.83),
]


def generate_samples(count: int = 5) -> list[Sample]:
    """
    SAMPLE_POOL에서 count개를 중복 없이 선택하여 Sample 객체 목록을 반환한다.
    count가 SAMPLE_POOL 크기를 초과하면 SAMPLE_POOL 전체를 반환한다.
    sample_id: S001, S002, ... (1-based, 3자리 zero-pad)
    stock: 0~200 사이 랜덤 정수
    """
    count = min(count, len(SAMPLE_POOL))
    selected = random.sample(SAMPLE_POOL, count)
    samples: list[Sample] = []
    for i, (name, avg_time, yield_rate) in enumerate(selected, start=1):
        sample_id = f"S{i:03d}"
        stock = random.randint(0, 200)
        s = Sample(sample_id, name, avg_time, yield_rate)
        s.stock = stock
        samples.append(s)
    return samples
