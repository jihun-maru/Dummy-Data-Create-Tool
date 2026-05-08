from typing import Optional

from model.order import Order
from model.order_status import OrderStatus
from model.production_line import ProductionJob, ProductionLine
from persistence.order_repository import OrderRepository
from persistence.production_repository import ProductionRepository
from persistence.sample_repository import SampleRepository


class ProductionController:
    def __init__(
        self,
        production_line: ProductionLine,
        order_repo: OrderRepository,
        sample_repo: SampleRepository,
        production_repo: ProductionRepository,
    ) -> None:
        self._production_line = production_line
        self._order_repo = order_repo
        self._sample_repo = sample_repo
        self._production_repo = production_repo

    def get_current_production(self) -> Optional[ProductionJob]:
        return self._production_line.get_current_job()

    def get_waiting_queue(self) -> list[ProductionJob]:
        return self._production_line.get_waiting_jobs()

    def advance_production(self) -> Optional[Order]:
        current_job = self._production_line.get_current_job()
        if current_job is None:
            return None

        job = self._production_line.current_job
        order = self._order_repo.find_by_id(job.order.order_id)
        sample = self._sample_repo.find_by_id(job.sample.sample_id)

        sample.add_stock(job.actual_qty)
        order.transition_to(OrderStatus.CONFIRMED)

        self._sample_repo.save(sample)
        self._order_repo.save(order)

        self._production_line.complete_current_job()
        self._production_repo.save_state(self._production_line)

        return order
