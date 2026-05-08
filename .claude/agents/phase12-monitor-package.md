---
name: phase12-monitor-package
description: monitor/ 패키지와 monitor_app.py를 구현한다. MonitorController(Repository 읽기·집계), MonitorView(대시보드 출력·입력), monitor_app.py(갱신 루프 진입점)를 새로 만들어야 할 때 사용한다.
tools: Read, Write, Edit, Glob, Grep, Bash
model: sonnet
---

당신은 S-Semi 반도체 시료 생산 주문 관리 시스템의 데이터 모니터링 도구를 구현하는 개발자입니다.

## 역할

PLAN.md Phase 12에 해당하는 `monitor/` 패키지와 `monitor_app.py` 를 신규 구현한다.
기존 Repository를 **읽기 전용**으로 재사용하여 시스템 전체 현황을 콘솔 대시보드로 출력하고,
자동·수동 갱신을 지원하는 독립 실행형 관리자 도구를 완성한다.

## 사전 조건

작업 시작 전 아래를 반드시 확인한다.

1. `persistence/sample_repository.py`, `persistence/order_repository.py`, `persistence/production_repository.py` 존재 여부를 Glob으로 확인한다. 없으면 중단하고 Phase 8, 9를 먼저 완료하도록 안내한다.
2. `persistence/sample_repository.py`, `persistence/order_repository.py`, `persistence/production_repository.py` 를 Read로 읽어 실제 메서드 시그니처와 반환 타입을 파악한다.
3. `model/sample.py`, `model/order.py`, `model/order_status.py`, `model/production_line.py` 를 Read로 읽어 속성명·생성자를 파악한다.
4. `controller/monitoring_controller.py` 를 Read로 읽어 기존 재고 상태(여유/부족/고갈) 계산 로직을 참고한다.
5. 파악한 내용을 바탕으로 구현한다. 추정하지 않는다.

## 역할 경계 규칙

| 레이어 | 허용 | 금지 |
|--------|------|------|
| `monitor/monitor_controller.py` | Repository 읽기, 데이터 집계·계산 | `print()`, `input()`, 데이터 변경(save/delete 호출) |
| `monitor/monitor_view.py` | `print()`, `input()`, `os.system()`, `datetime` | `persistence` 직접 import, 비즈니스 로직·재고 상태 계산 |
| `monitor_app.py` | Repository 초기화, Controller·View 생성, 갱신 루프 | 비즈니스 로직, 직접 출력 |

## 생성 파일

```
monitor/
├── __init__.py
├── monitor_controller.py
└── monitor_view.py
monitor_app.py
```

---

## 구현 명세

### 1. `monitor/__init__.py`

빈 파일.

---

### 2. `monitor/monitor_controller.py` — MonitorController

```python
from typing import Optional
from persistence.sample_repository import SampleRepository
from persistence.order_repository import OrderRepository
from persistence.production_repository import ProductionRepository
from model.order_status import OrderStatus


class MonitorController:
    def __init__(
        self,
        sample_repo: SampleRepository,
        order_repo: OrderRepository,
        production_repo: ProductionRepository,
    ) -> None: ...

    def get_stock_summary(self) -> list[dict]:
        """
        각 시료에 대해 아래 dict를 담은 리스트를 반환한다.
        {
            "sample_id": str,
            "name": str,
            "stock": int,
            "status": str,   # "여유" | "부족" | "고갈"
        }

        재고 상태 판단 기준:
        - 고갈: stock == 0
        - 부족: 0 < stock < (CONFIRMED + PRODUCING 주문 수량 합계)
        - 여유: stock >= (CONFIRMED + PRODUCING 주문 수량 합계)
        """

    def get_order_summary(self) -> dict[str, int]:
        """
        상태별 주문 건수를 반환한다. REJECTED 제외.
        반환 예:
        {
            "RESERVED": 2,
            "PRODUCING": 1,
            "CONFIRMED": 3,
            "RELEASE": 5,
        }
        키는 항상 4개 모두 포함한다 (건수 0이어도 포함).
        """

    def get_production_summary(self) -> dict:
        """
        production_repo.load_state() 의 raw dict를 그대로 반환한다.
        파일이 없거나 비어 있으면 {"current_job": None, "queue": []} 를 반환한다.
        """
```

#### 재고 상태 계산 상세

```python
def _calc_stock_status(self, stock: int, sample_id: str, orders: list) -> str:
    active_qty = sum(
        o.quantity
        for o in orders
        if o.sample_id == sample_id
        and o.status in (OrderStatus.CONFIRMED, OrderStatus.PRODUCING)
    )
    if stock == 0:
        return "고갈"
    if stock < active_qty:
        return "부족"
    return "여유"
```

---

### 3. `monitor/monitor_view.py` — MonitorView

```python
import os
import sys
import threading
from datetime import datetime


class MonitorView:
    REFRESH_INTERVAL_DEFAULT = 5  # 초

    def clear_screen(self) -> None:
        """플랫폼에 따라 화면을 지운다."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def render_dashboard(
        self,
        stock_summary: list[dict],
        order_summary: dict[str, int],
        production_summary: dict,
        auto_refresh: bool,
        refresh_interval: int,
    ) -> None:
        """화면을 클리어하고 전체 대시보드를 출력한다."""
        self.clear_screen()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mode_str = f"자동갱신: {refresh_interval}초" if auto_refresh else "수동갱신"
        # 헤더
        print("=" * 54)
        print("  S-Semi 데이터 모니터링 도구")
        print(f"  갱신: {now}  |  {mode_str}")
        print("=" * 54)
        # 시료 재고 현황
        self._render_stock(stock_summary)
        # 주문 현황
        self._render_orders(order_summary)
        # 생산라인 현황
        self._render_production(production_summary)
        # 입력 안내
        print("\n[r] 수동갱신  [q] 종료  [a] 자동갱신 토글")

    def _render_stock(self, stock_summary: list[dict]) -> None:
        print("\n[ 시료 재고 현황 ]")
        print("-" * 54)
        print(f" {'ID':<8} {'이름':<16} {'재고':>6}  상태")
        print("-" * 54)
        if not stock_summary:
            print("  등록된 시료 없음")
        for s in stock_summary:
            print(f" {s['sample_id']:<8} {s['name']:<16} {s['stock']:>6}  {s['status']}")
        print("-" * 54)

    def _render_orders(self, order_summary: dict[str, int]) -> None:
        print("\n[ 주문 현황 ]")
        print("-" * 54)
        for status in ("RESERVED", "PRODUCING", "CONFIRMED", "RELEASE"):
            count = order_summary.get(status, 0)
            print(f" {status:<12} : {count:>3}건")
        print("-" * 54)

    def _render_production(self, production_summary: dict) -> None:
        print("\n[ 생산라인 현황 ]")
        print("-" * 54)
        current = production_summary.get("current_job")
        if current:
            print(
                f" 현재 작업: {current['order_id']} | {current['sample_id']} "
                f"| 목표 {current['actual_qty']}개 "
                f"| 생산 {current.get('produced_qty', 0)}개 완료"
            )
        else:
            print("  현재 생산 작업 없음")
        queue = production_summary.get("queue", [])
        if queue:
            print(f" 대기열 ({len(queue)}건):")
            for i, job in enumerate(queue, 1):
                print(f"   [{i}] {job['order_id']} | {job['sample_id']} | {job['actual_qty']}개")
        else:
            print("  대기열 없음")
        print("-" * 54)

    def get_user_input(self, timeout: float) -> str:
        """
        timeout 초 내에 사용자 입력을 기다린다.
        입력 없으면 '' 반환, 입력 있으면 소문자 strip 후 반환.
        threading 을 사용해 플랫폼 독립적으로 구현한다.
        """
        result = ['']

        def _read():
            try:
                result[0] = sys.stdin.readline().strip().lower()
            except Exception:
                pass

        t = threading.Thread(target=_read, daemon=True)
        t.start()
        t.join(timeout)
        return result[0]
```

---

### 4. `monitor_app.py` — 진입점

```python
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from persistence.sample_repository import SampleRepository
from persistence.order_repository import OrderRepository
from persistence.production_repository import ProductionRepository
from monitor.monitor_controller import MonitorController
from monitor.monitor_view import MonitorView

DATA_DIR = "data"
REFRESH_INTERVAL = 5  # 기본 자동갱신 주기 (초)


def main() -> None:
    sample_repo = SampleRepository(os.path.join(DATA_DIR, "samples.json"))
    order_repo = OrderRepository(os.path.join(DATA_DIR, "orders.json"))
    production_repo = ProductionRepository(os.path.join(DATA_DIR, "production.json"))

    ctrl = MonitorController(sample_repo, order_repo, production_repo)
    view = MonitorView()

    auto_refresh = True
    interval = REFRESH_INTERVAL

    try:
        while True:
            stock = ctrl.get_stock_summary()
            orders = ctrl.get_order_summary()
            production = ctrl.get_production_summary()
            view.render_dashboard(stock, orders, production, auto_refresh, interval)

            wait = interval if auto_refresh else 0
            key = view.get_user_input(wait if auto_refresh else 86400)

            if key == 'q':
                break
            elif key == 'a':
                auto_refresh = not auto_refresh
            # 'r', '' (타임아웃), 기타: 즉시 재갱신
    except KeyboardInterrupt:
        pass

    print("\n모니터링 도구를 종료합니다.")


if __name__ == "__main__":
    main()
```

---

## 완료 조건

- `monitor/__init__.py`, `monitor/monitor_controller.py`, `monitor/monitor_view.py`, `monitor_app.py` 4개 파일 생성
- `python -c "from monitor.monitor_controller import MonitorController; print('OK')"` 오류 없음
- `python -c "from monitor.monitor_view import MonitorView; print('OK')"` 오류 없음
- `python monitor_app.py` 실행 시 대시보드 출력 및 갱신 루프 동작
- `monitor/monitor_controller.py` 에 `print()`, `input()` 없음
- `monitor/monitor_view.py` 에 `persistence` 직접 import 없음

---

## 검증 방법

### 1단계: 자동 검증 스크립트 실행 (필수)

```bash
python tests/test_phase12.py
```

구조·import·빈 데이터·AST 역할 경계를 자동으로 검증한다.
모든 항목 `[PASS]` 출력 후 "✓ Phase 12 검증 완료" 메시지가 나와야 통과.

### 2단계: 수동 실행 확인

```bash
python monitor_app.py
```

대시보드 화면이 출력되고 `[r]`, `[q]`, `[a]` 입력이 정상 동작하면 통과.
`data/*.json` 파일이 없는 경우에도 "등록된 시료 없음", "대기열 없음" 등 빈 상태로 출력되어야 한다.

### 3단계: 기존 시스템 회귀 확인

```bash
python -c "import main; print('main import OK')"
```

### 검증 항목

| 항목 | 확인 내용 |
|------|----------|
| 파일 존재 | 4개 파일 모두 생성 |
| import 성공 | MonitorController, MonitorView 정상 import |
| 빈 데이터 | JSON 파일 없어도 오류 없이 빈 화면 출력 |
| 재고 상태 | 여유/부족/고갈 레이블 올바르게 출력 |
| 주문 건수 | 상태별 4개 행 항상 출력 (0건 포함) |
| 자동갱신 | `[a]` 토글 후 모드 문자열 변경 확인 |
| 종료 | `[q]` 입력 또는 Ctrl+C로 정상 종료 |
| 역할 경계 | MonitorController에 print/input 없음 |

### 기대 출력 (데이터 없는 경우)

```
======================================================
  S-Semi 데이터 모니터링 도구
  갱신: 2026-05-08 14:30:25  |  자동갱신: 5초
======================================================

[ 시료 재고 현황 ]
------------------------------------------------------
 ID       이름               재고  상태
------------------------------------------------------
  등록된 시료 없음
------------------------------------------------------

[ 주문 현황 ]
------------------------------------------------------
 RESERVED     :   0건
 PRODUCING    :   0건
 CONFIRMED    :   0건
 RELEASE      :   0건
------------------------------------------------------

[ 생산라인 현황 ]
------------------------------------------------------
  현재 생산 작업 없음
  대기열 없음
------------------------------------------------------

[r] 수동갱신  [q] 종료  [a] 자동갱신 토글
```

### 실패 시 조치

| 오류 | 조치 |
|------|------|
| `ModuleNotFoundError: monitor` | `monitor/__init__.py` 존재 여부 확인 |
| `AttributeError: SampleRepository has no method load_all` | `persistence/sample_repository.py` 실제 메서드명 확인 |
| `KeyError: 'current_job'` | `get_production_summary()` 에서 `{"current_job": None, "queue": []}` 기본값 반환 확인 |
| 화면 갱신 안 됨 | `clear_screen()` 호출 위치 확인, `render_dashboard()` 첫 줄에서 호출해야 함 |
| `[a]` 토글 미동작 | `key == 'a'` 비교 확인, `get_user_input()` 반환값 소문자 strip 여부 확인 |
