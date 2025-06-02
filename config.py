"""
config.py
Configuration settings for the Stock Arbitrage Bot
"""

from typing import List, Dict, Any
import os

class Config:
    """Configuration class for the arbitrage bot"""
    
    # Stock symbols to track
    STOCKS: List[str] = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN"]
    
    # Trading parameters
    DEFAULT_THRESHOLD: float = 0.005  # 0.5% minimum difference for arbitrage
    MIN_THRESHOLD: float = 0.001      # 0.1% minimum allowed threshold
    MAX_THRESHOLD: float = 0.1        # 10% maximum allowed threshold
    
    # Price simulation parameters
    PRICE_UPDATE_INTERVAL: float = 1.0  # seconds between price updates
    MAX_PRICE_CHANGE: float = 2.0       # maximum price change per tick
    MIN_STOCK_PRICE: float = 1.0        # minimum allowed stock price
    INITIAL_PRICE_MIN: float = 50.0     # minimum initial stock price
    INITIAL_PRICE_MAX: float = 500.0    # maximum initial stock price
    
    # Data management
    MAX_OPPORTUNITIES_IN_MEMORY: int = 1000   # max opportunities to keep in memory
    MAX_OPPORTUNITIES_IN_FILE: int = 10000    # max opportunities to keep in file
    MAX_DEBUG_ENTRIES: int = 50               # max debug log entries to keep
    
    # File paths
    LOGS_DIR: str = "logs"
    OPPORTUNITY_LOG: str = os.path.join(LOGS_DIR, "opportunities.json")
    ERROR_LOG: str = os.path.join(LOGS_DIR, "errors.log")
    CONFIG_LOG: str = os.path.join(LOGS_DIR, "config.log")
    
    # Streamlit configuration
    STREAMLIT_PAGE_TITLE: str = "Stock Arbitrage Bot"
    STREAMLIT_LAYOUT: str = "wide"
    STREAMLIT_REFRESH_INTERVAL: float = 0.5  # seconds between UI refreshes
    
    # Broker simulation settings
    BROKER_NAMES: List[str] = ["BrokerA", "BrokerB"]
    PRICE_VARIANCE_FACTOR: float = 0.02  # how much prices can vary between brokers
    
    # Risk management
    MAX_SIMULATION_ERRORS: int = 100  # max errors before stopping simulation
    ERROR_RECOVERY_DELAY: float = 0.1  # seconds to wait after error
    
    # Performance settings
    ASYNC_TIMEOUT: float = 30.0  # timeout for async operations
    FILE_BACKUP_ENABLED: bool = True  # create backups of important files
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate configuration settings and return validation results"""
        validation_results = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        try:
            # Validate thresholds
            if not (cls.MIN_THRESHOLD <= cls.DEFAULT_THRESHOLD <= cls.MAX_THRESHOLD):
                validation_results["errors"].append(
                    f"Threshold values invalid: MIN({cls.MIN_THRESHOLD}) <= DEFAULT({cls.DEFAULT_THRESHOLD}) <= MAX({cls.MAX_THRESHOLD})"
                )
                validation_results["valid"] = False
            
            # Validate price ranges
            if cls.INITIAL_PRICE_MIN >= cls.INITIAL_PRICE_MAX:
                validation_results["errors"].append(
                    f"Invalid price range: MIN({cls.INITIAL_PRICE_MIN}) >= MAX({cls.INITIAL_PRICE_MAX})"
                )
                validation_results["valid"] = False
            
            # Validate stocks list
            if not cls.STOCKS or len(cls.STOCKS) == 0:
                validation_results["errors"].append("STOCKS list cannot be empty")
                validation_results["valid"] = False
            
            # Check for duplicate stocks
            if len(cls.STOCKS) != len(set(cls.STOCKS)):
                validation_results["warnings"].append("Duplicate stocks found in STOCKS list")
            
            # Validate broker names
            if len(cls.BROKER_NAMES) != 2:
                validation_results["errors"].append("Exactly 2 broker names required")
                validation_results["valid"] = False
            
            # Validate memory limits
            if cls.MAX_OPPORTUNITIES_IN_MEMORY > cls.MAX_OPPORTUNITIES_IN_FILE:
                validation_results["warnings"].append(
                    "MAX_OPPORTUNITIES_IN_MEMORY > MAX_OPPORTUNITIES_IN_FILE may cause data loss"
                )
            
            # Check directory paths
            try:
                os.makedirs(cls.LOGS_DIR, exist_ok=True)
            except Exception as e:
                validation_results["errors"].append(f"Cannot create logs directory: {e}")
                validation_results["valid"] = False
            
        except Exception as e:
            validation_results["errors"].append(f"Configuration validation failed: {e}")
            validation_results["valid"] = False
        
        return validation_results
    
    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        return {
            "stocks_count": len(cls.STOCKS),
            "stocks": cls.STOCKS,
            "default_threshold_pct": cls.DEFAULT_THRESHOLD * 100,
            "update_interval_sec": cls.PRICE_UPDATE_INTERVAL,
            "max_opportunities": cls.MAX_OPPORTUNITIES_IN_MEMORY,
            "brokers": cls.BROKER_NAMES,
            "logs_directory": cls.LOGS_DIR
        }

# Environment-specific configurations
class DevelopmentConfig(Config):
    """Development environment configuration"""
    PRICE_UPDATE_INTERVAL = 0.5  # faster updates for development
    MAX_DEBUG_ENTRIES = 100      # more debug info
    STREAMLIT_REFRESH_INTERVAL = 0.3

class ProductionConfig(Config):
    """Production environment configuration"""
    PRICE_UPDATE_INTERVAL = 2.0  # slower updates for stability
    MAX_DEBUG_ENTRIES = 25       # less debug info
    STREAMLIT_REFRESH_INTERVAL = 1.0
    ERROR_RECOVERY_DELAY = 0.5   # longer recovery time

class TestingConfig(Config):
    """Testing environment configuration"""
    STOCKS = ["TEST1", "TEST2"]  # test stocks only
    PRICE_UPDATE_INTERVAL = 0.1  # very fast for testing
    MAX_OPPORTUNITIES_IN_MEMORY = 10
    MAX_OPPORTUNITIES_IN_FILE = 50
    LOGS_DIR = "test_logs"

# Default configuration
DEFAULT_CONFIG = Config

def get_config(environment: str = "default") -> Config:
    """Get configuration for specified environment"""
    configs = {
        "default": Config,
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig
    }
    
    return configs.get(environment.lower(), Config)

def validate_environment_config(environment: str = "default") -> Dict[str, Any]:
    """Validate configuration for specified environment"""
    config_class = get_config(environment)
    return config_class.validate_config()
