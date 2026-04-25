from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonStore:
    """Small JSON-backed storage helper with startup file bootstrap."""

    def __init__(self, base_dir: Path, file_map: dict[str, str]) -> None:
        self.base_dir = base_dir
        self.file_map = file_map

    def path_for(self, name: str) -> Path:
        if name not in self.file_map:
            raise KeyError(f'Unknown collection: {name}')
        return self.base_dir / self.file_map[name]

    def ensure_files(self) -> None:
        for name, filename in self.file_map.items():
            path = self.base_dir / filename
            if not path.exists():
                path.write_text('[]\n', encoding='utf-8')
            try:
                payload = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(payload, list):
                    raise ValueError(f'{name} must contain a JSON list')
            except json.JSONDecodeError as exc:
                raise ValueError(f'{name} contains invalid JSON') from exc

    def read(self, name: str) -> list[dict[str, Any]]:
        path = self.path_for(name)
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding='utf-8'))

    def write(self, name: str, rows: list[dict[str, Any]]) -> None:
        path = self.path_for(name)
        path.write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
