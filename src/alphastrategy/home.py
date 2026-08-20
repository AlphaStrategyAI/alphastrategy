from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class AlphaStrategyHome:
    root: Path

    @classmethod
    def from_env(cls, env: dict | None = None) -> "AlphaStrategyHome":
        e = os.environ if env is None else env
        raw = e.get("ALPHASTRATEGY_HOME") or str(Path.home() / ".alphastrategy")
        return cls(root=Path(raw))

    def imported_dir(self) -> Path:
        return self.root / "imported"

    def bundle_dir(self, bundle_id: str) -> Path:
        return self.imported_dir() / bundle_id

    def runtime_path(self) -> Path:
        return self.root / "runtime.yaml"

    def audit_path(self) -> Path:
        return self.root / "audit.jsonl"

    def state_path(self) -> Path:
        return self.root / "supervisor-state.json"
