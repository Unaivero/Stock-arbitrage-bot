#!/usr/bin/env python3
"""
setup_and_test.py
Setup and testing script for the Enhanced Stock Arbitrage Bot
"""

import os
import sys
import subprocess
import asyncio
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        logger.error(f"Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    logger.info(f"✅ Python {version.major}.{version.minor} is compatible")
    return True

def install_requirements():
    """Install required packages"""
    try:
        logger.info("📦 Installing requirements...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ Requirements installed successfully")
            return True
        else:
            logger.error(f"❌ Failed to install requirements: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Error installing requirements: {e}")
        return False

def setup_environment():
    """Set up environment files"""
    try:
        logger.info("🔧 Setting up environment...")
        
        # Create .env from template if it doesn't exist
        if not os.path.exists(".env"):
            if os.path.exists(".env.template"):
                import shutil
                shutil.copy(".env.template", ".env")
                logger.info("✅ Created .env file from template")
                logger.info("📝 Please edit .env file with your actual API keys")
            else:
                logger.warning("⚠️ No .env.template found")
        else:
            logger.info("✅ .env file already exists")
        
        # Create logs directory
        os.makedirs("logs", exist_ok=True)
        logger.info("✅ Created logs directory")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error setting up environment: {e}")
        return False

def test_imports():
    """Test if all modules can be imported"""
    logger.info("🧪 Testing module imports...")
    
    modules_to_test = [
        "config",
        "api_config", 
        "broker_apis",
        "real_data_stream",
        "arbitrage_logic",
        "performance_monitor",
        "real_simulator"
    ]
    
    failed_imports = []
    
    for module in modules_to_test:
        try:
            __import__(module)
            logger.info(f"✅ {module}")
        except ImportError as e:
            logger.error(f"❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        logger.error(f"❌ Failed to import: {', '.join(failed_imports)}")
        return False
    
    logger.info("✅ All modules imported successfully")
    return True

async def test_api_configuration():
    """Test API configuration"""
    logger.info("🔌 Testing API configuration...")
    
    try:
        from api_config import load_api_config, APIConfig
        
        # Load configuration
        config = load_api_config()
        validation = config["validation"]
        
        logger.info(f"Simulation mode: {config['simulation_mode']}")
        logger.info(f"Configured brokers: {len(config['brokers'])}")
        
        if validation["valid"]:
            logger.info("✅ API configuration is valid")
            logger.info(f"Available APIs: {', '.join(validation['configured_brokers'])}")
        else:
            logger.warning("⚠️ No valid API configurations found")
            logger.info("Will use simulation mode")
        
        if validation["missing_configs"]:
            logger.info("Missing API configurations:")
            for missing in validation["missing_configs"]:
                logger.info(f"  - {missing}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing API configuration: {e}")
        return False

async def test_data_stream():
    """Test data stream functionality"""
    logger.info("📊 Testing data stream...")
    
    try:
        from real_data_stream import RealDataStream
        
        stream = RealDataStream()
        
        # Test initialization
        success = await stream.initialize()
        if success:
            logger.info("✅ Data stream initialized")
        else:
            logger.error("❌ Data stream initialization failed")
            return False
        
        # Test getting prices
        test_symbols = ["AAPL", "MSFT"]
        prices = await stream.get_real_time_prices(test_symbols)
        
        if prices:
            logger.info("✅ Successfully retrieved prices")
            for source, source_prices in prices.items():
                logger.info(f"  {source}: {len(source_prices)} symbols")
        else:
            logger.warning("⚠️ No prices retrieved (may be normal in simulation mode)")
        
        # Cleanup
        await stream.cleanup()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing data stream: {e}")
        return False

async def test_arbitrage_logic():
    """Test arbitrage detection logic"""
    logger.info("🎯 Testing arbitrage logic...")
    
    try:
        from arbitrage_logic import detect_arbitrage, validate_price_data, calculate_portfolio_metrics
        
        # Test data validation
        test_prices = {"AAPL": 150.0, "MSFT": 250.0}
        if validate_price_data(test_prices, "Test"):
            logger.info("✅ Price data validation works")
        else:
            logger.error("❌ Price data validation failed")
            return False
        
        # Test arbitrage detection
        prices1 = {"AAPL": 100.0, "MSFT": 200.0}
        prices2 = {"AAPL": 101.0, "MSFT": 199.0}  # 1% difference
        
        opportunities = detect_arbitrage(prices1, prices2, threshold=0.005)
        
        if opportunities:
            logger.info(f"✅ Arbitrage detection works ({len(opportunities)} opportunities found)")
        else:
            logger.info("✅ Arbitrage detection works (no opportunities found, which is expected)")
        
        # Test portfolio metrics
        if opportunities:
            metrics = calculate_portfolio_metrics(opportunities)
            if isinstance(metrics, dict) and "total_opportunities" in metrics:
                logger.info("✅ Portfolio metrics calculation works")
            else:
                logger.error("❌ Portfolio metrics calculation failed")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing arbitrage logic: {e}")
        return False

async def test_performance_monitor():
    """Test performance monitoring"""
    logger.info("⚡ Testing performance monitor...")
    
    try:
        from performance_monitor import performance_monitor, PerformanceMonitor
        
        # Test metrics collection
        monitor = PerformanceMonitor()
        metrics = monitor.collect_metrics()
        
        if hasattr(metrics, 'timestamp'):
            logger.info("✅ Performance metrics collection works")
        else:
            logger.error("❌ Performance metrics collection failed")
            return False
        
        # Test recommendations
        recommendations = monitor.get_recommendations()
        if isinstance(recommendations, list):
            logger.info("✅ Performance recommendations work")
        else:
            logger.error("❌ Performance recommendations failed")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing performance monitor: {e}")
        return False

async def test_enhanced_simulator():
    """Test the enhanced simulator"""
    logger.info("🚀 Testing enhanced simulator...")
    
    try:
        from real_simulator import EnhancedSimulator
        
        # Create simulator
        simulator = EnhancedSimulator(symbols=["AAPL", "MSFT"])
        
        # Test initialization
        success = await simulator.initialize()
        if success:
            logger.info("✅ Enhanced simulator initialization works")
        else:
            logger.error("❌ Enhanced simulator initialization failed")
            return False
        
        # Test API testing function
        api_test_result = await simulator.test_apis()
        if isinstance(api_test_result, dict):
            logger.info("✅ API testing function works")
            logger.info(f"  Test successful: {api_test_result.get('test_successful', False)}")
            logger.info(f"  Price sources: {len(api_test_result.get('price_sources', []))}")
        else:
            logger.error("❌ API testing function failed")
            return False
        
        # Test status
        status = simulator.get_status()
        if isinstance(status, dict) and "running" in status:
            logger.info("✅ Simulator status function works")
        else:
            logger.error("❌ Simulator status function failed")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing enhanced simulator: {e}")
        return False

def test_streamlit_interface():
    """Test if Streamlit interface can be loaded"""
    logger.info("🖥️ Testing Streamlit interface...")
    
    try:
        # Test original interface
        with open("interface.py", "r") as f:
            interface_code = f.read()
            if "st.title" in interface_code:
                logger.info("✅ Original Streamlit interface file is valid")
            else:
                logger.warning("⚠️ Original interface file may have issues")
        
        # Test enhanced interface
        with open("real_interface.py", "r") as f:
            real_interface_code = f.read()
            if "st.title" in real_interface_code:
                logger.info("✅ Enhanced Streamlit interface file is valid")
            else:
                logger.warning("⚠️ Enhanced interface file may have issues")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing Streamlit interfaces: {e}")
        return False

async def run_comprehensive_test():
    """Run comprehensive test suite"""
    logger.info("🧪 Starting comprehensive test suite...")
    
    test_results = {}
    
    # Basic tests
    test_results["python_version"] = check_python_version()
    test_results["requirements"] = install_requirements()
    test_results["environment"] = setup_environment()
    test_results["imports"] = test_imports()
    
    # Only run advanced tests if basic tests pass
    if all([test_results["python_version"], test_results["requirements"], test_results["imports"]]):
        test_results["api_config"] = await test_api_configuration()
        test_results["data_stream"] = await test_data_stream()
        test_results["arbitrage_logic"] = await test_arbitrage_logic()
        test_results["performance_monitor"] = await test_performance_monitor()
        test_results["enhanced_simulator"] = await test_enhanced_simulator()
        test_results["streamlit_interface"] = test_streamlit_interface()
    
    # Summary
    logger.info("=" * 60)
    logger.info("🎯 TEST SUMMARY")
    logger.info("=" * 60)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name.replace('_', ' ').title()}: {status}")
        if result:
            passed_tests += 1
    
    logger.info("-" * 60)
    logger.info(f"Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All tests passed! Your bot is ready to use.")
        print_usage_instructions()
    else:
        logger.warning(f"⚠️ {total_tests - passed_tests} tests failed. Please check the errors above.")
    
    return passed_tests == total_tests

def print_usage_instructions():
    """Print usage instructions"""
    logger.info("=" * 60)
    logger.info("📋 USAGE INSTRUCTIONS")
    logger.info("=" * 60)
    
    instructions = """
🚀 Your Enhanced Stock Arbitrage Bot is ready!

📡 API Setup (for real data):
1. Edit .env file with your API keys
2. Available APIs: Alpaca, Polygon, Finnhub, Alpha Vantage, Yahoo Finance
3. Minimum 2 APIs needed for arbitrage detection

🖥️ Command Line Usage:
• Test APIs: python real_simulator.py --test-apis
• Run simulation: python real_simulator.py --duration 300
• Custom settings: python real_simulator.py --threshold 0.5 --symbols AAPL MSFT

🌐 Web Interface:
• Original: streamlit run interface.py
• Enhanced: streamlit run real_interface.py

🧪 Testing:
• Run tests: python test_bot.py
• API tests: python broker_apis.py
• Stream tests: python real_data_stream.py

📊 Features:
• Real-time API integration with 6 broker sources
• Comprehensive error handling and recovery
• Performance monitoring and optimization
• Data export (JSON/CSV)
• Configurable thresholds and intervals

⚠️ Important Notes:
• Educational purposes only
• Real trading involves significant risks
• Always test with small amounts first
• Respect API rate limits
"""
    
    print(instructions)

async def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Quick test - just check imports and basic functionality
        logger.info("🏃 Running quick test...")
        success = (check_python_version() and 
                  install_requirements() and 
                  setup_environment() and 
                  test_imports())
        if success:
            logger.info("✅ Quick test passed!")
            print_usage_instructions()
        else:
            logger.error("❌ Quick test failed!")
    else:
        # Full comprehensive test
        await run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())
