class ShippingView:
    def display_confirmed_orders(self, orders: list) -> None:
        if not orders:
            print("[목록] 출고 대기 중인 주문이 없습니다.")
            return
        print("-----------------------------")
        print(f"{'번호':>4} {'주문ID':<12} {'시료ID':<12} {'고객명':<12} {'수량':>6}")
        print("-----------------------------")
        for idx, order in enumerate(orders, start=1):
            print(
                f"{idx:>4} {order.order_id:<12} {order.sample_id:<12} "
                f"{order.customer:<12} {order.quantity:>6}"
            )
        print("-----------------------------")

    def get_ship_choice(self) -> str:
        return input("출고할 주문 ID 입력 > ")

    def display_ship_result(self, order) -> None:
        print(f"출고 완료: {order.order_id} → {order.status.value}")
