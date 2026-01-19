# DeFi Market Activity Dimensions - Quick Reference

## 8 Core Dimensions

```
┌─────────────────────────────────────────────────────────────────┐
│                   DeFiMarketActivity                            │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │     TIME     │  │    PRICE     │  │   VOLUME     │         │
│  │              │  │              │  │              │         │
│  │ • Timestamp  │  │ • Spot Price │  │ • Trading $  │         │
│  │ • Block #    │  │ • Slippage   │  │ • TVL        │         │
│  │ • TX Index   │  │ • Impact     │  │ • Liquidity  │         │
│  │ • Epoch MS   │  │ • Volatility │  │ • # Trades   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ LIQUIDITY    │  │ TRANSACTION  │  │     MEV      │         │
│  │    POOL      │  │              │  │              │         │
│  │              │  │ • TX Hash    │  │ • Profit $   │         │
│  │ • Pool Addr  │  │ • Gas Used   │  │ • MEV Type   │         │
│  │ • Reserves   │  │ • Gas Price  │  │ • Sandwich   │         │
│  │ • Token Pair │  │ • Fees $     │  │ • Arbitrage  │         │
│  │ • DEX Proto  │  │ • Success    │  │ • Searcher   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐                           │
│  │ CROSS-CHAIN  │  │   MARKET     │                           │
│  │              │  │   METRICS    │                           │
│  │ • Chains     │  │              │                           │
│  │ • Bridge     │  │ • Aggregated │                           │
│  │ • Amount $   │  │ • Period     │                           │
│  │ • Status     │  │ • Market Cap │                           │
│  │ • Fees       │  │ • Supply     │                           │
│  └──────────────┘  └──────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

## Supported Blockchains (8)

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Ethereum │  │   BSC    │  │ Polygon  │  │ Arbitrum │
└──────────┘  └──────────┘  └──────────┘  └──────────┘

┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Optimism │  │ Avalanche│  │  Fantom  │  │   Base   │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
```

## Transaction Types (7)

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│      Swap        │  │  Add Liquidity   │  │ Remove Liquidity │
└──────────────────┘  └──────────────────┘  └──────────────────┘

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│     Bridge       │  │  MEV Arbitrage   │  │  MEV Sandwich    │
└──────────────────┘  └──────────────────┘  └──────────────────┘

┌──────────────────┐
│ MEV Liquidation  │
└──────────────────┘
```

## Aggregation Functions

```
┌─────────────────────────────────────────────────┐
│  aggregate_volume_metrics(activities)           │
│  → total_volume_usd, trades, traders, avg_size  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  aggregate_gas_metrics(activities)              │
│  → total_gas, avg_gas, total_cost, avg_cost     │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  aggregate_mev_metrics(activities)              │
│  → total_profit, count, percentage, types       │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  aggregate_cross_chain_metrics(activities)      │
│  → bridged_volume, count, routes, protocols     │
└─────────────────────────────────────────────────┘
```

## Key Features

✓ **Type Safety**: Full Python type hints and validation
✓ **Precision**: Decimal type for financial calculations
✓ **Computed Properties**: Automatic derived metrics
✓ **Flexible Export**: Dictionary conversion for APIs
✓ **Data Provenance**: Track data sources
✓ **Extensible**: Easy to add chains/types/dimensions

## Usage Flow

```
1. Create Dimensions
   └─> TimeDimension, PriceDimension, etc.

2. Build Activity
   └─> DeFiMarketActivity(time, transaction, ...)

3. Access Properties
   └─> activity.total_value_usd, is_mev_activity

4. Export or Store
   └─> activity.to_dict()

5. Aggregate Multiple
   └─> aggregate_*_metrics([activity1, activity2, ...])
```

## Example Metrics Captured

### Volume Metrics
- Trading volume (USD)
- Total Value Locked (TVL)
- Liquidity depth
- Number of trades
- Unique traders
- Average trade size

### Price Metrics
- Spot prices (USD)
- Price impact (%)
- Slippage (%)
- Volatility (24h)

### Transaction Metrics
- Gas used
- Gas price (gwei)
- Transaction fees (USD)
- Success/failure rate

### MEV Metrics
- MEV profit (USD)
- MEV type distribution
- Sandwich attack rate
- Searcher identification

### Cross-Chain Metrics
- Bridged volume (USD)
- Bridge fees
- Popular routes
- Protocol usage
- Bridge completion rate

## Data Storage Compatibility

```
Time-Series DBs    │ InfluxDB, TimescaleDB
Document Stores    │ MongoDB, Elasticsearch  
Data Warehouses    │ BigQuery, Snowflake
Graph Databases    │ Neo4j
Relational DBs     │ PostgreSQL, MySQL
```

## Quick Start

```python
from defi_market_dimensions import *
from datetime import datetime
from decimal import Decimal

# Create activity
activity = DeFiMarketActivity(
    time=TimeDimension(datetime.now(), 18500000, "0x...", 42),
    transaction=TransactionDimension(
        "0x...", TransactionType.SWAP, "0xfrom", "0xto",
        150000, Decimal("30"), Decimal("12.50"), True
    ),
    chain=ChainType.ETHEREUM
)

# Access metrics
print(f"Total Value: ${activity.total_value_usd}")

# Export
data = activity.to_dict()
```

For full documentation, see DIMENSIONS.md
For examples, see examples.py
