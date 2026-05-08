"""
더미 데이터 생성 도구 최종 통합 검증 — Phase D-1~D-3 E2E
"""
import gc
import os
import subprocess
import sys
import tempfile

# Windows CP949 환경에서 한글 출력 보장
import io
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    msg = f"{status} {name}"
    if not condition and detail:
        msg += f" — {detail}"
    print(msg)
    results.append(condition)


def make_temp_db() -> str:
    """임시 DB 파일 경로를 반환한다. DummyInserter가 새로 생성하도록 파일을 삭제해 둔다."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


# ---------------------------------------------------------------------------
# 단계 1: test_dummy.py subprocess 실행 — D-1~D-9 전체 통과 확인
# ---------------------------------------------------------------------------

def test_step1_run_test_dummy() -> None:
    print("\n[단계 1] 단위 검증 (test_dummy.py)")
    print("-" * 54)
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, os.path.join(base, "tests", "test_dummy.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=base,
    )
    passed = result.returncode == 0
    if not passed:
        print(result.stdout[-2000:] if result.stdout else "")
        print(result.stderr[-500:] if result.stderr else "")
    check("단계 1: test_dummy.py (D-1~D-9) 전체 통과", passed)


# ---------------------------------------------------------------------------
# 단계 2: E2E 기본 세트 생성 → 삽입 → SELECT 건수 검증
# ---------------------------------------------------------------------------

def test_step2_e2e_basic_set() -> None:
    print("\n[단계 2] E2E — 기본 세트 생성 및 삽입")
    print("-" * 54)
    tmp = make_temp_db()
    try:
        import sqlite3
        from dummy.sample_generator import generate_samples
        from dummy.order_generator import generate_orders
        from dummy.production_generator import generate_production_jobs
        from dummy.db.inserter import DummyInserter

        # 기본 세트 생성
        samples = generate_samples(5)
        orders = generate_orders(samples, 20)
        jobs = generate_production_jobs(orders, samples)

        inserter = DummyInserter(db_path=tmp)
        n_s = inserter.insert_samples(samples)
        n_o = inserter.insert_orders(orders)
        n_j = inserter.insert_production_jobs(jobs)

        # SELECT로 검증
        with sqlite3.connect(tmp) as conn:
            cnt_s = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
            cnt_o = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            cnt_j = conn.execute("SELECT COUNT(*) FROM production_jobs").fetchone()[0]

            # 외래 키 무결성: orders.sample_id 가 samples 에 모두 존재
            invalid_fk = conn.execute(
                "SELECT COUNT(*) FROM orders o "
                "LEFT JOIN samples s ON o.sample_id = s.sample_id "
                "WHERE s.sample_id IS NULL"
            ).fetchone()[0]

            # PRODUCING 주문 수 = production_jobs 행 수
            producing_count = conn.execute(
                "SELECT COUNT(*) FROM orders WHERE status = 'PRODUCING'"
            ).fetchone()[0]

            # is_current=1 플래그 최대 1개
            current_count = conn.execute(
                "SELECT COUNT(*) FROM production_jobs WHERE is_current = 1"
            ).fetchone()[0]

        check("단계 2-1: 시료 5개 삽입", cnt_s == 5, f"실제 {cnt_s}개")
        check("단계 2-2: 주문 20개 삽입", cnt_o == 20, f"실제 {cnt_o}개")
        check("단계 2-3: 외래 키 무결성", invalid_fk == 0, f"무결성 위반 {invalid_fk}건")
        check(
            "단계 2-4: PRODUCING 수 = production_jobs 수",
            cnt_j == producing_count,
            f"jobs={cnt_j}, PRODUCING={producing_count}",
        )
        check(
            "단계 2-5: is_current=1 최대 1개",
            current_count <= 1,
            f"is_current=1 행 {current_count}개",
        )

    except Exception as e:
        check(f"단계 2 E2E 기본 세트 ({e})", False)
    finally:
        gc.collect()
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# 단계 3: reset() 후 재삽입 — upsert 검증 (중복 없이 동일 건수 유지)
# ---------------------------------------------------------------------------

def test_step3_reset_and_reinsert() -> None:
    print("\n[단계 3] reset() 후 재삽입 검증")
    print("-" * 54)
    tmp = make_temp_db()
    try:
        import sqlite3
        from dummy.sample_generator import generate_samples
        from dummy.order_generator import generate_orders
        from dummy.production_generator import generate_production_jobs
        from dummy.db.inserter import DummyInserter

        samples = generate_samples(3)
        orders = generate_orders(samples, 10)
        jobs = generate_production_jobs(orders, samples)

        inserter = DummyInserter(db_path=tmp)

        # 1회 삽입
        inserter.insert_samples(samples)
        inserter.insert_orders(orders)
        inserter.insert_production_jobs(jobs)

        # reset 후 재삽입
        inserter.reset()
        inserter.insert_samples(samples)
        inserter.insert_orders(orders)
        inserter.insert_production_jobs(jobs)

        with sqlite3.connect(tmp) as conn:
            cnt_s = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
            cnt_o = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            cnt_j = conn.execute("SELECT COUNT(*) FROM production_jobs").fetchone()[0]

        check(
            "단계 3-1: reset 후 재삽입 — samples 중복 없음",
            cnt_s == len(samples),
            f"기대 {len(samples)}, 실제 {cnt_s}",
        )
        check(
            "단계 3-2: reset 후 재삽입 — orders 중복 없음",
            cnt_o == len(orders),
            f"기대 {len(orders)}, 실제 {cnt_o}",
        )
        check(
            "단계 3-3: reset 후 재삽입 — production_jobs 중복 없음",
            cnt_j == len(jobs),
            f"기대 {len(jobs)}, 실제 {cnt_j}",
        )

    except Exception as e:
        check(f"단계 3 reset 재삽입 ({e})", False)
    finally:
        gc.collect()
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# 단계 4: 전체 파일 구조 최종 확인
# ---------------------------------------------------------------------------

def test_step4_file_structure() -> None:
    print("\n[단계 4] 전체 파일 구조 최종 확인")
    print("-" * 54)
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    required_files = [
        "main.py",
        "monitor_app.py",
        "dummy_app.py",
        "dummy/__init__.py",
        "dummy/sample_generator.py",
        "dummy/order_generator.py",
        "dummy/production_generator.py",
        "dummy/db/__init__.py",
        "dummy/db/connection.py",
        "dummy/db/schema.py",
        "dummy/db/inserter.py",
        "tests/test_dummy.py",
        "tests/test_dummy_final.py",
    ]
    for rel in required_files:
        full = os.path.join(base, rel)
        check(f"파일 존재: {rel}", os.path.isfile(full))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 54)
    print("더미 데이터 생성 도구 최종 통합 검증")
    print("=" * 54)

    test_step1_run_test_dummy()
    test_step2_e2e_basic_set()
    test_step3_reset_and_reinsert()
    test_step4_file_structure()

    total = len(results)
    passed = sum(results)
    print(f"\n결과: {passed}개 통과 / {total - passed}개 실패")
    if passed == total:
        print("✓ 최종 통합 검증 완료 — 모든 항목 통과")
        print("  더미 데이터 생성 도구 POC 구현 완성")
    else:
        print("✗ 일부 항목 실패 — 위 [FAIL] 항목을 확인하세요")
    sys.exit(0 if passed == total else 1)
