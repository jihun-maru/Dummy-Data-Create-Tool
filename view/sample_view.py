class SampleView:
    def display_sample_menu(self) -> None:
        print("-----------------------------")
        print(" 시료 관리")
        print("-----------------------------")
        print("1. 시료 등록")
        print("2. 시료 목록 조회")
        print("3. 시료 검색")
        print("0. 뒤로")
        print("-----------------------------")

    def get_register_input(self) -> dict:
        sample_id = input("시료 ID > ")
        name = input("시료 이름 > ")
        avg_production_time = float(input("평균 생산시간 (시간) > "))
        yield_rate = float(input("수율 (0 초과 1 이하) > "))
        return {
            "sample_id": sample_id,
            "name": name,
            "avg_production_time": avg_production_time,
            "yield_rate": yield_rate,
        }

    def display_sample_list(self, samples: list) -> None:
        print("-----------------------------")
        print(f"{'ID':<12} {'이름':<16} {'평균생산시간':>12} {'수율':>8} {'재고':>6}")
        print("-----------------------------")
        for s in samples:
            print(f"{s.sample_id:<12} {s.name:<16} {s.avg_production_time:>12.2f} {s.yield_rate:>8.4f} {s.stock:>6}")
        print("-----------------------------")

    def get_search_keyword(self) -> str:
        return input("검색 키워드 > ")

    def display_search_result(self, samples: list) -> None:
        if not samples:
            print("[결과] 검색된 시료가 없습니다.")
            return
        print("-----------------------------")
        print(f"{'ID':<12} {'이름':<16} {'평균생산시간':>12} {'수율':>8} {'재고':>6}")
        print("-----------------------------")
        for s in samples:
            print(f"{s.sample_id:<12} {s.name:<16} {s.avg_production_time:>12.2f} {s.yield_rate:>8.4f} {s.stock:>6}")
        print("-----------------------------")

    def get_sample_menu_choice(self) -> str:
        return input("선택 > ")
