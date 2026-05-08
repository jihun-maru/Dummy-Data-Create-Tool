import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dummy.sample_generator import generate_samples
from dummy.order_generator import generate_orders
from dummy.production_generator import generate_production_jobs
from dummy.db.inserter import DummyInserter

DB_PATH = os.path.join("data", "dummy.db")

PRESETS = {
    "1": {"label": "기본 세트",     "sample_count": 5,  "order_count": 20},
    "2": {"label": "대용량 세트",   "sample_count": 10, "order_count": 100},
}


def show_menu() -> None:
    print("\n" + "=" * 46)
    print("  S-Semi 더미 데이터 생성 도구")
    print("=" * 46)
    print("  [1] 기본 세트 생성   (시료  5개 / 주문  20개)")
    print("  [2] 대용량 세트 생성 (시료 10개 / 주문 100개)")
    print("  [3] 직접 설정")
    print("  [4] DB 초기화 후 재생성 (기본 세트)")
    print("  [q] 종료")
    print("-" * 46)


def run_generate(sample_count: int, order_count: int, reset: bool = False) -> None:
    samples = generate_samples(sample_count)
    orders = generate_orders(samples, order_count)
    jobs = generate_production_jobs(orders, samples)

    inserter = DummyInserter(db_path=DB_PATH)
    if reset:
        inserter.reset()

    n_s = inserter.insert_samples(samples)
    n_o = inserter.insert_orders(orders)
    n_j = inserter.insert_production_jobs(jobs)

    from collections import Counter
    status_counts = Counter(
        (o.status.value if hasattr(o.status, "value") else str(o.status))
        for o in orders
    )

    print("\n" + "-" * 46)
    print(f"  시료       {n_s:>3}개 생성 완료")
    status_str = " / ".join(f"{k}:{v}" for k, v in sorted(status_counts.items()))
    print(f"  주문       {n_o:>3}개 생성 완료 ({status_str})")
    print(f"  생산 작업  {n_j:>3}개 생성 완료")
    print(f"\n  DB 경로: {DB_PATH}")
    print(f"  삽입 완료: {n_s + n_o + n_j}개 레코드")
    print("-" * 46)


def run_custom() -> None:
    try:
        sample_count = int(input("  생성할 시료 수 (1~10): ").strip())
        order_count = int(input("  생성할 주문 수 (1~500): ").strip())
    except ValueError:
        print("  [오류] 숫자를 입력해주세요.")
        return
    sample_count = max(1, min(10, sample_count))
    order_count = max(1, min(500, order_count))
    run_generate(sample_count, order_count)


def main() -> None:
    while True:
        show_menu()
        choice = input("선택 > ").strip().lower()

        if choice == "q":
            print("\n종료합니다.")
            break
        elif choice in PRESETS:
            preset = PRESETS[choice]
            run_generate(preset["sample_count"], preset["order_count"])
        elif choice == "3":
            run_custom()
        elif choice == "4":
            run_generate(
                PRESETS["1"]["sample_count"],
                PRESETS["1"]["order_count"],
                reset=True,
            )
        else:
            print("  [오류] 올바른 메뉴 번호를 입력해주세요.")


if __name__ == "__main__":
    main()
