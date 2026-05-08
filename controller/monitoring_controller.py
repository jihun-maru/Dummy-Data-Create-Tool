from model.order import Order
from model.order_status import OrderStatus
from persistence.order_repository import OrderRepository
from persistence.sample_repository import SampleRepository

_MONITORED_STATUSES = [
    OrderStatus.RESERVED,
    OrderStatus.PRODUCING,
    OrderStatus.CONFIRMED,
    OrderStatus.RELEASE,
]

_ACTIVE_STATUSES = {OrderStatus.CONFIRMED, OrderStatus.PRODUCING}


class MonitoringController:
    def __init__(self, order_repo: OrderRepository, sample_repo: SampleRepository) -> None:
        self._order_repo = order_repo
        self._sample_repo = sample_repo

    def get_orders_by_status(self) -> dict[OrderStatus, list[Order]]:
        result: dict[OrderStatus, list[Order]] = {s: [] for s in _MONITORED_STATUSES}
        for order in self._order_repo.load_all():
            if order.status in result:
                result[order.status].append(order)
        return result

    def get_stock_status(self) -> list[dict]:
        orders = self._order_repo.load_all()
        samples = self._sample_repo.load_all()

        # 시료별 CONFIRMED + PRODUCING 수량 합계 계산
        active_qty: dict[str, int] = {}
        for order in orders:
            if order.status in _ACTIVE_STATUSES:
                active_qty[order.sample_id] = (
                    active_qty.get(order.sample_id, 0) + order.quantity
                )

        result = []
        for sample in samples:
            stock = sample.stock
            total_active = active_qty.get(sample.sample_id, 0)

            if stock == 0:
                label = "고갈"
            elif stock < total_active:
                label = "부족"
            else:
                label = "여유"

            result.append({"sample": sample, "stock": stock, "label": label})

        return result
