# src/analysis.py
from __future__ import annotations
import os, sys, argparse
from typing import List, Tuple, Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_DIR = os.path.join(ROOT, "data", "csv")
FIG_DIR = os.path.join(ROOT, "data", "figs")

# -------------------------------------------------
# Utilities
# -------------------------------------------------
def _ensure_dirs():
    os.makedirs(FIG_DIR, exist_ok=True)

def _read_csv(path: str, parse_dates: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
    if not os.path.exists(path):
        print(f"[skip] missing file: {os.path.relpath(path, ROOT)}")
        return None
    try:
        df = pd.read_csv(path, parse_dates=parse_dates)
        return df
    except Exception as e:
        print(f"[warn] failed to read {path}: {e}")
        return None

def _tscol(df: pd.DataFrame, candidates=("datetime","timestamp","time","date")) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None

def _savefig(name: str):
    out = os.path.join(FIG_DIR, name)
    plt.tight_layout()
    plt.savefig(out, dpi=140)
    plt.close()
    print(f"[fig] {os.path.relpath(out, ROOT)}")

# -------------------------------------------------
# 1) Price series (VWAP) & Cross-chain spread
# -------------------------------------------------
def plot_price_series(span: int):
    eth_path = os.path.join(CSV_DIR, f"price_series_ethereum_{span}.csv")
    arb_path = os.path.join(CSV_DIR, f"price_series_arbitrum_{span}.csv")
    eth = _read_csv(eth_path, parse_dates=["datetime"])
    arb = _read_csv(arb_path, parse_dates=["datetime"])
    if eth is None or arb is None: 
        return

    m = pd.merge(eth, arb, on="datetime", how="inner", suffixes=("_eth","_arb"))
    if m.empty:
        print("[skip] no overlap minutes between price series")
        return

    # line: prices
    plt.figure(figsize=(10,4))
    plt.plot(m["datetime"], m["vwap_eth"], label="Ethereum VWAP (USDC/WETH)")
    plt.plot(m["datetime"], m["vwap_arb"], label="Arbitrum VWAP (USDC/WETH)")
    plt.title(f"VWAP (USDC per WETH) — span {span} blocks")
    plt.xlabel("Time (UTC)"); plt.ylabel("Price (USDC/WETH)")
    plt.legend(); plt.grid(True, alpha=0.3)
    _savefig(f"price_vwap_eth_vs_arb_{span}.png")

    # spread series
    m["spread_bps"] = ( (m["vwap_eth"] - m["vwap_arb"]) / m["vwap_arb"] ) * 1e4
    plt.figure(figsize=(10,3.6))
    plt.plot(m["datetime"], m["spread_bps"])
    plt.axhline(0, ls="--", lw=1, color="k")
    plt.title(f"Cross-chain Spread (Ethereum vs Arbitrum) — bps, span {span}")
    plt.xlabel("Time (UTC)"); plt.ylabel("Spread (bps)")
    plt.grid(True, alpha=0.3)
    _savefig(f"spread_timeseries_{span}.png")

    # histogram
    plt.figure(figsize=(6.5,4))
    plt.hist(m["spread_bps"].dropna(), bins=60)
    plt.title(f"Distribution of Spread (bps) — span {span}")
    plt.xlabel("Spread (bps)"); plt.ylabel("Count")
    _savefig(f"spread_hist_{span}.png")

def plot_spread_threshold(span: int, thr_bps: float):
    path = os.path.join(CSV_DIR, f"crosschain_spread_{span}_thr{int(thr_bps)}bps.csv")
    df = _read_csv(path, parse_dates=["datetime"])
    if df is None or df.empty: 
        return
    plt.figure(figsize=(10,3.6))
    plt.plot(df["datetime"], df["spread_bps"], label="Spread (bps)")
    plt.axhline(thr_bps, color="red", ls="--", label=f"Threshold +{thr_bps:.0f} bps")
    plt.axhline(-thr_bps, color="red", ls="--", label=f"Threshold -{thr_bps:.0f} bps")
    plt.title(f"Spread vs Threshold (±{thr_bps:.0f} bps) — span {span}")
    plt.xlabel("Time (UTC)"); plt.ylabel("Spread (bps)")
    plt.legend(); plt.grid(True, alpha=0.3)
    _savefig(f"spread_threshold_{span}_thr{int(thr_bps)}bps.png")

def plot_costed_windows(span: int, fee_bps_each=5, bridge_bps=10):
    path = os.path.join(CSV_DIR, f"crosschain_cost_{span}_fee{int(fee_bps_each)}bps_bridge{int(bridge_bps)}bps.csv")
    df = _read_csv(path, parse_dates=["datetime"])
    if df is None or df.empty: 
        return
    # net bps timeline
    plt.figure(figsize=(10,3.6))
    plt.plot(df["datetime"], df["net_bps"], label="Net bps (spread - total cost)")
    plt.axhline(0, color="k", ls="--", lw=1)
    plt.title(f"Cost-aware Net Opportunity — span {span}, fee={fee_bps_each}bps, bridge={bridge_bps}bps")
    plt.xlabel("Time (UTC)"); plt.ylabel("Net bps")
    plt.grid(True, alpha=0.3); plt.legend()
    _savefig(f"net_bps_costed_{span}_fee{int(fee_bps_each)}_bridge{int(bridge_bps)}.png")

    # histogram of net
    plt.figure(figsize=(6.5,4))
    plt.hist(df["net_bps"].dropna(), bins=60)
    plt.title("Distribution of Net bps (after costs)")
    plt.xlabel("Net bps"); plt.ylabel("Count")
    _savefig(f"net_bps_hist_{span}_fee{int(fee_bps_each)}_bridge{int(bridge_bps)}.png")

# -------------------------------------------------
# 2) MEV: sandwich actors & price impact
# -------------------------------------------------
def plot_mev_summary(chain: str, span: int, min_bp: float):
    summ = _read_csv(os.path.join(CSV_DIR, f"mev_summary_{chain}_{span}_min{int(min_bp)}.csv"))
    if summ is None or summ.empty:
        return
    top = summ.sort_values("events", ascending=False).head(15)
    plt.figure(figsize=(9,4))
    plt.bar(top["actor"], top["events"])
    plt.xticks(rotation=70, ha="right", fontsize=8)
    plt.title(f"Top MEV sandwich actors — {chain}, span {span}, min {int(min_bp)} bps")
    plt.ylabel("Events"); plt.xlabel("Actor")
    _savefig(f"mev_top_actors_{chain}_{span}_min{int(min_bp)}.png")

    # price move distribution
    sus = _read_csv(os.path.join(CSV_DIR, f"mev_suspects_{chain}_{span}_min{int(min_bp)}.csv"))
    if sus is None or sus.empty:
        return
    if "price_move_bps" in sus.columns:
        plt.figure(figsize=(6.5,4))
        plt.hist(sus["price_move_bps"].dropna(), bins=60)
        plt.title(f"MEV Victim Price Move (bps) — {chain}")
        plt.xlabel("Price move (bps)"); plt.ylabel("Count")
        _savefig(f"mev_price_move_hist_{chain}_{span}_min{int(min_bp)}.png")

# -------------------------------------------------
# 3) Uniswap v3 Concentrated Liquidity
# -------------------------------------------------
def plot_liquidity_profile(chain: str, pair_tag="WETHUSDC", fee=500):
    path = os.path.join(CSV_DIR, f"liquidity_profile_{chain}_{pair_tag}_{fee}.csv")
    df = _read_csv(path)
    if df is None or df.empty:
        return
    # Active liquidity vs price
    plt.figure(figsize=(9,4))
    plt.plot(df["price_t1_per_t0"], df["active_liquidity"])
    plt.title(f"Active Liquidity across Price — {chain} {pair_tag} fee={fee}")
    plt.xlabel("Price (USDC per WETH)"); plt.ylabel("Active Liquidity")
    plt.grid(True, alpha=0.3)
    _savefig(f"liq_profile_active_{chain}_{pair_tag}_{fee}.png")

    # Net liquidity per tick (bar-like line)
    if "liquidity_net" in df.columns:
        plt.figure(figsize=(9,3.6))
        plt.plot(df["price_t1_per_t0"], df["liquidity_net"])
        plt.title(f"Net Liquidity by Price — {chain} {pair_tag} fee={fee}")
        plt.xlabel("Price (USDC per WETH)"); plt.ylabel("Net Liquidity")
        plt.grid(True, alpha=0.3)
        _savefig(f"liq_profile_net_{chain}_{pair_tag}_{fee}.png")

# -------------------------------------------------
# 4) Aave Liquidations vs Market
# -------------------------------------------------
def plot_liquidations(chain: str, span_liq: int, price_span: int):
    # liquidations
    liq = _read_csv(os.path.join(CSV_DIR, f"liquidations_{chain}_{span_liq}.csv"))
    if liq is None or liq.empty:
        return

    # timestamp to datetime (UTC)
    ts_col = _tscol(liq, candidates=("timestamp","datetime"))
    if ts_col is None:
        print(f"[skip] no timestamp column in liquidations_{chain}_{span_liq}.csv")
        return
    liq["ts"] = pd.to_datetime(liq[ts_col], unit="s", utc=True, errors="coerce")

    # aggregate: hourly count & seized amount
    liq["hour"] = liq["ts"].dt.floor("h")
    liq_agg = liq.groupby("hour").agg(events=("tx","count"),
                                      seized=("collateral_seized","sum")).reset_index()

    # price series on same chain
    ps = _read_csv(os.path.join(CSV_DIR, f"price_series_{chain}_{price_span}.csv"), parse_dates=["datetime"])
    if ps is None or ps.empty:
        # just plot events
        plt.figure(figsize=(10,3.6))
        plt.bar(liq_agg["hour"], liq_agg["events"], width=0.03)
        plt.title(f"Aave Liquidations — {chain}, hourly events")
        plt.xlabel("Time (UTC)"); plt.ylabel("Events")
        _savefig(f"liquidations_events_{chain}_{span_liq}.png")
        return

    # merge by nearest hour
    m = pd.merge_asof(liq_agg.sort_values("hour"),
                      ps.sort_values("datetime")[["datetime","vwap"]],
                      left_on="hour", right_on="datetime", direction="nearest")
    # plot with twin ax
    fig, ax1 = plt.subplots(figsize=(10,3.8))
    ax1.bar(m["hour"], m["events"], width=0.03, alpha=0.6, label="Liquidations (count)")
    ax1.set_ylabel("Events")
    ax2 = ax1.twinx()
    ax2.plot(m["hour"], m["vwap"], label="Price (USDC/WETH)")
    ax2.set_ylabel("Price (USDC/WETH)")
    ax1.set_title(f"Liquidations vs Price — {chain}")
    ax1.set_xlabel("Time (UTC)")
    ax1.grid(True, alpha=0.3)
    _savefig(f"liquidations_vs_price_{chain}_{span_liq}.png")

    # correlation: minute returns vs hourly liquidations
    ps2 = ps.copy()
    ps2["ret"] = ps2["vwap"].pct_change()
    ps2["hour"] = ps2["datetime"].dt.floor("h")
    r = pd.merge(ps2.groupby("hour")["ret"].mean().reset_index(),
                 liq_agg[["hour","events"]], on="hour", how="inner")
    if not r.empty:
        corr = r["ret"].corr(r["events"])
        stats_path = os.path.join(CSV_DIR, f"analysis_stats_{chain}.csv")
        pd.DataFrame([{"chain": chain, "corr_ret_vs_events": corr}]).to_csv(stats_path, index=False)
        print(f"[stat] corr(ret, events) {chain} = {corr:.4f} -> {os.path.relpath(stats_path, ROOT)}")

# -------------------------------------------------
# 5) Lido stETH yield
# -------------------------------------------------
def plot_staking(days: int):
    path = os.path.join(CSV_DIR, f"staking_returns_ethereum_{days}d.csv")
    df = _read_csv(path)
    if df is None or df.empty:
        return
    # share_to_eth
    plt.figure(figsize=(9,3.6))
    plt.plot(pd.to_datetime(df["date"]), df["share_to_eth"])
    plt.title(f"stETH Share → ETH (per 1e18 shares) — {days} days")
    plt.xlabel("Date (UTC)"); plt.ylabel("ETH per share")
    plt.grid(True, alpha=0.3)
    _savefig(f"staking_share_to_eth_{days}d.png")

    # apy_est
    if "apy_est" in df.columns:
        plt.figure(figsize=(9,3.6))
        plt.plot(pd.to_datetime(df["date"]), df["apy_est"]*100.0)
        plt.title(f"stETH APY (rough, annualized from daily) — {days} days")
        plt.xlabel("Date (UTC)"); plt.ylabel("APY (%)")
        plt.grid(True, alpha=0.3)
        _savefig(f"staking_apy_{days}d.png")

# -------------------------------------------------
# Runner
# -------------------------------------------------
def run_all(span:int, thr_bps:float, fee_bps_each:int, bridge_bps:int,
            mev_min_bp:float, liq_span:int, staking_days:int):
    _ensure_dirs()
    print("[run] price series & spreads ...")
    plot_price_series(span)
    plot_spread_threshold(span, thr_bps)
    plot_costed_windows(span, fee_bps_each, bridge_bps)

    print("[run] MEV summaries ...")
    for ch in ("ethereum","arbitrum"):
        plot_mev_summary(ch, span, mev_min_bp)

    print("[run] liquidity profiles ...")
    for ch in ("ethereum","arbitrum"):
        plot_liquidity_profile(ch, "WETHUSDC", 500)

    print("[run] Aave liquidations ...")
    for ch in ("ethereum","arbitrum"):
        plot_liquidations(ch, liq_span, price_span=span)

    print("[run] Lido staking ...")
    plot_staking(staking_days)

def main():
    ap = argparse.ArgumentParser(description="Generate figures from CSV outputs")
    ap.add_argument("--span", type=int, default=500, help="block span for price series & swaps (default: 500)")
    ap.add_argument("--thr_bps", type=float, default=30.0, help="spread threshold bps (default: 30)")
    ap.add_argument("--fee_bps_each", type=int, default=5, help="DEX fee per side bps for cost-aware (default: 5)")
    ap.add_argument("--bridge_bps", type=int, default=10, help="bridge cost bps (default: 10)")
    ap.add_argument("--mev_min_bp", type=float, default=10.0, help="MEV min price move bps (default: 10)")
    ap.add_argument("--liq_span", type=int, default=50000, help="Aave liquidation lookback blocks (default: 50000)")
    ap.add_argument("--staking_days", type=int, default=7, help="Lido staking recent days (default: 7)")
    args = ap.parse_args()

    run_all(span=args.span, thr_bps=args.thr_bps, fee_bps_each=args.fee_bps_each,
            bridge_bps=args.bridge_bps, mev_min_bp=args.mev_min_bp,
            liq_span=args.liq_span, staking_days=args.staking_days)

if __name__ == "__main__":
    main()