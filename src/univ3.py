from __future__ import annotations
import os, json, yaml
from typing import Dict, Tuple
from web3 import Web3
from .rpc import get_w3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# Load configuration
ADDRESSES = load_yaml(os.path.join(ROOT, "configs", "addresses.yaml"))
PAIRS_CONF = load_yaml(os.path.join(ROOT, "configs", "pairs.yaml"))

def load_abi(name: str):
    with open(os.path.join(ROOT, "abis", name), "r", encoding="utf-8") as f:
        return json.load(f)

ABI_FACTORY = load_abi("UniswapV3Factory.json")
ABI_ERC20   = load_abi("ERC20.json")

def get_addresses(chain: str) -> Dict[str,str]:
    chain = chain.lower()
    if chain not in ADDRESSES:
        raise KeyError(f"unknown chain in addresses.yaml: {chain}")
    return ADDRESSES[chain]

def token_addr_by_symbol(chain_addrs: Dict[str,str], sym: str) -> str:
    s = sym.lower()
    if s == "weth": return chain_addrs["weth"]
    if s == "usdc": return chain_addrs["usdc"]
    raise KeyError(f"unsupported token symbol: {sym}")

def ordered_tokens(addrA: str, addrB: str) -> Tuple[str,str]:
    # Uniswap v3 convention: token0 < token1 (by address)
    return (addrA, addrB) if addrA.lower() < addrB.lower() else (addrB, addrA)

def get_pool_address(w3: Web3, factory_addr: str, tokenA: str, tokenB: str, fee: int) -> str:
    factory = w3.eth.contract(address=Web3.to_checksum_address(factory_addr), abi=ABI_FACTORY)
    t0, t1 = ordered_tokens(tokenA, tokenB)
    pool = factory.functions.getPool(t0, t1, fee).call()
    return pool  # May be 0x000... indicating non-existent

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
