class Sample:
    def __init__(
        self,
        sample_id: str,
        name: str,
        avg_production_time: float,
        yield_rate: float,
    ) -> None:
        self.sample_id = sample_id
        self.name = name
        self.avg_production_time = avg_production_time
        self.yield_rate = yield_rate
        self.stock: int = 0

    def add_stock(self, qty: int) -> None:
        self.stock += qty

    def consume_stock(self, qty: int) -> None:
        self.stock = max(0, self.stock - qty)
