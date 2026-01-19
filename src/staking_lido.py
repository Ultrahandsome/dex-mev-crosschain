from __future__ import annotations
import os, sys, csv, math, time, datetime as dt, argparse
from typing import List, Tuple
import pandas as pd
from web3 import Web3
from .rpc import get_w3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_DIR = os.path.join(ROOT, "data", "csv")

# -----------------------------
# Config: only Ethereum mainnet Lido stETH (native)
# -----------------------------
LIDO_STETH = {
    "ethereum": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
}

# Minimal ABI: only two functions are required
ABI_STETH = [
    {
        "inputs":[{"internalType":"uint256","name":"_sharesAmount","type":"uint256"}],
        "name":"getPooledEthByShares",
        "outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
        "stateMutability":"view",
        "type":"function"
    },
    {
        "inputs":[{"internalType":"uint256","name":"_ethAmount","type":"uint256"}],
        "name":"getSharesByPooledEth",
        "outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
        "stateMutability":"view",
        "type":"function"
    },
]

WEI = 10**18

# -----------------------------
# Utility functions
# -----------------------------

def _utc_midnight_days_ago(days_ago:int) -> int:
    """Return the Unix timestamp (int) of UTC 00:00:00 for the given days ago. days_ago=0 means today 00:00 UTC."""
    now_utc = dt.datetime.utcnow()
    midnight = dt.datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=dt.timezone.utc)
    target = midnight - dt.timedelta(days=days_ago)
    return int(target.timestamp())

def _estimate_seconds_per_block(w3: Web3, lookback: int = 10000) -> float:
    """Estimate average seconds per block using a lookback window, to avoid heavy RPC from binary search."""
    latest = w3.eth.get_block("latest")
    b2 = int(latest.number)
    b1 = max(0, b2 - lookback)
    blk1 = w3.eth.get_block(b1)
    dt_secs = int(latest.timestamp) - int(blk1.timestamp)
    if dt_secs <= 0 or b2 == b1:
        return 12.0  # fallback
    return dt_secs / (b2 - b1)

def _block_at_or_before(w3: Web3, target_ts: int, spb: float) -> int:
    """
    Approx + refine: first estimate block using spb, then converge locally to find the maximum block
    with timestamp <= target_ts. Avoids full binary search with too many RPC calls.
    """
    latest = w3.eth.get_block("latest")
    b_hi = int(latest.number)
    t_hi = int(latest.timestamp)

    # If target time is later than latest block, just return latest
    if target_ts >= t_hi:
        return b_hi

    # Rough guess
    delta_sec = t_hi - target_ts
    guess = max(0, b_hi - int(delta_sec / max(spb, 1e-6)))

    # Clamp within [0, latest]
    b = min(max(guess, 0), b_hi)
    blk = w3.eth.get_block(b)
    t = int(blk.timestamp)

    # Adjust until we find block <= target_ts
    if t > target_ts:
        # Search backwards
        step = max(1, int(300 / max(spb, 1)))  # initial step ~5 minutes
        while True:
            if b - step < 0:
                b = 0
                break
            b -= step
            blk = w3.eth.get_block(b)
            t = int(blk.timestamp)
            if t <= target_ts:
                break
            step = min(step * 2, 20000)  # exponential backoff
        # Fine-tune forward until just before exceeding target_ts
        while True:
            nb = b + 1
            if nb > b_hi: break
            nt = int(w3.eth.get_block(nb).timestamp)
            if nt > target_ts: break
            b = nb
    else:
        # If already <= target_ts, move forward until just before it exceeds
        while True:
            nb = b + 1
            if nb > b_hi: break
            nt = int(w3.eth.get_block(nb).timestamp)
            if nt > target_ts: break
            b = nb

    return b

def _daily_blocks(w3: Web3, days: int, lookback_blocks:int=10000, step_sleep:float=0.05) -> List[Tuple[int,int]]:
    """
    Get the last N days (including today 00:00 UTC), returning [(timestamp, block)], sorted ascending.
    timestamp = each day’s 00:00 UTC, block = max block <= timestamp.
    """
    spb = _estimate_seconds_per_block(w3, lookback=lookback_blocks)
    out = []
    # Iterate from oldest to newest
    for d in range(days, -1, -1):
        ts = _utc_midnight_days_ago(d)
        # Retry several times (public RPC nodes may fail occasionally)
        last_err = None
        for attempt in range(4):
            try:
                b = _block_at_or_before(w3, ts, spb)
                out.append((ts, b))
                break
            except Exception as e:
                last_err = e
                time.sleep(0.2 * (attempt + 1))
        if len(out) == 0 or out[-1][0] != ts:
            # Still failed, append placeholder (NaN later)
            out.append((ts, None))
        time.sleep(step_sleep)
    return out

# -----------------------------
# Main logic
# -----------------------------

def run(chain: str, days: int, lookback_blocks:int=10000, step_sleep:float=0.05):
    chain = chain.lower()
    if chain not in LIDO_STETH:
        print(f"Unsupported chain for stETH: {chain}. Only 'ethereum' supported.")
        sys.exit(1)

    w3 = get_w3(chain)
    steth_addr = Web3.to_checksum_address(LIDO_STETH[chain])
    steth = w3.eth.contract(address=steth_addr, abi=ABI_STETH)

    # Get “aligned blocks” at daily 00:00 UTC
    day_points = _daily_blocks(w3, days, lookback_blocks=lookback_blocks, step_sleep=step_sleep)  # List[(ts, block)]
    rows = []
    one_share = WEI  # 1e18 shares

    for ts, blk in day_points:
        share_to_eth = None
        if blk is not None:
            for attempt in range(3):
                try:
                    pooled_eth = steth.functions.getPooledEthByShares(one_share).call(block_identifier=int(blk))
                    share_to_eth = pooled_eth / WEI
                    break
                except Exception:
                    time.sleep(0.2 * (attempt + 1))
        rows.append({
            "date": dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"),
            "timestamp": ts,
            "block": blk if blk is not None else "",
            "share_to_eth": share_to_eth,
        })
        time.sleep(0.02)

    df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    if df["share_to_eth"].notna().sum() >= 2:
        # Daily return: today/yesterday - 1
        df["day_return"] = df["share_to_eth"].pct_change()
        # Approximate APY: (1 + day_return)^365 - 1
        df["apy_est"] = (1.0 + df["day_return"]).pow(365) - 1.0
    else:
        df["day_return"] = None
        df["apy_est"] = None

    os.makedirs(CSV_DIR, exist_ok=True)
    out_path = os.path.join(CSV_DIR, f"staking_returns_{chain}_{days}d.csv")
    df.to_csv(out_path, index=False)
    print(f"Saved: {out_path}, rows={len(df)}")

def main():
    ap = argparse.ArgumentParser(description="Fetch Lido stETH daily share->ETH rates and compute returns (Ethereum)")
    ap.add_argument("--chain", default="ethereum", choices=["ethereum"], help="only ethereum supported, default=ethereum")
    ap.add_argument("--days", type=int, default=30, help="how many past days (including today) to fetch, default=30")
    ap.add_argument("--lookback", type=int, default=10000, help="blocks lookback for seconds-per-block estimate, default=10000")
    ap.add_argument("--step_sleep", type=float, default=0.05, help="sleep between per-day block lookups, default=0.05s")
    args = ap.parse_args()

    run(chain=args.chain, days=int(args.days), lookback_blocks=int(args.lookback), step_sleep=float(args.step_sleep))

if __name__ == "__main__":
    main()