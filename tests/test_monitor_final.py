"""
데이터 모니터링 도구 최종 통합 검증 — 전체 Phase E2E
"""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile

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


def run_script(rel_path: str, label: str) -> bool:
    path = os.path.join(BASE, rel_path)
    if not os.path.isfile(path):
        check(f"{label} (파일 없음: {rel_path})", False)
        return False
    result = subprocess.run([sys.executable, path], capture_output=True, text=True)
    success = result.returncode == 0
    check(label, success)
    if not success:
        tail = result.stdout[-600:] if result.stdout else ""
        err = result.stderr[-300:] if result.stderr else ""
        if tail:
            print(f"  stdout(끝):\n{tail}")
        if err:
            print(f"  stderr:\n{err}")
    return success


# ──────────────────────────────────────────────────────────────
# 단계 1: 기존 전체 Phase 검증 (Phase 1~11)
# ──────────────────────────────────────────────────────────────
def run_legacy_final():
    print("\n[단계 1] 기존 전체 Phase 검증 (test_final.py)")
    print("-" * 54)
    run_script("tests/test_final.py", "Phase 1~11 전체 검증 (test_final.py)")


# ──────────────────────────────────────────────────────────────
# 단계 2: 모니터링 도구 Phase 검증 (Phase 12~13)
# ──────────────────────────────────────────────────────────────
def run_monitor_phase_scripts():
    print("\n[단계 2] 모니터링 도구 Phase 검증")
    print("-" * 54)
    run_script("tests/test_phase12.py", "Phase 12: monitor/ 패키지 구조·역할 경계")
    run_script("tests/test_monitor.py", "Phase 13: 모니터링 도구 집계·AST 검증")


# ──────────────────────────────────────────────────────────────
# 단계 3: E2E 모니터링 시나리오
# ──────────────────────────────────────────────────────────────
def run_e2e_scenario():
    print("\n[단계 3] E2E 모니터링 시나리오")
    print("-" * 54)

    from model.sample import Sample
    from model.order import Order
    from model.order_status import OrderStatus
    from model.production_line import ProductionLine
    from persistence.sample_repository import SampleRepository
    from persistence.order_repository import OrderRepository
    from persistence.production_repository import ProductionRepository
    from monitor.monitor_controller import MonitorController
    from monitor.monitor_view import MonitorView

    tmp = tempfile.mkdtemp()
    try:
        sample_repo = SampleRepository(os.path.join(tmp, "samples.json"))
        order_repo = OrderRepository(os.path.join(tmp, "orders.json"))
        production_repo = ProductionRepository(os.path.join(tmp, "production.json"))

        # ── 세션 1: 데이터 생성 (메인 앱 시뮬레이션) ────────────
        s1 = Sample("S001", "GaN 웨이퍼", 2.5, 0.9)
        s1.stock = 100
        sample_repo.save(s1)

        s2 = Sample("S002", "SiC 웨이퍼", 3.0, 0.8)
        s2.stock = 0
        sample_repo.save(s2)

        for oid, sid, status, qty in [
            ("O001", "S001", OrderStatus.RESERVED,  5),
            ("O002", "S001", OrderStatus.CONFIRMED, 10),
            ("O003", "S002", OrderStatus.PRODUCING, 8),
            ("O004", "S001", OrderStatus.RELEASE,   3),
            ("O005", "S001", OrderStatus.REJECTED,  2),  # 집계 제외 대상
        ]:
            o = Order(oid, sid, "고객", qty)
            o.status = status
            order_repo.save(o)

        pl = ProductionLine()
        o_prod = order_repo.find_by_id("O003")
        pl.enqueue(o_prod, s2)
        production_repo.save_state(pl)

        check("세션 1: 시료 2개 등록 완료", len(sample_repo.load_all()) == 2)
        check("세션 1: 주문 5개 등록 완료", len(order_repo.load_all()) == 5)

        # ── 세션 2: 모니터링 도구로 조회 ────────────────────────
        ctrl = MonitorController(sample_repo, order_repo, production_repo)

        stock = ctrl.get_stock_summary()
        check("세션 2: 재고 현황 2건 반환", len(stock) == 2)

        s1_info = next((r for r in stock if r["sample_id"] == "S001"), None)
        s2_info = next((r for r in stock if r["sample_id"] == "S002"), None)
        check("세션 2: S001 재고 상태 여유", s1_info is not None and s1_info["status"] == "여유")
        check("세션 2: S002 재고 상태 고갈", s2_info is not None and s2_info["status"] == "고갈")

        orders = ctrl.get_order_summary()
        check("세션 2: RESERVED 1건", orders.get("RESERVED") == 1)
        check("세션 2: CONFIRMED 1건", orders.get("CONFIRMED") == 1)
        check("세션 2: PRODUCING 1건", orders.get("PRODUCING") == 1)
        check("세션 2: RELEASE 1건",   orders.get("RELEASE")   == 1)
        check("세션 2: REJECTED 집계 제외", "REJECTED" not in orders)

        prod = ctrl.get_production_summary()
        check("세션 2: 생산 current_job 존재", prod.get("current_job") is not None)
        check("세션 2: current_job order_id O003", prod["current_job"].get("order_id") == "O003")

        # ── 세션 2: 대시보드 렌더링 검증 ────────────────────────
        view = MonitorView()
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                view.render_dashboard(stock, orders, prod, False, 5)
            rendered = buf.getvalue()
            check("세션 2: render_dashboard 오류 없이 실행", True)
            check("세션 2: 대시보드에 S001 포함",       "S001"     in rendered)
            check("세션 2: 대시보드에 주문 현황 포함",  "RESERVED" in rendered)
            check("세션 2: 대시보드에 생산 작업 포함",  "O003"     in rendered)
        except Exception as e:
            check(f"세션 2: render_dashboard 오류 없이 실행 ({e})", False)
            check("세션 2: 대시보드에 S001 포함", False)
            check("세션 2: 대시보드에 주문 현황 포함", False)
            check("세션 2: 대시보드에 생산 작업 포함", False)

    finally:
        shutil.rmtree(tmp)


# ──────────────────────────────────────────────────────────────
# 단계 4: 전체 파일 구조 최종 확인
# ──────────────────────────────────────────────────────────────
def check_final_structure():
    print("\n[단계 4] 전체 파일 구조 최종 확인")
    print("-" * 54)
    required = [
        # 기존 POC 파일
        "main.py",
        "model/sample.py",
        "model/order.py",
        "persistence/base_repository.py",
        "persistence/sample_repository.py",
        "persistence/order_repository.py",
        "persistence/production_repository.py",
        # 3차 POC 신규 파일
        "monitor/__init__.py",
        "monitor/monitor_controller.py",
        "monitor/monitor_view.py",
        "monitor_app.py",
        # 테스트 파일
        "tests/test_phase12.py",
        "tests/test_monitor.py",
        "tests/test_monitor_final.py",
    ]
    for rel_path in required:
        check(f"파일 존재: {rel_path}", os.path.isfile(os.path.join(BASE, rel_path)))


# ──────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────
def main():
    print("=" * 54)
    print("데이터 모니터링 도구 최종 통합 검증")
    print("=" * 54)

    run_legacy_final()
    run_monitor_phase_scripts()
    run_e2e_scenario()
    check_final_structure()

    print("\n" + "=" * 54)
    print(f"결과: {_pass}개 통과 / {_fail}개 실패")
    if _fail == 0:
        print("✓ 최종 통합 검증 완료 — 모든 항목 통과")
        print("  데이터 모니터링 도구 POC 구현 완성")
    else:
        print("✗ 일부 항목 실패 — 위 [FAIL] 항목을 확인하세요")
        sys.exit(1)


if __name__ == "__main__":
    main()
