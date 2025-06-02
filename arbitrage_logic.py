"""
arbitrage_logic.py
Contains logic to detect arbitrage opportunities with comprehensive error handling.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_price_data(prices: Dict[str, float], source_name: str) -> bool:
    """
    Validate price data for common issues.
    
    Args:
        prices: Dictionary of ticker -> price
        source_name: Name of the price source for error messages
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        if not isinstance(prices, dict):
            logger.error(f"Invalid price data type for {source_name}: expected dict, got {type(prices)}")
            return False
            
        if not prices:
            logger.warning(f"Empty price data for {source_name}")
            return False
            
        for ticker, price in prices.items():
            if not isinstance(ticker, str):
                logger.error(f"Invalid ticker type in {source_name}: {type(ticker)}")
                return False
                
            if not isinstance(price, (int, float)):
                logger.error(f"Invalid price type for {ticker} in {source_name}: {type(price)}")
                return False
                
            if price <= 0:
                logger.error(f"Invalid price value for {ticker} in {source_name}: {price}")
                return False
                
        return True
        
    except Exception as e:
        logger.error(f"Validation error for {source_name}: {e}")
        return False

def detect_arbitrage(
    prices1: Dict[str, float], 
    prices2: Dict[str, float], 
    threshold: float = 0.005
) -> List[Dict[str, Any]]:
    """
    Detect arbitrage opportunities between two price sources for each stock.
    
    Args:
        prices1: Price data from first source
        prices2: Price data from second source  
        threshold: Minimum percentage difference to trigger arbitrage (default: 0.5%)
    
    Returns:
        List of arbitrage opportunity dictionaries
    """
    opportunities = []
    
    try:
        # Validate inputs
        if not validate_price_data(prices1, "Source 1"):
            logger.error("Invalid price data from source 1")
            return opportunities
            
        if not validate_price_data(prices2, "Source 2"):
            logger.error("Invalid price data from source 2")
            return opportunities
            
        if not isinstance(threshold, (int, float)) or threshold <= 0:
            logger.error(f"Invalid threshold value: {threshold}")
            return opportunities
            
        # Find common tickers
        common_tickers = set(prices1.keys()) & set(prices2.keys())
        
        if not common_tickers:
            logger.warning("No common tickers found between price sources")
            return opportunities
            
        logger.info(f"Checking {len(common_tickers)} common tickers for arbitrage")
        
        # Check each common ticker for arbitrage opportunities
        for ticker in common_tickers:
            try:
                p1, p2 = prices1[ticker], prices2[ticker]
                
                # Calculate price difference and percentage
                diff = abs(p1 - p2)
                avg = (p1 + p2) / 2
                
                # Avoid division by zero
                if avg == 0:
                    logger.warning(f"Average price is zero for {ticker}")
                    continue
                    
                diff_pct = diff / avg
                
                # Check if opportunity exceeds threshold
                if diff_pct > threshold:
                    # Determine buy/sell sides
                    buy_source = "Source 1" if p1 < p2 else "Source 2"
                    sell_source = "Source 2" if p1 < p2 else "Source 1"
                    buy_price = min(p1, p2)
                    sell_price = max(p1, p2)
                    
                    opportunity = {
                        "timestamp": datetime.now().isoformat(),
                        "ticker": ticker,
                        "price_source_1": round(p1, 4),
                        "price_source_2": round(p2, 4),
                        "difference_abs": round(diff, 4),
                        "difference_pct": round(diff_pct * 100, 4),
                        "estimated_profit": round(diff, 4),
                        "buy_source": buy_source,
                        "sell_source": sell_source,
                        "buy_price": round(buy_price, 4),
                        "sell_price": round(sell_price, 4),
                        "profit_margin": round((sell_price - buy_price) / buy_price * 100, 4)
                    }
                    
                    opportunities.append(opportunity)
                    logger.info(f"Arbitrage opportunity found for {ticker}: {diff_pct*100:.2f}% difference")
                    
            except Exception as e:
                logger.error(f"Error processing ticker {ticker}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Critical error in arbitrage detection: {e}")
        
    logger.info(f"Found {len(opportunities)} arbitrage opportunities")
    return opportunities

def calculate_portfolio_metrics(opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate portfolio-level metrics from arbitrage opportunities.
    
    Args:
        opportunities: List of arbitrage opportunity dictionaries
    
    Returns:
        Dictionary containing portfolio metrics
    """
    try:
        if not opportunities:
            return {
                "total_opportunities": 0,
                "total_estimated_profit": 0.0,
                "average_profit_margin": 0.0,
                "max_profit_opportunity": None,
                "most_active_ticker": None
            }
            
        total_profit = sum(opp.get("estimated_profit", 0) for opp in opportunities)
        profit_margins = [opp.get("profit_margin", 0) for opp in opportunities if opp.get("profit_margin")]
        avg_profit_margin = sum(profit_margins) / len(profit_margins) if profit_margins else 0
        
        # Find max profit opportunity
        max_profit_opp = max(opportunities, key=lambda x: x.get("estimated_profit", 0))
        
        # Find most active ticker
        ticker_counts = {}
        for opp in opportunities:
            ticker = opp.get("ticker")
            if ticker:
                ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
        
        most_active_ticker = max(ticker_counts.items(), key=lambda x: x[1]) if ticker_counts else None
        
        return {
            "total_opportunities": len(opportunities),
            "total_estimated_profit": round(total_profit, 4),
            "average_profit_margin": round(avg_profit_margin, 4),
            "max_profit_opportunity": max_profit_opp,
            "most_active_ticker": most_active_ticker[0] if most_active_ticker else None,
            "most_active_ticker_count": most_active_ticker[1] if most_active_ticker else 0
        }
        
    except Exception as e:
        logger.error(f"Error calculating portfolio metrics: {e}")
        return {"error": str(e)}
