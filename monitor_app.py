import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from persistence.sample_repository import SampleRepository
from persistence.order_repository import OrderRepository
from persistence.production_repository import ProductionRepository
from monitor.monitor_controller import MonitorController
from monitor.monitor_view import MonitorView

DATA_DIR = "data"
REFRESH_INTERVAL = 5  # 기본 자동갱신 주기 (초)


def main() -> None:
    sample_repo = SampleRepository(os.path.join(DATA_DIR, "samples.json"))
    order_repo = OrderRepository(os.path.join(DATA_DIR, "orders.json"))
    production_repo = ProductionRepository(os.path.join(DATA_DIR, "production.json"))

    ctrl = MonitorController(sample_repo, order_repo, production_repo)
    view = MonitorView()

    auto_refresh = True
    interval = REFRESH_INTERVAL

    try:
        while True:
            stock = ctrl.get_stock_summary()
            orders = ctrl.get_order_summary()
            production = ctrl.get_production_summary()
            view.render_dashboard(stock, orders, production, auto_refresh, interval)

            key = view.get_user_input(interval if auto_refresh else 86400)

            if key == 'q':
                break
            elif key == 'a':
                auto_refresh = not auto_refresh
            # 'r', '' (타임아웃), 기타: 즉시 재갱신
    except KeyboardInterrupt:
        pass

    print("\n모니터링 도구를 종료합니다.")


if __name__ == "__main__":
    main()
