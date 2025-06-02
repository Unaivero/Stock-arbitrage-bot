"""
real_data_stream.py
Real-time data stream using actual broker APIs with fallback to simulation
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import time

from broker_apis import APIFactory, PriceData, BrokerAPI
from api_config import load_api_config
from data_stream import PriceSimulator  # Fallback simulation
from config import Config

logger = logging.getLogger(__name__)

class RealDataStream:
    """Real-time data stream manager with API integration"""
    
    def __init__(self):
        self.config = load_api_config()
        self.apis: Dict[str, BrokerAPI] = {}
        self.simulation_fallback = PriceSimulator()
        self.last_prices: Dict[str, Dict[str, float]] = {}
        self.error_counts: Dict[str, int] = {}
        self.max_errors_per_broker = 5
        
    async def initialize(self) -> bool:
        """Initialize API connections"""
        try:
            if self.config["simulation_mode"]:
                logger.info("Running in simulation mode - no real APIs will be used")
                return True
            
            # Create API instances
            self.apis = APIFactory.create_all_apis(self.config["brokers"])
            
            if len(self.apis) < 2:
                logger.warning("Less than 2 APIs available, enabling simulation fallback")
                self.config["simulation_mode"] = True
                return True
            
            # Test API connections
            working_apis = await self._test_api_connections()
            
            if len(working_apis) < 2:
                logger.warning("Less than 2 working APIs, enabling simulation fallback")
                self.config["simulation_mode"] = True
                return True
            
            logger.info(f"Successfully initialized {len(working_apis)} APIs")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize data stream: {e}")
            self.config["simulation_mode"] = True
            return True  # Always return True to allow fallback
    
    async def _test_api_connections(self) -> List[str]:
        """Test API connections and return working API names"""
        working_apis = []
        
        for name, api in self.apis.items():
            try:
                async with api:
                    # Test with a simple symbol
                    price_data = await api.get_price("AAPL")
                    if price_data and price_data.price > 0:
                        working_apis.append(name)
                        logger.info(f"API {name} is working (AAPL=${price_data.price:.2f})")
                    else:
                        logger.warning(f"API {name} returned invalid data")
                        
            except Exception as e:
                logger.error(f"API {name} connection failed: {e}")
        
        return working_apis
    
    async def get_real_time_prices(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """Get real-time prices from all available sources"""
        if self.config["simulation_mode"]:
            return await self._get_simulated_prices(symbols)
        
        all_prices = {}
        
        # Get prices from each API
        for name, api in self.apis.items():
            try:
                async with api:
                    prices = await api.get_multiple_prices(symbols)
                    
                    # Convert PriceData to simple dict
                    api_prices = {}
                    for symbol, price_data in prices.items():
                        if price_data and price_data.price > 0:
                            api_prices[symbol] = price_data.price
                    
                    if api_prices:
                        all_prices[name] = api_prices
                        self.last_prices[name] = api_prices
                        self.error_counts[name] = 0  # Reset error count on success
                        logger.debug(f"Got {len(api_prices)} prices from {name}")
                    else:
                        raise Exception("No valid prices returned")
                        
            except Exception as e:
                self.error_counts[name] = self.error_counts.get(name, 0) + 1
                logger.error(f"Error getting prices from {name}: {e}")
                
                # Use last known prices if available
                if name in self.last_prices:
                    all_prices[name] = self.last_prices[name]
                    logger.info(f"Using cached prices for {name}")
                
                # Disable API if too many errors
                if self.error_counts[name] >= self.max_errors_per_broker:
                    logger.error(f"Disabling {name} due to repeated errors")
                    self.apis.pop(name, None)
        
        # If we don't have enough price sources, add simulation
        if len(all_prices) < 2:
            logger.warning("Insufficient real price sources, adding simulation data")
            sim_prices = await self._get_simulated_prices(symbols)
            all_prices.update(sim_prices)
        
        return all_prices
    
    async def _get_simulated_prices(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """Get simulated prices as fallback"""
        try:
            prices1 = self.simulation_fallback.update_prices("BrokerA")
            prices2 = self.simulation_fallback.update_prices("BrokerB")
            
            # Filter to requested symbols
            filtered_prices1 = {k: v for k, v in prices1.items() if k in symbols}
            filtered_prices2 = {k: v for k, v in prices2.items() if k in symbols}
            
            return {
                "SimulatedBrokerA": filtered_prices1,
                "SimulatedBrokerB": filtered_prices2
            }
            
        except Exception as e:
            logger.error(f"Error getting simulated prices: {e}")
            return {}
    
    async def stream_prices(
        self, 
        symbols: List[str], 
        update_interval: float = 1.0
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream real-time prices continuously"""
        
        if not await self.initialize():
            logger.error("Failed to initialize data stream")
            return
        
        iteration = 0
        start_time = time.time()
        
        logger.info(f"Starting real-time price stream for {symbols}")
        
        try:
            while True:
                iteration_start = time.time()
                
                try:
                    # Get current prices
                    all_prices = await self.get_real_time_prices(symbols)
                    
                    # Create standardized output
                    price_feeds = []
                    for source_name, prices in all_prices.items():
                        price_feeds.append({
                            "source": source_name,
                            "prices": prices,
                            "timestamp": datetime.now().isoformat(),
                            "iteration": iteration
                        })
                    
                    # Yield the price update
                    yield {
                        "feeds": price_feeds,
                        "iteration": iteration,
                        "runtime_seconds": time.time() - start_time,
                        "simulation_mode": self.config["simulation_mode"],
                        "active_apis": list(self.apis.keys()),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    iteration += 1
                    
                    # Calculate sleep time to maintain interval
                    processing_time = time.time() - iteration_start
                    sleep_time = max(0.1, update_interval - processing_time)
                    
                    await asyncio.sleep(sleep_time)
                    
                except Exception as e:
                    logger.error(f"Error in price stream iteration {iteration}: {e}")
                    await asyncio.sleep(1.0)  # Brief pause on error
                    
        except asyncio.CancelledError:
            logger.info("Price stream cancelled")
        except Exception as e:
            logger.error(f"Critical error in price stream: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up API connections"""
        try:
            for name, api in self.apis.items():
                if hasattr(api, 'session') and api.session:
                    await api.session.close()
            logger.info("API connections cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the data stream"""
        return {
            "simulation_mode": self.config["simulation_mode"],
            "active_apis": list(self.apis.keys()),
            "error_counts": self.error_counts.copy(),
            "last_update": datetime.now().isoformat(),
            "configured_brokers": list(self.config["brokers"].keys()),
            "validation": self.config["validation"]
        }

# Convenience function for backward compatibility
async def merged_price_stream_real(
    symbols: List[str] = None,
    update_interval: float = 1.0,
    max_duration: Optional[float] = None
) -> AsyncGenerator[List[Dict[str, Any]], None]:
    """
    Real-time price stream with API integration (backward compatible interface)
    
    Args:
        symbols: List of symbols to track (uses Config.STOCKS if None)
        update_interval: Seconds between updates
        max_duration: Maximum duration in seconds (None for infinite)
    
    Yields:
        List containing price data from available sources
    """
    if symbols is None:
        symbols = Config.STOCKS
    
    stream = RealDataStream()
    start_time = time.time()
    
    try:
        async for update in stream.stream_prices(symbols, update_interval):
            # Check duration limit
            if max_duration is not None:
                elapsed = time.time() - start_time
                if elapsed >= max_duration:
                    logger.info(f"Reached maximum duration ({max_duration}s)")
                    break
            
            # Convert to backward compatible format
            feeds = update.get("feeds", [])
            if len(feeds) >= 2:
                yield feeds[:2]  # Return first two sources for arbitrage
            elif feeds:
                # If only one real source, add simulation
                yield feeds + [{
                    "source": "SimulationFallback",
                    "prices": {symbol: 100.0 for symbol in symbols},
                    "timestamp": datetime.now().isoformat(),
                    "iteration": update.get("iteration", 0)
                }]
            
    except Exception as e:
        logger.error(f"Error in merged price stream: {e}")
    finally:
        await stream.cleanup()

# Test function
async def test_real_data_stream():
    """Test the real data stream"""
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    stream = RealDataStream()
    
    logger.info("Testing real data stream...")
    
    # Test initialization
    success = await stream.initialize()
    logger.info(f"Initialization: {'Success' if success else 'Failed'}")
    
    # Test status
    status = stream.get_status()
    logger.info(f"Status: {status}")
    
    # Test price fetching
    prices = await stream.get_real_time_prices(symbols)
    logger.info(f"Price sources: {list(prices.keys())}")
    
    for source, source_prices in prices.items():
        logger.info(f"{source}: {source_prices}")
    
    # Test streaming for a few iterations
    logger.info("Testing price stream...")
    iteration_count = 0
    
    async for update in stream.stream_prices(symbols, update_interval=2.0):
        iteration_count += 1
        logger.info(f"Stream iteration {iteration_count}")
        
        for feed in update["feeds"]:
            source = feed["source"]
            sample_symbol = list(feed["prices"].keys())[0] if feed["prices"] else "N/A"
            sample_price = feed["prices"].get(sample_symbol, 0) if feed["prices"] else 0
            logger.info(f"  {source}: {sample_symbol} = ${sample_price:.2f}")
        
        if iteration_count >= 3:  # Test 3 iterations
            break
    
    await stream.cleanup()
    logger.info("Test completed")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_real_data_stream())
