"""
Phase 3 검증 스크립트 — Controller 레이어
실행: python tests/test_phase3.py  (프로젝트 루트에서)
"""
import ast
import glob
import os
import sys
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


def _setup():
    import tempfile
    import shutil
    from model.production_line import ProductionLine
    from controller.sample_controller import SampleController
    from controller.order_controller import OrderController
    from controller.monitoring_controller import MonitoringController
    from controller.shipping_controller import ShippingController
    from controller.production_controller import ProductionController
    from persistence.sample_repository import SampleRepository
    from persistence.order_repository import OrderRepository
    from persistence.production_repository import ProductionRepository

    _tmp = tempfile.mkdtemp()
    sr = SampleRepository(os.path.join(_tmp, "samples.json"))
    or_ = OrderRepository(os.path.join(_tmp, "orders.json"))
    pr = ProductionRepository(os.path.join(_tmp, "production.json"))
    pl = ProductionLine()
    return (
        _tmp, sr, pl,
        SampleController(sr),
        OrderController(or_, sr, pl, pr),
        MonitoringController(or_, sr),
        ShippingController(or_),
        ProductionController(pl, or_, sr, pr),
    )


def test_controller_files_exist():
    required = [
        "controller/sample_controller.py",
        "controller/order_controller.py",
        "controller/monitoring_controller.py",
        "controller/shipping_controller.py",
        "controller/production_controller.py",
    ]
    for f in required:
        check(os.path.isfile(f), f"파일 존재: {f}")


def test_sample_controller():
    try:
        _tmp, sr, pl, sc, oc, mc, shc, pc = _setup()

        s = sc.register_sample("S001", "테스트시료", 2.0, 0.9)
        check(s.sample_id == "S001", "SampleController.register_sample(): Sample 반환")
        check(len(sc.list_samples()) == 1, "SampleController.list_samples(): 1개")

        results = sc.search_sample("테스트")
        check(len(results) == 1, "SampleController.search_sample('테스트'): 1개 매칭")
        check(len(sc.search_sample("없는이름")) == 0, "SampleController.search_sample(): 없는 경우 빈 리스트")

        check(sc.get_sample("S001") is not None and sc.get_sample("S001").sample_id == "S001",
              "SampleController.get_sample(): 존재하는 ID")
        check(sc.get_sample("X999") is None, "SampleController.get_sample(): 없는 ID → None")

        try:
            sc.register_sample("S001", "중복", 1.0, 0.8)
            check(False, "중복 ID에서 ValueError 미발생")
        except ValueError:
            check(True, "SampleController.register_sample(): 중복 ID → ValueError")
    except Exception as e:
        check(False, f"SampleController 오류: {e}")


def test_order_controller_confirmed():
    try:
        from model.order_status import OrderStatus
        _tmp, sr, pl, sc, oc, mc, shc, pc = _setup()

        s = sc.register_sample("S001", "충분시료", 1.0, 0.9)
        s.add_stock(20)
        sr.save(s)  # Repository에 재고 변경 반영

        order = oc.place_order("S001", "고객A", 5)
        check(order.status == OrderStatus.RESERVED, "place_order(): 초기 상태 RESERVED")

        approved = oc.approve_order(order.order_id)
        check(approved.status == OrderStatus.CONFIRMED, "approve_order(재고충분): → CONFIRMED")
        s_after = sr.find_by_id("S001")
        check(s_after.stock == 15, "approve_order(재고충분): 재고 차감 (20→15)")
    except Exception as e:
        check(False, f"OrderController(CONFIRMED) 오류: {e}")


def test_order_controller_producing():
    try:
        from model.order_status import OrderStatus
        _tmp, sr, pl, sc, oc, mc, shc, pc = _setup()

        sc.register_sample("S002", "재고없는시료", 1.0, 0.9)

        order = oc.place_order("S002", "고객B", 10)
        approved = oc.approve_order(order.order_id)
        check(approved.status == OrderStatus.PRODUCING, "approve_order(재고부족): → PRODUCING")
        check(pl.get_current_job() is not None, "approve_order(재고부족): ProductionLine에 job 등록")
    except Exception as e:
        check(False, f"OrderController(PRODUCING) 오류: {e}")


def test_order_controller_reject():
    try:
        from model.order_status import OrderStatus
        _tmp, sr, pl, sc, oc, mc, shc, pc = _setup()

        sc.register_sample("S003", "거절시료", 1.0, 0.9)
        order = oc.place_order("S003", "고객C", 3)
        rejected = oc.reject_order(order.order_id)
        check(rejected.status == OrderStatus.REJECTED, "reject_order(): → REJECTED")

        try:
            oc.reject_order(order.order_id)
            check(False, "이미 REJECTED인 주문 재거절 시 ValueError 미발생")
        except ValueError:
            check(True, "reject_order(비RESERVED): → ValueError")
    except Exception as e:
        check(False, f"OrderController(REJECTED) 오류: {e}")


def test_monitoring_controller():
    try:
        from model.order_status import OrderStatus
        _tmp, sr, pl, sc, oc, mc, shc, pc = _setup()

        s = sc.register_sample("S001", "모니터링시료", 1.0, 0.9)
        s.add_stock(5)
        sr.save(s)  # Repository에 재고 변경 반영
        oc.place_order("S001", "고객A", 3)

        status_map = mc.get_orders_by_status()
        check(OrderStatus.REJECTED not in status_map or len(status_map.get(OrderStatus.REJECTED, [])) == 0,
              "MonitoringController.get_orders_by_status(): REJECTED 제외")
        check(OrderStatus.RESERVED in status_map, "get_orders_by_status(): RESERVED 포함")

        stock_list = mc.get_stock_status()
        check(len(stock_list) == 1, "get_stock_status(): 시료 1개")
        check("label" in stock_list[0], "get_stock_status(): label 필드 존재")
        check(stock_list[0]["label"] in ("여유", "부족", "고갈"),
              f"get_stock_status(): label 값 유효 ({stock_list[0]['label']})")
    except Exception as e:
        check(False, f"MonitoringController 오류: {e}")


def test_monitoring_stock_labels():
    try:
        _tmp, sr, pl, sc, oc, mc, shc, pc = _setup()
        s = sc.register_sample("S001", "레이블시료", 1.0, 0.9)

        stock_list = mc.get_stock_status()
        check(stock_list[0]["label"] == "고갈", "get_stock_status(): stock=0 → 고갈")

        s.add_stock(2)
        sr.save(s)  # Repository에 재고 변경 반영
        order = oc.place_order("S001", "고객A", 10)
        oc.approve_order(order.order_id)

        stock_list = mc.get_stock_status()
        check(stock_list[0]["label"] == "부족",
              f"get_stock_status(): stock<주문량 → 부족 (실제: {stock_list[0]['label']})")

        s_fresh = sr.find_by_id("S001")
        s_fresh.add_stock(100)
        sr.save(s_fresh)  # Repository에 재고 변경 반영
        stock_list = mc.get_stock_status()
        check(stock_list[0]["label"] == "여유",
              f"get_stock_status(): stock충분 → 여유 (실제: {stock_list[0]['label']})")
    except Exception as e:
        check(False, f"MonitoringController 재고 레이블 오류: {e}")


def test_shipping_controller():
    try:
        from model.order_status import OrderStatus
        _tmp, sr, pl, sc, oc, mc, shc, pc = _setup()

        s = sc.register_sample("S001", "출고시료", 1.0, 0.9)
        s.add_stock(10)
        sr.save(s)  # Repository에 재고 변경 반영
        order = oc.place_order("S001", "고객A", 5)
        oc.approve_order(order.order_id)

        confirmed = shc.list_confirmed_orders()
        check(len(confirmed) == 1, "ShippingController.list_confirmed_orders(): 1개")

        shipped = shc.ship_order(order.order_id)
        check(shipped.status == OrderStatus.RELEASE, "ShippingController.ship_order(): → RELEASE")
        check(len(shc.list_confirmed_orders()) == 0, "출고 후 CONFIRMED 목록 비어있음")

        try:
            shc.ship_order(order.order_id)
            check(False, "이미 RELEASE된 주문 출고 시 ValueError 미발생")
        except ValueError:
            check(True, "ship_order(비CONFIRMED): → ValueError")
    except Exception as e:
        check(False, f"ShippingController 오류: {e}")


def test_production_controller():
    try:
        from model.order_status import OrderStatus
        _tmp, sr, pl, sc, oc, mc, shc, pc = _setup()

        sc.register_sample("S001", "생산시료", 1.0, 0.9)
        order = oc.place_order("S001", "고객A", 10)
        oc.approve_order(order.order_id)

        check(pc.get_current_production() is not None, "ProductionController.get_current_production(): job 존재")
        check(isinstance(pc.get_waiting_queue(), list), "get_waiting_queue(): list 반환")

        completed = pc.advance_production()
        check(completed is not None, "advance_production(): 완료된 Order 반환")
        check(completed.status == OrderStatus.CONFIRMED, "advance_production(): 주문 → CONFIRMED")
        check(pc.get_current_production() is None, "advance_production() 후 current_job == None")
    except Exception as e:
        check(False, f"ProductionController 오류: {e}")


def test_no_print_input_in_controllers():
    for filepath in glob.glob("controller/*.py"):
        if filepath.endswith("__init__.py"):
            continue
        try:
            with open(filepath, encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
            violations = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in ("print", "input"):
                        violations.append(f"line {node.lineno}: {node.func.id}()")
            check(len(violations) == 0,
                  f"{filepath}: print/input 없음" if not violations
                  else f"{filepath}: 금지 호출 발견 → {violations}")
        except Exception as e:
            check(False, f"{filepath} AST 분석 실패: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 3 검증 — Controller 레이어")
    print("=" * 50)

    test_controller_files_exist()
    test_sample_controller()
    test_order_controller_confirmed()
    test_order_controller_producing()
    test_order_controller_reject()
    test_monitoring_controller()
    test_monitoring_stock_labels()
    test_shipping_controller()
    test_production_controller()
    test_no_print_input_in_controllers()

    print("-" * 50)
    if _failures:
        print(f"결과: {len(_failures)}개 실패")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("✓ Phase 3 검증 완료 — 모든 항목 통과")
