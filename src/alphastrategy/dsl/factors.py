"""Vendored alpha factors (no look-ahead audit decorator)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _empty_weights_like(prices: pd.Series) -> pd.Series:
    return pd.Series(0.0, index=prices.index, dtype=float)


def rsi(prices: pd.Series, window: int = 14, threshold: float = 50.0) -> pd.Series:
    if prices.empty or len(prices) < window + 1:
        return _empty_weights_like(prices)

    delta = prices.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi_raw = 100.0 - (100.0 / (1.0 + rs))
    rsi_val = pd.Series(rsi_raw, index=prices.index).astype(float)
    rsi_val = rsi_val.bfill().fillna(50.0)
    rsi_val = rsi_val.where(avg_loss > 0, 100.0)
    rsi_val = rsi_val.where(avg_gain > 0, rsi_val)
    signal = (rsi_val > threshold).astype(float)
    return signal.shift(1).fillna(0.0)


def macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> pd.Series:
    if prices.empty or len(prices) < slow + signal_period:
        return _empty_weights_like(prices)

    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    long_signal = (macd_line > signal_line).astype(float)
    return long_signal.shift(1).fillna(0.0)


def roc(prices: pd.Series, window: int = 20, threshold: float = 0.0) -> pd.Series:
    if prices.empty or len(prices) < window + 1:
        return _empty_weights_like(prices)

    rate = prices.pct_change(periods=window)
    signal = (rate > threshold).astype(float)
    return signal.shift(1).fillna(0.0)


def momentum_12_1(prices: pd.Series, skip: int = 21) -> pd.Series:
    if prices.empty or len(prices) < 252 + skip:
        return _empty_weights_like(prices)

    long_term = prices.pct_change(periods=252)
    shifted_long = long_term.shift(skip)
    short_term = prices.pct_change(periods=skip).shift(skip)
    signal = ((shifted_long > 0) & (short_term > 0)).astype(float)
    return signal


def bollinger_zscore(
    prices: pd.Series,
    window: int = 20,
    num_std: float = 1.5,
    invert: bool = True,
) -> pd.Series:
    if prices.empty or len(prices) < window:
        return _empty_weights_like(prices)

    ma = prices.rolling(window=window).mean()
    sd = prices.rolling(window=window).std()
    zscore = (prices - ma) / sd.replace(0.0, np.nan)
    if invert:
        signal = (zscore < -num_std).astype(float)
    else:
        signal = (zscore > num_std).astype(float)
    return signal.shift(1).fillna(0.0)


def ohlr_4_pct(
    ohlc: pd.DataFrame,
    threshold: float = 0.0,
) -> pd.Series:
    if ohlc.empty or len(ohlc) < 14:
        return pd.Series(0.0, index=ohlc.index, dtype=float)
    high = ohlc["high"]
    low = ohlc["low"]
    close = ohlc["close"]
    period = 14
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    denom = (hh - ll).replace(0.0, np.nan)
    pct_r = -100.0 * (hh - close) / denom
    pct_r = pd.Series(pct_r, index=ohlc.index).astype(float)
    pct_r = pct_r.bfill().fillna(-50.0)
    signal = (pct_r < -threshold).astype(float) if threshold > 0 else (pct_r < 0).astype(float)
    return signal.shift(1).fillna(0.0)


def pairs_spread(
    prices_a: pd.Series,
    prices_b: pd.Series,
    window: int = 60,
    num_std: float = 1.5,
) -> pd.Series:
    if prices_a.empty or prices_b.empty:
        return _empty_weights_like(prices_a)

    joined = pd.concat([prices_a.rename("a"), prices_b.rename("b")], axis=1, join="inner").dropna()
    if joined.empty or len(joined) < window:
        out = pd.Series(0.0, index=prices_a.index)
        return out.reindex(prices_a.index).fillna(0.0)

    log_a = pd.Series(np.log(joined["a"].to_numpy()), index=joined.index)
    log_b = pd.Series(np.log(joined["b"].to_numpy()), index=joined.index)
    spread = log_a - log_b
    ma = spread.rolling(window=window).mean()
    sd = spread.rolling(window=window).std()
    zscore = (spread - ma) / sd.replace(0.0, np.nan)
    long_a = (zscore < -num_std).astype(float)
    out = long_a.reindex(prices_a.index).fillna(0.0)
    return out.shift(1).fillna(0.0)


def atr_breakout(
    ohlc: pd.DataFrame,
    atr_window: int = 14,
    breakout_window: int = 50,
    atr_multiplier: float = 1.5,
) -> pd.Series:
    if ohlc.empty or len(ohlc) < max(atr_window, breakout_window) + 1:
        return _empty_weights_like(ohlc["close"])

    high = ohlc["high"]
    low = ohlc["low"]
    close = ohlc["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr = tr.ewm(alpha=1.0 / atr_window, adjust=False, min_periods=atr_window).mean()
    rolling_close_high = close.rolling(window=breakout_window).max().shift(1)
    threshold = rolling_close_high + atr_multiplier * atr
    breakout = (close > threshold).astype(float)
    return breakout.shift(1).fillna(0.0)


def parkinson_hist_vol(prices: pd.Series, window: int = 30) -> pd.Series:
    if prices.empty or len(prices) < window + 1:
        return _empty_weights_like(prices)

    rolling_high = prices.rolling(window=window).max()
    rolling_low = prices.rolling(window=window).min()
    log_hl = np.log((rolling_high / rolling_low).replace(0.0, np.nan))
    parkinson_var = (log_hl**2) / (4.0 * np.log(2.0))
    annualized = pd.Series(
        np.sqrt(parkinson_var * (252.0 / window)),
        index=prices.index,
    )
    return annualized.bfill().fillna(0.0)


def obv_slope(
    close: pd.Series,
    volume: pd.Series,
    window: int = 20,
    threshold: float = 0.0,
) -> pd.Series:
    if close.empty or volume.empty or len(close) < window + 1:
        return _empty_weights_like(close)

    direction = pd.Series(np.sign(close.diff().fillna(0.0).to_numpy()), index=close.index)
    volume_aligned = volume.reindex(close.index).fillna(0.0)
    signed_volume = direction * volume_aligned
    obv = signed_volume.cumsum()

    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_centered = x - x_mean

    def _slope(s: pd.Series) -> float:
        if s.isna().any() or len(s) < window:
            return np.nan
        y = s.to_numpy() - s.mean()
        return float((x_centered * y).sum() / (x_centered**2).sum())

    slopes = obv.rolling(window=window).apply(_slope, raw=False)
    signal = (slopes > threshold).astype(float)
    return signal.shift(1).fillna(0.0)
