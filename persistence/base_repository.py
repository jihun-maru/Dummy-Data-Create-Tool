from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseRepository(ABC):
    def __init__(self, file_path: str) -> None:
        self._path = Path(file_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def save_all(self, entities: list) -> None:
        """엔티티 목록 전체를 파일에 덮어씌워 저장한다."""

    @abstractmethod
    def load_all(self) -> list:
        """파일에서 엔티티 목록 전체를 읽어 반환한다."""

    def _read_json(self) -> Any:
        """파일이 없으면 None을 반환하고, 있으면 파싱된 Python 객체를 반환한다."""
        if not self._path.exists():
            return None
        with open(self._path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, data: Any) -> None:
        """data를 들여쓰기 2칸 JSON으로 파일에 쓴다."""
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
