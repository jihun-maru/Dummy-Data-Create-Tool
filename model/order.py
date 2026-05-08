from model.order_status import OrderStatus


class Order:
    def __init__(
        self,
        order_id: str,
        sample_id: str,
        customer: str,
        quantity: int,
    ) -> None:
        self.order_id = order_id
        self.sample_id = sample_id
        self.customer = customer
        self.quantity = quantity
        self.status: OrderStatus = OrderStatus.RESERVED

    def transition_to(self, status: OrderStatus) -> None:
        self.status = status
