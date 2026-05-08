class MonitoringView:
    def display_orders_by_status(self, status_map: dict) -> None:
        # REJECTED는 표시하지 않음
        display_statuses = ["RESERVED", "PRODUCING", "CONFIRMED", "RELEASE"]
        print("=============================")
        print(" 주문 상태별 현황")
        print("=============================")
        for status_key in display_statuses:
            orders = status_map.get(status_key, [])
            print(f"[{status_key}] {len(orders)}건")
            if orders:
                print(f"  {'주문ID':<12} {'시료ID':<12} {'고객명':<12} {'수량':>6}")
                print("  " + "-" * 46)
                for order in orders:
                    print(
                        f"  {order.order_id:<12} {order.sample_id:<12} "
                        f"{order.customer:<12} {order.quantity:>6}"
                    )
        print("-----------------------------")

    def display_stock_status(self, stock_list: list) -> None:
        print("=============================")
        print(" 시료별 재고 현황")
        print("=============================")
        print(f"{'시료명':<16} {'재고':>6} {'상태':<6}")
        print("-----------------------------")
        for item in stock_list:
            print(f"{item['name']:<16} {item['stock']:>6} {item['status']:<6}")
        print("-----------------------------")
