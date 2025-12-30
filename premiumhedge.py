#!/usr/bin/env python3
"""
MT5 Pivot Strategy Backtester
Strategia: Poniedziałkowe sygnały (Buy<S3 / Sell>R3) + stały holding period
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="Forex Pivot Strategy Backtester",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .metric-positive {
        background: #d4edda;
        border: 2px solid #28a745;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .metric-negative {
        background: #f8d7da;
        border: 2px solid #dc3545;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Forex symbols mapping
FOREX_SYMBOLS = {
    'EURUSD': 'EURUSD=X',
    'GBPUSD': 'GBPUSD=X', 
    'AUDUSD': 'AUDUSD=X',
    'NZDUSD': 'NZDUSD=X',
    'USDCAD': 'USDCAD=X',
    'USDCHF': 'USDCHF=X',
    'USDJPY': 'USDJPY=X',
    'EURJPY': 'EURJPY=X',
    'GBPJPY': 'GBPJPY=X',
    'EURGBP': 'EURGBP=X',
    'CHFPLN': 'CHFPLN=X',
    'EURPLN': 'EURPLN=X',
    'USDPLN': 'USDPLN=X',
    'GBPPLN': 'GBPPLN=X'
}

class PivotBacktester:
    def __init__(self, lookback_days=7):
        self.lookback_days = lookback_days
    
    def get_forex_data(self, symbol, days=365):
        """Pobierz dane forex"""
        try:
            yf_symbol = FOREX_SYMBOLS.get(symbol, f"{symbol}=X")
            ticker = yf.Ticker(yf_symbol)
            
            data = ticker.history(period=f"{days}d", interval="1d")
            
            if data.empty:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days + 5)
                data = ticker.history(start=start_date, end=end_date, interval="1d")
            
            if data.empty:
                return None
            
            data = data.dropna()
            
            if hasattr(data.index, 'tz_localize'):
                try:
                    if data.index.tz is not None:
                        data.index = data.index.tz_convert(None)
                except:
                    pass
            
            df = pd.DataFrame({
                'Date': pd.to_datetime(data.index),
                'Open': data['Open'].astype(float),
                'High': data['High'].astype(float), 
                'Low': data['Low'].astype(float),
                'Close': data['Close'].astype(float),
                'Volume': data['Volume'].astype(float) if 'Volume' in data.columns else 0
            }).reset_index(drop=True)
            
            df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
            
            return df
            
        except Exception as e:
            st.error(f"Błąd pobierania danych: {str(e)}")
            return None
    
    def calculate_pivot_points(self, df):
        """Oblicz punkty pivot z poziomami S3 i R3"""
        if len(df) < self.lookback_days:
            return df
        
        df = df.reset_index(drop=True)
        pivot_data = []
        
        for i in range(self.lookback_days, len(df)):
            window = df.iloc[i-self.lookback_days:i]
            avg_high = window['High'].mean()
            avg_low = window['Low'].mean()
            avg_close = window['Close'].mean()
            
            pivot = (avg_high + avg_low + avg_close) / 3
            range_val = avg_high - avg_low
            
            r1 = 2 * pivot - avg_low
            r2 = pivot + range_val
            s1 = 2 * pivot - avg_high
            s2 = pivot - range_val
            
            r3 = r2 + range_val
            s3 = s2 - range_val
            
            pivot_data.append({
                'Date': df.iloc[i]['Date'],
                'Pivot': pivot,
                'R1': r1, 'R2': r2, 'R3': r3,
                'S1': s1, 'S2': s2, 'S3': s3
            })
        
        if pivot_data:
            pivot_df = pd.DataFrame(pivot_data)
            df = df.merge(pivot_df, on='Date', how='left')
        
        return df
    
    def run_backtest(self, df, initial_capital=10000, lot_size=1.0, spread_pips=2, holding_days=5):
        """
        Uruchom backtest strategii TYGODNIOWEJ
        Strategia: 
        - Każdy PONIEDZIAŁEK sprawdź sygnał:
          * Jeśli cena < S3 → KUP i trzymaj X dni
          * Jeśli cena > R3 → SPRZEDAJ i trzymaj X dni
        """
        
        trades = []
        capital = initial_capital
        open_positions = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            
            if pd.isna(row.get('S3')) or pd.isna(row.get('R3')):
                continue
            
            current_date = row['Date']
            current_price = row['Close']
            
            # ZAMKNIJ wygasające pozycje
            positions_to_close = []
            for pos_idx, pos in enumerate(open_positions):
                if current_date >= pos['exit_date']:
                    positions_to_close.append(pos_idx)
            
            for pos_idx in sorted(positions_to_close, reverse=True):
                pos = open_positions.pop(pos_idx)
                
                pip_value = 0.0001
                if 'JPY' in df.attrs.get('symbol', ''):
                    pip_value = 0.01
                
                if pos['type'] == 'long':
                    exit_price = current_price - (spread_pips * 0.0001)
                    pips_gained = (exit_price - pos['entry_price']) / pip_value
                else:
                    exit_price = current_price + (spread_pips * 0.0001)
                    pips_gained = (pos['entry_price'] - exit_price) / pip_value
                
                profit = pips_gained * pip_value * pos['lot_size'] * 100000
                capital += profit
                
                days_held = (current_date - pos['entry_date']).days
                
                trades.append({
                    'Entry Date': pos['entry_date'],
                    'Exit Date': current_date,
                    'Type': pos['type'].upper(),
                    'Entry Price': pos['entry_price'],
                    'Exit Price': exit_price,
                    'Entry Level': pos['entry_level'],
                    'Pips': pips_gained,
                    'Profit': profit,
                    'Capital': capital,
                    'Duration': days_held
                })
            
            # OTWIERAJ NOWE POZYCJE W PONIEDZIAŁKI
            if current_date.weekday() == 0:
                
                # Sygnał BUY: cena < S3
                if current_price < row['S3']:
                    entry_price = current_price + (spread_pips * 0.0001)
                    exit_date = current_date + timedelta(days=holding_days)
                    
                    open_positions.append({
                        'type': 'long',
                        'entry_date': current_date,
                        'exit_date': exit_date,
                        'entry_price': entry_price,
                        'entry_level': row['S3'],
                        'lot_size': lot_size
                    })
                
                # Sygnał SELL: cena > R3
                if current_price > row['R3']:
                    entry_price = current_price - (spread_pips * 0.0001)
                    exit_date = current_date + timedelta(days=holding_days)
                    
                    open_positions.append({
                        'type': 'short',
                        'entry_date': current_date,
                        'exit_date': exit_date,
                        'entry_price': entry_price,
                        'entry_level': row['R3'],
                        'lot_size': lot_size
                    })
        
        # Zamknij pozostałe pozycje
        last_row = df.iloc[-1]
        for pos in open_positions:
            pip_value = 0.0001
            if 'JPY' in df.attrs.get('symbol', ''):
                pip_value = 0.01
            
            if pos['type'] == 'long':
                exit_price = last_row['Close'] - (spread_pips * 0.0001)
                pips_gained = (exit_price - pos['entry_price']) / pip_value
            else:
                exit_price = last_row['Close'] + (spread_pips * 0.0001)
                pips_gained = (pos['entry_price'] - exit_price) / pip_value
            
            profit = pips_gained * pip_value * pos['lot_size'] * 100000
            capital += profit
            
            days_held = (last_row['Date'] - pos['entry_date']).days
            
            trades.append({
                'Entry Date': pos['entry_date'],
                'Exit Date': last_row['Date'],
                'Type': pos['type'].upper(),
                'Entry Price': pos['entry_price'],
                'Exit Price': exit_price,
                'Entry Level': pos['entry_level'],
                'Pips': pips_gained,
                'Profit': profit,
                'Capital': capital,
                'Duration': days_held
            })
        
        return pd.DataFrame(trades), capital

# TYTUŁ
st.title("📊 Forex Pivot Strategy Backtester")
st.markdown("**Strategia: Sygnały poniedziałkowe (Buy<S3 / Sell>R3) + stały holding period**")

# SIDEBAR
st.sidebar.header("⚙️ Konfiguracja")

# Wybór pary
major_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'GBPJPY', 'AUDUSD']
selected_symbol = st.sidebar.selectbox("Para walutowa:", major_pairs)

# Parametry
st.sidebar.markdown("### 💰 Parametry")
initial_capital = st.sidebar.number_input("Kapitał początkowy ($)", 1000, 100000, 10000, 1000)
lot_size = st.sidebar.number_input("Wielkość lota", 0.01, 10.0, 1.0, 0.01)
spread_pips = st.sidebar.number_input("Spread (pips)", 0.0, 10.0, 2.0, 0.1)

st.sidebar.markdown("### 📅 Analiza")
backtest_days = st.sidebar.slider("Dni historii", 30, 730, 365)
lookback_days = st.sidebar.slider("Okres pivot (dni)", 3, 14, 7)
holding_days = st.sidebar.slider("Holding period (dni)", 1, 30, 5)

# Przycisk
if st.sidebar.button("🚀 URUCHOM BACKTEST", type="primary"):
    
    backtester = PivotBacktester(lookback_days=lookback_days)
    
    with st.spinner(f"Pobieranie danych {selected_symbol}..."):
        df = backtester.get_forex_data(selected_symbol, backtest_days)
    
    if df is not None and len(df) > 0:
        st.success(f"✅ Pobrano {len(df)} dni danych")
        
        with st.spinner("Obliczanie pivot points..."):
            df = backtester.calculate_pivot_points(df)
            df.attrs['symbol'] = selected_symbol
        
        pivot_data = df[df['Pivot'].notna()].copy()
        
        if len(pivot_data) > 0:
            st.success(f"✅ Obliczono poziomy pivot dla {len(pivot_data)} dni")
            
            with st.spinner("Wykonywanie backtestu..."):
                trades_df, final_capital = backtester.run_backtest(
                    df, initial_capital, lot_size, spread_pips, holding_days
                )
            
            # WYNIKI
            st.markdown("## 📈 Wyniki Backtestu")
            
            col1, col2, col3, col4 = st.columns(4)
            total_return = final_capital - initial_capital
            return_pct = (total_return / initial_capital) * 100
            
            with col1:
                st.metric("Kapitał końcowy", f"${final_capital:,.2f}", f"{total_return:+,.2f}")
            with col2:
                st.metric("Zwrot %", f"{return_pct:.2f}%")
            with col3:
                st.metric("Liczba transakcji", len(trades_df))
            with col4:
                if len(trades_df) > 0:
                    win_rate = (trades_df['Profit'] > 0).sum() / len(trades_df) * 100
                    st.metric("Win Rate", f"{win_rate:.1f}%")
            
            if len(trades_df) > 0:
                
                # Statystyki per typ
                st.markdown("### 📊 Statystyki per typ pozycji")
                col1, col2 = st.columns(2)
                
                with col1:
                    long_trades = trades_df[trades_df['Type'] == 'LONG']
                    st.markdown("**📈 LONG positions**")
                    st.write(f"Liczba: {len(long_trades)}")
                    if len(long_trades) > 0:
                        long_wins = (long_trades['Profit'] > 0).sum()
                        st.write(f"Win rate: {long_wins / len(long_trades) * 100:.1f}%")
                        st.write(f"Avg profit: ${long_trades['Profit'].mean():.2f}")
                        st.write(f"Total profit: ${long_trades['Profit'].sum():.2f}")
                
                with col2:
                    short_trades = trades_df[trades_df['Type'] == 'SHORT']
                    st.markdown("**📉 SHORT positions**")
                    st.write(f"Liczba: {len(short_trades)}")
                    if len(short_trades) > 0:
                        short_wins = (short_trades['Profit'] > 0).sum()
                        st.write(f"Win rate: {short_wins / len(short_trades) * 100:.1f}%")
                        st.write(f"Avg profit: ${short_trades['Profit'].mean():.2f}")
                        st.write(f"Total profit: ${short_trades['Profit'].sum():.2f}")
                
                # Krzywa kapitału
                st.markdown("### 💹 Krzywa kapitału")
                
                fig = go.Figure()
                
                capital_curve = [initial_capital] + trades_df['Capital'].tolist()
                dates_curve = [df['Date'].iloc[0]] + trades_df['Exit Date'].tolist()
                
                fig.add_trace(go.Scatter(
                    x=dates_curve,
                    y=capital_curve,
                    mode='lines+markers',
                    name='Kapitał',
                    line=dict(color='#1f77b4', width=2),
                    fill='tonexty'
                ))
                
                fig.add_hline(y=initial_capital, line_dash='dash', line_color='gray')
                
                fig.update_layout(
                    title=f"Rozwój kapitału - {selected_symbol}",
                    xaxis_title="Data",
                    yaxis_title="Kapitał ($)",
                    height=400,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabela transakcji
                st.markdown("### 📝 Historia transakcji")
                
                display = trades_df.copy()
                display['Entry Date'] = display['Entry Date'].dt.strftime('%Y-%m-%d')
                display['Exit Date'] = display['Exit Date'].dt.strftime('%Y-%m-%d')
                for col in ['Entry Price', 'Exit Price', 'Entry Level']:
                    display[col] = display[col].round(5)
                display['Pips'] = display['Pips'].round(1)
                display['Profit'] = display['Profit'].round(2)
                
                st.dataframe(display, use_container_width=True)
                
                # Download
                csv = trades_df.to_csv(index=False)
                st.download_button(
                    "📥 Pobierz wyniki (CSV)",
                    csv,
                    f"backtest_{selected_symbol}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.warning("⚠️ Brak transakcji w wybranym okresie")
        else:
            st.error("❌ Za mało danych dla obliczenia pivot points")
    else:
        st.error("❌ Nie udało się pobrać danych")

else:
    st.info("👈 Skonfiguruj parametry w panelu bocznym i kliknij 'URUCHOM BACKTEST'")
    
    st.markdown("""
    ## 📖 Strategia
    
    **Tygodniowy system sygnałów:**
    
    - 📅 **Każdy poniedziałek** sprawdzamy sygnał:
      - Jeśli `Cena < S3` → Otwieramy **LONG** (kupno)
      - Jeśli `Cena > R3` → Otwieramy **SHORT** (sprzedaż)
    
    - ⏱️ **Holding period:** Każda pozycja trzymana przez X dni (np. 5)
    
    - 🔄 **Nakładające się pozycje:** Możesz mieć jednocześnie LONG i SHORT
    
    - 📊 **Rolling pivots:** Poziomy S3/R3 obliczane z ostatnich N dni
    """)

# Footer
st.markdown("---")
st.markdown(f"**🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}** | ⚠️ Tylko do celów edukacyjnych")
