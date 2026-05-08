"""
Phase 2 검증 스크립트 — Model 레이어
실행: python tests/test_phase2.py  (프로젝트 루트에서)
"""
import ast
import glob
import math
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


def test_model_files_exist():
    required = [
        "model/order_status.py",
        "model/sample.py",
        "model/order.py",
        "model/production_line.py",
    ]
    import os
    for f in required:
        check(os.path.isfile(f), f"파일 존재: {f}")


def test_order_status_enum():
    try:
        from model.order_status import OrderStatus
        expected = {"RESERVED", "REJECTED", "PRODUCING", "CONFIRMED", "RELEASE"}
        actual = {s.value for s in OrderStatus}
        check(len(OrderStatus) == 5, "OrderStatus: 상태 5개 정의")
        check(actual == expected, f"OrderStatus: 모든 값 일치 ({actual})")
    except Exception as e:
        check(False, f"OrderStatus import 실패: {e}")


def test_sample_class():
    try:
        from model.sample import Sample
        s = Sample("S001", "테스트시료", 2.0, 0.9)
        check(s.sample_id == "S001", "Sample: sample_id 속성")
        check(s.name == "테스트시료", "Sample: name 속성")
        check(s.avg_production_time == 2.0, "Sample: avg_production_time 속성")
        check(s.yield_rate == 0.9, "Sample: yield_rate 속성")
        check(s.stock == 0, "Sample: 초기 stock == 0")

        s.add_stock(10)
        check(s.stock == 10, "Sample.add_stock(10): stock == 10")

        s.consume_stock(3)
        check(s.stock == 7, "Sample.consume_stock(3): stock == 7")

        s.consume_stock(999)
        check(s.stock >= 0, "Sample.consume_stock(과다): stock 음수 방지")
    except Exception as e:
        check(False, f"Sample 클래스 오류: {e}")


def test_order_class():
    try:
        from model.order import Order
        from model.order_status import OrderStatus
        o = Order("O001", "S001", "고객A", 5)
        check(o.order_id == "O001", "Order: order_id 속성")
        check(o.sample_id == "S001", "Order: sample_id 속성")
        check(o.customer == "고객A", "Order: customer 속성")
        check(o.quantity == 5, "Order: quantity 속성")
        check(o.status == OrderStatus.RESERVED, "Order: 초기 상태 == RESERVED")

        o.transition_to(OrderStatus.CONFIRMED)
        check(o.status == OrderStatus.CONFIRMED, "Order.transition_to(CONFIRMED)")

        o.transition_to(OrderStatus.RELEASE)
        check(o.status == OrderStatus.RELEASE, "Order.transition_to(RELEASE)")
    except Exception as e:
        check(False, f"Order 클래스 오류: {e}")


def test_production_line_enqueue():
    try:
        from model.production_line import ProductionLine, ProductionJob
        from model.sample import Sample
        from model.order import Order

        pl = ProductionLine()
        s = Sample("S001", "생산시료", 2.0, 0.8)
        s.add_stock(3)
        o = Order("O001", "S001", "고객A", 10)

        shortage = 10 - 3  # 7
        expected_qty = math.ceil(shortage / (0.8 * 0.9))
        expected_time = 2.0 * expected_qty

        job = pl.enqueue(o, s)
        check(isinstance(job, ProductionJob), "ProductionLine.enqueue(): ProductionJob 반환")
        check(job.actual_qty == expected_qty,
              f"실생산량 계산: ceil({shortage}/(0.8*0.9)) == {expected_qty}, 실제: {job.actual_qty}")
        check(job.total_time == expected_time,
              f"총생산시간: {expected_time}, 실제: {job.total_time}")
        check(pl.get_current_job() is job, "첫 enqueue → current_job으로 설정")
        check(len(pl.get_waiting_jobs()) == 0, "첫 enqueue → 대기 큐 비어있음")
    except Exception as e:
        check(False, f"ProductionLine.enqueue() 오류: {e}")


def test_production_line_queue_fifo():
    try:
        from model.production_line import ProductionLine
        from model.sample import Sample
        from model.order import Order

        pl = ProductionLine()
        s = Sample("S001", "FIFO시료", 1.0, 0.9)
        o1 = Order("O001", "S001", "고객1", 5)
        o2 = Order("O002", "S001", "고객2", 3)

        pl.enqueue(o1, s)
        pl.enqueue(o2, s)
        check(pl.get_current_job().order.order_id == "O001", "FIFO: 첫 작업이 current_job")
        check(len(pl.get_waiting_jobs()) == 1, "FIFO: 두 번째 작업이 대기 큐에 존재")

        pl.complete_current_job()
        check(pl.get_current_job().order.order_id == "O002",
              "complete_current_job(): 대기 큐 → current_job 이동")
    except Exception as e:
        check(False, f"ProductionLine FIFO 오류: {e}")


def test_no_print_input_in_models():
    for filepath in glob.glob("model/*.py"):
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
    print("Phase 2 검증 — Model 레이어")
    print("=" * 50)

    test_model_files_exist()
    test_order_status_enum()
    test_sample_class()
    test_order_class()
    test_production_line_enqueue()
    test_production_line_queue_fifo()
    test_no_print_input_in_models()

    print("-" * 50)
    if _failures:
        print(f"결과: {len(_failures)}개 실패")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("✓ Phase 2 검증 완료 — 모든 항목 통과")
