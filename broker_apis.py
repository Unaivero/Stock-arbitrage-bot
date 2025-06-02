"""
broker_apis.py
Real broker API implementations for stock price data
"""

import asyncio
import aiohttp
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from api_config import BrokerConfig, BrokerType

logger = logging.getLogger(__name__)

@dataclass
class PriceData:
    """Standardized price data structure"""
    symbol: str
    price: float
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None
    source: str = ""

class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, max_calls_per_minute: int):
        self.max_calls = max_calls_per_minute
        self.calls = []
    
    async def acquire(self):
        """Acquire permission to make an API call"""
        now = time.time()
        
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls if now - call_time < 60]
        
        # Check if we can make a call
        if len(self.calls) >= self.max_calls:
            # Calculate wait time
            oldest_call = min(self.calls)
            wait_time = 60 - (now - oldest_call)
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
        
        # Record this call
        self.calls.append(now)

class BrokerAPI(ABC):
    """Abstract base class for broker APIs"""
    
    def __init__(self, config: BrokerConfig):
        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit_per_minute)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """Get current price for a symbol"""
        pass
    
    @abstractmethod
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Get current prices for multiple symbols"""
        pass

class AlpacaAPI(BrokerAPI):
    """Alpaca Trading API implementation"""
    
    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """Get current price from Alpaca"""
        try:
            await self.rate_limiter.acquire()
            
            headers = {
                "APCA-API-KEY-ID": self.config.api_key,
                "APCA-API-SECRET-KEY": self.config.secret_key
            }
            
            url = f"{self.config.base_url}/v2/stocks/{symbol}/quotes/latest"
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    quote = data.get("quote", {})
                    
                    # Use mid price (bid + ask) / 2
                    bid = float(quote.get("bid", 0))
                    ask = float(quote.get("ask", 0))
                    price = (bid + ask) / 2 if bid and ask else bid or ask
                    
                    return PriceData(
                        symbol=symbol,
                        price=price,
                        timestamp=datetime.now(),
                        bid=bid,
                        ask=ask,
                        source=self.config.name
                    )
                else:
                    logger.error(f"Alpaca API error for {symbol}: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error getting Alpaca price for {symbol}: {e}")
        
        return None
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Get multiple prices from Alpaca"""
        prices = {}
        
        # Alpaca supports batch requests
        try:
            await self.rate_limiter.acquire()
            
            symbols_str = ",".join(symbols)
            headers = {
                "APCA-API-KEY-ID": self.config.api_key,
                "APCA-API-SECRET-KEY": self.config.secret_key
            }
            
            url = f"{self.config.base_url}/v2/stocks/quotes/latest"
            params = {"symbols": symbols_str}
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    quotes = data.get("quotes", {})
                    
                    for symbol, quote in quotes.items():
                        bid = float(quote.get("bid", 0))
                        ask = float(quote.get("ask", 0))
                        price = (bid + ask) / 2 if bid and ask else bid or ask
                        
                        if price > 0:
                            prices[symbol] = PriceData(
                                symbol=symbol,
                                price=price,
                                timestamp=datetime.now(),
                                bid=bid,
                                ask=ask,
                                source=self.config.name
                            )
                
        except Exception as e:
            logger.error(f"Error getting Alpaca batch prices: {e}")
        
        return prices

class PolygonAPI(BrokerAPI):
    """Polygon.io API implementation"""
    
    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """Get current price from Polygon"""
        try:
            await self.rate_limiter.acquire()
            
            url = f"{self.config.base_url}/v2/last/trade/{symbol}"
            params = {"apikey": self.config.api_key}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", {})
                    
                    price = float(results.get("p", 0))
                    if price > 0:
                        return PriceData(
                            symbol=symbol,
                            price=price,
                            timestamp=datetime.now(),
                            source=self.config.name
                        )
                        
        except Exception as e:
            logger.error(f"Error getting Polygon price for {symbol}: {e}")
        
        return None
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Get multiple prices from Polygon (sequential calls due to rate limits)"""
        prices = {}
        
        for symbol in symbols:
            price_data = await self.get_price(symbol)
            if price_data:
                prices[symbol] = price_data
            
            # Small delay between calls for free tier
            await asyncio.sleep(0.1)
        
        return prices

class FinnhubAPI(BrokerAPI):
    """Finnhub API implementation"""
    
    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """Get current price from Finnhub"""
        try:
            await self.rate_limiter.acquire()
            
            url = f"{self.config.base_url}/quote"
            params = {
                "symbol": symbol,
                "token": self.config.api_key
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    price = float(data.get("c", 0))  # Current price
                    if price > 0:
                        return PriceData(
                            symbol=symbol,
                            price=price,
                            timestamp=datetime.now(),
                            source=self.config.name
                        )
                        
        except Exception as e:
            logger.error(f"Error getting Finnhub price for {symbol}: {e}")
        
        return None
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Get multiple prices from Finnhub"""
        prices = {}
        
        for symbol in symbols:
            price_data = await self.get_price(symbol)
            if price_data:
                prices[symbol] = price_data
            
            # Respect rate limits
            await asyncio.sleep(1.1)  # ~60 calls per minute
        
        return prices

class YahooFinanceAPI(BrokerAPI):
    """Yahoo Finance API implementation (free, no key required)"""
    
    async def get_price(self, symbol: str) -> Optional[PriceData]:
        """Get current price from Yahoo Finance"""
        try:
            await self.rate_limiter.acquire()
            
            url = f"{self.config.base_url}/v8/finance/chart/{symbol}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    chart = data.get("chart", {})
                    results = chart.get("result", [])
                    
                    if results:
                        meta = results[0].get("meta", {})
                        price = float(meta.get("regularMarketPrice", 0))
                        
                        if price > 0:
                            return PriceData(
                                symbol=symbol,
                                price=price,
                                timestamp=datetime.now(),
                                source=self.config.name
                            )
                            
        except Exception as e:
            logger.error(f"Error getting Yahoo Finance price for {symbol}: {e}")
        
        return None
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Get multiple prices from Yahoo Finance"""
        prices = {}
        
        # Yahoo Finance supports batch requests
        try:
            await self.rate_limiter.acquire()
            
            symbols_str = ",".join(symbols)
            url = f"{self.config.base_url}/v8/finance/chart/{symbols_str}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    chart = data.get("chart", {})
                    results = chart.get("result", [])
                    
                    for result in results:
                        meta = result.get("meta", {})
                        symbol = meta.get("symbol", "")
                        price = float(meta.get("regularMarketPrice", 0))
                        
                        if symbol and price > 0:
                            prices[symbol] = PriceData(
                                symbol=symbol,
                                price=price,
                                timestamp=datetime.now(),
                                source=self.config.name
                            )
                            
        except Exception as e:
            logger.error(f"Error getting Yahoo Finance batch prices: {e}")
            
            # Fallback to individual calls
            for symbol in symbols:
                price_data = await self.get_price(symbol)
                if price_data:
                    prices[symbol] = price_data
        
        return prices

class APIFactory:
    """Factory for creating broker API instances"""
    
    API_CLASSES = {
        BrokerType.ALPACA: AlpacaAPI,
        BrokerType.POLYGON: PolygonAPI,
        BrokerType.FINNHUB: FinnhubAPI,
        BrokerType.YAHOO_FINANCE: YahooFinanceAPI,
    }
    
    @classmethod
    def create_api(cls, config: BrokerConfig) -> Optional[BrokerAPI]:
        """Create API instance for broker"""
        api_class = cls.API_CLASSES.get(config.broker_type)
        
        if api_class:
            return api_class(config)
        else:
            logger.error(f"Unsupported broker type: {config.broker_type}")
            return None
    
    @classmethod
    def create_all_apis(cls, configs: Dict[str, BrokerConfig]) -> Dict[str, BrokerAPI]:
        """Create all configured APIs"""
        apis = {}
        
        for name, config in configs.items():
            if config.enabled:
                api = cls.create_api(config)
                if api:
                    apis[name] = api
                    logger.info(f"Created API for {name}")
                else:
                    logger.warning(f"Failed to create API for {name}")
        
        return apis

# Usage example and testing
async def test_apis():
    """Test function for broker APIs"""
    from api_config import load_api_config
    
    config = load_api_config()
    apis = APIFactory.create_all_apis(config["brokers"])
    
    test_symbols = ["AAPL", "MSFT"]
    
    for name, api in apis.items():
        logger.info(f"Testing {name} API...")
        
        async with api:
            try:
                # Test single price
                price_data = await api.get_price("AAPL")
                if price_data:
                    logger.info(f"{name}: AAPL = ${price_data.price:.2f}")
                
                # Test multiple prices
                prices = await api.get_multiple_prices(test_symbols)
                logger.info(f"{name}: Got {len(prices)} prices")
                
            except Exception as e:
                logger.error(f"Error testing {name}: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_apis())
