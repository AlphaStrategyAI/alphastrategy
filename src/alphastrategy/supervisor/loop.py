from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import yaml

from alphastrategy.bundle.schema import load_risk_envelope

from alphastrategy.errors import FlattenRequested, HaltRequested, IllegalWeights
from alphastrategy.home import AlphaStrategyHome
from alphastrategy.risk.check import check_book
from alphastrategy.risk.policy import AccountPolicy, merge_limits, tighten_policy
from alphastrategy.supervisor import audit
from alphastrategy.supervisor.clock import ClockSnapshot, next_rebalance_event
from alphastrategy.supervisor.combine import combine
from alphastrategy.supervisor.orders import plan_orders
from alphastrategy.supervisor.state import (
    SupervisorSnapshot,
    SupervisorState,
    load_state,
    save_state,
)


def _parse_clock_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def _clock_snapshot(clock: dict[str, Any]) -> ClockSnapshot:
    now = _parse_clock_dt(clock.get("timestamp") or clock.get("now"))
    return ClockSnapshot(
        is_open=bool(clock.get("is_open", False)),
        next_open=_parse_clock_dt(clock["next_open"]),
        next_close=_parse_clock_dt(clock["next_close"]),
        now=now,
    )


def _last_bar_close(symbol_data: Any) -> float | None:
    if isinstance(symbol_data, (int, float)):
        return float(symbol_data)
    if isinstance(symbol_data, dict):
        if "bars" in symbol_data:
            bars = symbol_data.get("bars") or []
            if not bars:
                return None
            last = bars[-1]
            if isinstance(last, dict) and "c" in last:
                return float(last["c"])
        if "c" in symbol_data:
            return float(symbol_data["c"])
    return None


def _positions_map(positions: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for pos in positions:
        symbol = str(pos.get("symbol", ""))
        if not symbol:
            continue
        out[symbol] = float(pos.get("qty", 0))
    return out


class Supervisor:
    def __init__(
        self,
        home: AlphaStrategyHome,
        broker: Any,
        policy: AccountPolicy | None = None,
        evaluators: dict[str, dict[str, float]] | None = None,
        weight_fn: Callable[[str], dict[str, float]] | None = None,
    ) -> None:
        self._home = home
        self._broker = broker
        self._policy = policy or AccountPolicy.defaults()
        self._evaluators = evaluators or {}
        self._weight_fn = weight_fn
        self._prev_clock: ClockSnapshot | None = None
        self._lock = threading.RLock()
        self._snapshot = load_state(home.state_path())
        if self._snapshot.state == SupervisorState.STARTING:
            self._snapshot.state = SupervisorState.IDLE_OUT_OF_SESSION

    @property
    def state(self) -> SupervisorState:
        return self._snapshot.state

    @property
    def last_rebalance_event(self) -> str | None:
        return self._snapshot.last_rebalance_event

    @property
    def snapshot(self) -> SupervisorSnapshot:
        return self._snapshot

    @property
    def policy(self) -> AccountPolicy:
        return self._policy

    @property
    def broker(self) -> Any:
        return self._broker

    def set_policy(self, overlay: dict) -> None:
        """Apply a tighten-only overlay patch to the account policy."""
        with self._lock:
            self._policy = merge_limits({}, self._policy, overlay)

    def reload_from_disk(self) -> None:
        """Reload persisted snapshot from disk without reconstructing the broker."""
        with self._lock:
            self._snapshot = load_state(self._home.state_path())
            if self._snapshot.state == SupervisorState.STARTING:
                self._snapshot.state = SupervisorState.IDLE_OUT_OF_SESSION

    def _persist(self) -> None:
        save_state(self._home.state_path(), self._snapshot)

    def _audit(self, event: str, **payload: Any) -> None:
        audit.append(self._home.audit_path(), {"event": event, **payload})

    def start_sleeve(self, bundle_id: str, allocation: float) -> None:
        with self._lock:
            if allocation < 0:
                raise ValueError("allocation must be >= 0")
            other_total = sum(
                alloc
                for bid, alloc in self._snapshot.sleeves.items()
                if bid != bundle_id
            )
            total = other_total + allocation
            if total > 1.0:
                raise ValueError("allocation sum must be <= 1.0")
            self._snapshot.sleeves[bundle_id] = allocation
            self._audit("paper_start", bundle_id=bundle_id, allocation=allocation)
            self._persist()

    def stop_sleeve(self, bundle_id: str) -> None:
        with self._lock:
            if bundle_id in self._snapshot.sleeves:
                self._snapshot.sleeves[bundle_id] = 0.0
                self._audit("paper_stop", bundle_id=bundle_id)
                self._persist()

    def kill_sleeve(self, bundle_id: str) -> None:
        with self._lock:
            if bundle_id not in self._snapshot.sleeves:
                return
            self._snapshot.sleeves[bundle_id] = 0.0
            self._flatten_account()
            self._audit("kill", bundle_id=bundle_id)
            self._persist()

    def kill_account(self) -> None:
        with self._lock:
            self._flatten_account()
            self._audit("kill", scope="account")
            self._persist()

    def resume(self) -> None:
        with self._lock:
            if self._snapshot.state != SupervisorState.HALTED:
                return
            self._snapshot.halt_reason = None
            self._audit("resume")
            try:
                clock_raw = self._broker.get_clock()
                cur = _clock_snapshot(clock_raw)
                self._set_idle_state(cur)
            except Exception:
                self._snapshot.state = SupervisorState.IDLE_OUT_OF_SESSION
            self._persist()

    def tick(self) -> None:
        with self._lock:
            self.reload_from_disk()
            if self._snapshot.state in (SupervisorState.STOPPED, SupervisorState.FLATTENING):
                return
            if self._snapshot.state == SupervisorState.HALTED:
                return

            try:
                clock_raw = self._broker.get_clock()
            except Exception as exc:
                self._halt(f"broker get_clock failed: {exc}")
                return

            cur = _clock_snapshot(clock_raw)

            try:
                self._heartbeat_health_check()
            except HaltRequested as exc:
                self._halt(str(exc))
                self._update_prev_clock(cur, None)
                return
            except Exception as exc:
                self._halt(str(exc))
                self._update_prev_clock(cur, None)
                return

            event = next_rebalance_event(
                self._prev_clock,
                cur,
                self._snapshot.last_rebalance_event,
            )

            if event is None:
                self._set_idle_state(cur)
                self._update_prev_clock(cur, None)
                self._persist()
                return

            if event in ("open", "close"):
                try:
                    self._rebalance(cur, event)
                except HaltRequested as exc:
                    self._halt(str(exc))
                except IllegalWeights as exc:
                    self._halt(str(exc))
                except FlattenRequested:
                    self._flatten_account()
                except Exception as exc:
                    self._halt(str(exc))
                finally:
                    self._update_prev_clock(cur, event)
                    self._persist()

    def _heartbeat_health_check(self) -> None:
        symbols: set[str] = set()
        for bundle_id, allocation in self._snapshot.sleeves.items():
            if allocation <= 0:
                continue
            weights = self._sleeve_weights(bundle_id)
            symbols.update(weights.keys())
        if not symbols:
            return
        self._fetch_prices(symbols)

    def _set_idle_state(self, cur: ClockSnapshot) -> None:
        if self._snapshot.state == SupervisorState.HALTED:
            return
        self._snapshot.state = (
            SupervisorState.IDLE_IN_SESSION
            if cur.is_open
            else SupervisorState.IDLE_OUT_OF_SESSION
        )

    def _update_prev_clock(
        self,
        cur: ClockSnapshot,
        event: str | None,
    ) -> None:
        session_date = cur.next_close.date().isoformat()
        open_key = f"{session_date}:open"
        if event == "open" or self._snapshot.last_rebalance_event == open_key:
            self._prev_clock = cur
        elif not cur.is_open:
            self._prev_clock = cur

    def _sleeve_weights(self, bundle_id: str) -> dict[str, float]:
        if self._weight_fn is not None:
            return self._weight_fn(bundle_id)
        if bundle_id in self._evaluators:
            return dict(self._evaluators[bundle_id])
        raise HaltRequested(f"no evaluator for sleeve {bundle_id}")

    def _collect_sleeves(self) -> list[tuple[float, dict[str, float]]]:
        sleeves: list[tuple[float, dict[str, float]]] = []
        for bundle_id, allocation in self._snapshot.sleeves.items():
            if allocation <= 0:
                continue
            weights = self._sleeve_weights(bundle_id)
            self._validate_weights(weights)
            sleeves.append((allocation, weights))
        return sleeves

    def _validate_weights(self, weights: dict[str, float]) -> None:
        if not weights:
            raise HaltRequested("empty weights")
        if any(w < 0 for w in weights.values()):
            raise IllegalWeights("negative weight")
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-5:
            raise IllegalWeights(f"weights sum to {total}, expected 1.0")

    def _read_runtime(self) -> dict[str, Any]:
        path = self._home.runtime_path()
        if not path.is_file():
            return {}
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}

    def _bundle_envelope(self, bundle_id: str) -> dict[str, Any]:
        envelope_path = self._home.bundle_dir(bundle_id) / "risk-envelope.yaml"
        if not envelope_path.is_file():
            return {}
        return load_risk_envelope(envelope_path.read_bytes())

    def _effective_sleeve_policy(self, bundle_id: str) -> AccountPolicy:
        runtime = self._read_runtime()
        sleeve_overlays = runtime.get("sleeve_overlays", {})
        overlay = sleeve_overlays.get(bundle_id) if isinstance(sleeve_overlays, dict) else None
        envelope = self._bundle_envelope(bundle_id)
        return merge_limits(envelope, self._policy, overlay)

    def _rebalance_policy(self) -> AccountPolicy:
        policy = self._policy
        for bundle_id, allocation in self._snapshot.sleeves.items():
            if allocation <= 0:
                continue
            policy = tighten_policy(policy, self._effective_sleeve_policy(bundle_id))
        return policy

    def _equity(self) -> float:
        account = self._broker.get_account()
        return float(account.get("equity", 0))

    def _fetch_prices(self, symbols: set[str]) -> dict[str, float]:
        if not symbols:
            return {}
        end = datetime.now(timezone.utc).date().isoformat()
        start = (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat()
        try:
            bars = self._broker.get_bars(sorted(symbols), start, end)
        except Exception as exc:
            raise HaltRequested(f"broker get_bars failed: {exc}") from exc
        prices: dict[str, float] = {}
        for symbol in symbols:
            price = _last_bar_close(bars.get(symbol))
            if price is None:
                raise HaltRequested(f"missing price for {symbol}")
            prices[symbol] = price
        return prices

    def _rebalance(self, cur: ClockSnapshot, event: str) -> None:
        sleeves = self._collect_sleeves()
        if not sleeves:
            session_date = cur.next_close.date().isoformat()
            self._snapshot.last_rebalance_event = f"{session_date}:{event}"
            self._set_idle_state(cur)
            return

        self._snapshot.state = SupervisorState.REBALANCING
        combined = combine(sleeves)
        equity = self._equity()
        rebalance_policy = self._rebalance_policy()
        check_book(combined, equity, rebalance_policy)

        positions = _positions_map(self._broker.list_positions())
        symbols = set(combined) | set(positions)
        prices = self._fetch_prices(symbols)
        plans = plan_orders(combined, positions, prices, equity, rebalance_policy)

        for plan in plans:
            self._broker.place_order(plan.symbol, plan.qty, plan.side)
            self._audit(
                "order",
                symbol=plan.symbol,
                qty=plan.qty,
                side=plan.side,
            )

        session_date = cur.next_close.date().isoformat()
        self._snapshot.last_rebalance_event = f"{session_date}:{event}"
        self._audit("rebalance", event=event, orders=len(plans))
        self._set_idle_state(cur)

    def _halt(self, reason: str) -> None:
        self._snapshot.state = SupervisorState.HALTED
        self._snapshot.halt_reason = reason
        self._audit("halt", reason=reason)
        self._persist()

    def _flatten_account(self) -> None:
        self._snapshot.state = SupervisorState.FLATTENING
        self._persist()
        try:
            self._broker.close_all()
        except Exception as exc:
            self._halt(f"flatten close_all failed: {exc}")
            return
        self._snapshot.state = SupervisorState.STOPPED
        self._audit("flatten", scope="account")
