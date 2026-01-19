from __future__ import annotations
import os, csv, sys
import pandas as pd
from web3 import Web3
from .rpc import get_w3
from .univ3 import load_yaml, load_abi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ABI_POOL = load_abi("UniswapV3Pool.json")

def price_from_sqrtPriceX96(sqrtPriceX96: int, dec0: int, dec1: int) -> float:
    # price = (sqrtPriceX96^2 / 2^192) * 10^(dec0 - dec1)
    ratio = (sqrtPriceX96 ** 2) / (2 ** 192)
    return ratio * (10 ** (dec0 - dec1))

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m src.spot_price <chain>")
        sys.exit(1)
    
    chain = sys.argv[1].lower()
    pools_csv = os.path.join(ROOT, "data", "csv", f"pools_found_{chain}.csv")
    
    if not os.path.exists(pools_csv):
        print(f"Error: {pools_csv} not found. Run get_pool first.")
        sys.exit(1)
        
    df = pd.read_csv(pools_csv)
    # Process only current chain data
    df = df[df["chain"].str.lower() == chain]

    out_path = os.path.join(ROOT, "data", "csv", f"spot_price_{chain}.csv")
    rows = []

    w3 = get_w3(chain)
    
    for _, row in df.iterrows():
        pool_addr = row["pool"]
        if pool_addr.lower() == "0x0000000000000000000000000000000000000000":
            continue  # skip non-existing pool

        pool = w3.eth.contract(address=Web3.to_checksum_address(pool_addr), abi=ABI_POOL)
        slot0 = pool.functions.slot0().call()
        sqrtPriceX96 = slot0[0]

        price = price_from_sqrtPriceX96(
            sqrtPriceX96,
            int(row["base_decimals"]),
            int(row["quote_decimals"])
        )

        rows.append([
            chain, row["base"], row["quote"], row["fee"],
            pool_addr, sqrtPriceX96, price
        ])
        print(f"[{chain}] {row['base']}/{row['quote']} fee={row['fee']} -> {price:.6f}")

    # Write to CSV
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["chain","base","quote","fee","pool","sqrtPriceX96","price_base_per_quote"])
        writer.writerows(rows)

    print(f"\nSaved: {out_path}")

if __name__ == "__main__":
    main()
