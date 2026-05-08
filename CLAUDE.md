# CLAUDE.md — S-Semi 반도체 시료 생산 주문 관리 시스템

## 프로젝트 개요

가상의 반도체 회사 **S-Semi**의 시료(Sample) 생산 주문 관리 시스템.
콘솔 기반 Python 애플리케이션으로, 담당자가 직접 명령을 입력해 시료 등록·주문 처리·생산라인 운영을 수행한다.

**데이터 모니터링 도구(Data Monitoring Tool)** 는 현재 저장된 JSON 데이터를 읽어
관리자가 콘솔에서 시스템 전체 현황을 실시간으로 조회할 수 있는 독립 실행형 뷰어다.
메인 관리 시스템(`main.py`)과 별도 프로세스로 동작하며 데이터를 수정하지 않는다.

**POC 이력:**
- **1차 POC (완료):** MVC 패키지 구조와 역할 분리 완성 — 인메모리 스켈레톤
- **2차 POC (완료):** 데이터 영속성 처리 — JSON 파일 기반 Repository 패턴으로 CRUD 및 재시작 후 데이터 유지 구현
- **3차 POC (현재):** 데이터 모니터링 도구 — JSON 파일에서 데이터를 읽어 콘솔 대시보드로 실시간 제공

## 기술 스택

- **언어:** Python 3.x
- **아키텍처:** MVC + Repository (Model / View / Controller / Persistence) + Monitor
- **인터페이스:** 콘솔(CLI) 기반 — GUI 없음
- **외부 의존성:** 없음 (표준 라이브러리만 사용)
- **영속성 방식:** JSON 파일 (`json`, `pathlib` 모듈) — `data/` 디렉토리에 저장

## 패키지 구조 및 역할 분리 원칙

```
Data-Monitoring-Tool/
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
│   ├── base_repository.py      # 추상 Repository 인터페이스
│   ├── sample_repository.py    # Sample CRUD + JSON 직렬화
│   ├── order_repository.py     # Order CRUD + JSON 직렬화
│   └── production_repository.py # ProductionLine 상태 저장/복원
├── monitor/             # 데이터 모니터링 도구 — 읽기 전용 대시보드 (3차 POC 신규)
│   ├── __init__.py
│   ├── monitor_controller.py   # Repository 읽기 + 데이터 집계
│   └── monitor_view.py         # 대시보드 화면 출력 + 입력 처리
├── data/                # 런타임 데이터 파일 (git 제외)
│   ├── samples.json
│   ├── orders.json
│   └── production.json
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
│   └── test_monitor.py         # Phase 13: 모니터링 도구 검증 (3차 POC 신규)
├── main.py              # 메인 관리 시스템 진입점
├── monitor_app.py       # 데이터 모니터링 도구 진입점 (3차 POC 신규)
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

### 데이터 모니터링 도구 (`monitor_app.py`) — 3차 POC 신규

7. **대시보드 화면** — 시스템 전체 현황을 단일 화면에 표시
   - 헤더: 툴 이름, 마지막 갱신 시각
   - 시료 재고 현황: ID / 이름 / 재고 수량 / 상태(여유·부족·고갈)
   - 주문 현황: 상태별 건수 (RESERVED / PRODUCING / CONFIRMED / RELEASE)
   - 생산라인 현황: 현재 작업 정보 + 대기열 목록
8. **실시간 갱신** — 자동 주기 갱신(기본 5초) + 수동 갱신(키 입력)
9. **종료** — `q` 입력 또는 Ctrl+C로 종료

## 데이터 모니터링 도구 — 화면 구성

```
==============================================
  S-Semi 데이터 모니터링 도구
  갱신: 2026-05-08 14:30:25  | 자동갱신: 5초
==============================================

[ 시료 재고 현황 ]
--------------------------------------------------
 ID     이름           재고    상태
--------------------------------------------------
 S001   GaN 웨이퍼     100     여유
 S002   SiC 웨이퍼     0       고갈
--------------------------------------------------

[ 주문 현황 ]
--------------------------------------------------
 RESERVED    :  2건
 PRODUCING   :  1건
 CONFIRMED   :  3건
 RELEASE     :  5건
--------------------------------------------------

[ 생산라인 현황 ]
--------------------------------------------------
 현재 작업: O003 | S002 | 목표 12개 | 생산 4개 완료
 대기열 (2건):
   [1] O004 | S001 | 12개
   [2] O005 | S002 | 18개
--------------------------------------------------

[r] 수동갱신  [q] 종료  [a] 자동갱신 토글
```

## JSON 직렬화 규칙

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
├── test_phase1.py        # Phase 1: 패키지 뼈대 구조 검증
├── test_phase2.py        # Phase 2: Model 레이어 단위 검증
├── test_phase3.py        # Phase 3: Controller 레이어 단위 검증
├── test_phase4.py        # Phase 4: View 레이어 구조 검증 (AST 기반)
├── test_phase7.py        # Phase 7: BaseRepository 구조·동작 검증
├── test_phase8.py        # Phase 8: 구체 Repository 3종 CRUD·직렬화 검증
├── test_phase9.py        # Phase 9: Controller Repository 연동, 파일 반영, 회귀 검증
├── test_integration.py   # Phase 5/6: 전체 E2E 시나리오 검증
├── test_persistence.py   # Phase 10: 영속성 CRUD 및 재시작 시나리오 검증
├── test_final.py         # Phase 11: 전체 Phase 순차 실행 + 영속성 E2E 최종 검증
├── test_phase12.py       # Phase 12: monitor/ 패키지 구조·import·역할 경계 검증 (사전 제공)
├── test_monitor.py       # Phase 13: 모니터링 도구 집계·AST 검증 M-1~M-9 (Phase 13 생성)
└── test_monitor_final.py # Phase 14: 전체 Phase E2E 최종 통합 검증 (사전 제공)
```

### 테스트 파일 제공 방식

| 구분 | 파일 | 설명 |
|------|------|------|
| **사전 제공** (agent 실행 전 존재) | `test_phase12.py` | Phase 12 agent가 구현 후 실행해 검증 |
| **사전 제공** (agent 실행 전 존재) | `test_monitor_final.py` | Phase 14 agent가 실행해 전체 완성 판정 |
| **agent 생성** (agent가 직접 작성) | `test_monitor.py` | Phase 13 agent의 결과물이자 검증 수단 |

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
| 12 | `python monitor_app.py` (수동) | 대시보드 화면 출력·갱신 동작 확인 |
| 13 | `python tests/test_monitor.py` | 집계 로직 M-1~M-9, 역할 경계(AST) |
| 14 | `python tests/test_monitor_final.py` | 전체 Phase E2E 최종 통합 검증 |

### AST 정적 검사 항목

| 파일 대상 | 금지 항목 |
|-----------|----------|
| `model/*.py` | `print()`, `input()` 호출, 파일 I/O |
| `controller/*.py` | `print()`, `input()` 호출, 직접 파일 I/O |
| `view/*.py` | `controller` 모듈 import, `math` 모듈 import, `open()` 등 외부 IO |
| `persistence/*.py` | `print()`, `input()`, 비즈니스 로직 (상태 전이 등) |
| `monitor/monitor_controller.py` | `print()`, `input()`, 데이터 변경 호출 |
| `monitor/monitor_view.py` | Repository 직접 import, 비즈니스 로직 |

## 이번 POC 범위 (3차 — 데이터 모니터링 도구)

- **목표:** JSON 파일에 저장된 데이터를 읽어 콘솔 대시보드로 실시간 표시
- **범위:**
  - `monitor/` 패키지 신규 구현 (`MonitorController` + `MonitorView`)
  - 기존 `SampleRepository` / `OrderRepository` / `ProductionRepository` 재사용 (읽기 전용)
  - 시료 재고 현황·주문 현황·생산라인 현황을 단일 화면으로 구성
  - 자동 갱신(기본 5초) 및 수동 갱신 지원
  - `monitor_app.py` 진입점 구현
  - `tests/test_monitor.py` 작성
- **제외:** 데이터 수정, 인증, GUI, 동시성 처리
