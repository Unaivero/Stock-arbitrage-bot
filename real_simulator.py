"""
real_simulator.py
Enhanced simulator with real API integration and comprehensive monitoring
"""

import asyncio
import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from real_data_stream import RealDataStream, merged_price_stream_real
from arbitrage_logic import detect_arbitrage, calculate_portfolio_metrics
from performance_monitor import performance_monitor, monitor_performance
from config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ensure_logs_directory():
    """Ensure the logs directory exists"""
    try:
        os.makedirs("logs", exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create logs directory: {e}")
        return False

class EnhancedSimulator:
    """Enhanced simulator with real API integration"""
    
    def __init__(self, threshold: float = None, symbols: List[str] = None):
        """
        Initialize the enhanced simulator
        
        Args:
            threshold: Arbitrage detection threshold (uses config default if None)
            symbols: List of symbols to track (uses config default if None)
        """
        try:
            self.threshold = threshold or Config.DEFAULT_THRESHOLD
            self.symbols = symbols or Config.STOCKS
            self.running = False
            self.data_stream = RealDataStream()
            
            # State tracking
            self.latest_prices = {}
            self.opportunities = []
            self.error_count = 0
            self.start_time = None
            self.total_profit = 0.0
            
            # Performance tracking
            self.iteration_count = 0
            self.last_status_update = datetime.now()
            
            # Ensure logs directory exists
            if not ensure_logs_directory():
                logger.warning("Could not create logs directory - file logging may fail")
            
            logger.info(f"Enhanced simulator initialized:")
            logger.info(f"  Symbols: {self.symbols}")
            logger.info(f"  Threshold: {self.threshold * 100:.2f}%")
            
        except Exception as e:
            logger.error(f"Failed to initialize enhanced simulator: {e}")
            raise

    @monitor_performance
    async def initialize(self) -> bool:
        """Initialize the simulator and data sources"""
        try:
            logger.info("Initializing enhanced simulator...")
            
            # Initialize data stream
            success = await self.data_stream.initialize()
            if not success:
                logger.error("Failed to initialize data stream")
                return False
            
            # Log data stream status
            status = self.data_stream.get_status()
            logger.info(f"Data stream status: {status}")
            
            # Reset performance monitor
            performance_monitor.reset_metrics()
            
            return True
            
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            return False

    async def run(
        self, 
        max_duration: Optional[float] = None,
        update_interval: float = 1.0,
        max_errors: int = 100
    ):
        """
        Run the enhanced simulation
        
        Args:
            max_duration: Maximum simulation duration in seconds
            update_interval: Seconds between price updates
            max_errors: Maximum errors before stopping
        """
        try:
            self.running = True
            self.start_time = datetime.now()
            self.error_count = 0
            
            logger.info("Starting enhanced arbitrage simulation...")
            logger.info(f"Max duration: {max_duration}s" if max_duration else "Duration: Unlimited")
            logger.info(f"Update interval: {update_interval}s")
            logger.info(f"Symbols: {', '.join(self.symbols)}")
            
            # Use real data stream
            async for feeds in merged_price_stream_real(
                symbols=self.symbols,
                update_interval=update_interval,
                max_duration=max_duration
            ):
                if not self.running:
                    logger.info("Simulation stopped by user")
                    break
                
                if self.error_count >= max_errors:
                    logger.error(f"Maximum error count ({max_errors}) reached. Stopping simulation.")
                    break
                
                try:
                    await self._process_price_feeds(feeds)
                    self.iteration_count += 1
                    
                    # Periodic status updates
                    if self.iteration_count % 10 == 0:
                        await self._log_status_update()
                    
                    # Check if we should throttle based on performance
                    if performance_monitor.should_throttle():
                        logger.warning("System under stress, adding throttle delay")
                        await asyncio.sleep(1.0)
                    
                except Exception as e:
                    self.error_count += 1
                    performance_monitor.record_error()
                    error_msg = f"Error processing feeds (iteration {self.iteration_count}, error #{self.error_count}): {e}"
                    logger.error(error_msg)
                    
                    # Brief pause before continuing
                    await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Critical error in enhanced simulation: {e}")
        finally:
            await self._cleanup()

    @monitor_performance
    async def _process_price_feeds(self, feeds: List[Dict[str, Any]]):
        """Process price feeds and detect arbitrage opportunities"""
        try:
            if not feeds or len(feeds) < 2:
                raise ValueError(f"Need at least 2 price feeds, got {len(feeds) if feeds else 0}")
            
            source1, source2 = feeds[0], feeds[1]
            
            # Validate feed structure
            if not all("prices" in feed for feed in [source1, source2]):
                raise ValueError("Invalid feed structure: missing 'prices' key")
            
            prices1 = source1["prices"]
            prices2 = source2["prices"]
            
            # Update latest prices
            self.latest_prices = {
                source1.get("source", "Unknown1"): prices1,
                source2.get("source", "Unknown2"): prices2,
                "last_update": datetime.now().isoformat(),
                "iteration": self.iteration_count
            }
            
            # Detect arbitrage opportunities
            opportunities = detect_arbitrage(prices1, prices2, self.threshold)
            
            if opportunities:
                # Record opportunities
                performance_monitor.record_opportunity()
                self.opportunities.extend(opportunities)
                
                # Calculate profit
                profit = sum(opp.get("estimated_profit", 0) for opp in opportunities)
                self.total_profit += profit
                
                # Save opportunities
                await self._save_opportunities(opportunities)
                
                logger.info(f"📈 Found {len(opportunities)} arbitrage opportunities (Total profit: ${profit:.2f})")
                
                # Log details for significant opportunities
                for opp in opportunities:
                    if opp.get("profit_margin", 0) > 1.0:  # > 1% margin
                        logger.info(f"🎯 {opp['ticker']}: {opp['profit_margin']:.2f}% margin, ${opp['estimated_profit']:.2f} profit")
            
        except Exception as e:
            logger.error(f"Error processing price feeds: {e}")
            raise

    async def _save_opportunities(self, opportunities: List[Dict[str, Any]]):
        """Save opportunities to JSON file with enhanced error handling"""
        try:
            if not opportunities:
                return
            
            opportunity_log = "logs/opportunities_real.json"
            
            # Load existing data
            existing_data = []
            if os.path.exists(opportunity_log):
                try:
                    with open(opportunity_log, "r") as f:
                        content = f.read().strip()
                        if content:
                            existing_data = json.loads(content)
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Could not load existing opportunities: {e}")
                    # Create backup of corrupted file
                    backup_file = f"{opportunity_log}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    try:
                        os.rename(opportunity_log, backup_file)
                        logger.info(f"Corrupted file backed up as {backup_file}")
                    except Exception:
                        pass
            
            # Ensure existing_data is a list
            if not isinstance(existing_data, list):
                logger.warning("Existing data is not a list, starting fresh")
                existing_data = []
            
            # Add metadata to opportunities
            for opp in opportunities:
                opp.update({
                    "simulation_type": "real_api",
                    "iteration": self.iteration_count,
                    "runtime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
                })
            
            # Add new opportunities
            existing_data.extend(opportunities)
            
            # Limit total opportunities to prevent file from growing too large
            max_opportunities = Config.MAX_OPPORTUNITIES_IN_FILE
            if len(existing_data) > max_opportunities:
                existing_data = existing_data[-max_opportunities:]
                logger.info(f"Truncated opportunities to last {max_opportunities} entries")
            
            # Save to file with atomic write
            temp_file = f"{opportunity_log}.tmp"
            with open(temp_file, "w") as f:
                json.dump(existing_data, f, indent=2)
            
            # Atomic rename
            os.rename(temp_file, opportunity_log)
            
            logger.debug(f"Saved {len(opportunities)} opportunities to {opportunity_log}")
            
        except Exception as e:
            logger.error(f"Failed to save opportunities: {e}")

    async def _log_status_update(self):
        """Log periodic status updates"""
        try:
            # Get performance metrics
            metrics = performance_monitor.collect_metrics()
            summary = performance_monitor.get_performance_summary()
            recommendations = performance_monitor.get_recommendations()
            
            # Get data stream status
            stream_status = self.data_stream.get_status()
            
            # Calculate portfolio metrics
            portfolio_metrics = calculate_portfolio_metrics(self.opportunities)
            
            runtime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            
            logger.info("=" * 60)
            logger.info(f"📊 STATUS UPDATE - Iteration {self.iteration_count}")
            logger.info(f"⏱️  Runtime: {runtime:.1f}s")
            logger.info(f"💰 Total Opportunities: {len(self.opportunities)}")
            logger.info(f"💵 Total Profit: ${self.total_profit:.2f}")
            logger.info(f"📈 Avg Profit/Opp: ${self.total_profit/max(len(self.opportunities), 1):.2f}")
            logger.info(f"🔄 Update Rate: {summary.get('opportunities_per_second', 0):.3f} opp/sec")
            logger.info(f"🖥️  CPU: {summary.get('current_cpu_percent', 0):.1f}%")
            logger.info(f"💾 Memory: {summary.get('current_memory_mb', 0):.1f}MB")
            logger.info(f"⚡ Processing: {summary.get('average_processing_time_ms', 0):.1f}ms")
            logger.info(f"🌐 APIs Active: {', '.join(stream_status.get('active_apis', []))}")
            logger.info(f"⚠️  Errors: {self.error_count}")
            
            if recommendations and recommendations[0] != "✅ System performing optimally":
                logger.info("💡 Recommendations:")
                for rec in recommendations[:3]:  # Show top 3 recommendations
                    logger.info(f"   {rec}")
            
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error logging status update: {e}")

    async def _cleanup(self):
        """Cleanup and final logging"""
        try:
            self.running = False
            
            # Cleanup data stream
            await self.data_stream.cleanup()
            
            # Log final summary
            await self._log_final_summary()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def _log_final_summary(self):
        """Log final simulation summary"""
        try:
            if self.start_time:
                duration = datetime.now() - self.start_time
                
                # Get final metrics
                portfolio_metrics = calculate_portfolio_metrics(self.opportunities)
                performance_summary = performance_monitor.get_performance_summary()
                
                logger.info("🏁 FINAL SIMULATION SUMMARY")
                logger.info("=" * 50)
                logger.info(f"⏱️  Total Duration: {duration}")
                logger.info(f"🔄 Total Iterations: {self.iteration_count}")
                logger.info(f"💰 Total Opportunities: {len(self.opportunities)}")
                logger.info(f"💵 Total Estimated Profit: ${self.total_profit:.2f}")
                logger.info(f"📈 Average Profit per Opportunity: ${self.total_profit/max(len(self.opportunities), 1):.2f}")
                logger.info(f"⚠️  Total Errors: {self.error_count}")
                logger.info(f"📊 Performance Status: {performance_summary.get('status', 'Unknown')}")
                
                if portfolio_metrics.get("most_active_ticker"):
                    logger.info(f"🎯 Most Active Ticker: {portfolio_metrics['most_active_ticker']} ({portfolio_metrics.get('most_active_ticker_count', 0)} opportunities)")
                
                if portfolio_metrics.get("max_profit_opportunity"):
                    max_opp = portfolio_metrics["max_profit_opportunity"]
                    logger.info(f"💎 Best Opportunity: {max_opp.get('ticker', 'N/A')} - ${max_opp.get('estimated_profit', 0):.2f}")
                
                logger.info("=" * 50)
                
        except Exception as e:
            logger.error(f"Error logging final summary: {e}")

    def stop(self):
        """Stop the simulation"""
        try:
            self.running = False
            logger.info("Enhanced simulation stop requested")
        except Exception as e:
            logger.error(f"Error stopping simulation: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current simulation status"""
        try:
            # Get performance metrics
            perf_summary = performance_monitor.get_performance_summary()
            stream_status = self.data_stream.get_status()
            portfolio_metrics = calculate_portfolio_metrics(self.opportunities)
            
            status = {
                "running": self.running,
                "threshold": self.threshold,
                "symbols": self.symbols,
                "iteration_count": self.iteration_count,
                "opportunities_count": len(self.opportunities),
                "total_profit": self.total_profit,
                "error_count": self.error_count,
                "latest_prices": self.latest_prices.copy(),
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "performance": perf_summary,
                "data_stream": stream_status,
                "portfolio_metrics": portfolio_metrics
            }
            
            if self.start_time:
                status["runtime_seconds"] = (datetime.now() - self.start_time).total_seconds()
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"error": str(e)}

    async def test_apis(self) -> Dict[str, Any]:
        """Test API connections and return results"""
        try:
            logger.info("Testing API connections...")
            
            # Initialize if not already done
            if not hasattr(self, 'data_stream') or not self.data_stream:
                await self.initialize()
            
            # Test getting prices
            test_prices = await self.data_stream.get_real_time_prices(["AAPL", "MSFT"])
            
            status = self.data_stream.get_status()
            
            result = {
                "test_successful": len(test_prices) > 0,
                "price_sources": list(test_prices.keys()),
                "simulation_mode": status.get("simulation_mode", True),
                "active_apis": status.get("active_apis", []),
                "sample_prices": {}
            }
            
            # Add sample prices
            for source, prices in test_prices.items():
                if prices:
                    sample_symbol = list(prices.keys())[0]
                    result["sample_prices"][source] = {
                        "symbol": sample_symbol,
                        "price": prices[sample_symbol]
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Error testing APIs: {e}")
            return {"test_successful": False, "error": str(e)}

# CLI interface for testing
async def main():
    """Main function for CLI testing"""
    import signal
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Stock Arbitrage Bot")
    parser.add_argument("--duration", type=int, help="Max simulation duration in seconds")
    parser.add_argument("--interval", type=float, default=1.0, help="Update interval in seconds")
    parser.add_argument("--threshold", type=float, help="Arbitrage threshold percentage (e.g., 0.5 for 0.5%)")
    parser.add_argument("--symbols", nargs="+", help="Stock symbols to track")
    parser.add_argument("--test-apis", action="store_true", help="Test API connections only")
    
    args = parser.parse_args()
    
    # Convert threshold from percentage if provided
    threshold = args.threshold / 100 if args.threshold else None
    
    # Create simulator
    sim = EnhancedSimulator(
        threshold=threshold,
        symbols=args.symbols
    )
    
    # Test APIs if requested
    if args.test_apis:
        logger.info("Testing API connections...")
        result = await sim.test_apis()
        print("\n" + "="*50)
        print("API TEST RESULTS")
        print("="*50)
        print(f"Test Successful: {result.get('test_successful', False)}")
        print(f"Simulation Mode: {result.get('simulation_mode', True)}")
        print(f"Active APIs: {', '.join(result.get('active_apis', []))}")
        print(f"Price Sources: {', '.join(result.get('price_sources', []))}")
        
        if result.get('sample_prices'):
            print("\nSample Prices:")
            for source, price_info in result['sample_prices'].items():
                print(f"  {source}: {price_info['symbol']} = ${price_info['price']:.2f}")
        
        if result.get('error'):
            print(f"Error: {result['error']}")
        
        print("="*50)
        return
    
    # Set up signal handler for graceful shutdown
    def signal_handler(signum, frame):
        print("\nShutdown signal received...")
        sim.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Initialize simulator
        if not await sim.initialize():
            logger.error("Failed to initialize simulator")
            return
        
        print("\n" + "="*60)
        print("🚀 ENHANCED STOCK ARBITRAGE BOT STARTING")
        print("="*60)
        print(f"📈 Symbols: {', '.join(sim.symbols)}")
        print(f"🎯 Threshold: {sim.threshold*100:.2f}%")
        print(f"⏱️  Update Interval: {args.interval}s")
        print(f"⏰ Max Duration: {args.duration}s" if args.duration else "⏰ Duration: Unlimited")
        print("🛑 Press Ctrl+C to stop gracefully")
        print("="*60)
        
        # Run simulation
        await sim.run(
            max_duration=args.duration,
            update_interval=args.interval
        )
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        print("\n🏁 Enhanced simulation completed.")

if __name__ == "__main__":
    asyncio.run(main())
