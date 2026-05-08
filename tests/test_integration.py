"""
전체 통합 테스트 — 시나리오 기반 End-to-End 검증
실행: python tests/test_integration.py  (프로젝트 루트에서)

Phase 1~4가 완료된 상태에서 실행한다.
모든 레이어(Model·Controller)가 연결되어 정상 동작하는지 검증한다.
"""
import math
import os
import shutil
import sys
sys.stdout.reconfigure(encoding='utf-8')
import tempfile

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

PASS = "[PASS]"
FAIL = "[FAIL]"
_failures = []


def check(condition: bool, message: str) -> None:
    if condition:
        print(f"{PASS} {message}")
    else:
        print(f"{FAIL} {message}")
        _failures.append(message)


def _make_repos(tmp: str):
    from persistence.sample_repository import SampleRepository
    from persistence.order_repository import OrderRepository
    from persistence.production_repository import ProductionRepository
    return (
        SampleRepository(os.path.join(tmp, "samples.json")),
        OrderRepository(os.path.join(tmp, "orders.json")),
        ProductionRepository(os.path.join(tmp, "production.json")),
    )


def _setup():
    from model.production_line import ProductionLine
    from controller.sample_controller import SampleController
    from controller.order_controller import OrderController
    from controller.monitoring_controller import MonitoringController
    from controller.shipping_controller import ShippingController
    from controller.production_controller import ProductionController

    tmp = tempfile.mkdtemp()
    sample_repo, order_repo, production_repo = _make_repos(tmp)
    pl = ProductionLine()
    return (
        tmp,
        sample_repo, order_repo, production_repo, pl,
        SampleController(sample_repo),
        OrderController(order_repo, sample_repo, pl, production_repo),
        MonitoringController(order_repo, sample_repo),
        ShippingController(order_repo),
        ProductionController(pl, order_repo, sample_repo, production_repo),
    )


def test_scenario_1_stock_sufficient():
    """시나리오 1: 재고 충분 → 즉시 CONFIRMED → RELEASE"""
    print("\n[시나리오 1] 재고 충분 → RESERVED → CONFIRMED → RELEASE")
    tmp = None
    try:
        from model.order_status import OrderStatus
        tmp, sample_repo, order_repo, production_repo, pl, sc, oc, mc, shc, pc = _setup()

        s = sc.register_sample("S001", "충분시료", 1.0, 0.9)
        s.add_stock(50)
        sample_repo.save(s)

        order = oc.place_order("S001", "고객A", 10)
        check(order.status == OrderStatus.RESERVED, "주문접수 → RESERVED")

        approved = oc.approve_order(order.order_id)
        check(approved.status == OrderStatus.CONFIRMED, "재고충분 승인 → CONFIRMED")

        reloaded_s = sample_repo.find_by_id("S001")
        check(reloaded_s.stock == 40, "승인 후 재고 차감 (50→40)")

        shipped = shc.ship_order(order.order_id)
        check(shipped.status == OrderStatus.RELEASE, "출고 처리 → RELEASE")

        status_map = mc.get_orders_by_status()
        from model.order_status import OrderStatus as OS
        release_orders = status_map.get(OS.RELEASE, [])
        check(any(o.order_id == order.order_id for o in release_orders),
              "RELEASE 주문이 모니터링에 표시")
    except Exception as e:
        check(False, f"시나리오 1 예외: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp)


def test_scenario_2_production_required():
    """시나리오 2: 재고 부족 → PRODUCING → 생산완료 → CONFIRMED → RELEASE"""
    print("\n[시나리오 2] 재고 부족 → PRODUCING → CONFIRMED → RELEASE")
    tmp = None
    try:
        from model.order_status import OrderStatus
        tmp, sample_repo, order_repo, production_repo, pl, sc, oc, mc, shc, pc = _setup()

        sc.register_sample("S002", "부족시료", 2.0, 0.8)

        order = oc.place_order("S002", "고객B", 10)
        approved = oc.approve_order(order.order_id)
        check(approved.status == OrderStatus.PRODUCING, "재고부족 승인 → PRODUCING")

        job = pc.get_current_production()
        check(job is not None, "생산라인에 job 등록됨")

        expected_qty = math.ceil(10 / (0.8 * 0.9))
        check(job.actual_qty == expected_qty,
              f"실생산량: ceil(10/(0.8*0.9)) == {expected_qty}")

        completed = pc.advance_production()
        check(completed.status == OrderStatus.CONFIRMED, "생산완료 → CONFIRMED")

        reloaded_s = sample_repo.find_by_id("S002")
        check(reloaded_s.stock >= 0, "생산 후 재고 음수 아님")

        shipped = shc.ship_order(order.order_id)
        check(shipped.status == OrderStatus.RELEASE, "출고 처리 → RELEASE")
    except Exception as e:
        check(False, f"시나리오 2 예외: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp)


def test_scenario_3_reject_excluded_from_monitoring():
    """시나리오 3: REJECTED 주문은 모니터링 제외"""
    print("\n[시나리오 3] 주문 거절 → REJECTED → 모니터링 제외")
    tmp = None
    try:
        from model.order_status import OrderStatus
        tmp, sample_repo, order_repo, production_repo, pl, sc, oc, mc, shc, pc = _setup()

        sc.register_sample("S003", "거절시료", 1.0, 0.9)
        order = oc.place_order("S003", "고객C", 5)
        rejected = oc.reject_order(order.order_id)
        check(rejected.status == OrderStatus.REJECTED, "거절 → REJECTED")

        status_map = mc.get_orders_by_status()
        all_orders_in_monitoring = [o for lst in status_map.values() for o in lst]
        check(
            all(o.order_id != order.order_id for o in all_orders_in_monitoring),
            "REJECTED 주문이 모니터링에 미포함"
        )
        check(OrderStatus.REJECTED not in status_map or
              len(status_map.get(OrderStatus.REJECTED, [])) == 0,
              "모니터링 status_map에 REJECTED 키 없음 또는 비어있음")
    except Exception as e:
        check(False, f"시나리오 3 예외: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp)


def test_scenario_4_production_fifo():
    """시나리오 4: 여러 주문 승인 시 생산 큐가 FIFO 순서를 유지"""
    print("\n[시나리오 4] 생산 큐 FIFO 순서 검증")
    tmp = None
    try:
        from model.order_status import OrderStatus
        tmp, sample_repo, order_repo, production_repo, pl, sc, oc, mc, shc, pc = _setup()

        sc.register_sample("S001", "FIFO시료", 1.0, 0.9)

        o1 = oc.place_order("S001", "고객1", 5)
        o2 = oc.place_order("S001", "고객2", 3)
        o3 = oc.place_order("S001", "고객3", 7)

        oc.approve_order(o1.order_id)
        oc.approve_order(o2.order_id)
        oc.approve_order(o3.order_id)

        current = pc.get_current_production()
        check(current is not None, "첫 번째 job이 current_job으로 설정")
        check(current.order.order_id == o1.order_id, "FIFO: 첫 승인 주문이 먼저 생산")

        waiting = pc.get_waiting_queue()
        check(len(waiting) == 2, "FIFO: 대기 큐에 2개 존재")
        check(waiting[0].order.order_id == o2.order_id, "FIFO: 대기 큐 1번째 == 두 번째 승인 주문")
        check(waiting[1].order.order_id == o3.order_id, "FIFO: 대기 큐 2번째 == 세 번째 승인 주문")

        pc.advance_production()
        current = pc.get_current_production()
        check(current.order.order_id == o2.order_id, "advance 후 FIFO: 다음 current_job == o2")
    except Exception as e:
        check(False, f"시나리오 4 예외: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp)


def test_scenario_5_stock_status_labels():
    """시나리오 5: 재고 상태 레이블 전환 (고갈 → 부족 → 여유)"""
    print("\n[시나리오 5] 재고 상태 레이블 전환")
    tmp = None
    try:
        tmp, sample_repo, order_repo, production_repo, pl, sc, oc, mc, shc, pc = _setup()
        s = sc.register_sample("S001", "레이블시료", 1.0, 0.9)

        stock_list = mc.get_stock_status()
        check(stock_list[0]["label"] == "고갈", "재고=0 → 레이블: 고갈")

        s.add_stock(2)
        sample_repo.save(s)
        order = oc.place_order("S001", "고객A", 10)
        oc.approve_order(order.order_id)
        stock_list = mc.get_stock_status()
        check(stock_list[0]["label"] == "부족",
              f"재고<주문 → 레이블: 부족 (실제: {stock_list[0]['label']})")

        reloaded_s = sample_repo.find_by_id("S001")
        reloaded_s.add_stock(200)
        sample_repo.save(reloaded_s)
        stock_list = mc.get_stock_status()
        check(stock_list[0]["label"] == "여유",
              f"재고충분 → 레이블: 여유 (실제: {stock_list[0]['label']})")
    except Exception as e:
        check(False, f"시나리오 5 예외: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp)


def test_scenario_6_multiple_samples():
    """시나리오 6: 다수 시료·주문 동시 운용 — 데이터 간 격리"""
    print("\n[시나리오 6] 다수 시료 동시 운용 격리성")
    tmp = None
    try:
        from model.order_status import OrderStatus
        tmp, sample_repo, order_repo, production_repo, pl, sc, oc, mc, shc, pc = _setup()

        sa = sc.register_sample("SA", "시료A", 1.0, 0.9)
        sc.register_sample("SB", "시료B", 2.0, 0.8)
        sa.add_stock(100)
        sample_repo.save(sa)

        oa = oc.place_order("SA", "고객A", 10)
        ob = oc.place_order("SB", "고객B", 5)

        oc.approve_order(oa.order_id)
        oc.approve_order(ob.order_id)

        reloaded_oa = order_repo.find_by_id(oa.order_id)
        reloaded_ob = order_repo.find_by_id(ob.order_id)
        check(reloaded_oa.status == OrderStatus.CONFIRMED, "시료A 주문: 재고충분 → CONFIRMED")
        check(reloaded_ob.status == OrderStatus.PRODUCING, "시료B 주문: 재고없음 → PRODUCING")

        reloaded_sa = sample_repo.find_by_id("SA")
        reloaded_sb = sample_repo.find_by_id("SB")
        check(reloaded_sa.stock == 90, "시료A 재고 독립 차감 (100→90)")
        check(reloaded_sb.stock == 0, "시료B 재고 미변경 (생산 전)")

        stock_list = mc.get_stock_status()
        labels = {item["sample"].sample_id: item["label"] for item in stock_list}
        check(labels.get("SA") == "여유", "시료A 재고 상태: 여유")
        check(labels.get("SB") in ("고갈", "부족"), f"시료B 재고 상태: 고갈 또는 부족 (실제: {labels.get('SB')})")
    except Exception as e:
        check(False, f"시나리오 6 예외: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    print("=" * 50)
    print("전체 통합 테스트 — End-to-End 시나리오")
    print("=" * 50)

    test_scenario_1_stock_sufficient()
    test_scenario_2_production_required()
    test_scenario_3_reject_excluded_from_monitoring()
    test_scenario_4_production_fifo()
    test_scenario_5_stock_status_labels()
    test_scenario_6_multiple_samples()

    print("\n" + "=" * 50)
    if _failures:
        print(f"결과: {len(_failures)}개 실패")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("✓ 전체 통합 테스트 완료 — 모든 시나리오 통과")
