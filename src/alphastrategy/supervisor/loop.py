from __future__ import annotations

import copy
import hashlib
import math
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from alphastrategy.bundle.schema import load_risk_envelope

from alphastrategy.errors import FlattenRequested, HaltRequested, IllegalWeights
from alphastrategy.home import AlphaStrategyHome
from alphastrategy.persist import discard_stale, replace_text
from alphastrategy.risk.check import check_book
from alphastrategy.risk.policy import AccountPolicy, merge_limits, tighten_policy
from alphastrategy.supervisor import audit
from alphastrategy.supervisor.clock import ClockSnapshot, next_rebalance_event
from alphastrategy.supervisor.combine import combine
from alphastrategy.supervisor.orders import deviations_after, plan_orders
from alphastrategy.supervisor.residual import residual_book
from alphastrategy.supervisor.state import (
    KillOutcome,
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


def _last_bar_timestamp(symbol_data: Any) -> datetime | None:
    if not isinstance(symbol_data, dict):
        return None
    bars = symbol_data.get("bars")
    if isinstance(bars, list) and bars:
        last = bars[-1]
        if isinstance(last, dict):
            timestamp = last.get("t") or last.get("timestamp")
            if timestamp:
                return _parse_clock_dt(timestamp)
    timestamp = symbol_data.get("t") or symbol_data.get("timestamp")
    return _parse_clock_dt(timestamp) if timestamp else None


def _positions_map(positions: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for pos in positions:
        symbol = str(pos.get("symbol", ""))
        if not symbol:
            continue
        out[symbol] = float(pos.get("qty", 0))
    return out


class Supervisor:
    LIVE_BOOK_TTL_SEC = 1.0

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
        discard_stale(home.root)
        self._snapshot = load_state(home.state_path())
        if self._snapshot.state == SupervisorState.STARTING:
            self._snapshot.state = SupervisorState.IDLE_OUT_OF_SESSION
        self._recover_interrupted_rebalance()
        self._recover_interrupted_flatten()
        self._recover_interrupted_isolate()
        self._spoken_cache: tuple[tuple, AccountPolicy] | None = None
        self._live_book_cache: (
            tuple[float, dict[str, Any], list[dict[str, Any]], bool] | None
        ) = None
        self._runtime_doc_cache: tuple[str, dict[str, Any]] | None = None
        self._envelope_cache: dict[str, tuple[str, dict[str, Any]]] = {}

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
            self._enforce_live_book()

    def enforce_live_book(self) -> None:
        with self._lock:
            self._enforce_live_book()

    def _live_book_unlocked(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        now = time.monotonic()
        cached = self._live_book_cache
        if cached is not None and (
            cached[3] or (now - cached[0]) < self.LIVE_BOOK_TTL_SEC
        ):
            return cached[1], cached[2]
        account = self._broker.get_account()
        positions = self._broker.list_positions()
        self._live_book_cache = (now, account, positions, False)
        return account, positions

    def _priced_live_weights(
        self, equity: float, raw_positions: list[dict[str, Any]]
    ) -> dict[str, float]:
        positions = _positions_map(raw_positions)
        prices = dict(self._snapshot.last_prices)
        if equity > 0 and prices:
            got = {
                symbol: (qty * prices[symbol]) / equity
                for symbol, qty in positions.items()
                if symbol in prices
            }
            if got:
                return got
        return {}

    def _live_book_weights(
        self, equity: float, raw_positions: list[dict[str, Any]]
    ) -> dict[str, float]:
        priced = self._priced_live_weights(equity, raw_positions)
        if priced:
            return priced
        if self._snapshot.last_got:
            return dict(self._snapshot.last_got)
        return dict(self._snapshot.last_combined)

    def live_cap_weights(
        self, equity: float, raw_positions: list[dict[str, Any]]
    ) -> dict[str, float]:
        with self._lock:
            priced = self._priced_live_weights(equity, raw_positions)
            if priced:
                return priced
            if self._snapshot.last_got:
                return dict(self._snapshot.last_got)
            return {}

    def _enforce_live_book(
        self,
        account: dict[str, Any] | None = None,
        positions: list[dict[str, Any]] | None = None,
    ) -> None:
        if self._broker is None:
            return
        if self._snapshot.state in (
            SupervisorState.FLATTENING,
            SupervisorState.STOPPED,
        ):
            return
        try:
            if account is None or positions is None:
                account, positions = self._live_book_unlocked()
            equity = float(account.get("equity", 0))
            weights = self._live_book_weights(equity, positions)
        except Exception as exc:
            self._halt(f"tighten live book: {exc}")
            return
        try:
            check_book(weights, equity, self._rebalance_policy())
        except FlattenRequested as exc:
            reason = exc.reason or "limit"
            self._flatten_account(reason=reason)
            self._record_kill(
                KillOutcome(
                    isolated=False,
                    flattened=True,
                    scope="account",
                    reason=reason,
                    bundle_id=None,
                )
            )

    def reload_from_disk(self) -> None:
        """Reload persisted snapshot from disk without reconstructing the broker."""
        with self._lock:
            self._snapshot = load_state(self._home.state_path())
            if self._snapshot.state == SupervisorState.STARTING:
                self._snapshot.state = SupervisorState.IDLE_OUT_OF_SESSION
            self._recover_interrupted_rebalance()
            self._recover_interrupted_flatten()
            self._recover_interrupted_isolate()

    def _persist(self) -> None:
        save_state(self._home.state_path(), self._snapshot)

    def _audit(self, event: str, **payload: Any) -> None:
        audit.append(self._home.audit_path(), {"event": event, **payload})

    def _record_kill(self, outcome: KillOutcome) -> KillOutcome:
        self._snapshot.last_kill = outcome.to_dict()
        self._persist()
        return outcome

    def start_sleeve(self, bundle_id: str, allocation: float) -> bool:
        with self._lock:
            if not self._home.bundle_dir(bundle_id).is_dir():
                raise ValueError(f"bundle is not imported: {bundle_id}")
            if not math.isfinite(allocation) or not 0.0 <= allocation <= 1.0:
                raise ValueError("allocation must be finite and between 0 and 1")
            other_total = sum(
                alloc
                for bid, alloc in self._snapshot.sleeves.items()
                if bid != bundle_id
            )
            total = other_total + allocation
            if total > 1.0:
                raise ValueError("allocation sum must be <= 1.0")
            if self._snapshot.state == SupervisorState.STOPPED:
                self._snapshot.prime_clock_after_resume = True
                try:
                    clock_raw = self._broker.get_clock()
                    cur = _clock_snapshot(clock_raw)
                    self._prev_clock = cur
                    self._snapshot.state = (
                        SupervisorState.IDLE_IN_SESSION
                        if cur.is_open
                        else SupervisorState.IDLE_OUT_OF_SESSION
                    )
                except Exception:
                    self._snapshot.state = SupervisorState.IDLE_OUT_OF_SESSION
            self._snapshot.sleeves[bundle_id] = allocation
            self._snapshot.stopped = [
                item for item in self._snapshot.stopped if item != bundle_id
            ]
            self._audit("paper_start", bundle_id=bundle_id, allocation=allocation)
            self._seed_last_sleeve_weights(bundle_id, allocation)
            self._persist()
            self._enforce_live_book()
            return self._snapshot.state == SupervisorState.HALTED

    def stop_sleeve(self, bundle_id: str) -> None:
        with self._lock:
            if bundle_id not in self._snapshot.sleeves:
                return
            self._snapshot.sleeves[bundle_id] = 0.0
            if bundle_id not in self._snapshot.stopped:
                self._snapshot.stopped.append(bundle_id)
            self._audit("paper_stop", bundle_id=bundle_id)
            self._persist()

    def kill_sleeve(self, bundle_id: str) -> KillOutcome:
        with self._lock:
            if bundle_id not in self._snapshot.sleeves:
                return self._record_kill(
                    KillOutcome(
                        isolated=False,
                        flattened=False,
                        scope="none",
                        reason="unknown_sleeve",
                        bundle_id=bundle_id,
                    )
                )
            self._snapshot.sleeves[bundle_id] = 0.0
            if bundle_id not in self._snapshot.stopped:
                self._snapshot.stopped.append(bundle_id)
            if self._isolation_ready(bundle_id):
                try:
                    self._isolate_sleeve(bundle_id)
                    self._audit("kill", bundle_id=bundle_id, isolated=True)
                    return self._record_kill(
                        KillOutcome(
                            isolated=True,
                            flattened=False,
                            scope="sleeve",
                            reason="isolated",
                            bundle_id=bundle_id,
                        )
                    )
                except Exception:
                    self._flatten_account()
                    self._audit("kill", bundle_id=bundle_id, isolated=False)
                    return self._record_kill(
                        KillOutcome(
                            isolated=False,
                            flattened=True,
                            scope="account",
                            reason="fallback_error",
                            bundle_id=bundle_id,
                        )
                    )
            self._flatten_account()
            self._audit("kill", bundle_id=bundle_id, isolated=False)
            return self._record_kill(
                KillOutcome(
                    isolated=False,
                    flattened=True,
                    scope="account",
                    reason="fallback_not_ready",
                    bundle_id=bundle_id,
                )
            )

    def _isolation_ready(self, bundle_id: str) -> bool:
        contribution = self._snapshot.last_sleeve_contribution.get(bundle_id) or {}
        combined = self._snapshot.last_combined
        prices = self._snapshot.last_prices
        if not contribution or not combined or not prices:
            return False
        try:
            clock = self._broker.get_clock()
        except Exception:
            return False
        if not clock.get("is_open"):
            return False
        symbols = (
            set(_positions_map(self._broker.list_positions()))
            | set(combined)
            | set(contribution)
        )
        return all(symbol in prices for symbol in symbols)

    def _isolate_sleeve(self, bundle_id: str) -> None:
        self._snapshot.isolate_in_flight = bundle_id
        self._persist()
        contribution = dict(self._snapshot.last_sleeve_contribution.get(bundle_id) or {})
        combined = dict(self._snapshot.last_combined)
        prices = dict(self._snapshot.last_prices)
        residual = residual_book(combined, contribution)
        equity = self._equity()
        positions = _positions_map(self._broker.list_positions())
        policy = self._rebalance_policy()
        session_date = None
        try:
            clock = self._broker.get_clock()
            session_date = _parse_clock_dt(clock["next_close"]).date().isoformat()
        except Exception:
            session_date = self._snapshot.orders_date
        already = self._session_order_budget(session_date) if session_date else 0
        self._broker.cancel_open_orders()
        plans = plan_orders(
            residual,
            positions,
            prices,
            equity,
            policy,
            orders_already_today=already,
        )
        placed, place_error = self._place_batch(
            plans, already, extra_audit={"reason": "sleeve_kill"}
        )
        if place_error is not None:
            raise place_error
        self._snapshot.isolate_in_flight = None
        if session_date:
            self._snapshot.orders_date = session_date
        self._snapshot.last_combined = dict(residual)
        self._snapshot.last_sleeve_contribution.pop(bundle_id, None)
        self._snapshot.last_sleeve_weights.pop(bundle_id, None)
        self._persist()

    def kill_account(self) -> KillOutcome:
        with self._lock:
            self._flatten_account()
            self._audit("kill", scope="account")
            return self._record_kill(
                KillOutcome(
                    isolated=False,
                    flattened=True,
                    scope="account",
                    reason="account",
                    bundle_id=None,
                )
            )

    def resume(self) -> None:
        with self._lock:
            if self._snapshot.state != SupervisorState.HALTED:
                return
            self._snapshot.halt_reason = None
            self._snapshot.prime_clock_after_resume = True
            self._audit("resume")
            try:
                clock_raw = self._broker.get_clock()
                cur = _clock_snapshot(clock_raw)
                self._prev_clock = cur
                self._snapshot.state = (
                    SupervisorState.IDLE_IN_SESSION
                    if cur.is_open
                    else SupervisorState.IDLE_OUT_OF_SESSION
                )
            except Exception:
                self._snapshot.state = SupervisorState.IDLE_OUT_OF_SESSION
            self._persist()

    def tick(self) -> None:
        with self._lock:
            self.reload_from_disk()
            self._snapshot.last_heartbeat_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )
            if self._snapshot.state == SupervisorState.STOPPED:
                self._persist()
                return
            if self._snapshot.state == SupervisorState.FLATTENING:
                self._flatten_account()
                self._persist()
                return
            if self._snapshot.state == SupervisorState.HALTED:
                self._persist()
                return

            try:
                clock_raw = self._broker.get_clock()
            except Exception as exc:
                self._halt(f"broker get_clock failed: {exc}")
                return

            cur = _clock_snapshot(clock_raw)
            try:
                self._validate_session(cur)
            except HaltRequested as exc:
                self._halt(str(exc))
                return
            if self._snapshot.prime_clock_after_resume:
                self._prev_clock = cur
                self._snapshot.prime_clock_after_resume = False

            event = next_rebalance_event(
                self._prev_clock,
                cur,
                self._snapshot.last_rebalance_event,
            )

            try:
                self._heartbeat_health_check(cur)
            except HaltRequested as exc:
                self._mark_detected_event(cur, event)
                self._halt(str(exc))
                self._update_prev_clock(cur, None)
                return
            except Exception as exc:
                self._mark_detected_event(cur, event)
                self._halt(str(exc))
                self._update_prev_clock(cur, None)
                return

            if event is None:
                self._set_idle_state(cur)
                self._update_prev_clock(cur, None)
                self._persist()
                self._touch_live_book_cache()
                return

            if event in ("open", "close"):
                try:
                    self._rebalance(cur, event)
                except HaltRequested as exc:
                    self._mark_detected_event(cur, event)
                    self._halt(str(exc))
                except IllegalWeights as exc:
                    self._mark_detected_event(cur, event)
                    self._halt(str(exc))
                except FlattenRequested as exc:
                    reason = exc.reason or "limit"
                    self._flatten_account(reason=reason)
                    self._record_kill(
                        KillOutcome(
                            isolated=False,
                            flattened=True,
                            scope="account",
                            reason=reason,
                            bundle_id=None,
                        )
                    )
                except Exception as exc:
                    self._mark_detected_event(cur, event)
                    self._halt(str(exc))
                finally:
                    self._update_prev_clock(cur, event)
                    self._persist()
                    self._touch_live_book_cache()

    def _validate_session(self, cur: ClockSnapshot) -> None:
        if not cur.is_open:
            return
        now = cur.now
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        else:
            now = now.astimezone(timezone.utc)
        minutes = now.hour * 60 + now.minute
        if now.weekday() >= 5 or not (13 * 60 + 30 <= minutes <= 21 * 60):
            raise HaltRequested(
                f"unexpected open session at {now.isoformat().replace('+00:00', 'Z')}"
            )

    def _mark_detected_event(
        self,
        cur: ClockSnapshot,
        event: str | None,
    ) -> None:
        if event not in ("open", "close"):
            return
        session_date = cur.next_close.date().isoformat()
        self._snapshot.last_rebalance_event = f"{session_date}:{event}"

    def _price_universe(self, positions: dict[str, float]) -> set[str]:
        symbols: set[str] = set()
        for bundle_id, allocation in self._snapshot.sleeves.items():
            if allocation <= 0:
                continue
            symbols.update(self._sleeve_weights(bundle_id).keys())
        symbols.update(self._snapshot.last_combined.keys())
        symbols.update(positions.keys())
        return {
            str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()
        }

    def _heartbeat_health_check(self, cur: ClockSnapshot) -> None:
        try:
            raw_positions = self._broker.list_positions()
            account = self._broker.get_account()
        except Exception as exc:
            raise HaltRequested(f"heartbeat live book: {exc}") from exc
        try:
            positions = _positions_map(raw_positions)
            symbols = self._price_universe(positions)
            if not symbols:
                return
            prices = self._fetch_prices(symbols, now=cur.now if cur.is_open else None)
            equity = float(account.get("equity", 0))
            self._snapshot.last_prices = {
                **self._snapshot.last_prices,
                **{symbol: float(price) for symbol, price in prices.items()},
            }
            if equity > 0:
                self._snapshot.last_got = {
                    symbol: (qty * prices[symbol]) / equity
                    for symbol, qty in positions.items()
                    if symbol in prices and qty != 0.0
                }
        finally:
            self._live_book_cache = (time.monotonic(), account, raw_positions, True)

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

    def _seed_last_sleeve_weights(self, bundle_id: str, allocation: float) -> None:
        if allocation <= 0 or self._broker is None:
            return
        stored = self._snapshot.last_sleeve_weights.get(bundle_id)
        if isinstance(stored, dict) and stored:
            return
        try:
            weights = self._sleeve_weights(bundle_id)
            self._validate_weights(weights)
        except (HaltRequested, IllegalWeights) as exc:
            self._halt(str(exc))
            return
        self._snapshot.last_sleeve_weights[bundle_id] = dict(weights)

    def _collect_sleeves(self) -> list[tuple[str, float, dict[str, float]]]:
        sleeves: list[tuple[str, float, dict[str, float]]] = []
        for bundle_id, allocation in self._snapshot.sleeves.items():
            if allocation <= 0:
                continue
            weights = self._sleeve_weights(bundle_id)
            self._validate_weights(weights)
            implied = {asset: allocation * weight for asset, weight in weights.items()}
            check_book(implied, 0.0, self._effective_sleeve_policy(bundle_id))
            sleeves.append((bundle_id, allocation, weights))
        return sleeves

    def _validate_weights(self, weights: dict[str, float]) -> None:
        if any(not math.isfinite(w) for w in weights.values()):
            raise IllegalWeights("non-finite weight")
        if any(w < 0 for w in weights.values()):
            raise IllegalWeights("negative weight")
        total = sum(weights.values())
        if total > 1.0 + 1e-9:
            raise IllegalWeights(f"weights sum to {total}, exceeds 1.0")

    def _read_runtime(self) -> dict[str, Any]:
        path = self._home.runtime_path()
        if not path.is_file():
            raw = b""
            digest = ""
        else:
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
        cached = self._runtime_doc_cache
        if cached is not None and cached[0] == digest:
            return cached[1]
        if not raw:
            doc: dict[str, Any] = {}
        else:
            loaded = yaml.safe_load(raw.decode("utf-8"))
            doc = loaded if isinstance(loaded, dict) else {}
        self._runtime_doc_cache = (digest, doc)
        return doc

    def _write_runtime(self, runtime: dict[str, Any]) -> None:
        path = self._home.runtime_path()
        replace_text(
            path,
            yaml.safe_dump(runtime, sort_keys=True),
            prefix=".runtime.",
        )

    def apply_risk(
        self,
        account_patch: dict[str, Any] | None,
        sleeves_patch: dict[str, Any] | None,
    ) -> bool:
        with self._lock:
            if account_patch is not None and not isinstance(account_patch, dict):
                raise ValueError("account must be an object")
            if sleeves_patch is not None and not isinstance(sleeves_patch, dict):
                raise ValueError("sleeves must be an object")
            runtime = copy.deepcopy(self._read_runtime())
            account_overlay = runtime.get("account_overlay", {})
            if not isinstance(account_overlay, dict):
                account_overlay = {}
            sleeve_overlays = runtime.get("sleeve_overlays", {})
            if not isinstance(sleeve_overlays, dict):
                sleeve_overlays = {}
            planned_account_overlay = dict(account_overlay)
            planned_sleeve_overlays = {
                bundle_id: dict(overlay)
                for bundle_id, overlay in sleeve_overlays.items()
                if isinstance(overlay, dict)
            }
            projected_policy = self._policy
            if account_patch is not None:
                projected_policy = merge_limits({}, self._policy, account_patch)
                planned_account_overlay.update(account_patch)
            if sleeves_patch is not None:
                for bundle_id, patch in sleeves_patch.items():
                    if not isinstance(patch, dict):
                        raise ValueError(
                            f"sleeve overlay for {bundle_id} must be an object"
                        )
                    envelope = self._bundle_envelope(bundle_id)
                    stored = planned_sleeve_overlays.get(bundle_id, {})
                    current_effective = merge_limits(envelope, projected_policy, stored)
                    merge_limits({}, current_effective, patch)
                    stored.update(patch)
                    planned_sleeve_overlays[bundle_id] = stored
            if account_patch is not None:
                self._policy = merge_limits({}, self._policy, account_patch)
                self._enforce_live_book()
                runtime["account_overlay"] = planned_account_overlay
            if sleeves_patch is not None:
                runtime["sleeve_overlays"] = planned_sleeve_overlays
            if account_patch is not None or sleeves_patch is not None:
                self._write_runtime(runtime)
                if sleeves_patch is not None:
                    self._enforce_live_book()
            return self._snapshot.state in (
                SupervisorState.FLATTENING,
                SupervisorState.STOPPED,
            )

    def _file_digest(self, path: Path) -> str:
        if not path.is_file():
            return ""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _bundle_envelope(self, bundle_id: str) -> dict[str, Any]:
        envelope_path = self._home.bundle_dir(bundle_id) / "risk-envelope.yaml"
        if not envelope_path.is_file():
            raw = b""
            digest = ""
        else:
            raw = envelope_path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
        cached = self._envelope_cache.get(bundle_id)
        if cached is not None and cached[0] == digest:
            return cached[1]
        doc: dict[str, Any] = load_risk_envelope(raw) if raw else {}
        self._envelope_cache[bundle_id] = (digest, doc)
        return doc

    def _effective_sleeve_policy(
        self, bundle_id: str, runtime: dict[str, Any] | None = None
    ) -> AccountPolicy:
        doc = runtime if runtime is not None else self._read_runtime()
        sleeve_overlays = doc.get("sleeve_overlays", {})
        overlay = sleeve_overlays.get(bundle_id) if isinstance(sleeve_overlays, dict) else None
        envelope = self._bundle_envelope(bundle_id)
        return merge_limits(envelope, self._policy, overlay)

    def _spoken_cache_key(self) -> tuple:
        allocated = tuple(
            sorted(
                (bundle_id, float(allocation))
                for bundle_id, allocation in self._snapshot.sleeves.items()
                if float(allocation) > 0
            )
        )
        envelopes = tuple(
            (
                bundle_id,
                self._file_digest(self._home.bundle_dir(bundle_id) / "risk-envelope.yaml"),
            )
            for bundle_id, _allocation in allocated
        )
        return (
            self._file_digest(self._home.runtime_path()),
            envelopes,
            allocated,
            self._policy,
        )

    def live_book(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        with self._lock:
            return self._live_book_unlocked()

    def live_book_source(self) -> str:
        with self._lock:
            cached = self._live_book_cache
            if cached is None:
                return "none"
            return "heartbeat" if cached[3] else "glance"

    def sleeve_policies(self, bundle_ids: list[str]) -> dict[str, AccountPolicy]:
        with self._lock:
            runtime = self._read_runtime()
            return {
                bundle_id: self._effective_sleeve_policy(bundle_id, runtime)
                for bundle_id in bundle_ids
            }

    def _invalidate_live_book(self) -> None:
        self._live_book_cache = None

    def _touch_live_book_cache(self) -> None:
        cached = self._live_book_cache
        if cached is None:
            return
        self._live_book_cache = (time.monotonic(), cached[1], cached[2], cached[3])

    def spoken_policy(self) -> AccountPolicy:
        with self._lock:
            return self._rebalance_policy()

    def _rebalance_policy(self) -> AccountPolicy:
        key = self._spoken_cache_key()
        cached = self._spoken_cache
        if cached is not None and cached[0] == key:
            return cached[1]
        runtime = self._read_runtime()
        policy = self._policy
        for bundle_id, allocation in self._snapshot.sleeves.items():
            if allocation <= 0:
                continue
            policy = tighten_policy(policy, self._effective_sleeve_policy(bundle_id, runtime))
        self._spoken_cache = (key, policy)
        return policy

    def _equity(self) -> float:
        account = self._broker.get_account()
        return float(account.get("equity", 0))

    def _session_order_budget(self, session_date: str) -> int:
        if self._snapshot.orders_date != session_date:
            self._snapshot.orders_date = session_date
            self._snapshot.orders_today = 0
        return self._snapshot.orders_today

    def _fetch_prices(
        self,
        symbols: set[str],
        now: datetime | None = None,
    ) -> dict[str, float]:
        if not symbols:
            return {}
        reference = now or datetime.now(timezone.utc)
        end = reference.date().isoformat()
        start = (reference.date() - timedelta(days=400)).isoformat()
        try:
            bars = self._broker.get_bars(sorted(symbols), start, end)
        except Exception as exc:
            raise HaltRequested(f"broker get_bars failed: {exc}") from exc
        prices: dict[str, float] = {}
        for symbol in symbols:
            symbol_data = bars.get(symbol)
            price = _last_bar_close(symbol_data)
            if price is None:
                raise HaltRequested(f"missing price for {symbol}")
            bar_timestamp = _last_bar_timestamp(symbol_data)
            if now is not None and bar_timestamp is not None:
                stale_before = now.date() - timedelta(days=3)
                if bar_timestamp.date() < stale_before:
                    raise HaltRequested(
                        f"stale bars for {symbol}: last bar {bar_timestamp.date()}"
                    )
            prices[symbol] = price
        return prices

    def _place_batch(
        self,
        plans: list,
        already: int,
        extra_audit: dict | None = None,
    ) -> tuple[int, Exception | None]:
        placed = 0
        extra = extra_audit or {}
        for plan in plans:
            try:
                self._broker.place_order(plan.symbol, plan.qty, plan.side)
            except Exception as exc:
                self._invalidate_live_book()
                return placed, exc
            self._audit(
                "order",
                symbol=plan.symbol,
                qty=plan.qty,
                side=plan.side,
                **extra,
            )
            placed += 1
            self._snapshot.orders_today = already + placed
            if self._snapshot.state == SupervisorState.REBALANCING:
                self._snapshot.rebalance_placed = placed
            self._persist()
        self._invalidate_live_book()
        return placed, None

    def _snapshot_got(
        self,
        combined: dict[str, float],
        prices: dict[str, float],
        equity: float,
    ) -> dict[str, float]:
        positions_after = _positions_map(self._broker.list_positions())
        got = {
            symbol: (qty * prices[symbol]) / equity
            for symbol, qty in positions_after.items()
            if symbol in prices and equity > 0
        }
        self._snapshot.last_got = dict(got)
        self._snapshot.last_fill_got = dict(got)
        for deviation in deviations_after(combined, got, equity, prices):
            self._audit("execution_deviation", **deviation)
        return got

    def _recover_interrupted_rebalance(self) -> None:
        if self._snapshot.state != SupervisorState.REBALANCING:
            return
        combined = dict(self._snapshot.last_combined)
        prices = dict(self._snapshot.last_prices)
        try:
            equity = self._equity()
            self._snapshot_got(combined, prices, equity)
        except Exception:
            pass
        placed = int(self._snapshot.rebalance_placed or 0)
        self._snapshot.last_rebalance_complete = False
        event = "open"
        marker = self._snapshot.last_rebalance_event or ""
        if ":" in marker:
            event = marker.split(":", 1)[1]
        self._audit(
            "rebalance",
            session_event=event,
            orders=placed,
            wanted=dict(combined),
            got=dict(self._snapshot.last_got),
            complete=False,
        )
        if marker:
            self._halt(f"interrupted rebalancing after {placed} orders; {marker} spent")
        else:
            self._halt(f"interrupted rebalancing after {placed} orders")

    def _recover_interrupted_flatten(self) -> None:
        if self._snapshot.state != SupervisorState.FLATTENING:
            return
        self._flatten_account(reason="flatten_interrupted")
        self._record_kill(
            KillOutcome(
                isolated=False,
                flattened=True,
                scope="account",
                reason="flatten_interrupted",
                bundle_id=None,
            )
        )

    def _recover_interrupted_isolate(self) -> None:
        bundle_id = self._snapshot.isolate_in_flight
        if not bundle_id:
            return
        self._flatten_account()
        self._audit(
            "kill",
            bundle_id=bundle_id,
            isolated=False,
            reason="fallback_interrupted",
        )
        self._record_kill(
            KillOutcome(
                isolated=False,
                flattened=True,
                scope="account",
                reason="fallback_interrupted",
                bundle_id=bundle_id,
            )
        )

    def _rebalance(self, cur: ClockSnapshot, event: str) -> None:
        collected = self._collect_sleeves()
        self._snapshot.state = SupervisorState.REBALANCING
        sleeves = [(alloc, weights) for _bid, alloc, weights in collected]
        combined = combine(sleeves)
        account = self._broker.get_account()
        equity = float(account.get("equity", 0))
        rebalance_policy = self._rebalance_policy()
        check_book(combined, equity, rebalance_policy)

        raw_positions = self._broker.list_positions()
        positions = _positions_map(raw_positions)
        symbols = set(combined) | set(positions)
        prices = self._fetch_prices(symbols, now=cur.now if cur.is_open else None)
        self._snapshot.last_sleeve_weights = {
            bid: dict(weights) for bid, _alloc, weights in collected
        }
        self._snapshot.last_sleeve_contribution = {
            bid: {asset: alloc * weight for asset, weight in weights.items()}
            for bid, alloc, weights in collected
        }
        self._snapshot.last_combined = dict(combined)
        self._snapshot.last_prices = dict(prices)
        self._enforce_live_book(account, raw_positions)
        if self._snapshot.state in (
            SupervisorState.FLATTENING,
            SupervisorState.STOPPED,
        ):
            return
        session_date = cur.next_close.date().isoformat()
        already = self._session_order_budget(session_date)
        plans = plan_orders(
            combined,
            positions,
            prices,
            equity,
            rebalance_policy,
            orders_already_today=already,
        )

        if plans:
            self._snapshot.last_rebalance_event = f"{session_date}:{event}"
            self._snapshot.rebalance_placed = 0
            self._snapshot.last_rebalance_complete = False
            self._persist()
        placed, place_error = self._place_batch(plans, already)
        got = self._snapshot_got(combined, prices, equity)
        self._snapshot.last_rebalance_event = f"{session_date}:{event}"
        self._audit(
            "rebalance",
            session_event=event,
            orders=placed,
            wanted=dict(combined),
            got=dict(got),
            complete=place_error is None,
        )
        if place_error is not None:
            raise HaltRequested(
                f"place_order failed after {placed} of {len(plans)}: {place_error}"
            ) from place_error
        self._snapshot.rebalance_placed = 0
        self._snapshot.last_rebalance_complete = True
        self._set_idle_state(cur)

    def _halt(self, reason: str) -> None:
        self._snapshot.state = SupervisorState.HALTED
        self._snapshot.halt_reason = reason
        self._snapshot.prime_clock_after_resume = True
        self._audit("halt", reason=reason)
        self._persist()

    def _flatten_account(self, *, reason: str = "account") -> None:
        self._invalidate_live_book()
        self._snapshot.isolate_in_flight = None
        self._snapshot.state = SupervisorState.FLATTENING
        self._persist()
        try:
            self._broker.cancel_open_orders()
        except Exception as exc:
            self._halt(f"flatten cancel_open_orders failed: {exc}")
            return
        try:
            self._broker.close_all()
        except Exception as exc:
            self._halt(f"flatten close_all failed: {exc}")
            return
        self._snapshot.state = SupervisorState.STOPPED
        self._snapshot.halt_reason = None
        self._snapshot.last_combined = {}
        self._snapshot.last_got = {}
        self._snapshot.last_fill_got = {}
        self._snapshot.last_sleeve_weights = {}
        self._snapshot.last_sleeve_contribution = {}
        self._snapshot.last_prices = {}
        for bundle_id in list(self._snapshot.sleeves):
            self._snapshot.sleeves[bundle_id] = 0.0
            if bundle_id not in self._snapshot.stopped:
                self._snapshot.stopped.append(bundle_id)
        self._audit("flatten", scope="account", reason=reason)
        self._persist()
