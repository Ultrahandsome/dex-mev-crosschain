from __future__ import annotations
import os, csv, sys
from typing import List
from .rpc import get_w3
from .univ3 import get_addresses, token_addr_by_symbol, get_pool_address, get_token_meta, load_yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m src.get_pool <ethereum|arbitrum> [<ethereum|arbitrum> ...]")
        sys.exit(1)

    pairs_conf = load_yaml(os.path.join(ROOT, "configs", "pairs.yaml"))
    pairs = pairs_conf["pairs"]

    for chain in sys.argv[1:]:
        w3 = get_w3(chain)
        addrs = get_addresses(chain)
        factory = addrs["univ3_factory"]

        header = [
            "chain","base","quote","fee",
            "base_addr","quote_addr",
            "base_symbol","base_decimals","quote_symbol","quote_decimals",
            "factory","pool"
        ]
        rows = []

        for p in pairs:
            base = p["base"].upper()
            quote = p["quote"].upper()
            fees: List[int] = p["fees"]

            base_addr = token_addr_by_symbol(addrs, base)
            quote_addr = token_addr_by_symbol(addrs, quote)

            base_sym, base_dec = get_token_meta(w3, base_addr)
            quote_sym, quote_dec = get_token_meta(w3, quote_addr)

            for fee in fees:
                pool = get_pool_address(w3, factory, base_addr, quote_addr, int(fee))
                rows.append([
                    chain, base, quote, fee,
                    base_addr, quote_addr,
                    base_sym, base_dec, quote_sym, quote_dec,
                    factory, pool
                ])
                print(f"[{chain}] {base}:{quote} fee={fee} -> pool {pool}")

        out_path = os.path.join(ROOT, "data", "csv", f"pools_found_{chain}.csv")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

        print(f"\nSaved: {out_path}")

if __name__ == "__main__":
    main()