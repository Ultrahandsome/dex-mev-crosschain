from __future__ import annotations
import os, sys, math, argparse
from typing import List, Dict, Tuple
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_DIR = os.path.join(ROOT, "data", "csv")

# ---------- Utils ----------
def _read_swaps(chain: str, span: int) -> pd.DataFrame:
    path = os.path.join(CSV_DIR, f"swaps_{chain}_{span}.csv")
    if not os.path.exists(path):
        print(f"[ERR] swaps CSV not found: {path}\nPlease run: python3 -m src.swaps --chain {chain} --blocks {span}")
        sys.exit(1)
    df = pd.read_csv(path)

    # Minimum required columns: only these
    required = ["block","tx","log_index","amount0","amount1"]
    # Compatible with case/variants
    rename_map = {}
    if "logIndex" in df.columns and "log_index" not in df.columns:
        rename_map["logIndex"] = "log_index"
    if "tx_hash" in df.columns and "tx" not in df.columns:
        rename_map["tx_hash"] = "tx"
    if rename_map:
        df = df.rename(columns=rename_map)

    for c in required:
        if c not in df.columns:
            print(f"[ERR] required column missing in {path}: {c}")
            sys.exit(1)

    # Type conversion and numerics
    df["block"] = pd.to_numeric(df["block"], errors="coerce").astype("Int64")
    df["log_index"] = pd.to_numeric(df["log_index"], errors="coerce").astype("Int64")
    df["amount0"] = pd.to_numeric(df["amount0"], errors="coerce")
    df["amount1"] = pd.to_numeric(df["amount1"], errors="coerce")

    # Optional time columns: timestamp / datetime / time
    ts_col = None
    for cand in ["timestamp","datetime","time"]:
        if cand in df.columns:
            ts_col = cand
            break
    if ts_col is not None:
        try:
            df[ts_col] = pd.to_datetime(df[ts_col], utc=True, errors="coerce")
        except Exception:
            df[ts_col] = pd.NaT
    df["_ts_col"] = ts_col

    # Optional columns: price_after / sender / recipient / pool / address / contract_address / emitter / pair / token0 / token1
    if "price_after" in df.columns:
        df["price_after"] = pd.to_numeric(df["price_after"], errors="coerce")
    if "sender" not in df.columns: df["sender"] = ""
    if "recipient" not in df.columns: df["recipient"] = ""

    # Unify pool_key (multi-level fallback)
    pool_key = None
    for cand in ["pool","address","contract_address","emitter","pair"]:
        if cand in df.columns and df[cand].notna().any():
            pool_key = cand
            break
    if pool_key is None and ("token0" in df.columns and "token1" in df.columns):
        df["pool_key"] = (df["token0"].astype(str) + "_" + df["token1"].astype(str))
    elif pool_key is not None:
        df["pool_key"] = df[pool_key].astype(str)
    else:
        df["pool_key"] = "all"  # If nothing else available, use single bucket (can still do sandwich)

    # Drop rows with empty key columns
    df = df.dropna(subset=["block","log_index","pool_key"]).reset_index(drop=True)
    return df

def _exec_price(row) -> float:
    # Priority use price_after (if exists and > 0)
    if "price_after" in row and pd.notna(row["price_after"]) and row["price_after"] > 0:
        return float(row["price_after"])
    # Otherwise infer from volume: token1 per token0
    a0 = row.get("amount0", None)
    a1 = row.get("amount1", None)
    if a0 is None or a1 is None or pd.isna(a0) or pd.isna(a1) or a0 == 0 or a1 == 0:
        return float("nan")
    try:
        return abs(float(a1)) / abs(float(a0))
    except Exception:
        return float("nan")

def _bps(a: float, b: float) -> float:
    if a is None or b is None or a <= 0 or b <= 0 or math.isnan(a) or math.isnan(b):
        return float("nan")
    return (a / b - 1.0) * 10000.0

def _dir_from_amounts(a0: float, a1: float) -> int:
    try:
        if a0 < 0 and a1 > 0: return +1   # buy token1
        if a0 > 0 and a1 < 0: return -1   # sell token1
    except Exception:
        pass
    return 0

# ---------- Cross-pool arbitrage signals ----------
def detect_cross_pool_arb(df: pd.DataFrame, min_bp: float = 5.0) -> pd.DataFrame:
    dfx = df.copy()
    dfx["price_exec"] = dfx.apply(_exec_price, axis=1)
    dfx = dfx[(dfx["price_exec"] > 0) & dfx["price_exec"].notna()]

    # block-level granularity
    agg_blk = dfx.groupby(["block","pool_key"])["price_exec"].median().reset_index().rename(columns={"price_exec":"px"})
    recs = []
    for blk, g in agg_blk.groupby("block"):
        if len(g) < 2: 
            continue  # only one pool_key in same block, cannot do cross-pool comparison
        for i in range(len(g)):
            for j in range(i+1, len(g)):
                p1 = float(g.iloc[i]["px"]); p2 = float(g.iloc[j]["px"])
                k1 = g.iloc[i]["pool_key"];  k2 = g.iloc[j]["pool_key"]
                spread_bp = abs(_bps(p1, p2))
                if pd.notna(spread_bp) and spread_bp >= min_bp:
                    recs.append({
                        "type": "cross_pool",
                        "level": "block",
                        "block": int(blk),
                        "pool_a": k1, "pool_b": k2,
                        "px_a": p1, "px_b": p2,
                        "spread_bps": spread_bp
                    })

    # minute-level granularity (if time column available)
    ts_col = dfx["_ts_col"].iloc[0] if "_ts_col" in dfx.columns and len(dfx) else None
    if ts_col:
        dfx["minute"] = dfx[ts_col].dt.floor("min")
        agg_min = dfx.dropna(subset=["minute"]).groupby(["minute","pool_key"])["price_exec"].median().reset_index().rename(columns={"price_exec":"px"})
        for minute, g in agg_min.groupby("minute"):
            if len(g) < 2: 
                continue
            for i in range(len(g)):
                for j in range(i+1, len(g)):
                    p1 = float(g.iloc[i]["px"]); p2 = float(g.iloc[j]["px"])
                    k1 = g.iloc[i]["pool_key"];  k2 = g.iloc[j]["pool_key"]
                    spread_bp = abs(_bps(p1, p2))
                    if pd.notna(spread_bp) and spread_bp >= min_bp:
                        recs.append({
                            "type": "cross_pool",
                            "level": "minute",
                            "minute": minute,
                            "pool_a": k1, "pool_b": k2,
                            "px_a": p1, "px_b": p2,
                            "spread_bps": spread_bp
                        })
    return pd.DataFrame(recs)

# ---------- Sandwich / backrun heuristics ----------
def detect_sandwich(df: pd.DataFrame, min_bp: float = 5.0) -> pd.DataFrame:
    dfx = df.copy()
    dfx["price_exec"] = dfx.apply(_exec_price, axis=1)
    dfx = dfx[(dfx["price_exec"] > 0) & dfx["price_exec"].notna()].copy()

    if "sender" not in dfx.columns: dfx["sender"] = ""
    if "recipient" not in dfx.columns: dfx["recipient"] = ""

    cols_keep = ["block","pool_key","tx","log_index","sender","recipient","amount0","amount1","price_exec"]
    dfx = dfx[cols_keep].dropna(subset=["block","log_index","pool_key"]).copy()
    dfx["block"] = dfx["block"].astype(int)
    dfx["log_index"] = dfx["log_index"].astype(int)
    dfx.sort_values(["pool_key","block","log_index"], inplace=True)

    suspects = []
    for (pkey, blk), g in dfx.groupby(["pool_key","block"]):
        arr = g.to_dict(orient="records")
        n = len(arr)
        if n < 3: 
            continue
        for i in range(n - 2):
            a = arr[i]; v = arr[i+1]; b = arr[i+2]
            addrA1 = (a["sender"] or a["recipient"] or "").lower()
            addrA2 = (b["sender"] or b["recipient"] or "").lower()
            addrV  = (v["sender"] or v["recipient"] or "").lower()
            if not addrA1 or not addrA2 or not addrV: 
                continue
            if addrA1 != addrA2: 
                continue
            if addrA1 == addrV: 
                continue

            dirA1 = _dir_from_amounts(a["amount0"], a["amount1"])
            dirA2 = _dir_from_amounts(b["amount0"], b["amount1"])
            if dirA1 == 0 or dirA2 == 0 or (dirA1 + dirA2 != 0):
                continue

            ref_px = (a["price_exec"] + b["price_exec"]) / 2.0
            move_bp = abs(_bps(v["price_exec"], ref_px))
            if math.isnan(move_bp) or move_bp < min_bp:
                continue

            try:
                v_q0 = abs(float(v["amount0"]))
                if (v_q0 == 0 or math.isnan(v_q0)) and v["price_exec"] > 0:
                    v_q0 = abs(float(v["amount1"])) / float(v["price_exec"])
            except Exception:
                v_q0 = 0.0
            est_profit_token1 = (b["price_exec"] - a["price_exec"]) * (v_q0 if v_q0 == v_q0 else 0.0)

            suspects.append({
                "type": "sandwich",
                "pool_key": pkey,
                "block": int(blk),
                "front_tx": a["tx"],
                "victim_tx": v["tx"],
                "back_tx": b["tx"],
                "actor": addrA1,
                "front_price": a["price_exec"],
                "victim_price": v["price_exec"],
                "back_price": b["price_exec"],
                "price_move_bps": move_bp,
                "est_profit_token1": est_profit_token1
            })
    return pd.DataFrame(suspects)

def summarize_mev(sandwich_df: pd.DataFrame, topN: int = 10) -> Tuple[pd.DataFrame, list]:
    if sandwich_df.empty:
        return pd.DataFrame(columns=["actor","events","sum_move_bp","unique_blocks","unique_pool_keys","est_profit_token1"]), []
    actors = sandwich_df.groupby("actor").agg(
        events=("actor","count"),
        sum_move_bp=("price_move_bps","sum"),
        unique_blocks=("block","nunique"),
        unique_pool_keys=("pool_key","nunique"),
        est_profit_token1=("est_profit_token1","sum")
    ).reset_index().sort_values("events", ascending=False)
    top = list(actors[["actor","events"]].head(topN).itertuples(index=False, name=None))
    return actors, top

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description="Detect cross-pool arbitrage and sandwich MEV from swaps CSV")
    ap.add_argument("--chain", default="ethereum", choices=["ethereum","arbitrum","base"],
                    help="chain name, default=ethereum")
    ap.add_argument("--span", type=int, default=2000,
                    help="lookback blocks span that matches swaps filename, default=2000")
    ap.add_argument("--min_bp", type=float, default=10.0,
                    help="minimum spread / price move in bps to flag, default=10")
    ap.add_argument("--top", type=int, default=10,
                    help="top N actors in summary, default=10")
    args = ap.parse_args()

    chain = args.chain.lower()
    span  = int(args.span)
    min_bp = float(args.min_bp)
    topN = int(args.top)

    df = _read_swaps(chain, span)

    cross = detect_cross_pool_arb(df, min_bp=min_bp)
    sand  = detect_sandwich(df, min_bp=min_bp)

    os.makedirs(CSV_DIR, exist_ok=True)
    out_sus = os.path.join(CSV_DIR, f"mev_suspects_{chain}_{span}_min{int(min_bp)}.csv")
    out_sum = os.path.join(CSV_DIR, f"mev_summary_{chain}_{span}_min{int(min_bp)}.csv")

    parts = []
    if not cross.empty: parts.append(cross)
    if not sand.empty:  parts.append(sand)
    sus_all = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    sus_all.to_csv(out_sus, index=False)

    actors, top_actors = summarize_mev(sand, topN=topN)
    actors.to_csv(out_sum, index=False)

    print(f"Saved suspects -> {out_sus} (rows={len(sus_all)})")
    print(f"Saved summary  -> {out_sum} (rows={len(actors)})")
    if top_actors:
        print("\nTop actors by sandwich events:")
        for addr, cnt in top_actors:
            print(f"  {addr} : {cnt}")

if __name__ == "__main__":
    main()
