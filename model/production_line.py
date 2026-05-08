import math
from collections import deque
from typing import Optional

from model.order import Order
from model.sample import Sample


class ProductionJob:
    def __init__(self, order: Order, sample: Sample, actual_qty: int, total_time: float) -> None:
        self.order = order
        self.sample = sample
        self.actual_qty = actual_qty
        self.total_time = total_time
        self.produced_qty: int = 0


class ProductionLine:
    def __init__(self) -> None:
        self.current_job: Optional[ProductionJob] = None
        self.queue: deque[ProductionJob] = deque()

    def enqueue(self, order: Order, sample: Sample) -> ProductionJob:
        shortage = max(0, order.quantity - sample.stock)
        actual_qty = math.ceil(shortage / (sample.yield_rate * 0.9))
        total_time = sample.avg_production_time * actual_qty

        job = ProductionJob(order, sample, actual_qty, total_time)

        if self.current_job is None and len(self.queue) == 0:
            self.current_job = job
        else:
            self.queue.append(job)

        return job

    def complete_current_job(self) -> Optional[ProductionJob]:
        completed = self.current_job
        if self.queue:
            self.current_job = self.queue.popleft()
        else:
            self.current_job = None
        return completed

    def get_current_job(self) -> Optional[ProductionJob]:
        return self.current_job

    def get_waiting_jobs(self) -> list[ProductionJob]:
        return list(self.queue)
