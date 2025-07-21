import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import io
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import time
import threading

# Streamlit app configuration
st.set_page_config(page_title="Portfolio Momentum Pivot Points Trading Strategy", layout="wide")

# Initialize session state for MT5 connection
if 'mt5_connected' not in st.session_state:
    st.session_state.mt5_connected = False
if 'mt5_account_info' not in st.session_state:
    st.session_state.mt5_account_info = None
if 'live_positions' not in st.session_state:
    st.session_state.live_positions = []
if 'live_signals' not in st.session_state:
    st.session_state.live_signals = []

# MT5 Helper Functions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_mt5_symbols():
    """Get available MT5 symbols"""
    if not st.session_state.mt5_connected:
        return []
    
    try:
        symbols = mt5.symbols_get()
        symbol_list = []
        for symbol in symbols:
            if symbol.visible and ('USD' in symbol.name or 'EUR' in symbol.name):
                symbol_list.append({
                    'symbol': symbol.name,
                    'description': symbol.description,
                    'spread': symbol.spread
                })
        return symbol_list
    except:
        return []

def connect_mt5(login, password, server):
    """Connect to MT5"""
    try:
        if not mt5.initialize():
            return False, f"MT5 initialization failed: {mt5.last_error()}"
        
        if not mt5.login(login, password=password, server=server):
            mt5.shutdown()
            return False, f"Login failed: {mt5.last_error()}"
        
        account = mt5.account_info()
        st.session_state.mt5_connected = True
        st.session_state.mt5_account_info = {
            'login': account.login,
            'balance': account.balance,
            'equity': account.equity,
            'currency': account.currency,
            'leverage': account.leverage,
            'server': account.server
        }
        
        return True, "Connected successfully!"
        
    except Exception as e:
        return False, f"Connection error: {str(e)}"

def disconnect_mt5():
    """Disconnect from MT5"""
    if st.session_state.mt5_connected:
        mt5.shutdown()
        st.session_state.mt5_connected = False
        st.session_state.mt5_account_info = None

def get_mt5_live_data(symbol, timeframe='D1', count=30):
    """Get live data from MT5"""
    if not st.session_state.mt5_connected:
        return None
    
    try:
        # Convert timeframe
        tf_map = {
            'M1': mt5.TIMEFRAME_M1, 'M5': mt5.TIMEFRAME_M5, 'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30, 'H1': mt5.TIMEFRAME_H1, 'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1, 'W1': mt5.TIMEFRAME_W1
        }
        
        mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_D1)
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, count)
        
        if rates is None:
            return None
        
        df = pd.DataFrame(rates)
        df['Date'] = pd.to_datetime(df['time'], unit='s')
        df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'})
        
        return df[['Date', 'Open', 'High', 'Low', 'Close']]
        
    except Exception as e:
        st.error(f"Error getting MT5 data: {e}")
        return None

def get_current_positions():
    """Get current MT5 positions"""
    if not st.session_state.mt5_connected:
        return []
    
    try:
        positions = mt5.positions_get()
        if positions is None:
            return []
        
        position_list = []
        for pos in positions:
            position_list.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL',
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'profit': pos.profit,
                'time': datetime.fromtimestamp(pos.time),
                'comment': pos.comment
            })
        
        return position_list
        
    except Exception as e:
        st.error(f"Error getting positions: {e}")
        return []

def place_mt5_order(symbol, order_type, volume, comment="Streamlit Bot"):
    """Place order via MT5"""
    if not st.session_state.mt5_connected:
        return False, "Not connected to MT5"
    
    try:
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "deviation": 10,
            "magic": 234000,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            return True, f"Order executed: {result.order}"
        else:
            return False, f"Order failed: {result.comment}"
            
    except Exception as e:
        return False, f"Error placing order: {str(e)}"

# Page Layout
st.title("Portfolio Momentum Pivot Points Trading Strategy")

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📊 Backtesting", "🔴 Live Trading", "📈 Live Positions", "⚙️ Settings"])

# Tab 1: Original Backtesting (your existing code)
with tab1:
    st.markdown("**Backtest strategii momentum dla maksymalnie 5 par walutowych w formacie Investing.com. Wyniki prezentowane jako portfel z równą alokacją.**")
    
    # Your existing backtesting code goes here
    st.subheader("Wczytaj pliki CSV (maks. 5 par walutowych)")
    st.markdown("Wczytaj pliki CSV z danymi w formacie Investing.com (np. EUR_PLN Historical Data.csv). Wymagane kolumny: Date, Price, Open, High, Low.")
    uploaded_files = st.file_uploader("Wybierz pliki CSV", type=["csv"], accept_multiple_files=True, key="backtest_files")
    
    # Trading parameters
    st.subheader("Parametry Handlowe")
    holding_days = st.slider("Liczba dni trzymania pozycji", min_value=1, max_value=10, value=3, step=1, key="bt_holding")
    stop_loss_percent = st.number_input("Stop Loss (%):", min_value=0.0, max_value=10.0, value=2.0, step=0.1, key="bt_sl")
    no_overlap = st.checkbox("Brak nakładających się pozycji", value=True, key="bt_overlap")
    dynamic_leverage = st.checkbox("Dynamiczne dźwignia finansowa", value=False, key="bt_leverage")
    
    # Rest of your existing backtesting code...
    if uploaded_files:
        st.success("Backtesting functionality - use your existing code here")

# Tab 2: Live Trading
with tab2:
    st.header("🔴 Live Trading with OANDA TMS")
    
    # MT5 Connection Section
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("MT5 Connection")
        
        if not st.session_state.mt5_connected:
            with st.form("mt5_connection"):
                mt5_login = st.number_input("MT5 Login", min_value=1, value=12345678, help="Your MT5 account number")
                mt5_password = st.text_input("MT5 Password", type="password", help="Your MT5 password")
                mt5_server = st.text_input("MT5 Server", value="OANDA TMS Brokers S.A", help="Your MT5 server name")
                
                connect_btn = st.form_submit_button("Connect to MT5", type="primary")
                
                if connect_btn:
                    with st.spinner("Connecting to MT5..."):
                        success, message = connect_mt5(mt5_login, mt5_password, mt5_server)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
        else:
            # Show connection status
            account = st.session_state.mt5_account_info
            st.success("✅ Connected to MT5!")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Account", f"{account['login']}")
                st.metric("Balance", f"{account['balance']:.2f} {account['currency']}")
            with col_b:
                st.metric("Equity", f"{account['equity']:.2f} {account['currency']}")
                st.metric("Leverage", f"1:{account['leverage']}")
            
            if st.button("Disconnect", type="secondary"):
                disconnect_mt5()
                st.rerun()
    
    with col2:
        st.subheader("Live Trading Controls")
        
        if st.session_state.mt5_connected:
            # Get available symbols
            symbols = get_mt5_symbols()
            
            if symbols:
                symbol_names = [s['symbol'] for s in symbols]
                selected_symbols = st.multiselect(
                    "Select Trading Pairs",
                    options=symbol_names,
                    default=[s for s in symbol_names if s in ['EURUSD.pro', 'GBPUSD.pro', 'USDJPY.pro']][:3],
                    help="Choose up to 5 currency pairs for live trading"
                )
                
                # Live trading parameters
                st.subheader("Live Trading Parameters")
                live_holding_days = st.slider("Holding Days", 1, 10, 3, key="live_holding")
                live_stop_loss = st.number_input("Stop Loss (%)", 0.1, 10.0, 2.0, 0.1, key="live_sl")
                live_risk_percent = st.number_input("Risk Per Trade (%)", 0.1, 5.0, 1.0, 0.1, key="live_risk")
                live_lot_size = st.number_input("Lot Size", 0.01, 10.0, 0.01, 0.01, key="live_lots")
                
                # Manual signal check
                if st.button("🔍 Check Signals Now", type="primary"):
                    if selected_symbols:
                        with st.spinner("Checking for trading signals..."):
                            signals = []
                            
                            for symbol in selected_symbols:
                                # Get live data
                                df = get_mt5_live_data(symbol, 'D1', 30)
                                if df is not None and len(df) >= 7:
                                    # Calculate pivot points (your existing function)
                                    window = df.iloc[-7:]
                                    avg_high = window['High'].mean()
                                    avg_low = window['Low'].mean()
                                    avg_close = window['Close'].mean()
                                    
                                    pivot = (avg_high + avg_low + avg_close) / 3
                                    r2 = pivot + (avg_high - avg_low)
                                    s2 = pivot - (avg_high - avg_low)
                                    
                                    # Get current price
                                    tick = mt5.symbol_info_tick(symbol)
                                    if tick:
                                        current_price = tick.ask
                                        
                                        signal = None
                                        if current_price < s2:
                                            signal = 'BUY'
                                        elif current_price > r2:
                                            signal = 'SELL'
                                        
                                        if signal:
                                            signals.append({
                                                'Symbol': symbol,
                                                'Signal': signal,
                                                'Current Price': current_price,
                                                'S2/R2 Level': s2 if signal == 'BUY' else r2,
                                                'Spread': tick.ask - tick.bid,
                                                'Time': datetime.now()
                                            })
                            
                            st.session_state.live_signals = signals
                            
                            if signals:
                                st.success(f"Found {len(signals)} trading signals!")
                            else:
                                st.info("No trading signals found at this time.")
                
                # Show current signals
                if st.session_state.live_signals:
                    st.subheader("🚨 Current Signals")
                    signals_df = pd.DataFrame(st.session_state.live_signals)
                    st.dataframe(signals_df, use_container_width=True)
                    
                    # Execute signals
                    st.subheader("Execute Trades")
                    for i, signal in enumerate(st.session_state.live_signals):
                        col_sig1, col_sig2, col_sig3 = st.columns([2, 1, 1])
                        
                        with col_sig1:
                            st.write(f"**{signal['Signal']} {signal['Symbol']}** @ {signal['Current Price']:.5f}")
                        
                        with col_sig2:
                            if st.button(f"Execute {signal['Signal']}", key=f"exec_{i}"):
                                order_type = mt5.ORDER_TYPE_BUY if signal['Signal'] == 'BUY' else mt5.ORDER_TYPE_SELL
                                
                                success, message = place_mt5_order(
                                    symbol=signal['Symbol'],
                                    order_type=order_type,
                                    volume=live_lot_size,
                                    comment=f"Pivot {signal['Signal']}"
                                )
                                
                                if success:
                                    st.success(f"✅ {message}")
                                else:
                                    st.error(f"❌ {message}")
                        
                        with col_sig3:
                            st.write(f"Risk: {live_risk_percent}%")
            else:
                st.warning("No trading symbols available. Check your MT5 connection.")
        else:
            st.warning("Please connect to MT5 first to enable live trading.")

# Tab 3: Live Positions
with tab3:
    st.header("📈 Live Positions")
    
    if st.session_state.mt5_connected:
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh positions", value=False)
        
        if auto_refresh:
            # Auto refresh every 10 seconds
            placeholder = st.empty()
            
            # This would need to be handled differently in production
            # For demo purposes, we'll just refresh on manual button click
            pass
        
        # Manual refresh button
        if st.button("🔄 Refresh Positions"):
            st.session_state.live_positions = get_current_positions()
        
        # Show current positions
        positions = get_current_positions()
        
        if positions:
            st.subheader(f"Open Positions ({len(positions)})")
            
            # Calculate total P&L
            total_pnl = sum([pos['profit'] for pos in positions])
            
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                st.metric("Open Positions", len(positions))
            with col_p2:
                st.metric("Total P&L", f"{total_pnl:.2f} {st.session_state.mt5_account_info['currency']}")
            with col_p3:
                if st.button("🔴 Close All Positions", type="secondary"):
                    st.warning("Close all functionality would go here")
            
            # Positions table
            positions_df = pd.DataFrame(positions)
            positions_df['Time'] = positions_df['time'].dt.strftime('%Y-%m-%d %H:%M')
            
            # Display positions
            st.dataframe(
                positions_df[['ticket', 'symbol', 'type', 'volume', 'price_open', 'price_current', 'profit', 'Time', 'comment']],
                use_container_width=True
            )
            
            # Individual position controls
            st.subheader("Position Controls")
            for i, pos in enumerate(positions):
                col_pos1, col_pos2, col_pos3, col_pos4 = st.columns([2, 1, 1, 1])
                
                with col_pos1:
                    profit_color = "🟢" if pos['profit'] >= 0 else "🔴"
                    st.write(f"{profit_color} **{pos['type']} {pos['volume']} {pos['symbol']}**")
                
                with col_pos2:
                    st.write(f"P&L: {pos['profit']:.2f}")
                
                with col_pos3:
                    st.write(f"Price: {pos['price_current']:.5f}")
                
                with col_pos4:
                    if st.button(f"Close", key=f"close_{pos['ticket']}"):
                        st.info(f"Would close position {pos['ticket']}")
        else:
            st.info("No open positions")
    else:
        st.warning("Connect to MT5 to view live positions")

# Tab 4: Settings
with tab4:
    st.header("⚙️ Settings")
    
    st.subheader("Strategy Configuration")
    
    col_set1, col_set2 = st.columns(2)
    
    with col_set1:
        st.write("**Pivot Point Calculation**")
        pivot_period = st.slider("Pivot Period (days)", 3, 14, 7)
        st.write("**Risk Management**")
        max_positions = st.slider("Max Open Positions", 1, 10, 3)
        max_daily_loss = st.number_input("Max Daily Loss (%)", 1.0, 20.0, 5.0)
    
    with col_set2:
        st.write("**Notification Settings**")
        enable_alerts = st.checkbox("Enable Signal Alerts", True)
        email_notifications = st.checkbox("Email Notifications", False)
        
        if email_notifications:
            email_address = st.text_input("Email Address")
    
    st.subheader("Data Sources")
    data_source = st.selectbox(
        "Primary Data Source",
        ["MT5 Live Data", "MT5 + Yahoo Finance Backup", "Yahoo Finance Only"]
    )
    
    st.subheader("Export/Import")
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        if st.button("📥 Export Settings"):
            st.success("Settings export functionality would go here")
    
    with col_exp2:
        uploaded_settings = st.file_uploader("📤 Import Settings", type=['json'])
        if uploaded_settings:
            st.success("Settings import functionality would go here")

# Sidebar - Quick Status
with st.sidebar:
    st.header("📊 Quick Status")
    
    if st.session_state.mt5_connected:
        st.success("🟢 MT5 Connected")
        account = st.session_state.mt5_account_info
        st.metric("Balance", f"{account['balance']:.2f}")
        st.metric("Equity", f"{account['equity']:.2f}")
        
        positions = get_current_positions()
        st.metric("Open Positions", len(positions))
        
        if positions:
            total_pnl = sum([pos['profit'] for pos in positions])
            st.metric("Total P&L", f"{total_pnl:.2f}")
    else:
        st.error("🔴 MT5 Disconnected")
        st.write("Connect in Live Trading tab")
    
    st.divider()
    
    st.header("🎯 Strategy Rules")
    st.write("""
    **BUY Signal**: Price < S2 level
    **SELL Signal**: Price > R2 level  
    **Pivot**: 7-day average (H+L+C)/3
    **S2**: Pivot - (AvgHigh - AvgLow)
    **R2**: Pivot + (AvgHigh - AvgLow)
    """)

# Cleanup on app exit
def cleanup():
    if st.session_state.mt5_connected:
        disconnect_mt5()

import atexit
atexit.register(cleanup)
