# CLAUDE.md — S-Semi 반도체 시료 생산 주문 관리 시스템

## 프로젝트 개요

가상의 반도체 회사 **S-Semi**의 시료(Sample) 생산 주문 관리 시스템.
콘솔 기반 Python 애플리케이션으로, 담당자가 직접 명령을 입력해 시료 등록·주문 처리·생산라인 운영을 수행한다.

**데이터 모니터링 도구(Data Monitoring Tool)** 는 현재 저장된 JSON 데이터를 읽어
관리자가 콘솔에서 시스템 전체 현황을 실시간으로 조회할 수 있는 독립 실행형 뷰어다.
메인 관리 시스템(`main.py`)과 별도 프로세스로 동작하며 데이터를 수정하지 않는다.

**더미 데이터 생성 도구(Dummy Data Create Tool)** 는 테스트를 위한 S-Semi 도메인 더미 데이터를
생성하고 연결된 SQLite DB에 삽입하는 독립 실행형 도구다.
기존 `model/` 도메인 객체를 재사용하며, `main.py` / `monitor_app.py`와 별도 프로세스로 동작한다.

**POC 이력:**
- **1차 POC (완료):** MVC 패키지 구조와 역할 분리 완성 — 인메모리 스켈레톤
- **2차 POC (완료):** 데이터 영속성 처리 — JSON 파일 기반 Repository 패턴으로 CRUD 및 재시작 후 데이터 유지 구현
- **3차 POC (완료):** 데이터 모니터링 도구 — JSON 파일에서 데이터를 읽어 콘솔 대시보드로 실시간 제공
- **4차 POC (현재):** 더미 데이터 생성 도구 — S-Semi 도메인 테스트 데이터 생성 + SQLite DB 삽입

## 기술 스택

- **언어:** Python 3.x
- **아키텍처:** MVC + Repository (Model / View / Controller / Persistence) + Monitor + Dummy
- **인터페이스:** 콘솔(CLI) 기반 — GUI 없음
- **외부 의존성:** 없음 (표준 라이브러리만 사용)
- **영속성 방식:**
  - 관리 시스템: JSON 파일 (`json`, `pathlib`) — `data/` 디렉토리
  - 더미 데이터 도구: SQLite (`sqlite3`) — `data/dummy.db`

## 패키지 구조 및 역할 분리 원칙

```
Dummy-Data-Create-Tool/
├── model/               # 데이터 구조 및 비즈니스 로직
│   ├── __init__.py
│   ├── sample.py
│   ├── order.py
│   ├── order_status.py
│   └── production_line.py
├── controller/          # 유스케이스 처리 — Model↔View 연결
│   ├── __init__.py
│   ├── sample_controller.py
│   ├── order_controller.py
│   ├── monitoring_controller.py
│   ├── shipping_controller.py
│   └── production_controller.py
├── view/                # 출력 및 입력 전담 — 비즈니스 로직 없음
│   ├── __init__.py
│   ├── main_menu_view.py
│   ├── sample_view.py
│   ├── order_view.py
│   ├── monitoring_view.py
│   ├── shipping_view.py
│   └── production_view.py
├── persistence/         # 영속성 레이어 — JSON 파일 I/O 전담
│   ├── __init__.py
│   ├── base_repository.py
│   ├── sample_repository.py
│   ├── order_repository.py
│   └── production_repository.py
├── monitor/             # 데이터 모니터링 도구 — 읽기 전용 대시보드
│   ├── __init__.py
│   ├── monitor_controller.py
│   └── monitor_view.py
├── dummy/               # 더미 데이터 생성 도구 (4차 POC 신규)
│   ├── __init__.py
│   ├── sample_generator.py      # Sample 더미 데이터 생성
│   ├── order_generator.py       # Order 더미 데이터 생성
│   ├── production_generator.py  # ProductionJob 더미 데이터 생성
│   └── db/                      # SQLite DB 연결·스키마·삽입 서브패키지
│       ├── __init__.py
│       ├── connection.py        # SQLite 연결 컨텍스트 매니저
│       ├── schema.py            # 테이블 DDL 정의 + 생성
│       └── inserter.py          # 생성 데이터 → DB 삽입
├── data/                # 런타임 데이터 파일 (git 제외)
│   ├── samples.json
│   ├── orders.json
│   ├── production.json
│   └── dummy.db         # 더미 데이터 SQLite DB (4차 POC)
├── tests/
│   ├── test_phase1.py
│   ├── test_phase2.py
│   ├── test_phase3.py
│   ├── test_phase4.py
│   ├── test_phase7.py
│   ├── test_phase8.py
│   ├── test_phase9.py
│   ├── test_integration.py
│   ├── test_persistence.py
│   ├── test_final.py
│   ├── test_monitor.py
│   ├── test_phase12.py
│   ├── test_monitor_final.py
│   ├── test_dummy.py            # Phase D-3: 더미 도구 단위 검증 (4차 POC 신규)
│   └── test_dummy_final.py      # Phase D-4: 더미 도구 최종 통합 검증 (4차 POC 신규)
├── main.py              # 메인 관리 시스템 진입점
├── monitor_app.py       # 데이터 모니터링 도구 진입점
├── dummy_app.py         # 더미 데이터 생성 도구 진입점 (4차 POC 신규)
├── CLAUDE.md
└── PLAN.md
```

### 역할 경계 규칙

| 레이어 | 허용 | 금지 |
|--------|------|------|
| **Model** | 데이터 속성, 상태 전이 메서드, 도메인 계산 | `print()`, `input()`, 파일 I/O |
| **Controller** | Model 조작, Repository 호출, View 호출 순서 결정, 입력값 검증 | 직접 `print()`, 직접 파일 I/O |
| **View** | `print()` 출력, `input()` 입력 수집, 화면 포맷 | 비즈니스 로직, Model 상태 직접 변경, 파일 I/O |
| **Persistence** | JSON 파일 읽기/쓰기, Model 객체 직렬화/역직렬화 | `print()`, `input()`, 비즈니스 로직 |
| **Monitor/Controller** | Repository 읽기, 화면용 데이터 집계 | `print()`, `input()`, 데이터 변경 |
| **Monitor/View** | `print()` 출력, `input()` 입력, 화면 클리어(`os.system`) | Repository 직접 접근, 비즈니스 로직 |
| **Dummy/Generator** | 도메인 객체 생성, 랜덤 데이터 조합 | `print()`, `input()`, DB/파일 I/O |
| **Dummy/DB** | SQLite 연결, DDL 실행, 데이터 삽입 | `print()`, `input()`, 비즈니스 로직, 도메인 계산 |
| **dummy_app.py** | Generator 호출, Inserter 호출, 진행 현황 출력 | 비즈니스 로직, 도메인 계산 |

### Repository 패턴 원칙

- Controller는 인메모리 `dict`/`list` 대신 Repository 인스턴스를 주입받는다.
- Repository는 Model 객체를 받아 JSON으로 직렬화하고, JSON을 읽어 Model 객체로 복원한다.
- `save()` 계열 메서드는 매 변경 시 파일에 즉시 반영한다.
- 파일이 없는 경우 빈 상태로 초기화한다 (최초 실행 대응).
- **모니터링 도구는 Repository를 읽기 전용으로만 사용한다.**

## 도메인 개념

### 시료 (Sample)

| 속성 | 타입 | 설명 |
|------|------|------|
| `sample_id` | str | 고유 식별자 |
| `name` | str | 시료 이름 |
| `avg_production_time` | float | 평균 생산시간 (단위: 시간) |
| `yield_rate` | float | 수율 (0 < yield_rate ≤ 1) |
| `stock` | int | 현재 재고 수량 |

### 주문 (Order)

| 속성 | 타입 | 설명 |
|------|------|------|
| `order_id` | str | 고유 식별자 |
| `sample_id` | str | 대상 시료 ID |
| `customer` | str | 고객명 |
| `quantity` | int | 주문 수량 |
| `status` | OrderStatus | 주문 상태 |

### 주문 상태 (OrderStatus)

```
RESERVED   → 주문 접수
REJECTED   → 주문 거절 (정상 흐름 외, 모니터링 제외)
PRODUCING  → 승인 완료 + 재고 부족으로 생산 중
CONFIRMED  → 승인 완료 + 출고 대기 중
RELEASE    → 출고 완료
```

### 생산 계산식

```
실생산량 = ceil(부족분 / (수율 * 0.9))
총생산시간 = 평균생산시간 × 실생산량
```

### 재고 상태 표기 (모니터링)

| 표기 | 조건 |
|------|------|
| 여유 | 재고 ≥ CONFIRMED + PRODUCING 주문 수량 합계 |
| 부족 | 재고 < 주문 수량 합계, 단 재고 > 0 |
| 고갈 | 재고 = 0 |

## 기능 목록

### 메인 관리 시스템 (`main.py`)

1. **메인 메뉴** — 기능 선택 화면 + 전체 시료 요약 정보
2. **시료관리** — 시료 등록 / 목록 조회(재고 포함) / 이름 검색
3. **주문 접수·승인·거절** — RESERVED 목록 확인, 개별 승인/거절
4. **모니터링** — 상태별 주문 수(REJECTED 제외), 시료별 재고 상태
5. **출고처리** — CONFIRMED 주문 선택 후 RELEASE 전환
6. **생산라인** — 현재 생산 현황 + 대기 큐(FIFO) 조회

### 데이터 모니터링 도구 (`monitor_app.py`)

7. **대시보드 화면** — 시스템 전체 현황을 단일 화면에 표시
   - 헤더: 툴 이름, 마지막 갱신 시각
   - 시료 재고 현황: ID / 이름 / 재고 수량 / 상태(여유·부족·고갈)
   - 주문 현황: 상태별 건수 (RESERVED / PRODUCING / CONFIRMED / RELEASE)
   - 생산라인 현황: 현재 작업 정보 + 대기열 목록
8. **실시간 갱신** — 자동 주기 갱신(기본 5초) + 수동 갱신(키 입력)
9. **종료** — `q` 입력 또는 Ctrl+C로 종료

### 더미 데이터 생성 도구 (`dummy_app.py`) — 4차 POC 신규

10. **생성 설정** — 생성할 데이터 종류 및 수량 선택 (시료 수 / 주문 수 / 상태 비율)
11. **DB 연결 및 스키마 초기화** — SQLite DB 파일 생성, 테이블 DDL 자동 실행
12. **더미 데이터 생성** — S-Semi 도메인 기반 현실적인 테스트 데이터 생성
    - 시료: 반도체 소재 기반 이름, 현실적인 수율·생산시간·재고
    - 주문: 다양한 고객명, 상태별 분포, 수량 범위
    - 생산 작업: PRODUCING 주문에 연동된 생산 작업 데이터
13. **DB 삽입** — 생성된 데이터를 SQLite DB에 삽입 (upsert 또는 초기화 후 삽입)
14. **삽입 결과 요약** — 삽입 완료된 레코드 수 및 DB 경로 출력

## 더미 데이터 생성 도구 — 화면 구성

```
==============================================
  S-Semi 더미 데이터 생성 도구
==============================================

생성 옵션을 선택하세요:
  [1] 기본 세트 생성 (시료 5개 / 주문 20개)
  [2] 대용량 세트 생성 (시료 10개 / 주문 100개)
  [3] 직접 설정
  [4] DB 초기화 후 재생성
  [q] 종료

선택 > 1

----------------------------------------------
  데이터 생성 중...
  시료      5개 생성 완료
  주문     20개 생성 완료 (RESERVED:4 / PRODUCING:4 / CONFIRMED:6 / RELEASE:6)
  생산 작업  4개 생성 완료

  DB 삽입 중...
  DB 경로  : data/dummy.db
  삽입 완료: 29개 레코드
----------------------------------------------
```

## SQLite DB 스키마 (더미 데이터 도구)

```sql
CREATE TABLE IF NOT EXISTS samples (
    sample_id   TEXT PRIMARY KEY,
    name        TEXT    NOT NULL,
    avg_production_time REAL NOT NULL,
    yield_rate  REAL    NOT NULL,
    stock       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id    TEXT PRIMARY KEY,
    sample_id   TEXT NOT NULL,
    customer    TEXT NOT NULL,
    quantity    INTEGER NOT NULL,
    status      TEXT NOT NULL,
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id)
);

CREATE TABLE IF NOT EXISTS production_jobs (
    order_id    TEXT PRIMARY KEY,
    sample_id   TEXT NOT NULL,
    actual_qty  INTEGER NOT NULL,
    total_time  REAL    NOT NULL,
    produced_qty INTEGER NOT NULL DEFAULT 0,
    is_current  INTEGER NOT NULL DEFAULT 0
);
```

## JSON 직렬화 규칙 (관리 시스템)

### samples.json 스키마
```json
[
  {
    "sample_id": "S001",
    "name": "GaN 웨이퍼",
    "avg_production_time": 2.5,
    "yield_rate": 0.9,
    "stock": 100
  }
]
```

### orders.json 스키마
```json
[
  {
    "order_id": "O001",
    "sample_id": "S001",
    "customer": "A연구소",
    "quantity": 10,
    "status": "RESERVED"
  }
]
```

### production.json 스키마
```json
{
  "current_job": {
    "order_id": "O001",
    "sample_id": "S001",
    "actual_qty": 12,
    "total_time": 30.0,
    "produced_qty": 0
  },
  "queue": []
}
```

## 코딩 컨벤션

- Python PEP 8 준수
- 파일명·변수명: `snake_case`
- 클래스명: `PascalCase`
- 상수: `UPPER_SNAKE_CASE`
- 각 패키지에 `__init__.py` 필수
- 타입 힌트 사용 권장
- 주석은 WHY가 비자명한 경우에만 작성

## 테스트 전략

외부 테스트 프레임워크 없이 순수 Python으로 작성된 검증 스크립트를 사용한다.
모든 스크립트는 프로젝트 루트에서 실행하며, `[PASS]` / `[FAIL]` 형태로 결과를 출력한다.

### 테스트 파일 구조

```
tests/
├── test_phase1.py          # Phase 1: 패키지 뼈대 구조 검증
├── test_phase2.py          # Phase 2: Model 레이어 단위 검증
├── test_phase3.py          # Phase 3: Controller 레이어 단위 검증
├── test_phase4.py          # Phase 4: View 레이어 구조 검증 (AST 기반)
├── test_phase7.py          # Phase 7: BaseRepository 구조·동작 검증
├── test_phase8.py          # Phase 8: 구체 Repository 3종 CRUD·직렬화 검증
├── test_phase9.py          # Phase 9: Controller Repository 연동, 파일 반영, 회귀 검증
├── test_integration.py     # Phase 5/6: 전체 E2E 시나리오 검증
├── test_persistence.py     # Phase 10: 영속성 CRUD 및 재시작 시나리오 검증
├── test_final.py           # Phase 11: 전체 Phase 순차 실행 + 영속성 E2E 최종 검증
├── test_phase12.py         # Phase 12: monitor/ 패키지 구조·import·역할 경계 검증
├── test_monitor.py         # Phase 13: 모니터링 도구 집계·AST 검증 M-1~M-9
├── test_monitor_final.py   # Phase 14: 전체 Phase E2E 최종 통합 검증
├── test_dummy.py           # Phase D-3: 더미 도구 단위 검증 (4차 POC 신규)
└── test_dummy_final.py     # Phase D-4: 더미 도구 최종 통합 검증 (4차 POC 신규)
```

### Phase별 검증 명령

| Phase | 명령 | 주요 검증 |
|-------|------|----------|
| 1 | `python tests/test_phase1.py` | 디렉토리·파일 구조, 패키지 import |
| 2 | `python tests/test_phase2.py` | Model 속성·메서드, 계산식, 역할경계(AST) |
| 3 | `python tests/test_phase3.py` | Controller 비즈니스 로직, ValueError, 역할경계(AST) |
| 4 | `python tests/test_phase4.py` | View 메서드 시그니처, 금지 import(AST) |
| 5+6 | `python tests/test_integration.py` | E2E 6개 시나리오 |
| 7 | `python tests/test_phase7.py` | BaseRepository 추상 클래스, 디렉토리 자동생성, 라운드트립 |
| 8 | `python tests/test_phase8.py` | Repository 3종 CRUD, Enum 직렬화, 재시작 시뮬레이션 |
| 9 | `python tests/test_phase9.py` | Controller 인스턴스화, 파일 반영, 회귀 시나리오 3종 |
| 10 | `python tests/test_persistence.py` | 영속성 CRUD 시나리오 P-1~P-6 |
| 11 | `python tests/test_final.py` | Phase 1~10 전체 + 재시작 E2E |
| 12 | `python tests/test_phase12.py` | monitor/ 패키지 구조·import·빈 데이터·역할 경계(AST) |
| 13 | `python tests/test_monitor.py` | 집계 로직 M-1~M-9, 역할 경계(AST) |
| 14 | `python tests/test_monitor_final.py` | 전체 Phase E2E 최종 통합 검증 |
| D-3 | `python tests/test_dummy.py` | 더미 도구 단위 검증 D-1~D-9 |
| D-4 | `python tests/test_dummy_final.py` | 더미 도구 최종 통합 검증 |

### AST 정적 검사 항목

| 파일 대상 | 금지 항목 |
|-----------|----------|
| `model/*.py` | `print()`, `input()` 호출, 파일 I/O |
| `controller/*.py` | `print()`, `input()` 호출, 직접 파일 I/O |
| `view/*.py` | `controller` 모듈 import, `math` 모듈 import, `open()` 등 외부 IO |
| `persistence/*.py` | `print()`, `input()`, 비즈니스 로직 (상태 전이 등) |
| `monitor/monitor_controller.py` | `print()`, `input()`, 데이터 변경 호출 |
| `monitor/monitor_view.py` | Repository 직접 import, 비즈니스 로직 |
| `dummy/*.py` (generator) | `print()`, `input()`, DB/파일 I/O |
| `dummy/db/*.py` | `print()`, `input()`, 비즈니스 로직, 도메인 계산 |

## 이번 POC 범위 (4차 — 더미 데이터 생성 도구)

- **목표:** S-Semi 도메인 기반 테스트용 더미 데이터를 생성하여 SQLite DB에 삽입
- **범위:**
  - `dummy/` 패키지 신규 구현
    - `sample_generator.py` — 반도체 시료 더미 데이터 생성
    - `order_generator.py` — 주문 더미 데이터 생성 (상태 비율 설정 가능)
    - `production_generator.py` — 생산 작업 더미 데이터 생성
  - `dummy/db/` 서브패키지 신규 구현
    - `connection.py` — SQLite 연결 컨텍스트 매니저
    - `schema.py` — 테이블 DDL 정의 + 자동 생성
    - `inserter.py` — 생성 데이터 → DB 삽입 (초기화·upsert 지원)
  - `dummy_app.py` — 진입점: 생성 옵션 선택 → 생성 → 삽입 → 결과 출력
  - `tests/test_dummy.py` — 단위 검증 (D-1~D-9 시나리오)
  - `tests/test_dummy_final.py` — 최종 통합 검증
- **제외:** 인증, GUI, 동시성, 기존 JSON 파일 직접 수정
