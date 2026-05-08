"""
Phase 4 검증 스크립트 — View 레이어
실행: python tests/test_phase4.py  (프로젝트 루트에서)
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


def test_view_files_exist():
    required = [
        "view/main_menu_view.py",
        "view/sample_view.py",
        "view/order_view.py",
        "view/monitoring_view.py",
        "view/shipping_view.py",
        "view/production_view.py",
    ]
    for f in required:
        check(os.path.isfile(f), f"파일 존재: {f}")


def test_view_method_signatures():
    checks = [
        ("view.main_menu_view", "MainMenuView",
         ["display_menu", "display_summary", "get_menu_choice"]),
        ("view.sample_view", "SampleView",
         ["display_sample_menu", "get_register_input", "display_sample_list",
          "get_search_keyword", "display_search_result", "get_sample_menu_choice"]),
        ("view.order_view", "OrderView",
         ["display_order_menu", "get_order_input", "display_reserved_orders",
          "get_order_choice", "get_approve_or_reject", "display_order_result",
          "get_order_menu_choice"]),
        ("view.monitoring_view", "MonitoringView",
         ["display_orders_by_status", "display_stock_status"]),
        ("view.shipping_view", "ShippingView",
         ["display_confirmed_orders", "get_ship_choice", "display_ship_result"]),
        ("view.production_view", "ProductionView",
         ["display_current_production", "display_waiting_queue"]),
    ]
    for module_path, class_name, methods in checks:
        try:
            import importlib
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            for method in methods:
                check(hasattr(cls, method),
                      f"{class_name}.{method}() 메서드 존재")
        except ImportError as e:
            check(False, f"{module_path} import 실패: {e}")
        except AttributeError as e:
            check(False, f"{class_name} 클래스 없음: {e}")


def test_no_controller_import_in_views():
    for filepath in glob.glob("view/*.py"):
        if filepath.endswith("__init__.py"):
            continue
        try:
            with open(filepath, encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
            violations = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("controller"):
                            violations.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("controller"):
                        violations.append(f"from {node.module} import ...")
            check(len(violations) == 0,
                  f"{filepath}: controller import 없음" if not violations
                  else f"{filepath}: 금지된 import → {violations}")
        except Exception as e:
            check(False, f"{filepath} AST 분석 실패: {e}")


def test_no_business_logic_in_views():
    """View 파일에 상태 판정 계산(math 모듈 사용 등)이 없는지 확인"""
    for filepath in glob.glob("view/*.py"):
        if filepath.endswith("__init__.py"):
            continue
        try:
            with open(filepath, encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
            violations = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ("math",):
                            violations.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module in ("math",):
                        violations.append(f"from {node.module} import ...")
            check(len(violations) == 0,
                  f"{filepath}: 비즈니스 로직 모듈 import 없음" if not violations
                  else f"{filepath}: 금지된 import → {violations}")
        except Exception as e:
            check(False, f"{filepath} AST 분석 실패: {e}")


def test_views_use_only_print_input_for_io():
    """View가 외부 IO로 print/input만 사용하는지 확인 (file IO, network 등 금지)"""
    forbidden_calls = {"open", "requests", "urllib", "socket"}
    for filepath in glob.glob("view/*.py"):
        if filepath.endswith("__init__.py"):
            continue
        try:
            with open(filepath, encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
            violations = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in forbidden_calls:
                        violations.append(f"line {node.lineno}: {node.func.id}()")
            check(len(violations) == 0,
                  f"{filepath}: 외부 IO 없음" if not violations
                  else f"{filepath}: 금지된 외부 IO → {violations}")
        except Exception as e:
            check(False, f"{filepath} AST 분석 실패: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 4 검증 — View 레이어")
    print("=" * 50)

    test_view_files_exist()
    test_view_method_signatures()
    test_no_controller_import_in_views()
    test_no_business_logic_in_views()
    test_views_use_only_print_input_for_io()

    print("-" * 50)
    if _failures:
        print(f"결과: {len(_failures)}개 실패")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("✓ Phase 4 검증 완료 — 모든 항목 통과")
