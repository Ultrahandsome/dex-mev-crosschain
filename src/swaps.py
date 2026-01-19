from __future__ import annotations
import os, sys, math, time, argparse
from typing import List, Tuple, Dict, Any, Optional
import pandas as pd
from web3 import Web3

from .rpc import get_w3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_DIR = os.path.join(ROOT, "data", "csv")

# ---------------- Minimal ABIs ----------------
ABI_FACTORY = [
    {"inputs":[
        {"internalType":"address","name":"tokenA","type":"address"},
        {"internalType":"address","name":"tokenB","type":"address"},
        {"internalType":"uint24","name":"fee","type":"uint24"}],
     "name":"getPool",
     "outputs":[{"internalType":"address","name":"pool","type":"address"}],
     "stateMutability":"view","type":"function"}
]

ABI_POOL = [
    {"inputs":[],"name":"slot0","outputs":[
        {"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},
        {"internalType":"int24","name":"tick","type":"int24"},
        {"internalType":"uint16","name":"observationIndex","type":"uint16"},
        {"internalType":"uint16","name":"observationCardinality","type":"uint16"},
        {"internalType":"uint16","name":"observationCardinalityNext","type":"uint16"},
        {"internalType":"uint8","name":"feeProtocol","type":"uint8"},
        {"internalType":"bool","name":"unlocked","type":"bool"}
    ],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"liquidity","outputs":[{"internalType":"uint128","name":"","type":"uint128"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"token0","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"token1","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"fee","outputs":[{"internalType":"uint24","name":"","type":"uint24"}],"stateMutability":"view","type":"function"},
    {"anonymous":False,"inputs":[
        {"indexed":True,"internalType":"address","name":"sender","type":"address"},
        {"indexed":True,"internalType":"address","name":"recipient","type":"address"},
        {"indexed":False,"internalType":"int256","name":"amount0","type":"int256"},
        {"indexed":False,"internalType":"int256","name":"amount1","type":"int256"},
        {"indexed":False,"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},
        {"indexed":False,"internalType":"uint128","name":"liquidity","type":"uint128"},
        {"indexed":False,"internalType":"int24","name":"tick","type":"int24"}],
     "name":"Swap","type":"event"}
]

ABI_ERC20 = [
    {"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
]

UNIV3_FACTORY = "0x1F98431c8aD98523631AE4a59f267346ea31F984"

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

def normalize_pair(p: str) -> str:
    return p.replace("/", ":").replace(" ", "").upper()

def ordered_tokens(addrA: str, addrB: str) -> Tuple[str,str]:
    # Uniswap v3 convention: token0 < token1 (by address)
    return (addrA, addrB) if addrA.lower() < addrB.lower() else (addrB, addrA)

def get_pool_address(w3: Web3, factory_addr: str, tokenA: str, tokenB: str, fee: int) -> str:
    factory = w3.eth.contract(address=Web3.to_checksum_address(factory_addr), abi=ABI_FACTORY)
    t0, t1 = ordered_tokens(tokenA, tokenB)
    # Ensure correct address format
    t0 = Web3.to_checksum_address(t0)
    t1 = Web3.to_checksum_address(t1)
    pool = factory.functions.getPool(t0, t1, fee).call()
    return pool

def get_token_meta(w3: Web3, token_addr: str) -> Tuple[str, int]:
    erc20 = w3.eth.contract(address=Web3.to_checksum_address(token_addr), abi=ABI_ERC20)
    try:
        sym = erc20.functions.symbol().call()
    except Exception:
        sym = "UNKNOWN"
    try:
        dec = erc20.functions.decimals().call()
    except Exception:
        dec = 18
    return sym, int(dec)

def price_from_sqrtPriceX96(sqrtPriceX96: int, dec0: int, dec1: int) -> float:
    # price = (sqrtPriceX96^2 / 2^192) * 10^(dec0 - dec1)
    ratio = (sqrtPriceX96 ** 2) / (2 ** 192)
    return ratio * (10 ** (dec0 - dec1))

def ensure_pools(w3: Web3, chain: str, pair: str, fees: List[int]) -> List[Tuple[str, int]]:
    """Ensure pool addresses exist, return (pool_addr, fee) list"""
    if chain.lower() not in DEFAULT_TOKENS:
        print(f"[ERR] unsupported chain: {chain}")
        return []
    
    pair_norm = normalize_pair(pair)
    tokens = pair_norm.split(":")
    if len(tokens) != 2:
        print(f"[ERR] invalid pair format: {pair}")
        return []
    
    t0_sym, t1_sym = tokens[0], tokens[1]
    chain_tokens = DEFAULT_TOKENS[chain.lower()]
    
    if t0_sym not in chain_tokens or t1_sym not in chain_tokens:
        print(f"[ERR] unsupported tokens {t0_sym}:{t1_sym} for chain {chain}")
        return []
    
    # Ensure correct address format
    t0_addr = Web3.to_checksum_address(chain_tokens[t0_sym])
    t1_addr = Web3.to_checksum_address(chain_tokens[t1_sym])
    
    pools = []
    for fee in fees:
        pool_addr = get_pool_address(w3, UNIV3_FACTORY, t0_addr, t1_addr, fee)
        if pool_addr and pool_addr != "0x0000000000000000000000000000000000000000":
            pools.append((pool_addr, fee))
        else:
            print(f"[WARN] pool not found for {pair} fee={fee}")
    
    return pools

def fetch_swaps_for_pool(w3: Web3, chain: str, pool_addr: str, fee: int, from_block: int, to_block: int) -> List[Dict[str,Any]]:
    """Fetch Swap events from specified pool"""
    pool = w3.eth.contract(address=Web3.to_checksum_address(pool_addr), abi=ABI_POOL)
    
    # Get token information
    token0 = pool.functions.token0().call()
    token1 = pool.functions.token1().call()
    token0_sym, token0_dec = get_token_meta(w3, token0)
    token1_sym, token1_dec = get_token_meta(w3, token1)
    
    rows = []
    step = 1000  # Block range per query
    
    for start in range(from_block, to_block + 1, step):
        end = min(start + step - 1, to_block)
        
        try:
            # Get Swap events
            logs = w3.eth.get_logs({
                'fromBlock': start,
                'toBlock': end,
                'address': pool_addr,
                'topics': ['0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67']  # Swap event signature
            })
            
            for log in logs:
                # Parse Swap events
                decoded = pool.events.Swap().process_log(log)
                args = decoded['args']
                
                # Calculate price
                sqrtPriceX96 = args['sqrtPriceX96']
                price_after = price_from_sqrtPriceX96(sqrtPriceX96, token0_dec, token1_dec)
                
                # Get block timestamp
                block = w3.eth.get_block(log['blockNumber'])
                timestamp = block['timestamp']
                
                # Convert amounts to float
                amount0 = float(args['amount0']) / (10 ** token0_dec)
                amount1 = float(args['amount1']) / (10 ** token1_dec)
                
                rows.append({
                    'timestamp': timestamp,
                    'block': log['blockNumber'],
                    'tx': log['transactionHash'].hex(),
                    'log_index': log['logIndex'],
                    'chain': chain,
                    'pool': pool_addr,
                    'fee': fee,
                    'token0': token0,
                    'token1': token1,
                    'token0_symbol': token0_sym,
                    'token1_symbol': token1_sym,
                    'amount0': amount0,
                    'amount1': amount1,
                    'price_after': price_after,
                    'tick_after': args['tick'],
                    'liquidity_after': args['liquidity'],
                    'sender': args['sender'],
                    'recipient': args['recipient'],
                    'sqrtPriceX96': sqrtPriceX96,
                    'decimals0': token0_dec,
                    'decimals1': token1_dec
                })
                
        except Exception as e:
            print(f"[WARN] error fetching blocks {start}-{end}: {e}")
            continue
    
    return rows

def main():
    ap = argparse.ArgumentParser(description="Fetch Uniswap v3 Swap events to CSV (with pool & fee columns)")
    ap.add_argument("--chain", default="ethereum", choices=["ethereum","arbitrum","base"],
                    help="blockchain to query, default=ethereum")
    ap.add_argument("--blocks", type=int, default=2000,
                    help="lookback blocks span, default=2000")
    ap.add_argument("--pair", default="WETH:USDC",
                    help="token pair, default=WETH:USDC")
    ap.add_argument("--fees", nargs="+", type=int, default=[500, 3000],
                    help="fee tiers in bps, default 500 3000")
    args = ap.parse_args()

    w3 = get_w3(args.chain)

    latest = int(w3.eth.block_number)
    from_block = max(1, latest - int(args.blocks))
    to_block = latest
    print(f"[{args.chain}] fetching swaps for {args.pair} fees={args.fees} blocks {from_block}..{to_block}")

    pools = ensure_pools(w3, args.chain, args.pair, args.fees)
    if not pools:
        print("[ERR] no pools to fetch")
        sys.exit(1)

    all_rows: List[Dict[str,Any]] = []
    for pool_addr, fee in pools:
        print(f"  -> pool {pool_addr} (fee={fee})")
        rows = fetch_swaps_for_pool(w3, args.chain, pool_addr, fee, from_block, to_block)
        print(f"     fetched {len(rows)} swaps")
        all_rows.extend(rows)

    os.makedirs(CSV_DIR, exist_ok=True)
    out = os.path.join(CSV_DIR, f"swaps_{args.chain}_{int(args.blocks)}.csv")
    if all_rows:
        df = pd.DataFrame(all_rows)
        df.sort_values(["block","log_index","pool"], inplace=True)
        df.to_csv(out, index=False)
        print(f"Saved: {out} (rows={len(df)})")
    else:
        cols = ["timestamp","block","tx","log_index","chain","pool","fee","token0","token1","token0_symbol","token1_symbol",
                "amount0","amount1","price_after","tick_after","liquidity_after","sender","recipient","sqrtPriceX96","decimals0","decimals1"]
        pd.DataFrame(columns=cols).to_csv(out, index=False)
        print(f"Saved: {out} (rows=0)")

if __name__ == "__main__":
    main()