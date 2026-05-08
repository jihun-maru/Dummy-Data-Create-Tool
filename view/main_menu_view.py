from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.sample import Sample


class MainMenuView:
    def display_menu(self) -> None:
        print("=============================")
        print(" S-Semi 시료 주문 관리 시스템")
        print("=============================")
        print("1. 시료 관리")
        print("2. 주문 (접수 / 승인 / 거절)")
        print("3. 모니터링")
        print("4. 출고 처리")
        print("5. 생산 라인")
        print("0. 종료")
        print("-----------------------------")

    def display_summary(self, samples: list) -> None:
        total_stock = sum(s.stock for s in samples)
        print(f"[요약] 등록된 시료 수: {len(samples)}개 | 총 재고 합계: {total_stock}개")

    def get_menu_choice(self) -> str:
        return input("선택 > ")
