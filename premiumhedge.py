#!/usr/bin/env python3
"""
MT5 Pivot Strategy Backtester
Strategia: Poniedziałkowe sygnały (wybór kierunku i poziomów) + holding period + stop loss
Spread: Realistyczny (LONG: entry+spread, exit-spread | SHORT: entry-spread, exit+spread)
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
    
    def run_backtest(self, df, initial_capital=10000, lot_size=1.0, spread_pips=2, 
                    holding_days=5, stop_loss_pct=None, support_level='S3', resistance_level='R3',
                    trade_direction='Both'):
        """
        Uruchom backtest strategii TYGODNIOWEJ
        
        Spread w pipsach (np. 2 pips = 0.0002 dla większości par, 0.02 dla JPY)
        - LONG: entry = price + spread, exit = price - spread
        - SHORT: entry = price - spread, exit = price + spread
        """
        
        trades = []
        capital = initial_capital
        open_positions = []
        
        # Określ wartość pipsa dla danej pary
        pip_value = 0.0001  # standardowo dla większości par
        if 'JPY' in df.attrs.get('symbol', ''):
            pip_value = 0.01  # dla par z JPY
        
        # Spread w jednostkach ceny
        spread_value = spread_pips * pip_value
        
        for i in range(len(df)):
            row = df.iloc[i]
            
            if pd.isna(row.get('S3')) or pd.isna(row.get('R3')):
                continue
            
            current_date = row['Date']
            current_price = row['Close']
            current_high = row['High']
            current_low = row['Low']
            
            # SPRAWDŹ STOP LOSS dla otwartych pozycji
            positions_to_close = []
            
            for pos_idx, pos in enumerate(open_positions):
                
                # Sprawdź czy upłynął holding period
                if current_date >= pos['exit_date']:
                    positions_to_close.append((pos_idx, 'Time exit', current_price))
                    continue
                
                # Sprawdź STOP LOSS (jeśli aktywny)
                if stop_loss_pct is not None and stop_loss_pct > 0:
                    
                    if pos['type'] == 'long':
                        stop_loss_price = pos['entry_price'] * (1 - stop_loss_pct / 100)
                        
                        if current_low <= stop_loss_price:
                            positions_to_close.append((pos_idx, 'Stop Loss', stop_loss_price))
                            continue
                    
                    else:  # short
                        stop_loss_price = pos['entry_price'] * (1 + stop_loss_pct / 100)
                        
                        if current_high >= stop_loss_price:
                            positions_to_close.append((pos_idx, 'Stop Loss', stop_loss_price))
                            continue
            
            # Zamknij pozycje
            for pos_idx, exit_reason, exit_price_raw in sorted(positions_to_close, reverse=True, key=lambda x: x[0]):
                pos = open_positions.pop(pos_idx)
                
                if pos['type'] == 'long':
                    # LONG: zamykamy po BID (odejmujemy spread)
                    exit_price = exit_price_raw - spread_value
                    pips_gained = (exit_price - pos['entry_price']) / pip_value
                    pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
                else:  # short
                    # SHORT: zamykamy po ASK (dodajemy spread)
                    exit_price = exit_price_raw + spread_value
                    pips_gained = (pos['entry_price'] - exit_price) / pip_value
                    pnl_pct = ((pos['entry_price'] - exit_price) / pos['entry_price']) * 100
                
                profit = pips_gained * pip_value * pos['lot_size'] * 100000
                capital += profit
                
                days_held = (current_date - pos['entry_date']).days
                
                trades.append({
                    'Entry Date': pos['entry_date'],
                    'Exit Date': current_date,
                    'Type': pos['type'].upper(),
                    'Entry Price': pos['entry_price'],
                    'Exit Price': exit_price,
                    'Entry Level': pos['entry_level_name'],
                    'Entry Level Value': pos['entry_level_value'],
                    'Pips': pips_gained,
                    'Profit': profit,
                    'P&L %': pnl_pct,
                    'Capital': capital,
                    'Duration': days_held,
                    'Exit Reason': exit_reason
                })
            
            # OTWIERAJ NOWE POZYCJE W PONIEDZIAŁKI
            if current_date.weekday() == 0:
                
                # Pobierz wartości wybranych poziomów
                support_value = row[support_level]
                resistance_value = row[resistance_level]
                
                # Sygnał BUY (tylko jeśli trade_direction pozwala)
                if trade_direction in ['Both', 'Long Only']:
                    if current_price < support_value:
                        # LONG: kupujemy po ASK (dodajemy spread)
                        entry_price = current_price + spread_value
                        exit_date = current_date + timedelta(days=holding_days)
                        
                        open_positions.append({
                            'type': 'long',
                            'entry_date': current_date,
                            'exit_date': exit_date,
                            'entry_price': entry_price,
                            'entry_level_name': support_level,
                            'entry_level_value': support_value,
                            'lot_size': lot_size
                        })
                
                # Sygnał SELL (tylko jeśli trade_direction pozwala)
                if trade_direction in ['Both', 'Short Only']:
                    if current_price > resistance_value:
                        # SHORT: sprzedajemy po BID (odejmujemy spread)
                        entry_price = current_price - spread_value
                        exit_date = current_date + timedelta(days=holding_days)
                        
                        open_positions.append({
                            'type': 'short',
                            'entry_date': current_date,
                            'exit_date': exit_date,
                            'entry_price': entry_price,
                            'entry_level_name': resistance_level,
                            'entry_level_value': resistance_value,
                            'lot_size': lot_size
                        })
        
        # Zamknij pozostałe pozycje na końcu
        last_row = df.iloc[-1]
        for pos in open_positions:
            
            if pos['type'] == 'long':
                # LONG: zamykamy po BID (odejmujemy spread)
                exit_price = last_row['Close'] - spread_value
                pips_gained = (exit_price - pos['entry_price']) / pip_value
                pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
            else:
                # SHORT: zamykamy po ASK (dodajemy spread)
                exit_price = last_row['Close'] + spread_value
                pips_gained = (pos['entry_price'] - exit_price) / pip_value
                pnl_pct = ((pos['entry_price'] - exit_price) / pos['entry_price']) * 100
            
            profit = pips_gained * pip_value * pos['lot_size'] * 100000
            capital += profit
            
            days_held = (last_row['Date'] - pos['entry_date']).days
            
            trades.append({
                'Entry Date': pos['entry_date'],
                'Exit Date': last_row['Date'],
                'Type': pos['type'].upper(),
                'Entry Price': pos['entry_price'],
                'Exit Price': exit_price,
                'Entry Level': pos['entry_level_name'],
                'Entry Level Value': pos['entry_level_value'],
                'Pips': pips_gained,
                'Profit': profit,
                'P&L %': pnl_pct,
                'Capital': capital,
                'Duration': days_held,
                'Exit Reason': 'End of data'
            })
        
        return pd.DataFrame(trades), capital

# TYTUŁ
st.title("📊 Forex Pivot Strategy Backtester")
st.markdown("**Strategia: Sygnały poniedziałkowe (wybór kierunku i poziomów) + holding period + stop loss**")

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
st.sidebar.markdown("### 💰 Parametry Backtestu")
initial_capital = st.sidebar.number_input("Kapitał początkowy ($)", 1000, 100000, 10000, 1000)
lot_size = st.sidebar.number_input("Wielkość lota", 0.01, 10.0, 1.0, 0.01)
spread_pips = st.sidebar.number_input(
    "Spread (pips)", 
    0.0, 10.0, 2.0, 0.1,
    help="Spread w pipsach (np. 2 = 0.0002 dla większości par, 0.02 dla JPY)"
)

# Info o spreadzie
with st.sidebar.expander("ℹ️ Jak działa spread?"):
    pip_val = 0.0001
    if selected_symbol and 'JPY' in selected_symbol:
        pip_val = 0.01
    spread_val = spread_pips * pip_val
    
    st.markdown(f"""
    **Spread: {spread_pips} pips = {spread_val:.5f}**
    
    **LONG (kupno):**
    - Entry: Cena + {spread_val:.5f} (ASK)
    - Exit: Cena - {spread_val:.5f} (BID)
    
    **SHORT (sprzedaż):**
    - Entry: Cena - {spread_val:.5f} (BID)
    - Exit: Cena + {spread_val:.5f} (ASK)
    
    💡 Spread zawsze działa **przeciwko** traderowi (koszt transakcji).
    """)

st.sidebar.markdown("### 📅 Parametry Strategii")
if data_source == "🌐 Yahoo Finance":
    backtest_days = st.sidebar.slider("Dni historii", 30, 730, 365)
lookback_days = st.sidebar.slider("Okres pivot (dni)", 3, 14, 7)
holding_days = st.sidebar.slider("Holding period (dni)", 1, 30, 5)

# WYBÓR KIERUNKU TRADINGU
st.sidebar.markdown("### 🎲 Kierunek Tradingu")
trade_direction = st.sidebar.radio(
    "Wybierz kierunek:",
    ["Both (Long + Short)", "Long Only (Buy)", "Short Only (Sell)"],
    index=0
)

# Mapowanie nazwy na wartość
direction_map = {
    "Both (Long + Short)": "Both",
    "Long Only (Buy)": "Long Only",
    "Short Only (Sell)": "Short Only"
}
trade_direction_value = direction_map[trade_direction]

# Info o kierunku
if trade_direction_value == "Both":
    st.sidebar.success("📊 Strategia dwukierunkowa")
elif trade_direction_value == "Long Only":
    st.sidebar.info("📈 Tylko pozycje LONG (kupno)")
else:
    st.sidebar.info("📉 Tylko pozycje SHORT (sprzedaż)")

# WYBÓR POZIOMÓW WEJŚCIA
st.sidebar.markdown("### 🎯 Poziomy Wejścia")

if trade_direction_value in ["Both", "Long Only"]:
    support_level = st.sidebar.radio(
        "📉 Support (LONG):",
        ["S3", "S2"],
        index=0,
        help="S3 = agresywne, S2 = konserwatywne"
    )
else:
    support_level = "S3"

if trade_direction_value in ["Both", "Short Only"]:
    resistance_level = st.sidebar.radio(
        "📈 Resistance (SHORT):",
        ["R3", "R2"],
        index=0,
        help="R3 = agresywne, R2 = konserwatywne"
    )
else:
    resistance_level = "R3"

# STOP LOSS
st.sidebar.markdown("### 🛡️ Stop Loss")
use_stop_loss = st.sidebar.checkbox("Aktywuj Stop Loss", value=False)
if use_stop_loss:
    stop_loss_pct = st.sidebar.select_slider(
        "Stop Loss (%)",
        options=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
        value=1.0
    )
else:
    stop_loss_pct = None

if use_stop_loss:
    st.sidebar.info(f"🛡️ SL aktywny: {stop_loss_pct}%")
else:
    st.sidebar.warning("⚠️ SL wyłączony")

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
            
            # Info o strategii
            if trade_direction_value == "Both":
                st.info(f"📊 **Strategia:** LONG przy {support_level} | SHORT przy {resistance_level} | Spread: {spread_pips} pips")
            elif trade_direction_value == "Long Only":
                st.info(f"📈 **Strategia:** Tylko LONG przy {support_level} | Spread: {spread_pips} pips")
            else:
                st.info(f"📉 **Strategia:** Tylko SHORT przy {resistance_level} | Spread: {spread_pips} pips")
            
            with st.spinner("Wykonywanie backtestu..."):
                trades_df, final_capital = backtester.run_backtest(
                    df, initial_capital, lot_size, spread_pips, holding_days, 
                    stop_loss_pct, support_level, resistance_level, trade_direction_value
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
                st.markdown("### 📊 Statystyki szczegółowe")
                
                long_trades = trades_df[trades_df['Type'] == 'LONG']
                short_trades = trades_df[trades_df['Type'] == 'SHORT']
                
                if trade_direction_value == "Both":
                    col1, col2, col3 = st.columns(3)
                elif trade_direction_value == "Long Only":
                    col1, col3 = st.columns(2)
                else:
                    col2, col3 = st.columns(2)
                
                if trade_direction_value in ["Both", "Long Only"] and len(long_trades) > 0:
                    with col1:
                        st.markdown(f"**📈 LONG ({support_level})**")
                        st.write(f"Liczba: {len(long_trades)}")
                        long_wins = (long_trades['Profit'] > 0).sum()
                        st.write(f"Win rate: {long_wins / len(long_trades) * 100:.1f}%")
                        st.write(f"Avg profit: ${long_trades['Profit'].mean():.2f}")
                        st.write(f"Total profit: ${long_trades['Profit'].sum():.2f}")
                        st.write(f"Avg pips: {long_trades['Pips'].mean():.1f}")
                        sl_hits = len(long_trades[long_trades['Exit Reason'] == 'Stop Loss'])
                        if sl_hits > 0:
                            st.write(f"⚠️ SL: {sl_hits} ({sl_hits/len(long_trades)*100:.1f}%)")
                
                if trade_direction_value in ["Both", "Short Only"] and len(short_trades) > 0:
                    with col2:
                        st.markdown(f"**📉 SHORT ({resistance_level})**")
                        st.write(f"Liczba: {len(short_trades)}")
                        short_wins = (short_trades['Profit'] > 0).sum()
                        st.write(f"Win rate: {short_wins / len(short_trades) * 100:.1f}%")
                        st.write(f"Avg profit: ${short_trades['Profit'].mean():.2f}")
                        st.write(f"Total profit: ${short_trades['Profit'].sum():.2f}")
                        st.write(f"Avg pips: {short_trades['Pips'].mean():.1f}")
                        sl_hits = len(short_trades[short_trades['Exit Reason'] == 'Stop Loss'])
                        if sl_hits > 0:
                            st.write(f"⚠️ SL: {sl_hits} ({sl_hits/len(short_trades)*100:.1f}%)")
                
                with col3:
                    st.markdown("**🛡️ EXIT REASONS**")
                    total_sl = len(trades_df[trades_df['Exit Reason'] == 'Stop Loss'])
                    time_exits = len(trades_df[trades_df['Exit Reason'] == 'Time exit'])
                    
                    st.write(f"Stop Loss: {total_sl}")
                    st.write(f"Time exit: {time_exits}")
                    if len(trades_df) > 0:
                        st.write(f"SL rate: {total_sl/len(trades_df)*100:.1f}%")
                    
                    # Spread cost
                    pip_val = 0.0001
                    if 'JPY' in selected_symbol:
                        pip_val = 0.01
                    total_spread_cost = len(trades_df) * 2 * spread_pips * pip_val * lot_size * 100000
                    st.write(f"💸 Spread cost: ${total_spread_cost:.2f}")
                
                # Dodatkowe statystyki
                st.markdown("### 📉 Rozkład P&L")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    avg_win = trades_df[trades_df['Profit'] > 0]['Profit'].mean() if len(trades_df[trades_df['Profit'] > 0]) > 0 else 0
                    st.metric("Średni zysk", f"${avg_win:.2f}")
                
                with col2:
                    avg_loss = trades_df[trades_df['Profit'] < 0]['Profit'].mean() if len(trades_df[trades_df['Profit'] < 0]) > 0 else 0
                    st.metric("Średnia strata", f"${avg_loss:.2f}")
                
                with col3:
                    max_dd = (trades_df['Capital'] - trades_df['Capital'].cummax()).min()
                    st.metric("Max Drawdown", f"${max_dd:.2f}")
                
                with col4:
                    total_pips = trades_df['Pips'].sum()
                    st.metric("Total Pips", f"{total_pips:.1f}")
                
                # Krzywa kapitału
                st.markdown("### 💹 Krzywa kapitału")
                
                fig = go.Figure()
                capital_curve = [initial_capital] + trades_df['Capital'].tolist()
                dates_curve = [df['Date'].iloc[0]] + trades_df['Exit Date'].tolist()
                
                fig.add_trace(go.Scatter(
                    x=dates_curve, y=capital_curve,
                    mode='lines+markers', name='Kapitał',
                    line=dict(color='#1f77b4', width=2), 
                    fill='tonexty',
                    fillcolor='rgba(31, 119, 180, 0.1)'
                ))
                
                fig.add_hline(y=initial_capital, line_dash='dash', line_color='gray', annotation_text='Start')
                
                direction_label = trade_direction_value.replace(' Only', '').replace('Both', 'Long+Short')
                fig.update_layout(
                    title=f"Rozwój kapitału - {selected_symbol} ({direction_label})",
                    xaxis_title="Data",
                    yaxis_title="Kapitał ($)",
                    height=400, 
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Histogram P&L
                st.markdown("### 📊 Histogram zysków/strat")
                
                fig_hist = go.Figure()
                
                fig_hist.add_trace(go.Histogram(
                    x=trades_df['Profit'],
                    nbinsx=30,
                    name='Wszystkie',
                    marker_color='#1f77b4',
                    opacity=0.7
                ))
                
                fig_hist.update_layout(
                    title="Rozkład profitów z transakcji",
                    xaxis_title="Profit ($)",
                    yaxis_title="Liczba transakcji",
                    height=300
                )
                
                st.plotly_chart(fig_hist, use_container_width=True)
                
                # Tabela transakcji
                st.markdown("### 📝 Historia transakcji")
                
                display = trades_df.copy()
                display['Entry Date'] = display['Entry Date'].dt.strftime('%Y-%m-%d')
                display['Exit Date'] = display['Exit Date'].dt.strftime('%Y-%m-%d')
                for col in ['Entry Price', 'Exit Price', 'Entry Level Value']:
                    display[col] = display[col].round(5)
                display['Pips'] = display['Pips'].round(1)
                display['Profit'] = display['Profit'].round(2)
                display['P&L %'] = display['P&L %'].round(2)
                
                # Pokoloruj Exit Reason
                def highlight_exit(row):
                    if row['Exit Reason'] == 'Stop Loss':
                        return ['background-color: #ffcccc'] * len(row)
                    elif row['Exit Reason'] == 'Time exit':
                        return ['background-color: #ccffcc'] * len(row)
                    return [''] * len(row)
                
                styled = display.style.apply(highlight_exit, axis=1)
                st.dataframe(styled, use_container_width=True)
                
                # Download
                csv = trades_df.to_csv(index=False)
                direction_short = trade_direction_value.replace(' Only', '').replace('Both', 'LongShort')
                st.download_button(
                    "📥 Pobierz wyniki (CSV)",
                    csv,
                    f"backtest_{selected_symbol}_{direction_short}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.warning("⚠️ Brak transakcji w wybranym okresie")
        else:
            st.error("❌ Za mało danych dla pivot points")
    else:
        st.error("❌ Nie udało się pobrać danych")

else:
    st.info("👈 Skonfiguruj parametry i kliknij 'URUCHOM BACKTEST'")
    
    st.markdown("""
    ## 📖 Strategia
    
    **Tygodniowy system sygnałów z realistycznym spreadem:**
    
    ### 💸 Spread (koszt transakcji):
    - **LONG:** Entry po ASK (+spread), Exit po BID (-spread)
    - **SHORT:** Entry po BID (-spread), Exit po ASK (+spread)
    - Spread zawsze działa **przeciwko** traderowi
    - Typowe spready: 1-3 pips (major pairs), 3-10 pips (cross/exotic)
    
    ### 🎲 Kierunek Tradingu:
    - **Both** - Pełna strategia dwukierunkowa
    - **Long Only** - Tylko kupno (bullish bias)
    - **Short Only** - Tylko sprzedaż (bearish bias)
    
    ### 🎯 Poziomy wejścia:
    - **S3/R3** = Agresywne (dalej, rzadsze sygnały)
    - **S2/R2** = Konserwatywne (bliżej, częstsze sygnały)
    
    ### 📅 Sygnały (każdy poniedziałek):
    - **LONG:** Cena < Support Level
    - **SHORT:** Cena > Resistance Level
    
    ### ⏱️ Zamknięcie:
    - **Holding period:** Auto po X dniach
    - **Stop Loss:** Opcjonalnie 0.5% - 3.0%
    
    ### 💡 Przykład spreadu:
```
    EURUSD, spread 2 pips = 0.0002
    
    LONG:
    - Cena: 1.1000
    - Entry: 1.1002 (ASK)
    - Exit: 1.1098 (BID)
    - Profit: 96 pips
    
    SHORT:
    - Cena: 1.1000
    - Entry: 1.0998 (BID)
    - Exit: 1.0902 (ASK)
    - Profit: 96 pips
```
    """)

# Footer
st.markdown("---")
st.markdown(f"""
**🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}** | 
⚠️ Tylko do celów edukacyjnych | 
📊 Yahoo Finance + CSV | 
💸 Spread: Realistyczny (ASK/BID)
""")
