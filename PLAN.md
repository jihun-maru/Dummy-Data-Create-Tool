# PLAN.md — S-Semi 더미 데이터 생성 도구 POC 구현 계획

## 목표

기존 완성된 MVC + Repository + Monitor 인프라를 베이스라인으로 삼아,
S-Semi 도메인 기반 테스트 더미 데이터를 생성하고 SQLite DB에 삽입하는
독립 실행형 도구를 완성한다.

---

## 완료된 베이스라인

### 1차 POC — MVC 스켈레톤 (✅ 완료)

| Phase | 상태 | 내용 |
|-------|------|------|
| Phase 1 | ✅ 완료 | 패키지 뼈대 (model / controller / view / tests / main.py) |
| Phase 2 | ✅ 완료 | Model 레이어 (Sample, Order, OrderStatus, ProductionLine) |
| Phase 3 | ✅ 완료 | Controller 레이어 (5개 Controller, 비즈니스 로직 포함) |
| Phase 4 | ✅ 완료 | View 레이어 (6개 View, 역할 분리 준수) |
| Phase 5 | ✅ 완료 | main.py 진입점 조립 |
| Phase 6 | ✅ 완료 | 전체 E2E 통합 테스트 6개 시나리오 통과 |

### 2차 POC — 데이터 영속성 (✅ 완료)

| Phase | 상태 | 내용 |
|-------|------|------|
| Phase 7  | ✅ 완료 | `persistence/` 패키지 뼈대 + BaseRepository |
| Phase 8  | ✅ 완료 | 구체 Repository 3종 (Sample / Order / Production) CRUD + 직렬화 |
| Phase 9  | ✅ 완료 | Controller → Repository 연동, main.py 의존성 주입 교체 |
| Phase 10 | ✅ 완료 | `tests/test_persistence.py` — 영속성 CRUD 시나리오 P-1~P-6 |
| Phase 11 | ✅ 완료 | `tests/test_final.py` — 전체 Phase 순차 실행 + 재시작 E2E |

### 3차 POC — 데이터 모니터링 도구 (✅ 완료)

| Phase | 상태 | 내용 |
|-------|------|------|
| Phase 12 | ✅ 완료 | `monitor/` 패키지 (MonitorController + MonitorView) + monitor_app.py |
| Phase 13 | ✅ 완료 | `tests/test_monitor.py` — 집계·AST 검증 M-1~M-9 |
| Phase 14 | ✅ 완료 | `tests/test_monitor_final.py` — 전체 Phase E2E 최종 통합 검증 |

---

## 신규 구현 Phase (4차 POC — 더미 데이터 생성 도구)

### Phase D-1. `dummy/db/` 서브패키지 구현

#### 목적

SQLite DB 연결을 관리하고, S-Semi 도메인 테이블 스키마를 정의하며,
생성된 더미 데이터를 DB에 삽입하는 영속성 레이어를 구성한다.

#### 생성 파일

```
dummy/
├── __init__.py
└── db/
    ├── __init__.py
    ├── connection.py       # SQLite 연결 컨텍스트 매니저
    ├── schema.py           # 테이블 DDL + 자동 생성 함수
    └── inserter.py         # 생성 데이터 → DB 삽입 (초기화·upsert 지원)
```

#### `connection.py` 인터페이스

```python
from contextlib import contextmanager
import sqlite3

DB_PATH = "data/dummy.db"

@contextmanager
def get_connection(db_path: str = DB_PATH):
    # data/ 디렉토리 자동 생성
    # yield conn
    # finally conn.close()
```

#### `schema.py` 인터페이스

```python
def create_tables(conn: sqlite3.Connection) -> None:
    # samples, orders, production_jobs 테이블 DDL 실행
    # CREATE TABLE IF NOT EXISTS 사용
```

DDL 정의:
```sql
CREATE TABLE IF NOT EXISTS samples (
    sample_id            TEXT PRIMARY KEY,
    name                 TEXT    NOT NULL,
    avg_production_time  REAL    NOT NULL,
    yield_rate           REAL    NOT NULL,
    stock                INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id   TEXT PRIMARY KEY,
    sample_id  TEXT    NOT NULL,
    customer   TEXT    NOT NULL,
    quantity   INTEGER NOT NULL,
    status     TEXT    NOT NULL,
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id)
);

CREATE TABLE IF NOT EXISTS production_jobs (
    order_id     TEXT PRIMARY KEY,
    sample_id    TEXT    NOT NULL,
    actual_qty   INTEGER NOT NULL,
    total_time   REAL    NOT NULL,
    produced_qty INTEGER NOT NULL DEFAULT 0,
    is_current   INTEGER NOT NULL DEFAULT 0
);
```

#### `inserter.py` 인터페이스

```python
class DummyInserter:
    def __init__(self, db_path: str = DB_PATH): ...

    def reset(self) -> None:
        # 모든 테이블 데이터 삭제 (DROP 아님)

    def insert_samples(self, samples: list[Sample]) -> int:
        # INSERT OR REPLACE, 삽입 건수 반환

    def insert_orders(self, orders: list[Order]) -> int:
        # INSERT OR REPLACE, 삽입 건수 반환

    def insert_production_jobs(self, jobs: list[dict]) -> int:
        # INSERT OR REPLACE, 삽입 건수 반환
```

#### 역할 경계

- `dummy/db/*.py`: `print()`, `input()`, 비즈니스 로직, 도메인 계산 금지

#### 검증

> **사전 제공 검증 스크립트:** `tests/test_dummy_d1.py` 는 Phase D-1 agent 실행 전 이미 존재한다.

```bash
python tests/test_dummy_d1.py
```

| 시나리오 | 검증 내용 |
|----------|----------|
| D1-1 | 패키지 구조 — `dummy/`, `dummy/db/`, 5개 파일 존재 |
| D1-2 | `get_connection()` — 컨텍스트 매니저 동작, `DEFAULT_DB_PATH` 상수 |
| D1-3 | `create_tables()` — 테이블 3개·컬럼 구조·멱등성 |
| D1-4 | `DummyInserter` — 4개 메서드 존재, 실제 삽입·SELECT 검증, reset, upsert |
| D1-5 | AST — `dummy/db/*.py` 에 `print()`/`input()` 없음 |

---

### Phase D-2. `dummy/` 생성기 구현

#### 목적

S-Semi 도메인에 기반한 현실적인 더미 데이터를 생성하는 Generator를 구현한다.
기존 `model/` 도메인 클래스(Sample, Order, OrderStatus)를 그대로 사용한다.

#### 생성 파일

```
dummy/
├── sample_generator.py      # Sample 더미 데이터 생성
├── order_generator.py       # Order 더미 데이터 생성
└── production_generator.py  # ProductionJob 더미 데이터 생성
```

#### `sample_generator.py` 인터페이스

```python
# 사전 정의된 반도체 시료 후보 풀
SAMPLE_POOL = [
    ("GaN 웨이퍼",  2.5, 0.90),
    ("SiC 웨이퍼",  3.0, 0.85),
    ("InP 웨이퍼",  4.0, 0.80),
    ("GaAs 웨이퍼", 2.0, 0.88),
    ("Si 웨이퍼",   1.5, 0.95),
    ("Ge 웨이퍼",   2.8, 0.82),
    ("AlN 웨이퍼",  3.5, 0.78),
    ("ZnO 웨이퍼",  2.2, 0.87),
    ("InGaAs 웨이퍼", 4.5, 0.75),
    ("AlGaN 웨이퍼",  3.8, 0.83),
]

def generate_samples(count: int = 5) -> list[Sample]:
    # SAMPLE_POOL에서 count개 선택 (중복 없음)
    # sample_id: S001, S002, ...
    # stock: 0~200 사이 랜덤
```

#### `order_generator.py` 인터페이스

```python
# 사전 정의된 고객 후보 풀
CUSTOMER_POOL = [
    "A연구소", "B팹리스", "C대학교", "D반도체",
    "E연구원", "F기업", "G랩", "H테크",
]

def generate_orders(
    samples: list[Sample],
    count: int = 20,
    status_ratio: dict[str, float] | None = None,
) -> list[Order]:
    # status_ratio 기본값: RESERVED 0.2 / PRODUCING 0.2 / CONFIRMED 0.3 / RELEASE 0.3
    # order_id: O001, O002, ...
    # quantity: 5~50 사이 랜덤
    # REJECTED는 생성하지 않음 (정상 흐름 외)
```

#### `production_generator.py` 인터페이스

```python
def generate_production_jobs(orders: list[Order], samples: list[Sample]) -> list[dict]:
    # PRODUCING 상태 주문에 대해서만 생산 작업 생성
    # 첫 번째 PRODUCING 주문 → is_current=1, 나머지 → is_current=0
    # actual_qty: ceil(quantity / (yield_rate * 0.9))
    # total_time: avg_production_time * actual_qty
    # produced_qty: 0 ~ actual_qty 사이 랜덤 (현재 작업만)
    # 반환: list[dict] — production_jobs 테이블 스키마와 동일
```

#### 역할 경계

- `dummy/*.py` (generator): `print()`, `input()`, DB/파일 I/O 금지

#### 검증

> **사전 제공 검증 스크립트:** `tests/test_dummy_d2.py` 는 Phase D-2 agent 실행 전 이미 존재한다.

```bash
python tests/test_dummy_d2.py
```

| 시나리오 | 검증 내용 |
|----------|----------|
| D2-1 | 파일 구조 — 생성기 3개 파일 존재 |
| D2-2 | `generate_samples()` — 건수, 속성, 범위, 중복, pool 초과 처리 |
| D2-3 | `generate_orders()` — 건수, REJECTED 미포함, 4가지 상태, status_ratio, 빈 입력 |
| D2-4 | `generate_production_jobs()` — PRODUCING 연동, 계산식, is_current, 빈 처리 |
| D2-5 | AST — `print()`/`input()`/`sqlite3`/`open()` 없음 |

---

### Phase D-3. `dummy_app.py` 진입점 + 테스트 작성

#### 목적

생성기와 삽입기를 조합해 사용자가 옵션을 선택하면 더미 데이터를 생성·삽입하는
진입점을 구현하고, 단위 검증 테스트를 작성한다.

#### `dummy_app.py` 흐름

```python
# 사전 정의 세트
PRESET = {
    "1": {"sample_count": 5,  "order_count": 20,  "label": "기본 세트"},
    "2": {"sample_count": 10, "order_count": 100, "label": "대용량 세트"},
}

# 메인 루프
while True:
    show_menu()
    choice = input("선택 > ").strip()

    if choice == "q":
        break
    elif choice in ("1", "2"):
        run_preset(PRESET[choice])
    elif choice == "3":
        run_custom()
    elif choice == "4":
        run_reset_and_generate()

def run_preset(preset: dict) -> None:
    samples   = generate_samples(preset["sample_count"])
    orders    = generate_orders(samples, preset["order_count"])
    jobs      = generate_production_jobs(orders, samples)

    with get_connection() as conn:
        create_tables(conn)

    inserter = DummyInserter()
    n_s = inserter.insert_samples(samples)
    n_o = inserter.insert_orders(orders)
    n_j = inserter.insert_production_jobs(jobs)

    print_summary(n_s, n_o, n_j, orders)
```

#### 생성 파일: `tests/test_dummy.py`

##### 테스트 시나리오

| 번호 | 시나리오 | 검증 내용 |
|------|----------|----------|
| D-1 | 패키지 구조 검증 | `dummy/` 디렉토리, `dummy/db/` 서브패키지, `dummy_app.py` 존재 확인 |
| D-2 | DB 연결 및 스키마 생성 | `get_connection()`, `create_tables()` — 테이블 3개 정상 생성 |
| D-3 | Sample 생성기 검증 | `generate_samples(5)` — 5개 반환, 속성 타입·범위 검증 |
| D-4 | Order 생성기 검증 | `generate_orders(samples, 20)` — 20개 반환, REJECTED 미포함, 상태 비율 검증 |
| D-5 | ProductionJob 생성기 검증 | PRODUCING 주문에만 Job 생성, is_current 플래그 최대 1개 |
| D-6 | DB 삽입 검증 | `insert_samples/orders/production_jobs` — 삽입 건수 일치, SELECT로 확인 |
| D-7 | 초기화(reset) 검증 | `reset()` 후 모든 테이블 row 수 = 0 |
| D-8 | 빈 PRODUCING 처리 | PRODUCING 주문 없을 때 `generate_production_jobs` → 빈 리스트 반환 |
| D-9 | 역할 경계 (AST) | `dummy/*.py` 에서 `print()` / `input()` / `sqlite3` 직접 호출 미사용 확인 |

##### 테스트 격리

- 각 테스트는 임시 DB 파일(`tempfile.mkstemp(suffix=".db")`)을 사용하고 종료 후 삭제
- `data/dummy.db` 실제 파일을 오염시키지 않는다

---

### Phase D-4. 최종 통합 검증

#### 목적

4차 POC 전체 구현이 완료된 후 단일 명령으로 정합성을 검증한다.

#### 생성 파일: `tests/test_dummy_final.py`

##### 4단계 검증 흐름

| 단계 | 검증 내용 |
|------|----------|
| 단계 1 | `test_dummy.py` subprocess 실행 — D-1~D-9 전체 통과 |
| 단계 2 | E2E 시나리오: 기본 세트(시료 5 / 주문 20) 생성 → DB 삽입 → SELECT 건수 검증 |
| 단계 3 | reset() 후 재삽입 → 중복 없이 동일 건수 유지 (upsert 검증) |
| 단계 4 | 파일 구조 확인 — `dummy/`, `dummy/db/`, `dummy_app.py`, 테스트 파일 존재 |

##### E2E 시나리오 검증 항목

| 항목 | 검증 내용 |
|------|----------|
| 생성 정확성 | 요청 수량과 실제 생성 수량 일치 |
| DB 삽입 정확성 | SELECT COUNT 결과가 생성 수량과 일치 |
| 외래 키 무결성 | orders.sample_id → samples.sample_id 참조 유효 |
| PRODUCING 연동 | PRODUCING 상태 주문 수 = production_jobs 행 수 |
| is_current 플래그 | is_current=1인 행 최대 1개 |

##### 검증 명령

```bash
python tests/test_dummy_final.py
```

또는 단계별 분리 실행:

```bash
python tests/test_dummy.py
python tests/test_dummy_final.py
python dummy_app.py   # 수동 확인
```

##### 기대 최종 출력

```
결과: N개 통과 / 0개 실패
✓ 최종 통합 검증 완료 — 모든 항목 통과
  더미 데이터 생성 도구 POC 구현 완성
```

---

## 의존성 흐름 (전체)

```
main.py (관리 시스템)
  └─► Controller (유스케이스 조율)
        ├─► Model (상태 변경)
        ├─► Repository (영속화) ──► data/*.json
        └─► View (입출력)

monitor_app.py (모니터링 도구, 별도 프로세스)
  └─► MonitorController (읽기 전용 집계)
        └─► Repository (읽기 전용) ──► data/*.json
  └─► MonitorView (대시보드 출력)

dummy_app.py (더미 데이터 도구, 별도 프로세스)
  └─► SampleGenerator / OrderGenerator / ProductionGenerator
        └─► model.Sample / model.Order / model.OrderStatus (재사용)
  └─► DummyInserter
        └─► dummy/db/connection.py + schema.py ──► data/dummy.db
```

---

## 사전 제공 테스트 파일

| 구분 | 파일 | 설명 |
|------|------|------|
| **사전 제공** | `tests/test_dummy_d1.py` | Phase D-1 agent 검증용 (구현 전 존재) |
| **사전 제공** | `tests/test_dummy_d2.py` | Phase D-2 agent 검증용 (구현 전 존재) |
| **agent 생성** | `tests/test_dummy.py` | Phase D-3 agent의 결과물이자 검증 수단 |
| **agent 생성** | `tests/test_dummy_final.py` | Phase D-4 agent의 결과물이자 최종 검증 수단 |

---

## 체크리스트

### Phase D-1 — `dummy/db/` 서브패키지

- [ ] `dummy/__init__.py`
- [ ] `dummy/db/__init__.py`
- [ ] `dummy/db/connection.py` — `get_connection()` 컨텍스트 매니저, `DEFAULT_DB_PATH` 상수
- [ ] `dummy/db/schema.py` — `create_tables()`, DDL 3개 테이블, `CREATE TABLE IF NOT EXISTS`
- [ ] `dummy/db/inserter.py` — `DummyInserter.reset()`, `insert_samples()`, `insert_orders()`, `insert_production_jobs()`
- [ ] `python tests/test_dummy_d1.py` 전체 통과 ← **자동 검증**
  - [ ] D1-1: 패키지 구조 7개 항목 통과
  - [ ] D1-2: connection — 컨텍스트 매니저 동작
  - [ ] D1-3: schema — 테이블 3개·컬럼·멱등성
  - [ ] D1-4: inserter — 삽입·reset·upsert
  - [ ] D1-5: AST — `print()`/`input()` 없음

### Phase D-2 — `dummy/` 생성기

- [ ] `dummy/sample_generator.py` — `generate_samples(count)`
- [ ] `dummy/order_generator.py` — `generate_orders(samples, count, status_ratio)`
- [ ] `dummy/production_generator.py` — `generate_production_jobs(orders, samples)`
- [ ] `python tests/test_dummy_d2.py` 전체 통과 ← **자동 검증**
  - [ ] D2-1: 파일 구조
  - [ ] D2-2: sample_generator — count, 속성, 범위, 중복, pool 초과
  - [ ] D2-3: order_generator — REJECTED 미포함, 4가지 상태, status_ratio, 빈 입력
  - [ ] D2-4: production_generator — PRODUCING 연동, 계산식, is_current, 빈 처리
  - [ ] D2-5: AST — `print()`/`input()`/`sqlite3`/`open()` 없음

### Phase D-3 — 진입점 + 테스트

- [ ] `dummy_app.py` — 메뉴 루프, 기본 세트·대용량 세트·직접 설정·초기화 후 재생성
- [ ] `tests/test_dummy.py` — 시나리오 D-1 ~ D-9 작성 및 통과
- [ ] `python tests/test_dummy.py` 전체 통과 ← **자동 검증**
- [ ] `python dummy_app.py` 수동 확인 통과

### Phase D-4 — 최종 통합 검증

- [ ] `tests/test_dummy_final.py` — 4단계 검증 흐름 작성
- [ ] `python tests/test_dummy_final.py` 전체 통과 ← **자동 검증**
  - [ ] 단계 1: `test_dummy.py` (D-1~D-9) subprocess 통과
  - [ ] 단계 2: E2E 기본 세트 삽입·SELECT·외래 키·is_current 검증 통과
  - [ ] 단계 3: reset + 재삽입 upsert 검증 통과
  - [ ] 단계 4: 전체 파일 구조 확인 통과

### 최종 확인

- [ ] `dummy_app.py` 실행 시 메뉴 정상 출력
- [ ] 기본 세트 생성 → `data/dummy.db` 파일 생성 확인
- [ ] SQLite 클라이언트로 데이터 직접 조회 가능
- [ ] `python tests/test_dummy_final.py` 전체 통과
