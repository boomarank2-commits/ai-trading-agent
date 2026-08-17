"""V12 pair-local adaptive situation optimizer.

Research-only. Downloads public Binance 15m spot klines, trains on 730 days,
freezes a situation router, then evaluates on the following 365 blind days.
BTC/USDT, ETH/USDT and SOL/USDT are optimized independently.
"""
from __future__ import annotations

import argparse
import io
import itertools
import json
import math
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

FEE = 0.002
STRESS_FEE = 0.003
STAKE = 80.0
TRAIN_DAYS = 730
BLIND_DAYS = 365
PAIRS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
BASE_URL = "https://data.binance.vision/data/spot/monthly/klines"
COLS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
]


@dataclass(frozen=True)
class Variant:
    family: str
    name: str
    p1: float
    p2: float
    stop: float
    target: float
    max_bars: int


@dataclass
class Trade:
    variant: str
    family: str
    situation: str
    open_i: int
    close_i: int
    entry: float
    exit: float
    net_ret: float
    pnl: float


def months(start: pd.Timestamp, end: pd.Timestamp):
    cur = pd.Timestamp(start.year, start.month, 1, tz="UTC")
    last = pd.Timestamp(end.year, end.month, 1, tz="UTC")
    while cur <= last:
        yield cur
        cur = cur + pd.offsets.MonthBegin(1)


def download_pair(symbol: str, start: pd.Timestamp, end: pd.Timestamp, cache: Path) -> pd.DataFrame:
    cache.mkdir(parents=True, exist_ok=True)
    frames = []
    for month in months(start, end):
        ym = month.strftime("%Y-%m")
        local = cache / f"{symbol}-15m-{ym}.zip"
        if not local.exists():
            url = f"{BASE_URL}/{symbol}/15m/{symbol}-15m-{ym}.zip"
            try:
                with urllib.request.urlopen(url, timeout=45) as response:
                    local.write_bytes(response.read())
            except Exception as exc:
                raise RuntimeError(f"download failed {url}: {exc}") from exc
        with zipfile.ZipFile(local) as zf:
            names = zf.namelist()
            if len(names) != 1:
                raise RuntimeError(f"unexpected archive layout: {local}")
            raw = zf.read(names[0])
        frame = pd.read_csv(io.BytesIO(raw), header=None, names=COLS)
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    unit = np.where(df["open_time"].to_numpy(dtype=np.int64) > 10**14, 1000, 1)
    ms = df["open_time"].to_numpy(dtype=np.int64) // unit
    df["date"] = pd.to_datetime(ms, unit="ms", utc=True)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df = df.dropna().drop_duplicates("date").sort_values("date").reset_index(drop=True)
    df = df[(df["date"] >= start) & (df["date"] < end)].reset_index(drop=True)
    expected = pd.Timedelta(minutes=15)
    gaps = df["date"].diff().dropna()
    if (gaps <= pd.Timedelta(0)).any():
        raise RuntimeError(f"{symbol}: non-monotone candle sequence")
    bad = int((gaps > expected).sum())
    if bad > 5:
        raise RuntimeError(f"{symbol}: too many historical candle gaps={bad}")
    if bad:
        print(f"{symbol}: research warning - tolerated historical gaps={bad}", flush=True)
    return df


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat(
        [(df["high"] - df["low"]), (df["high"] - pc).abs(), (df["low"] - pc).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def adx(frame: pd.DataFrame, n: int = 14) -> pd.Series:
    high, low, close = frame["high"], frame["low"], frame["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    pc = close.shift(1)
    tr = pd.concat([(high - low), (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)
    atr_n = tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / atr_n
    minus_di = 100 * minus_dm.ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / atr_n
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def add_tf_features(base: pd.DataFrame, rule: str, suffix: str) -> pd.DataFrame:
    x = base.set_index("date").resample(rule, label="right", closed="right").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum"),
    ).dropna().reset_index()
    x[f"ema20_{suffix}"] = ema(x["close"], 20)
    x[f"ema50_{suffix}"] = ema(x["close"], 50)
    x[f"ema200_{suffix}"] = ema(x["close"], 200)
    x[f"rsi_{suffix}"] = rsi(x["close"])
    x[f"mom6_{suffix}"] = x["close"].pct_change(6)
    x[f"close_{suffix}"] = x["close"]
    keep = ["date", f"close_{suffix}", f"ema20_{suffix}", f"ema50_{suffix}", f"ema200_{suffix}", f"rsi_{suffix}", f"mom6_{suffix}"]
    if suffix == "4h":
        x["adx_4h"] = adx(x)
        x["donchian120_4h"] = x["high"].shift(1).rolling(120, min_periods=120).max()
        x["low60_4h"] = x["low"].shift(1).rolling(60, min_periods=60).min()
        x["mom180_4h"] = x["close"].pct_change(180)
        x["ema50_rising_4h"] = x["ema50_4h"] > x["ema50_4h"].shift(6)
        keep.extend(["adx_4h", "donchian120_4h", "low60_4h", "mom180_4h", "ema50_rising_4h"])
    return x[keep]


def features(df: pd.DataFrame, train_end: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    x = df.copy()
    x["ema20"] = ema(x["close"], 20)
    x["ema50"] = ema(x["close"], 50)
    x["ema200"] = ema(x["close"], 200)
    x["rsi"] = rsi(x["close"])
    x["atr"] = atr(x)
    x["atr_pct"] = x["atr"] / x["close"]
    x["vol_mean"] = x["volume"].shift(1).rolling(20, min_periods=20).mean()
    x["vol_ratio"] = x["volume"] / x["vol_mean"]
    x["ret24h"] = x["close"].pct_change(96)
    x["ret6h"] = x["close"].pct_change(24)
    x["hh_40"] = x["high"].shift(1).rolling(40, min_periods=40).max()
    x["hh_80"] = x["high"].shift(1).rolling(80, min_periods=80).max()
    x["hh_120"] = x["high"].shift(1).rolling(120, min_periods=120).max()
    mid = x["close"].rolling(20, min_periods=20).mean()
    std = x["close"].rolling(20, min_periods=20).std(ddof=0)
    x["bb_mid"] = mid
    x["bb_lower_18"] = mid - 1.8 * std
    x["bb_lower_20"] = mid - 2.0 * std
    x["bb_lower_22"] = mid - 2.2 * std
    x["bb_width"] = (4.0 * std) / mid
    h9, l9 = x["high"].rolling(9).max(), x["low"].rolling(9).min()
    h26, l26 = x["high"].rolling(26).max(), x["low"].rolling(26).min()
    h52, l52 = x["high"].rolling(52).max(), x["low"].rolling(52).min()
    x["tenkan"] = (h9 + l9) / 2
    x["kijun"] = (h26 + l26) / 2
    pa, pb = (x["tenkan"] + x["kijun"]) / 2, (h52 + l52) / 2
    x["cloud_a"] = pa.shift(26)
    x["cloud_b"] = pb.shift(26)
    x["cloud_top"] = x[["cloud_a", "cloud_b"]].max(axis=1)
    x["future_bull"] = pa > pb
    x["chikou_clear"] = x["close"] > x["high"].shift(26)
    for tf, suffix in (("1h", "1h"), ("4h", "4h")):
        y = add_tf_features(df, tf, suffix)
        x = pd.merge_asof(x.sort_values("date"), y.sort_values("date"), on="date", direction="backward")
    train = x[x["date"] < train_end]
    q = {
        "atr_lo": float(train["atr_pct"].quantile(0.33)),
        "atr_hi": float(train["atr_pct"].quantile(0.67)),
        "vol_hi": float(train["vol_ratio"].quantile(0.67)),
        "trend_hi": float(((train["ema20_4h"] - train["ema50_4h"]).abs() / train["close"]).quantile(0.67)),
    }
    return x, q


def situation_keys(x: pd.DataFrame, q: dict) -> pd.Series:
    trend_spread = (x["ema20_4h"] - x["ema50_4h"]) / x["close"]
    trend = np.select([trend_spread > q["trend_hi"], trend_spread < -q["trend_hi"]], ["up", "down"], default="flat")
    vol = np.select([x["atr_pct"] < q["atr_lo"], x["atr_pct"] > q["atr_hi"]], ["lowv", "highv"], default="midv")
    mom = np.select([x["ret24h"] > 0.025, x["ret24h"] < -0.025], ["momup", "momdn"], default="momflat")
    liq = np.where(x["vol_ratio"] >= q["vol_hi"], "volhi", "volnorm")
    return pd.Series(trend + "|" + vol + "|" + mom + "|" + liq, index=x.index)


def variants() -> list[Variant]:
    out = []
    for adx_min, vol in itertools.product((16, 20, 24), (0.0, 0.8, 1.0)):
        out.append(Variant("donchian_trend", f"donchian_a{adx_min}_v{vol}", adx_min, vol, 0.055, 0.50, 5760))
    for n, vol, stop, tp in itertools.product((40, 80, 120), (0.8, 1.0, 1.2), (0.025, 0.04), (0.05, 0.08, 0.12)):
        out.append(Variant("slow_breakout", f"bo_n{n}_v{vol}_s{stop}_t{tp}", n, vol, stop, tp, 384))
    for vol, stop, tp in itertools.product((0.7, 0.9, 1.1), (0.02, 0.03), (0.035, 0.055, 0.08)):
        out.append(Variant("trend_pullback", f"pb_v{vol}_s{stop}_t{tp}", vol, 0, stop, tp, 192))
    for dev, rmax, stop in itertools.product((1.8, 2.0, 2.2), (38, 42, 46), (0.012, 0.018, 0.025)):
        out.append(Variant("bollinger_mr", f"mr_d{dev}_r{rmax}_s{stop}", dev, rmax, stop, 0.0, 64))
    for vol, stop, tp in itertools.product((0.7, 0.9, 1.1), (0.025, 0.035), (0.05, 0.08)):
        out.append(Variant("ichimoku", f"ichi_v{vol}_s{stop}_t{tp}", vol, 0, stop, tp, 256))
    for drop, rmax, stop, tp in itertools.product((-0.04, -0.06, -0.08), (35, 40), (0.018, 0.025), (0.03, 0.05)):
        out.append(Variant("panic_bounce", f"panic_d{drop}_r{rmax}_s{stop}_t{tp}", drop, rmax, stop, tp, 96))
    return out


def signal(x: pd.DataFrame, v: Variant) -> pd.Series:
    trend = (
        (x["close_4h"] > x["ema50_4h"])
        & (x["ema20_4h"] > x["ema50_4h"])
        & (x["close_1h"] > x["ema50_1h"])
    )
    if v.family == "donchian_trend":
        fresh = (x["close_4h"] > x["donchian120_4h"]) & (
            x["close_4h"].shift(1) <= x["donchian120_4h"].shift(1)
        )
        return (
            fresh
            & (x["ema50_4h"] > x["ema200_4h"])
            & x["ema50_rising_4h"].fillna(False)
            & (x["adx_4h"] >= v.p1)
            & (x["mom180_4h"] > 0)
            & (x["close_1h"] > x["ema200_1h"])
            & ((v.p2 <= 0) | (x["vol_ratio"] >= v.p2))
        )
    if v.family == "slow_breakout":
        hh = x[f"hh_{int(v.p1)}"]
        return trend & (x["close"] > hh) & (x["vol_ratio"] >= v.p2) & x["rsi"].between(48, 78)
    if v.family == "trend_pullback":
        return (
            trend & (x["low"] <= x["ema20"] + 0.35 * x["atr"]) & (x["close"] > x["ema20"])
            & (x["close"] > x["open"]) & (x["rsi"] > x["rsi"].shift(1))
            & (x["vol_ratio"] >= v.p1) & x["rsi"].between(45, 70)
        )
    if v.family == "bollinger_mr":
        col = {1.8: "bb_lower_18", 2.0: "bb_lower_20", 2.2: "bb_lower_22"}[v.p1]
        lower = x[col]
        rangeish = ((x["ema20_4h"] - x["ema50_4h"]).abs() / x["close"] < 0.018) & (x["bb_width"] < 0.055)
        return (
            rangeish & (x["low"] <= lower) & (x["close"] > lower)
            & (x["close"] > x["open"]) & (x["rsi"] <= v.p2) & (x["rsi"] > x["rsi"].shift(1))
        )
    if v.family == "ichimoku":
        cross = (x["tenkan"] > x["kijun"]) & (x["tenkan"].shift(1) <= x["kijun"].shift(1))
        return (
            trend & cross & (x["close"] > x["cloud_top"]) & x["future_bull"] & x["chikou_clear"]
            & (x["vol_ratio"] >= v.p1) & x["rsi"].between(47, 73)
        )
    if v.family == "panic_bounce":
        return (
            (x["ret24h"] <= v.p1) & (x["low"] <= x["bb_lower_20"])
            & (x["close"] > x["bb_lower_20"]) & (x["close"] > x["open"])
            & (x["rsi"] <= v.p2) & (x["rsi"] > x["rsi"].shift(1))
        )
    raise ValueError(v.family)


def net_return(entry: float, exit_: float, fee: float) -> float:
    return (exit_ / entry) * ((1 - fee) / (1 + fee)) - 1


def simulate_variant(x: pd.DataFrame, v: Variant, mask: pd.Series, start_i: int, end_i: int, situations: pd.Series, fee: float = FEE) -> list[Trade]:
    sig = mask.to_numpy(dtype=bool)
    high = x["high"].to_numpy()
    low = x["low"].to_numpy()
    close = x["close"].to_numpy()
    mid = x["bb_mid"].to_numpy()
    low60 = x["low60_4h"].to_numpy()
    ema50_4h = x["ema50_4h"].to_numpy()
    close_4h = x["close_4h"].to_numpy()
    out: list[Trade] = []
    i = max(start_i, 1)
    while i < end_i - 1:
        if not sig[i] or not np.isfinite(close[i]):
            i += 1
            continue
        entry_i = i + 1
        entry = float(x["open"].iloc[entry_i])
        if not math.isfinite(entry) or entry <= 0:
            i += 1
            continue
        stop_price = entry * (1 - v.stop)
        target_price = entry * (1 + v.target) if v.target > 0 else math.inf
        last = min(end_i - 1, entry_i + v.max_bars)
        exit_i, exit_price = last, float(close[last])
        for j in range(entry_i, last + 1):
            if low[j] <= stop_price:
                exit_i, exit_price = j, stop_price
                break
            if v.family == "bollinger_mr" and math.isfinite(mid[j]) and high[j] >= mid[j]:
                exit_i, exit_price = j, float(mid[j])
                break
            if v.family == "donchian_trend" and (
                (math.isfinite(low60[j]) and close[j] < low60[j])
                or (math.isfinite(ema50_4h[j]) and close_4h[j] < ema50_4h[j])
            ):
                exit_i, exit_price = j, float(close[j])
                break
            if high[j] >= target_price:
                exit_i, exit_price = j, target_price
                break
        nr = net_return(entry, exit_price, fee)
        out.append(Trade(v.name, v.family, str(situations.iloc[i]), entry_i, exit_i, entry, exit_price, nr, STAKE * nr))
        i = exit_i + 1
    return out


def metrics(trades: list[Trade], fee_override: float | None = None) -> dict:
    if not trades:
        return {"trades": 0, "pnl": 0.0, "pf": 0.0, "dd": 0.0, "winrate": 0.0}
    pnl = []
    equity = 0.0
    peak = 0.0
    dd = 0.0
    for t in trades:
        p = t.pnl if fee_override is None else STAKE * net_return(t.entry, t.exit, fee_override)
        pnl.append(p)
        equity += p
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    gp = sum(p for p in pnl if p > 0)
    gl = -sum(p for p in pnl if p < 0)
    return {
        "trades": len(pnl),
        "pnl": float(sum(pnl)),
        "pf": float(gp / gl) if gl > 0 else (99.0 if gp > 0 else 0.0),
        "dd": float(dd),
        "winrate": float(sum(p > 0 for p in pnl) / len(pnl)),
    }


def train_router(x: pd.DataFrame, train_start_i: int, train_end_i: int, situations: pd.Series) -> tuple[dict, dict]:
    candidates = variants()
    router: dict[str, dict] = {}
    diagnostics = {"tested_variants": len(candidates), "eligible_specialists": 0, "families": {}}
    for v in candidates:
        tr = simulate_variant(x, v, signal(x, v), train_start_i, train_end_i, situations)
        diagnostics["families"].setdefault(v.family, {"variants": 0, "trades": 0})
        diagnostics["families"][v.family]["variants"] += 1
        diagnostics["families"][v.family]["trades"] += len(tr)
        if not tr:
            continue
        global_m = metrics(tr)
        global_stress = metrics(tr, STRESS_FEE)
        if global_m["trades"] < 10 or global_m["pnl"] <= 0 or global_m["pf"] < 1.10 or global_stress["pnl"] <= 0:
            continue
        by_sit: dict[str, list[Trade]] = {}
        for t in tr:
            by_sit.setdefault(t.situation, []).append(t)
        for sit, ts in by_sit.items():
            m = metrics(ts)
            stress = metrics(ts, STRESS_FEE)
            min_trades = 4 if v.family == "donchian_trend" else 8
            if m["trades"] < min_trades or m["pnl"] <= 0 or m["pf"] < 1.20 or stress["pnl"] <= 0:
                continue
            cuts = np.linspace(train_start_i, train_end_i, 5, dtype=int)
            slice_pnls = [sum(t.pnl for t in ts if a <= t.open_i < b) for a, b in zip(cuts[:-1], cuts[1:])]
            if sum(p > 0 for p in slice_pnls) < 2:
                continue
            expectancy = m["pnl"] / m["trades"]
            score = expectancy * math.sqrt(m["trades"]) + 0.05 * m["pnl"]
            spec = {"variant": v.name, "family": v.family, "situation": sit, "score": score, "train": m, "stress_pnl": stress["pnl"], "slice_pnls": slice_pnls, "params": asdict(v)}
            prev = router.get(sit)
            if prev is None or spec["score"] > prev["score"]:
                router[sit] = spec
    diagnostics["eligible_specialists"] = len(router)
    return router, diagnostics


def blind_router(x: pd.DataFrame, router: dict, blind_start_i: int, blind_end_i: int, situations: pd.Series) -> list[Trade]:
    by_name = {v.name: v for v in variants()}
    masks = {name: signal(x, by_name[name]).to_numpy(dtype=bool) for name in {r["variant"] for r in router.values()}}
    high = x["high"].to_numpy()
    low = x["low"].to_numpy()
    close = x["close"].to_numpy()
    mid = x["bb_mid"].to_numpy()
    low60 = x["low60_4h"].to_numpy()
    ema50_4h = x["ema50_4h"].to_numpy()
    close_4h = x["close_4h"].to_numpy()
    out: list[Trade] = []
    i = max(blind_start_i, 1)
    while i < blind_end_i - 1:
        sit = str(situations.iloc[i])
        spec = router.get(sit)
        if not spec:
            i += 1
            continue
        v = by_name[spec["variant"]]
        if not masks[v.name][i]:
            i += 1
            continue
        entry_i = i + 1
        entry = float(x["open"].iloc[entry_i])
        stop_price = entry * (1 - v.stop)
        target_price = entry * (1 + v.target) if v.target > 0 else math.inf
        last = min(blind_end_i - 1, entry_i + v.max_bars)
        exit_i, exit_price = last, float(close[last])
        for j in range(entry_i, last + 1):
            if low[j] <= stop_price:
                exit_i, exit_price = j, stop_price
                break
            if v.family == "bollinger_mr" and math.isfinite(mid[j]) and high[j] >= mid[j]:
                exit_i, exit_price = j, float(mid[j])
                break
            if v.family == "donchian_trend" and (
                (math.isfinite(low60[j]) and close[j] < low60[j])
                or (math.isfinite(ema50_4h[j]) and close_4h[j] < ema50_4h[j])
            ):
                exit_i, exit_price = j, float(close[j])
                break
            if high[j] >= target_price:
                exit_i, exit_price = j, target_price
                break
        nr = net_return(entry, exit_price, FEE)
        out.append(Trade(v.name, v.family, sit, entry_i, exit_i, entry, exit_price, nr, STAKE * nr))
        i = exit_i + 1
    return out


def run_pair_window(symbol: str, df: pd.DataFrame, start: pd.Timestamp) -> dict:
    train_end = start + pd.Timedelta(days=TRAIN_DAYS)
    blind_end = train_end + pd.Timedelta(days=BLIND_DAYS)
    local = df[(df["date"] >= start) & (df["date"] < blind_end)].reset_index(drop=True)
    if local.empty or local["date"].max() < blind_end - pd.Timedelta(minutes=15):
        raise RuntimeError(f"{symbol}: insufficient data for fold starting {start}")
    x, q = features(local, train_end)
    situations = situation_keys(x, q)
    train_start_i = int(x["date"].searchsorted(start))
    train_end_i = int(x["date"].searchsorted(train_end))
    blind_end_i = int(x["date"].searchsorted(blind_end))
    router, diag = train_router(x, train_start_i, train_end_i, situations)
    blind = blind_router(x, router, train_end_i, blind_end_i, situations)
    bm, stress = metrics(blind), metrics(blind, STRESS_FEE)
    family_pnl = {}
    for t in blind:
        family_pnl[t.family] = family_pnl.get(t.family, 0.0) + t.pnl
    return {
        "symbol": symbol,
        "train_start": str(start),
        "train_end": str(train_end),
        "blind_start": str(train_end),
        "blind_end": str(blind_end),
        "router_specialists": len(router),
        "training_diagnostics": diag,
        "blind": bm,
        "blind_stress_fee_0_003": stress,
        "blind_family_pnl": family_pnl,
        "router": router,
        "blind_trades": [asdict(t) for t in blind],
    }


def aggregate_folds(folds: list[dict]) -> dict:
    all_trades = []
    family_pnl = {}
    for fold in folds:
        for raw in fold["blind_trades"]:
            t = Trade(**raw)
            all_trades.append(t)
            family_pnl[t.family] = family_pnl.get(t.family, 0.0) + t.pnl
    return {
        "blind": metrics(all_trades),
        "blind_stress_fee_0_003": metrics(all_trades, STRESS_FEE),
        "positive_folds": sum(f["blind"]["pnl"] > 0 for f in folds),
        "fold_count": len(folds),
        "family_pnl": family_pnl,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=Path("runtime/user_data/v12_public_cache"))
    ap.add_argument("--out", type=Path, default=Path("runtime/user_data/v12_optimizer_report.json"))
    ap.add_argument("--start", default="2021-08-01")
    ap.add_argument("--folds", type=int, default=3)
    args = ap.parse_args()
    first = pd.Timestamp(args.start, tz="UTC")
    starts = [first + pd.DateOffset(years=i) for i in range(args.folds)]
    end = max(starts) + pd.Timedelta(days=TRAIN_DAYS + BLIND_DAYS)
    results = {}
    for symbol in PAIRS:
        print(f"=== {symbol}: download/load ===", flush=True)
        df = download_pair(symbol, first, end, args.cache)
        print(f"{symbol}: {len(df)} candles {df.date.min()} -> {df.date.max()}", flush=True)
        folds = []
        for idx, fold_start in enumerate(starts):
            result = run_pair_window(symbol, df, fold_start)
            folds.append(result)
            b = result["blind"]
            print(f"{symbol} fold{idx + 1}: specialists={result['router_specialists']} trades={b['trades']} pnl={b['pnl']:.2f} PF={b['pf']:.3f} DD={b['dd']:.2f} families={result['blind_family_pnl']}", flush=True)
        agg = aggregate_folds(folds)
        results[symbol] = {"folds": folds, "aggregate": agg}
        b = agg["blind"]
        print(f"{symbol} AGG: positive_folds={agg['positive_folds']}/{agg['fold_count']} trades={b['trades']} pnl={b['pnl']:.2f} PF={b['pf']:.3f} DD={b['dd']:.2f} families={agg['family_pnl']}", flush=True)
    payload = {"version": "V12_RESEARCH_SEARCH_2", "generated_at": datetime.now(UTC).isoformat(), "fee_per_side": FEE, "stress_fee_per_side": STRESS_FEE, "stake_usdt": STAKE, "train_days": TRAIN_DAYS, "blind_days": BLIND_DAYS, "fold_starts": [str(s) for s in starts], "results": results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
