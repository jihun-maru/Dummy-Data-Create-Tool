"""
Phase 8 검증 스크립트 — 구체 Repository 3종 (SampleRepository, OrderRepository, ProductionRepository)
실행: python tests/test_phase8.py  (프로젝트 루트에서)
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


def _tmp_repos():
    """격리된 임시 Repository 3종을 반환한다."""
    from persistence.sample_repository import SampleRepository
    from persistence.order_repository import OrderRepository
    from persistence.production_repository import ProductionRepository

    tmp = tempfile.mkdtemp()
    return (
        tmp,
        SampleRepository(os.path.join(tmp, "samples.json")),
        OrderRepository(os.path.join(tmp, "orders.json")),
        ProductionRepository(os.path.join(tmp, "production.json")),
    )


# ──────────────────────────────────────────────────────────────
# 1. 파일 존재 확인
# ──────────────────────────────────────────────────────────────
def test_repository_files_exist():
    required = [
        "persistence/sample_repository.py",
        "persistence/order_repository.py",
        "persistence/production_repository.py",
    ]
    for f in required:
        check(os.path.isfile(f), f"파일 존재: {f}")


# ──────────────────────────────────────────────────────────────
# 2. import 확인
# ──────────────────────────────────────────────────────────────
def test_repository_imports():
    try:
        from persistence.sample_repository import SampleRepository
        check(True, "SampleRepository import 성공")
    except ImportError as e:
        check(False, f"SampleRepository import 실패: {e}")

    try:
        from persistence.order_repository import OrderRepository
        check(True, "OrderRepository import 성공")
    except ImportError as e:
        check(False, f"OrderRepository import 실패: {e}")

    try:
        from persistence.production_repository import ProductionRepository
        check(True, "ProductionRepository import 성공")
    except ImportError as e:
        check(False, f"ProductionRepository import 실패: {e}")


# ──────────────────────────────────────────────────────────────
# 3. SampleRepository CRUD 검증
# ──────────────────────────────────────────────────────────────
def test_sample_repository_crud():
    try:
        from model.sample import Sample

        tmp, sample_repo, _, _ = _tmp_repos()
        try:
            # 빈 초기 상태
            check(sample_repo.load_all() == [], "SampleRepository: 초기 load_all() == []")

            # Create
            s = Sample("S001", "GaN 웨이퍼", 2.5, 0.9)
            s.stock = 100
            sample_repo.save(s)
            check(os.path.isfile(os.path.join(tmp, "samples.json")), "SampleRepository.save(): 파일 생성")

            # Read
            loaded = sample_repo.find_by_id("S001")
            check(loaded is not None, "SampleRepository.find_by_id(): 저장된 항목 반환")
            check(loaded.sample_id == "S001", "find_by_id(): sample_id 일치")
            check(loaded.name == "GaN 웨이퍼", "find_by_id(): name 일치")
            check(loaded.avg_production_time == 2.5, "find_by_id(): avg_production_time 일치")
            check(loaded.yield_rate == 0.9, "find_by_id(): yield_rate 일치")
            check(loaded.stock == 100, "find_by_id(): stock 일치")
            check(len(sample_repo.load_all()) == 1, "load_all(): 1건 반환")

            # Update (upsert)
            loaded.stock = 50
            sample_repo.save(loaded)
            updated = sample_repo.find_by_id("S001")
            check(updated.stock == 50, "SampleRepository.save() upsert: stock 업데이트")
            check(len(sample_repo.load_all()) == 1, "upsert 후 중복 없음 (1건)")

            # find_by_id 없는 경우
            check(sample_repo.find_by_id("X999") is None, "find_by_id(): 없는 ID → None")

            # Delete
            sample_repo.delete("S001")
            check(sample_repo.find_by_id("S001") is None, "SampleRepository.delete(): 삭제 확인")
            check(sample_repo.load_all() == [], "delete() 후 load_all() == []")
        finally:
            shutil.rmtree(tmp)
    except Exception as e:
        check(False, f"SampleRepository CRUD 오류: {e}")


# ──────────────────────────────────────────────────────────────
# 4. OrderRepository CRUD + 상태 직렬화 검증
# ──────────────────────────────────────────────────────────────
def test_order_repository_crud():
    try:
        from model.order import Order
        from model.order_status import OrderStatus

        tmp, _, order_repo, _ = _tmp_repos()
        try:
            check(order_repo.load_all() == [], "OrderRepository: 초기 load_all() == []")

            # Create
            o = Order("O001", "S001", "A연구소", 10)
            order_repo.save(o)

            # Read
            loaded = order_repo.find_by_id("O001")
            check(loaded is not None, "OrderRepository.find_by_id(): 저장된 항목 반환")
            check(loaded.order_id == "O001", "find_by_id(): order_id 일치")
            check(loaded.customer == "A연구소", "find_by_id(): customer 일치")
            check(loaded.quantity == 10, "find_by_id(): quantity 일치")
            check(loaded.status == OrderStatus.RESERVED, "find_by_id(): status RESERVED 복원 (Enum)")

            # Enum 직렬화 확인 (파일에 문자열로 저장됐는지)
            import json
            with open(os.path.join(tmp, "orders.json"), encoding="utf-8") as f:
                raw = json.load(f)
            check(raw[0]["status"] == "RESERVED", "orders.json: status가 문자열로 직렬화")

            # 상태 변경 upsert
            loaded.status = OrderStatus.CONFIRMED
            order_repo.save(loaded)
            updated = order_repo.find_by_id("O001")
            check(updated.status == OrderStatus.CONFIRMED, "upsert: CONFIRMED 상태 반영")
            check(len(order_repo.load_all()) == 1, "upsert 후 중복 없음 (1건)")

            # find_by_status
            confirmed = order_repo.find_by_status(OrderStatus.CONFIRMED)
            check(len(confirmed) == 1, "find_by_status(CONFIRMED): 1건")
            reserved = order_repo.find_by_status(OrderStatus.RESERVED)
            check(len(reserved) == 0, "find_by_status(RESERVED): 0건 (상태 변경 후)")

            # 여러 상태 혼재
            o2 = Order("O002", "S001", "B연구소", 5)
            order_repo.save(o2)
            check(
                len(order_repo.find_by_status(OrderStatus.RESERVED)) == 1,
                "find_by_status: RESERVED 1건 (O002)",
            )

            # Delete
            order_repo.delete("O001")
            check(order_repo.find_by_id("O001") is None, "delete(): O001 삭제 확인")
            check(len(order_repo.load_all()) == 1, "delete() 후 O002 남음")
        finally:
            shutil.rmtree(tmp)
    except Exception as e:
        check(False, f"OrderRepository CRUD 오류: {e}")


# ──────────────────────────────────────────────────────────────
# 5. ProductionRepository save_state / load_state 검증
# ──────────────────────────────────────────────────────────────
def test_production_repository():
    try:
        from model.sample import Sample
        from model.order import Order
        from model.production_line import ProductionLine

        tmp, sample_repo, order_repo, production_repo = _tmp_repos()
        try:
            # 파일 없을 때 None 반환
            check(production_repo.load_state() is None, "ProductionRepository.load_state(): 파일 없으면 None")

            # 시료·주문 준비 (enqueue에 필요)
            s = Sample("S001", "생산시료", 1.0, 0.9)
            s.stock = 0
            sample_repo.save(s)
            o = Order("O001", "S001", "고객A", 10)
            order_repo.save(o)

            pl = ProductionLine()
            pl.enqueue(o, s)
            production_repo.save_state(pl)

            state = production_repo.load_state()
            check(state is not None, "save_state() 후 load_state() None 아님")
            check(isinstance(state, dict), "load_state(): dict 반환")
            check(state.get("current_job") is not None, "current_job 데이터 존재")
            check(state["current_job"]["order_id"] == "O001", "current_job.order_id 일치")
            check(state["current_job"]["sample_id"] == "S001", "current_job.sample_id 일치")
            check(state["current_job"]["actual_qty"] > 0, "current_job.actual_qty 양수")
            check(state["current_job"]["total_time"] > 0, "current_job.total_time 양수")
            check(isinstance(state.get("queue"), list), "queue 필드 list 타입")
            check(len(state["queue"]) == 0, "queue 비어있음 (단일 작업)")

            # 큐에 2개 이상 등록
            o2 = Order("O002", "S001", "고객B", 5)
            order_repo.save(o2)
            pl.enqueue(o2, s)
            production_repo.save_state(pl)
            state2 = production_repo.load_state()
            check(len(state2["queue"]) == 1, "2번째 enqueue 후 queue 1건")
        finally:
            shutil.rmtree(tmp)
    except Exception as e:
        check(False, f"ProductionRepository 오류: {e}")


# ──────────────────────────────────────────────────────────────
# 6. 재시작 시뮬레이션 — 같은 파일을 새 인스턴스로 로드
# ──────────────────────────────────────────────────────────────
def test_restart_simulation():
    try:
        from model.sample import Sample
        from persistence.sample_repository import SampleRepository

        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "samples.json")

            repo_a = SampleRepository(path)
            s = Sample("S999", "재시작시료", 1.5, 0.85)
            s.stock = 77
            repo_a.save(s)

            # 새 인스턴스 (재시작 시뮬레이션)
            repo_b = SampleRepository(path)
            loaded = repo_b.find_by_id("S999")
            check(loaded is not None, "재시작 후 find_by_id() 성공")
            check(loaded.name == "재시작시료", "재시작 후 name 보존")
            check(loaded.stock == 77, "재시작 후 stock 보존")
            check(loaded.yield_rate == 0.85, "재시작 후 yield_rate 보존")
        finally:
            shutil.rmtree(tmp)
    except Exception as e:
        check(False, f"재시작 시뮬레이션 오류: {e}")


# ──────────────────────────────────────────────────────────────
# 7. AST 검사 — persistence/*.py에 print/input 없음
# ──────────────────────────────────────────────────────────────
def test_no_print_input_in_persistence():
    for filepath in glob.glob("persistence/*.py"):
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
# 메인
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("Phase 8 검증 — 구체 Repository 3종")
    print("=" * 50)

    test_repository_files_exist()
    test_repository_imports()
    test_sample_repository_crud()
    test_order_repository_crud()
    test_production_repository()
    test_restart_simulation()
    test_no_print_input_in_persistence()

    print("-" * 50)
    if _failures:
        print(f"결과: {len(_failures)}개 실패")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("✓ Phase 8 검증 완료 — 모든 항목 통과")
