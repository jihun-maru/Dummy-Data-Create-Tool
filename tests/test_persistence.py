"""
영속성 레이어 검증 — CRUD, 직렬화, 재시작 시나리오
"""
import os
import shutil
import sys
sys.stdout.reconfigure(encoding='utf-8')
import tempfile

# 프로젝트 루트를 sys.path에 추가 (tests/ 외부 패키지 import용)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model.order import Order
from model.order_status import OrderStatus
from model.production_line import ProductionLine
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


# ──────────────────────────────────────────────────────────────
# P-1: Sample CRUD
# ──────────────────────────────────────────────────────────────
def test_p1_sample_crud():
    print("\n[P-1] Sample CRUD")
    tmp, sample_repo, _, _ = make_temp_repos()
    try:
        # Create
        s = Sample("S001", "GaN 웨이퍼", 2.5, 0.9)
        s.stock = 100
        sample_repo.save(s)
        check("P-1-1 Sample 저장 후 파일 생성", os.path.exists(os.path.join(tmp, "samples.json")))

        # Read
        loaded = sample_repo.find_by_id("S001")
        check("P-1-2 find_by_id 반환 성공", loaded is not None)
        check("P-1-3 name 일치", loaded.name == "GaN 웨이퍼")
        check("P-1-4 stock 일치", loaded.stock == 100)
        check("P-1-5 yield_rate 일치", loaded.yield_rate == 0.9)

        # Update (재고 변경)
        loaded.stock = 50
        sample_repo.save(loaded)
        updated = sample_repo.find_by_id("S001")
        check("P-1-6 재고 수정 반영", updated.stock == 50)

        # Delete
        sample_repo.delete("S001")
        check("P-1-7 삭제 후 find_by_id None", sample_repo.find_by_id("S001") is None)
        check("P-1-8 삭제 후 load_all 빈 목록", sample_repo.load_all() == [])
    finally:
        shutil.rmtree(tmp)


# ──────────────────────────────────────────────────────────────
# P-2: Order CRUD + status 직렬화
# ──────────────────────────────────────────────────────────────
def test_p2_order_crud():
    print("\n[P-2] Order CRUD + status 직렬화")
    tmp, _, order_repo, _ = make_temp_repos()
    try:
        o = Order("O001", "S001", "A연구소", 10)
        order_repo.save(o)
        check("P-2-1 Order 저장 성공", order_repo.find_by_id("O001") is not None)

        loaded = order_repo.find_by_id("O001")
        check("P-2-2 status RESERVED 복원", loaded.status == OrderStatus.RESERVED)
        check("P-2-3 customer 일치", loaded.customer == "A연구소")
        check("P-2-4 quantity 일치", loaded.quantity == 10)

        # 상태 변경 후 저장
        loaded.status = OrderStatus.CONFIRMED
        order_repo.save(loaded)
        updated = order_repo.find_by_id("O001")
        check("P-2-5 CONFIRMED 상태 반영", updated.status == OrderStatus.CONFIRMED)

        # find_by_status
        results = order_repo.find_by_status(OrderStatus.CONFIRMED)
        check("P-2-6 find_by_status 필터 정상", len(results) == 1)
        check("P-2-7 find_by_status RESERVED 0건", len(order_repo.find_by_status(OrderStatus.RESERVED)) == 0)

        # Delete
        order_repo.delete("O001")
        check("P-2-8 삭제 후 find_by_id None", order_repo.find_by_id("O001") is None)
    finally:
        shutil.rmtree(tmp)


# ──────────────────────────────────────────────────────────────
# P-3: ProductionLine 저장/복원
# ──────────────────────────────────────────────────────────────
def test_p3_production_save_restore():
    print("\n[P-3] ProductionLine 저장/복원")
    tmp, sample_repo, order_repo, production_repo = make_temp_repos()
    try:
        # 시료·주문 준비
        s = Sample("S001", "GaN", 2.5, 0.9)
        s.stock = 0
        sample_repo.save(s)
        o = Order("O001", "S001", "A연구소", 10)
        order_repo.save(o)

        # ProductionLine에 작업 등록
        production_line = ProductionLine()
        production_line.enqueue(o, s)
        production_repo.save_state(production_line)

        # 새 인스턴스로 load_state
        state = production_repo.load_state()
        check("P-3-1 load_state None 아님", state is not None)
        check("P-3-2 current_job 데이터 존재", state.get("current_job") is not None)
        check("P-3-3 order_id 일치", state["current_job"]["order_id"] == "O001")
        check("P-3-4 sample_id 일치", state["current_job"]["sample_id"] == "S001")
        check("P-3-5 actual_qty 양수", state["current_job"]["actual_qty"] > 0)
        check("P-3-6 queue 빈 목록", state["queue"] == [])
    finally:
        shutil.rmtree(tmp)


# ──────────────────────────────────────────────────────────────
# P-4: 재시작 시뮬레이션
# ──────────────────────────────────────────────────────────────
def test_p4_restart_simulation():
    print("\n[P-4] 재시작 시뮬레이션")
    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, "samples.json")

        # 세션 A: 데이터 저장
        repo_a = SampleRepository(path)
        s = Sample("S999", "테스트 시료", 1.0, 0.8)
        s.stock = 42
        repo_a.save(s)

        # 세션 B: 동일 파일에서 로드 (재시작 시뮬레이션)
        repo_b = SampleRepository(path)
        loaded = repo_b.find_by_id("S999")
        check("P-4-1 재시작 후 find_by_id 성공", loaded is not None)
        check("P-4-2 name 보존", loaded.name == "테스트 시료")
        check("P-4-3 stock 보존", loaded.stock == 42)
        check("P-4-4 avg_production_time 보존", loaded.avg_production_time == 1.0)
    finally:
        shutil.rmtree(tmp)


# ──────────────────────────────────────────────────────────────
# P-5: 파일 미존재 시 빈 상태 초기화
# ──────────────────────────────────────────────────────────────
def test_p5_empty_initialization():
    print("\n[P-5] 파일 미존재 시 빈 상태 초기화")
    tmp = tempfile.mkdtemp()
    try:
        sample_path = os.path.join(tmp, "new_dir", "samples.json")
        order_path  = os.path.join(tmp, "new_dir", "orders.json")
        prod_path   = os.path.join(tmp, "new_dir", "production.json")

        sample_repo = SampleRepository(sample_path)
        order_repo  = OrderRepository(order_path)
        prod_repo   = ProductionRepository(prod_path)

        check("P-5-1 SampleRepository load_all 빈 목록", sample_repo.load_all() == [])
        check("P-5-2 OrderRepository load_all 빈 목록", order_repo.load_all() == [])
        check("P-5-3 ProductionRepository load_state None", prod_repo.load_state() is None)
        check("P-5-4 data 디렉토리 자동 생성", os.path.isdir(os.path.join(tmp, "new_dir")))
    finally:
        shutil.rmtree(tmp)


# ──────────────────────────────────────────────────────────────
# P-6: upsert 동작 (동일 ID 두 번 save)
# ──────────────────────────────────────────────────────────────
def test_p6_upsert():
    print("\n[P-6] upsert 동작")
    tmp, sample_repo, order_repo, _ = make_temp_repos()
    try:
        # Sample upsert
        s1 = Sample("S001", "초기 이름", 1.0, 0.8)
        s1.stock = 10
        sample_repo.save(s1)

        s2 = Sample("S001", "변경된 이름", 2.0, 0.9)
        s2.stock = 99
        sample_repo.save(s2)

        all_samples = sample_repo.load_all()
        check("P-6-1 Sample 중복 없음 (1건)", len(all_samples) == 1)
        check("P-6-2 Sample 최신값 반영", all_samples[0].name == "변경된 이름")
        check("P-6-3 Sample stock 최신값", all_samples[0].stock == 99)

        # Order upsert
        o1 = Order("O001", "S001", "A연구소", 5)
        order_repo.save(o1)
        o1.status = OrderStatus.CONFIRMED
        order_repo.save(o1)

        all_orders = order_repo.load_all()
        check("P-6-4 Order 중복 없음 (1건)", len(all_orders) == 1)
        check("P-6-5 Order status 최신값", all_orders[0].status == OrderStatus.CONFIRMED)
    finally:
        shutil.rmtree(tmp)


# ──────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("영속성 레이어 검증 — CRUD 및 재시작 시나리오")
    print("=" * 50)

    test_p1_sample_crud()
    test_p2_order_crud()
    test_p3_production_save_restore()
    test_p4_restart_simulation()
    test_p5_empty_initialization()
    test_p6_upsert()

    print("\n" + "-" * 50)
    print(f"결과: {_pass}개 통과 / {_fail}개 실패")
    if _fail == 0:
        print("✓ 영속성 검증 완료 — 모든 항목 통과")
    else:
        print("✗ 일부 항목 실패 — 위 [FAIL] 항목을 확인하세요")
        sys.exit(1)


if __name__ == "__main__":
    main()
