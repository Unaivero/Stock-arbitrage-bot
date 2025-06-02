"""
test_bot.py
Unit tests for the Stock Arbitrage Bot
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock
from arbitrage_logic import detect_arbitrage, validate_price_data, calculate_portfolio_metrics
from config import Config, validate_environment_config
from data_stream import PriceSimulator
import tempfile
import os

class TestArbitrageLogic(unittest.TestCase):
    """Test arbitrage detection logic"""
    
    def test_detect_arbitrage_basic(self):
        """Test basic arbitrage detection"""
        prices1 = {"AAPL": 100.0, "TSLA": 200.0}
        prices2 = {"AAPL": 101.0, "TSLA": 199.0}  # 1% difference
        
        opportunities = detect_arbitrage(prices1, prices2, threshold=0.005)
        
        self.assertEqual(len(opportunities), 2)
        self.assertEqual(opportunities[0]["ticker"], "AAPL")
        self.assertEqual(opportunities[1]["ticker"], "TSLA")
    
    def test_detect_arbitrage_no_opportunities(self):
        """Test when no arbitrage opportunities exist"""
        prices1 = {"AAPL": 100.0, "TSLA": 200.0}
        prices2 = {"AAPL": 100.1, "TSLA": 200.1}  # 0.1% difference
        
        opportunities = detect_arbitrage(prices1, prices2, threshold=0.005)
        
        self.assertEqual(len(opportunities), 0)
    
    def test_validate_price_data_valid(self):
        """Test price data validation with valid data"""
        prices = {"AAPL": 100.0, "TSLA": 200.0}
        
        result = validate_price_data(prices, "Test Source")
        
        self.assertTrue(result)
    
    def test_validate_price_data_invalid(self):
        """Test price data validation with invalid data"""
        # Test with negative price
        prices = {"AAPL": -100.0}
        
        result = validate_price_data(prices, "Test Source")
        
        self.assertFalse(result)
    
    def test_calculate_portfolio_metrics(self):
        """Test portfolio metrics calculation"""
        opportunities = [
            {"estimated_profit": 1.0, "profit_margin": 0.5, "ticker": "AAPL"},
            {"estimated_profit": 2.0, "profit_margin": 1.0, "ticker": "AAPL"},
            {"estimated_profit": 1.5, "profit_margin": 0.75, "ticker": "TSLA"}
        ]
        
        metrics = calculate_portfolio_metrics(opportunities)
        
        self.assertEqual(metrics["total_opportunities"], 3)
        self.assertEqual(metrics["total_estimated_profit"], 4.5)
        self.assertEqual(metrics["most_active_ticker"], "AAPL")

class TestConfig(unittest.TestCase):
    """Test configuration management"""
    
    def test_config_validation(self):
        """Test configuration validation"""
        result = Config.validate_config()
        
        self.assertIn("valid", result)
        self.assertIn("warnings", result)
        self.assertIn("errors", result)
    
    def test_environment_configs(self):
        """Test different environment configurations"""
        dev_result = validate_environment_config("development")
        prod_result = validate_environment_config("production")
        test_result = validate_environment_config("testing")
        
        self.assertTrue(dev_result["valid"])
        self.assertTrue(prod_result["valid"])
        self.assertTrue(test_result["valid"])

class TestPriceSimulator(unittest.TestCase):
    """Test price simulation"""
    
    def setUp(self):
        """Set up test environment"""
        self.simulator = PriceSimulator()
    
    def test_price_simulator_initialization(self):
        """Test price simulator initialization"""
        self.assertIsInstance(self.simulator.initial_prices, dict)
        self.assertEqual(len(self.simulator.initial_prices), len(Config.STOCKS))
    
    def test_price_updates(self):
        """Test price updates"""
        initial_prices = self.simulator.current_prices.copy()
        updated_prices = self.simulator.update_prices("BrokerA")
        
        self.assertEqual(len(updated_prices), len(initial_prices))
        # Prices should be positive
        for price in updated_prices.values():
            self.assertGreater(price, 0)

class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_end_to_end_simulation(self):
        """Test end-to-end simulation flow"""
        simulator = PriceSimulator()
        
        # Generate prices from both brokers
        prices1 = simulator.update_prices("BrokerA")
        prices2 = simulator.update_prices("BrokerB")
        
        # Detect arbitrage
        opportunities = detect_arbitrage(prices1, prices2)
        
        # Calculate metrics
        metrics = calculate_portfolio_metrics(opportunities)
        
        # Verify results structure
        self.assertIsInstance(opportunities, list)
        self.assertIsInstance(metrics, dict)
        self.assertIn("total_opportunities", metrics)

def run_tests():
    """Run all tests"""
    # Create test suite
    test_classes = [
        TestArbitrageLogic,
        TestConfig,
        TestPriceSimulator,
        TestIntegration
    ]
    
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    print(f"\n{'='*50}")
    print(f"Tests {'PASSED' if success else 'FAILED'}")
    print(f"{'='*50}")
