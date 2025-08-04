# TRADING PAIRS SUMMARY TABLE - Add to your ultra-fast app

import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
import MetaTrader5 as mt5

# Enhanced batch data loader with more pairs
@st.cache_data(ttl=30, show_spinner=False)
def get_all_pairs_data():
    """Load data for all major pairs efficiently"""
    pairs = [
        'EURUSD.pro', 'GBPUSD.pro', 'USDJPY.pro', 'AUDUSD.pro',
        'USDCHF.pro', 'NZDUSD.pro', 'USDCAD.pro', 'EURJPY.pro',
        'GBPJPY.pro', 'EURGBP.pro', 'AUDCAD.pro', 'XAUUSD.pro'
    ]
    
    batch_data = {}
    
    def load_pair_data(symbol):
        try:
            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return symbol, None
            
            # Get last 20 daily candles for signal calculation
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 20)
            if rates is None or len(rates) < 10:
                return symbol, None
            
            # Calculate basic indicators
            highs = [r['high'] for r in rates[-10:]]
            lows = [r['low'] for r in rates[-10:]]
            closes = [r['close'] for r in rates[-10:]]
            
            # Pivot points
            pivot = (max(highs) + min(lows) + closes[-1]) / 3
            r1 = 2 * pivot - min(lows)
            s1 = 2 * pivot - max(highs)
            r2 = pivot + (max(highs) - min(lows))
            s2 = pivot - (max(highs) - min(lows))
            
            # Simple trend analysis
            ma_5 = sum(closes[-5:]) / 5
            ma_10 = sum(closes[-10:]) / 10
            trend = "UP" if ma_5 > ma_10 else "DOWN" if ma_5 < ma_10 else "FLAT"
            
            # Signal generation
            current_price = tick.ask
            signal = "NEUTRAL"
            strength = 0
            
            if current_price <= s2:
                signal = "STRONG BUY"
                strength = 3
            elif current_price <= s1:
                signal = "BUY"
                strength = 2
            elif current_price >= r2:
                signal = "STRONG SELL"
                strength = -3
            elif current_price >= r1:
                signal = "SELL"
                strength = -2
            elif current_price < pivot and trend == "UP":
                signal = "WEAK BUY"
                strength = 1
            elif current_price > pivot and trend == "DOWN":
                signal = "WEAK SELL"
                strength = -1
            
            # Price change calculation
            if len(rates) > 1:
                prev_close = rates[-2]['close']
                change_pct = ((current_price - prev_close) / prev_close) * 100
            else:
                change_pct = 0
            
            return symbol, {
                'bid': tick.bid,
                'ask': tick.ask,
                'spread': (tick.ask - tick.bid) * 10000,  # in pips
                'change_pct': change_pct,
                'pivot': pivot,
                'r1': r1, 'r2': r2,
                's1': s1, 's2': s2,
                'signal': signal,
                'strength': strength,
                'trend': trend,
                'volume': getattr(tick, 'volume', 0),
                'time': tick.time
            }
            
        except Exception as e:
            print(f"Error loading {symbol}: {e}")
            return symbol, None
    
    # Load all pairs in parallel
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=6) as executor:
        results = executor.map(load_pair_data, pairs)
    
    for symbol, data in results:
        if data:
            batch_data[symbol] = data
    
    return batch_data

# Create the summary table
def create_pairs_summary_table():
    """Create a comprehensive pairs summary table"""
    
    # Get all pairs data
    pairs_data = get_all_pairs_data()
    
    if not pairs_data:
        st.error("No market data available")
        return
    
    # Convert to DataFrame for easy manipulation
    summary_data = []
    
    for symbol, data in pairs_data.items():
        # Clean symbol name
        clean_symbol = symbol.replace('.pro', '')
        
        summary_data.append({
            'Pair': clean_symbol,
            'Price': data['ask'],
            'Change%': data['change_pct'],
            'Spread': data['spread'],
            'Signal': data['signal'],
            'Strength': data['strength'],
            'Trend': data['trend'],
            'Pivot': data['pivot'],
            'R2': data['r2'],
            'R1': data['r1'],
            'S1': data['s1'],
            'S2': data['s2'],
            'Volume': data['volume'],
            'Updated': datetime.fromtimestamp(data['time']).strftime('%H:%M:%S')
        })
    
    df = pd.DataFrame(summary_data)
    
    # Sort by signal strength (strongest signals first)
    df = df.sort_values('Strength', key=abs, ascending=False)
    
    return df

# Enhanced display function with color coding
def display_pairs_summary():
    """Display the pairs summary with advanced formatting"""
    
    st.markdown("## 📊 **Live Trading Pairs Summary**")
    
    # Get summary data
    df = create_pairs_summary_table()
    
    if df.empty:
        st.warning("No trading data available")
        return
    
    # Create metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_pairs = len(df)
        st.metric("📈 Total Pairs", total_pairs)
    
    with col2:
        buy_signals = len(df[df['Signal'].str.contains('BUY')])
        st.metric("🟢 Buy Signals", buy_signals)
    
    with col3:
        sell_signals = len(df[df['Signal'].str.contains('SELL')])
        st.metric("🔴 Sell Signals", sell_signals)
    
    with col4:
        strong_signals = len(df[df['Signal'].str.contains('STRONG')])
        st.metric("⚡ Strong Signals", strong_signals)
    
    with col5:
        avg_spread = df['Spread'].mean()
        st.metric("📏 Avg Spread", f"{avg_spread:.1f}")
    
    st.markdown("---")
    
    # Style the dataframe
    def style_dataframe(df):
        """Apply conditional formatting to the dataframe"""
        
        def color_signal(val):
            if 'STRONG BUY' in val:
                return 'background-color: #00ff00; color: black; font-weight: bold'
            elif 'BUY' in val:
                return 'background-color: #90EE90; color: black'
            elif 'STRONG SELL' in val:
                return 'background-color: #ff0000; color: white; font-weight: bold'
            elif 'SELL' in val:
                return 'background-color: #FFB6C1; color: black'
            else:
                return 'background-color: #f0f0f0; color: black'
        
        def color_change(val):
            if val > 0:
                return 'color: green; font-weight: bold'
            elif val < 0:
                return 'color: red; font-weight: bold'
            else:
                return 'color: gray'
        
        def color_trend(val):
            if val == 'UP':
                return 'color: green'
            elif val == 'DOWN':
                return 'color: red'
            else:
                return 'color: orange'
        
        # Apply styles
        styled = df.style.applymap(color_signal, subset=['Signal']) \
                        .applymap(color_change, subset=['Change%']) \
                        .applymap(color_trend, subset=['Trend']) \
                        .format({
                            'Price': '{:.5f}',
                            'Change%': '{:+.2f}%',
                            'Spread': '{:.1f}',
                            'Pivot': '{:.5f}',
                            'R2': '{:.5f}',
                            'R1': '{:.5f}',
                            'S1': '{:.5f}',
                            'S2': '{:.5f}',
                            'Volume': '{:,.0f}'
                        })
        
        return styled
    
    # Display the styled table
    styled_df = style_dataframe(df)
    st.dataframe(styled_df, use_container_width=True, height=400)
    
    # Quick action buttons
    st.markdown("### ⚡ Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔍 Refresh All", key="refresh_all"):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        strong_buy_pairs = df[df['Signal'] == 'STRONG BUY']
        if not strong_buy_pairs.empty and st.button("🚀 Execute Strong Buys", key="exec_buy"):
            st.success(f"Would execute BUY orders for: {', '.join(strong_buy_pairs['Pair'].tolist())}")
    
    with col3:
        strong_sell_pairs = df[df['Signal'] == 'STRONG SELL']
        if not strong_sell_pairs.empty and st.button("📉 Execute Strong Sells", key="exec_sell"):
            st.success(f"Would execute SELL orders for: {', '.join(strong_sell_pairs['Pair'].tolist())}")
    
    with col4:
        if st.button("📊 Export Data", key="export"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="💾 Download CSV",
                data=csv,
                file_name=f"trading_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

# Auto-refresh functionality
def setup_auto_refresh():
    """Setup auto-refresh with countdown"""
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        auto_refresh = st.checkbox("🔄 Auto Refresh (30s)", key="auto_refresh")
    
    with col2:
        refresh_interval = st.selectbox("Interval", [15, 30, 60, 120], index=1, key="refresh_interval")
    
    if auto_refresh:
        # Show countdown
        placeholder = st.empty()
        
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = time.time()
        
        time_since_refresh = time.time() - st.session_state.last_refresh
        time_to_refresh = refresh_interval - time_since_refresh
        
        if time_to_refresh <= 0:
            st.cache_data.clear()
            st.session_state.last_refresh = time.time()
            st.rerun()
        else:
            placeholder.info(f"⏱️ Next refresh in {time_to_refresh:.0f} seconds")
            time.sleep(1)
            st.rerun()

# Compact view for mobile/small screens
def display_compact_summary():
    """Compact view for better mobile experience"""
    
    if st.checkbox("📱 Compact View"):
        df = create_pairs_summary_table()
        
        # Show only essential columns
        compact_df = df[['Pair', 'Price', 'Change%', 'Signal', 'Updated']].copy()
        
        # Add emoji indicators
        def add_signal_emoji(signal):
            if 'STRONG BUY' in signal:
                return '🚀 ' + signal
            elif 'BUY' in signal:
                return '📈 ' + signal
            elif 'STRONG SELL' in signal:
                return '📉 ' + signal
            elif 'SELL' in signal:
                return '🔻 ' + signal
            else:
                return '➖ ' + signal
        
        compact_df['Signal'] = compact_df['Signal'].apply(add_signal_emoji)
        
        st.dataframe(compact_df, use_container_width=True, height=300)

# Integration with your existing ultra-fast app
def enhanced_ultra_fast_app():
    """Enhanced version with pairs summary table"""
    
    # Add the CSS for better styling
    st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .signal-strong-buy {
        background-color: #00ff00 !important;
        color: black !important;
        font-weight: bold !important;
    }
    
    .signal-strong-sell {
        background-color: #ff0000 !important;
        color: white !important;
        font-weight: bold !important;
    }
    
    .stDataFrame {
        border: 1px solid #333;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # App title
    st.markdown("# ⚡ **Ultra Fast Pivot Trading Bot**")
    
    # Connection status (your existing code)
    if st.session_state.get('mt5_connected', False):
        account = st.session_state.get('mt5_account_info', {})
        st.success(f"✅ Connected | Balance: {account.get('balance', 0):.0f} | Server: {account.get('server', 'Unknown')}")
    else:
        st.error("🔴 MT5 Disconnected - Please connect first")
    
    # Add the pairs summary table at the top
    display_pairs_summary()
    
    # Auto-refresh setup
    setup_auto_refresh()
    
    # Compact view option
    display_compact_summary()
    
    # Separator
    st.markdown("---")
    
    # Your existing minimal UI can go here
    st.markdown("### 🎯 Quick Actions")
    minimal_trading_ui()  # Your existing function

# Usage in your main app
if __name__ == "__main__":
    # Initialize MT5 connection (your existing code)
    if not st.session_state.get('mt5_connected', False):
        # Your MT5 connection code here
        pass
    
    # Run the enhanced app
    enhanced_ultra_fast_app()

# Additional utility functions for the summary table

def get_market_hours_status():
    """Check if major markets are open"""
    now = datetime.now()
    hour = now.hour
    
    # Simplified market hours (UTC)
    market_status = {
        'FOREX': 'OPEN' if 0 <= hour <= 23 else 'CLOSED',  # Forex is almost always open
        'LONDON': 'OPEN' if 8 <= hour <= 16 else 'CLOSED',
        'NEW_YORK': 'OPEN' if 13 <= hour <= 21 else 'CLOSED',
        'TOKYO': 'OPEN' if 23 <= hour or hour <= 7 else 'CLOSED'
    }
    
    return market_status

def display_market_status():
    """Display market hours status"""
    status = get_market_hours_status()
    
    st.markdown("#### 🌍 Market Hours")
    cols = st.columns(len(status))
    
    for i, (market, state) in enumerate(status.items()):
        with cols[i]:
            emoji = "🟢" if state == "OPEN" else "🔴"
            st.metric(f"{emoji} {market}", state)

# Performance monitoring for the table
def monitor_table_performance():
    """Monitor how fast the table loads"""
    if st.checkbox("📊 Performance Monitor"):
        start_time = time.time()
        
        # Measure table creation time
        df = create_pairs_summary_table()
        table_time = (time.time() - start_time) * 1000
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Table Load Time", f"{table_time:.0f}ms")
        with col2:
            st.metric("Pairs Loaded", len(df))
        with col3:
            cache_info = st.cache_data.get_stats()
            st.metric("Cache Hits", len(cache_info))

# Add this to your existing config.toml for even better performance
additional_config = """
# Add to your .streamlit/config.toml for table optimization

[theme]
base = "dark"
primaryColor = "#00ff00"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#262730"
textColor = "#FAFAFA"

[server]
maxUploadSize = 50
maxMessageSize = 50
enableStaticServing = false
"""
