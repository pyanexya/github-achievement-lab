from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class State:
    path: Path = Path(".achievement-unlocker-state.json")
    data: dict[str, Any] = field(default_factory=lambda: {"version": 1, "operations": {}})

    @classmethod
    def load(cls, path: Path | None = None) -> State:
        chosen = path or Path(".achievement-unlocker-state.json")
        if not chosen.exists():
            return cls(path=chosen)
        loaded = json.loads(chosen.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict) or loaded.get("version") != 1:
            raise RuntimeError(f"Unsupported state file: {chosen}")
        return cls(path=chosen, data=loaded)

    def save(self) -> None:
        self.path.write_text(
            json.dumps(self.data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def record(self, key: str, **values: Any) -> None:
        operations = self.data.setdefault("operations", {})
        current = operations.setdefault(key, {})
        current.update(values)
        self.save()

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()

