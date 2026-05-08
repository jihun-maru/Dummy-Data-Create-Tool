# PLAN.md — 데이터 모니터링 도구 POC 구현 계획

## 목표

기존에 완성된 JSON 파일 기반 Repository 인프라를 재사용하여,
현재 저장된 데이터 상태를 콘솔에서 실시간으로 조회할 수 있는 독립 관리자 도구를 완성한다.
메인 관리 시스템(`main.py`)과 별도 프로세스로 동작하며 데이터를 수정하지 않는다.

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

---

## 신규 구현 Phase (3차 POC — 데이터 모니터링 도구)

### Phase 12. `monitor/` 패키지 구현

> **사전 제공 검증 스크립트:** `tests/test_phase12.py` 는 Phase 12 agent 실행 전 이미 존재한다.
> Phase 12 agent는 구현 완료 후 이 스크립트를 실행해 검증한다.
> ```bash
> python tests/test_phase12.py
> ```

#### 목적

기존 Repository를 읽기 전용으로 사용하여 시스템 전체 현황을 대시보드 형태로 출력한다.

#### 생성 파일

```
monitor/
├── __init__.py
├── monitor_controller.py   # Repository 읽기 + 화면용 데이터 집계
└── monitor_view.py         # 대시보드 화면 출력 + 사용자 입력 처리
monitor_app.py              # 진입점 + 갱신 루프
```

#### MonitorController 인터페이스

```python
class MonitorController:
    def __init__(
        self,
        sample_repo: SampleRepository,
        order_repo: OrderRepository,
        production_repo: ProductionRepository,
    ): ...

    def get_stock_summary(self) -> list[dict]:
        # 각 시료별: sample_id, name, stock, status(여유/부족/고갈)
        # 재고 상태 판단: CONFIRMED + PRODUCING 주문 수량 합계와 비교

    def get_order_summary(self) -> dict[str, int]:
        # 상태별 건수: {RESERVED: n, PRODUCING: n, CONFIRMED: n, RELEASE: n}
        # REJECTED 제외

    def get_production_summary(self) -> dict:
        # current_job 정보 + queue 목록 (raw dict 활용)
```

#### MonitorView 인터페이스

```python
class MonitorView:
    def render_dashboard(
        self,
        stock_summary: list[dict],
        order_summary: dict[str, int],
        production_summary: dict,
        last_updated: str,
        auto_refresh: bool,
        refresh_interval: int,
    ) -> None:
        # 화면 클리어 후 전체 대시보드 출력

    def get_user_input(self, timeout: float) -> str:
        # 타임아웃 내 키 입력 반환 ('r', 'q', 'a' 또는 '')
        # timeout 초 내 입력 없으면 '' 반환 (자동갱신 트리거)
```

#### monitor_app.py 갱신 루프

```python
# 초기화
sample_repo = SampleRepository("data/samples.json")
order_repo  = OrderRepository("data/orders.json")
production_repo = ProductionRepository("data/production.json")

ctrl = MonitorController(sample_repo, order_repo, production_repo)
view = MonitorView()

# 갱신 루프
while True:
    data = ctrl.collect()           # 집계
    view.render_dashboard(...)      # 출력
    key = view.get_user_input(REFRESH_INTERVAL)
    if key == 'q':   break
    if key == 'a':   auto_refresh = not auto_refresh
    # 'r' 또는 타임아웃: 즉시 재갱신
```

#### 수동 갱신 vs 자동 갱신

| 모드 | 동작 |
|------|------|
| 자동 갱신(기본 ON) | `REFRESH_INTERVAL`초(기본 5) 마다 자동 재렌더링 |
| 수동 갱신 | `[r]` 입력 시 즉시 재렌더링 |
| 자동갱신 토글 | `[a]` 입력 시 자동/수동 전환 |
| 종료 | `[q]` 입력 또는 Ctrl+C |

#### 역할 경계

- `MonitorController`: `print()`, `input()`, 데이터 변경 호출 금지
- `MonitorView`: Repository 직접 import 금지, 비즈니스 로직 금지
- `monitor_app.py`: Repository 초기화 및 루프만 담당

#### 검증 (수동)

```bash
python monitor_app.py
```

대시보드가 출력되고 자동 갱신·수동 갱신·종료가 정상 동작하면 통과.

---

### Phase 13. `tests/test_monitor.py` 작성

> **Phase 13 자체가 테스트 파일 생성이다.** 완성된 `tests/test_monitor.py` 를 실행해 전체 통과 여부로 검증한다.
> ```bash
> python tests/test_monitor.py
> ```

#### 파일: `tests/test_monitor.py`

##### 테스트 시나리오

| 번호 | 시나리오 | 검증 내용 |
|------|----------|----------|
| M-1 | 패키지 구조 검증 | `monitor/` 디렉토리, 3개 파일, `monitor_app.py` 존재 확인 |
| M-2 | MonitorController import | `MonitorController` 클래스 정상 import 및 인스턴스화 |
| M-3 | 재고 현황 집계 | 시료·주문 데이터 주입 → `get_stock_summary()` 반환값 형식·상태 검증 |
| M-4 | 주문 현황 집계 | 상태별 건수 합산 정확성 검증 (REJECTED 제외 확인) |
| M-5 | 생산라인 현황 집계 | current_job / queue 반환 구조 검증 |
| M-6 | 빈 데이터 처리 | 데이터 없는 경우(파일 미존재) 정상 반환 (빈 리스트/딕셔너리) |
| M-7 | MonitorView import | `MonitorView` 클래스 정상 import 확인 |
| M-8 | 역할 경계 (AST) | `monitor_controller.py`에서 `print()` / `input()` 미사용 확인 |
| M-9 | 역할 경계 (AST) | `monitor_view.py`에서 `persistence` 직접 import 미사용 확인 |

##### 테스트 격리

- 각 테스트는 임시 디렉토리(`tempfile.mkdtemp()`)에 JSON 파일을 생성하고 종료 후 삭제
- `data/` 실제 파일을 오염시키지 않는다

#### 검증 명령

```bash
python tests/test_monitor.py
```

---

---

### Phase 14. 최종 통합 검증

> **사전 제공 검증 스크립트:** `tests/test_monitor_final.py` 는 Phase 14 agent 실행 전 이미 존재한다.
> Phase 14 agent는 사전 조건 확인 후 이 스크립트를 실행해 전체 POC 완성 여부를 판정한다.

#### 목적

Phase 1~13이 모두 완료된 후 단일 명령으로 전체 시스템의 정합성을 검증한다.

#### 검증 스크립트: `tests/test_monitor_final.py`

```bash
python tests/test_monitor_final.py
```

#### 4단계 검증 흐름

| 단계 | 스크립트/내용 | 검증 대상 |
|------|--------------|----------|
| 단계 1 | `test_final.py` subprocess | Phase 1~11 전체 (MVC + 영속성 POC) |
| 단계 2 | `test_phase12.py` subprocess | Phase 12: monitor/ 패키지 구조·역할 경계 |
| 단계 3 | `test_monitor.py` subprocess | Phase 13: 집계 로직·AST 검증 (M-1~M-9) |
| 단계 4 | 인라인 E2E 시나리오 | 데이터 생성 → MonitorController 조회 → render_dashboard 렌더링 |
| 단계 5 | 파일 구조 확인 | 전체 필수 파일 14개 존재 확인 |

#### E2E 시나리오 검증 항목

| 항목 | 검증 내용 |
|------|----------|
| 세션 1: 데이터 생성 | 시료 2개, 주문 5개(상태별), 생산 작업 1개 |
| 세션 2: 재고 현황 | S001 여유 / S002 고갈 레이블 정확성 |
| 세션 2: 주문 현황 | RESERVED·CONFIRMED·PRODUCING·RELEASE 각 1건, REJECTED 제외 |
| 세션 2: 생산 현황 | current_job order_id 일치 |
| 세션 2: 렌더링 | render_dashboard 오류 없음, 출력에 핵심 데이터 포함 |

#### 실행 명령

```bash
python tests/test_monitor_final.py
```

또는 단계별 분리 실행:

```bash
python tests/test_final.py
python tests/test_phase12.py
python tests/test_monitor.py
python tests/test_monitor_final.py
```

#### 기대 최종 출력

```
결과: N개 통과 / 0개 실패
✓ 최종 통합 검증 완료 — 모든 항목 통과
  데이터 모니터링 도구 POC 구현 완성
```

---

## 의존성 흐름 (갱신)

```
main.py (관리 시스템)
  └─► Controller (유스케이스 조율)
        ├─► Model (상태 변경)
        ├─► Repository (영속화) ──► data/*.json
        └─► View (입출력)

monitor_app.py (모니터링 도구, 별도 프로세스)
  └─► MonitorController (읽기 전용 집계)
        └─► Repository (읽기 전용) ──► data/*.json (동일 파일)
  └─► MonitorView (대시보드 출력)
```

Repository는 두 프로세스에서 독립적으로 읽기 전용 접근이 가능하다.
동시 쓰기 충돌은 이번 POC 범위 외이다.

---

## 체크리스트

### Phase 12 — `monitor/` 패키지

- [ ] `monitor/__init__.py`
- [ ] `monitor/monitor_controller.py` — `get_stock_summary()`, `get_order_summary()`, `get_production_summary()`
- [ ] `monitor/monitor_view.py` — `render_dashboard()`, `get_user_input()`
- [ ] `monitor_app.py` — Repository 초기화 + 갱신 루프
- [ ] `python tests/test_phase12.py` 전체 통과 ← **자동 검증**
- [ ] `python monitor_app.py` 수동 확인 통과

### Phase 13 — `tests/test_monitor.py`

- [ ] `tests/test_monitor.py` — 시나리오 M-1 ~ M-9 작성 및 통과
- [ ] `python tests/test_monitor.py` 전체 통과 ← **자동 검증**

### Phase 14 — 최종 통합 검증

- [ ] `python tests/test_monitor_final.py` 전체 통과
  - [ ] 단계 1: `test_final.py` (Phase 1~11) 통과
  - [ ] 단계 2: `test_phase12.py` 통과
  - [ ] 단계 3: `test_monitor.py` 통과
  - [ ] 단계 4: E2E 시나리오 (데이터 생성 → 조회 → 렌더링) 통과
  - [ ] 단계 5: 전체 파일 구조 확인 통과

### 사전 제공 테스트 파일

- [x] `tests/test_phase12.py` — Phase 12 agent 검증용 (이미 작성)
- [x] `tests/test_monitor_final.py` — Phase 14 최종 검증용 (이미 작성)

### 최종 확인

- [ ] `monitor/` 패키지 구조 완성
- [ ] `monitor_app.py` 실행 시 대시보드 정상 출력
- [ ] 자동 갱신(5초) 및 수동 갱신(`r`) 동작
- [ ] `[q]` 및 Ctrl+C 종료 동작
- [ ] `python tests/test_monitor_final.py` 전체 통과
