#!/usr/bin/env python3
"""
MT5 Pivot Strategy Backtester
Strategia: Kup przy S3, zamknij po X dniach
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
    .trade-buy {
        color: #28a745;
        font-weight: bold;
    }
    .trade-sell {
        color: #dc3545;
        font-weight: bold;
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
            # Spróbuj różnych separatorów i enkodingów
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
            
            # Normalizuj nazwy kolumn
            df.columns = df.columns.str.strip().str.lower().str.replace('"', '')
            
            # Mapowanie możliwych nazw kolumn
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
                st.info(f"💡 Dostępne kolumny w pliku: {', '.join(df.columns.tolist())}")
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
            
            # Konwertuj kolumny OHLC na float
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
                st.warning(f"⚠️ Usunięto {before_count - len(new_df)} wierszy z brakującymi wartościami OHLC")
            
            new_df = new_df.sort_values('Date').reset_index(drop=True)
            
            if len(new_df) == 0:
                st.error("❌ Brak prawidłowych danych po przetworzeniu")
                return None
            
            st.success(f"✅ Załadowano {len(new_df)} prawidłowych wierszy danych")
            st.info(f"📅 Okres: {new_df['Date'].min().strftime('%Y-%m-%d')} do {new_df['Date'].max().strftime('%Y-%m-%d')}")
            
            return new_df
            
        except Exception as e:
            st.error(f"❌ Błąd wczytywania CSV: {str(e)}")
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
        Uruchom backtest strategii
        Strategia: KUP gdy cena dotknie S3, ZAMKNIJ po X dniach
        """
        
        trades = []
        capital = initial_capital
        position = None
        
        for i in range(len(df)):
            row = df.iloc[i]
            
            if pd.isna(row.get('S3')) or pd.isna(row.get('R3')):
                continue
            
            current_price = row['Close']
            current_low = row['Low']
            
            # Sprawdź czy zamknąć pozycję (po X dniach)
            if position is not None:
                days_held = (row['Date'] - position['entry_date']).days
                
                if days_held >= holding_days:
                    exit_price = current_price - (spread_pips * 0.0001)
                    
                    pip_value = 0.0001
                    if 'JPY' in df.attrs.get('symbol', ''):
                        pip_value = 0.01
                    
                    pips_gained = (exit_price - position['entry_price']) / pip_value
                    profit = pips_gained * pip_value * position['lot_size'] * 100000
                    
                    capital += profit
                    
                    trades.append({
                        'Entry Date': position['entry_date'],
                        'Exit Date': row['Date'],
                        'Entry Price': position['entry_price'],
                        'Exit Price': exit_price,
                        'Entry S3': position['entry_s3'],
                        'Exit R3': row.get('R3', 0),
                        'Pips': pips_gained,
                        'Profit': profit,
                        'Capital': capital,
                        'Duration': days_held,
                        'Exit Reason': f'{holding_days}d hold'
                    })
                    
                    position = None
            
            # Otwórz nową pozycję LONG przy S3
            if position is None and current_low <= row['S3']:
                entry_price = max(current_price, row['S3']) + (spread_pips * 0.0001)
                
                position = {
                    'type': 'long',
                    'entry_date': row['Date'],
                    'entry_price': entry_price,
                    'entry_s3': row['S3'],
                    'target_r3': row['R3'],
                    'lot_size': lot_size
                }
        
        # Zamknij ostatnią pozycję
        if position is not None:
            last_row = df.iloc[-1]
            exit_price = last_row['Close'] - (spread_pips * 0.0001)
            
            pip_value = 0.0001
            if 'JPY' in df.attrs.get('symbol', ''):
                pip_value = 0.01
            
            pips_gained = (exit_price - position['entry_price']) / pip_value
            profit = pips_gained * pip_value * position['lot_size'] * 100000
            capital += profit
            
            days_held = (last_row['Date'] - position['entry_date']).days
            
            trades.append({
                'Entry Date': position['entry_date'],
                'Exit Date': last_row['Date'],
                'Entry Price': position['entry_price'],
                'Exit Price': exit_price,
                'Entry S3': position['entry_s3'],
                'Exit R3': last_row.get('R3', 0),
                'Pips': pips_gained,
                'Profit': profit,
                'Capital': capital,
                'Duration': days_held,
                'Exit Reason': 'End of data'
            })
        
        return pd.DataFrame(trades), capital

# TYTUŁ
st.title("📊 Forex Pivot Strategy Backtester")
st.markdown("**Strategia: Kup przy S3 → Zamknij po X dniach**")

# SIDEBAR
st.sidebar.header("⚙️ Konfiguracja")

data_source = st.sidebar.radio(
    "📂 Źródło danych:",
    ["📥 CSV", "🌐 Yahoo Finance"]
)

selected_symbol = None
uploaded_file = None

if data_source == "📥 CSV":
    uploaded_file = st.sidebar.file_uploader("Plik CSV", type=['csv'])
    if uploaded_file:
        selected_symbol = st.sidebar.text_input("Nazwa pary:", "CUSTOM")
else:
    major_pairs = ['EURUSD', 'GBPUSD', 'USDJPY']
    selected_symbol = st.sidebar.selectbox("Para:", major_pairs)

# Parametry
st.sidebar.markdown("### 💰 Parametry")
initial_capital = st.sidebar.number_input("Kapitał ($)", 1000, 100000, 10000, 1000)
lot_size = st.sidebar.number_input("Lot", 0.01, 10.0, 1.0, 0.01)
spread_pips = st.sidebar.number_input("Spread (pips)", 0.0, 10.0, 2.0, 0.1)

st.sidebar.markdown("### 📅 Analiza")
if data_source == "🌐 Yahoo Finance":
    backtest_days = st.sidebar.slider("Dni wstecz", 30, 730, 365)
lookback_days = st.sidebar.slider("Okres pivot", 3, 14, 7)
holding_days = st.sidebar.slider("Holding period (dni)", 1, 30, 5)

# Przycisk
can_run = (uploaded_file is not None) if data_source == "📥 CSV" else (selected_symbol is not None)

if st.sidebar.button("🚀 START", type="primary", disabled=not can_run):
    backtester = PivotBacktester(lookback_days=lookback_days)
    df = None
    
    if data_source == "📥 CSV":
        with st.spinner("Wczytywanie CSV..."):
            df = backtester.load_csv_data(uploaded_file)
    else:
        with st.spinner(f"Pobieranie {selected_symbol}..."):
            df = backtester.get_forex_data(selected_symbol, backtest_days)
            if df is not None:
                st.success(f"✅ Pobrano {len(df)} dni")
    
    if df is not None and len(df) > 0:
        with st.spinner("Obliczanie pivot..."):
            df = backtester.calculate_pivot_points(df)
            df.attrs['symbol'] = selected_symbol
        
        pivot_data = df[df['Pivot'].notna()].copy()
        if len(pivot_data) > 0:
            st.success(f"✅ Pivot: {len(pivot_data)} dni")
            
            with st.spinner("Backtest..."):
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
                # Tabela
                st.markdown("### 📝 Transakcje")
                display = trades_df.copy()
                display['Entry Date'] = display['Entry Date'].dt.strftime('%Y-%m-%d')
                display['Exit Date'] = display['Exit Date'].dt.strftime('%Y-%m-%d')
                for col in ['Entry Price', 'Exit Price', 'Entry S3', 'Exit R3']:
                    display[col] = display[col].round(5)
                display['Pips'] = display['Pips'].round(1)
                display['Profit'] = display['Profit'].round(2)
                st.dataframe(display, use_container_width=True)
                
                # Download
                csv = trades_df.to_csv(index=False)
                st.download_button(
                    "📥 CSV",
                    csv,
                    f"backtest_{selected_symbol}.csv",
                    "text/csv"
                )
            else:
                st.warning("Brak transakcji")
        else:
            st.error("Za mało danych dla pivot")
    else:
        st.error("Nie udało się pobrać danych")
else:
    st.info("👈 Skonfiguruj parametry i kliknij START")
