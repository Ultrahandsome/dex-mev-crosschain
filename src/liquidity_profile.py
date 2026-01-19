from __future__ import annotations
import os, sys, csv, math, time, argparse
import pandas as pd
from typing import List, Tuple, Dict, Any, Optional
from web3 import Web3

from .rpc import get_w3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---------------- Minimal ABIs ----------------
ABI_POOL = [
    {"inputs":[{"internalType":"uint256","name":"index","type":"uint256"}],
     "name":"ticks","outputs":[
        {"internalType":"uint128","name":"liquidityGross","type":"uint128"},
        {"internalType":"int128","name":"liquidityNet","type":"int128"},
        {"internalType":"uint256","name":"feeGrowthOutside0X128","type":"uint256"},
        {"internalType":"uint256","name":"feeGrowthOutside1X128","type":"uint256"},
        {"internalType":"int56","name":"tickCumulativeOutside","type":"int56"},
        {"internalType":"uint160","name":"secondsPerLiquidityOutsideX128","type":"uint160"},
        {"internalType":"uint32","name":"secondsOutside","type":"uint32"},
        {"internalType":"bool","name":"initialized","type":"bool"}
     ],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"slot0","outputs":[
        {"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},
        {"internalType":"int24","name":"tick","type":"int24"},
        {"internalType":"uint16","name":"observationIndex","type":"uint16"},
        {"internalType":"uint16","name":"observationCardinality","type":"uint16"},
        {"internalType":"uint16","name":"observationCardinalityNext","type":"uint16"},
        {"internalType":"uint8","name":"feeProtocol","type":"uint8"},
        {"internalType":"bool","name":"unlocked","type":"bool"}
    ],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"tickSpacing","outputs":[{"internalType":"int24","name":"","type":"int24"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"liquidity","outputs":[{"internalType":"uint128","name":"","type":"uint128"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"token0","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"token1","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
]

# Uniswap v3 Factory (getPool)
ABI_FACTORY = [
    {"inputs":[
        {"internalType":"address","name":"tokenA","type":"address"},
        {"internalType":"address","name":"tokenB","type":"address"},
        {"internalType":"uint24","name":"fee","type":"uint24"}],
     "name":"getPool",
     "outputs":[{"internalType":"address","name":"pool","type":"address"}],
     "stateMutability":"view","type":"function"}
]

ABI_ERC20 = [
    {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
]

# TickLens
ABI_TICKLENS = [
    {"inputs":[
        {"internalType":"address","name":"pool","type":"address"},
        {"internalType":"int16","name":"tickBitmapIndex","type":"int16"}],
     "name":"getPopulatedTicksInWord",
     "outputs":[
        {"components":[
            {"internalType":"int24","name":"tick","type":"int24"},
            {"internalType":"int128","name":"liquidityNet","type":"int128"},
            {"internalType":"uint128","name":"liquidityGross","type":"uint128"}],
         "internalType":"struct ITickLens.PopulatedTick[]",
         "name":"populatedTicks","type":"tuple[]"}],
     "stateMutability":"view","type":"function"}
]

# ---------------- Constants ----------------
UNIV3_FACTORY = "0x1F98431c8aD98523631AE4a59f267346ea31F984"

# Official TickLens contract (same address across chains)
TICKLENS_BY_CHAIN = {
    "ethereum": "0xbfd8137f7d1516d3ea5ca83523914859ec47f573",
    "arbitrum": "0xbfd8137f7d1516d3ea5ca83523914859ec47f573",
    "base":     "0xbfd8137f7d1516d3ea5ca83523914859ec47f573",
}

# Fallback token addresses (if not configured locally)
DEFAULT_TOKENS = {
    "ethereum": {
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    },
    "arbitrum": {
        "WETH": "0x82aF49447D8a07E3bd95BD0d56f35241523fBab1",
        "USDC": "0xAf88d065e77c8cC2239327C5EDb3A432268e5831",  # Native USDC
    },
    "base": {
        "WETH": "0x4200000000000000000000000000000000000006",
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    },
}

# ---------------- Helpers ----------------
def normalize_pair(p: str) -> str:
    return p.replace("/", ":").replace(" ", "").upper()

def price_from_tick(tick: int, decimals0: int, decimals1: int) -> float:
    # price = token1 per token0
    return (1.0001 ** tick) * (10 ** (decimals0 - decimals1))

def load_pools_found(chain: str) -> Optional[pd.DataFrame]:
    # First try chain-specific file
    chain_path = os.path.join(ROOT, "data", "csv", f"pools_found_{chain}.csv")
    if os.path.exists(chain_path):
        return pd.read_csv(chain_path)
    
    # Fallback to old unified file (backward compatibility)
    unified_path = os.path.join(ROOT, "data", "csv", "pools_found.csv")
    if os.path.exists(unified_path):
        df = pd.read_csv(unified_path)
        # Only return data for current chain
        return df[df["chain"].str.lower() == chain.lower()]
    
    return None

def try_pool_from_csv(df: pd.DataFrame, chain: str, pair: str, fee: int) -> Optional[str]:
    """
    Flexible matching: prioritize chain+pair+fee; if no pair column, take first match by chain+fee.
    """
    chain_mask = df["chain"].astype(str).str.lower() == chain.lower()
    fee_mask = df["fee"].astype(int) == int(fee)

    if "pair" in df.columns:
        pnorm = normalize_pair(pair)
        pair_mask = df["pair"].astype(str).str.replace("/",":").str.upper() == pnorm
        cand = df[chain_mask & fee_mask & pair_mask]
    else:
        cand = df[chain_mask & fee_mask]

    if cand.empty:
        return None
    return str(cand.iloc[0]["pool"])

def load_token_addrs(chain: str, pair: str) -> Tuple[str, str]:
    """
    Try to read from configs/addresses.yaml; if not found, use DEFAULT_TOKENS.
    """
    t0, t1 = normalize_pair(pair).split(":")
    # Prioritize local address configuration
    yml = os.path.join(ROOT, "configs", "addresses.yaml")
    if os.path.exists(yml):
        try:
            import yaml
            with open(yml, "r") as f:
                data = yaml.safe_load(f)
            cd = data.get(chain, {})
            addrs = {k.upper(): v for k, v in cd.items() if isinstance(k, str)}
            a0 = addrs.get(t0) or addrs.get(t0.upper())
            a1 = addrs.get(t1) or addrs.get(t1.upper())
            if a0 and a1:
                return a0, a1
        except Exception:
            pass
    # Fallback
    if chain in DEFAULT_TOKENS and t0 in DEFAULT_TOKENS[chain] and t1 in DEFAULT_TOKENS[chain]:
        return DEFAULT_TOKENS[chain][t0], DEFAULT_TOKENS[chain][t1]
    raise RuntimeError(f"No token addresses for chain={chain}, pair={pair}. Please fill configs/addresses.yaml.")

def resolve_pool(chain: str, pair: str, fee: int, w3: Web3) -> str:
    """
    Resolve pool address: first try pools_found_{chain}.csv; fallback to Factory.getPool(token0, token1, fee).
    """
    df = load_pools_found(chain)
    if df is not None and all(c in df.columns for c in ["chain","fee","pool"]):
        addr = try_pool_from_csv(df, chain, pair, fee)
        if addr:
            return Web3.to_checksum_address(addr)

    # CSV unavailable → Factory resolution
    t0_addr, t1_addr = load_token_addrs(chain, pair)
    # Uniswap v3 requires token0 < token1 (sorted by address)
    a0 = Web3.to_checksum_address(t0_addr)
    a1 = Web3.to_checksum_address(t1_addr)
    token0, token1 = (a0, a1) if a0.lower() < a1.lower() else (a1, a0)

    factory = w3.eth.contract(address=Web3.to_checksum_address(UNIV3_FACTORY), abi=ABI_FACTORY)
    pool = factory.functions.getPool(token0, token1, int(fee)).call()
    if int(pool, 16) == 0:
        raise RuntimeError(f"Factory.getPool returned 0x0 for {pair} fee={fee} on {chain}.")
    return Web3.to_checksum_address(pool)

def fetch_token_meta(w3: Web3, addr: str) -> Tuple[str, int]:
    c = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=ABI_ERC20)
    try:
        sym = c.functions.symbol().call()
    except Exception:
        sym = "UNK"
    try:
        dec = c.functions.decimals().call()
    except Exception:
        dec = 18
    return sym, int(dec)

def tick_to_word(t: int, tick_spacing: int) -> int:
    return math.floor(t / (tick_spacing * 256))

def get_populated_ticks_around(w3: Web3, pool_addr: str, current_tick: int, tick_spacing: int,
                               words_each_side: int, ticklens_addr: str) -> List[Dict[str, Any]]:
    lens = w3.eth.contract(address=Web3.to_checksum_address(ticklens_addr), abi=ABI_TICKLENS)
    center = tick_to_word(current_tick, tick_spacing)
    results: List[Dict[str, Any]] = []
    for off in range(-words_each_side, words_each_side + 1):
        idx = int(center + off)
        try:
            ticks = lens.functions.getPopulatedTicksInWord(Web3.to_checksum_address(pool_addr), idx).call()
        except Exception:
            ticks = []
        for t in ticks:
            results.append({
                "tick": int(t[0]),
                "liquidityNet": int(t[1]),
                "liquidityGross": int(t[2]),
                "word_index": idx,
            })
        time.sleep(0.02)
    if results:
        df = pd.DataFrame(results).drop_duplicates(subset=["tick"]).sort_values("tick")
        return df.to_dict(orient="records")
    return results

def reconstruct_liquidity_profile(ticks: List[Dict[str, Any]], current_tick: int, L_current: int) -> pd.DataFrame:
    if not ticks:
        return pd.DataFrame(columns=["tick", "liquidity_net", "liquidity_gross", "active_liquidity","word_index"])
    df = pd.DataFrame(ticks).sort_values("tick").reset_index(drop=True)
    df["liquidity_net"] = df["liquidityNet"].astype("int64")
    df["liquidity_gross"] = df["liquidityGross"].astype("int64")
    df = df[["tick","liquidity_net","liquidity_gross","word_index"]]

    # Above current tick (>= current_tick)
    up = df[df["tick"] >= current_tick].copy().reset_index(drop=True)
    L = int(L_current)
    active_vals_up = []
    for _, r in up.iterrows():
        active_vals_up.append(L)
        L += int(r["liquidity_net"])
    up["active_liquidity"] = active_vals_up

    # Below current tick (< current_tick), reverse order
    down = df[df["tick"] < current_tick].copy().sort_values("tick", ascending=False).reset_index(drop=True)
    L = int(L_current)
    active_vals_down = []
    for _, r in down.iterrows():
        active_vals_down.append(L)
        L -= int(r["liquidity_net"])
    down["active_liquidity"] = active_vals_down

    prof = pd.concat([down.sort_values("tick"), up], ignore_index=True)
    return prof[["tick","liquidity_net","liquidity_gross","active_liquidity","word_index"]].sort_values("tick").reset_index(drop=True)

def run(chain: str, pair: str, fee: int, words_each_side: int = 10):
    w3 = get_w3(chain)

    # Resolve pool address (CSV -> Factory fallback)
    pool_addr = resolve_pool(chain, pair, fee, w3)

    # Instantiate pool
    pool = w3.eth.contract(address=Web3.to_checksum_address(pool_addr), abi=ABI_POOL)
    sqrtPriceX96, current_tick, *_ = pool.functions.slot0().call()
    tick_spacing = pool.functions.tickSpacing().call()
    L_current = pool.functions.liquidity().call()
    token0 = pool.functions.token0().call()
    token1 = pool.functions.token1().call()
    sym0, dec0 = fetch_token_meta(w3, token0)
    sym1, dec1 = fetch_token_meta(w3, token1)

    # TickLens
    lens_addr = TICKLENS_BY_CHAIN.get(chain)
    if not lens_addr:
        raise RuntimeError(f"No TickLens address configured for chain {chain}")

    ticks = get_populated_ticks_around(
        w3=w3,
        pool_addr=pool_addr,
        current_tick=int(current_tick),
        tick_spacing=int(tick_spacing),
        words_each_side=words_each_side,
        ticklens_addr=lens_addr
    )

    prof = reconstruct_liquidity_profile(ticks, int(current_tick), int(L_current))
    prof["price_t1_per_t0"] = prof["tick"].apply(lambda t: price_from_tick(int(t), dec0, dec1))

    tag = normalize_pair(pair).replace(":", "")
    out_path = os.path.join(ROOT, "data", "csv", f"liquidity_profile_{chain}_{tag}_{fee}.csv")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    prof.to_csv(out_path, index=False, columns=["tick","price_t1_per_t0","liquidity_net","liquidity_gross","active_liquidity","word_index"])

    print(f"[{chain}] pool={pool_addr}")
    print(f"token0={sym0}({dec0}) token1={sym1}({dec1}) tickSpacing={tick_spacing} current_tick={current_tick} liquidity={L_current}")
    print(f"Saved: {out_path} (rows={len(prof)})")

def main():
    ap = argparse.ArgumentParser(description="Build Uniswap v3 concentrated-liquidity profile using TickLens")
    ap.add_argument("--chain", default="ethereum", choices=["ethereum","arbitrum","base"], help="default=ethereum")
    ap.add_argument("--pair",  default="WETH:USDC", help="token pair, default=WETH:USDC")
    ap.add_argument("--fee",   type=int, default=500, help="fee tier in bps, default=500")
    ap.add_argument("--words_each_side", type=int, default=10, help="how many tick bitmap words to fetch on each side, default=10")
    args = ap.parse_args()

    run(chain=args.chain, pair=args.pair, fee=int(args.fee), words_each_side=int(args.words_each_side))

if __name__ == "__main__":
    main()
