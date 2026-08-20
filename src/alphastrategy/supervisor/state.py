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
    prime_clock_after_resume: bool = False
    last_combined: dict[str, float] = field(default_factory=dict)
    last_sleeve_weights: dict[str, dict[str, float]] = field(default_factory=dict)
    last_sleeve_contribution: dict[str, dict[str, float]] = field(default_factory=dict)
    last_prices: dict[str, float] = field(default_factory=dict)
    stopped: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["state"] = self.state.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SupervisorSnapshot:
        state_raw = payload.get("state", SupervisorState.STARTING.value)
        raw_weights = payload.get("last_sleeve_weights") or {}
        last_sleeve_weights = {
            str(bundle_id): {str(asset): float(weight) for asset, weight in weights.items()}
            for bundle_id, weights in raw_weights.items()
            if isinstance(weights, dict)
        }
        raw_contrib = payload.get("last_sleeve_contribution") or {}
        last_sleeve_contribution = {
            str(bundle_id): {str(asset): float(weight) for asset, weight in weights.items()}
            for bundle_id, weights in raw_contrib.items()
            if isinstance(weights, dict)
        }
        return cls(
            state=SupervisorState(state_raw),
            last_rebalance_event=payload.get("last_rebalance_event"),
            sleeves=dict(payload.get("sleeves") or {}),
            halt_reason=payload.get("halt_reason"),
            prime_clock_after_resume=bool(payload.get("prime_clock_after_resume", False)),
            last_combined={
                str(asset): float(weight)
                for asset, weight in (payload.get("last_combined") or {}).items()
            },
            last_sleeve_weights=last_sleeve_weights,
            last_sleeve_contribution=last_sleeve_contribution,
            last_prices={
                str(asset): float(price)
                for asset, price in (payload.get("last_prices") or {}).items()
            },
            stopped=[str(bundle_id) for bundle_id in (payload.get("stopped") or [])],
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
