"""
Phase 7 검증 스크립트 — persistence/ 패키지 뼈대 및 BaseRepository
실행: python tests/test_phase7.py  (프로젝트 루트에서)
"""
import ast
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


# ──────────────────────────────────────────────────────────────
# 1. 파일 구조 확인
# ──────────────────────────────────────────────────────────────
def test_persistence_structure():
    check(os.path.isdir("persistence"), "디렉토리 존재: persistence/")
    check(os.path.isfile("persistence/__init__.py"), "파일 존재: persistence/__init__.py")
    check(os.path.isfile("persistence/base_repository.py"), "파일 존재: persistence/base_repository.py")


# ──────────────────────────────────────────────────────────────
# 2. import 및 추상 클래스 구조 확인
# ──────────────────────────────────────────────────────────────
def test_base_repository_import():
    try:
        from persistence.base_repository import BaseRepository
        check(True, "BaseRepository import 성공")
    except ImportError as e:
        check(False, f"BaseRepository import 실패: {e}")
        return

    import abc
    check(issubclass(BaseRepository, abc.ABC), "BaseRepository는 ABC 상속")

    abstract_methods = getattr(BaseRepository, "__abstractmethods__", set())
    check("save_all" in abstract_methods, "save_all이 @abstractmethod 선언")
    check("load_all" in abstract_methods, "load_all이 @abstractmethod 선언")

    check(hasattr(BaseRepository, "_read_json"), "_read_json 메서드 존재")
    check(hasattr(BaseRepository, "_write_json"), "_write_json 메서드 존재")

    import inspect
    sig = inspect.signature(BaseRepository.__init__)
    check("file_path" in sig.parameters, "__init__에 file_path 파라미터 존재")


# ──────────────────────────────────────────────────────────────
# 3. 동작 검증 — 임시 디렉토리 사용
# ──────────────────────────────────────────────────────────────
def test_base_repository_behavior():
    try:
        from persistence.base_repository import BaseRepository

        # 테스트용 구체 클래스
        class _ConcreteRepo(BaseRepository):
            def save_all(self, entities: list) -> None:
                pass
            def load_all(self) -> list:
                return []

        tmp = tempfile.mkdtemp()
        try:
            nested_path = os.path.join(tmp, "sub", "test.json")
            repo = _ConcreteRepo(nested_path)
            check(
                os.path.isdir(os.path.join(tmp, "sub")),
                "생성자 호출 시 parent 디렉토리 자동 생성",
            )

            # 파일 없을 때 _read_json → None
            result = repo._read_json()
            check(result is None, "_read_json: 파일 없으면 None 반환")

            # 리스트 라운드트립
            repo._write_json([{"id": "X01", "value": 42}])
            loaded = repo._read_json()
            check(loaded == [{"id": "X01", "value": 42}], "_write_json → _read_json 리스트 라운드트립")

            # 딕트 라운드트립 (ProductionRepository 대응)
            repo._write_json({"current_job": None, "queue": []})
            loaded2 = repo._read_json()
            check(
                isinstance(loaded2, dict) and loaded2.get("queue") == [],
                "_write_json → _read_json 딕셔너리 라운드트립",
            )

            # 덮어쓰기
            repo._write_json([{"id": "X02"}])
            overwritten = repo._read_json()
            check(
                overwritten == [{"id": "X02"}],
                "_write_json: 기존 파일 덮어쓰기 정상",
            )
        finally:
            shutil.rmtree(tmp)
    except Exception as e:
        check(False, f"BaseRepository 동작 테스트 오류: {e}")


# ──────────────────────────────────────────────────────────────
# 4. AST 검사 — persistence/base_repository.py에 print/input 없음
# ──────────────────────────────────────────────────────────────
def test_no_print_input_in_base():
    filepath = "persistence/base_repository.py"
    if not os.path.isfile(filepath):
        check(False, f"{filepath} 파일 없음 — AST 검사 불가")
        return
    try:
        with open(filepath, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        violations = [
            f"line {n.lineno}: {n.func.id}()"
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id in ("print", "input")
        ]
        check(
            len(violations) == 0,
            f"{filepath}: print/input 없음"
            if not violations
            else f"{filepath}: 금지 호출 발견 → {violations}",
        )
    except Exception as e:
        check(False, f"{filepath} AST 분석 실패: {e}")


# ──────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("Phase 7 검증 — persistence/ 뼈대 및 BaseRepository")
    print("=" * 50)

    test_persistence_structure()
    test_base_repository_import()
    test_base_repository_behavior()
    test_no_print_input_in_base()

    print("-" * 50)
    if _failures:
        print(f"결과: {len(_failures)}개 실패")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("✓ Phase 7 검증 완료 — 모든 항목 통과")
