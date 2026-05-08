from __future__ import annotations

from typing import Optional

from model.order import Order
from model.order_status import OrderStatus
from persistence.base_repository import BaseRepository


class OrderRepository(BaseRepository):

    def save_all(self, orders: list[Order]) -> None:
        self._write_json([self._serialize(o) for o in orders])

    def load_all(self) -> list[Order]:
        raw = self._read_json()
        if not raw:
            return []
        return [self._deserialize(d) for d in raw]

    def find_by_id(self, order_id: str) -> Optional[Order]:
        for o in self.load_all():
            if o.order_id == order_id:
                return o
        return None

    def save(self, order: Order) -> None:
        """신규면 추가, 기존 ID면 덮어씌운다 (upsert)."""
        orders = self.load_all()
        for i, o in enumerate(orders):
            if o.order_id == order.order_id:
                orders[i] = order
                self.save_all(orders)
                return
        orders.append(order)
        self.save_all(orders)

    def delete(self, order_id: str) -> None:
        self.save_all([o for o in self.load_all() if o.order_id != order_id])

    def find_by_status(self, status: OrderStatus) -> list[Order]:
        return [o for o in self.load_all() if o.status == status]

    # ── 직렬화 헬퍼 ──────────────────────────────────────────
    def _serialize(self, order: Order) -> dict:
        return {
            "order_id": order.order_id,
            "sample_id": order.sample_id,
            "customer": order.customer,
            "quantity": order.quantity,
            "status": order.status.value,  # Enum → 문자열
        }

    def _deserialize(self, data: dict) -> Order:
        # Order.__init__(order_id, sample_id, customer, quantity)
        # status는 생성자 외부에서 Enum으로 복원
        o = Order(
            data["order_id"],
            data["sample_id"],
            data["customer"],
            data["quantity"],
        )
        o.status = OrderStatus(data["status"])  # 문자열 → Enum
        return o
