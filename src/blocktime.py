from __future__ import annotations
import os, csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Iterable
from web3 import Web3
from .rpc import get_w3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def _cache_path(chain:str):
    return os.path.join(ROOT, "data", "csv", f"block_ts_cache_{chain}.csv")

def load_cache(chain:str) -> Dict[int,int]:
    path = _cache_path(chain)
    m: Dict[int,int] = {}
    if os.path.exists(path):
        with open(path, "r", newline="", encoding="utf-8") as f:
            r = csv.reader(f)
            next(r, None)
            for b, ts in r:
                m[int(b)] = int(ts)
    return m

def save_cache(chain:str, m:Dict[int,int]):
    path = _cache_path(chain)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["block","timestamp"])
        for b, ts in sorted(m.items()):
            w.writerow([b, ts])

def fetch_block_timestamps(chain:str, blocks:Iterable[int], max_workers:int=6) -> Dict[int,int]:
    """
    Fetch block timestamps in parallel with local CSV cache.
    First run will make parallel RPC calls; subsequent runs for same blocks read from cache with near-zero latency.
    """
    w3 = get_w3(chain)
    cache = load_cache(chain)
    todo = [int(b) for b in set(blocks) if int(b) not in cache]
    if not todo:
        return cache

    def _one(b:int):
        return b, w3.eth.get_block(b).timestamp

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_one, b) for b in todo]
        for fut in as_completed(futs):
            b, ts = fut.result()
            cache[int(b)] = int(ts)

    save_cache(chain, cache)
    return cache
