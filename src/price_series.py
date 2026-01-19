# src/price_series.py
from __future__ import annotations
import os
import sys
import argparse
import pandas as pd
from web3 import Web3
from .rpc import get_w3
from .blocktime import fetch_block_timestamps  # Parallel + local cache for block timestamps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_DIR = os.path.join(ROOT, "data", "csv")

def _compute_price_from_price_after(row) -> float | None:
    """
    Priority use price_after (post-event sqrtPrice derived price).
    We standardize output as USDC per WETH:
      - If token0=WETH, token1=USDC: price_after is already USDC/WETH, return directly
      - If token0=USDC, token1=WETH: price_after is WETH/USDC, need to take reciprocal
      - Other combinations: return None (this project focuses on WETH/USDC)
    """
    try:
        p = float(row.get("price_after", float("nan")))
    except Exception:
        return None
    if not (p and p > 0):
        return None

    s0 = str(row.get("token0_symbol", "")).upper()
    s1 = str(row.get("token1_symbol", "")).upper()
    if s0 == "WETH" and s1 == "USDC":
        return p
    if s0 == "USDC" and (s1 == "WETH" or s1 == "ETH"):
        return 1.0 / p
    # Not the target pair we care about
    return None

def _compute_price_from_amounts(row) -> float | None:
    """
    Fallback: infer USDC/WETH from trade amounts.
    Need to identify which side is WETH and which is USDC.
      - token0=WETH, token1=USDC:
           sell WETH get USDC: amount0<0, amount1>0 -> USDC/WETH = |a1|/|a0|
           sell USDC get WETH: amount1<0, amount0>0 -> USDC/WETH = |a0|/|a1|
      - token0=USDC, token1=WETH:
           sell WETH get USDC: amount1<0, amount0>0 -> USDC/WETH = |a0|/|a1|
           sell USDC get WETH: amount0<0, amount1>0 -> USDC/WETH = |a0|/|a1|
    """
    try:
        a0 = float(row["amount0"]); a1 = float(row["amount1"])
    except Exception:
        return None
    if a0 == 0 or a1 == 0:
        return None

    s0 = str(row.get("token0_symbol", "")).upper()
    s1 = str(row.get("token1_symbol", "")).upper()

    # token0=WETH, token1=USDC
    if s0 == "WETH" and s1 == "USDC":
        if a0 < 0 and a1 > 0:  # sell WETH get USDC
            return abs(a1) / abs(a0)
        if a1 < 0 and a0 > 0:  # sell USDC get WETH
            return abs(a0) / abs(a1)
        return None

    # token0=USDC, token1=WETH
    if s0 == "USDC" and (s1 == "WETH" or s1 == "ETH"):
        # Regardless of direction, USDC/WETH is always |USDC|/|WETH|
        usdc = abs(a0) if a0 != 0 else None
        weth = abs(a1) if a1 != 0 else None
        if usdc and weth:
            return usdc / weth
        return None

    return None

def compute_price(row) -> float | None:
    """
    Calculate trade price (USDC per WETH).
    First try price_after + sign to determine direction; if unavailable, fallback to amounts calculation.
    """
    p = _compute_price_from_price_after(row)
    if p and p > 0:
        return p
    return _compute_price_from_amounts(row)

def _trade_weight_weth(row) -> float:
    """
    VWAP weight: use absolute value of WETH trading volume.
      - If token0=WETH, use |amount0|
      - If token1=WETH, use |amount1|
      - Otherwise fallback to max(|a0|, |a1|)
    """
    try:
        a0 = float(row["amount0"]); a1 = float(row["amount1"])
    except Exception:
        return 0.0
    s0 = str(row.get("token0_symbol", "")).upper()
    s1 = str(row.get("token1_symbol", "")).upper()
    if s0 == "WETH":
        return abs(a0)
    if s1 == "WETH" or s1 == "ETH":
        return abs(a1)
    return max(abs(a0), abs(a1))

def main():
    ap = argparse.ArgumentParser(description="Build minute VWAP price series (USDC per WETH) from swaps CSV")
    ap.add_argument("--chain", default="ethereum", choices=["ethereum","arbitrum","base"],
                    help="blockchain to use, default=ethereum")
    ap.add_argument("--blocks", type=int, default=2000,
                    help="lookback blocks span that matches swaps CSV filename, default=2000")
    ap.add_argument("--freq", default="1Min",
                    help="resample frequency, default=1Min")
    args = ap.parse_args()

    chain = args.chain.lower()
    span = int(args.blocks)
    swaps_path = os.path.join(CSV_DIR, f"swaps_{chain}_{span}.csv")
    if not os.path.exists(swaps_path):
        print(f"swaps file not found: {swaps_path}\nPlease run: python3 -m src.swaps --chain {chain} --blocks {span}")
        sys.exit(1)

    df = pd.read_csv(swaps_path)
    if df.empty:
        print("no swaps data"); sys.exit(0)

    # Force numeric columns to be numeric to avoid string calculations
    for col in ["amount0", "amount1", "block", "log_index"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["amount0", "amount1", "block"])

    # ---------- Time column: prefer timestamp from swaps CSV ----------
    ts_col = None
    if "timestamp" in df.columns:
        ts_col = "timestamp"
        try:
            df["datetime"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        except Exception:
            ts_col = None

    # If no timestamp or parsing failed, fallback to parallel block timestamp fetch
    if ts_col is None:
        uniq_blocks = df["block"].astype(int).unique()
        ts_map = fetch_block_timestamps(chain, uniq_blocks, max_workers=6)
        df["datetime"] = df["block"].astype(int).map(ts_map)
        df["datetime"] = pd.to_datetime(df["datetime"], unit="s", utc=True, errors="coerce")

    # ---------- Per-trade price ----------
    df["price"] = df.apply(compute_price, axis=1)
    df = df[pd.notna(df["price"]) & (df["price"] > 0)].copy()

    # ---------- Weight ----------
    df["w"] = df.apply(_trade_weight_weth, axis=1)

    # ---------- Aggregate by frequency (VWAP / trades / min/max) ----------
    def agg_func(g: pd.DataFrame) -> pd.Series:
        wsum = g["w"].sum()
        vwap = (g["price"] * g["w"]).sum() / wsum if wsum > 0 else None
        return pd.Series({
            "vwap": vwap,
            "trades": int(len(g)),
            "min_price": g["price"].min(),
            "max_price": g["price"].max()
        })

    out = df.groupby(pd.Grouper(key="datetime", freq=args.freq)).apply(agg_func).reset_index()

    out_path = os.path.join(CSV_DIR, f"price_series_{chain}_{span}.csv")
    out.to_csv(out_path, index=False)
    print(f"Saved: {out_path}, rows={len(out)}")

if __name__ == "__main__":
    main()
