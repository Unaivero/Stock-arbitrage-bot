"""
interface.py
Real-time Stock Arbitrage Trading Bot with GUARANTEED live updates.
"""

import streamlit as st
import json
import time
import random
import pandas as pd
from typing import Dict, Any
from datetime import datetime

# Import project modules
try:
    from arbitrage_logic import detect_arbitrage
    from config import Config
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

st.set_page_config(page_title="Real-Time Arbitrage Bot", layout="wide")

# Force auto-refresh when running
if 'force_refresh' not in st.session_state:
    st.session_state.force_refresh = 0

# Initialize session state
def initialize_session_state():
    """Initialize session state for real-time simulation"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.sim_status = "stopped"
        st.session_state.paused = False
        st.session_state.tick = 0
        st.session_state.opportunities = []
        st.session_state.total_profit = 0.0
        
        # Initialize with random starting prices
        st.session_state.broker_prices = {
            "BrokerA": {},
            "BrokerB": {}
        }
        
        # Set realistic starting prices for each stock
        for ticker in Config.STOCKS:
            base_price = random.uniform(Config.INITIAL_PRICE_MIN, Config.INITIAL_PRICE_MAX)
            st.session_state.broker_prices["BrokerA"][ticker] = round(base_price, 2)
            # BrokerB starts with slight variance
            variance = random.uniform(-0.01, 0.01)  # 1% variance to start
            st.session_state.broker_prices["BrokerB"][ticker] = round(base_price * (1 + variance), 2)

def update_prices_realtime():
    """Update all stock prices in real-time with realistic movements"""
    for ticker in Config.STOCKS:
        # Update BrokerA prices with realistic movement
        if ticker in st.session_state.broker_prices["BrokerA"]:
            current_price_a = st.session_state.broker_prices["BrokerA"][ticker]
            
            # Random walk with slight trend
            change_pct = random.normalvariate(0, 0.003)  # 0.3% standard deviation
            change_amount = current_price_a * change_pct
            new_price_a = max(Config.MIN_STOCK_PRICE, current_price_a + change_amount)
            st.session_state.broker_prices["BrokerA"][ticker] = round(new_price_a, 2)
            
            # Update BrokerB with different movement + variance for arbitrage
            current_price_b = st.session_state.broker_prices["BrokerB"][ticker]
            change_pct_b = random.normalvariate(0, 0.003)  # Independent movement
            broker_variance = random.uniform(-Config.PRICE_VARIANCE_FACTOR, Config.PRICE_VARIANCE_FACTOR)
            
            change_amount_b = current_price_b * (change_pct_b + broker_variance)
            new_price_b = max(Config.MIN_STOCK_PRICE, current_price_b + change_amount_b)
            st.session_state.broker_prices["BrokerB"][ticker] = round(new_price_b, 2)
    
    # Memory cleanup - prevent unlimited growth
    if st.session_state.tick > 1000 and st.session_state.tick % 100 == 0:
        # Keep only recent opportunities to prevent memory issues
        if len(st.session_state.opportunities) > Config.MAX_OPPORTUNITIES_IN_MEMORY:
            st.session_state.opportunities = st.session_state.opportunities[-Config.MAX_OPPORTUNITIES_IN_MEMORY//2:]

def detect_and_log_arbitrage():
    """Detect arbitrage opportunities and log them"""
    prices_a = st.session_state.broker_prices["BrokerA"]
    prices_b = st.session_state.broker_prices["BrokerB"]
    
    opportunities = detect_arbitrage(prices_a, prices_b, Config.DEFAULT_THRESHOLD)
    
    if opportunities:
        # Add timestamp and tick info
        for opp in opportunities:
            opp['tick'] = st.session_state.tick
        
        st.session_state.opportunities.extend(opportunities)
        
        # Calculate total profit
        new_profit = sum(opp.get('estimated_profit', 0) for opp in opportunities)
        st.session_state.total_profit += new_profit
        
        # Keep only recent opportunities
        if len(st.session_state.opportunities) > Config.MAX_OPPORTUNITIES_IN_MEMORY:
            st.session_state.opportunities = st.session_state.opportunities[-Config.MAX_OPPORTUNITIES_IN_MEMORY:]

def reset_simulation():
    """Reset all simulation data"""
    st.session_state.sim_status = "stopped"
    st.session_state.paused = False
    st.session_state.tick = 0
    st.session_state.opportunities = []
    st.session_state.total_profit = 0.0
    
    # Reset to new random prices
    for ticker in Config.STOCKS:
        base_price = random.uniform(Config.INITIAL_PRICE_MIN, Config.INITIAL_PRICE_MAX)
        st.session_state.broker_prices["BrokerA"][ticker] = round(base_price, 2)
        variance = random.uniform(-0.01, 0.01)
        st.session_state.broker_prices["BrokerB"][ticker] = round(base_price * (1 + variance), 2)

# Initialize everything
initialize_session_state()

# Main interface
st.title("🚀 Real-Time Stock Arbitrage Trading Bot")

# Control buttons
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("▶️ Start Simulation", key="start_btn"):
        st.session_state.paused = False
        st.session_state.sim_status = "running"

with col2:
    if st.button("⏸️ Pause Simulation", key="pause_btn"):
        st.session_state.paused = True
        st.session_state.sim_status = "paused"

with col3:
    if st.button("🔄 Reset Simulation", key="restart_btn"):
        reset_simulation()
        st.success("✅ Simulation reset! Click Start to begin.")

st.markdown("---")

# Simulation execution with guaranteed updates
if st.session_state.sim_status == "running" and not st.session_state.paused:
    # Show running status
    st.success(f"🟢 **LIVE SIMULATION ACTIVE** - Tick #{st.session_state.tick}")
    
    # Update prices and detect arbitrage
    update_prices_realtime()
    detect_and_log_arbitrage()
    st.session_state.tick += 1
    
    # Force refresh using rerun
    time.sleep(1.0)  # 1 second updates for visibility
    st.rerun()
    
elif st.session_state.sim_status == "paused":
    st.warning(f"🟡 **SIMULATION PAUSED** at Tick #{st.session_state.tick}")
else:
    st.info("🔵 **SIMULATION READY** - Click ▶️ Start to begin live trading")

# Real-time price display
st.subheader(f"📈 Live Stock Prices - Tick #{st.session_state.tick}")

if st.session_state.broker_prices["BrokerA"]:
    # Display current prices in columns
    price_col1, price_col2 = st.columns(2)
    
    with price_col1:
        st.write("### 🏢 BrokerA Prices")
        for ticker in Config.STOCKS:
            price = st.session_state.broker_prices["BrokerA"][ticker]
            st.write(f"**{ticker}**: ${price:.2f}")
    
    with price_col2:
        st.write("### 🏢 BrokerB Prices")
        for ticker in Config.STOCKS:
            price = st.session_state.broker_prices["BrokerB"][ticker]
            st.write(f"**{ticker}**: ${price:.2f}")
    
    # Real-time price difference metrics with arbitrage detection
    st.write("### 📊 Live Price Analysis")
    diff_cols = st.columns(len(Config.STOCKS))
    
    current_arbitrage_stocks = []
    
    for i, ticker in enumerate(Config.STOCKS):
        price_a = st.session_state.broker_prices["BrokerA"][ticker]
        price_b = st.session_state.broker_prices["BrokerB"][ticker]
        diff = abs(price_a - price_b)
        avg_price = (price_a + price_b) / 2
        diff_pct = (diff / avg_price) * 100
        
        # Check if this is an arbitrage opportunity
        is_arbitrage = diff_pct > (Config.DEFAULT_THRESHOLD * 100)
        if is_arbitrage:
            current_arbitrage_stocks.append(ticker)
        
        with diff_cols[i]:
            if is_arbitrage:
                st.metric(
                    label=f"🔥 {ticker}",
                    value=f"${diff:.2f}",
                    delta=f"{diff_pct:.2f}%",
                    delta_color="inverse"
                )
            else:
                st.metric(
                    label=ticker,
                    value=f"${diff:.2f}",
                    delta=f"{diff_pct:.2f}%"
                )
    
    # Show current arbitrage status
    if current_arbitrage_stocks:
        st.success(f"🎯 **ARBITRAGE OPPORTUNITY!** Active: {', '.join(current_arbitrage_stocks)}")
    else:
        st.info("🔍 **MONITORING** - No arbitrage opportunities at current prices")

else:
    st.write("⏳ Initializing price data...")

# Live arbitrage opportunities log
st.subheader("💰 Arbitrage Opportunities Log")

if st.session_state.opportunities:
    total_opps = len(st.session_state.opportunities)
    st.success(f"**📊 {total_opps} Opportunities Found | Total Profit: ${st.session_state.total_profit:.2f}**")
    
    # Show recent opportunities in a table
    recent_opps = st.session_state.opportunities[-15:]  # Last 15
    
    if recent_opps:
        # Create formatted dataframe
        df_data = []
        for opp in recent_opps:
            df_data.append({
                'Tick': opp.get('tick', 0),
                'Time': pd.to_datetime(opp['timestamp']).strftime('%H:%M:%S'),
                'Stock': opp['ticker'],
                'Buy From': opp.get('buy_source', 'N/A'),
                'Sell To': opp.get('sell_source', 'N/A'),
                'Buy Price': f"${opp.get('buy_price', 0):.2f}",
                'Sell Price': f"${opp.get('sell_price', 0):.2f}",
                'Profit': f"${opp.get('estimated_profit', 0):.2f}",
                'Margin': f"{opp.get('profit_margin', 0):.2f}%"
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Show chart if enough data
        if len(st.session_state.opportunities) > 10:
            chart_data = pd.DataFrame(st.session_state.opportunities[-50:])
            if 'ticker' in chart_data.columns:
                ticker_counts = chart_data['ticker'].value_counts()
                st.bar_chart(ticker_counts)
else:
    st.info("🔍 **NO OPPORTUNITIES YET** - Start simulation to begin detecting arbitrage!")

# Live statistics dashboard
st.subheader("📊 Live Statistics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("⏱️ Simulation Ticks", st.session_state.tick)

with col2:
    st.metric("🎯 Total Opportunities", len(st.session_state.opportunities))

with col3:
    st.metric("💰 Total Profit", f"${st.session_state.total_profit:.2f}")

with col4:
    if st.session_state.opportunities:
        avg_profit = st.session_state.total_profit / len(st.session_state.opportunities)
        st.metric("📈 Avg Profit/Opp", f"${avg_profit:.2f}")
    else:
        st.metric("📈 Avg Profit/Opp", "$0.00")

# Export functionality
if st.button("⬇️ Export All Data as JSON", key="export_btn"):
    if st.session_state.opportunities:
        export_data = json.dumps(st.session_state.opportunities, indent=2)
        st.download_button(
            label="📥 Download Complete Log",
            data=export_data,
            file_name=f"arbitrage_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            key="download_btn"
        )
    else:
        st.warning("⚠️ No data to export yet!")

# Configuration info
with st.expander("⚙️ System Configuration"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📈 Monitored Stocks:**")
        for stock in Config.STOCKS:
            st.write(f"• {stock}")
    
    with col2:
        st.write("**⚙️ Trading Parameters:**")
        st.write(f"• Arbitrage Threshold: {Config.DEFAULT_THRESHOLD*100:.1f}%")
        st.write(f"• Update Frequency: ~1.0 seconds")
        st.write(f"• Price Variance: ±{Config.PRICE_VARIANCE_FACTOR*100:.1f}%")
        st.write(f"• Max Opportunities Stored: {Config.MAX_OPPORTUNITIES_IN_MEMORY}")

# Status indicator at bottom
if st.session_state.sim_status == "running" and not st.session_state.paused:
    st.info("⚡ **LIVE MODE ACTIVE** - Watch prices and opportunities update automatically!")
