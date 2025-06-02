"""
simulator.py
Orchestrates the simulation, manages state, and saves arbitrage opportunities to JSON.
Enhanced with comprehensive error handling and logging.
"""

import asyncio
import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from data_stream import merged_price_stream
from arbitrage_logic import detect_arbitrage

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OPPORTUNITY_LOG = "logs/opportunities.json"
ERROR_LOG = "logs/errors.log"

def ensure_logs_directory():
    """Ensure the logs directory exists"""
    try:
        os.makedirs("logs", exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create logs directory: {e}")
        return False

class Simulator:
    def __init__(self, threshold: float = 0.005):
        """
        Initialize the simulator with error handling.
        
        Args:
            threshold: Minimum percentage difference for arbitrage detection
        """
        try:
            self.threshold = self._validate_threshold(threshold)
            self.running = False
            self.latest_prices = {}
            self.opportunities = []
            self.error_count = 0
            self.start_time = None
            
            # Ensure logs directory exists
            if not ensure_logs_directory():
                logger.warning("Could not create logs directory - file logging may fail")
                
            logger.info(f"Simulator initialized with threshold: {self.threshold}")
            
        except Exception as e:
            logger.error(f"Failed to initialize simulator: {e}")
            raise

    def _validate_threshold(self, threshold: float) -> float:
        """Validate and return a safe threshold value"""
        try:
            if not isinstance(threshold, (int, float)):
                logger.warning(f"Invalid threshold type: {type(threshold)}, using default 0.005")
                return 0.005
                
            if threshold <= 0 or threshold > 1:
                logger.warning(f"Threshold {threshold} out of range, using default 0.005")
                return 0.005
                
            return float(threshold)
            
        except Exception as e:
            logger.error(f"Error validating threshold: {e}")
            return 0.005

    async def run(self, max_errors: int = 100):
        """
        Run the simulation with error handling and recovery.
        
        Args:
            max_errors: Maximum number of errors before stopping simulation
        """
        try:
            self.running = True
            self.start_time = datetime.now()
            self.error_count = 0
            
            logger.info("Starting arbitrage simulation...")
            
            async for feeds in merged_price_stream():
                if not self.running:
                    logger.info("Simulation stopped by user")
                    break
                    
                if self.error_count >= max_errors:
                    logger.error(f"Maximum error count ({max_errors}) reached. Stopping simulation.")
                    break
                
                try:
                    await self._process_feeds(feeds)
                    
                except Exception as e:
                    self.error_count += 1
                    error_msg = f"Error processing feeds (error #{self.error_count}): {e}"
                    logger.error(error_msg)
                    self._log_error(error_msg)
                    
                    # Brief pause before continuing
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Critical error in simulation: {e}")
            self._log_error(f"Critical simulation error: {e}")
        finally:
            self.running = False
            self._log_simulation_summary()

    async def _process_feeds(self, feeds):
        """Process price feeds and detect arbitrage opportunities"""
        try:
            if not feeds or len(feeds) != 2:
                raise ValueError(f"Invalid feeds data: expected 2 sources, got {len(feeds) if feeds else 0}")
                
            source1, source2 = feeds
            
            # Validate feed structure
            if not all(isinstance(feed, dict) and "prices" in feed for feed in [source1, source2]):
                raise ValueError("Invalid feed structure: missing 'prices' key")
            
            prices1 = source1["prices"]
            prices2 = source2["prices"]
            
            # Update latest prices
            self.latest_prices = {
                source1.get("source", "Unknown1"): prices1,
                source2.get("source", "Unknown2"): prices2,
            }
            
            # Detect arbitrage opportunities
            opps = detect_arbitrage(prices1, prices2, self.threshold)
            
            if opps:
                self.opportunities.extend(opps)
                await self._save_opportunities(opps)
                logger.info(f"Detected {len(opps)} new arbitrage opportunities")
                
        except Exception as e:
            logger.error(f"Error processing feeds: {e}")
            raise

    async def _save_opportunities(self, opps: List[Dict[str, Any]]):
        """Save opportunities to JSON file with error handling"""
        try:
            if not opps:
                return
                
            # Load existing data
            existing_data = []
            if os.path.exists(OPPORTUNITY_LOG):
                try:
                    with open(OPPORTUNITY_LOG, "r") as f:
                        content = f.read().strip()
                        if content:
                            existing_data = json.loads(content)
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Could not load existing opportunities: {e}")
                    # Create backup of corrupted file
                    backup_file = f"{OPPORTUNITY_LOG}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    try:
                        os.rename(OPPORTUNITY_LOG, backup_file)
                        logger.info(f"Corrupted file backed up as {backup_file}")
                    except Exception:
                        pass
            
            # Ensure existing_data is a list
            if not isinstance(existing_data, list):
                logger.warning("Existing data is not a list, starting fresh")
                existing_data = []
            
            # Add new opportunities
            existing_data.extend(opps)
            
            # Limit total opportunities to prevent file from growing too large
            max_opportunities = 10000
            if len(existing_data) > max_opportunities:
                existing_data = existing_data[-max_opportunities:]
                logger.info(f"Truncated opportunities to last {max_opportunities} entries")
            
            # Save to file
            with open(OPPORTUNITY_LOG, "w") as f:
                json.dump(existing_data, f, indent=2)
                
            logger.debug(f"Saved {len(opps)} opportunities to {OPPORTUNITY_LOG}")
            
        except Exception as e:
            logger.error(f"Failed to save opportunities: {e}")
            self._log_error(f"Save error: {e}")

    def _log_error(self, error_msg: str):
        """Log error to file"""
        try:
            with open(ERROR_LOG, "a") as f:
                f.write(f"{datetime.now().isoformat()} - {error_msg}\n")
        except Exception:
            pass  # Don't fail if we can't log errors

    def _log_simulation_summary(self):
        """Log simulation summary"""
        try:
            if self.start_time:
                duration = datetime.now() - self.start_time
                logger.info(f"Simulation summary:")
                logger.info(f"  Duration: {duration}")
                logger.info(f"  Total opportunities: {len(self.opportunities)}")
                logger.info(f"  Error count: {self.error_count}")
        except Exception as e:
            logger.error(f"Error logging summary: {e}")

    def stop(self):
        """Stop the simulation"""
        try:
            self.running = False
            logger.info("Simulation stop requested")
        except Exception as e:
            logger.error(f"Error stopping simulation: {e}")

    def reset(self):
        """Reset simulation state"""
        try:
            self.opportunities = []
            self.latest_prices = {}
            self.error_count = 0
            self.start_time = None
            
            # Optionally archive old log files instead of deleting
            if os.path.exists(OPPORTUNITY_LOG):
                try:
                    archive_name = f"{OPPORTUNITY_LOG}.archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.rename(OPPORTUNITY_LOG, archive_name)
                    logger.info(f"Previous opportunities archived as {archive_name}")
                except Exception as e:
                    logger.warning(f"Could not archive previous opportunities: {e}")
                    try:
                        os.remove(OPPORTUNITY_LOG)
                    except Exception:
                        pass
            
            logger.info("Simulation reset completed")
            
        except Exception as e:
            logger.error(f"Error resetting simulation: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current simulation status"""
        try:
            status = {
                "running": self.running,
                "threshold": self.threshold,
                "opportunities_count": len(self.opportunities),
                "error_count": self.error_count,
                "latest_prices": self.latest_prices.copy(),
                "start_time": self.start_time.isoformat() if self.start_time else None
            }
            
            if self.start_time:
                status["runtime"] = str(datetime.now() - self.start_time)
                
            return status
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"error": str(e)}

# CLI interface for testing
if __name__ == "__main__":
    import signal
    
    sim = Simulator()
    
    def signal_handler(signum, frame):
        print("\nShutdown signal received...")
        sim.stop()
    
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        print("Starting arbitrage simulation (Ctrl+C to stop)...")
        asyncio.run(sim.run())
    except KeyboardInterrupt:
        pass
    finally:
        print("\nSimulation stopped.")
