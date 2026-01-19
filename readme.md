# DeFi Cross-chain MEV Analysis

Data analysis toolkit for cross-chain arbitrage, MEV detection, Aave liquidation monitoring, and Uniswap V3 liquidity analysis.

## Features

- Cross-chain arbitrage analysis between Ethereum and Arbitrum
- MEV detection for sandwich attacks and cross-pool arbitrage
- Uniswap V3 concentrated liquidity distribution analysis
- Aave protocol liquidation event tracking
- Lido stETH staking yield analysis
- Automated data visualization and reporting

## Supported Networks

- **Ethereum** - Uniswap V3, Aave V2, Lido stETH
- **Arbitrum** - Uniswap V3, Aave V3
- **Base** (partial) - Uniswap V3

## Requirements

- Python 3.9+
- RPC endpoint access (Infura, Alchemy, or other Ethereum RPC providers)

## Installation

### 1. Clone and install dependencies

```bash
git clone <repository-url>
cd dex-mev-crosschain

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure RPC endpoints

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your RPC URLs
vim .env
```

Example .env file:
```env
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/your_project_id
ARBITRUM_RPC_URL=https://arbitrum-mainnet.infura.io/v3/your_project_id
```

### 3. Verify setup

```bash
# Test RPC connections
python3 -m src.check_rpc --chains ethereum arbitrum
```

## Usage

```bash
# Run complete data collection pipeline (500 blocks test)
python3 -m src.run_all

# Generate analysis charts
python3 -m src.analysis

# Generate categorized charts
python3 -m src.visualize
```

## Pipeline Overview

1. check_rpc.py → 2. get_pool.py → 3. spot_price.py → 4. swaps.py → 5. price_series.py → 6. crosschain.py → 7. crosschain_cost.py → 8. mev_detect.py → 9. aave.py → 10. staking_lido.py → 11. liquidity_profile.py → 12. analysis.py

## Project Structure

```
dex-mev-crosschain/
├── src/
│   ├── check_rpc.py              # RPC connection testing
│   ├── get_pool.py               # Uniswap V3 pool discovery
│   ├── spot_price.py             # Spot price queries
│   ├── swaps.py                  # Swap event extraction
│   ├── price_series.py           # Price time series construction
│   ├── crosschain.py             # Cross-chain spread analysis
│   ├── crosschain_cost.py        # Cost-aware arbitrage analysis
│   ├── mev_detect.py             # MEV detection algorithms
│   ├── aave.py                   # Aave liquidation monitoring
│   ├── staking_lido.py           # Lido staking analysis
│   ├── liquidity_profile.py      # Liquidity distribution analysis
│   ├── analysis.py               # Comprehensive data visualization
│   ├── visualize.py              # Categorized chart generation
│   ├── run_all.py                # Complete pipeline execution
│   └── ...                       # Utility modules
├── configs/
│   ├── addresses.yaml            # Token address configuration
│   ├── chains.yaml               # Blockchain configuration
│   └── pairs.yaml                # Trading pair configuration
├── abis/                         # Smart contract ABIs
├── data/
│   ├── csv/                      # Data files
│   ├── figs/                     # Basic charts
│   └── analysis/                 # Categorized charts
│       ├── prices/               # Price analysis
│       ├── spreads/              # Spread analysis
│       ├── liquidity/            # Liquidity analysis
│       ├── liquidations/         # Liquidation analysis
│       ├── staking/              # Staking analysis
│       └── swaps/                # Swap analysis
├── requirements.txt
├── setup.py
├── .env.example
├── DEPLOYMENT.md
└── readme.md

## Output Data Files

```
data/csv/
├── pools_found_{chain}.csv       # Pool address information
├── spot_price_{chain}.csv        # Spot price data
├── swaps_{chain}_{blocks}.csv    # Swap event data
├── price_series_{chain}_{blocks}.csv # Minute-level price series
├── crosschain_spread_*.csv       # Cross-chain spread analysis
├── crosschain_cost_*.csv         # Cost-aware arbitrage analysis
├── mev_suspects_{chain}_*.csv    # MEV suspicious events
├── mev_summary_{chain}_*.csv     # MEV activity summary
├── liquidations_{chain}_*.csv    # Aave liquidation events
├── staking_returns_*.csv         # Lido staking returns
└── liquidity_profile_{chain}_*.csv # Liquidity distribution
```
	•	[words_each_side]（可选，默认 10）tickBitmap 的 word 数（每 word 覆盖 256 * tickSpacing 个 tick）

命令示例：
	•	python3 -m src.liquidity_profile ethereum WETH:USDC 500 10
	•	python3 -m src.liquidity_profile arbitrum WETH:USDC 500 5

产出：liquidity_profile_<chain>_<PAIR无分隔>_<fee>.csv
（含列：tick,price_t1_per_t0,liquidity_net,liquidity_gross,active_liquidity,word_index）

⸻

12) analysis.py —— 数据可视化分析

用途：读取所有前序步骤生成的 CSV 文件，生成综合的数据可视化图表。
参数：
	•	--span（可选，默认 500）数据采集的区块跨度
	•	--thr_bps（可选，默认 30）跨链价差阈值（bps）
	•	--fee_bps_each（可选，默认 5）单边 DEX 手续费（bps）
	•	--bridge_bps（可选，默认 10）跨链成本（bps）
	•	--mev_min_bp（可选，默认 10）MEV 价格变动阈值（bps）
	•	--liq_span（可选，默认 50000）Aave 清算数据区块跨度
	•	--staking_days（可选，默认 7）Lido 质押数据天数

命令示例：
	•	python3 -m src.analysis
	•	python3 -m src.analysis --span 500 --thr_bps 30

产出图表（保存至 data/figs/）：
	•	价格分析：price_vwap_eth_vs_arb_*.png, spread_timeseries_*.png, spread_hist_*.png
	•	套利分析：spread_threshold_*.png, net_bps_costed_*.png, net_bps_hist_*.png
	•	MEV分析：mev_top_actors_*.png, mev_price_move_hist_*.png
	•	流动性：liq_profile_active_*.png, liq_profile_net_*.png
	•	风险监控：liquidations_vs_price_*.png
	•	质押收益：staking_share_to_eth_*.png, staking_apy_*.png

⸻

## 使用示例

### 单独运行模块
```bash
# 检查 RPC 连接
python3 -m src.check_rpc ethereum

# 获取池地址
python3 -m src.get_pool ethereum

# 抓取交易数据
python3 -m src.swaps --chain ethereum --blocks 1000

# 分析跨链套利机会
python3 -m src.crosschain_cost --span 1000 --fee_bps_each_side 5

# 检测 MEV 活动
python3 -m src.mev_detect --chain ethereum --span 1000 --min_bp 10

# 生成特定分析图表
python3 -m src.analysis --span 1000 --thr_bps 50
```

### 配置 RPC 端点
在项目根目录创建 `.env` 文件：
```
ETHEREUM_RPC_URL=https://your-ethereum-rpc-url
ARBITRUM_RPC_URL=https://your-arbitrum-rpc-url
```

## 技术特性

- **多链支持** - 同时支持 Ethereum、Arbitrum、Base
- **高性能** - 并发 RPC 调用、本地区块时间戳缓存
- **容错性** - 多 RPC 端点自动切换、错误重试机制  
- **模块化设计** - 每个功能独立可运行，支持增量分析
- **数据完整性** - 链名区分输出，避免文件覆盖
- **专业可视化** - 自动生成高质量分析图表

## 注意事项

- 脚本会自动解析池地址（优先 pools_found_{chain}.csv，失败则走 Factory）
- 对公共 RPC 的区块限制做分片与退避处理
- 如果清空了 data/csv/，请按文档顺序重新生成所有 CSV
- 建议配置私有 RPC 端点以获得更好的性能和稳定性
- 大区块跨度查询可能需要较长时间，建议先用小参数测试

## 许可证

MIT License