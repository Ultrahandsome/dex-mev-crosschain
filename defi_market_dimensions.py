"""
DeFi Market Activity Dimensions

This module defines the core dimensions for capturing DeFi market activity,
including trading, liquidity, MEV, and cross-chain metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional


class ChainType(Enum):
    """Supported blockchain networks"""
    ETHEREUM = "ethereum"
    BINANCE_SMART_CHAIN = "bsc"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    AVALANCHE = "avalanche"
    FANTOM = "fantom"
    BASE = "base"


class TransactionType(Enum):
    """Types of DeFi transactions"""
    SWAP = "swap"
    ADD_LIQUIDITY = "add_liquidity"
    REMOVE_LIQUIDITY = "remove_liquidity"
    BRIDGE = "bridge"
    MEV_ARBITRAGE = "mev_arbitrage"
    MEV_SANDWICH = "mev_sandwich"
    MEV_LIQUIDATION = "mev_liquidation"


@dataclass
class TimeDimension:
    """Temporal dimensions for market activity"""
    timestamp: datetime
    block_number: int
    block_hash: str
    transaction_index: int
    
    @property
    def epoch_ms(self) -> int:
        """Get timestamp as milliseconds since epoch"""
        return int(self.timestamp.timestamp() * 1000)


@dataclass
class PriceDimension:
    """Price-related dimensions"""
    token_address: str
    token_symbol: str
    spot_price_usd: Decimal
    price_impact_percent: Decimal
    slippage_percent: Decimal
    volatility_24h: Optional[Decimal] = None
    
    def __post_init__(self):
        """Validate price values"""
        if self.spot_price_usd < 0:
            raise ValueError("Price cannot be negative")


@dataclass
class VolumeDimension:
    """Volume and liquidity dimensions"""
    trading_volume_usd: Decimal
    trading_volume_24h_usd: Decimal
    total_value_locked_usd: Decimal
    liquidity_depth_usd: Decimal
    number_of_trades: int
    unique_traders: int
    
    @property
    def average_trade_size_usd(self) -> Decimal:
        """Calculate average trade size"""
        if self.number_of_trades == 0:
            return Decimal("0")
        return self.trading_volume_usd / self.number_of_trades


@dataclass
class LiquidityPoolDimension:
    """Liquidity pool specific dimensions"""
    pool_address: str
    dex_protocol: str  # e.g., "uniswap_v3", "curve", "balancer"
    token0_address: str
    token0_symbol: str
    token0_reserve: Decimal
    token1_address: str
    token1_symbol: str
    token1_reserve: Decimal
    pool_fee_percent: Decimal
    pool_tvl_usd: Decimal
    
    @property
    def pool_pair(self) -> str:
        """Get formatted pool pair"""
        return f"{self.token0_symbol}/{self.token1_symbol}"


@dataclass
class TransactionDimension:
    """Transaction-level dimensions"""
    transaction_hash: str
    transaction_type: TransactionType
    from_address: str
    to_address: str
    gas_used: int
    gas_price_gwei: Decimal
    transaction_fee_usd: Decimal
    success: bool
    
    @property
    def gas_cost_eth(self) -> Decimal:
        """Calculate gas cost in ETH"""
        return (self.gas_price_gwei * self.gas_used) / Decimal("1e9")


@dataclass
class MEVDimension:
    """MEV (Maximum Extractable Value) dimensions"""
    mev_type: TransactionType
    mev_profit_usd: Decimal
    bundle_hash: Optional[str] = None
    front_run_tx: Optional[str] = None
    victim_tx: Optional[str] = None
    back_run_tx: Optional[str] = None
    searcher_address: Optional[str] = None
    
    @property
    def is_sandwich_attack(self) -> bool:
        """Check if this is a sandwich attack"""
        return self.mev_type == TransactionType.MEV_SANDWICH


@dataclass
class CrossChainDimension:
    """Cross-chain bridge and activity dimensions"""
    source_chain: ChainType
    destination_chain: ChainType
    bridge_protocol: str  # e.g., "layerzero", "wormhole", "stargate"
    bridged_amount_usd: Decimal
    bridge_fee_usd: Decimal
    source_tx_hash: str
    destination_tx_hash: Optional[str] = None
    bridge_status: str = "pending"  # pending, completed, failed
    
    @property
    def is_completed(self) -> bool:
        """Check if bridge transaction is completed"""
        return self.bridge_status == "completed"
    
    @property
    def chain_route(self) -> str:
        """Get formatted chain route"""
        return f"{self.source_chain.value} -> {self.destination_chain.value}"


@dataclass
class MarketMetricsDimension:
    """Aggregated market metrics dimensions"""
    metric_name: str
    metric_value: Decimal
    aggregation_period: str  # e.g., "1h", "24h", "7d"
    calculation_time: datetime
    
    # Common market metrics
    market_cap_usd: Optional[Decimal] = None
    circulating_supply: Optional[Decimal] = None
    diluted_market_cap_usd: Optional[Decimal] = None


@dataclass
class DeFiMarketActivity:
    """
    Comprehensive data structure capturing all core dimensions of DeFi market activity.
    
    This combines all dimension classes to provide a complete view of a DeFi market event.
    """
    # Core dimensions
    time: TimeDimension
    transaction: TransactionDimension
    
    # Market dimensions
    prices: List[PriceDimension] = field(default_factory=list)
    volume: Optional[VolumeDimension] = None
    liquidity_pool: Optional[LiquidityPoolDimension] = None
    
    # Advanced dimensions
    mev: Optional[MEVDimension] = None
    cross_chain: Optional[CrossChainDimension] = None
    market_metrics: List[MarketMetricsDimension] = field(default_factory=list)
    
    # Metadata
    chain: ChainType = ChainType.ETHEREUM
    data_source: str = ""
    raw_data: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            "timestamp": self.time.timestamp.isoformat(),
            "block_number": self.time.block_number,
            "transaction_hash": self.transaction.transaction_hash,
            "transaction_type": self.transaction.transaction_type.value,
            "chain": self.chain.value,
            "gas_used": self.transaction.gas_used,
            "gas_price_gwei": str(self.transaction.gas_price_gwei),
            "prices": [
                {
                    "token": p.token_symbol,
                    "price_usd": str(p.spot_price_usd),
                    "slippage": str(p.slippage_percent)
                }
                for p in self.prices
            ],
            "volume": {
                "trading_volume_usd": str(self.volume.trading_volume_usd),
                "tvl_usd": str(self.volume.total_value_locked_usd),
                "num_trades": self.volume.number_of_trades
            } if self.volume else None,
            "liquidity_pool": {
                "pool_address": self.liquidity_pool.pool_address,
                "pair": self.liquidity_pool.pool_pair,
                "protocol": self.liquidity_pool.dex_protocol,
                "tvl_usd": str(self.liquidity_pool.pool_tvl_usd)
            } if self.liquidity_pool else None,
            "mev": {
                "type": self.mev.mev_type.value,
                "profit_usd": str(self.mev.mev_profit_usd),
                "is_sandwich": self.mev.is_sandwich_attack
            } if self.mev else None,
            "cross_chain": {
                "route": self.cross_chain.chain_route,
                "protocol": self.cross_chain.bridge_protocol,
                "amount_usd": str(self.cross_chain.bridged_amount_usd),
                "status": self.cross_chain.bridge_status
            } if self.cross_chain else None
        }
    
    @property
    def total_value_usd(self) -> Decimal:
        """Calculate total USD value of the activity"""
        total = Decimal("0")
        
        if self.volume:
            total += self.volume.trading_volume_usd
        
        if self.mev:
            total += self.mev.mev_profit_usd
        
        if self.cross_chain:
            total += self.cross_chain.bridged_amount_usd
        
        return total
    
    @property
    def is_mev_activity(self) -> bool:
        """Check if this activity involves MEV"""
        return self.mev is not None


# Dimension aggregation utilities

def aggregate_volume_metrics(activities: List[DeFiMarketActivity]) -> Dict:
    """Aggregate volume metrics from multiple activities"""
    total_volume = Decimal("0")
    total_trades = 0
    unique_traders = set()
    
    for activity in activities:
        if activity.volume:
            total_volume += activity.volume.trading_volume_usd
            total_trades += activity.volume.number_of_trades
        unique_traders.add(activity.transaction.from_address)
    
    return {
        "total_volume_usd": total_volume,
        "total_trades": total_trades,
        "unique_traders": len(unique_traders),
        "average_trade_size_usd": total_volume / total_trades if total_trades > 0 else Decimal("0")
    }


def aggregate_gas_metrics(activities: List[DeFiMarketActivity]) -> Dict:
    """Aggregate gas usage metrics from multiple activities"""
    total_gas = 0
    total_gas_cost_usd = Decimal("0")
    
    for activity in activities:
        total_gas += activity.transaction.gas_used
        total_gas_cost_usd += activity.transaction.transaction_fee_usd
    
    avg_gas = total_gas / len(activities) if activities else 0
    avg_gas_cost = total_gas_cost_usd / len(activities) if activities else Decimal("0")
    
    return {
        "total_gas_used": total_gas,
        "average_gas_per_tx": avg_gas,
        "total_gas_cost_usd": total_gas_cost_usd,
        "average_gas_cost_usd": avg_gas_cost
    }


def aggregate_mev_metrics(activities: List[DeFiMarketActivity]) -> Dict:
    """Aggregate MEV metrics from multiple activities"""
    mev_activities = [a for a in activities if a.is_mev_activity]
    
    total_mev_profit = Decimal("0")
    mev_types = {}
    
    for activity in mev_activities:
        if activity.mev:
            total_mev_profit += activity.mev.mev_profit_usd
            mev_type = activity.mev.mev_type.value
            mev_types[mev_type] = mev_types.get(mev_type, 0) + 1
    
    return {
        "total_mev_profit_usd": total_mev_profit,
        "mev_transaction_count": len(mev_activities),
        "mev_percentage": (len(mev_activities) / len(activities) * 100) if activities else 0,
        "mev_types_distribution": mev_types
    }


def aggregate_cross_chain_metrics(activities: List[DeFiMarketActivity]) -> Dict:
    """Aggregate cross-chain metrics from multiple activities"""
    cross_chain_activities = [a for a in activities if a.cross_chain is not None]
    
    total_bridged_volume = Decimal("0")
    chain_pairs = {}
    protocols = {}
    
    for activity in cross_chain_activities:
        if activity.cross_chain:
            total_bridged_volume += activity.cross_chain.bridged_amount_usd
            
            route = activity.cross_chain.chain_route
            chain_pairs[route] = chain_pairs.get(route, 0) + 1
            
            protocol = activity.cross_chain.bridge_protocol
            protocols[protocol] = protocols.get(protocol, Decimal("0")) + activity.cross_chain.bridged_amount_usd
    
    return {
        "total_bridged_volume_usd": total_bridged_volume,
        "bridge_transaction_count": len(cross_chain_activities),
        "popular_routes": chain_pairs,
        "protocol_volumes": {k: str(v) for k, v in protocols.items()}
    }
