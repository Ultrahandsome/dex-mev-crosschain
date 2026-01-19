from __future__ import annotations
import argparse, sys, subprocess

def run_mod(mod: str, *args: str) -> int:
    cmd = [sys.executable, "-m", f"src.{mod}", *[str(a) for a in args]]
    return subprocess.run(cmd, check=False).returncode

def main():
    p = argparse.ArgumentParser(
        prog="dex-mev-crosschain",
        description="One-stop CLI for cross-chain DEX/MEV/Aave/Lido/UniV3 data collection & analysis"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # 1) Pool discovery (get_pool.py)
    sp = sub.add_parser("pools", help="Find Uniswap v3 pools by pair & fees and save pools_found.csv")
    sp.add_argument("--chain", required=True, choices=["ethereum","arbitrum","base"], help="Which chain")
    sp.add_argument("--pair",  required=True, help="e.g. WETH:USDC")
    sp.add_argument("--fees",  required=True, nargs="+", help="e.g. 500 3000")
    # 2) Spot price (spot_price.py)
    sp2 = sub.add_parser("spot", help="Fetch slot0 & compute spot price for configured pools")
    sp2.add_argument("--chain", required=True, choices=["ethereum","arbitrum","base"])
    # 3) Recent swaps (swaps.py)
    sp3 = sub.add_parser("swaps", help="Fetch recent Uniswap v3 Swap events to CSV")
    sp3.add_argument("--chain", required=True, choices=["ethereum","arbitrum","base"])
    sp3.add_argument("--blocks", type=int, default=2000, help="lookback blocks span (default: 2000)")
    # 4) Trade-by-trade -> minute prices (price_series.py)
    sp4 = sub.add_parser("price", help="Build minute VWAP series from swaps_{chain}_{span}.csv")
    sp4.add_argument("--chain", required=True, choices=["ethereum","arbitrum","base"])
    sp4.add_argument("--blocks", type=int, required=True, help="the same span you used for swaps")
    # 5) Cross-chain spread (crosschain_spread.py)
    sp5 = sub.add_parser("xspread", help="Join two chains' minute VWAP to compute cross-chain spread")
    sp5.add_argument("--span", type=int, required=True, help="block span used for price series")
    sp5.add_argument("--thr_bps", type=float, default=30.0, help="threshold bps for marking executable windows")
    # 6) Spread - cost filtering (crosschain_cost.py)
    sp6 = sub.add_parser("xcost", help="Apply fees/gas/bridge cost on cross-chain spread windows")
    sp6.add_argument("span", type=int, help="block span used for price series")
    sp6.add_argument("dex_fee_bps", type=float, help="per-side DEX taker fee in bps (e.g. 5)")
    sp6.add_argument("gas_usd", type=float, help="rough gas USD per side (e.g. 2.0)")
    sp6.add_argument("bridge_bps", type=float, help="bridge fee bps (e.g. 10)")
    sp6.add_argument("min_trades", type=int, help="min trades per minute for liquidity sanity (e.g. 1)")
    # 7) MEV detection (mev_detect.py)
    sp7 = sub.add_parser("mev", help="Heuristic detection of sandwich/backrun by (block,pool)")
    sp7.add_argument("--chain", required=True, choices=["ethereum","arbitrum","base"])
    sp7.add_argument("--blocks", type=int, required=True, help="span used for swaps")
    sp7.add_argument("--min_bp", type=float, default=5.0, help="min price move in bps (default 5)")
    sp7.add_argument("--top", type=int, default=10, help="print top-N actors (default 10)")
    # 8) Aave liquidations (aave.py)
    sp8 = sub.add_parser("aave", help="Fetch Aave V2 (ETH) / V3 (Arb) LiquidationCall events")
    sp8.add_argument("--chain", required=True, choices=["ethereum","arbitrum"])
    sp8.add_argument("--blocks", type=int, required=True)
    # 9) Lido stETH yields (staking_lido.py)
    sp9 = sub.add_parser("staking", help="Daily stETH share->ETH ratio & APY estimate")
    sp9.add_argument("--days", type=int, default=30)
    # 10) Uni v3 liquidity profile (liquidity_profile.py)
    sp10 = sub.add_parser("liquidity", help="TickLens-based active liquidity profile")
    sp10.add_argument("--chain", required=True, choices=["ethereum","arbitrum","base"])
    sp10.add_argument("--pair", required=True, help="e.g. WETH:USDC")
    sp10.add_argument("--fee", type=int, required=True, help="fee in bps, e.g. 500")
    sp10.add_argument("--words", type=int, default=10, help="words each side around current tick (default 10)")

    args = p.parse_args()

    if args.cmd == "pools":
        return sys.exit(run_mod("get_pool", args.chain, args.pair, *args.fees))
    if args.cmd == "spot":
        return sys.exit(run_mod("spot_price", args.chain))
    if args.cmd == "swaps":
        return sys.exit(run_mod("swaps", args.chain, args.blocks))
    if args.cmd == "price":
        return sys.exit(run_mod("price_series", args.chain, args.blocks))
    if args.cmd == "xspread":
        return sys.exit(run_mod("crosschain_spread", args.span, args.thr_bps))
    if args.cmd == "xcost":
        return sys.exit(run_mod("crosschain_cost", args.span, args.dex_fee_bps, args.gas_usd, args.bridge_bps, args.min_trades, 1))
    if args.cmd == "mev":
        return sys.exit(run_mod("mev_detect", args.chain, args.blocks, args.min_bp, args.top))
    if args.cmd == "aave":
        return sys.exit(run_mod("aave", args.chain, args.blocks))
    if args.cmd == "staking":
        return sys.exit(run_mod("staking_lido", "ethereum", args.days))
    if args.cmd == "liquidity":
        return sys.exit(run_mod("liquidity_profile", args.chain, args.pair, args.fee, args.words))

    p.print_help()
    return sys.exit(1)

if __name__ == "__main__":
    main()
