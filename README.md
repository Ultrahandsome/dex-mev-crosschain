# dex-mev-crosschain

A comprehensive framework for capturing and analyzing the core dimensions of DeFi market activity, including DEX trading, MEV extraction, and cross-chain bridge operations.

## Overview

This project provides structured data models and utilities to capture, analyze, and aggregate key metrics from DeFi market activities across multiple blockchains. It enables traders, researchers, and developers to monitor and understand DeFi markets through multiple dimensions.

## Core Features

### Multi-Dimensional Market Activity Capture

Captures **8 core dimensions** of DeFi market activity:

1. **Time Dimension** - Timestamps, block numbers, transaction indices
2. **Price Dimension** - Spot prices, slippage, price impact, volatility
3. **Volume Dimension** - Trading volumes, TVL, liquidity depth, trader counts
4. **Liquidity Pool Dimension** - Pool reserves, fees, DEX protocols
5. **Transaction Dimension** - Gas metrics, transaction details, success status
6. **MEV Dimension** - MEV profits, sandwich attacks, arbitrage, liquidations
7. **Cross-Chain Dimension** - Bridge activity, multi-chain flows, bridge protocols
8. **Market Metrics Dimension** - Aggregated market statistics

### Supported Chains

- Ethereum
- Binance Smart Chain (BSC)
- Polygon
- Arbitrum
- Optimism
- Avalanche
- Fantom
- Base

### Transaction Types

- Token Swaps
- Liquidity Provision (Add/Remove)
- Cross-Chain Bridges
- MEV Arbitrage
- MEV Sandwich Attacks
- MEV Liquidations

## Quick Start

### Basic Usage

```python
from defi_market_dimensions import (
    DeFiMarketActivity,
    TimeDimension,
    TransactionDimension,
    PriceDimension,
    VolumeDimension,
    ChainType,
    TransactionType
)
from datetime import datetime
from decimal import Decimal

# Create a market activity record
activity = DeFiMarketActivity(
    time=TimeDimension(
        timestamp=datetime.now(),
        block_number=18500000,
        block_hash="0x1234...",
        transaction_index=42
    ),
    transaction=TransactionDimension(
        transaction_hash="0xabcd...",
        transaction_type=TransactionType.SWAP,
        from_address="0x742d...",
        to_address="0x68b3...",
        gas_used=150000,
        gas_price_gwei=Decimal("30"),
        transaction_fee_usd=Decimal("12.50"),
        success=True
    ),
    chain=ChainType.ETHEREUM,
    data_source="etherscan_api"
)

# Access computed properties
print(f"Total Value: ${activity.total_value_usd}")
print(f"Is MEV Activity: {activity.is_mev_activity}")

# Export to dictionary
activity_dict = activity.to_dict()
```

### Metric Aggregation

```python
from defi_market_dimensions import (
    aggregate_volume_metrics,
    aggregate_gas_metrics,
    aggregate_mev_metrics,
    aggregate_cross_chain_metrics
)

# Aggregate metrics from multiple activities
volume_metrics = aggregate_volume_metrics(activities)
gas_metrics = aggregate_gas_metrics(activities)
mev_metrics = aggregate_mev_metrics(activities)
cross_chain_metrics = aggregate_cross_chain_metrics(activities)
```

### Run Examples

```bash
python examples.py
```

This will demonstrate:
- Uniswap swap capture
- MEV sandwich attack tracking
- Cross-chain bridge monitoring
- Liquidity provision recording
- Comprehensive metric aggregation

## Documentation

- **[DIMENSIONS.md](DIMENSIONS.md)** - Detailed documentation of all dimensions, features, and use cases
- **[examples.py](examples.py)** - Comprehensive usage examples and demonstrations

## Use Cases

- **Market Analysis** - Analyze trading patterns, volumes, and liquidity
- **MEV Research** - Track and quantify MEV extraction
- **Cross-Chain Monitoring** - Monitor bridge activity and flows
- **Risk Management** - Assess slippage and market depth
- **Data Analytics** - Build time-series DeFi databases
- **Trading Strategies** - Inform decisions with market data
- **Academic Research** - Study DeFi market microstructure

## Project Structure

```
dex-mev-crosschain/
├── README.md                      # This file
├── DIMENSIONS.md                  # Detailed dimension documentation
├── defi_market_dimensions.py      # Core dimension classes and utilities
└── examples.py                    # Usage examples and demonstrations
```

## Key Features

- **Type Safety** - Full Python type hints and dataclass validation
- **Decimal Precision** - Uses `Decimal` for accurate financial calculations
- **Computed Properties** - Automatic calculations (avg trade size, gas costs, etc.)
- **Flexible Export** - Convert to dictionaries for storage/APIs
- **Data Provenance** - Track data sources for each activity
- **Extensible Design** - Easy to add new chains, transaction types, and dimensions

## Dependencies

Standard Python 3.7+ libraries only:
- `dataclasses`
- `datetime`
- `decimal`
- `enum`
- `typing`

No external dependencies required!

## Contributing

Contributions are welcome! When adding features:
1. Follow existing dataclass patterns
2. Add validation and type hints
3. Update documentation and examples
4. Ensure backward compatibility

## License

This project captures DeFi market activity dimensions for MEV and cross-chain DEX applications.