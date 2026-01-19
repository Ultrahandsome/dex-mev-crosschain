from __future__ import annotations
import os, sys
import argparse
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_DIR = os.path.join(ROOT, "data", "csv")

def _require_cols(df: pd.DataFrame, cols: list[str], name: str):
    miss = [c for c in cols if c not in df.columns]
    if miss:
        print(f"[ERR] {name} is missing required columns: {miss}")
        sys.exit(1)

def main():
    ap = argparse.ArgumentParser(
        description="Cross-chain arbitrage windows with cost model (ETH vs Arbitrum, WETH/USDC VWAP)"
    )
    ap.add_argument("--span", type=int, default=2000,
                    help="lookback blocks span that matches price_series filenames, default=2000")
    ap.add_argument("--fee_bps_each_side", type=float, default=5.0,
                    help="DEX fee (bps) per side, default=5")
    ap.add_argument("--gas_usd_eth", type=float, default=2.0,
                    help="gas cost per swap on Ethereum, USD, default=2.0")
    ap.add_argument("--gas_usd_arb", type=float, default=0.2,
                    help="gas cost per swap on Arbitrum, USD, default=0.2")
    ap.add_argument("--bridge_bps", type=float, default=10.0,
                    help="approx cross-chain/bridge cost in bps, default=10")
    ap.add_argument("--min_trades_per_min", type=int, default=1,
                    help="minimum trades per minute to consider VWAP valid, default=1")
    args = ap.parse_args()

    span = int(args.span)
    dex_fee_bps_each = float(args.fee_bps_each_side)
    gas_usd_eth = float(args.gas_usd_eth)
    gas_usd_arb = float(args.gas_usd_arb)
    bridge_bps = float(args.bridge_bps)
    min_trades = int(args.min_trades_per_min)

    # Read minute-level VWAP from both chains
    f_eth = os.path.join(CSV_DIR, f"price_series_ethereum_{span}.csv")
    f_arb = os.path.join(CSV_DIR, f"price_series_arbitrum_{span}.csv")
    if not os.path.exists(f_eth) or not os.path.exists(f_arb):
        print("price series not found.")
        print(f"- expected: {f_eth}")
        print(f"- expected: {f_arb}")
        print("Run first:")
        print(f"  python3 -m src.price_series --chain ethereum --blocks {span}")
        print(f"  python3 -m src.price_series --chain arbitrum --blocks {span}")
        sys.exit(1)

    eth = pd.read_csv(f_eth, parse_dates=["datetime"])
    arb = pd.read_csv(f_arb, parse_dates=["datetime"])

    _require_cols(eth, ["datetime","vwap","trades"], "ethereum price_series")
    _require_cols(arb, ["datetime","vwap","trades"], "arbitrum price_series")

    # Filter minutes with too few trades
    eth = eth[(pd.to_numeric(eth["trades"], errors="coerce") >= min_trades) & eth["vwap"].notna()].copy()
    arb = arb[(pd.to_numeric(arb["trades"], errors="coerce") >= min_trades) & arb["vwap"].notna()].copy()
    eth = eth.rename(columns={"vwap":"vwap_eth","trades":"trades_eth"})
    arb = arb.rename(columns={"vwap":"vwap_arb","trades":"trades_arb"})

    m = pd.merge(eth, arb, on="datetime", how="inner")
    if m.empty:
        print("No overlapping minutes between chains. Try a different span or ensure both series exist.")
        sys.exit(0)

    # Ensure numeric values
    for c in ["vwap_eth","vwap_arb","trades_eth","trades_arb"]:
        m[c] = pd.to_numeric(m[c], errors="coerce")

    # Price spread (normalized by ARB price), in bps
    m["spread_pct"] = (m["vwap_eth"] - m["vwap_arb"]) / m["vwap_arb"]
    m["spread_bps"] = m["spread_pct"] * 1e4
    m["abs_spread_bps"] = m["spread_bps"].abs()

    # —— Cost model (bps)
    # 1) DEX fees on both sides: round trip trades
    fees_total_bps = dex_fee_bps_each * 2.0

    # 2) Gas cost (USD) → convert to bps: gasUSD / reference_price(average of both chains) * 1e4
    m["mid_price_usd"] = (m["vwap_eth"] + m["vwap_arb"]) / 2.0
    m["gas_bps"] = (gas_usd_eth + gas_usd_arb) / m["mid_price_usd"] * 1e4

    # 3) Optional cross-chain bridge/capital cost approximation (bps)
    m["bridge_bps"] = bridge_bps

    # Total cost (bps) and net spread (bps)
    m["total_cost_bps"] = fees_total_bps + m["gas_bps"] + m["bridge_bps"]
    m["net_bps"] = m["abs_spread_bps"] - m["total_cost_bps"]

    # Executable: net spread > 0
    m["executable_costed"] = m["net_bps"] > 0

    # Direction indicator
    def _dir(r):
        if r["spread_bps"] > 0:
            return "Buy ARB sell ETH"
        elif r["spread_bps"] < 0:
            return "Buy ETH sell ARB"
        return "flat"
    m["arb_direction"] = m.apply(_dir, axis=1)

    # Output
    out_path = os.path.join(
        CSV_DIR,
        f"crosschain_cost_{span}_fee{int(dex_fee_bps_each)}bps_bridge{int(bridge_bps)}bps.csv"
    )
    cols = [
        "datetime",
        "vwap_eth","trades_eth",
        "vwap_arb","trades_arb",
        "spread_bps","abs_spread_bps",
        "mid_price_usd","gas_bps","bridge_bps","total_cost_bps",
        "net_bps","executable_costed","arb_direction"
    ]
    m[cols].to_csv(out_path, index=False)
    print(f"Saved: {out_path} (rows={len(m)}, exec_costed_windows={int(m['executable_costed'].sum())})")

    # Print Top 10 (by net bps)
    top = m[m["executable_costed"]].sort_values("net_bps", ascending=False).head(10)
    if len(top):
        print("\nTop cost-aware windows:")
        for _, r in top.iterrows():
            print(f"- {r['datetime']}  spread={r['spread_bps']:.1f} bps  cost={r['total_cost_bps']:.1f} bps  net≈{r['net_bps']:.1f} bps  dir={r['arb_direction']}")
    else:
        print("\nNo cost-aware executable windows under current params.")

if __name__ == "__main__":
    main()
