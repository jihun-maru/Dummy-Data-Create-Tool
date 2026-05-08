from __future__ import annotations

import random

from model.order import Order
from model.order_status import OrderStatus
from model.sample import Sample

# 고객 후보 풀
CUSTOMER_POOL: list[str] = [
    "A연구소", "B팹리스", "C대학교", "D반도체",
    "E연구원", "F기업", "G랩", "H테크",
    "I연구소", "J반도체",
]

# 기본 상태 비율 (REJECTED는 정상 흐름 외이므로 생성하지 않음)
DEFAULT_STATUS_RATIO: dict[str, float] = {
    "RESERVED":  0.20,
    "PRODUCING": 0.20,
    "CONFIRMED": 0.30,
    "RELEASE":   0.30,
}

_STATUS_MAP: dict[str, OrderStatus] = {
    "RESERVED":  OrderStatus.RESERVED,
    "PRODUCING": OrderStatus.PRODUCING,
    "CONFIRMED": OrderStatus.CONFIRMED,
    "RELEASE":   OrderStatus.RELEASE,
}


def generate_orders(
    samples: list[Sample],
    count: int = 20,
    status_ratio: dict[str, float] | None = None,
) -> list[Order]:
    """
    samples 중 하나를 무작위로 선택해 count개의 Order를 생성한다.
    status_ratio로 상태별 분포를 제어한다 (합계가 1.0이 되도록 자동 정규화).
    order_id: O001, O002, ... (1-based, 3자리 zero-pad)
    quantity: 5~50 사이 랜덤 정수
    """
    if not samples:
        return []

    ratio = status_ratio or DEFAULT_STATUS_RATIO
    # 비율 정규화
    total = sum(ratio.values())
    normalized = {k: v / total for k, v in ratio.items()}

    # 각 상태별 건수 계산 (반올림 오차를 마지막 상태에 흡수)
    counts: dict[str, int] = {}
    assigned = 0
    keys = list(normalized.keys())
    for k in keys[:-1]:
        n = round(normalized[k] * count)
        counts[k] = n
        assigned += n
    counts[keys[-1]] = count - assigned

    # 상태별로 주문 생성 후 섞기
    orders: list[Order] = []
    order_num = 1
    for status_key, n in counts.items():
        status = _STATUS_MAP[status_key]
        for _ in range(n):
            order_id = f"O{order_num:03d}"
            sample = random.choice(samples)
            customer = random.choice(CUSTOMER_POOL)
            quantity = random.randint(5, 50)
            o = Order(order_id, sample.sample_id, customer, quantity)
            o.status = status
            orders.append(o)
            order_num += 1

    random.shuffle(orders)
    # order_id 재부여 (섞인 순서 반영)
    for i, o in enumerate(orders, start=1):
        o.order_id = f"O{i:03d}"

    return orders
