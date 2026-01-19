# DeFi Market Activity Dimensions

A comprehensive framework for capturing and analyzing the core dimensions of DeFi (Decentralized Finance) market activity across multiple blockchains, including DEX trading, MEV extraction, and cross-chain bridge operations.

## Overview

This project provides structured data models and utilities to capture, analyze, and aggregate key metrics from DeFi market activities. It's designed to help traders, researchers, and developers understand and monitor DeFi markets across multiple dimensions.

## Core Dimensions

The framework captures the following core dimensions of DeFi market activity:

### 1. **Time Dimension** (`TimeDimension`)
Temporal context for market activities:
- Timestamp (datetime)
- Block number and hash
- Transaction index within block
- Epoch milliseconds for time-series analysis

### 2. **Price Dimension** (`PriceDimension`)
Price-related metrics:
- Token address and symbol
- Spot price in USD
- Price impact percentage
- Slippage percentage
- 24-hour volatility

### 3. **Volume Dimension** (`VolumeDimension`)
Trading volume and liquidity metrics:
- Trading volume (current and 24h)
- Total Value Locked (TVL)
- Liquidity depth
- Number of trades and unique traders
- Average trade size calculation

### 4. **Liquidity Pool Dimension** (`LiquidityPoolDimension`)
Pool-specific metrics:
- Pool address and DEX protocol
- Token pair information and reserves
- Pool fees and TVL
- Token pair formatting

### 5. **Transaction Dimension** (`TransactionDimension`)
Blockchain transaction details:
- Transaction hash and type
- From/to addresses
- Gas usage and pricing
- Transaction fees in USD
- Success/failure status

### 6. **MEV Dimension** (`MEVDimension`)
Maximum Extractable Value metrics:
- MEV type (arbitrage, sandwich, liquidation)
- Profit in USD
- Bundle information
- Front-run, victim, and back-run transactions
- Searcher address identification

### 7. **Cross-Chain Dimension** (`CrossChainDimension`)
Bridge and cross-chain activity:
- Source and destination chains
- Bridge protocol used
- Bridged amount and fees
- Transaction hashes on both chains
- Bridge status tracking
- Chain route formatting

### 8. **Market Metrics Dimension** (`MarketMetricsDimension`)
Aggregated market-level metrics:
- Named metrics with values
- Aggregation periods (1h, 24h, 7d, etc.)
- Market cap and supply metrics
- Calculation timestamps

## Supported Chains

The framework supports major blockchain networks:
- Ethereum
- Binance Smart Chain (BSC)
- Polygon
- Arbitrum
- Optimism
- Avalanche
- Fantom
- Base

## Transaction Types

Captures various DeFi transaction types:
- **Swap**: Token swaps on DEXes
- **Add/Remove Liquidity**: Liquidity provision operations
- **Bridge**: Cross-chain bridge transactions
- **MEV Arbitrage**: Arbitrage MEV extraction
- **MEV Sandwich**: Sandwich attack transactions
- **MEV Liquidation**: Liquidation MEV extraction

## Data Structure

The main `DeFiMarketActivity` class combines all dimensions to provide a comprehensive view of any DeFi market event:

```python
from defi_market_dimensions import (
    DeFiMarketActivity,
    TimeDimension,
    TransactionDimension,
    ChainType,
    TransactionType
)
from datetime import datetime
from decimal import Decimal

# Create a comprehensive market activity record
activity = DeFiMarketActivity(
    time=TimeDimension(
        timestamp=datetime.now(),
        block_number=18500000,
        block_hash="0x...",
        transaction_index=42
    ),
    transaction=TransactionDimension(
        transaction_hash="0x...",
        transaction_type=TransactionType.SWAP,
        from_address="0x...",
        to_address="0x...",
        gas_used=150000,
        gas_price_gwei=Decimal("30"),
        transaction_fee_usd=Decimal("12.50"),
        success=True
    ),
    chain=ChainType.ETHEREUM,
    data_source="etherscan_api"
)
```

## Aggregation Functions

The framework provides built-in aggregation utilities:

### Volume Aggregation
```python
from defi_market_dimensions import aggregate_volume_metrics

metrics = aggregate_volume_metrics(activities)
# Returns: total_volume_usd, total_trades, unique_traders, average_trade_size_usd
```

### Gas Aggregation
```python
from defi_market_dimensions import aggregate_gas_metrics

metrics = aggregate_gas_metrics(activities)
# Returns: total_gas_used, average_gas_per_tx, total/average_gas_cost_usd
```

### MEV Aggregation
```python
from defi_market_dimensions import aggregate_mev_metrics

metrics = aggregate_mev_metrics(activities)
# Returns: total_mev_profit_usd, mev_transaction_count, mev_percentage, mev_types_distribution
```

### Cross-Chain Aggregation
```python
from defi_market_dimensions import aggregate_cross_chain_metrics

metrics = aggregate_cross_chain_metrics(activities)
# Returns: total_bridged_volume_usd, bridge_transaction_count, popular_routes, protocol_volumes
```

## Usage Examples

See `examples.py` for comprehensive usage examples including:

1. **Uniswap Swap**: Capturing a standard DEX swap transaction
2. **MEV Sandwich Attack**: Recording MEV extraction activities
3. **Cross-Chain Bridge**: Tracking bridge transactions
4. **Liquidity Provision**: Monitoring liquidity pool operations
5. **Metric Aggregation**: Analyzing multiple activities together

Run the examples:
```bash
python examples.py
```

## Key Features

### Computed Properties
Many dimension classes include computed properties for convenience:
- `average_trade_size_usd`: Automatic calculation from volume/trade count
- `gas_cost_eth`: Convert gas to ETH from gwei
- `is_sandwich_attack`: Quick MEV type checking
- `is_completed`: Bridge status checking
- `chain_route`: Formatted cross-chain route
- `pool_pair`: Formatted token pair

### Data Validation
Built-in validation ensures data integrity:
- Price values cannot be negative
- Decimal precision for financial calculations
- Type checking via Python type hints
- Enums for categorical data

### Export Capabilities
Convert activities to dictionaries for storage or API responses:
```python
activity_dict = activity.to_dict()
# Returns structured dictionary with all dimensions
```

### Flexible Data Sources
Track data provenance with `data_source` field:
- Etherscan API
- The Graph
- Flashbots Relay
- Custom data sources

## Use Cases

This framework is ideal for:

1. **Market Analysis**: Analyze trading patterns, volumes, and liquidity across DEXes
2. **MEV Research**: Track and quantify MEV extraction activities
3. **Cross-Chain Monitoring**: Monitor bridge activity and cross-chain flows
4. **Risk Management**: Assess slippage, price impact, and market depth
5. **Data Analytics**: Build time-series databases of DeFi activity
6. **Trading Strategies**: Inform trading decisions with comprehensive market data
7. **Academic Research**: Study DeFi market microstructure
8. **Regulatory Reporting**: Capture detailed transaction information

## Data Storage

The structured format makes it easy to store data in various backends:

- **Time-series databases**: InfluxDB, TimescaleDB
- **Document stores**: MongoDB, Elasticsearch
- **Data warehouses**: BigQuery, Snowflake
- **Graph databases**: Neo4j (for network analysis)

## Extending the Framework

The modular design allows easy extension:

1. Add new chain types to `ChainType` enum
2. Define new transaction types in `TransactionType` enum
3. Create additional dimension classes following the same pattern
4. Add new aggregation functions for custom analytics

## Dependencies

- Python 3.7+
- dataclasses (standard library)
- datetime (standard library)
- decimal (standard library for precise financial calculations)
- enum (standard library)
- typing (standard library)

## Best Practices

1. **Use Decimal for Money**: Always use `Decimal` type for financial values to avoid floating-point precision issues
2. **Validate Inputs**: Leverage dataclass validation and type hints
3. **Track Sources**: Always set the `data_source` field for data provenance
4. **Batch Processing**: Use aggregation functions for analyzing multiple activities
5. **Raw Data**: Store original data in the `raw_data` field for reference

## Contributing

When adding new dimensions or features:
1. Follow the existing dataclass pattern
2. Add validation in `__post_init__` methods
3. Include computed properties for common calculations
4. Update documentation and examples
5. Ensure backward compatibility

## License

This project is designed for capturing DeFi market activity dimensions in MEV and cross-chain DEX applications.
