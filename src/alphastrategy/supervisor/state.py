from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SupervisorState(str, Enum):
    STARTING = "starting"
    IDLE_OUT_OF_SESSION = "idle_out_of_session"
    IDLE_IN_SESSION = "idle_in_session"
    REBALANCING = "rebalancing"
    HALTED = "halted"
    FLATTENING = "flattening"
    STOPPED = "stopped"


@dataclass
class SupervisorSnapshot:
    state: SupervisorState = SupervisorState.STARTING
    last_rebalance_event: str | None = None
    sleeves: dict[str, float] = field(default_factory=dict)
    halt_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["state"] = self.state.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SupervisorSnapshot:
        state_raw = payload.get("state", SupervisorState.STARTING.value)
        return cls(
            state=SupervisorState(state_raw),
            last_rebalance_event=payload.get("last_rebalance_event"),
            sleeves=dict(payload.get("sleeves") or {}),
            halt_reason=payload.get("halt_reason"),
        )


def load_state(path: Path | str) -> SupervisorSnapshot:
    state_path = Path(path)
    if not state_path.exists():
        return SupervisorSnapshot()
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    return SupervisorSnapshot.from_dict(payload)


def save_state(path: Path | str, snapshot: SupervisorSnapshot) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(snapshot.to_dict(), separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
