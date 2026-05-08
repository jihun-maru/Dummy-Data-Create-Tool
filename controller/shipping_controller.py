from typing import Optional

from model.order import Order
from model.order_status import OrderStatus
from persistence.order_repository import OrderRepository


class ShippingController:
    def __init__(self, order_repo: OrderRepository) -> None:
        self._order_repo = order_repo

    def list_confirmed_orders(self) -> list[Order]:
        return self._order_repo.find_by_status(OrderStatus.CONFIRMED)

    def ship_order(self, order_id: str) -> Order:
        order: Optional[Order] = self._order_repo.find_by_id(order_id)

        if order is None:
            raise ValueError(f"존재하지 않는 주문 ID: {order_id}")
        if order.status != OrderStatus.CONFIRMED:
            raise ValueError(
                f"CONFIRMED 상태가 아닌 주문은 출고할 수 없습니다: {order.status}"
            )

        order.transition_to(OrderStatus.RELEASE)
        self._order_repo.save(order)
        return order
