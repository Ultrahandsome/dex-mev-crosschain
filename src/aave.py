from __future__ import annotations
import os, sys, csv, time, argparse
from typing import List, Dict
from web3 import Web3
from .rpc import get_w3
from .blocktime import fetch_block_timestamps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_DIR = os.path.join(ROOT, "data", "csv")

# -----------------------------
# Chain -> Aave version & provider mapping
# -----------------------------
CHAIN_AAVE = {
    # Ethereum mainnet: Aave V2
    "ethereum": {
        "version": "v2",
        "provider": "0xb53c1a33016b2dc2ff3653530bff1848a515c8c5",  # LendingPoolAddressesProvider (V2)
        "provider_fn": "getLendingPool",
        # V2 LiquidationCall event (3 indexed topics)
        "pool_event_abi": [
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True,  "internalType": "address", "name": "collateral", "type": "address"},
                    {"indexed": True,  "internalType": "address", "name": "principal",  "type": "address"},
                    {"indexed": True,  "internalType": "address", "name": "user",       "type": "address"},
                    {"indexed": False, "internalType": "uint256", "name": "purchaseAmount",              "type": "uint256"},
                    {"indexed": False, "internalType": "uint256", "name": "liquidatedCollateralAmount", "type": "uint256"},
                    {"indexed": False, "internalType": "address", "name": "liquidator", "type": "address"},
                    {"indexed": False, "internalType": "bool",    "name": "receiveAToken", "type": "bool"}
                ],
                "name": "LiquidationCall",
                "type": "event"
            }
        ],
    },
    # Arbitrum One：Aave V3
    "arbitrum": {
        "version": "v3",
        "provider": "0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb",  # PoolAddressesProvider (V3)
        "provider_fn": "getPool",
        # V3 LiquidationCall event (3 indexed topics)
        "pool_event_abi": [
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True,  "internalType": "address", "name": "collateral", "type": "address"},
                    {"indexed": True,  "internalType": "address", "name": "debt",       "type": "address"},
                    {"indexed": True,  "internalType": "address", "name": "user",       "type": "address"},
                    {"indexed": False, "internalType": "uint256", "name": "debtToCover",                  "type": "uint256"},
                    {"indexed": False, "internalType": "uint256", "name": "liquidatedCollateralAmount",   "type": "uint256"},
                    {"indexed": False, "internalType": "address", "name": "liquidator", "type": "address"},
                    {"indexed": False, "internalType": "bool",    "name": "receiveAToken", "type": "bool"}
                ],
                "name": "LiquidationCall",
                "type": "event"
            }
        ],
    },
}

# Provider ABIs
ABI_PROVIDER_GET_POOL = [
    {
        "inputs": [],
        "name": "getPool",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    }
]

ABI_PROVIDER_GET_LENDING_POOL = [
    {
        "inputs": [],
        "name": "getLendingPool",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    }
]


def get_pool_address_via_provider(w3: Web3, provider_addr: str, provider_fn: str) -> str:
    """Get Pool address through Provider in different versions."""
    if provider_fn == "getPool":
        provider = w3.eth.contract(address=Web3.to_checksum_address(provider_addr), abi=ABI_PROVIDER_GET_POOL)
        return provider.functions.getPool().call()
    elif provider_fn == "getLendingPool":
        provider = w3.eth.contract(address=Web3.to_checksum_address(provider_addr), abi=ABI_PROVIDER_GET_LENDING_POOL)
        return provider.functions.getLendingPool().call()
    else:
        raise ValueError(f"Unsupported provider function: {provider_fn}")


def fetch_liquidations(
    chain: str,
    pool_addr: str,
    from_block: int,
    to_block: int,
    w3: Web3,
    event_abi: List[dict],
    step: int = 800,
) -> List[Dict]:
    """
    Fetch LiquidationCall events in chunks, compatible with V2 / V3.
    """
    pool = w3.eth.contract(address=Web3.to_checksum_address(pool_addr), abi=event_abi)
    event = pool.events.LiquidationCall()
    rows: List[Dict] = []

    start = from_block
    while start <= to_block:
        end = min(start + step - 1, to_block)
        logs = []
        for attempt in range(4):
            try:
                logs = event.get_logs(fromBlock=start, toBlock=end)
                break
            except ValueError as e:
                msg = str(e)
                # Common: range too large / rate limiting
                if "range is too large" in msg and step > 200:
                    step = max(200, step // 2)
                    continue
                time.sleep(0.8 * (attempt + 1))
                if attempt == 3:
                    print(f"[warn] get_logs failed range {start}-{end}: {e}")
            except Exception as e:
                time.sleep(0.8 * (attempt + 1))
                if attempt == 3:
                    print(f"[warn] unexpected error at range {start}-{end}: {e}")

        for log in logs:
            args = log["args"]
            if chain == "ethereum":  # V2
                debt_token  = args.get("principal")
                repay_amt   = int(args.get("purchaseAmount"))
            else:  # V3
                debt_token  = args.get("debt")
                repay_amt   = int(args.get("debtToCover"))

            rows.append({
                "block": log["blockNumber"],
                "tx": log["transactionHash"].hex(),
                "collateral": args.get("collateral"),
                "debt_token": debt_token,
                "user": args.get("user"),
                "repay_amount": repay_amt,
                "collateral_seized": int(args.get("liquidatedCollateralAmount")),
                "liquidator": args.get("liquidator"),
                "receiveAToken": bool(args.get("receiveAToken")),
            })
        start = end + 1
        time.sleep(0.05)

    return rows


def main():
    ap = argparse.ArgumentParser(description="Fetch Aave LiquidationCall events (V2 on Ethereum, V3 on Arbitrum)")
    ap.add_argument("--chain", default="arbitrum", choices=list(CHAIN_AAVE.keys()),
                    help="chain to query (ethereum=v2, arbitrum=v3), default=arbitrum")
    ap.add_argument("--blocks", type=int, default=50000,
                    help="lookback block span, default=50000")
    ap.add_argument("--step", type=int, default=800,
                    help="block step per getLogs call (will auto-shrink on errors), default=800")
    args = ap.parse_args()

    chain = args.chain.lower()
    span = int(args.blocks)
    step = int(args.step)

    if chain not in CHAIN_AAVE:
        print(f"Unsupported chain: {chain}. Supported: {list(CHAIN_AAVE.keys())}")
        sys.exit(1)

    cfg = CHAIN_AAVE[chain]
    w3 = get_w3(chain)

    latest = int(w3.eth.block_number)
    from_block = max(0, latest - span)
    to_block = latest

    pool_addr = get_pool_address_via_provider(w3, cfg["provider"], cfg["provider_fn"])
    print(f"[rpc] {chain} using provider {cfg['provider']} -> Pool {pool_addr}")
    print(f"[{chain}] Aave {cfg['version']} LiquidationCall blocks {from_block}..{to_block} (step≈{step})")

    rows = fetch_liquidations(
        chain=chain,
        pool_addr=pool_addr,
        from_block=from_block,
        to_block=to_block,
        w3=w3,
        event_abi=cfg["pool_event_abi"],
        step=step,
    )

    if not rows:
        print("no liquidation events found in range")
        # Also write empty file to avoid subsequent analysis failures
        os.makedirs(CSV_DIR, exist_ok=True)
        empty_path = os.path.join(CSV_DIR, f"liquidations_{chain}_{span}.csv")
        with open(empty_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "timestamp","chain","version","block","tx",
                "collateral","debt_token","repay_amount","collateral_seized",
                "liquidator","user","receiveAToken"
            ])
            w.writeheader()
        print(f"Saved: {empty_path}, events=0")
        sys.exit(0)

    blks = [r["block"] for r in rows]
    ts_map = fetch_block_timestamps(chain, blks, max_workers=6)
    for r in rows:
        r["timestamp"] = ts_map.get(int(r["block"]), None)
        r["chain"] = chain
        r["version"] = cfg["version"]

    out_path = os.path.join(CSV_DIR, f"liquidations_{chain}_{span}.csv")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    cols = [
        "timestamp","chain","version","block","tx",
        "collateral","debt_token","repay_amount","collateral_seized",
        "liquidator","user","receiveAToken"
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in cols})

    print(f"Saved: {out_path}, events={len(rows)}")

if __name__ == "__main__":
    main()
