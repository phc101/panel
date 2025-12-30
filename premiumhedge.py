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
    
    def load_csv_data(self, uploaded_file):
        """Załaduj dane z pliku CSV - wspiera format Investing.com i inne"""
        try:
            df = None
            successful_config = None
            
            for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                for sep in [',', ';', '\t']:
                    try:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, sep=sep, encoding=encoding, thousands=',')
                        if len(df.columns) >= 5:
                            successful_config = f"{encoding} + separator '{sep}'"
                            break
                    except:
                        continue
                if df is not None and len(df.columns) >= 5:
                    break
            
            if df is None or len(df.columns) < 5:
                st.error("❌ Nie można odczytać pliku CSV. Sprawdź format.")
                return None
            
            st.info(f"✅ Odczytano plik używając: {successful_config}")
            st.info(f"📋 Znalezione kolumny: {', '.join(df.columns.tolist())}")
            
            df.columns = df.columns.str.strip().str.lower().str.replace('"', '')
            
            column_mapping = {}
            
            date_cols = ['date', 'datetime', 'time', 'timestamp', 'data', 'datum']
            for col in df.columns:
                if col in date_cols or any(d in col for d in date_cols):
                    column_mapping['Date'] = col
                    break
            
            ohlc_mapping = {
                'Open': ['open', 'o', 'opening'],
                'High': ['high', 'h', 'max', 'hi'],
                'Low': ['low', 'l', 'min', 'lo'],
                'Close': ['close', 'c', 'last', 'price', 'closing']
            }
            
            for target, possible_names in ohlc_mapping.items():
                for col in df.columns:
                    if col in possible_names or any(name in col for name in possible_names):
                        column_mapping[target] = col
                        break
            
            volume_cols = ['volume', 'vol', 'v', 'vol.', 'wolumen', 'volume.']
            for col in df.columns:
                if col in volume_cols or any(v in col for v in volume_cols):
                    column_mapping['Volume'] = col
                    break
            
            required = ['Date', 'Open', 'High', 'Low', 'Close']
            missing = [col for col in required if col not in column_mapping]
            
            if missing:
                st.error(f"❌ Brakujące kolumny: {', '.join(missing)}")
                st.info(f"💡 Dostępne kolumny: {', '.join(df.columns.tolist())}")
                return None
            
            new_df = pd.DataFrame()
            for target, source in column_mapping.items():
                new_df[target] = df[source].copy()
            
            if 'Volume' not in new_df.columns:
                new_df['Volume'] = 0
            
            # Parsuj daty
            try:
                new_df['Date'] = pd.to_datetime(new_df['Date'], errors='coerce')
                
                if new_df['Date'].isna().sum() > len(new_df) * 0.5:
                    sample_date = str(df[column_mapping['Date']].iloc[0]) if len(df) > 0 else None
                    if sample_date:
                        sample_date = sample_date.strip().replace('"', '').replace("'", '')
                    
                    date_formats = [
                        '%m/%d/%Y', '%d/%m/%Y', '%b %d, %Y', '%B %d, %Y',
                        '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d', '%d-%m-%Y',
                        '%d %b %Y', '%b %d %Y'
                    ]
                    
                    for date_format in date_formats:
                        try:
                            clean_dates = df[column_mapping['Date']].astype(str).str.strip().str.replace('"', '').str.replace("'", '')
                            test_date = pd.to_datetime(clean_dates.iloc[0], format=date_format, errors='coerce')
                            
                            if pd.notna(test_date):
                                new_df['Date'] = pd.to_datetime(clean_dates, format=date_format, errors='coerce')
                                if new_df['Date'].notna().sum() > len(new_df) * 0.5:
                                    st.success(f"✅ Użyto formatu daty: {date_format}")
                                    break
                        except:
                            continue
            except Exception as e:
                st.warning(f"⚠️ Problem z parsowaniem dat: {str(e)}")
            
            before_count = len(new_df)
            new_df = new_df.dropna(subset=['Date'])
            if len(new_df) < before_count:
                st.warning(f"⚠️ Usunięto {before_count - len(new_df)} wierszy z nieprawidłowymi datami")
            
            # Konwertuj kolumny OHLC
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                try:
                    if new_df[col].dtype == 'object':
                        new_df[col] = new_df[col].astype(str).str.strip().str.replace('"', '').str.replace("'", '')
                        
                        sample_val = str(new_df[col].iloc[0]) if len(new_df) > 0 else "0"
                        comma_count = sample_val.count(',')
                        dot_count = sample_val.count('.')
                        
                        if comma_count > 0 and dot_count > 0:
                            last_comma_pos = sample_val.rfind(',')
                            last_dot_pos = sample_val.rfind('.')
                            
                            if last_comma_pos > last_dot_pos:
                                new_df[col] = new_df[col].str.replace('.', '').str.replace(',', '.')
                            else:
                                new_df[col] = new_df[col].str.replace(',', '')
                        elif comma_count > 0 and dot_count == 0:
                            comma_pos = sample_val.rfind(',')
                            digits_after = len(sample_val) - comma_pos - 1
                            if digits_after == 3:
                                new_df[col] = new_df[col].str.replace(',', '')
                            else:
                                new_df[col] = new_df[col].str.replace(',', '.')
                        
                        new_df[col] = new_df[col].str.replace('%', '').str.replace(' ', '').str.replace('\xa0', '')
                    
                    new_df[col] = pd.to_numeric(new_df[col], errors='coerce')
                except Exception as e:
                    st.error(f"❌ Błąd konwersji kolumny {col}: {str(e)}")
                    return None
            
            before_count = len(new_df)
            new_df = new_df.dropna(subset=['Open', 'High', 'Low', 'Close'])
            if len(new_df) < before_count:
                st.warning(f"⚠️ Usunięto {before_count - len(new_df)} wierszy z brakującymi wartościami")
            
            new_df = new_df.sort_values('Date').reset_index(drop=True)
            
            if len(new_df) == 0:
                st.error("❌ Brak prawidłowych danych")
                return None
            
            st.success(f"✅ Załadowano {len(new_df)} wierszy")
            st.info(f"📅 Okres: {new_df['Date'].min().strftime('%Y-%m-%d')} do {new_df['Date'].max().strftime('%Y-%m-%d')}")
            
            return new_df
            
        except Exception as e:
            st.error(f"❌ Błąd: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            return None
    
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

# Źródło danych
data_source = st.sidebar.radio(
    "📂 Źródło danych:",
    ["🌐 Yahoo Finance", "📥 Upload CSV"]
)

selected_symbol = None
uploaded_file = None

if data_source == "📥 Upload CSV":
    uploaded_file = st.sidebar.file_uploader("Wybierz plik CSV", type=['csv'])
    if uploaded_file:
        selected_symbol = st.sidebar.text_input("Nazwa pary:", "CUSTOM_PAIR")
else:
    major_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'GBPJPY', 'AUDUSD', 'EURPLN', 'USDPLN']
    selected_symbol = st.sidebar.selectbox("Para walutowa:", major_pairs)

# Parametry
st.sidebar.markdown("### 💰 Parametry")
initial_capital = st.sidebar.number_input("Kapitał początkowy ($)", 1000, 100000, 10000, 1000)
lot_size = st.sidebar.number_input("Wielkość lota", 0.01, 10.0, 1.0, 0.01)
spread_pips = st.sidebar.number_input("Spread (pips)", 0.0, 10.0, 2.0, 0.1)

st.sidebar.markdown("### 📅 Analiza")
if data_source == "🌐 Yahoo Finance":
    backtest_days = st.sidebar.slider("Dni historii", 30, 730, 365)
lookback_days = st.sidebar.slider("Okres pivot (dni)", 3, 14, 7)
holding_days = st.sidebar.slider("Holding period (dni)", 1, 30, 5)

# Przycisk
can_run = (uploaded_file is not None) if data_source == "📥 Upload CSV" else (selected_symbol is not None)

if st.sidebar.button("🚀 URUCHOM BACKTEST", type="primary", disabled=not can_run):
    
    backtester = PivotBacktester(lookback_days=lookback_days)
    df = None
    
    if data_source == "📥 Upload CSV":
        with st.spinner("Wczytywanie CSV..."):
            df = backtester.load_csv_data(uploaded_file)
    else:
        with st.spinner(f"Pobieranie {selected_symbol}..."):
            df = backtester.get_forex_data(selected_symbol, backtest_days)
            if df is not None:
                st.success(f"✅ Pobrano {len(df)} dni")
    
    if df is not None and len(df) > 0:
        
        with st.spinner("Obliczanie pivot points..."):
            df = backtester.calculate_pivot_points(df)
            df.attrs['symbol'] = selected_symbol
        
        pivot_data = df[df['Pivot'].notna()].copy()
        
        if len(pivot_data) > 0:
            st.success(f"✅ Pivot dla {len(pivot_data)} dni")
            
            with st.spinner("Wykonywanie backtestu..."):
                trades_df, final_capital = backtester.run_backtest(
                    df, initial_capital, lot_size, spread_pips, holding_days
                )
            
            # WYNIKI
            st.markdown("## 📈 Wyniki")
            
            col1, col2, col3, col4 = st.columns(4)
            total_return = final_capital - initial_capital
            return_pct = (total_return / initial_capital) * 100
            
            with col1:
                st.metric("Kapitał", f"${final_capital:,.2f}", f"{total_return:+,.2f}")
            with col2:
                st.metric("Zwrot", f"{return_pct:.2f}%")
            with col3:
                st.metric("Transakcje", len(trades_df))
            with col4:
                if len(trades_df) > 0:
                    win_rate = (trades_df['Profit'] > 0).sum() / len(trades_df) * 100
                    st.metric("Win Rate", f"{win_rate:.1f}%")
            
            if len(trades_df) > 0:
                
                # Statystyki per typ
                st.markdown("### 📊 Statystyki")
                col1, col2 = st.columns(2)
                
                with col1:
                    long_trades = trades_df[trades_df['Type'] == 'LONG']
                    st.markdown("**📈 LONG**")
                    st.write(f"Liczba: {len(long_trades)}")
                    if len(long_trades) > 0:
                        st.write(f"Win: {(long_trades['Profit'] > 0).sum() / len(long_trades) * 100:.1f}%")
                        st.write(f"Avg: ${long_trades['Profit'].mean():.2f}")
                        st.write(f"Total: ${long_trades['Profit'].sum():.2f}")
                
                with col2:
                    short_trades = trades_df[trades_df['Type'] == 'SHORT']
                    st.markdown("**📉 SHORT**")
                    st.write(f"Liczba: {len(short_trades)}")
                    if len(short_trades) > 0:
                        st.write(f"Win: {(short_trades['Profit'] > 0).sum() / len(short_trades) * 100:.1f}%")
                        st.write(f"Avg: ${short_trades['Profit'].mean():.2f}")
                        st.write(f"Total: ${short_trades['Profit'].sum():.2f}")
                
                # Krzywa kapitału
                st.markdown("### 💹 Krzywa kapitału")
                
                fig = go.Figure()
                capital_curve = [initial_capital] + trades_df['Capital'].tolist()
                dates_curve = [df['Date'].iloc[0]] + trades_df['Exit Date'].tolist()
                
                fig.add_trace(go.Scatter(
                    x=dates_curve, y=capital_curve,
                    mode='lines+markers', name='Kapitał',
                    line=dict(color='#1f77b4', width=2), fill='tonexty'
                ))
                
                fig.add_hline(y=initial_capital, line_dash='dash', line_color='gray')
                fig.update_layout(
                    title=f"{selected_symbol}", xaxis_title="Data",
                    yaxis_title="Kapitał ($)", height=400, hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabela
                st.markdown("### 📝 Transakcje")
                display = trades_df.copy()
                display['Entry Date'] = display['Entry Date'].dt.strftime('%Y-%m-%d')
                display['Exit Date'] = display['Exit Date'].dt.strftime('%Y-%m-%d')
                for col in ['Entry Price', 'Exit Price', 'Entry Level']:
                    display[col] = display[col].round(5)
                display['Pips'] = display['Pips'].round(1)
                display['Profit'] = display['Profit'].round(2)
                
                st.dataframe(display, use_container_width=True)
                
                csv = trades_df.to_csv(index=False)
                st.download_button("📥 CSV", csv, f"backtest_{selected_symbol}.csv", "text/csv")
            else:
                st.warning("Brak transakcji")
        else:
            st.error("Za mało danych")
    else:
        st.error("Nie udało się pobrać danych")

else:
    st.info("👈 Kliknij URUCHOM BACKTEST")

# Footer
st.markdown("---")
st.markdown(f"**🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}** | ⚠️ Tylko edukacyjnie")
