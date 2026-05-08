"""
모니터링 도구 검증: 패키지 구조, 집계 로직, 역할 경계 AST
"""
import ast
import os
import shutil
import sys
sys.stdout.reconfigure(encoding='utf-8')
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model.order import Order
from model.order_status import OrderStatus
from model.sample import Sample
from persistence.order_repository import OrderRepository
from persistence.production_repository import ProductionRepository
from persistence.sample_repository import SampleRepository

_pass = 0
_fail = 0


def check(label: str, condition: bool) -> None:
    global _pass, _fail
    if condition:
        print(f"[PASS] {label}")
        _pass += 1
    else:
        print(f"[FAIL] {label}")
        _fail += 1


def make_temp_repos():
    """격리된 임시 디렉토리와 Repository 3종을 반환한다."""
    tmp = tempfile.mkdtemp()
    return (
        tmp,
        SampleRepository(os.path.join(tmp, "samples.json")),
        OrderRepository(os.path.join(tmp, "orders.json")),
        ProductionRepository(os.path.join(tmp, "production.json")),
    )


# ── M-1: 패키지 구조 검증 ──────────────────────────────────────────

def test_m1_package_structure():
    print("\n[M-1] 패키지 구조 검증")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    check("M-1-1 monitor/ 디렉토리 존재", os.path.isdir(os.path.join(base, "monitor")))
    check("M-1-2 monitor/__init__.py 존재", os.path.isfile(os.path.join(base, "monitor", "__init__.py")))
    check("M-1-3 monitor/monitor_controller.py 존재", os.path.isfile(os.path.join(base, "monitor", "monitor_controller.py")))
    check("M-1-4 monitor/monitor_view.py 존재", os.path.isfile(os.path.join(base, "monitor", "monitor_view.py")))
    check("M-1-5 monitor_app.py 존재", os.path.isfile(os.path.join(base, "monitor_app.py")))


# ── M-2: MonitorController import 및 인스턴스화 ──────────────────

def test_m2_monitor_controller_import():
    print("\n[M-2] MonitorController import 및 인스턴스화")
    tmp, sample_repo, order_repo, production_repo = make_temp_repos()
    try:
        from monitor.monitor_controller import MonitorController
        check("M-2-1 MonitorController import 성공", True)
        ctrl = MonitorController(sample_repo, order_repo, production_repo)
        check("M-2-2 MonitorController 인스턴스화 성공", ctrl is not None)
        check("M-2-3 get_stock_summary 메서드 존재", hasattr(ctrl, "get_stock_summary"))
        check("M-2-4 get_order_summary 메서드 존재", hasattr(ctrl, "get_order_summary"))
        check("M-2-5 get_production_summary 메서드 존재", hasattr(ctrl, "get_production_summary"))
    except ImportError as e:
        check(f"M-2-1 MonitorController import 성공 ({e})", False)
    finally:
        shutil.rmtree(tmp)


# ── M-3: 재고 현황 집계 검증 ──────────────────────────────────────

def test_m3_stock_summary():
    print("\n[M-3] 재고 현황 집계")
    tmp, sample_repo, order_repo, production_repo = make_temp_repos()
    try:
        from monitor.monitor_controller import MonitorController

        # 시료 등록
        s1 = Sample("S001", "GaN 웨이퍼", 2.5, 0.9)
        s1.stock = 100
        sample_repo.save(s1)

        s2 = Sample("S002", "SiC 웨이퍼", 3.0, 0.8)
        s2.stock = 0
        sample_repo.save(s2)

        # 주문 등록 (S001: CONFIRMED 10개 → 재고 100 → 여유)
        o1 = Order("O001", "S001", "A연구소", 10)
        o1.status = OrderStatus.CONFIRMED
        order_repo.save(o1)

        ctrl = MonitorController(sample_repo, order_repo, production_repo)
        result = ctrl.get_stock_summary()

        check("M-3-1 반환값 리스트 타입", isinstance(result, list))
        check("M-3-2 시료 2건 반환", len(result) == 2)

        s1_data = next((r for r in result if r["sample_id"] == "S001"), None)
        check("M-3-3 S001 데이터 존재", s1_data is not None)
        check("M-3-4 S001 name 일치", s1_data["name"] == "GaN 웨이퍼")
        check("M-3-5 S001 stock 일치", s1_data["stock"] == 100)
        check("M-3-6 S001 상태 여유", s1_data["status"] == "여유")

        s2_data = next((r for r in result if r["sample_id"] == "S002"), None)
        check("M-3-7 S002 상태 고갈", s2_data["status"] == "고갈")
    finally:
        shutil.rmtree(tmp)


# ── M-4: 주문 현황 집계 검증 ──────────────────────────────────────

def test_m4_order_summary():
    print("\n[M-4] 주문 현황 집계")
    tmp, sample_repo, order_repo, production_repo = make_temp_repos()
    try:
        from monitor.monitor_controller import MonitorController

        # 다양한 상태 주문 등록
        statuses = [
            ("O001", OrderStatus.RESERVED),
            ("O002", OrderStatus.RESERVED),
            ("O003", OrderStatus.PRODUCING),
            ("O004", OrderStatus.CONFIRMED),
            ("O005", OrderStatus.RELEASE),
            ("O006", OrderStatus.REJECTED),  # 집계 제외
        ]
        for oid, status in statuses:
            o = Order(oid, "S001", "고객", 1)
            o.status = status
            order_repo.save(o)

        ctrl = MonitorController(sample_repo, order_repo, production_repo)
        result = ctrl.get_order_summary()

        check("M-4-1 반환값 dict 타입", isinstance(result, dict))
        check("M-4-2 RESERVED 2건", result.get("RESERVED") == 2)
        check("M-4-3 PRODUCING 1건", result.get("PRODUCING") == 1)
        check("M-4-4 CONFIRMED 1건", result.get("CONFIRMED") == 1)
        check("M-4-5 RELEASE 1건", result.get("RELEASE") == 1)
        check("M-4-6 REJECTED 집계 제외", "REJECTED" not in result)
        check("M-4-7 키 4개 존재", all(k in result for k in ("RESERVED", "PRODUCING", "CONFIRMED", "RELEASE")))
    finally:
        shutil.rmtree(tmp)


# ── M-5: 생산라인 현황 집계 검증 ──────────────────────────────────

def test_m5_production_summary():
    print("\n[M-5] 생산라인 현황 집계")
    tmp, sample_repo, order_repo, production_repo = make_temp_repos()
    try:
        from monitor.monitor_controller import MonitorController
        from model.production_line import ProductionLine

        # 시료·주문 준비 후 생산 등록
        s = Sample("S001", "GaN", 2.5, 0.9)
        s.stock = 0
        sample_repo.save(s)
        o = Order("O001", "S001", "A연구소", 10)
        order_repo.save(o)

        pl = ProductionLine()
        pl.enqueue(o, s)
        production_repo.save_state(pl)

        ctrl = MonitorController(sample_repo, order_repo, production_repo)
        result = ctrl.get_production_summary()

        check("M-5-1 반환값 dict 타입", isinstance(result, dict))
        check("M-5-2 current_job 키 존재", "current_job" in result)
        check("M-5-3 queue 키 존재", "queue" in result)
        check("M-5-4 current_job not None", result["current_job"] is not None)
        check("M-5-5 current_job order_id 일치", result["current_job"].get("order_id") == "O001")
    finally:
        shutil.rmtree(tmp)


# ── M-6: 빈 데이터 처리 검증 ──────────────────────────────────────

def test_m6_empty_data():
    print("\n[M-6] 빈 데이터 처리")
    tmp, sample_repo, order_repo, production_repo = make_temp_repos()
    try:
        from monitor.monitor_controller import MonitorController

        ctrl = MonitorController(sample_repo, order_repo, production_repo)

        stock = ctrl.get_stock_summary()
        orders = ctrl.get_order_summary()
        production = ctrl.get_production_summary()

        check("M-6-1 빈 시료 → 빈 리스트", stock == [])
        check("M-6-2 빈 주문 → 4개 키 모두 0", all(orders.get(k, -1) == 0 for k in ("RESERVED", "PRODUCING", "CONFIRMED", "RELEASE")))
        check("M-6-3 빈 생산 → current_job None", production.get("current_job") is None)
        check("M-6-4 빈 생산 → queue 빈 목록", production.get("queue") == [])
    finally:
        shutil.rmtree(tmp)


# ── M-7: MonitorView import 검증 ──────────────────────────────────

def test_m7_monitor_view_import():
    print("\n[M-7] MonitorView import")
    try:
        from monitor.monitor_view import MonitorView
        check("M-7-1 MonitorView import 성공", True)
        view = MonitorView()
        check("M-7-2 MonitorView 인스턴스화 성공", view is not None)
        check("M-7-3 render_dashboard 메서드 존재", hasattr(view, "render_dashboard"))
        check("M-7-4 get_user_input 메서드 존재", hasattr(view, "get_user_input"))
    except ImportError as e:
        check(f"M-7-1 MonitorView import 성공 ({e})", False)


# ── M-8: MonitorController 역할 경계 AST 검사 ─────────────────────

def test_m8_controller_ast():
    print("\n[M-8] MonitorController 역할 경계 (AST)")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "monitor", "monitor_controller.py")
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    forbidden_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in ("print", "input"):
                forbidden_calls.append(name)

    # Repository save/delete 호출 금지 확인
    write_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("save", "save_all", "save_state", "delete"):
                write_calls.append(node.func.attr)

    check("M-8-1 monitor_controller.py 에 print() 없음", "print" not in forbidden_calls)
    check("M-8-2 monitor_controller.py 에 input() 없음", "input" not in forbidden_calls)
    check("M-8-3 monitor_controller.py 에 데이터 변경 호출 없음", len(write_calls) == 0)


# ── M-9: MonitorView 역할 경계 AST 검사 ───────────────────────────

def test_m9_view_ast():
    print("\n[M-9] MonitorView 역할 경계 (AST)")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "monitor", "monitor_view.py")
    with open(path, encoding="utf-8") as f:
        source = f.read()
        tree = ast.parse(source)

    # persistence 직접 import 금지
    persistence_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "persistence" in alias.name:
                    persistence_imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and "persistence" in node.module:
                persistence_imports.append(node.module)

    check("M-9-1 monitor_view.py 에 persistence 직접 import 없음", len(persistence_imports) == 0)
    check("M-9-2 monitor_view.py 파일 정상 파싱", True)  # parse 성공 시 여기까지 도달


# ── main ──────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("모니터링 도구 검증: 구조, 집계, 역할 경계")
    print("=" * 50)

    test_m1_package_structure()
    test_m2_monitor_controller_import()
    test_m3_stock_summary()
    test_m4_order_summary()
    test_m5_production_summary()
    test_m6_empty_data()
    test_m7_monitor_view_import()
    test_m8_controller_ast()
    test_m9_view_ast()

    print("\n" + "-" * 50)
    print(f"결과: {_pass}개 통과 / {_fail}개 실패")
    if _fail == 0:
        print("[OK] 모니터링 도구 검증 완료 - 모든 항목 통과")
    else:
        print("[NG] 일부 항목 실패 - 위 [FAIL] 항목을 확인하세요")
        sys.exit(1)


if __name__ == "__main__":
    main()
