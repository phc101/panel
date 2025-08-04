# CURRENCY PAIRS TRADING SUMMARY TABLE

import streamlit as st
import pandas as pd
import MetaTrader5 as mt5
from concurrent.futures import ThreadPoolExecutor
import time

# Fast data loader for all major pairs
@st.cache_data(ttl=30, show_spinner=False)
def load_pairs_summary():
    """Load trading data for all major currency pairs"""
    
    pairs = [
        'EURUSD.pro', 'GBPUSD.pro', 'USDJPY.pro', 'AUDUSD.pro', 
        'USDCHF.pro', 'NZDUSD.pro', 'USDCAD.pro', 'EURJPY.pro',
        'GBPJPY.pro', 'EURGBP.pro', 'AUDCAD.pro', 'XAUUSD.pro'
    ]
    
    def get_pair_data(symbol):
        try:
            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return None
                
            # Get last 14 daily bars for calculation
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 14)
            if rates is None or len(rates) < 7:
                return None
            
            # Calculate pivot levels
            recent_rates = rates[-7:]  # Last 7 days
            high = max([r['high'] for r in recent_rates])
            low = min([r['low'] for r in recent_rates])
            close = recent_rates[-1]['close']
            
            # Standard pivot calculation
            pivot = (high + low + close) / 3
            r1 = 2 * pivot - low
            s1 = 2 * pivot - high
            r2 = pivot + (high - low)
            s2 = pivot - (high - low)
            
            # Current price
            current_price = tick.ask
            
            # Generate signal based on pivot levels
            signal = "NEUTRAL"
            strength = 0
            
            if current_price <= s2:
                signal = "BUY"
                strength = 3  # Strong
            elif current_price <= s1:
                signal = "BUY" 
                strength = 2  # Medium
            elif current_price <= pivot:
                signal = "BUY"
                strength = 1  # Weak
            elif current_price >= r2:
                signal = "SELL"
                strength = 3  # Strong
            elif current_price >= r1:
                signal = "SELL"
                strength = 2  # Medium
            elif current_price >= pivot:
                signal = "SELL"
                strength = 1  # Weak
            
            # Calculate price change
            if len(rates) >= 2:
                prev_close = rates[-2]['close']
                change_pct = ((current_price - prev_close) / prev_close) * 100
            else:
                change_pct = 0
            
            return {
                'symbol': symbol.replace('.pro', ''),
                'price': current_price,
                'change': change_pct,
                'signal': signal,
                'strength': strength,
                'pivot': pivot,
                'spread': (tick.ask - tick.bid) * 10000  # in pips
            }
            
        except Exception as e:
            print(f"Error loading {symbol}: {e}")
            return None
    
    # Load all pairs in parallel
    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(get_pair_data, pairs))
    
    # Filter successful results
    valid_results = [r for r in results if r is not None]
    return valid_results

def create_trading_table():
    """Create the main trading summary table"""
    
    # Load data
    pairs_data = load_pairs_summary()
    
    if not pairs_data:
        st.error("❌ No trading data available")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(pairs_data)
    
    # Sort by signal strength (strongest first)
    df['sort_key'] = df.apply(lambda row: row['strength'] if row['signal'] == 'BUY' else -row['strength'], axis=1)
    df = df.sort_values('sort_key', ascending=False)
    
    # Create display table
    display_data = []
    for _, row in df.iterrows():
        
        # Signal with strength indicators
        if row['signal'] == 'BUY':
            if row['strength'] == 3:
                signal_display = "🟢 STRONG BUY"
                signal_color = "#00ff00"
            elif row['strength'] == 2:
                signal_display = "🟢 BUY"
                signal_color = "#90EE90"
            else:
                signal_display = "🟢 WEAK BUY"
                signal_color = "#98FB98"
        elif row['signal'] == 'SELL':
            if row['strength'] == 3:
                signal_display = "🔴 STRONG SELL"
                signal_color = "#ff0000"
            elif row['strength'] == 2:
                signal_display = "🔴 SELL"
                signal_color = "#FFB6C1"
            else:
                signal_display = "🔴 WEAK SELL"
                signal_color = "#FFC0CB"
        else:
            signal_display = "⚪ NEUTRAL"
            signal_color = "#f0f0f0"
        
        # Strength bars
        strength_bars = "█" * row['strength'] if row['strength'] > 0 else "─"
        
        display_data.append({
            'Pair': row['symbol'],
            'Price': f"{row['price']:.5f}",
            'Change%': f"{row['change']:+.2f}%",
            'Signal': signal_display,
            'Strength': strength_bars,
            'Pivot': f"{row['pivot']:.5f}",
            'Spread': f"{row['spread']:.1f}"
        })
    
    display_df = pd.DataFrame(display_data)
    
    return display_df, pairs_data

def display_summary_metrics(pairs_data):
    """Display summary statistics"""
    
    buy_signals = sum(1 for p in pairs_data if p['signal'] == 'BUY')
    sell_signals = sum(1 for p in pairs_data if p['signal'] == 'SELL')
    strong_signals = sum(1 for p in pairs_data if p['strength'] == 3)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📊 Total Pairs", len(pairs_data))
    
    with col2:
        st.metric("🟢 Buy Signals", buy_signals)
        
    with col3:
        st.metric("🔴 Sell Signals", sell_signals)
        
    with col4:
        st.metric("⚡ Strong Signals", strong_signals)
        
    with col5:
        avg_spread = sum(p['spread'] for p in pairs_data) / len(pairs_data)
        st.metric("📏 Avg Spread", f"{avg_spread:.1f}")

def main_trading_summary():
    """Main function to display the trading summary"""
    
    # Page header
    st.markdown("# 📈 **CURRENCY PAIRS TRADING SUMMARY**")
    st.markdown("*Real-time signals based on pivot point analysis*")
    
    # Add refresh button
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        last_update = time.strftime("%H:%M:%S")
        st.info(f"🕒 Updated: {last_update}")
    
    # Create and display table
    try:
        display_df, pairs_data = create_trading_table()
        
        if display_df is not None:
            # Display summary metrics
            display_summary_metrics(pairs_data)
            
            st.markdown("---")
            
            # Main trading table
            st.markdown("### 📋 **TRADING SIGNALS TABLE**")
            
            # Style the dataframe
            def style_signal_column(val):
                if "STRONG BUY" in val:
                    return "background-color: #00ff00; color: black; font-weight: bold;"
                elif "WEAK BUY" in val or val == "🟢 BUY":
                    return "background-color: #90EE90; color: black;"
                elif "STRONG SELL" in val:
                    return "background-color: #ff0000; color: white; font-weight: bold;"
                elif "WEAK SELL" in val or val == "🔴 SELL":
                    return "background-color: #FFB6C1; color: black;"
                else:
                    return "background-color: #f0f0f0; color: black;"
            
            def style_change_column(val):
                if "+" in val:
                    return "color: green; font-weight: bold;"
                elif "-" in val:
                    return "color: red; font-weight: bold;"
                else:
                    return "color: gray;"
            
            # Apply styling
            styled_df = display_df.style.applymap(
                style_signal_column, subset=['Signal']
            ).applymap(
                style_change_column, subset=['Change%']
            ).set_properties(**{
                'text-align': 'center',
                'font-size': '14px'
            })
            
            # Display the table
            st.dataframe(
                styled_df, 
                use_container_width=True, 
                height=400,
                hide_index=True
            )
            
            # Quick action buttons
            st.markdown("### ⚡ **QUICK ACTIONS**")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                strong_buys = [p for p in pairs_data if p['signal'] == 'BUY' and p['strength'] == 3]
                if strong_buys:
                    if st.button(f"🚀 Execute {len(strong_buys)} Strong Buys"):
                        buy_pairs = [p['symbol'] for p in strong_buys]
                        st.success(f"Ready to BUY: {', '.join(buy_pairs)}")
            
            with col2:
                strong_sells = [p for p in pairs_data if p['signal'] == 'SELL' and p['strength'] == 3]
                if strong_sells:
                    if st.button(f"📉 Execute {len(strong_sells)} Strong Sells"):
                        sell_pairs = [p['symbol'] for p in strong_sells]
                        st.success(f"Ready to SELL: {', '.join(sell_pairs)}")
            
            with col3:
                if st.button("💾 Export CSV"):
                    csv = display_df.to_csv(index=False)
                    st.download_button(
                        "📁 Download Data",
                        csv,
                        f"trading_signals_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv"
                    )
        
    except Exception as e:
        st.error(f"❌ Error creating table: {str(e)}")

# Auto-refresh functionality
def setup_auto_refresh():
    """Setup automatic refresh"""
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        auto_refresh = st.checkbox("🔄 Auto Refresh", value=False)
    
    with col2:
        if auto_refresh:
            refresh_seconds = st.selectbox("Refresh Every", [30, 60, 120, 300], index=0)
            
            # Auto refresh logic
            if 'last_refresh' not in st.session_state:
                st.session_state.last_refresh = time.time()
            
            elapsed = time.time() - st.session_state.last_refresh
            
            if elapsed >= refresh_seconds:
                st.cache_data.clear()
                st.session_state.last_refresh = time.time()
                st.rerun()
            else:
                remaining = refresh_seconds - elapsed
                st.info(f"⏰ Next refresh in {remaining:.0f}s")

# Integration with your existing app
def run_trading_summary_app():
    """Complete app with trading summary"""
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    
    .metric-container {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem;
    }
    
    .dataframe td {
        font-weight: 500 !important;
    }
    
    h1, h3 {
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Check MT5 connection
    if not st.session_state.get('mt5_connected', False):
        st.warning("⚠️ MT5 not connected. Please connect to MetaTrader 5 first.")
        # Add your MT5 connection form here
        return
    
    # Main trading summary
    main_trading_summary()
    
    # Auto refresh setup
    setup_auto_refresh()

# Run the app
if __name__ == "__main__":
    run_trading_summary_app()
