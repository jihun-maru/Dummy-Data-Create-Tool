import os
import sys
import threading
from datetime import datetime


class MonitorView:
    REFRESH_INTERVAL_DEFAULT = 5  # 초

    def clear_screen(self) -> None:
        """플랫폼에 따라 화면을 지운다."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def render_dashboard(
        self,
        stock_summary: list[dict],
        order_summary: dict[str, int],
        production_summary: dict,
        auto_refresh: bool,
        refresh_interval: int,
    ) -> None:
        """화면을 클리어하고 전체 대시보드를 출력한다."""
        self.clear_screen()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mode_str = f"자동갱신: {refresh_interval}초" if auto_refresh else "수동갱신"
        # 헤더
        print("=" * 54)
        print("  S-Semi 데이터 모니터링 도구")
        print(f"  갱신: {now}  |  {mode_str}")
        print("=" * 54)
        # 시료 재고 현황
        self._render_stock(stock_summary)
        # 주문 현황
        self._render_orders(order_summary)
        # 생산라인 현황
        self._render_production(production_summary)
        # 입력 안내
        print("\n[r] 수동갱신  [q] 종료  [a] 자동갱신 토글")

    def _render_stock(self, stock_summary: list[dict]) -> None:
        print("\n[ 시료 재고 현황 ]")
        print("-" * 54)
        print(f" {'ID':<8} {'이름':<16} {'재고':>6}  상태")
        print("-" * 54)
        if not stock_summary:
            print("  등록된 시료 없음")
        for s in stock_summary:
            print(f" {s['sample_id']:<8} {s['name']:<16} {s['stock']:>6}  {s['status']}")
        print("-" * 54)

    def _render_orders(self, order_summary: dict[str, int]) -> None:
        print("\n[ 주문 현황 ]")
        print("-" * 54)
        for status in ("RESERVED", "PRODUCING", "CONFIRMED", "RELEASE"):
            count = order_summary.get(status, 0)
            print(f" {status:<12} : {count:>3}건")
        print("-" * 54)

    def _render_production(self, production_summary: dict) -> None:
        print("\n[ 생산라인 현황 ]")
        print("-" * 54)
        current = production_summary.get("current_job")
        if current:
            print(
                f" 현재 작업: {current['order_id']} | {current['sample_id']} "
                f"| 목표 {current['actual_qty']}개 "
                f"| 생산 {current.get('produced_qty', 0)}개 완료"
            )
        else:
            print("  현재 생산 작업 없음")
        queue = production_summary.get("queue", [])
        if queue:
            print(f" 대기열 ({len(queue)}건):")
            for i, job in enumerate(queue, 1):
                print(f"   [{i}] {job['order_id']} | {job['sample_id']} | {job['actual_qty']}개")
        else:
            print("  대기열 없음")
        print("-" * 54)

    def get_user_input(self, timeout: float) -> str:
        """
        timeout 초 내에 사용자 입력을 기다린다.
        입력 없으면 '' 반환, 입력 있으면 소문자 strip 후 반환.
        threading 을 사용해 플랫폼 독립적으로 구현한다.
        """
        result = ['']

        def _read():
            try:
                result[0] = sys.stdin.readline().strip().lower()
            except Exception:
                pass

        t = threading.Thread(target=_read, daemon=True)
        t.start()
        t.join(timeout)
        return result[0]
