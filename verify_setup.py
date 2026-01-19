#!/usr/bin/env python3
"""
Deployment verification script - Check if project is properly installed and configured
"""

import sys
import os
import importlib
from pathlib import Path

def check_python_version():
    """Check Python version"""
    print("Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.9+")
        return False

def check_dependencies():
    """Check project dependencies"""
    print("\nChecking dependencies...")
    
    dependencies = [
        ('web3', 'Web3 blockchain interaction'),
        ('pandas', 'Data processing'),
        ('numpy', 'Numerical computing'),
        ('matplotlib', 'Data visualization'),
        ('yaml', 'YAML configuration'),
        ('tenacity', 'Retry logic'),
        ('tqdm', 'Progress bars'),
        ('dotenv', 'Environment variables'),
    ]
    
    all_ok = True
    for dep, desc in dependencies:
        try:
            importlib.import_module(dep)
            print(f"✅ {dep:<15} - {desc}")
        except ImportError:
            print(f"❌ {dep:<15} - MISSING ({desc})")
            all_ok = False
    
    return all_ok

def check_project_structure():
    """Check project structure"""
    print("\nChecking project structure...")
    
    required_files = [
        'src/__init__.py',
        'src/run_all.py',
        'src/check_rpc.py',
        'configs/addresses.yaml',
        'configs/chains.yaml',
        'abis/UniswapV3Factory.json',
        'requirements.txt',
        '.env.example',
    ]
    
    required_dirs = [
        'src',
        'configs', 
        'abis',
        'data/csv',
    ]
    
    all_ok = True
    
    # Check directories
    for dirname in required_dirs:
        if os.path.isdir(dirname):
            print(f"✅ {dirname}/ - Directory exists")
        else:
            print(f"❌ {dirname}/ - Directory missing")
            all_ok = False
    
    # Check files
    for filename in required_files:
        if os.path.isfile(filename):
            print(f"✅ {filename} - File exists")
        else:
            print(f"❌ {filename} - File missing")
            all_ok = False
    
    return all_ok

def check_env_config():
    """Check environment configuration"""
    print("\nChecking environment configuration...")
    
    if os.path.isfile('.env'):
        print("✅ .env file exists")
        # Check key environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        env_vars = ['ETHEREUM_RPC_URL', 'ARBITRUM_RPC_URL']
        for var in env_vars:
            value = os.getenv(var)
            if value and value != 'https://mainnet.infura.io/v3/YOUR_PROJECT_ID':
                print(f"✅ {var} - Configured")
            else:
                print(f"⚠️  {var} - Not configured or using placeholder")
        return True
    else:
        print("⚠️  .env file not found - Copy .env.example to .env and configure")
        return False

def check_imports():
    """Check project module imports"""
    print("\nChecking project imports...")
    
    modules = [
        'src.rpc',
        'src.univ3',
        'src.get_pool',
        'src.spot_price',
        'src.run_all',
    ]
    
    all_ok = True
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module} - Import OK")
        except ImportError as e:
            print(f"❌ {module} - Import failed: {e}")
            all_ok = False
    
    return all_ok

def main():
    """Main verification workflow"""
    print("DEX MEV CrossChain - Deployment Verification")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies), 
        ("Project Structure", check_project_structure),
        ("Environment Config", check_env_config),
        ("Module Imports", check_imports),
    ]
    
    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))
    
    print("\n" + "=" * 50)
    print("VERIFICATION SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:<20} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("ALL CHECKS PASSED! Project is ready to use.")
        print("\nNext steps:")
        print("1. Configure your RPC URLs in .env")
        print("2. Run: python3 -m src.check_rpc --chains ethereum arbitrum")
        print("3. Run: python3 -m src.run_all")
    else:
        print("SOME CHECKS FAILED! Please fix the issues above.")
        print("\nRefer to DEPLOYMENT.md for detailed setup instructions.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
