from __future__ import annotations

import math
import random

from model.order import Order
from model.order_status import OrderStatus
from model.sample import Sample


def generate_production_jobs(
    orders: list[Order],
    samples: list[Sample],
) -> list[dict]:
    """
    PRODUCING 상태 주문에 대해서만 생산 작업 dict를 생성한다.
    - 첫 번째 PRODUCING 주문: is_current=1, produced_qty는 0~actual_qty 사이 랜덤
    - 나머지 PRODUCING 주문: is_current=0, produced_qty=0

    반환값 각 dict 구조:
    {
        "order_id":    str,
        "sample_id":   str,
        "actual_qty":  int,
        "total_time":  float,
        "produced_qty": int,
        "is_current":  int,   # 0 또는 1
    }

    생산 계산식:
        actual_qty = ceil(quantity / (yield_rate * 0.9))
        total_time = avg_production_time * actual_qty
    """
    sample_map: dict[str, Sample] = {s.sample_id: s for s in samples}
    producing_orders = [o for o in orders if o.status == OrderStatus.PRODUCING]

    jobs: list[dict] = []
    for idx, order in enumerate(producing_orders):
        sample = sample_map.get(order.sample_id)
        if sample is None:
            continue

        actual_qty = math.ceil(order.quantity / (sample.yield_rate * 0.9))
        total_time = sample.avg_production_time * actual_qty
        is_current = 1 if idx == 0 else 0
        produced_qty = random.randint(0, actual_qty) if is_current else 0

        jobs.append({
            "order_id":    order.order_id,
            "sample_id":   order.sample_id,
            "actual_qty":  actual_qty,
            "total_time":  round(total_time, 2),
            "produced_qty": produced_qty,
            "is_current":  is_current,
        })

    return jobs
