class OrderView:
    def display_order_menu(self) -> None:
        print("-----------------------------")
        print(" 주문 관리")
        print("-----------------------------")
        print("1. 주문 접수")
        print("2. 주문 승인 / 거절")
        print("0. 뒤로")
        print("-----------------------------")

    def get_order_input(self) -> dict:
        sample_id = input("시료 ID > ")
        customer = input("고객명 > ")
        quantity = int(input("수량 > "))
        return {
            "sample_id": sample_id,
            "customer": customer,
            "quantity": quantity,
        }

    def display_reserved_orders(self, orders: list) -> None:
        if not orders:
            print("[목록] 접수된 주문이 없습니다.")
            return
        print("-----------------------------")
        print(f"{'번호':>4} {'주문ID':<12} {'시료ID':<12} {'고객명':<12} {'수량':>6} {'상태':<10}")
        print("-----------------------------")
        for idx, order in enumerate(orders, start=1):
            print(
                f"{idx:>4} {order.order_id:<12} {order.sample_id:<12} "
                f"{order.customer:<12} {order.quantity:>6} {order.status.value:<10}"
            )
        print("-----------------------------")

    def get_order_choice(self) -> str:
        return input("처리할 주문 ID 입력 > ")

    def get_approve_or_reject(self) -> str:
        return input("1. 승인 / 2. 거절 선택 > ")

    def display_order_result(self, order) -> None:
        print("-----------------------------")
        print(f"[처리 결과] 주문ID: {order.order_id} | 최종 상태: {order.status.value}")
        print("-----------------------------")

    def get_order_menu_choice(self) -> str:
        return input("선택 > ")
