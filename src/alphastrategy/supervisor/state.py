from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from alphastrategy.persist import replace_text


class SupervisorState(str, Enum):
    STARTING = "starting"
    IDLE_OUT_OF_SESSION = "idle_out_of_session"
    IDLE_IN_SESSION = "idle_in_session"
    REBALANCING = "rebalancing"
    HALTED = "halted"
    FLATTENING = "flattening"
    STOPPED = "stopped"


@dataclass(frozen=True)
class KillOutcome:
    isolated: bool
    flattened: bool
    scope: str
    reason: str
    bundle_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "isolated": self.isolated,
            "flattened": self.flattened,
            "scope": self.scope,
            "reason": self.reason,
            "bundle_id": self.bundle_id,
        }


def _kill_from_payload(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    return {
        "isolated": bool(raw.get("isolated")),
        "flattened": bool(raw.get("flattened")),
        "scope": str(raw.get("scope") or "none"),
        "reason": str(raw.get("reason") or ""),
        "bundle_id": (
            None if raw.get("bundle_id") in (None, "") else str(raw.get("bundle_id"))
        ),
    }


@dataclass
class SupervisorSnapshot:
    state: SupervisorState = SupervisorState.STARTING
    last_rebalance_event: str | None = None
    last_rebalance_complete: bool = True
    sleeves: dict[str, float] = field(default_factory=dict)
    halt_reason: str | None = None
    prime_clock_after_resume: bool = False
    last_combined: dict[str, float] = field(default_factory=dict)
    last_sleeve_weights: dict[str, dict[str, float]] = field(default_factory=dict)
    last_sleeve_contribution: dict[str, dict[str, float]] = field(default_factory=dict)
    last_prices: dict[str, float] = field(default_factory=dict)
    stopped: list[str] = field(default_factory=list)
    orders_date: str | None = None
    orders_today: int = 0
    last_got: dict[str, float] = field(default_factory=dict)
    last_fill_got: dict[str, float] = field(default_factory=dict)
    last_kill: dict[str, Any] | None = None
    last_heartbeat_at: str | None = None
    rebalance_placed: int = 0
    isolate_in_flight: str | None = None

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
            last_rebalance_complete=bool(payload.get("last_rebalance_complete", True)),
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
            orders_date=payload.get("orders_date"),
            orders_today=int(payload.get("orders_today") or 0),
            last_got={
                str(asset): float(weight)
                for asset, weight in (payload.get("last_got") or {}).items()
            },
            last_fill_got={
                str(asset): float(weight)
                for asset, weight in (payload.get("last_fill_got") or {}).items()
            },
            last_kill=_kill_from_payload(payload.get("last_kill")),
            last_heartbeat_at=(
                None
                if payload.get("last_heartbeat_at") in (None, "")
                else str(payload.get("last_heartbeat_at"))
            ),
            rebalance_placed=int(payload.get("rebalance_placed") or 0),
            isolate_in_flight=(
                None
                if payload.get("isolate_in_flight") in (None, "")
                else str(payload.get("isolate_in_flight"))
            ),
        )


def load_state(path: Path | str) -> SupervisorSnapshot:
    state_path = Path(path)
    if not state_path.exists():
        return SupervisorSnapshot()
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    return SupervisorSnapshot.from_dict(payload)


def save_state(path: Path | str, snapshot: SupervisorSnapshot) -> None:
    payload = json.dumps(snapshot.to_dict(), separators=(",", ":"), sort_keys=True) + "\n"
    replace_text(path, payload, prefix=".state.")
