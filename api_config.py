"""
api_config.py
Configuration for real broker API integrations
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class BrokerType(Enum):
    """Supported broker types"""
    ALPACA = "alpaca"
    POLYGON = "polygon"
    FINNHUB = "finnhub"
    ALPHA_VANTAGE = "alpha_vantage"
    YAHOO_FINANCE = "yahoo_finance"
    IEX_CLOUD = "iex_cloud"

@dataclass
class BrokerConfig:
    """Configuration for a single broker"""
    name: str
    broker_type: BrokerType
    api_key: str
    secret_key: Optional[str] = None
    base_url: str = ""
    rate_limit_per_minute: int = 200
    enabled: bool = True
    timeout_seconds: int = 30

class APIConfig:
    """Main API configuration class"""
    
    # Environment variable names for API keys
    ENV_VARS = {
        BrokerType.ALPACA: {
            "api_key": "ALPACA_API_KEY",
            "secret_key": "ALPACA_SECRET_KEY",
            "base_url": "ALPACA_BASE_URL"
        },
        BrokerType.POLYGON: {
            "api_key": "POLYGON_API_KEY",
            "base_url": "POLYGON_BASE_URL"
        },
        BrokerType.FINNHUB: {
            "api_key": "FINNHUB_API_KEY",
            "base_url": "FINNHUB_BASE_URL"
        },
        BrokerType.ALPHA_VANTAGE: {
            "api_key": "ALPHA_VANTAGE_API_KEY",
            "base_url": "ALPHA_VANTAGE_BASE_URL"
        },
        BrokerType.IEX_CLOUD: {
            "api_key": "IEX_CLOUD_API_KEY",
            "base_url": "IEX_CLOUD_BASE_URL"
        }
    }
    
    # Default base URLs
    DEFAULT_URLS = {
        BrokerType.ALPACA: "https://paper-api.alpaca.markets",  # Paper trading by default
        BrokerType.POLYGON: "https://api.polygon.io",
        BrokerType.FINNHUB: "https://finnhub.io/api/v1",
        BrokerType.ALPHA_VANTAGE: "https://www.alphavantage.co/query",
        BrokerType.YAHOO_FINANCE: "https://query1.finance.yahoo.com",  # No API key needed
        BrokerType.IEX_CLOUD: "https://cloud.iexapis.com/stable"
    }
    
    # Rate limits per broker (requests per minute)
    RATE_LIMITS = {
        BrokerType.ALPACA: 200,
        BrokerType.POLYGON: 5,  # Free tier
        BrokerType.FINNHUB: 60,
        BrokerType.ALPHA_VANTAGE: 5,  # Free tier
        BrokerType.YAHOO_FINANCE: 2000,  # Unofficial limit
        BrokerType.IEX_CLOUD: 100
    }
    
    @classmethod
    def create_broker_config(cls, broker_type: BrokerType, custom_name: str = None) -> Optional[BrokerConfig]:
        """Create broker configuration from environment variables"""
        try:
            env_vars = cls.ENV_VARS.get(broker_type, {})
            
            # Get API key
            api_key = os.getenv(env_vars.get("api_key", ""))
            
            # Yahoo Finance doesn't need API key
            if broker_type == BrokerType.YAHOO_FINANCE:
                api_key = "no_key_needed"
            elif not api_key:
                return None
            
            # Get optional secret key
            secret_key = os.getenv(env_vars.get("secret_key", ""))
            
            # Get base URL
            base_url = os.getenv(
                env_vars.get("base_url", ""),
                cls.DEFAULT_URLS.get(broker_type, "")
            )
            
            return BrokerConfig(
                name=custom_name or broker_type.value,
                broker_type=broker_type,
                api_key=api_key,
                secret_key=secret_key if secret_key else None,
                base_url=base_url,
                rate_limit_per_minute=cls.RATE_LIMITS.get(broker_type, 100),
                enabled=True
            )
            
        except Exception as e:
            print(f"Error creating broker config for {broker_type}: {e}")
            return None
    
    @classmethod
    def get_all_configured_brokers(cls) -> Dict[str, BrokerConfig]:
        """Get all properly configured brokers"""
        brokers = {}
        
        for broker_type in BrokerType:
            config = cls.create_broker_config(broker_type)
            if config:
                brokers[config.name] = config
        
        return brokers
    
    @classmethod
    def validate_configuration(cls) -> Dict[str, Any]:
        """Validate API configuration"""
        validation_result = {
            "valid": False,
            "configured_brokers": [],
            "missing_configs": [],
            "errors": []
        }
        
        try:
            brokers = cls.get_all_configured_brokers()
            
            if brokers:
                validation_result["valid"] = True
                validation_result["configured_brokers"] = list(brokers.keys())
            else:
                validation_result["errors"].append("No brokers configured with valid API keys")
            
            # Check for missing configurations
            for broker_type in BrokerType:
                if broker_type == BrokerType.YAHOO_FINANCE:
                    continue  # Skip Yahoo as it doesn't need API key
                    
                env_vars = cls.ENV_VARS.get(broker_type, {})
                api_key_var = env_vars.get("api_key", "")
                
                if not os.getenv(api_key_var):
                    validation_result["missing_configs"].append(
                        f"{broker_type.value}: Missing {api_key_var}"
                    )
            
        except Exception as e:
            validation_result["errors"].append(f"Configuration validation error: {e}")
        
        return validation_result

# Default configuration for testing
TEST_CONFIG = {
    "simulation_mode": True,
    "primary_broker": "yahoo_finance",
    "secondary_broker": "simulation",
    "fallback_to_simulation": True
}

def load_api_config() -> Dict[str, Any]:
    """Load API configuration with fallbacks"""
    # Try to load real broker configurations
    brokers = APIConfig.get_all_configured_brokers()
    
    config = {
        "brokers": brokers,
        "simulation_mode": len(brokers) < 2,  # Need at least 2 brokers for arbitrage
        "validation": APIConfig.validate_configuration()
    }
    
    # If we don't have enough real brokers, enable simulation mode
    if len(brokers) < 2:
        config.update(TEST_CONFIG)
    
    return config

def create_env_template() -> str:
    """Create a template .env file for API configuration"""
    template = """# Stock Arbitrage Bot - API Configuration
# Copy this file to .env and add your actual API keys

# Alpaca Trading API (Paper Trading)
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Polygon.io (Stock Market Data)
POLYGON_API_KEY=your_polygon_api_key_here

# Finnhub (Financial Data)
FINNHUB_API_KEY=your_finnhub_api_key_here

# Alpha Vantage (Financial Data)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here

# IEX Cloud (Financial Data)
IEX_CLOUD_API_KEY=your_iex_cloud_api_key_here

# Configuration Options:
# - Set SIMULATION_MODE=true to use simulated data
# - Set LOG_LEVEL=DEBUG for verbose logging
# - Set MAX_REQUESTS_PER_MINUTE=100 to limit API calls

SIMULATION_MODE=false
LOG_LEVEL=INFO
MAX_REQUESTS_PER_MINUTE=100
"""
    return template

if __name__ == "__main__":
    # Test configuration
    config = load_api_config()
    print("API Configuration Test:")
    print(f"Simulation Mode: {config['simulation_mode']}")
    print(f"Configured Brokers: {list(config['brokers'].keys())}")
    print(f"Validation: {config['validation']}")
    
    # Create .env template
    env_template = create_env_template()
    print("\n.env Template:")
    print(env_template)
