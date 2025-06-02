"""
data_stream.py
Simulates two real-time price feeds for stocks using asyncio with comprehensive error handling.
"""

import asyncio
import random
import logging
from typing import Dict, AsyncGenerator, List, Optional
from datetime import datetime
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriceFeedError(Exception):
    """Custom exception for price feed errors"""
    pass

class PriceSimulator:
    """Enhanced price simulator with error handling and configuration"""
    
    def __init__(self, config: Config = Config):
        """Initialize with configuration"""
        self.config = config
        self.stocks = config.STOCKS
        self.initial_prices = self._generate_initial_prices()
        self.current_prices = self.initial_prices.copy()
        logger.info(f"Price simulator initialized with {len(self.stocks)} stocks")
    
    def _generate_initial_prices(self) -> Dict[str, float]:
        """Generate realistic initial prices for all stocks"""
        try:
            prices = {}
            for ticker in self.stocks:
                price = random.uniform(
                    self.config.INITIAL_PRICE_MIN, 
                    self.config.INITIAL_PRICE_MAX
                )
                prices[ticker] = round(price, 2)
            
            logger.info(f"Generated initial prices: {prices}")
            return prices
            
        except Exception as e:
            logger.error(f"Error generating initial prices: {e}")
            # Fallback to simple prices
            return {ticker: 100.0 for ticker in self.stocks}
    
    def _simulate_price_movement(self, current_price: float) -> float:
        """Simulate realistic price movement for a single stock"""
        try:
            # Use normal distribution for more realistic price movements
            change_pct = random.gauss(0, 0.01)  # 1% standard deviation
            change_amount = current_price * change_pct
            
            # Limit maximum change
            max_change = self.config.MAX_PRICE_CHANGE
            change_amount = max(-max_change, min(max_change, change_amount))
            
            new_price = current_price + change_amount
            
            # Ensure price doesn't go below minimum
            new_price = max(self.config.MIN_STOCK_PRICE, new_price)
            
            return round(new_price, 2)
            
        except Exception as e:
            logger.error(f"Error in price movement simulation: {e}")
            return current_price  # Return unchanged price on error
    
    def update_prices(self, source: str) -> Dict[str, float]:
        """Update all stock prices and return new prices"""
        try:
            updated_prices = {}
            
            for ticker in self.stocks:
                if ticker not in self.current_prices:
                    logger.warning(f"Missing price for {ticker}, using fallback")
                    self.current_prices[ticker] = 100.0
                
                # Add broker-specific variance
                base_price = self.current_prices[ticker]
                
                # Different brokers have slightly different prices
                if source == self.config.BROKER_NAMES[1]:  # Second broker
                    variance = random.uniform(-self.config.PRICE_VARIANCE_FACTOR, 
                                            self.config.PRICE_VARIANCE_FACTOR)
                    base_price *= (1 + variance)
                
                new_price = self._simulate_price_movement(base_price)
                updated_prices[ticker] = new_price
                
                # Update base prices only for primary broker
                if source == self.config.BROKER_NAMES[0]:
                    self.current_prices[ticker] = new_price
            
            return updated_prices
            
        except Exception as e:
            logger.error(f"Error updating prices for {source}: {e}")
            return self.current_prices.copy()

# Global price simulator instance
_price_simulator = PriceSimulator()

async def simulate_price_feed(
    source: str, 
    update_interval: float = None,
    max_iterations: Optional[int] = None
) -> AsyncGenerator[Dict[str, any], None]:
    """
    Simulate a price feed for multiple stocks from a given source.
    
    Args:
        source: Name of the price source/broker
        update_interval: Seconds between updates (uses config default if None)
        max_iterations: Maximum number of iterations (None for infinite)
    
    Yields:
        Dict containing source name and current prices
    """
    if update_interval is None:
        update_interval = Config.PRICE_UPDATE_INTERVAL
    
    iteration_count = 0
    error_count = 0
    max_errors = 10  # Maximum consecutive errors before stopping
    
    logger.info(f"Starting price feed for {source}")
    
    try:
        while True:
            try:
                # Check iteration limit
                if max_iterations is not None and iteration_count >= max_iterations:
                    logger.info(f"Reached maximum iterations ({max_iterations}) for {source}")
                    break
                
                # Update prices
                current_prices = _price_simulator.update_prices(source)
                
                # Add some randomness to update timing
                jitter = random.uniform(-0.1, 0.1)
                actual_interval = max(0.1, update_interval + jitter)
                
                await asyncio.sleep(actual_interval)
                
                # Yield the price update
                yield {
                    "source": source,
                    "prices": current_prices,
                    "timestamp": datetime.now().isoformat(),
                    "iteration": iteration_count
                }
                
                iteration_count += 1
                error_count = 0  # Reset error count on successful iteration
                
            except asyncio.CancelledError:
                logger.info(f"Price feed for {source} was cancelled")
                break
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error in price feed {source} (error #{error_count}): {e}")
                
                if error_count >= max_errors:
                    logger.error(f"Too many errors in {source}, stopping feed")
                    raise PriceFeedError(f"Maximum errors reached for {source}")
                
                # Brief pause before retrying
                await asyncio.sleep(0.5)
                
    except Exception as e:
        logger.error(f"Critical error in price feed {source}: {e}")
        raise
    finally:
        logger.info(f"Price feed for {source} stopped after {iteration_count} iterations")

async def merged_price_stream(
    update_interval: float = None,
    max_duration: Optional[float] = None
) -> AsyncGenerator[List[Dict[str, any]], None]:
    """
    Async generator yielding latest prices from both broker sources.
    
    Args:
        update_interval: Seconds between updates
        max_duration: Maximum duration in seconds (None for infinite)
    
    Yields:
        List containing price data from both brokers
    """
    if update_interval is None:
        update_interval = Config.PRICE_UPDATE_INTERVAL
    
    start_time = datetime.now()
    logger.info("Starting merged price stream")
    
    try:
        # Create price feeds for both brokers
        feed1 = simulate_price_feed(Config.BROKER_NAMES[0], update_interval)
        feed2 = simulate_price_feed(Config.BROKER_NAMES[1], update_interval)
        
        while True:
            try:
                # Check duration limit
                if max_duration is not None:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed >= max_duration:
                        logger.info(f"Reached maximum duration ({max_duration}s)")
                        break
                
                # Get next price update from both feeds with timeout
                try:
                    prices1, prices2 = await asyncio.wait_for(
                        asyncio.gather(feed1.__anext__(), feed2.__anext__()),
                        timeout=Config.ASYNC_TIMEOUT
                    )
                    
                    yield [prices1, prices2]
                    
                except asyncio.TimeoutError:
                    logger.warning("Price feed timeout, retrying...")
                    continue
                    
            except asyncio.CancelledError:
                logger.info("Merged price stream was cancelled")
                break
                
            except StopAsyncIteration:
                logger.info("Price feeds completed")
                break
                
            except Exception as e:
                logger.error(f"Error in merged price stream: {e}")
                # Brief pause before retrying
                await asyncio.sleep(1.0)
                
    except Exception as e:
        logger.error(f"Critical error in merged price stream: {e}")
        raise
    finally:
        logger.info("Merged price stream stopped")

async def test_price_feeds(duration: int = 10):
    """
    Test function to verify price feeds work correctly.
    
    Args:
        duration: Test duration in seconds
    """
    logger.info(f"Testing price feeds for {duration} seconds...")
    
    try:
        feed_count = 0
        async for feeds in merged_price_stream(update_interval=1.0, max_duration=duration):
            feed_count += 1
            logger.info(f"Feed #{feed_count}: {[feed['source'] for feed in feeds]}")
            
            # Log sample prices
            for feed in feeds:
                sample_ticker = list(feed['prices'].keys())[0]
                sample_price = feed['prices'][sample_ticker]
                logger.info(f"  {feed['source']}: {sample_ticker} = ${sample_price}")
        
        logger.info(f"Test completed successfully with {feed_count} feed updates")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

# CLI test interface
if __name__ == "__main__":
    import sys
    
    async def main():
        if len(sys.argv) > 1 and sys.argv[1] == "test":
            await test_price_feeds(10)
        else:
            print("Running continuous price feed simulation (Ctrl+C to stop)...")
            async for feeds in merged_price_stream():
                for feed in feeds:
                    print(f"{feed['source']}: {feed['prices']}")
                await asyncio.sleep(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPrice feed simulation stopped.")
