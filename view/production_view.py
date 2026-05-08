from typing import Optional


class ProductionView:
    def display_current_production(self, job: Optional[object]) -> None:
        print("=============================")
        print(" 현재 생산 현황")
        print("=============================")
        if job is None:
            print("현재 생산 중인 작업 없음")
        else:
            print(f"주문ID     : {job.order.order_id}")
            print(f"시료명     : {job.sample.name}")
            print(f"실생산량   : {job.actual_qty}")
            print(f"총생산시간 : {job.total_time:.2f} 시간")
        print("-----------------------------")

    def display_waiting_queue(self, jobs: list) -> None:
        print("=============================")
        print(" 생산 대기 목록")
        print("=============================")
        if not jobs:
            print("대기 중인 작업 없음")
        else:
            print(f"{'순번':>4} {'주문ID':<12} {'시료명':<16} {'실생산량':>8}")
            print("-----------------------------")
            for idx, job in enumerate(jobs, start=1):
                print(f"{idx:>4} {job.order.order_id:<12} {job.sample.name:<16} {job.actual_qty:>8}")
        print("-----------------------------")
