"""
Phase D-2 검증 — dummy/ 생성기 3종 (sample, order, production)
"""
import ast
import os
import sys

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


# ──────────────────────────────────────────────
# D2-1: 파일 구조 검증
# ──────────────────────────────────────────────
def test_d2_1_file_structure():
    print("\n[D2-1] 파일 구조 검증")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [
        "dummy/sample_generator.py",
        "dummy/order_generator.py",
        "dummy/production_generator.py",
    ]
    for rel in files:
        check(f"D2-1 {rel} 존재", os.path.isfile(os.path.join(base, rel)))


# ──────────────────────────────────────────────
# D2-2: sample_generator 검증
# ──────────────────────────────────────────────
def test_d2_2_sample_generator():
    print("\n[D2-2] sample_generator — generate_samples 검증")
    try:
        from dummy.sample_generator import generate_samples
        check("D2-2-1 generate_samples import 성공", True)

        samples = generate_samples(5)
        check("D2-2-2 반환값 리스트 타입", isinstance(samples, list))
        check("D2-2-3 5개 반환", len(samples) == 5)

        if samples:
            s = samples[0]
            check("D2-2-4 sample_id 속성 존재", hasattr(s, "sample_id"))
            check("D2-2-5 name 속성 존재", hasattr(s, "name"))
            check("D2-2-6 stock 속성 존재", hasattr(s, "stock"))
            check("D2-2-7 yield_rate 속성 존재", hasattr(s, "yield_rate"))
            check("D2-2-8 avg_production_time 속성 존재", hasattr(s, "avg_production_time"))

        check("D2-2-9 yield_rate 범위 (0 < yr ≤ 1)",
              all(0 < s.yield_rate <= 1.0 for s in samples))
        check("D2-2-10 avg_production_time 양수",
              all(s.avg_production_time > 0 for s in samples))
        check("D2-2-11 stock 0 이상",
              all(s.stock >= 0 for s in samples))

        ids = [s.sample_id for s in samples]
        check("D2-2-12 sample_id 중복 없음", len(ids) == len(set(ids)))
        check("D2-2-13 sample_id 형식 (S001 등)",
              all(sid.startswith("S") for sid in ids))

        # count 파라미터 동작
        s1 = generate_samples(1)
        s3 = generate_samples(3)
        check("D2-2-14 count=1 → 1개 반환", len(s1) == 1)
        check("D2-2-15 count=3 → 3개 반환", len(s3) == 3)

        # count 초과 시 pool 크기로 자동 조정
        s_max = generate_samples(999)
        check("D2-2-16 count 초과 시 pool 크기 이하 반환", len(s_max) > 0)

    except ImportError as e:
        check(f"D2-2-1 generate_samples import 성공 ({e})", False)
    except Exception as e:
        check(f"D2-2 sample_generator 오류 ({e})", False)


# ──────────────────────────────────────────────
# D2-3: order_generator 검증
# ──────────────────────────────────────────────
def test_d2_3_order_generator():
    print("\n[D2-3] order_generator — generate_orders 검증")
    try:
        from dummy.sample_generator import generate_samples
        from dummy.order_generator import generate_orders
        from model.order_status import OrderStatus

        samples = generate_samples(3)
        orders = generate_orders(samples, 20)

        check("D2-3-1 generate_orders import 성공", True)
        check("D2-3-2 반환값 리스트 타입", isinstance(orders, list))
        check("D2-3-3 20개 반환", len(orders) == 20)

        if orders:
            o = orders[0]
            check("D2-3-4 order_id 속성 존재", hasattr(o, "order_id"))
            check("D2-3-5 sample_id 속성 존재", hasattr(o, "sample_id"))
            check("D2-3-6 customer 속성 존재", hasattr(o, "customer"))
            check("D2-3-7 quantity 속성 존재", hasattr(o, "quantity"))
            check("D2-3-8 status 속성 존재", hasattr(o, "status"))

        check("D2-3-9 quantity 양수", all(o.quantity > 0 for o in orders))
        check("D2-3-10 REJECTED 미포함",
              all(o.status != OrderStatus.REJECTED for o in orders))

        statuses = {o.status for o in orders}
        expected = {
            OrderStatus.RESERVED, OrderStatus.PRODUCING,
            OrderStatus.CONFIRMED, OrderStatus.RELEASE,
        }
        check("D2-3-11 4가지 상태 모두 포함", statuses == expected)

        # order_id 중복 없음
        oids = [o.order_id for o in orders]
        check("D2-3-12 order_id 중복 없음", len(oids) == len(set(oids)))

        # sample_id가 전달된 samples 중 하나여야 함
        valid_sids = {s.sample_id for s in samples}
        check("D2-3-13 order.sample_id가 생성된 시료 중 하나",
              all(o.sample_id in valid_sids for o in orders))

        # status_ratio 파라미터 동작
        ratio = {"RESERVED": 1.0, "PRODUCING": 0.0, "CONFIRMED": 0.0, "RELEASE": 0.0}
        orders_r = generate_orders(samples, 10, status_ratio=ratio)
        check("D2-3-14 status_ratio=RESERVED 100% 적용",
              all(o.status == OrderStatus.RESERVED for o in orders_r))

        # 빈 samples 처리
        empty_orders = generate_orders([], 10)
        check("D2-3-15 빈 samples 입력 시 빈 리스트 반환",
              isinstance(empty_orders, list) and len(empty_orders) == 0)

    except ImportError as e:
        check(f"D2-3-1 generate_orders import 성공 ({e})", False)
    except Exception as e:
        check(f"D2-3 order_generator 오류 ({e})", False)


# ──────────────────────────────────────────────
# D2-4: production_generator 검증
# ──────────────────────────────────────────────
def test_d2_4_production_generator():
    print("\n[D2-4] production_generator — generate_production_jobs 검증")
    try:
        import math
        from dummy.sample_generator import generate_samples
        from dummy.order_generator import generate_orders
        from dummy.production_generator import generate_production_jobs
        from model.order_status import OrderStatus

        samples = generate_samples(3)
        orders = generate_orders(samples, 20)
        jobs = generate_production_jobs(orders, samples)

        check("D2-4-1 generate_production_jobs import 성공", True)
        check("D2-4-2 반환값 리스트 타입", isinstance(jobs, list))

        producing_count = sum(1 for o in orders if o.status == OrderStatus.PRODUCING)
        check("D2-4-3 PRODUCING 주문 수 = jobs 수", len(jobs) == producing_count)

        if jobs:
            required_keys = {"order_id", "sample_id", "actual_qty",
                             "total_time", "produced_qty", "is_current"}
            check("D2-4-4 필수 키 존재",
                  all(required_keys.issubset(j.keys()) for j in jobs))
            check("D2-4-5 actual_qty 양수", all(j["actual_qty"] > 0 for j in jobs))
            check("D2-4-6 total_time 양수", all(j["total_time"] > 0 for j in jobs))
            check("D2-4-7 produced_qty ≥ 0", all(j["produced_qty"] >= 0 for j in jobs))

            current_count = sum(1 for j in jobs if j["is_current"] == 1)
            check("D2-4-8 is_current=1 최대 1개", current_count <= 1)

            # 생산 계산식 검증: actual_qty = ceil(quantity / (yield_rate * 0.9))
            sample_map = {s.sample_id: s for s in samples}
            order_map = {o.order_id: o for o in orders}
            for j in jobs:
                o = order_map.get(j["order_id"])
                s = sample_map.get(j["sample_id"])
                if o and s:
                    expected_qty = math.ceil(o.quantity / (s.yield_rate * 0.9))
                    if j["actual_qty"] != expected_qty:
                        check(f"D2-4-9 actual_qty 계산식 ({j['order_id']})", False)
                        break
            else:
                check("D2-4-9 actual_qty 계산식 정확성", True)

        # 빈 PRODUCING 처리
        ratio_no_prod = {
            "RESERVED": 0.5, "PRODUCING": 0.0,
            "CONFIRMED": 0.3, "RELEASE": 0.2,
        }
        orders_no_prod = generate_orders(samples, 10, status_ratio=ratio_no_prod)
        jobs_empty = generate_production_jobs(orders_no_prod, samples)
        check("D2-4-10 PRODUCING 없을 때 빈 리스트 반환",
              isinstance(jobs_empty, list) and len(jobs_empty) == 0)

    except ImportError as e:
        check(f"D2-4-1 generate_production_jobs import 성공 ({e})", False)
    except Exception as e:
        check(f"D2-4 production_generator 오류 ({e})", False)


# ──────────────────────────────────────────────
# D2-5: 역할 경계 AST 검사
# ──────────────────────────────────────────────
def test_d2_5_ast():
    print("\n[D2-5] 역할 경계 (AST) — dummy/*.py (생성기)")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generator_files = [
        os.path.join(base, "dummy", "sample_generator.py"),
        os.path.join(base, "dummy", "order_generator.py"),
        os.path.join(base, "dummy", "production_generator.py"),
    ]
    for filepath in generator_files:
        rel = os.path.relpath(filepath, base)
        try:
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
            check(f"D2-5 {rel} — print/input 없음", len(forbidden) == 0)

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
            check(f"D2-5 {rel} — sqlite3 직접 import 없음", len(sqlite_imports) == 0)

            # open() 직접 호출 금지
            open_calls = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name) and func.id == "open":
                        open_calls.append("open")
            check(f"D2-5 {rel} — open() 직접 호출 없음", len(open_calls) == 0)

        except FileNotFoundError:
            check(f"D2-5 {rel} — 파일 존재", False)
        except SyntaxError as e:
            check(f"D2-5 {rel} — 구문 오류 없음 ({e})", False)


# ──────────────────────────────────────────────
# main
# ──────────────────────────────────────────────
def main():
    print("=" * 54)
    print("Phase D-2 검증 — dummy/ 생성기 3종")
    print("=" * 54)

    test_d2_1_file_structure()
    test_d2_2_sample_generator()
    test_d2_3_order_generator()
    test_d2_4_production_generator()
    test_d2_5_ast()

    print("\n" + "-" * 54)
    print(f"결과: {_pass}개 통과 / {_fail}개 실패")
    if _fail == 0:
        print("✓ Phase D-2 검증 완료 — 모든 항목 통과")
    else:
        print("✗ 일부 항목 실패 — 위 [FAIL] 항목을 확인하세요")
        sys.exit(1)


if __name__ == "__main__":
    main()
