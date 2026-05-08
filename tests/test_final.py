"""
최종 통합 검증 스크립트 — 전체 Phase 순차 실행 + 영속성 E2E 검증
실행: python tests/test_final.py  (프로젝트 루트에서)
"""
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding='utf-8')

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

PASS = "[PASS]"
FAIL = "[FAIL]"
_failures = []


def check(condition: bool, message: str) -> None:
    if condition:
        print(f"{PASS} {message}")
    else:
        print(f"{FAIL} {message}")
        _failures.append(message)


# ──────────────────────────────────────────────────────────────
# 1. 각 Phase 테스트 스크립트 순차 실행
# ──────────────────────────────────────────────────────────────
def run_phase_scripts():
    scripts = [
        ("tests/test_phase1.py", "Phase 1: 패키지 뼈대 구조"),
        ("tests/test_phase2.py", "Phase 2: Model 레이어"),
        ("tests/test_phase3.py", "Phase 3: Controller 레이어 (리팩터링 후)"),
        ("tests/test_phase4.py", "Phase 4: View 레이어"),
        ("tests/test_phase7.py", "Phase 7: BaseRepository"),
        ("tests/test_phase8.py", "Phase 8: 구체 Repository 3종"),
        ("tests/test_phase9.py", "Phase 9: Controller Repository 연동"),
        ("tests/test_integration.py", "Phase 5/6: E2E 통합 시나리오"),
        ("tests/test_persistence.py", "Phase 10: 영속성 CRUD 시나리오"),
    ]

    print("\n[단계 1] Phase별 테스트 스크립트 순차 실행")
    print("-" * 50)

    for script_path, label in scripts:
        if not os.path.isfile(script_path):
            check(False, f"{label} (스크립트 없음: {script_path})")
            continue
        result = subprocess.run(
            [sys.executable, "-X", "utf8", script_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        passed = result.returncode == 0
        check(passed, f"{label} ({script_path})")
        if not passed:
            # 실패 시 마지막 5줄 출력해서 원인 파악 지원
            output = (result.stdout + result.stderr).strip().splitlines()
            for line in output[-5:]:
                print(f"    {line}")


# ──────────────────────────────────────────────────────────────
# 2. 전체 영속성 E2E 시나리오 — "프로세스 재시작" 포함
# ──────────────────────────────────────────────────────────────
def test_full_persistence_e2e():
    print("\n[단계 2] 전체 영속성 E2E 시나리오")
    print("-" * 50)

    try:
        from model.production_line import ProductionLine
        from model.order_status import OrderStatus
        from controller.sample_controller import SampleController
        from controller.order_controller import OrderController
        from controller.monitoring_controller import MonitoringController
        from controller.shipping_controller import ShippingController
        from controller.production_controller import ProductionController
        from persistence.sample_repository import SampleRepository
        from persistence.order_repository import OrderRepository
        from persistence.production_repository import ProductionRepository

        tmp = tempfile.mkdtemp()
        try:
            samples_path    = os.path.join(tmp, "samples.json")
            orders_path     = os.path.join(tmp, "orders.json")
            production_path = os.path.join(tmp, "production.json")

            # ── 세션 1: 데이터 생성 및 조작 ──────────────────────
            def make_controllers(pl):
                sr = SampleRepository(samples_path)
                or_ = OrderRepository(orders_path)
                pr = ProductionRepository(production_path)
                return (
                    sr, or_, pr, pl,
                    SampleController(sr),
                    OrderController(or_, sr, pl, pr),
                    MonitoringController(or_, sr),
                    ShippingController(or_),
                    ProductionController(pl, or_, sr, pr),
                )

            pl1 = ProductionLine()
            sr1, or1, pr1, _, sc1, oc1, mc1, shc1, pc1 = make_controllers(pl1)

            s = sc1.register_sample("S001", "영속성테스트시료", 1.0, 0.9)
            s.add_stock(50)
            sr1.save(s)
            order1 = oc1.place_order("S001", "고객X", 5)
            oc1.approve_order(order1.order_id)

            # 재고 부족 주문 → PRODUCING
            sc1.register_sample("S002", "생산필요시료", 1.0, 0.9)
            order2 = oc1.place_order("S002", "고객Y", 10)
            oc1.approve_order(order2.order_id)

            check(True, "세션 1: 시료 2개 등록 + 주문 2건 처리 완료")

            # ── 세션 2: 재시작 시뮬레이션 ──────────────────────────
            pl2 = ProductionLine()

            # ProductionLine 상태 복원
            state = ProductionRepository(production_path).load_state()
            if state:
                def _make_job(jd):
                    from model.production_line import ProductionJob
                    o = OrderRepository(orders_path).find_by_id(jd["order_id"])
                    sa = SampleRepository(samples_path).find_by_id(jd["sample_id"])
                    job = ProductionJob.__new__(ProductionJob)
                    job.order       = o
                    job.sample      = sa
                    job.actual_qty  = jd["actual_qty"]
                    job.total_time  = jd["total_time"]
                    job.produced_qty = jd["produced_qty"]
                    return job

                if state.get("current_job"):
                    pl2.current_job = _make_job(state["current_job"])
                for jd in state.get("queue", []):
                    pl2.queue.append(_make_job(jd))

            sr2, or2, pr2, _, sc2, oc2, mc2, shc2, pc2 = make_controllers(pl2)

            # 재시작 후 데이터 검증
            samples = sc2.list_samples()
            check(len(samples) == 2, "세션 2: 시료 2개 유지 (재시작 후)")

            orders_confirmed = or2.find_by_status(OrderStatus.CONFIRMED)
            check(len(orders_confirmed) == 1, "세션 2: CONFIRMED 주문 1건 유지")

            orders_producing = or2.find_by_status(OrderStatus.PRODUCING)
            check(len(orders_producing) == 1, "세션 2: PRODUCING 주문 1건 유지")

            check(pl2.current_job is not None, "세션 2: ProductionLine 상태 복원 (current_job)")

            # 재시작 후 출고 처리
            confirmed_order = orders_confirmed[0]
            shipped = shc2.ship_order(confirmed_order.order_id)
            check(shipped.status == OrderStatus.RELEASE, "세션 2: 재시작 후 출고 처리 정상")

            # 재시작 후 생산 완료
            completed = pc2.advance_production()
            check(completed is not None, "세션 2: 재시작 후 advance_production() 성공")
            check(completed.status == OrderStatus.CONFIRMED, "세션 2: 생산 완료 → CONFIRMED")

            # 재고 확인 — 생산 완료 후 반영됐는지
            s2_reloaded = sr2.find_by_id("S002")
            check(s2_reloaded.stock > 0, "세션 2: 생산 완료 후 S002 재고 증가")

        finally:
            shutil.rmtree(tmp)

    except Exception as e:
        check(False, f"전체 영속성 E2E 시나리오 오류: {e}")
        import traceback
        traceback.print_exc()


# ──────────────────────────────────────────────────────────────
# 3. 패키지 구조 최종 확인
# ──────────────────────────────────────────────────────────────
def test_final_structure():
    print("\n[단계 3] 패키지 구조 최종 확인")
    print("-" * 50)

    required_files = [
        # MVC 뼈대
        "model/__init__.py", "model/sample.py", "model/order.py",
        "model/order_status.py", "model/production_line.py",
        "controller/__init__.py", "controller/sample_controller.py",
        "controller/order_controller.py", "controller/monitoring_controller.py",
        "controller/shipping_controller.py", "controller/production_controller.py",
        "view/__init__.py", "view/main_menu_view.py", "view/sample_view.py",
        "view/order_view.py", "view/monitoring_view.py",
        "view/shipping_view.py", "view/production_view.py",
        # 영속성
        "persistence/__init__.py", "persistence/base_repository.py",
        "persistence/sample_repository.py", "persistence/order_repository.py",
        "persistence/production_repository.py",
        # 진입점
        "main.py",
        # 테스트
        "tests/test_phase1.py", "tests/test_phase2.py", "tests/test_phase3.py",
        "tests/test_phase4.py", "tests/test_phase7.py", "tests/test_phase8.py",
        "tests/test_phase9.py", "tests/test_integration.py",
        "tests/test_persistence.py",
    ]
    for f in required_files:
        check(os.path.isfile(f), f"파일 존재: {f}")


# ──────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("최종 통합 검증 - 전체 Phase E2E")
    print("=" * 50)

    run_phase_scripts()
    test_full_persistence_e2e()
    test_final_structure()

    print("\n" + "=" * 50)
    if _failures:
        print(f"최종 결과: {len(_failures)}개 실패")
        for f in _failures:
            print(f"  [FAIL] {f}")
        sys.exit(1)
    else:
        total = sum(1 for _ in open(__file__, encoding="utf-8").readlines()
                    if "check(" in _ and "def " not in _)
        print("[OK] 최종 통합 검증 완료 - 모든 항목 통과")
        print("  전체 영속성 POC 구현 완성")
