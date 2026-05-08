"""
Phase 12 검증 — monitor/ 패키지 구조, import, 빈 데이터 처리, 역할 경계 AST
"""
import ast
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_pass = 0
_fail = 0
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(label: str, condition: bool) -> None:
    global _pass, _fail
    if condition:
        print(f"[PASS] {label}")
        _pass += 1
    else:
        print(f"[FAIL] {label}")
        _fail += 1


# ──────────────────────────────────────────────────────────────
# 구조 검증
# ──────────────────────────────────────────────────────────────
def test_structure():
    print("\n[구조] 파일·디렉토리 존재 확인")
    check("monitor/ 디렉토리 존재", os.path.isdir(os.path.join(BASE, "monitor")))
    check("monitor/__init__.py 존재", os.path.isfile(os.path.join(BASE, "monitor", "__init__.py")))
    check("monitor/monitor_controller.py 존재", os.path.isfile(os.path.join(BASE, "monitor", "monitor_controller.py")))
    check("monitor/monitor_view.py 존재", os.path.isfile(os.path.join(BASE, "monitor", "monitor_view.py")))
    check("monitor_app.py 존재", os.path.isfile(os.path.join(BASE, "monitor_app.py")))


# ──────────────────────────────────────────────────────────────
# import 및 인스턴스화
# ──────────────────────────────────────────────────────────────
def test_imports():
    print("\n[import] 클래스 import 및 인스턴스화")
    from persistence.sample_repository import SampleRepository
    from persistence.order_repository import OrderRepository
    from persistence.production_repository import ProductionRepository

    tmp = tempfile.mkdtemp()
    try:
        sr = SampleRepository(os.path.join(tmp, "s.json"))
        or_ = OrderRepository(os.path.join(tmp, "o.json"))
        pr = ProductionRepository(os.path.join(tmp, "p.json"))

        try:
            from monitor.monitor_controller import MonitorController
            check("MonitorController import 성공", True)
            ctrl = MonitorController(sr, or_, pr)
            check("MonitorController 인스턴스화 성공", ctrl is not None)
            check("get_stock_summary 메서드 존재", hasattr(ctrl, "get_stock_summary"))
            check("get_order_summary 메서드 존재", hasattr(ctrl, "get_order_summary"))
            check("get_production_summary 메서드 존재", hasattr(ctrl, "get_production_summary"))
        except ImportError as e:
            for lbl in [
                f"MonitorController import 성공 ({e})",
                "MonitorController 인스턴스화 성공",
                "get_stock_summary 메서드 존재",
                "get_order_summary 메서드 존재",
                "get_production_summary 메서드 존재",
            ]:
                check(lbl, False)

        try:
            from monitor.monitor_view import MonitorView
            check("MonitorView import 성공", True)
            view = MonitorView()
            check("MonitorView 인스턴스화 성공", view is not None)
            check("render_dashboard 메서드 존재", hasattr(view, "render_dashboard"))
            check("get_user_input 메서드 존재", hasattr(view, "get_user_input"))
        except ImportError as e:
            for lbl in [
                f"MonitorView import 성공 ({e})",
                "MonitorView 인스턴스화 성공",
                "render_dashboard 메서드 존재",
                "get_user_input 메서드 존재",
            ]:
                check(lbl, False)
    finally:
        shutil.rmtree(tmp)


# ──────────────────────────────────────────────────────────────
# 빈 데이터 처리
# ──────────────────────────────────────────────────────────────
def test_empty_data():
    print("\n[빈 데이터] 파일 없을 때 정상 반환 확인")
    from persistence.sample_repository import SampleRepository
    from persistence.order_repository import OrderRepository
    from persistence.production_repository import ProductionRepository
    from monitor.monitor_controller import MonitorController

    tmp = tempfile.mkdtemp()
    try:
        ctrl = MonitorController(
            SampleRepository(os.path.join(tmp, "s.json")),
            OrderRepository(os.path.join(tmp, "o.json")),
            ProductionRepository(os.path.join(tmp, "p.json")),
        )
        stock = ctrl.get_stock_summary()
        orders = ctrl.get_order_summary()
        prod = ctrl.get_production_summary()

        check("get_stock_summary() 빈 리스트 반환", isinstance(stock, list) and len(stock) == 0)
        check("get_order_summary() dict 반환", isinstance(orders, dict))
        check(
            "get_order_summary() 4개 키 존재",
            all(k in orders for k in ("RESERVED", "PRODUCING", "CONFIRMED", "RELEASE")),
        )
        check(
            "get_order_summary() 모든 값 0",
            all(orders.get(k) == 0 for k in ("RESERVED", "PRODUCING", "CONFIRMED", "RELEASE")),
        )
        check("get_production_summary() current_job None", prod.get("current_job") is None)
        check("get_production_summary() queue 빈 목록", prod.get("queue") == [])
    finally:
        shutil.rmtree(tmp)


# ──────────────────────────────────────────────────────────────
# AST 역할 경계 — MonitorController
# ──────────────────────────────────────────────────────────────
def test_ast_controller():
    print("\n[AST] MonitorController 역할 경계")
    path = os.path.join(BASE, "monitor", "monitor_controller.py")
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    forbidden, writes = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = (
                func.id if isinstance(func, ast.Name)
                else func.attr if isinstance(func, ast.Attribute)
                else ""
            )
            if name in ("print", "input"):
                forbidden.append(name)
            if name in ("save", "save_all", "save_state", "delete"):
                writes.append(name)

    check("monitor_controller.py: print() 없음", "print" not in forbidden)
    check("monitor_controller.py: input() 없음", "input" not in forbidden)
    check("monitor_controller.py: 데이터 변경 호출 없음", not writes)


# ──────────────────────────────────────────────────────────────
# AST 역할 경계 — MonitorView
# ──────────────────────────────────────────────────────────────
def test_ast_view():
    print("\n[AST] MonitorView 역할 경계")
    path = os.path.join(BASE, "monitor", "monitor_view.py")
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    persistence_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "persistence" in alias.name:
                    persistence_imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and "persistence" in node.module:
                persistence_imports.append(node.module)

    check("monitor_view.py: persistence 직접 import 없음", not persistence_imports)


# ──────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────
def main():
    print("=" * 54)
    print("Phase 12 검증 - monitor/ 패키지")
    print("=" * 54)

    test_structure()
    test_imports()
    test_empty_data()
    test_ast_controller()
    test_ast_view()

    print("\n" + "-" * 54)
    print(f"결과: {_pass}개 통과 / {_fail}개 실패")
    if _fail == 0:
        print("[OK] Phase 12 검증 완료 - 모든 항목 통과")
    else:
        print("[FAIL] 일부 항목 실패 - 위 [FAIL] 항목을 확인하세요")
        sys.exit(1)


if __name__ == "__main__":
    main()
