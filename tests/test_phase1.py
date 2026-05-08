"""
Phase 1 검증 스크립트 — 패키지 뼈대 구조 확인
실행: python tests/test_phase1.py  (프로젝트 루트에서)
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트를 sys.path에 추가 (tests/ 하위에서 실행해도 패키지를 찾을 수 있도록)
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


def test_directories_exist():
    for d in ["model", "controller", "view"]:
        check(os.path.isdir(d), f"디렉토리 존재: {d}/")


def test_init_files_exist():
    required = [
        "model/__init__.py",
        "controller/__init__.py",
        "view/__init__.py",
    ]
    for f in required:
        check(os.path.isfile(f), f"파일 존재: {f}")


def test_main_py_exists():
    check(os.path.isfile("main.py"), "파일 존재: main.py")


def test_packages_importable():
    try:
        import model
        import controller
        import view
        check(True, "패키지 import 성공: model, controller, view")
    except ImportError as e:
        check(False, f"패키지 import 실패: {e}")


def test_main_py_has_entry_point():
    if not os.path.isfile("main.py"):
        check(False, "main.py 없음 — 진입점 확인 불가")
        return
    with open("main.py", encoding="utf-8") as f:
        content = f.read()
    check('if __name__ == "__main__"' in content, 'main.py에 __main__ 진입점 존재')
    check("def main():" in content, "main.py에 main() 함수 정의 존재")


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 1 검증 — 패키지 뼈대 구조")
    print("=" * 50)

    test_directories_exist()
    test_init_files_exist()
    test_main_py_exists()
    test_packages_importable()
    test_main_py_has_entry_point()

    print("-" * 50)
    if _failures:
        print(f"결과: {len(_failures)}개 실패")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("✓ Phase 1 검증 완료 — 모든 항목 통과")
