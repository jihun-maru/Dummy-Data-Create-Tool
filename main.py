from controller.sample_controller import SampleController
from controller.order_controller import OrderController
from controller.monitoring_controller import MonitoringController
from controller.shipping_controller import ShippingController
from controller.production_controller import ProductionController
from model.production_line import ProductionLine, ProductionJob
from persistence.sample_repository import SampleRepository
from persistence.order_repository import OrderRepository
from persistence.production_repository import ProductionRepository
from view.main_menu_view import MainMenuView
from view.sample_view import SampleView
from view.order_view import OrderView
from view.monitoring_view import MonitoringView
from view.shipping_view import ShippingView
from view.production_view import ProductionView


def _restore_production_state(
    production_line: ProductionLine,
    production_repo: ProductionRepository,
    order_repo: OrderRepository,
    sample_repo: SampleRepository,
) -> None:
    """프로그램 재시작 시 저장된 ProductionLine 상태를 복원한다."""
    state = production_repo.load_state()
    if not state:
        return

    def _make_job(job_data: dict) -> ProductionJob:
        order = order_repo.find_by_id(job_data["order_id"])
        sample = sample_repo.find_by_id(job_data["sample_id"])
        job = ProductionJob(order, sample, job_data["actual_qty"], job_data["total_time"])
        job.produced_qty = job_data["produced_qty"]
        return job

    if state.get("current_job"):
        production_line.current_job = _make_job(state["current_job"])
    for job_data in state.get("queue", []):
        production_line.queue.append(_make_job(job_data))


def main():
    # Repository 초기화 (data/ 디렉토리는 자동 생성됨)
    sample_repo = SampleRepository("data/samples.json")
    order_repo = OrderRepository("data/orders.json")
    production_repo = ProductionRepository("data/production.json")

    # ProductionLine 초기화 + 저장된 상태 복원
    production_line = ProductionLine()
    _restore_production_state(production_line, production_repo, order_repo, sample_repo)

    # Controller 의존성 주입
    sample_ctrl = SampleController(sample_repo)
    order_ctrl = OrderController(order_repo, sample_repo, production_line, production_repo)
    monitoring_ctrl = MonitoringController(order_repo, sample_repo)
    shipping_ctrl = ShippingController(order_repo)
    production_ctrl = ProductionController(production_line, order_repo, sample_repo, production_repo)

    menu_view = MainMenuView()
    sample_view = SampleView()
    order_view = OrderView()
    monitoring_view = MonitoringView()
    shipping_view = ShippingView()
    production_view = ProductionView()

    while True:
        sample_list = sample_ctrl.list_samples()
        menu_view.display_summary(sample_list)
        menu_view.display_menu()
        choice = menu_view.get_menu_choice()

        if choice == "1":
            # 시료관리 서브루프
            while True:
                sample_view.display_sample_menu()
                sub = sample_view.get_sample_menu_choice()

                if sub == "1":
                    try:
                        data = sample_view.get_register_input()
                        sample = sample_ctrl.register_sample(
                            data["sample_id"],
                            data["name"],
                            data["avg_production_time"],
                            data["yield_rate"],
                        )
                        sample_view.display_sample_list([sample])
                    except ValueError as e:
                        print(f"[오류] {e}")

                elif sub == "2":
                    sample_list = sample_ctrl.list_samples()
                    sample_view.display_sample_list(sample_list)

                elif sub == "3":
                    keyword = sample_view.get_search_keyword()
                    results = sample_ctrl.search_sample(keyword)
                    sample_view.display_search_result(results)

                elif sub == "0":
                    break
                else:
                    print("잘못된 입력입니다.")

        elif choice == "2":
            # 주문 서브루프
            while True:
                order_view.display_order_menu()
                sub = order_view.get_order_menu_choice()

                if sub == "1":
                    try:
                        data = order_view.get_order_input()
                        order = order_ctrl.place_order(
                            data["sample_id"],
                            data["customer"],
                            data["quantity"],
                        )
                        order_view.display_order_result(order)
                    except ValueError as e:
                        print(f"[오류] {e}")

                elif sub == "2":
                    reserved = order_ctrl.list_reserved_orders()
                    order_view.display_reserved_orders(reserved)
                    if reserved:
                        try:
                            order_id = order_view.get_order_choice()
                            action = order_view.get_approve_or_reject()
                            if action == "1":
                                result = order_ctrl.approve_order(order_id)
                            elif action == "2":
                                result = order_ctrl.reject_order(order_id)
                            else:
                                print("잘못된 선택입니다.")
                                continue
                            order_view.display_order_result(result)
                        except ValueError as e:
                            print(f"[오류] {e}")

                elif sub == "0":
                    break
                else:
                    print("잘못된 입력입니다.")

        elif choice == "3":
            # 모니터링
            status_map = monitoring_ctrl.get_orders_by_status()
            # MonitoringView는 문자열 키를 기대하므로 변환
            str_status_map = {k.value: v for k, v in status_map.items()}
            monitoring_view.display_orders_by_status(str_status_map)

            stock_list_raw = monitoring_ctrl.get_stock_status()
            # MonitoringView는 name/status 키를 기대하므로 변환
            stock_list = [
                {
                    "name": item["sample"].name,
                    "stock": item["stock"],
                    "status": item["label"],
                }
                for item in stock_list_raw
            ]
            monitoring_view.display_stock_status(stock_list)

        elif choice == "4":
            # 출고처리
            confirmed = shipping_ctrl.list_confirmed_orders()
            shipping_view.display_confirmed_orders(confirmed)
            if confirmed:
                try:
                    order_id = shipping_view.get_ship_choice()
                    result = shipping_ctrl.ship_order(order_id)
                    shipping_view.display_ship_result(result)
                except ValueError as e:
                    print(f"[오류] {e}")

        elif choice == "5":
            # 생산라인
            current = production_ctrl.get_current_production()
            production_view.display_current_production(current)

            waiting = production_ctrl.get_waiting_queue()
            production_view.display_waiting_queue(waiting)

            if current is not None:
                advance = input("생산 완료 처리하시겠습니까? (1. 예 / 0. 아니오) > ")
                if advance == "1":
                    try:
                        completed_order = production_ctrl.advance_production()
                        if completed_order is not None:
                            print(
                                f"[완료] 주문 {completed_order.order_id} 생산 완료"
                                f" → {completed_order.status.value}"
                            )
                    except ValueError as e:
                        print(f"[오류] {e}")

        elif choice == "0":
            print("시스템을 종료합니다.")
            break
        else:
            print("잘못된 입력입니다.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n시스템을 종료합니다.")
