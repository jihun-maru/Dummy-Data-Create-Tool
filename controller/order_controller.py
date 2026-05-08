import uuid
from typing import Optional

from model.order import Order
from model.order_status import OrderStatus
from model.production_line import ProductionLine
from persistence.order_repository import OrderRepository
from persistence.production_repository import ProductionRepository
from persistence.sample_repository import SampleRepository


class OrderController:
    def __init__(
        self,
        order_repo: OrderRepository,
        sample_repo: SampleRepository,
        production_line: ProductionLine,
        production_repo: ProductionRepository,
    ) -> None:
        self._order_repo = order_repo
        self._sample_repo = sample_repo
        self._production_line = production_line
        self._production_repo = production_repo

    def place_order(self, sample_id: str, customer: str, quantity: int) -> Order:
        if self._sample_repo.find_by_id(sample_id) is None:
            raise ValueError(f"존재하지 않는 시료 ID: {sample_id}")
        order_id = str(uuid.uuid4())
        order = Order(order_id, sample_id, customer, quantity)
        self._order_repo.save(order)
        return order

    def approve_order(self, order_id: str) -> Order:
        order = self._order_repo.find_by_id(order_id)
        if order is None:
            raise ValueError(f"존재하지 않는 주문 ID: {order_id}")
        if order.status != OrderStatus.RESERVED:
            raise ValueError(f"RESERVED 상태가 아닌 주문은 승인할 수 없습니다: {order.status}")

        sample = self._sample_repo.find_by_id(order.sample_id)
        if sample.stock >= order.quantity:
            sample.consume_stock(order.quantity)
            self._sample_repo.save(sample)
            order.transition_to(OrderStatus.CONFIRMED)
            self._order_repo.save(order)
        else:
            self._production_line.enqueue(order, sample)
            order.transition_to(OrderStatus.PRODUCING)
            self._order_repo.save(order)
            self._production_repo.save_state(self._production_line)

        return order

    def reject_order(self, order_id: str) -> Order:
        order = self._order_repo.find_by_id(order_id)
        if order is None:
            raise ValueError(f"존재하지 않는 주문 ID: {order_id}")
        if order.status != OrderStatus.RESERVED:
            raise ValueError(f"RESERVED 상태가 아닌 주문은 거절할 수 없습니다: {order.status}")
        order.transition_to(OrderStatus.REJECTED)
        self._order_repo.save(order)
        return order

    def list_reserved_orders(self) -> list[Order]:
        return self._order_repo.find_by_status(OrderStatus.RESERVED)
