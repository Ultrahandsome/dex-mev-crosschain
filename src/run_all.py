from __future__ import annotations
import os, sys, subprocess, shlex

# ========= Unified default parameters =========
CHAINS = ["ethereum", "arbitrum"]

SPAN_SWAPS = 500      # swaps / price_series / mev_detect / crosschain / crosschain_cost
SPAN_AAVE  = 50000    # aave liquidations
LIDO_DAYS  = 7        # stETH returns
LP_FEE     = "500"    # liquidity profile fee tier
LP_WORDS   = "10"     # TickLens words_each_side

# Cost-aware cross-chain arbitrage parameters (defaults)
DEX_FEE_BPS_EACH   = "5"
GAS_USD_ETH        = "2.0"
GAS_USD_ARB        = "0.2"
BRIDGE_BPS         = "10"
MIN_TRADES_PER_MIN = "1"

# MEV detection (defaults)
MEV_MIN_BP = "10"
MEV_TOPN   = "10"

# Simple threshold cross-chain (defaults)
SPREAD_THR_BPS = "30"
# =================================

PYBIN = sys.executable
ROOT = os.path.dirname(os.path.dirname(__file__))
CSV_DIR = os.path.join(ROOT, "data", "csv")

def run_or_die(cmd: str):
    print("\n$ " + cmd, flush=True)
    try:
        subprocess.run(shlex.split(cmd), check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n[FAIL] exit={e.returncode}\n--> {cmd}\n", flush=True)
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\n[ABORT] interrupted by user.", flush=True)
        sys.exit(130)

def main():
    os.makedirs(CSV_DIR, exist_ok=True)

    # 1) check_rpc  — chain names only
    for chain in CHAINS:
        run_or_die(f"{PYBIN} -m src.check_rpc {chain}")

    # 2) get_pool   — chain names only (uses script internal defaults for pair/fees)
    for chain in CHAINS:
        run_or_die(f"{PYBIN} -m src.get_pool {chain}")

    # 3) spot_price — chain names only (internal defaults WETH:USDC, fees=[500,3000])
    for chain in CHAINS:
        run_or_die(f"{PYBIN} -m src.spot_price {chain}")

    # 4) swaps      — chain name + block span (rest uses defaults)
    for chain in CHAINS:
        run_or_die(f"{PYBIN} -m src.swaps --chain {chain} --blocks {SPAN_SWAPS}")

    # 5) price_series — chain name + block span
    for chain in CHAINS:
        run_or_die(f"{PYBIN} -m src.price_series --chain {chain} --blocks {SPAN_SWAPS}")

    # 6) crosschain (threshold version) — span + threshold + min trades only
    run_or_die(f"{PYBIN} -m src.crosschain --span {SPAN_SWAPS} --thr_bps {SPREAD_THR_BPS} --min_trades {MIN_TRADES_PER_MIN}")

    # 7) crosschain_cost (cost-aware) — all defaults
    run_or_die(f"{PYBIN} -m src.crosschain_cost --span {SPAN_SWAPS} --fee_bps_each_side {DEX_FEE_BPS_EACH} --gas_usd_eth {GAS_USD_ETH} --gas_usd_arb {GAS_USD_ARB} --bridge_bps {BRIDGE_BPS} --min_trades_per_min {MIN_TRADES_PER_MIN}")

    # 8) mev_detect — chain name + span + threshold + TopN
    for chain in CHAINS:
        run_or_die(f"{PYBIN} -m src.mev_detect --chain {chain} --span {SPAN_SWAPS} --min_bp {MEV_MIN_BP} --top {MEV_TOPN}")

    # 9) aave — chain name + liquidation span
    for chain in CHAINS:
        run_or_die(f"{PYBIN} -m src.aave --chain {chain} --blocks {SPAN_AAVE}")

    # 10) staking_lido — ethereum only + days
    run_or_die(f"{PYBIN} -m src.staking_lido --chain ethereum --days {LIDO_DAYS}")

    # 11) liquidity_profile — chain name + fee + words (pair uses script default WETH:USDC)
    for chain in CHAINS:
        run_or_die(f"{PYBIN} -m src.liquidity_profile --chain {chain} --pair WETH:USDC --fee {LP_FEE} --words_each_side {LP_WORDS}")

    # 12) visualize — generate plots from collected data
    print("\n=== Generating visualization plots ===")
    run_or_die(f"{PYBIN} -m src.visualize {SPAN_SWAPS}")

    # 13) analysis — generate comprehensive analysis figures
    print("\n=== Generating analysis figures ===")
    run_or_die(f"{PYBIN} -m src.analysis --span {SPAN_SWAPS} --thr_bps {SPREAD_THR_BPS} --fee_bps_each {DEX_FEE_BPS_EACH} --bridge_bps {BRIDGE_BPS} --mev_min_bp {MEV_MIN_BP} --liq_span {SPAN_AAVE} --staking_days {LIDO_DAYS}")

    print("\nALL DONE. Outputs ->", CSV_DIR)
    print("Figures -> data/figs/ and data/analysis/plots/")

if __name__ == "__main__":
    main()
