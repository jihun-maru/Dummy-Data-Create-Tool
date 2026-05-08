"""
Phase 9 검증 스크립트 — Controller Repository 연동 및 main.py 수정
실행: python tests/test_phase9.py  (프로젝트 루트에서)
"""
import ast
import glob
import os
import shutil
import sys
sys.stdout.reconfigure(encoding='utf-8')
import tempfile

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


def _make_repos(tmp: str):
    from persistence.sample_repository import SampleRepository
    from persistence.order_repository import OrderRepository
    from persistence.production_repository import ProductionRepository
    return (
        SampleRepository(os.path.join(tmp, "samples.json")),
        OrderRepository(os.path.join(tmp, "orders.json")),
        ProductionRepository(os.path.join(tmp, "production.json")),
    )


# ──────────────────────────────────────────────────────────────
# 1. main.py import 확인
# ──────────────────────────────────────────────────────────────
def test_main_import():
    try:
        import importlib
        import main as m
        importlib.reload(m)  # 최신 상태 로드
        check(True, "main 모듈 import 성공")
    except Exception as e:
        check(False, f"main import 실패: {e}")


# ──────────────────────────────────────────────────────────────
# 2. 구조 검사 — main.py가 persistence 패키지를 import하는지
# ──────────────────────────────────────────────────────────────
def test_main_uses_persistence():
    if not os.path.isfile("main.py"):
        check(False, "main.py 없음 — 구조 검사 불가")
        return
    with open("main.py", encoding="utf-8") as f:
        content = f.read()
    check("persistence" in content, "main.py: persistence 패키지 참조 확인")
    check(
        "SampleRepository" in content or "sample_repository" in content,
        "main.py: SampleRepository 사용 확인",
    )
    check(
        "OrderRepository" in content or "order_repository" in content,
        "main.py: OrderRepository 사용 확인",
    )


# ──────────────────────────────────────────────────────────────
# 3. 구조 검사 — Controller들이 persistence를 import하는지 (AST)
# ──────────────────────────────────────────────────────────────
def test_controllers_use_persistence():
    target_files = {
        "controller/sample_controller.py": "SampleRepository",
        "controller/order_controller.py": "OrderRepository",
        "controller/monitoring_controller.py": "OrderRepository",
        "controller/shipping_controller.py": "OrderRepository",
        "controller/production_controller.py": "ProductionRepository",
    }
    for filepath, expected_repo in target_files.items():
        if not os.path.isfile(filepath):
            check(False, f"{filepath}: 파일 없음")
            continue
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        check(
            "persistence" in content or expected_repo in content,
            f"{filepath}: {expected_repo} 참조 확인",
        )


# ──────────────────────────────────────────────────────────────
# 4. 기능 검증 — 각 Controller를 Repository와 함께 인스턴스화
# ──────────────────────────────────────────────────────────────
def test_controller_instantiation():
    try:
        from model.production_line import ProductionLine
        from controller.sample_controller import SampleController
        from controller.order_controller import OrderController
        from controller.monitoring_controller import MonitoringController
        from controller.shipping_controller import ShippingController
        from controller.production_controller import ProductionController

        tmp = tempfile.mkdtemp()
        try:
            sample_repo, order_repo, production_repo = _make_repos(tmp)
            pl = ProductionLine()

            sc = SampleController(sample_repo)
            check(True, "SampleController(sample_repo) 인스턴스화 성공")

            oc = OrderController(order_repo, sample_repo, pl, production_repo)
            check(True, "OrderController(order_repo, sample_repo, pl, production_repo) 인스턴스화 성공")

            mc = MonitoringController(order_repo, sample_repo)
            check(True, "MonitoringController(order_repo, sample_repo) 인스턴스화 성공")

            shc = ShippingController(order_repo)
            check(True, "ShippingController(order_repo) 인스턴스화 성공")

            pc = ProductionController(pl, order_repo, sample_repo, production_repo)
            check(True, "ProductionController(pl, order_repo, sample_repo, production_repo) 인스턴스화 성공")
        finally:
            shutil.rmtree(tmp)
    except Exception as e:
        check(False, f"Controller 인스턴스화 오류: {e}")


# ──────────────────────────────────────────────────────────────
# 5. 기능 검증 — 작업 수행 후 JSON 파일에 반영되는지
# ──────────────────────────────────────────────────────────────
def test_operations_write_to_files():
    try:
        from model.production_line import ProductionLine
        from model.order_status import OrderStatus
        from controller.sample_controller import SampleController
        from controller.order_controller import OrderController

        tmp = tempfile.mkdtemp()
        try:
            sample_repo, order_repo, production_repo = _make_repos(tmp)
            pl = ProductionLine()
            sc = SampleController(sample_repo)
            oc = OrderController(order_repo, sample_repo, pl, production_repo)

            # 시료 등록 → samples.json 작성 확인
            sc.register_sample("S001", "테스트시료", 2.0, 0.9)
            check(
                os.path.isfile(os.path.join(tmp, "samples.json")),
                "register_sample() 후 samples.json 파일 생성",
            )

            # 주문 접수 → orders.json 작성 확인
            oc.place_order("S001", "고객A", 3)
            check(
                os.path.isfile(os.path.join(tmp, "orders.json")),
                "place_order() 후 orders.json 파일 생성",
            )

            # 재고 충분 승인 → samples.json 재고 변경 반영 확인
            from persistence.sample_repository import SampleRepository
            s = sample_repo.find_by_id("S001")
            s.add_stock(10)
            sample_repo.save(s)

            order = order_repo.find_by_status(OrderStatus.RESERVED)[0]
            oc.approve_order(order.order_id)

            reloaded_sample = SampleRepository(os.path.join(tmp, "samples.json")).find_by_id("S001")
            check(reloaded_sample.stock < 10, "approve_order() 후 samples.json에 재고 차감 반영")

            reloaded_order = order_repo.find_by_id(order.order_id)
            check(
                reloaded_order.status == OrderStatus.CONFIRMED,
                "approve_order() 후 orders.json에 CONFIRMED 상태 반영",
            )
        finally:
            shutil.rmtree(tmp)
    except Exception as e:
        check(False, f"파일 반영 검증 오류: {e}")


# ──────────────────────────────────────────────────────────────
# 6. 기능 검증 — 재고 부족 시 PRODUCING + production.json 작성
# ──────────────────────────────────────────────────────────────
def test_producing_writes_production_json():
    try:
        from model.production_line import ProductionLine
        from model.order_status import OrderStatus
        from controller.sample_controller import SampleController
        from controller.order_controller import OrderController

        tmp = tempfile.mkdtemp()
        try:
            sample_repo, order_repo, production_repo = _make_repos(tmp)
            pl = ProductionLine()
            sc = SampleController(sample_repo)
            oc = OrderController(order_repo, sample_repo, pl, production_repo)

            sc.register_sample("S001", "재고없는시료", 1.0, 0.9)  # stock = 0
            order = oc.place_order("S001", "고객B", 10)
            approved = oc.approve_order(order.order_id)

            check(approved.status == OrderStatus.PRODUCING, "재고 부족 → PRODUCING 상태")
            check(
                os.path.isfile(os.path.join(tmp, "production.json")),
                "PRODUCING 승인 후 production.json 파일 생성",
            )

            from persistence.production_repository import ProductionRepository
            state = ProductionRepository(os.path.join(tmp, "production.json")).load_state()
            check(state is not None and state.get("current_job") is not None,
                  "production.json에 current_job 데이터 저장")
        finally:
            shutil.rmtree(tmp)
    except Exception as e:
        check(False, f"PRODUCING → production.json 검증 오류: {e}")


# ──────────────────────────────────────────────────────────────
# 7. AST 검사 — controller/*.py에 print/input 없음 (리팩터링 후 유지)
# ──────────────────────────────────────────────────────────────
def test_no_print_input_in_controllers():
    for filepath in glob.glob("controller/*.py"):
        if filepath.endswith("__init__.py"):
            continue
        try:
            with open(filepath, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            violations = [
                f"line {n.lineno}: {n.func.id}()"
                for n in ast.walk(tree)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id in ("print", "input")
            ]
            check(
                len(violations) == 0,
                f"{filepath}: print/input 없음"
                if not violations
                else f"{filepath}: 금지 호출 발견 → {violations}",
            )
        except Exception as e:
            check(False, f"{filepath} AST 분석 실패: {e}")


# ──────────────────────────────────────────────────────────────
# 8. 기존 통합 테스트 시나리오 회귀 검증
# ──────────────────────────────────────────────────────────────
def test_integration_regression():
    """핵심 E2E 시나리오가 Repository 연동 후에도 동작하는지 확인."""
    try:
        from model.production_line import ProductionLine
        from model.order_status import OrderStatus
        from controller.sample_controller import SampleController
        from controller.order_controller import OrderController
        from controller.monitoring_controller import MonitoringController
        from controller.shipping_controller import ShippingController
        from controller.production_controller import ProductionController

        tmp = tempfile.mkdtemp()
        try:
            sample_repo, order_repo, production_repo = _make_repos(tmp)
            pl = ProductionLine()
            sc = SampleController(sample_repo)
            oc = OrderController(order_repo, sample_repo, pl, production_repo)
            mc = MonitoringController(order_repo, sample_repo)
            shc = ShippingController(order_repo)
            pc = ProductionController(pl, order_repo, sample_repo, production_repo)

            # 시나리오 A: 재고 충분 → CONFIRMED → RELEASE
            s = sc.register_sample("SA01", "재고충분시료", 1.0, 0.9)
            s.add_stock(20)
            sample_repo.save(s)
            order_a = oc.place_order("SA01", "고객A", 5)
            approved_a = oc.approve_order(order_a.order_id)
            check(approved_a.status == OrderStatus.CONFIRMED, "회귀-A: 재고충분 → CONFIRMED")
            shipped_a = shc.ship_order(approved_a.order_id)
            check(shipped_a.status == OrderStatus.RELEASE, "회귀-A: 출고 → RELEASE")

            # 시나리오 B: 재고 부족 → PRODUCING → advance → CONFIRMED
            sc.register_sample("SB01", "재고없는시료", 1.0, 0.9)
            order_b = oc.place_order("SB01", "고객B", 10)
            approved_b = oc.approve_order(order_b.order_id)
            check(approved_b.status == OrderStatus.PRODUCING, "회귀-B: 재고부족 → PRODUCING")
            completed = pc.advance_production()
            check(completed is not None, "회귀-B: advance_production() 결과 반환")
            check(completed.status == OrderStatus.CONFIRMED, "회귀-B: advance 후 → CONFIRMED")

            # 시나리오 C: REJECTED는 모니터링 제외
            sc.register_sample("SC01", "거절시료", 1.0, 0.9)
            order_c = oc.place_order("SC01", "고객C", 3)
            oc.reject_order(order_c.order_id)
            status_map = mc.get_orders_by_status()
            rejected_count = len(status_map.get(OrderStatus.REJECTED, []))
            check(rejected_count == 0, "회귀-C: REJECTED 주문은 모니터링 제외")

        finally:
            shutil.rmtree(tmp)
    except Exception as e:
        check(False, f"통합 시나리오 회귀 오류: {e}")


# ──────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("Phase 9 검증 — Controller Repository 연동")
    print("=" * 50)

    test_main_import()
    test_main_uses_persistence()
    test_controllers_use_persistence()
    test_controller_instantiation()
    test_operations_write_to_files()
    test_producing_writes_production_json()
    test_no_print_input_in_controllers()
    test_integration_regression()

    print("-" * 50)
    if _failures:
        print(f"결과: {len(_failures)}개 실패")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("✓ Phase 9 검증 완료 — 모든 항목 통과")
