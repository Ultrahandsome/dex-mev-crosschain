"""
Example usage of DeFi Market Activity Dimensions

This module demonstrates how to use the core dimensions to capture and analyze
DeFi market activity across different scenarios.
"""

import json
from datetime import datetime
from decimal import Decimal
from defi_market_dimensions import (
    DeFiMarketActivity,
    TimeDimension,
    PriceDimension,
    VolumeDimension,
    LiquidityPoolDimension,
    TransactionDimension,
    MEVDimension,
    CrossChainDimension,
    MarketMetricsDimension,
    ChainType,
    TransactionType,
    aggregate_volume_metrics,
    aggregate_gas_metrics,
    aggregate_mev_metrics,
    aggregate_cross_chain_metrics,
)


def example_uniswap_swap():
    """Example: Capture a Uniswap swap transaction"""
    
    # Time dimension
    time = TimeDimension(
        timestamp=datetime.now(),
        block_number=18500000,
        block_hash="0x1234567890abcdef",
        transaction_index=42
    )
    
    # Transaction dimension
    transaction = TransactionDimension(
        transaction_hash="0xabcdef1234567890",
        transaction_type=TransactionType.SWAP,
        from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        to_address="0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
        gas_used=150000,
        gas_price_gwei=Decimal("30"),
        transaction_fee_usd=Decimal("12.50"),
        success=True
    )
    
    # Price dimensions
    prices = [
        PriceDimension(
            token_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            token_symbol="WETH",
            spot_price_usd=Decimal("2500.00"),
            price_impact_percent=Decimal("0.05"),
            slippage_percent=Decimal("0.1")
        ),
        PriceDimension(
            token_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            token_symbol="USDC",
            spot_price_usd=Decimal("1.00"),
            price_impact_percent=Decimal("0.02"),
            slippage_percent=Decimal("0.05")
        )
    ]
    
    # Volume dimension
    volume = VolumeDimension(
        trading_volume_usd=Decimal("25000.00"),
        trading_volume_24h_usd=Decimal("1500000.00"),
        total_value_locked_usd=Decimal("50000000.00"),
        liquidity_depth_usd=Decimal("2000000.00"),
        number_of_trades=1,
        unique_traders=1
    )
    
    # Liquidity pool dimension
    liquidity_pool = LiquidityPoolDimension(
        pool_address="0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
        dex_protocol="uniswap_v3",
        token0_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        token0_symbol="USDC",
        token0_reserve=Decimal("25000000.00"),
        token1_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        token1_symbol="WETH",
        token1_reserve=Decimal("10000.00"),
        pool_fee_percent=Decimal("0.05"),
        pool_tvl_usd=Decimal("50000000.00")
    )
    
    # Create activity
    activity = DeFiMarketActivity(
        time=time,
        transaction=transaction,
        prices=prices,
        volume=volume,
        liquidity_pool=liquidity_pool,
        chain=ChainType.ETHEREUM,
        data_source="etherscan_api"
    )
    
    return activity


def example_mev_sandwich_attack():
    """Example: Capture an MEV sandwich attack"""
    
    time = TimeDimension(
        timestamp=datetime.now(),
        block_number=18500001,
        block_hash="0xabcdef1234567890",
        transaction_index=15
    )
    
    transaction = TransactionDimension(
        transaction_hash="0x9876543210fedcba",
        transaction_type=TransactionType.MEV_SANDWICH,
        from_address="0x0000000000007F150Bd6f54c40A34d7C3d5e9f56",
        to_address="0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
        gas_used=250000,
        gas_price_gwei=Decimal("50"),
        transaction_fee_usd=Decimal("25.00"),
        success=True
    )
    
    # MEV dimension
    mev = MEVDimension(
        mev_type=TransactionType.MEV_SANDWICH,
        mev_profit_usd=Decimal("1500.00"),
        bundle_hash="0xbundle123456789",
        front_run_tx="0xfront123",
        victim_tx="0xvictim456",
        back_run_tx="0xback789",
        searcher_address="0x0000000000007F150Bd6f54c40A34d7C3d5e9f56"
    )
    
    prices = [
        PriceDimension(
            token_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            token_symbol="WETH",
            spot_price_usd=Decimal("2500.00"),
            price_impact_percent=Decimal("0.8"),
            slippage_percent=Decimal("1.2")
        )
    ]
    
    activity = DeFiMarketActivity(
        time=time,
        transaction=transaction,
        prices=prices,
        mev=mev,
        chain=ChainType.ETHEREUM,
        data_source="flashbots_relay"
    )
    
    return activity


def example_cross_chain_bridge():
    """Example: Capture a cross-chain bridge transaction"""
    
    time = TimeDimension(
        timestamp=datetime.now(),
        block_number=18500002,
        block_hash="0xfedcba9876543210",
        transaction_index=28
    )
    
    transaction = TransactionDimension(
        transaction_hash="0xbridge123456789",
        transaction_type=TransactionType.BRIDGE,
        from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        to_address="0x1116898DdA4015eD8dDefb84b6e8Bc24528Af2d8",
        gas_used=180000,
        gas_price_gwei=Decimal("35"),
        transaction_fee_usd=Decimal("15.75"),
        success=True
    )
    
    # Cross-chain dimension
    cross_chain = CrossChainDimension(
        source_chain=ChainType.ETHEREUM,
        destination_chain=ChainType.ARBITRUM,
        bridge_protocol="layerzero",
        bridged_amount_usd=Decimal("50000.00"),
        bridge_fee_usd=Decimal("25.00"),
        source_tx_hash="0xbridge123456789",
        destination_tx_hash="0xdest987654321",
        bridge_status="completed"
    )
    
    prices = [
        PriceDimension(
            token_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            token_symbol="USDC",
            spot_price_usd=Decimal("1.00"),
            price_impact_percent=Decimal("0.01"),
            slippage_percent=Decimal("0.02")
        )
    ]
    
    activity = DeFiMarketActivity(
        time=time,
        transaction=transaction,
        prices=prices,
        cross_chain=cross_chain,
        chain=ChainType.ETHEREUM,
        data_source="layerzero_api"
    )
    
    return activity


def example_liquidity_provision():
    """Example: Capture adding liquidity to a pool"""
    
    time = TimeDimension(
        timestamp=datetime.now(),
        block_number=18500003,
        block_hash="0x1111222233334444",
        transaction_index=55
    )
    
    transaction = TransactionDimension(
        transaction_hash="0xliquidity123456",
        transaction_type=TransactionType.ADD_LIQUIDITY,
        from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        to_address="0xC36442b4a4522E871399CD717aBDD847Ab11FE88",
        gas_used=220000,
        gas_price_gwei=Decimal("28"),
        transaction_fee_usd=Decimal("18.20"),
        success=True
    )
    
    liquidity_pool = LiquidityPoolDimension(
        pool_address="0xC36442b4a4522E871399CD717aBDD847Ab11FE88",
        dex_protocol="uniswap_v3",
        token0_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        token0_symbol="WETH",
        token0_reserve=Decimal("15000.00"),
        token1_address="0x6B175474E89094C44Da98b954EedeAC495271d0F",
        token1_symbol="DAI",
        token1_reserve=Decimal("37500000.00"),
        pool_fee_percent=Decimal("0.3"),
        pool_tvl_usd=Decimal("75000000.00")
    )
    
    volume = VolumeDimension(
        trading_volume_usd=Decimal("100000.00"),
        trading_volume_24h_usd=Decimal("5000000.00"),
        total_value_locked_usd=Decimal("75000000.00"),
        liquidity_depth_usd=Decimal("3000000.00"),
        number_of_trades=1,
        unique_traders=1
    )
    
    activity = DeFiMarketActivity(
        time=time,
        transaction=transaction,
        volume=volume,
        liquidity_pool=liquidity_pool,
        chain=ChainType.ETHEREUM,
        data_source="the_graph"
    )
    
    return activity


def demonstrate_aggregations():
    """Demonstrate aggregation of metrics across multiple activities"""
    
    # Create sample activities
    activities = [
        example_uniswap_swap(),
        example_mev_sandwich_attack(),
        example_cross_chain_bridge(),
        example_liquidity_provision()
    ]
    
    print("=== DeFi Market Activity Analysis ===\n")
    
    # Aggregate volume metrics
    volume_metrics = aggregate_volume_metrics(activities)
    print("Volume Metrics:")
    print(f"  Total Volume: ${volume_metrics['total_volume_usd']:,.2f}")
    print(f"  Total Trades: {volume_metrics['total_trades']}")
    print(f"  Unique Traders: {volume_metrics['unique_traders']}")
    print(f"  Avg Trade Size: ${volume_metrics['average_trade_size_usd']:,.2f}\n")
    
    # Aggregate gas metrics
    gas_metrics = aggregate_gas_metrics(activities)
    print("Gas Metrics:")
    print(f"  Total Gas Used: {gas_metrics['total_gas_used']:,}")
    print(f"  Average Gas per TX: {gas_metrics['average_gas_per_tx']:,.0f}")
    print(f"  Total Gas Cost: ${gas_metrics['total_gas_cost_usd']:,.2f}")
    print(f"  Avg Gas Cost per TX: ${gas_metrics['average_gas_cost_usd']:,.2f}\n")
    
    # Aggregate MEV metrics
    mev_metrics = aggregate_mev_metrics(activities)
    print("MEV Metrics:")
    print(f"  Total MEV Profit: ${mev_metrics['total_mev_profit_usd']:,.2f}")
    print(f"  MEV Transactions: {mev_metrics['mev_transaction_count']}")
    print(f"  MEV Percentage: {mev_metrics['mev_percentage']:.1f}%")
    print(f"  MEV Types: {mev_metrics['mev_types_distribution']}\n")
    
    # Aggregate cross-chain metrics
    cross_chain_metrics = aggregate_cross_chain_metrics(activities)
    print("Cross-Chain Metrics:")
    print(f"  Total Bridged Volume: ${cross_chain_metrics['total_bridged_volume_usd']:,.2f}")
    print(f"  Bridge Transactions: {cross_chain_metrics['bridge_transaction_count']}")
    print(f"  Popular Routes: {cross_chain_metrics['popular_routes']}")
    print(f"  Protocol Volumes: {cross_chain_metrics['protocol_volumes']}\n")
    
    # Individual activity details
    print("=== Individual Activity Details ===\n")
    for i, activity in enumerate(activities, 1):
        print(f"Activity {i}: {activity.transaction.transaction_type.value}")
        print(f"  Chain: {activity.chain.value}")
        print(f"  Block: {activity.time.block_number}")
        print(f"  TX Hash: {activity.transaction.transaction_hash}")
        print(f"  Total Value: ${activity.total_value_usd:,.2f}")
        print(f"  Is MEV: {activity.is_mev_activity}")
        print()


if __name__ == "__main__":
    # Run demonstrations
    demonstrate_aggregations()
    
    # Example: Convert activity to dictionary for storage/API response
    activity = example_uniswap_swap()
    print("=== Activity as Dictionary (for API/Storage) ===")
    print(json.dumps(activity.to_dict(), indent=2, default=str))
