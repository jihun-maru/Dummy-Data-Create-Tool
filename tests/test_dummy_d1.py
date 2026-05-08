"""
Phase D-1 검증 — dummy/db/ 패키지 구조·연결·스키마·삽입기
"""
import ast
import os
import sys
import tempfile

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
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


# ──────────────────────────────────────────────
# D1-1: 패키지 구조 검증
# ──────────────────────────────────────────────
def test_d1_1_package_structure():
    print("\n[D1-1] 패키지 구조 검증")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    targets = [
        ("dummy/",                 os.path.isdir),
        ("dummy/__init__.py",      os.path.isfile),
        ("dummy/db/",              os.path.isdir),
        ("dummy/db/__init__.py",   os.path.isfile),
        ("dummy/db/connection.py", os.path.isfile),
        ("dummy/db/schema.py",     os.path.isfile),
        ("dummy/db/inserter.py",   os.path.isfile),
    ]
    for rel, fn in targets:
        check(f"D1-1 {rel} 존재", fn(os.path.join(base, rel.rstrip("/"))))


# ──────────────────────────────────────────────
# D1-2: connection.py 검증
# ──────────────────────────────────────────────
def test_d1_2_connection():
    print("\n[D1-2] connection.py — get_connection 검증")
    tmp = make_temp_db()
    try:
        from dummy.db.connection import get_connection, DEFAULT_DB_PATH
        check("D1-2-1 get_connection import 성공", True)
        check("D1-2-2 DEFAULT_DB_PATH 상수 존재", isinstance(DEFAULT_DB_PATH, str))

        with get_connection(tmp) as conn:
            check("D1-2-3 컨텍스트 매니저 정상 동작 (conn not None)", conn is not None)
            # 연결 객체로 간단한 쿼리 실행 가능한지 확인
            conn.execute("SELECT 1")
            check("D1-2-4 연결 객체로 쿼리 실행 가능", True)
    except ImportError as e:
        check(f"D1-2-1 get_connection import 성공 ({e})", False)
    except Exception as e:
        check(f"D1-2-3 컨텍스트 매니저 동작 ({e})", False)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ──────────────────────────────────────────────
# D1-3: schema.py 검증
# ──────────────────────────────────────────────
def test_d1_3_schema():
    print("\n[D1-3] schema.py — create_tables 검증")
    tmp = make_temp_db()
    try:
        import sqlite3
        from dummy.db.connection import get_connection
        from dummy.db.schema import create_tables
        check("D1-3-1 create_tables import 성공", True)

        with get_connection(tmp) as conn:
            create_tables(conn)

        with sqlite3.connect(tmp) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = {row[0] for row in cursor.fetchall()}

        check("D1-3-2 samples 테이블 생성", "samples" in tables)
        check("D1-3-3 orders 테이블 생성", "orders" in tables)
        check("D1-3-4 production_jobs 테이블 생성", "production_jobs" in tables)

        # 컬럼 구조 확인
        with sqlite3.connect(tmp) as conn:
            cols_s = {row[1] for row in conn.execute("PRAGMA table_info(samples)")}
            cols_o = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
            cols_j = {row[1] for row in conn.execute("PRAGMA table_info(production_jobs)")}

        check("D1-3-5 samples 컬럼 구조",
              {"sample_id", "name", "avg_production_time", "yield_rate", "stock"}.issubset(cols_s))
        check("D1-3-6 orders 컬럼 구조",
              {"order_id", "sample_id", "customer", "quantity", "status"}.issubset(cols_o))
        check("D1-3-7 production_jobs 컬럼 구조",
              {"order_id", "sample_id", "actual_qty", "total_time", "produced_qty", "is_current"}.issubset(cols_j))

        # 멱등성: 이미 테이블이 있어도 오류 없이 실행 (CREATE TABLE IF NOT EXISTS)
        try:
            with get_connection(tmp) as conn:
                create_tables(conn)
            check("D1-3-8 create_tables 멱등성 (중복 호출 오류 없음)", True)
        except Exception as e:
            check(f"D1-3-8 create_tables 멱등성 ({e})", False)

    except ImportError as e:
        check(f"D1-3-1 create_tables import 성공 ({e})", False)
    except Exception as e:
        check(f"D1-3 스키마 생성 ({e})", False)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ──────────────────────────────────────────────
# D1-4: DummyInserter 검증
# ──────────────────────────────────────────────
def test_d1_4_inserter():
    print("\n[D1-4] inserter.py — DummyInserter 검증")
    tmp = make_temp_db()
    try:
        import sqlite3
        from dummy.db.inserter import DummyInserter
        check("D1-4-1 DummyInserter import 성공", True)

        inserter = DummyInserter(db_path=tmp)
        check("D1-4-2 DummyInserter 인스턴스화 성공", inserter is not None)
        check("D1-4-3 reset() 메서드 존재", hasattr(inserter, "reset"))
        check("D1-4-4 insert_samples() 메서드 존재", hasattr(inserter, "insert_samples"))
        check("D1-4-5 insert_orders() 메서드 존재", hasattr(inserter, "insert_orders"))
        check("D1-4-6 insert_production_jobs() 메서드 존재", hasattr(inserter, "insert_production_jobs"))

        # reset() 동작 (테이블이 비어 있어도 오류 없어야 함)
        inserter.reset()
        check("D1-4-7 reset() 오류 없이 실행", True)

        # insert_samples
        from model.sample import Sample
        s = Sample("S001", "GaN 웨이퍼", 2.5, 0.9)
        s.stock = 100
        n_s = inserter.insert_samples([s])
        check("D1-4-8 insert_samples() 반환값 = 삽입 건수(1)", n_s == 1)

        # insert_orders
        from model.order import Order
        from model.order_status import OrderStatus
        o = Order("O001", "S001", "A연구소", 10)
        o.status = OrderStatus.RESERVED
        n_o = inserter.insert_orders([o])
        check("D1-4-9 insert_orders() 반환값 = 삽입 건수(1)", n_o == 1)

        # insert_production_jobs
        job = {
            "order_id":    "O001",
            "sample_id":   "S001",
            "actual_qty":  12,
            "total_time":  30.0,
            "produced_qty": 0,
            "is_current":  1,
        }
        n_j = inserter.insert_production_jobs([job])
        check("D1-4-10 insert_production_jobs() 반환값 = 삽입 건수(1)", n_j == 1)

        # SELECT로 실제 DB 확인
        with sqlite3.connect(tmp) as conn:
            cnt_s = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
            cnt_o = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            cnt_j = conn.execute("SELECT COUNT(*) FROM production_jobs").fetchone()[0]

        check("D1-4-11 samples DB 행 수 확인", cnt_s == 1)
        check("D1-4-12 orders DB 행 수 확인", cnt_o == 1)
        check("D1-4-13 production_jobs DB 행 수 확인", cnt_j == 1)

        # reset() 후 0건 확인
        inserter.reset()
        with sqlite3.connect(tmp) as conn:
            cnt_s = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
            cnt_o = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        check("D1-4-14 reset() 후 samples 0건", cnt_s == 0)
        check("D1-4-15 reset() 후 orders 0건", cnt_o == 0)

        # INSERT OR REPLACE (upsert) 확인
        inserter.insert_samples([s])
        inserter.insert_samples([s])  # 동일 sample_id 두 번 삽입
        with sqlite3.connect(tmp) as conn:
            cnt_s = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
        check("D1-4-16 INSERT OR REPLACE — 중복 삽입 시 1건 유지", cnt_s == 1)

    except ImportError as e:
        check(f"D1-4-1 DummyInserter import 성공 ({e})", False)
    except Exception as e:
        check(f"D1-4 DummyInserter 오류 ({e})", False)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ──────────────────────────────────────────────
# D1-5: 역할 경계 AST 검사
# ──────────────────────────────────────────────
def test_d1_5_ast():
    print("\n[D1-5] 역할 경계 (AST) — dummy/db/*.py")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_files = [
        os.path.join(base, "dummy", "db", "connection.py"),
        os.path.join(base, "dummy", "db", "schema.py"),
        os.path.join(base, "dummy", "db", "inserter.py"),
    ]
    for filepath in db_files:
        rel = os.path.relpath(filepath, base)
        try:
            with open(filepath, encoding="utf-8") as f:
                tree = ast.parse(f.read())

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

            check(f"D1-5 {rel} — print/input 없음", len(forbidden) == 0)
        except FileNotFoundError:
            check(f"D1-5 {rel} — 파일 존재", False)
        except SyntaxError as e:
            check(f"D1-5 {rel} — 구문 오류 없음 ({e})", False)


# ──────────────────────────────────────────────
# main
# ──────────────────────────────────────────────
def main():
    print("=" * 54)
    print("Phase D-1 검증 — dummy/db/ 패키지")
    print("=" * 54)

    test_d1_1_package_structure()
    test_d1_2_connection()
    test_d1_3_schema()
    test_d1_4_inserter()
    test_d1_5_ast()

    print("\n" + "-" * 54)
    print(f"결과: {_pass}개 통과 / {_fail}개 실패")
    if _fail == 0:
        print("✓ Phase D-1 검증 완료 — 모든 항목 통과")
    else:
        print("✗ 일부 항목 실패 — 위 [FAIL] 항목을 확인하세요")
        sys.exit(1)


if __name__ == "__main__":
    main()
