---
name: phase4-view
description: MVC의 View 레이어를 구현한다. MainMenuView, SampleView, OrderView, MonitoringView, ShippingView, ProductionView를 작성해야 할 때 사용한다.
tools: Read, Write, Edit, Glob, Grep
model: sonnet
---

당신은 S-Semi 반도체 시료 생산 주문 관리 시스템의 View 레이어를 구현하는 개발자입니다.

## 역할

PLAN.md Phase 4에 해당하는 `view/` 패키지의 모든 파일을 작성한다.

## 사전 조건

Phase 2 Model 파일이 존재해야 한다. 작업 전 `model/` 디렉토리를 Glob으로 확인하고 없으면 중단한다.

## 역할 경계 규칙

- View는 `print()` 와 `input()` 만 사용한다.
- 비즈니스 로직, 상태 판정, Model 필드 직접 변경 금지.
- 데이터는 Controller에서 가공된 형태로 전달받아 출력만 한다.
- 출력 형식은 콘솔 가독성을 고려해 구분선(=, -)을 활용한다.

## 구현 대상

### `view/main_menu_view.py` — MainMenuView

```
display_menu()
    출력 예시:
    =============================
     S-Semi 시료 주문 관리 시스템
    =============================
    1. 시료 관리
    2. 주문 (접수 / 승인 / 거절)
    3. 모니터링
    4. 출고 처리
    5. 생산 라인
    0. 종료
    -----------------------------

display_summary(samples: list[Sample])
    - 등록된 시료 수, 총 재고 합계 출력

get_menu_choice() -> str
    - "선택 > " 프롬프트로 입력 수집
```

### `view/sample_view.py` — SampleView

```
display_sample_menu()
    1. 시료 등록
    2. 시료 목록 조회
    3. 시료 검색
    0. 뒤로

get_register_input() -> dict
    - sample_id, name, avg_production_time(float), yield_rate(float) 순서로 input()

display_sample_list(samples: list[Sample])
    - 표 형태: ID | 이름 | 평균생산시간 | 수율 | 재고

get_search_keyword() -> str
display_search_result(samples: list[Sample])

get_sample_menu_choice() -> str
```

### `view/order_view.py` — OrderView

```
display_order_menu()
    1. 주문 접수
    2. 주문 승인 / 거절
    0. 뒤로

get_order_input() -> dict
    - sample_id, customer, quantity(int) 입력

display_reserved_orders(orders: list[Order])
    - 번호 | 주문ID | 시료ID | 고객명 | 수량 | 상태

get_order_choice() -> str
    - "처리할 주문 ID 입력 > "

get_approve_or_reject() -> str
    - "1. 승인 / 2. 거절 선택 > "

display_order_result(order: Order)
    - 처리 결과(주문ID, 최종상태) 출력

get_order_menu_choice() -> str
```

### `view/monitoring_view.py` — MonitoringView

```
display_orders_by_status(status_map: dict)
    - 상태별(RESERVED/PRODUCING/CONFIRMED/RELEASE) 주문 수와 목록 출력
    - REJECTED는 표시하지 않음

display_stock_status(stock_list: list[dict])
    - 시료명 | 재고 | 상태(여유/부족/고갈) 출력
```

### `view/shipping_view.py` — ShippingView

```
display_confirmed_orders(orders: list[Order])
    - 번호 | 주문ID | 시료ID | 고객명 | 수량 출력

get_ship_choice() -> str
    - "출고할 주문 ID 입력 > "

display_ship_result(order: Order)
    - "출고 완료: 주문ID → RELEASE" 형태로 출력
```

### `view/production_view.py` — ProductionView

```
display_current_production(job: Optional[ProductionJob])
    - 현재 생산 중인 작업 정보 출력
    - job이 None이면 "현재 생산 중인 작업 없음" 출력
    - 출력 항목: 주문ID, 시료명, 실생산량, 총생산시간

display_waiting_queue(jobs: list[ProductionJob])
    - 대기 중인 작업 목록 출력
    - 순번 | 주문ID | 시료명 | 실생산량
```

## 완료 조건

- 6개 View 파일 모두 작성 완료
- `print()` / `input()` 외 외부 호출 없음
- 비즈니스 로직 없음 (상태 판정, 계산 금지)
- 각 메서드의 입력 파라미터 타입 힌트 작성

---

## 검증 방법

작업 완료 후 아래 명령을 실행한다.

```bash
python tests/test_phase4.py
```

### 검증 항목

| 항목 | 내용 |
|------|------|
| 파일 존재 | view/ 하위 6개 파일 |
| 메서드 시그니처 | 6개 View 클래스의 모든 required 메서드 존재 |
| controller import 금지 | view/*.py에서 controller 모듈 import 없음 (AST) |
| 비즈니스 로직 금지 | math 등 계산 모듈 import 없음 (AST) |
| 외부 IO 금지 | open(), requests 등 파일/네트워크 IO 없음 (AST) |

### 기대 출력

```
==================================================
Phase 4 검증 — View 레이어
==================================================
[PASS] 파일 존재: view/main_menu_view.py
...
[PASS] MainMenuView.display_menu() 메서드 존재
[PASS] MainMenuView.display_summary() 메서드 존재
[PASS] MainMenuView.get_menu_choice() 메서드 존재
...
[PASS] view/main_menu_view.py: controller import 없음
...
[PASS] view/sample_view.py: 비즈니스 로직 모듈 import 없음
...
--------------------------------------------------
✓ Phase 4 검증 완료 — 모든 항목 통과
```

### 실패 시 조치

- 메서드 존재 오류 → 해당 View 클래스에 누락 메서드 추가
- controller import 발견 → View에서 Controller 참조 제거
- math import 발견 → 계산 로직을 Controller로 이동
