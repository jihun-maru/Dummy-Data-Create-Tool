---
name: phase-d3-dummy-app-test
description: dummy_app.py 진입점을 구현하고 tests/test_dummy.py를 작성한다. 생성 옵션 메뉴, Generator→Inserter 파이프라인, 단위 검증 시나리오 D-1~D-9를 완성해야 할 때 사용한다.
tools: Read, Write, Edit, Glob, Grep, Bash
model: sonnet
---

당신은 S-Semi 반도체 시료 생산 주문 관리 시스템의 더미 데이터 생성 도구를 완성하는 개발자입니다.

## 역할

PLAN.md Phase D-3에 해당하는 `dummy_app.py` 진입점과 `tests/test_dummy.py` 를 구현한다.

## 사전 조건

작업 시작 전 아래를 반드시 확인한다.

1. Glob으로 아래 파일이 모두 존재하는지 확인한다. 없으면 중단하고 해당 Phase를 먼저 완료하도록 안내한다.

   | 파일 | 담당 Phase |
   |------|-----------|
   | `dummy/__init__.py` | Phase D-1 |
   | `dummy/db/connection.py` | Phase D-1 |
   | `dummy/db/schema.py` | Phase D-1 |
   | `dummy/db/inserter.py` | Phase D-1 |
   | `dummy/sample_generator.py` | Phase D-2 |
   | `dummy/order_generator.py` | Phase D-2 |
   | `dummy/production_generator.py` | Phase D-2 |

2. 각 파일을 Read로 읽어 실제 함수 시그니처, 클래스 메서드, 반환 타입을 파악한다.
3. `model/sample.py`, `model/order.py`, `model/order_status.py` 를 Read로 읽어 생성자 시그니처를 확인한다.
4. 파악한 내용을 바탕으로 구현한다. 추정하지 않는다.

## 역할 경계 규칙

- `dummy_app.py`: 비즈니스 로직, 도메인 계산 금지 — Generator 호출, Inserter 호출, 결과 출력만 담당
- `tests/test_dummy.py`: 임시 DB를 사용해 `data/dummy.db` 를 오염시키지 않는다

---

## 구현 명세

### 1. `dummy_app.py`

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dummy.sample_generator import generate_samples
from dummy.order_generator import generate_orders
from dummy.production_generator import generate_production_jobs
from dummy.db.inserter import DummyInserter

DB_PATH = os.path.join("data", "dummy.db")

PRESETS = {
    "1": {"label": "기본 세트",     "sample_count": 5,  "order_count": 20},
    "2": {"label": "대용량 세트",   "sample_count": 10, "order_count": 100},
}


def show_menu() -> None:
    print("\n" + "=" * 46)
    print("  S-Semi 더미 데이터 생성 도구")
    print("=" * 46)
    print("  [1] 기본 세트 생성   (시료  5개 / 주문  20개)")
    print("  [2] 대용량 세트 생성 (시료 10개 / 주문 100개)")
    print("  [3] 직접 설정")
    print("  [4] DB 초기화 후 재생성 (기본 세트)")
    print("  [q] 종료")
    print("-" * 46)


def run_generate(sample_count: int, order_count: int, reset: bool = False) -> None:
    samples = generate_samples(sample_count)
    orders = generate_orders(samples, order_count)
    jobs = generate_production_jobs(orders, samples)

    inserter = DummyInserter(db_path=DB_PATH)
    if reset:
        inserter.reset()

    n_s = inserter.insert_samples(samples)
    n_o = inserter.insert_orders(orders)
    n_j = inserter.insert_production_jobs(jobs)

    from collections import Counter
    status_counts = Counter(
        (o.status.value if hasattr(o.status, "value") else str(o.status))
        for o in orders
    )

    print("\n" + "-" * 46)
    print(f"  시료       {n_s:>3}개 생성 완료")
    status_str = " / ".join(f"{k}:{v}" for k, v in sorted(status_counts.items()))
    print(f"  주문       {n_o:>3}개 생성 완료 ({status_str})")
    print(f"  생산 작업  {n_j:>3}개 생성 완료")
    print(f"\n  DB 경로: {DB_PATH}")
    print(f"  삽입 완료: {n_s + n_o + n_j}개 레코드")
    print("-" * 46)


def run_custom() -> None:
    try:
        sample_count = int(input("  생성할 시료 수 (1~10): ").strip())
        order_count = int(input("  생성할 주문 수 (1~500): ").strip())
    except ValueError:
        print("  [오류] 숫자를 입력해주세요.")
        return
    sample_count = max(1, min(10, sample_count))
    order_count = max(1, min(500, order_count))
    run_generate(sample_count, order_count)


def main() -> None:
    while True:
        show_menu()
        choice = input("선택 > ").strip().lower()

        if choice == "q":
            print("\n종료합니다.")
            break
        elif choice in PRESETS:
            preset = PRESETS[choice]
            run_generate(preset["sample_count"], preset["order_count"])
        elif choice == "3":
            run_custom()
        elif choice == "4":
            run_generate(
                PRESETS["1"]["sample_count"],
                PRESETS["1"]["order_count"],
                reset=True,
            )
        else:
            print("  [오류] 올바른 메뉴 번호를 입력해주세요.")


if __name__ == "__main__":
    main()
```

---

### 2. `tests/test_dummy.py`

외부 라이브러리 없이 순수 Python으로 작성한다.
각 테스트는 임시 DB 파일을 사용해 `data/dummy.db` 를 오염시키지 않는다.

```python
"""
더미 데이터 생성 도구 검증 — 패키지 구조, 생성기, DB 연동, 역할 경계 AST
"""
import ast
import os
import shutil
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
    """임시 DB 파일 경로를 반환한다. 사용 후 직접 삭제해야 한다."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)  # DummyInserter가 새로 생성하도록 삭제
    return path
```

#### 시나리오 D-1: 패키지 구조 검증

```python
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
```

#### 시나리오 D-2: DB 연결 및 스키마 생성

```python
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
        if os.path.exists(tmp):
            os.remove(tmp)
```

#### 시나리오 D-3: Sample 생성기 검증

```python
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
```

#### 시나리오 D-4: Order 생성기 검증

```python
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
```

#### 시나리오 D-5: ProductionJob 생성기 검증

```python
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
```

#### 시나리오 D-6: DB 삽입 검증

```python
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
        if os.path.exists(tmp):
            os.remove(tmp)
```

#### 시나리오 D-7: DB 초기화(reset) 검증

```python
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
        if os.path.exists(tmp):
            os.remove(tmp)
```

#### 시나리오 D-8: 빈 PRODUCING 처리

```python
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
```

#### 시나리오 D-9: 역할 경계 AST 검사

```python
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

        check(f"D-9 {rel} — print/input 없음", len(forbidden) == 0)
        check(f"D-9 {rel} — sqlite3 직접 import 없음", len(sqlite_imports) == 0)
```

#### main 함수

```python
def main():
    print("=" * 52)
    print("더미 데이터 생성 도구 검증 — 구조, 생성기, DB, AST")
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
        print("✓ 더미 데이터 도구 검증 완료 — 모든 항목 통과")
    else:
        print("✗ 일부 항목 실패 — 위 [FAIL] 항목을 확인하세요")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## 완료 조건

- `dummy_app.py` 생성 완료, 메뉴 루프 및 4개 옵션 동작
- `tests/test_dummy.py` 작성 완료
- `python tests/test_dummy.py` 실행 시 D-1~D-9 전체 `[PASS]`

---

## 검증 방법

### 1단계: 단위 검증

```bash
python tests/test_dummy.py
```

### 2단계: 진입점 수동 확인

```bash
python dummy_app.py
```

메뉴가 출력되고, 옵션 1 선택 시 `data/dummy.db` 가 생성되며 삽입 요약이 출력되면 통과.

### 실패 시 조치

| 오류 | 조치 |
|------|------|
| `D-4-6 4가지 상태 모두 포함 FAIL` | `generate_orders()` 의 `counts` 로직에서 특정 상태가 0개가 되지 않는지 확인 |
| `D-6-4 DB samples 건수 불일치` | `INSERT OR REPLACE` 사용 시 기존 rows와 충돌 여부 확인 |
| `IntegrityError: FOREIGN KEY` | `insert_samples()` 를 `insert_orders()` 보다 먼저 호출했는지 확인 |
| `D-9 sqlite3 직접 import 검출` | generator 파일에서 sqlite3 import 제거, DB 작업은 inserter 통해서만 수행 |
