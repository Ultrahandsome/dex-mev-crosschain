# Deployment Guide

## System Requirements

- **Python 3.9+** (required)
- **Operating System**: macOS, Linux, Windows
- **Memory**: Recommended 4GB+ RAM
- **Storage**: At least 1GB available space
- **Network**: Stable internet connection (for RPC calls)

## Deployment Steps

### Method 1: Direct Installation

```bash
# 1. Clone project
git clone <your-repository-url>
cd dex-mev-crosschain

# 2. Create virtual environment (strongly recommended)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env file, fill in your RPC URLs

# 5. Test installation
python3 -m src.check_rpc --chains ethereum arbitrum
```

### Method 2: Using setup.py

```bash
# Clone and enter directory
git clone <your-repository-url>
cd dex-mev-crosschain

# Install project (including all dependencies)
pip install -e .

# Configure environment variables
cp .env.example .env
# Edit .env to fill in RPC URLs
```

## RPC Provider Configuration

### Infura (Recommended)

1. Visit https://infura.io/
2. Register account and create project
3. Get project ID
4. Configure in `.env`:

```env
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_PROJECT_ID
ARBITRUM_RPC_URL=https://arbitrum-mainnet.infura.io/v3/YOUR_PROJECT_ID
```

### Alchemy (Alternative)

```env
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY
ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/YOUR_API_KEY
```

## Verify Deployment

```bash
# 1. Test Python environment and dependencies
python3 -c "
import web3, pandas, numpy, matplotlib, yaml, tenacity, tqdm
from dotenv import load_dotenv
print('✅ All dependencies imported successfully')
"

# 2. Test RPC connections
python3 -m src.check_rpc --chains ethereum arbitrum

# 3. Run simple test
python3 -m src.get_pool --chain ethereum --pair WETH:USDC --fee 500

# 4. Run complete pipeline (small data test)
SPAN_SWAPS=100 python3 -m src.run_all
```

## Troubleshooting

### Python 版本问题
```bash
# 检查 Python 版本
python3 --version
# 应该是 3.9 或更高

# 如果版本过低，使用 pyenv 升级:
pyenv install 3.9.6
pyenv global 3.9.6
```

### 依赖安装失败
```bash
# 升级 pip
pip install --upgrade pip

# 清理缓存重新安装
pip cache purge
pip install -r requirements.txt --no-cache-dir
```

### RPC 连接问题
```bash
# 测试网络连接
curl https://mainnet.infura.io/v3/YOUR_PROJECT_ID \\
  -X POST \\
  -H "Content-Type: application/json" \\
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# 应该返回最新区块号
```

### 权限问题 (Linux/macOS)
```bash
# 确保有写权限
chmod +x setup.py
mkdir -p data/csv data/figs data/analysis
chmod 755 data/csv data/figs data/analysis
```

## 生产环境建议

### 1. 系统服务配置 (systemd)
```ini
# /etc/systemd/system/dex-mev.service
[Unit]
Description=DEX MEV Analysis Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/dex-mev-crosschain
Environment=PATH=/path/to/venv/bin
ExecStart=/path/to/venv/bin/python -m src.run_all
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2. Cron 定时任务
```bash
# 每小时运行一次数据收集
0 * * * * cd /path/to/dex-mev-crosschain && /path/to/venv/bin/python -m src.run_all

# 每天生成分析报告
0 6 * * * cd /path/to/dex-mev-crosschain && /path/to/venv/bin/python -m src.analysis
```

### 3. 日志管理
```bash
# 创建日志目录
mkdir -p logs

# 运行时重定向日志
python3 -m src.run_all > logs/run_$(date +%Y%m%d_%H%M%S).log 2>&1
```

## 性能优化

- **并发控制**: 根据 RPC 限制调整请求频率
- **缓存利用**: 启用区块时间戳缓存以加速重复查询
- **数据清理**: 定期清理旧的 CSV 文件以节省存储空间
- **监控设置**: 监控 RPC 调用量和成本

## 安全注意事项

- ✅ **永远不要提交 `.env` 文件到版本控制**
- ✅ **定期轮换 API 密钥**
- ✅ **监控 RPC 使用量避免超额费用**
- ✅ **在生产环境中使用专用的 RPC 端点**
