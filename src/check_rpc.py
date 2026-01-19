from __future__ import annotations
import sys, time, datetime as dt
from web3 import Web3
from .rpc import get_w3

def human_ts(ts:int)->str:
    return dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S UTC")

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.check_rpc <ethereum|arbitrum>")
        sys.exit(1)
    chain = sys.argv[1].lower()
    w3 = get_w3(chain)
    latest = w3.eth.get_block("latest")
    gas = w3.eth.gas_price
    print(f"[OK] {chain} connected")
    print(f"  chain_id: {w3.eth.chain_id}")
    print(f"  latest block: {latest.number} @ {human_ts(latest['timestamp'])}")
    try:
        base_fee = latest.get("baseFeePerGas", None)
        if base_fee is not None:
            print(f"  baseFeePerGas: {Web3.from_wei(base_fee, 'gwei')} gwei")
    except Exception:
        pass
    print(f"  gas_price: {Web3.from_wei(gas, 'gwei')} gwei")

if __name__ == "__main__":
    main()
