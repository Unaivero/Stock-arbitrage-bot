"""
real_interface.py
Enhanced Streamlit interface with real API integration
"""

import streamlit as st
import asyncio
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
from typing import Dict, Any

# Import project modules
try:
    from real_simulator import EnhancedSimulator
    from api_config import load_api_config, create_env_template
    from performance_monitor import performance_monitor
    from config import Config
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

st.set_page_config(
    page_title="Enhanced Arbitrage Bot", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #1f77b4;
}
.status-success { color: #28a745; }
.status-warning { color: #ffc107; }
.status-error { color: #dc3545; }
.big-font { font-size: 1.2em; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Initialize session state for async operations
def initialize_session_state():
    """Initialize session state for the enhanced interface"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.simulator = None
        st.session_state.running = False
        st.session_state.api_status = None
        st.session_state.last_update = None
        st.session_state.opportunities_history = []
        st.session_state.performance_history = []

initialize_session_state()

# Sidebar Configuration
st.sidebar.title("🔧 Configuration")

# API Configuration Section
st.sidebar.subheader("📡 API Configuration")

config = load_api_config()
api_validation = config["validation"]

if api_validation["valid"]:
    st.sidebar.success(f"✅ {len(api_validation['configured_brokers'])} APIs configured")
    for broker in api_validation['configured_brokers']:
        st.sidebar.write(f"• {broker}")
else:
    st.sidebar.error("❌ No APIs configured")
    if api_validation['missing_configs']:
        st.sidebar.write("Missing configurations:")
        for missing in api_validation['missing_configs']:
            st.sidebar.write(f"• {missing}")

# Show .env template
with st.sidebar.expander("🔑 API Setup Guide"):
    st.write("Create a `.env` file in your project directory with your API keys:")
    st.code(create_env_template(), language="bash")

# Simulation Parameters
st.sidebar.subheader("⚙️ Simulation Parameters")

symbols = st.sidebar.multiselect(
    "Stock Symbols",
    options=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX"],
    default=Config.STOCKS,
    help="Select stock symbols to monitor for arbitrage"
)

threshold = st.sidebar.slider(
    "Arbitrage Threshold (%)",
    min_value=0.1,
    max_value=5.0,
    value=Config.DEFAULT_THRESHOLD * 100,
    step=0.1,
    help="Minimum price difference percentage to trigger arbitrage detection"
) / 100

update_interval = st.sidebar.slider(
    "Update Interval (seconds)",
    min_value=0.5,
    max_value=10.0,
    value=1.0,
    step=0.5,
    help="How often to fetch new prices"
)

max_duration = st.sidebar.number_input(
    "Max Duration (seconds, 0=unlimited)",
    min_value=0,
    max_value=3600,
    value=0,
    help="Maximum simulation duration (0 for unlimited)"
)

# Main Interface
st.title("🚀 Enhanced Stock Arbitrage Bot")
st.markdown("Real-time arbitrage detection with live API integration")

# API Status Display
col1, col2, col3 = st.columns(3)

with col1:
    if config["simulation_mode"]:
        st.warning("🟡 **SIMULATION MODE**")
        st.write("Using simulated data (no real APIs configured)")
    else:
        st.success("🟢 **LIVE API MODE**")
        st.write(f"Using {len(config['brokers'])} real API sources")

with col2:
    if api_validation["valid"]:
        st.metric("API Sources", len(api_validation['configured_brokers']))
    else:
        st.metric("API Sources", 0)

with col3:
    st.metric("Target Symbols", len(symbols))

# Control Buttons
st.markdown("---")
button_col1, button_col2, button_col3, button_col4 = st.columns(4)

with button_col1:
    if st.button("🧪 Test APIs", help="Test API connections"):
        if not st.session_state.simulator:
            st.session_state.simulator = EnhancedSimulator(threshold=threshold, symbols=symbols)
        
        with st.spinner("Testing API connections..."):
            # Run async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(st.session_state.simulator.test_apis())
                st.session_state.api_status = result
            finally:
                loop.close()

with button_col2:
    start_disabled = st.session_state.running or len(symbols) == 0
    if st.button("▶️ Start Bot", disabled=start_disabled, help="Start arbitrage detection"):
        if not st.session_state.simulator:
            st.session_state.simulator = EnhancedSimulator(threshold=threshold, symbols=symbols)
        st.session_state.running = True
        st.rerun()

with button_col3:
    stop_disabled = not st.session_state.running
    if st.button("⏹️ Stop Bot", disabled=stop_disabled, help="Stop arbitrage detection"):
        if st.session_state.simulator:
            st.session_state.simulator.stop()
        st.session_state.running = False
        st.rerun()

with button_col4:
    if st.button("🔄 Reset", help="Reset all data"):
        st.session_state.simulator = None
        st.session_state.running = False
        st.session_state.api_status = None
        st.session_state.opportunities_history = []
        st.session_state.performance_history = []
        st.rerun()

# API Test Results
if st.session_state.api_status:
    st.markdown("---")
    st.subheader("🧪 API Test Results")
    
    if st.session_state.api_status.get("test_successful"):
        st.success("✅ API test successful!")
    else:
        st.error("❌ API test failed!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Configuration:**")
        st.write(f"• Simulation Mode: {st.session_state.api_status.get('simulation_mode', True)}")
        st.write(f"• Active APIs: {', '.join(st.session_state.api_status.get('active_apis', []))}")
        st.write(f"• Price Sources: {', '.join(st.session_state.api_status.get('price_sources', []))}")
    
    with col2:
        if st.session_state.api_status.get("sample_prices"):
            st.write("**Sample Prices:**")
            for source, price_info in st.session_state.api_status["sample_prices"].items():
                st.write(f"• {source}: {price_info['symbol']} = ${price_info['price']:.2f}")

# Simplified Live Display (avoiding complex async in Streamlit)
if st.session_state.running:
    st.markdown("---")
    st.success("🟢 **BOT IS RUNNING**")
    st.info("💡 **Note:** For full real-time functionality, use the command line interface: `python real_simulator.py`")
    
    # Show basic status
    if st.session_state.simulator:
        with st.spinner("Getting status..."):
            try:
                # Use a simple synchronous status check
                status_data = {
                    "configured": True,
                    "symbols": symbols,
                    "threshold": threshold * 100,
                    "update_interval": update_interval
                }
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Symbols", len(symbols))
                with col2:
                    st.metric("Threshold", f"{threshold*100:.1f}%")
                with col3:
                    st.metric("Interval", f"{update_interval}s")
                with col4:
                    st.metric("Mode", "Live" if not config["simulation_mode"] else "Sim")
                
            except Exception as e:
                st.error(f"Error getting status: {e}")

# Data Export Section
if st.session_state.opportunities_history:
    st.markdown("---")
    st.subheader("📥 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Export Opportunities as JSON"):
            export_data = json.dumps(st.session_state.opportunities_history, indent=2)
            st.download_button(
                label="📥 Download JSON",
                data=export_data,
                file_name=f"arbitrage_opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col2:
        if st.button("📊 Export as CSV"):
            if st.session_state.opportunities_history:
                df_export = pd.DataFrame(st.session_state.opportunities_history)
                csv_data = df_export.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name=f"arbitrage_opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

# Configuration Display
with st.expander("⚙️ Current Configuration"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Simulation Settings:**")
        st.write(f"• Symbols: {', '.join(symbols)}")
        st.write(f"• Threshold: {threshold*100:.2f}%")
        st.write(f"• Update Interval: {update_interval}s")
        st.write(f"• Max Duration: {max_duration}s" if max_duration > 0 else "• Duration: Unlimited")
    
    with col2:
        st.write("**API Configuration:**")
        st.write(f"• Simulation Mode: {config['simulation_mode']}")
        st.write(f"• Configured Brokers: {len(config['brokers'])}")
        if config['brokers']:
            for broker_name in config['brokers'].keys():
                st.write(f"  - {broker_name}")

# Command Line Instructions
st.markdown("---")
st.subheader("🖥️ Command Line Usage")
st.write("For full real-time functionality, use the enhanced command line interface:")

command_examples = f"""
# Test API connections
python real_simulator.py --test-apis

# Run with custom settings
python real_simulator.py --threshold {threshold*100} --interval {update_interval} --symbols {' '.join(symbols)}

# Run for specific duration
python real_simulator.py --duration 300 --interval 1.0

# Test broker APIs
python broker_apis.py

# Test data stream
python real_data_stream.py
"""

st.code(command_examples, language="bash")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Enhanced Stock Arbitrage Bot with Real API Integration</p>
    <p>⚠️ Educational purposes only. Real trading involves significant risks.</p>
</div>
""", unsafe_allow_html=True)
