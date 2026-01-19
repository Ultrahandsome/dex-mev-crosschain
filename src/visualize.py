# src/visualize.py
from __future__ import annotations
import os, sys, math, warnings
from typing import Optional, Tuple, List
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_DIR = os.path.join(ROOT, "data", "csv")
PLOT_DIR = os.path.join(ROOT, "data", "analysis", "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

# ------------------------- utils -------------------------

def _to_dt(x, unit: Optional[str] = None):
    """safe datetime parser; if already datetime-like just return"""
    try:
        if unit is not None:
            return pd.to_datetime(x, unit=unit, utc=True, errors="coerce")
        return pd.to_datetime(x, utc=True, errors="coerce")
    except Exception:
        return pd.to_datetime(pd.Series(x), utc=True, errors="coerce")

def _warn(msg: str):
    print(f"[viz] {msg}")

def _enough_points(series: pd.Series, minn: int = 5) -> bool:
    s = series.dropna()
    return len(s) >= minn

def _all_equal(series: pd.Series) -> bool:
    s = series.dropna()
    return (len(s) > 0) and (s.min() == s.max())

def _savefig(path: str):
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"[viz] saved -> {path}")

# ------------------------- price sanity -------------------------

def _as_usdc_per_weth(price_series: pd.Series) -> pd.Series:
    """
    Normalize price: if median price < 10 (e.g. values like 0.0005 are actually inverse),
    take reciprocal to represent USDC per ETH.
    Only applies to WETH/USDC in this project.
    """
    s = pd.to_numeric(price_series, errors="coerce")
    med = s.dropna().median() if len(s.dropna()) else np.nan
    if pd.notna(med) and med < 10:
        # Example: 0.00048 USDC/ETH -> 1/0.00048 ≈ 2083 USDC/ETH
        with np.errstate(divide='ignore', invalid='ignore'):
            inv = 1.0 / s.replace({0: np.nan})
        return inv
    return s

# ------------------------- loaders -------------------------

def load_price_series(chain: str, span: int) -> Optional[pd.DataFrame]:
    path = os.path.join(CSV_DIR, f"price_series_{chain}_{span}.csv")
    if not os.path.exists(path):
        _warn(f"missing {path}")
        return None
    df = pd.read_csv(path)
    # columns: datetime, vwap, trades, min_price, max_price
    if "datetime" in df.columns:
        df["datetime"] = _to_dt(df["datetime"])
    elif "timestamp" in df.columns:
        df["datetime"] = _to_dt(df["timestamp"], unit="s")
    else:
        _warn(f"{path} has no time column")
        df["datetime"] = pd.NaT
    df["vwap"] = _as_usdc_per_weth(df.get("vwap", np.nan))
    return df

def load_crosschain(span: int) -> Optional[pd.DataFrame]:
    # threshold file (spread only)
    path = os.path.join(CSV_DIR, f"crosschain_spread_{span}_thr30bps.csv")
    if not os.path.exists(path):
        _warn(f"missing {path}")
        return None
    df = pd.read_csv(path)
    if "datetime" in df.columns:
        df["datetime"] = _to_dt(df["datetime"])
    elif "timestamp" in df.columns:
        df["datetime"] = _to_dt(df["timestamp"], unit="s")
    df["spread_bps"] = pd.to_numeric(df.get("spread_bps", np.nan), errors="coerce")
    df["abs_spread_bps"] = pd.to_numeric(df.get("abs_spread_bps", np.nan), errors="coerce")
    return df

def load_crosschain_cost(span: int, fee_bps: int = 5, bridge_bps: int = 10) -> Optional[pd.DataFrame]:
    path = os.path.join(CSV_DIR, f"crosschain_cost_{span}_fee{fee_bps}bps_bridge{bridge_bps}bps.csv")
    if not os.path.exists(path):
        _warn(f"missing {path}")
        return None
    df = pd.read_csv(path)
    if "datetime" in df.columns:
        df["datetime"] = _to_dt(df["datetime"])
    elif "timestamp" in df.columns:
        df["datetime"] = _to_dt(df["timestamp"], unit="s")
    for c in ["net_bps","spread_bps","total_cost_bps"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def load_liquidity_profile(chain: str, fee: int) -> Optional[pd.DataFrame]:
    # filename like: liquidity_profile_{chain}_WETHUSDC_{fee}.csv
    path = os.path.join(CSV_DIR, f"liquidity_profile_{chain}_WETHUSDC_{fee}.csv")
    if not os.path.exists(path):
        _warn(f"missing {path}")
        return None
    df = pd.read_csv(path)
    # columns include: tick, price_t1_per_t0, liquidity_net, liquidity_gross, active_liquidity, word_index
    # normalize price
    if "price_t1_per_t0" in df.columns:
        df["price"] = _as_usdc_per_weth(df["price_t1_per_t0"])
    else:
        _warn(f"{path} missing price_t1_per_t0; plotting tick instead")
        df["price"] = df.get("tick", np.nan)
    df["active_liquidity"] = pd.to_numeric(df.get("active_liquidity", np.nan), errors="coerce")
    df["liquidity_net"] = pd.to_numeric(df.get("liquidity_net", np.nan), errors="coerce")
    return df

def load_liquidations(chain: str, span: int) -> Optional[pd.DataFrame]:
    path = os.path.join(CSV_DIR, f"liquidations_{chain}_{span}.csv")
    if not os.path.exists(path):
        _warn(f"missing {path}")
        return None
    df = pd.read_csv(path)
    # timestamp (seconds) → datetime
    if "timestamp" in df.columns:
        df["datetime"] = _to_dt(df["timestamp"], unit="s")
    else:
        df["datetime"] = pd.NaT
    return df

def load_swaps(chain: str, span: int) -> Optional[pd.DataFrame]:
    path = os.path.join(CSV_DIR, f"swaps_{chain}_{span}.csv")
    if not os.path.exists(path):
        _warn(f"missing {path}")
        return None
    df = pd.read_csv(path)
    # swaps file may already contain ISO timestamp; fallback otherwise
    if "timestamp" in df.columns:
        df["datetime"] = _to_dt(df["timestamp"])
    elif "time" in df.columns:
        df["datetime"] = _to_dt(df["time"])
    else:
        df["datetime"] = pd.NaT
    # normalize size (token0 units if decimals available)
    dec0 = pd.to_numeric(df.get("decimals0", np.nan), errors="coerce")
    # if decimals0 missing, fallback to raw abs
    if dec0.notna().any():
        df["size_token0"] = (pd.to_numeric(df.get("amount0", 0), errors="coerce").abs()
                             / (10.0 ** dec0.fillna(0)))
    else:
        df["size_token0"] = pd.to_numeric(df.get("amount0", 0), errors="coerce").abs()
    return df

# ------------------------- plotting -------------------------

def plot_vwap_comparison(span: int):
    eth = load_price_series("ethereum", span)
    arb = load_price_series("arbitrum", span)
    if eth is None or arb is None: 
        return
    m = pd.merge(
        eth[["datetime","vwap"]].rename(columns={"vwap":"eth_vwap"}),
        arb[["datetime","vwap"]].rename(columns={"vwap":"arb_vwap"}),
        on="datetime", how="inner"
    )
    if not _enough_points(m["datetime"]):
        _warn("vwap comparison: insufficient overlap")
        return
    fig = plt.figure(figsize=(12,4.4))
    plt.plot(m["datetime"], m["eth_vwap"], label="Ethereum VWAP (USDC/WETH)")
    plt.plot(m["datetime"], m["arb_vwap"], label="Arbitrum VWAP (USDC/WETH)")
    plt.ylabel("Price (USDC/WETH)")
    plt.title(f"VWAP (USDC per WETH) — span {span} blocks")
    plt.legend()
    _savefig(os.path.join(PLOT_DIR, f"vwap_eth_vs_arb_{span}.png"))

def plot_spread_timeseries(span: int, thr_bps: int = 30):
    cc = load_crosschain(span)
    if cc is None or not _enough_points(cc["datetime"]):
        return
    fig = plt.figure(figsize=(12,4.4))
    plt.plot(cc["datetime"], cc["spread_bps"], label="Spread (bps)")
    plt.axhline(+thr_bps, ls="--")
    plt.axhline(-thr_bps, ls="--")
    plt.ylabel("Spread (bps)")
    plt.title(f"Spread vs Threshold (±{thr_bps} bps) — span {span}")
    plt.legend()
    _savefig(os.path.join(PLOT_DIR, f"spread_threshold_{span}_thr{thr_bps}bps.png"))

def plot_spread_hist(span: int):
    cc = load_crosschain(span)
    if cc is None: 
        return
    x = cc["spread_bps"].dropna()
    if len(x) < 5 or _all_equal(x):
        _warn("spread hist: flat or too few points; skip")
        return
    fig = plt.figure(figsize=(10,5))
    plt.hist(x, bins=30)
    plt.xlabel("Spread (bps)")
    plt.ylabel("Count")
    plt.title(f"Distribution of Spread (bps) — span {span}")
    _savefig(os.path.join(PLOT_DIR, f"spread_hist_{span}.png"))

def plot_costed_net(span: int, fee_bps: int = 5, bridge_bps: int = 10):
    df = load_crosschain_cost(span, fee_bps, bridge_bps)
    if df is None or not _enough_points(df["datetime"]):
        return
    fig = plt.figure(figsize=(12,4.4))
    plt.plot(df["datetime"], df["net_bps"], label="Net bps (spread - total cost)")
    plt.axhline(0, ls="--", color="black", linewidth=0.8)
    plt.ylabel("Net bps")
    plt.title(f"Cost-aware Net Opportunity — span {span}, fee={fee_bps}bps, bridge={bridge_bps}bps")
    plt.legend()
    _savefig(os.path.join(PLOT_DIR, f"net_bps_costed_{span}_fee{fee_bps}_bridge{bridge_bps}.png"))

    x = df["net_bps"].dropna()
    if len(x) >= 5 and not _all_equal(x):
        fig = plt.figure(figsize=(7,5))
        plt.hist(x, bins=30)
        plt.xlabel("Net bps")
        plt.ylabel("Count")
        plt.title("Distribution of Net bps (after costs)")
        _savefig(os.path.join(PLOT_DIR, f"net_bps_hist_{span}_fee{fee_bps}_bridge{bridge_bps}.png"))
    else:
        _warn("net bps hist: flat or too few points; skip")

def plot_liquidity_profile(chain: str, fee: int):
    df = load_liquidity_profile(chain, fee)
    if df is None or not _enough_points(df["price"]):
        return

    # Active liquidity vs price
    fig = plt.figure(figsize=(12,4.4))
    plt.plot(df["price"], df["active_liquidity"])
    plt.xlabel("Price (USDC per WETH)")
    plt.ylabel("Active Liquidity")
    plt.title(f"Active Liquidity across Price — {chain} WETHUSDC fee={fee}")
    _savefig(os.path.join(PLOT_DIR, f"liq_profile_active_{chain}_WETHUSDC_{fee}.png"))

    # Net liquidity vs price
    if "liquidity_net" in df.columns and df["liquidity_net"].notna().any():
        fig = plt.figure(figsize=(12,4.4))
        plt.plot(df["price"], df["liquidity_net"])
        plt.xlabel("Price (USDC per WETH)")
        plt.ylabel("Net Liquidity")
        plt.title(f"Net Liquidity by Price — {chain} WETHUSDC fee={fee}")
        _savefig(os.path.join(PLOT_DIR, f"liq_profile_net_{chain}_WETHUSDC_{fee}.png"))

def plot_liquidations_vs_price(chain: str, span: int):
    liq = load_liquidations(chain, span)
    ps  = load_price_series(chain, span)
    if liq is None or ps is None:
        return
    # aggregate liquidations per hour (smoother)
    liq = liq.dropna(subset=["datetime"])
    if liq.empty:
        _warn(f"{chain} liquidations empty; skip plot")
        return
    liq["hour"] = liq["datetime"].dt.floor("H")
    agg = liq.groupby("hour").size().rename("events").reset_index()

    # align with price
    ps["minute"] = ps["datetime"].dt.floor("H")
    px = ps.groupby("minute")["vwap"].median().rename("price").reset_index()
    m = pd.merge(agg, px, left_on="hour", right_on="minute", how="left")

    if not _enough_points(m["hour"]):
        _warn(f"{chain} liquidations vs price: insufficient points")
        return

    fig, ax1 = plt.subplots(figsize=(12,4.4))
    ax1.bar(m["hour"], m["events"], alpha=0.35)
    ax1.set_ylabel("Events")
    ax1.set_xlabel("Time (UTC)")
    ax1.set_title(f"Liquidations vs Price — {chain}")

    ax2 = ax1.twinx()
    ax2.plot(m["hour"], _as_usdc_per_weth(m["price"]), alpha=0.9)
    ax2.set_ylabel("Price (USDC/WETH)")
    _savefig(os.path.join(PLOT_DIR, f"liquidations_vs_price_{chain}_{span}.png"))

def plot_swaps_volume(chain: str, span: int):
    df = load_swaps(chain, span)
    if df is None:
        return
    df = df.dropna(subset=["datetime"])
    if df.empty:
        _warn(f"{chain} swaps empty")
        return
    df["minute"] = df["datetime"].dt.floor("min")
    vol = df.groupby("minute")["size_token0"].sum().reset_index()
    if not _enough_points(vol["minute"]):
        _warn(f"{chain} swaps volume: insufficient points")
        return
    fig = plt.figure(figsize=(12,4.4))
    plt.plot(vol["minute"], vol["size_token0"])
    plt.title(f"Swap volume (|amount0| per minute) — {chain}, span {span}")
    plt.ylabel("Size (token0 units)")
    plt.xlabel("Time (UTC)")
    _savefig(os.path.join(PLOT_DIR, f"swaps_volume_{chain}_{span}.png"))

# ------------------------- main orchestration -------------------------

def main():
    """
    Default run with common parameters:
      span=500 (demo), fee=500, threshold=30bps, cost params fee=5bps bridge=10bps
    You can also customize: python -m src.visualize 1000
    """
    span = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    fee_tier = 500
    thr_bps = 30
    dex_fee_bps_each = 5
    bridge_bps = 10

    print(f"[viz] span={span}, fee_tier={fee_tier}, thr={thr_bps}bps, cost fee={dex_fee_bps_each}bps bridge={bridge_bps}bps")

    # 1) VWAP comparison + Spread
    plot_vwap_comparison(span)
    plot_spread_timeseries(span, thr_bps)
    plot_spread_hist(span)

    # 2) Cost-aware net opportunities
    plot_costed_net(span, dex_fee_bps_each, bridge_bps)

    # 3) Liquidity profile (both chains)
    for chain in ("ethereum", "arbitrum"):
        plot_liquidity_profile(chain, fee_tier)

    # 4) Liquidations vs price
    for chain in ("ethereum", "arbitrum"):
        plot_liquidations_vs_price(chain, 50000)

    # 5) Swap volume
    for chain in ("ethereum", "arbitrum"):
        plot_swaps_volume(chain, span)

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    main()