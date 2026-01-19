from __future__ import annotations
import os
import sys
import argparse
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_DIR = os.path.join(ROOT, "data", "csv")

def main():
    ap = argparse.ArgumentParser(
        description="Cross-chain price spread detection (ETH vs Arbitrum, WETH/USDC)"
    )
    ap.add_argument("--span", type=int, default=2000,
                    help="lookback blocks span (must match price_series filenames), default=2000")
    ap.add_argument("--thr_bps", type=float, default=30.0,
                    help="spread threshold in bps, default=30 (0.30%)")
    ap.add_argument("--min_trades", type=int, default=1,
                    help="minimum trades per minute to keep VWAP, default=1")
    args = ap.parse_args()

    span = int(args.span)
    thr_bps = float(args.thr_bps)
    min_trades = int(args.min_trades)

    # Read minute-level VWAP from both chains
    f_eth = os.path.join(CSV_DIR, f"price_series_ethereum_{span}.csv")
    f_arb = os.path.join(CSV_DIR, f"price_series_arbitrum_{span}.csv")
    if not (os.path.exists(f_eth) and os.path.exists(f_arb)):
        print("price series not found.")
        print(f"- expected {f_eth}")
        print(f"- expected {f_arb}")
        print("Run first: python3 -m src.price_series --chain ethereum --blocks {span}")
        print("           python3 -m src.price_series --chain arbitrum --blocks {span}")
        sys.exit(1)

    eth = pd.read_csv(f_eth, parse_dates=["datetime"])
    arb = pd.read_csv(f_arb, parse_dates=["datetime"])

    # Filter out minutes with too few trades
    eth = eth[(pd.to_numeric(eth["trades"], errors="coerce") >= min_trades) & eth["vwap"].notna()]
    arb = arb[(pd.to_numeric(arb["trades"], errors="coerce") >= min_trades) & arb["vwap"].notna()]

    # Align by time
    m = pd.merge(eth, arb, on="datetime", suffixes=("_eth", "_arb"))
    if m.empty:
        print("No overlapping minutes. Try a different span.")
        sys.exit(0)

    # Calculate spread (in bps)
    m["spread_pct"] = (m["vwap_eth"] - m["vwap_arb"]) / m["vwap_arb"]
    m["spread_bps"] = m["spread_pct"] * 1e4
    m["abs_spread_bps"] = m["spread_bps"].abs()

    # Mark executable windows
    m["executable"] = m["abs_spread_bps"] >= thr_bps

    # Direction hint
    def _dir(r):
        if r["spread_bps"] > 0:
            return "Buy ARB sell ETH"
        elif r["spread_bps"] < 0:
            return "Buy ETH sell ARB"
        return "flat"
    m["arb_direction"] = m.apply(_dir, axis=1)

    # Output
    out_path = os.path.join(CSV_DIR, f"crosschain_spread_{span}_thr{int(thr_bps)}bps.csv")
    cols = [
        "datetime",
        "vwap_eth","trades_eth",
        "vwap_arb","trades_arb",
        "spread_bps","abs_spread_bps","executable","arb_direction",
        "min_price_eth","max_price_eth","min_price_arb","max_price_arb"
    ]
    for c in ["min_price_eth","max_price_eth","min_price_arb","max_price_arb"]:
        if c not in m.columns:
            m[c] = None

    m[cols].to_csv(out_path, index=False)
    print(f"Saved: {out_path}  (rows={len(m)}, exec_windows={int(m['executable'].sum())})")

    # Print Top 10
    top = m[m["executable"]].sort_values("abs_spread_bps", ascending=False).head(10)
    if len(top):
        print("\nTop executable windows:")
        for _, r in top.iterrows():
            print(f"- {r['datetime']}  spread={r['spread_bps']:.1f} bps  dir={r['arb_direction']}")
    else:
        print("\nNo executable windows at current threshold.")

if __name__ == "__main__":
    main()