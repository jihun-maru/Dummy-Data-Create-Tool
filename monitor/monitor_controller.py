from __future__ import annotations

from persistence.sample_repository import SampleRepository
from persistence.order_repository import OrderRepository
from persistence.production_repository import ProductionRepository
from model.order_status import OrderStatus


class MonitorController:
    def __init__(
        self,
        sample_repo: SampleRepository,
        order_repo: OrderRepository,
        production_repo: ProductionRepository,
    ) -> None:
        self._sample_repo = sample_repo
        self._order_repo = order_repo
        self._production_repo = production_repo

    def get_stock_summary(self) -> list[dict]:
        """
        각 시료에 대해 아래 dict를 담은 리스트를 반환한다.
        {
            "sample_id": str,
            "name": str,
            "stock": int,
            "status": str,   # "여유" | "부족" | "고갈"
        }

        재고 상태 판단 기준:
        - 고갈: stock == 0
        - 부족: 0 < stock < (CONFIRMED + PRODUCING 주문 수량 합계)
        - 여유: stock >= (CONFIRMED + PRODUCING 주문 수량 합계)
        """
        samples = self._sample_repo.load_all()
        orders = self._order_repo.load_all()

        result = []
        for sample in samples:
            status = self._calc_stock_status(sample.stock, sample.sample_id, orders)
            result.append({
                "sample_id": sample.sample_id,
                "name": sample.name,
                "stock": sample.stock,
                "status": status,
            })
        return result

    def get_order_summary(self) -> dict[str, int]:
        """
        상태별 주문 건수를 반환한다. REJECTED 제외.
        반환 예:
        {
            "RESERVED": 2,
            "PRODUCING": 1,
            "CONFIRMED": 3,
            "RELEASE": 5,
        }
        키는 항상 4개 모두 포함한다 (건수 0이어도 포함).
        """
        summary: dict[str, int] = {
            "RESERVED": 0,
            "PRODUCING": 0,
            "CONFIRMED": 0,
            "RELEASE": 0,
        }
        for order in self._order_repo.load_all():
            key = order.status.value
            if key in summary:
                summary[key] += 1
        return summary

    def get_production_summary(self) -> dict:
        """
        production_repo.load_state() 의 raw dict를 그대로 반환한다.
        파일이 없거나 비어 있으면 {"current_job": None, "queue": []} 를 반환한다.
        """
        state = self._production_repo.load_state()
        if not state:
            return {"current_job": None, "queue": []}
        return {
            "current_job": state.get("current_job", None),
            "queue": state.get("queue", []),
        }

    def _calc_stock_status(self, stock: int, sample_id: str, orders: list) -> str:
        active_qty = sum(
            o.quantity
            for o in orders
            if o.sample_id == sample_id
            and o.status in (OrderStatus.CONFIRMED, OrderStatus.PRODUCING)
        )
        if stock == 0:
            return "고갈"
        if stock < active_qty:
            return "부족"
        return "여유"
