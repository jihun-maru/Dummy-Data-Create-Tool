"""
더미 데이터 생성 도구 검증 - 패키지 구조, 생성기, DB 연동, 역할 경계 AST
"""
import ast
import gc
import io
import os
import shutil
import sys
import tempfile

# Windows CP949 환경에서 한글 출력 보장
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def make_temp_db() -> str:
    """임시 DB 파일 경로를 반환한다. 사용 후 직접 삭제해야 한다."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)  # DummyInserter가 새로 생성하도록 삭제
    return path


# ---------------------------------------------------------------------------
# D-1: 패키지 구조 검증
# ---------------------------------------------------------------------------

def test_d1_package_structure():
    print("\n[D-1] 패키지 구조 검증")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [
        ("dummy/",                        os.path.isdir),
        ("dummy/__init__.py",             os.path.isfile),
        ("dummy/db/",                     os.path.isdir),
        ("dummy/db/__init__.py",          os.path.isfile),
        ("dummy/db/connection.py",        os.path.isfile),
        ("dummy/db/schema.py",            os.path.isfile),
        ("dummy/db/inserter.py",          os.path.isfile),
        ("dummy/sample_generator.py",     os.path.isfile),
        ("dummy/order_generator.py",      os.path.isfile),
        ("dummy/production_generator.py", os.path.isfile),
        ("dummy_app.py",                  os.path.isfile),
    ]
    for rel_path, check_fn in files:
        full = os.path.join(base, rel_path.rstrip("/"))
        check(f"D-1 {rel_path} 존재", check_fn(full))


# ---------------------------------------------------------------------------
# D-2: DB 연결 및 스키마 생성
# ---------------------------------------------------------------------------

def test_d2_db_schema():
    print("\n[D-2] DB 연결 및 스키마 생성")
    tmp = make_temp_db()
    try:
        from dummy.db.connection import get_connection
        from dummy.db.schema import create_tables
        import sqlite3

        with get_connection(tmp) as conn:
            create_tables(conn)

        # 테이블 3개 확인
        with sqlite3.connect(tmp) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = {row[0] for row in cursor.fetchall()}

        check("D-2-1 get_connection import 성공", True)
        check("D-2-2 create_tables import 성공", True)
        check("D-2-3 samples 테이블 생성", "samples" in tables)
        check("D-2-4 orders 테이블 생성", "orders" in tables)
        check("D-2-5 production_jobs 테이블 생성", "production_jobs" in tables)
    except Exception as e:
        check(f"D-2 DB 스키마 생성 ({e})", False)
    finally:
        gc.collect()
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# D-3: Sample 생성기 검증
# ---------------------------------------------------------------------------

def test_d3_sample_generator():
    print("\n[D-3] Sample 생성기 검증")
    try:
        from dummy.sample_generator import generate_samples

        samples = generate_samples(5)
        check("D-3-1 반환값 리스트 타입", isinstance(samples, list))
        check("D-3-2 5개 반환", len(samples) == 5)
        check("D-3-3 sample_id 속성 존재", all(hasattr(s, "sample_id") for s in samples))
        check("D-3-4 name 속성 존재", all(hasattr(s, "name") for s in samples))
        check("D-3-5 stock 속성 존재", all(hasattr(s, "stock") for s in samples))
        check("D-3-6 yield_rate 범위 (0~1]", all(0 < s.yield_rate <= 1.0 for s in samples))
        check("D-3-7 avg_production_time 양수", all(s.avg_production_time > 0 for s in samples))
        check("D-3-8 stock 0 이상", all(s.stock >= 0 for s in samples))
        ids = [s.sample_id for s in samples]
        check("D-3-9 sample_id 중복 없음", len(ids) == len(set(ids)))
    except Exception as e:
        check(f"D-3 Sample 생성기 ({e})", False)


# ---------------------------------------------------------------------------
# D-4: Order 생성기 검증
# ---------------------------------------------------------------------------

def test_d4_order_generator():
    print("\n[D-4] Order 생성기 검증")
    try:
        from dummy.sample_generator import generate_samples
        from dummy.order_generator import generate_orders
        from model.order_status import OrderStatus

        samples = generate_samples(3)
        orders = generate_orders(samples, 20)

        check("D-4-1 반환값 리스트 타입", isinstance(orders, list))
        check("D-4-2 20개 반환", len(orders) == 20)
        check("D-4-3 order_id 속성 존재", all(hasattr(o, "order_id") for o in orders))
        check("D-4-4 quantity 양수", all(o.quantity > 0 for o in orders))
        check("D-4-5 REJECTED 미포함", all(o.status != OrderStatus.REJECTED for o in orders))

        statuses = {o.status for o in orders}
        expected = {OrderStatus.RESERVED, OrderStatus.PRODUCING, OrderStatus.CONFIRMED, OrderStatus.RELEASE}
        check("D-4-6 4가지 상태 모두 포함", statuses == expected)
    except Exception as e:
        check(f"D-4 Order 생성기 ({e})", False)


# ---------------------------------------------------------------------------
# D-5: ProductionJob 생성기 검증
# ---------------------------------------------------------------------------

def test_d5_production_generator():
    print("\n[D-5] ProductionJob 생성기 검증")
    try:
        from dummy.sample_generator import generate_samples
        from dummy.order_generator import generate_orders
        from dummy.production_generator import generate_production_jobs
        from model.order_status import OrderStatus

        samples = generate_samples(3)
        orders = generate_orders(samples, 20)
        jobs = generate_production_jobs(orders, samples)

        producing_count = sum(1 for o in orders if o.status == OrderStatus.PRODUCING)
        check("D-5-1 반환값 리스트 타입", isinstance(jobs, list))
        check("D-5-2 PRODUCING 주문 수와 동일", len(jobs) == producing_count)

        if jobs:
            current_count = sum(1 for j in jobs if j.get("is_current") == 1)
            check("D-5-3 is_current=1 최대 1개", current_count <= 1)
            check("D-5-4 필수 키 존재", all(
                all(k in j for k in ("order_id", "sample_id", "actual_qty", "total_time", "produced_qty", "is_current"))
                for j in jobs
            ))
            check("D-5-5 actual_qty 양수", all(j["actual_qty"] > 0 for j in jobs))
            check("D-5-6 total_time 양수", all(j["total_time"] > 0 for j in jobs))
        else:
            check("D-5-3 PRODUCING 없으면 빈 리스트 정상", True)
    except Exception as e:
        check(f"D-5 ProductionJob 생성기 ({e})", False)


# ---------------------------------------------------------------------------
# D-6: DB 삽입 검증
# ---------------------------------------------------------------------------

def test_d6_db_insert():
    print("\n[D-6] DB 삽입 검증")
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
        n_s = inserter.insert_samples(samples)
        n_o = inserter.insert_orders(orders)
        n_j = inserter.insert_production_jobs(jobs)

        with sqlite3.connect(tmp) as conn:
            cnt_s = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
            cnt_o = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            cnt_j = conn.execute("SELECT COUNT(*) FROM production_jobs").fetchone()[0]

        check("D-6-1 insert_samples 반환 건수 일치", n_s == len(samples))
        check("D-6-2 insert_orders 반환 건수 일치", n_o == len(orders))
        check("D-6-3 insert_production_jobs 반환 건수 일치", n_j == len(jobs))
        check("D-6-4 DB samples 건수 일치", cnt_s == len(samples))
        check("D-6-5 DB orders 건수 일치", cnt_o == len(orders))
        check("D-6-6 DB production_jobs 건수 일치", cnt_j == len(jobs))
    except Exception as e:
        check(f"D-6 DB 삽입 ({e})", False)
    finally:
        gc.collect()
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# D-7: DB 초기화(reset) 검증
# ---------------------------------------------------------------------------

def test_d7_db_reset():
    print("\n[D-7] DB 초기화(reset) 검증")
    tmp = make_temp_db()
    try:
        import sqlite3
        from dummy.sample_generator import generate_samples
        from dummy.order_generator import generate_orders
        from dummy.db.inserter import DummyInserter

        samples = generate_samples(3)
        orders = generate_orders(samples, 5)

        inserter = DummyInserter(db_path=tmp)
        inserter.insert_samples(samples)
        inserter.insert_orders(orders)

        inserter.reset()

        with sqlite3.connect(tmp) as conn:
            cnt_s = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
            cnt_o = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

        check("D-7-1 reset() 후 samples 0건", cnt_s == 0)
        check("D-7-2 reset() 후 orders 0건", cnt_o == 0)
    except Exception as e:
        check(f"D-7 DB 초기화 ({e})", False)
    finally:
        gc.collect()
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# D-8: 빈 PRODUCING 처리
# ---------------------------------------------------------------------------

def test_d8_empty_producing():
    print("\n[D-8] 빈 PRODUCING 처리")
    try:
        from dummy.sample_generator import generate_samples
        from dummy.order_generator import generate_orders, DEFAULT_STATUS_RATIO
        from dummy.production_generator import generate_production_jobs

        samples = generate_samples(3)
        # PRODUCING 비율 0으로 설정
        ratio = {"RESERVED": 0.5, "PRODUCING": 0.0, "CONFIRMED": 0.3, "RELEASE": 0.2}
        orders = generate_orders(samples, 10, status_ratio=ratio)
        jobs = generate_production_jobs(orders, samples)

        check("D-8-1 PRODUCING 없을 때 빈 리스트 반환", isinstance(jobs, list))
        check("D-8-2 jobs 길이 0", len(jobs) == 0)
    except Exception as e:
        check(f"D-8 빈 PRODUCING 처리 ({e})", False)


# ---------------------------------------------------------------------------
# D-9: 역할 경계 AST 검사
# ---------------------------------------------------------------------------

def test_d9_ast_boundary():
    print("\n[D-9] 역할 경계 (AST)")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generator_files = [
        os.path.join(base, "dummy", "sample_generator.py"),
        os.path.join(base, "dummy", "order_generator.py"),
        os.path.join(base, "dummy", "production_generator.py"),
    ]

    for filepath in generator_files:
        rel = os.path.relpath(filepath, base)
        with open(filepath, encoding="utf-8") as f:
            tree = ast.parse(f.read())

        # print/input 금지
        forbidden = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = ""
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name in ("print", "input"):
                    forbidden.append(name)

        # sqlite3 직접 import 금지
        sqlite_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "sqlite3" in alias.name:
                        sqlite_imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and "sqlite3" in node.module:
                    sqlite_imports.append(node.module)

        check(f"D-9 {rel} -print/input 없음", len(forbidden) == 0)
        check(f"D-9 {rel} -sqlite3 직접 import 없음", len(sqlite_imports) == 0)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("=" * 52)
    print("더미 데이터 생성 도구 검증 - 구조, 생성기, DB, AST")
    print("=" * 52)

    test_d1_package_structure()
    test_d2_db_schema()
    test_d3_sample_generator()
    test_d4_order_generator()
    test_d5_production_generator()
    test_d6_db_insert()
    test_d7_db_reset()
    test_d8_empty_producing()
    test_d9_ast_boundary()

    print("\n" + "-" * 52)
    print(f"결과: {_pass}개 통과 / {_fail}개 실패")
    if _fail == 0:
        print("[OK] 더미 데이터 도구 검증 완료 - 모든 항목 통과")
    else:
        print("[NG] 일부 항목 실패 - 위 [FAIL] 항목을 확인하세요")
        sys.exit(1)


if __name__ == "__main__":
    main()
