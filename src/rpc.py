# src/rpc.py
from __future__ import annotations
import os, time, json
from typing import Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from web3 import Web3
from web3.providers.rpc import HTTPProvider
import yaml
from dotenv import load_dotenv  # NEW

# Load .env (ensure ETHEREUM_RPC_URL / ARBITRUM_RPC_URL take effect)
load_dotenv()

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

CHAINS = load_yaml(os.path.join(ROOT, "configs", "chains.yaml"))

def _endpoints_for(chain: str) -> List[str]:
    env_map = {
        "ethereum": "ETHEREUM_RPC_URL",
        "arbitrum": "ARBITRUM_RPC_URL",
    }
    eps = []
    env_key = env_map.get(chain.lower())
    if env_key and os.getenv(env_key):
        eps.append(os.getenv(env_key).strip())
    eps.extend(CHAINS[chain]["rpc_fallbacks"])
    # Deduplicate while preserving order
    seen = set(); uniq = []
    for e in eps:
        if e and e not in seen:
            uniq.append(e); seen.add(e)
    return uniq

def _mk_w3(endpoint: str) -> Web3:
    provider = HTTPProvider(endpoint, request_kwargs={"timeout": 20})
    return Web3(provider)

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type(Exception),
)
def _ping(w3: Web3, expected_chain_id: int) -> dict:
    cid = w3.eth.chain_id
    if cid != expected_chain_id:
        raise RuntimeError(f"ChainId mismatch: got {cid}, expect {expected_chain_id}")
    blk = w3.eth.get_block("latest")
    return {"chain_id": cid, "block": blk}

def get_w3(chain: str) -> Web3:
    chain = chain.lower()
    if chain not in CHAINS:
        raise KeyError(f"Unknown chain: {chain}")
    expected = CHAINS[chain]["chain_id"]
    last_err = None
    for ep in _endpoints_for(chain):
        try:
            w3 = _mk_w3(ep)
            _ = _ping(w3, expected)
            # Print current endpoint (useful for first run or debugging)
            print(f"[rpc] {chain} using {ep}")
            return w3
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All RPC endpoints failed for {chain}: {last_err}")