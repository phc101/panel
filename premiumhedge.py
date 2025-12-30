#!/usr/bin/env python3
"""
MT5 Pivot Strategy Backtester
Strategia: Poniedziałkowe sygnały + analiza roczna + prognoza
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
                                    break
                        except:
                            continue
            except Exception as e:
                st.warning(f"⚠️ Problem z parsowaniem dat: {str(e)}")
            
            new_df = new_df.dropna(subset=['Date'])
            
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
            
            new_df = new_df.dropna(subset=['Open', 'High', 'Low', 'Close'])
            new_df = new_df.sort_values('Date').reset_index(drop=True)
            
            if len(new_df) == 0:
                st.error("❌ Brak prawidłowych danych")
                return None
            
            st.success(f"✅ Załadowano {len(new_df)} wierszy")
            
            return new_df
            
        except Exception as e:
            st.error(f"❌ Błąd: {str(e)}")
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
        """Oblicz punkty pivot"""
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
    
    def run_backtest(self, df, initial_capital=10000, lot_size=1.0, spread_value=0.0002, 
                    holding_days=5, stop_loss_pct=None, support_level='S3', resistance_level='R3',
                    trade_direction='Both'):
        """Uruchom backtest strategii"""
        
        trades = []
        capital = initial_capital
        open_positions = []
        
        pip_value = 0.0001
        if 'JPY' in df.attrs.get('symbol', ''):
            pip_value = 0.01
        
        for i in range(len(df)):
            row = df.iloc[i]
            
            if pd.isna(row.get('S3')) or pd.isna(row.get('R3')):
                continue
            
            current_date = row['Date']
            current_price = row['Close']
            current_high = row['High']
            current_low = row['Low']
            
            positions_to_close = []
            
            for pos_idx, pos in enumerate(open_positions):
                
                if current_date >= pos['exit_date']:
                    positions_to_close.append((pos_idx, 'Time exit', current_price))
                    continue
                
                if stop_loss_pct is not None and stop_loss_pct > 0:
                    
                    if pos['type'] == 'long':
                        stop_loss_price = pos['entry_price'] * (1 - stop_loss_pct / 100)
                        
                        if current_low <= stop_loss_price:
                            positions_to_close.append((pos_idx, 'Stop Loss', stop_loss_price))
                            continue
                    
                    else:
                        stop_loss_price = pos['entry_price'] * (1 + stop_loss_pct / 100)
                        
                        if current_high >= stop_loss_price:
                            positions_to_close.append((pos_idx, 'Stop Loss', stop_loss_price))
                            continue
            
            for pos_idx, exit_reason, exit_price_raw in sorted(positions_to_close, reverse=True, key=lambda x: x[0]):
                pos = open_positions.pop(pos_idx)
                
                if pos['type'] == 'long':
                    exit_price = exit_price_raw - spread_value
                    pips_gained = (exit_price - pos['entry_price']) / pip_value
                    pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
                else:
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
            
            if current_date.weekday() == 0:
                
                support_value = row[support_level]
                resistance_value = row[resistance_level]
                
                if trade_direction in ['Both', 'Long Only']:
                    if current_price < support_value:
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
                
                if trade_direction in ['Both', 'Short Only']:
                    if current_price > resistance_value:
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
        
        last_row = df.iloc[-1]
        for pos in open_positions:
            
            if pos['type'] == 'long':
                exit_price = last_row['Close'] - spread_value
                pips_gained = (exit_price - pos['entry_price']) / pip_value
                pnl_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
            else:
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

def calculate_yearly_stats(trades_df, initial_capital):
    """Oblicz statystyki roczne"""
    if len(trades_df) == 0:
        return pd.DataFrame()
    
    trades_df['Year'] = trades_df['Exit Date'].dt.year
    
    yearly_stats = []
    
    for year in sorted(trades_df['Year'].unique()):
        year_trades = trades_df[trades_df['Year'] == year]
        
        # Kapitał na początek i koniec roku
        if year == trades_df['Year'].min():
            start_capital = initial_capital
        else:
            prev_year_trades = trades_df[trades_df['Year'] < year]
            if len(prev_year_trades) > 0:
                start_capital = prev_year_trades.iloc[-1]['Capital']
            else:
                start_capital = initial_capital
        
        end_capital = year_trades.iloc[-1]['Capital']
        
        # Zysk nominalny i %
        profit_nominal = end_capital - start_capital
        profit_pct = (profit_nominal / start_capital) * 100
        
        # Statystyki transakcji
        total_trades = len(year_trades)
        winning_trades = len(year_trades[year_trades['Profit'] > 0])
        losing_trades = len(year_trades[year_trades['Profit'] < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Max drawdown w roku
        year_capital = year_trades['Capital'].values
        running_max = np.maximum.accumulate(year_capital)
        drawdown = (year_capital - running_max) / running_max * 100
        max_dd = drawdown.min()
        
        # Sharpe ratio (uproszczony - dzienne zwroty)
        if len(year_trades) > 1:
            daily_returns = year_trades['Profit'].pct_change().dropna()
            if len(daily_returns) > 0 and daily_returns.std() != 0:
                sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
            else:
                sharpe = 0
        else:
            sharpe = 0
        
        yearly_stats.append({
            'Year': year,
            'Start Capital': start_capital,
            'End Capital': end_capital,
            'Profit ($)': profit_nominal,
            'Profit (%)': profit_pct,
            'Trades': total_trades,
            'Win Rate (%)': win_rate,
            'Max DD (%)': max_dd,
            'Sharpe Ratio': sharpe,
            'Total Pips': year_trades['Pips'].sum()
        })
    
    return pd.DataFrame(yearly_stats)

def calculate_projection(trades_df, initial_capital, years_ahead=5):
    """Prognoza na kolejne lata"""
    if len(trades_df) == 0:
        return None
    
    # Oblicz średnie roczne zwroty
    trades_df['Year'] = trades_df['Exit Date'].dt.year
    yearly_returns = []
    
    for year in sorted(trades_df['Year'].unique()):
        year_trades = trades_df[trades_df['Year'] == year]
        
        if year == trades_df['Year'].min():
            start_cap = initial_capital
        else:
            prev_trades = trades_df[trades_df['Year'] < year]
            start_cap = prev_trades.iloc[-1]['Capital'] if len(prev_trades) > 0 else initial_capital
        
        end_cap = year_trades.iloc[-1]['Capital']
        annual_return = (end_cap - start_cap) / start_cap
        yearly_returns.append(annual_return)
    
    # Średni roczny zwrot
    avg_annual_return = np.mean(yearly_returns)
    std_annual_return = np.std(yearly_returns)
    
    # Prognoza
    current_capital = trades_df.iloc[-1]['Capital']
    projections = []
    
    for year in range(1, years_ahead + 1):
        # Scenariusz pesymistyczny (avg - 1 std)
        pessimistic_return = avg_annual_return - std_annual_return
        pessimistic_capital = current_capital * ((1 + pessimistic_return) ** year)
        
        # Scenariusz bazowy (avg)
        base_capital = current_capital * ((1 + avg_annual_return) ** year)
        
        # Scenariusz optymistyczny (avg + 1 std)
        optimistic_return = avg_annual_return + std_annual_return
        optimistic_capital = current_capital * ((1 + optimistic_return) ** year)
        
        projections.append({
            'Year': datetime.now().year + year,
            'Pessimistic': pessimistic_capital,
            'Base': base_capital,
            'Optimistic': optimistic_capital
        })
    
    return pd.DataFrame(projections), avg_annual_return, std_annual_return

# TYTUŁ
st.title("📊 Forex Pivot Strategy Backtester")
st.markdown("**Strategia: Analiza roczna + Prognoza**")

# SIDEBAR
st.sidebar.header("⚙️ Konfiguracja")

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

st.sidebar.markdown("### 💰 Parametry")
initial_capital = st.sidebar.number_input("Kapitał początkowy ($)", 1000, 100000, 10000, 1000)
lot_size = st.sidebar.number_input("Wielkość lota", 0.01, 10.0, 1.0, 0.01)

spread_value = st.sidebar.number_input(
    "Spread (format 0.0000)", 
    min_value=0.0000,
    max_value=0.1000,
    value=0.0002,
    step=0.0001,
    format="%.4f"
)

st.sidebar.markdown("### 📅 Strategia")
if data_source == "🌐 Yahoo Finance":
    backtest_days = st.sidebar.slider("Dni historii", 365, 3650, 1825)  # do 10 lat
lookback_days = st.sidebar.slider("Okres pivot (dni)", 3, 14, 7)
holding_days = st.sidebar.slider("Holding period (dni)", 1, 30, 5)

trade_direction = st.sidebar.radio(
    "Kierunek:",
    ["Both (Long + Short)", "Long Only (Buy)", "Short Only (Sell)"],
    index=0
)

direction_map = {
    "Both (Long + Short)": "Both",
    "Long Only (Buy)": "Long Only",
    "Short Only (Sell)": "Short Only"
}
trade_direction_value = direction_map[trade_direction]

if trade_direction_value in ["Both", "Long Only"]:
    support_level = st.sidebar.radio("📉 Support:", ["S3", "S2"], index=0)
else:
    support_level = "S3"

if trade_direction_value in ["Both", "Short Only"]:
    resistance_level = st.sidebar.radio("📈 Resistance:", ["R3", "R2"], index=0)
else:
    resistance_level = "R3"

use_stop_loss = st.sidebar.checkbox("Aktywuj Stop Loss", value=False)
if use_stop_loss:
    stop_loss_pct = st.sidebar.select_slider("Stop Loss (%)", options=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0], value=1.0)
else:
    stop_loss_pct = None

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
                    df, initial_capital, lot_size, spread_value, holding_days, 
                    stop_loss_pct, support_level, resistance_level, trade_direction_value
                )
            
            # WYNIKI GŁÓWNE
            st.markdown("## 📈 Wyniki Ogólne")
            
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
                
                # ANALIZA ROCZNA
                st.markdown("## 📊 Analiza Roczna")
                
                yearly_stats = calculate_yearly_stats(trades_df, initial_capital)
                
                if len(yearly_stats) > 0:
                    # Tabela roczna
                    st.markdown("### 📅 Statystyki per rok")
                    
                    display_yearly = yearly_stats.copy()
                    display_yearly['Start Capital'] = display_yearly['Start Capital'].apply(lambda x: f"${x:,.2f}")
                    display_yearly['End Capital'] = display_yearly['End Capital'].apply(lambda x: f"${x:,.2f}")
                    display_yearly['Profit ($)'] = display_yearly['Profit ($)'].apply(lambda x: f"${x:+,.2f}")
                    display_yearly['Profit (%)'] = display_yearly['Profit (%)'].apply(lambda x: f"{x:+.2f}%")
                    display_yearly['Win Rate (%)'] = display_yearly['Win Rate (%)'].apply(lambda x: f"{x:.1f}%")
                    display_yearly['Max DD (%)'] = display_yearly['Max DD (%)'].apply(lambda x: f"{x:.2f}%")
                    display_yearly['Sharpe Ratio'] = display_yearly['Sharpe Ratio'].apply(lambda x: f"{x:.2f}")
                    display_yearly['Total Pips'] = display_yearly['Total Pips'].apply(lambda x: f"{x:.1f}")
                    
                    st.dataframe(display_yearly, use_container_width=True, hide_index=True)
                    
                    # Wykres rocznych zwrotów
                    st.markdown("### 📊 Roczne zwroty (%)")
                    
                    fig_yearly = go.Figure()
                    
                    colors = ['green' if x > 0 else 'red' for x in yearly_stats['Profit (%)']]
                    
                    fig_yearly.add_trace(go.Bar(
                        x=yearly_stats['Year'],
                        y=yearly_stats['Profit (%)'],
                        marker_color=colors,
                        text=yearly_stats['Profit (%)'].apply(lambda x: f"{x:+.1f}%"),
                        textposition='outside'
                    ))
                    
                    fig_yearly.update_layout(
                        title="Roczne zwroty procentowe",
                        xaxis_title="Rok",
                        yaxis_title="Zwrot (%)",
                        height=400,
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_yearly, use_container_width=True)
                    
                    # Wykres skumulowanego kapitału
                    st.markdown("### 💹 Skumulowany kapitał")
                    
                    fig_cum = go.Figure()
                    
                    fig_cum.add_trace(go.Scatter(
                        x=yearly_stats['Year'],
                        y=yearly_stats['End Capital'],
                        mode='lines+markers',
                        name='Kapitał',
                        line=dict(color='#1f77b4', width=3),
                        marker=dict(size=10),
                        fill='tozeroy',
                        fillcolor='rgba(31, 119, 180, 0.1)'
                    ))
                    
                    fig_cum.add_hline(y=initial_capital, line_dash='dash', line_color='gray', annotation_text='Start')
                    
                    fig_cum.update_layout(
                        title="Rozwój kapitału rok do roku",
                        xaxis_title="Rok",
                        yaxis_title="Kapitał ($)",
                        height=400
                    )
                    
                    st.plotly_chart(fig_cum, use_container_width=True)
                
                # PROGNOZA
                st.markdown("## 🔮 Prognoza 5-letnia")
                
                projection_df, avg_return, std_return = calculate_projection(trades_df, initial_capital, 5)
                
                if projection_df is not None:
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Średni roczny zwrot", f"{avg_return*100:.2f}%")
                    with col2:
                        st.metric("Odchylenie std", f"{std_return*100:.2f}%")
                    with col3:
                        final_projected = projection_df.iloc[-1]['Base']
                        projected_gain = final_projected - final_capital
                        st.metric("Prognoza za 5 lat", f"${final_projected:,.0f}", f"+${projected_gain:,.0f}")
                    
                    # Tabela prognozy
                    st.markdown("### 📋 Scenariusze prognozy")
                    
                    display_proj = projection_df.copy()
                    display_proj['Pessimistic'] = display_proj['Pessimistic'].apply(lambda x: f"${x:,.0f}")
                    display_proj['Base'] = display_proj['Base'].apply(lambda x: f"${x:,.0f}")
                    display_proj['Optimistic'] = display_proj['Optimistic'].apply(lambda x: f"${x:,.0f}")
                    
                    # Dodaj % zmiany
                    for idx in range(len(projection_df)):
                        if idx == 0:
                            base_val = final_capital
                        else:
                            base_val = projection_df.iloc[idx-1]['Base']
                        
                        pess_change = (projection_df.iloc[idx]['Pessimistic'] - base_val) / base_val * 100
                        base_change = (projection_df.iloc[idx]['Base'] - base_val) / base_val * 100
                        opt_change = (projection_df.iloc[idx]['Optimistic'] - base_val) / base_val * 100
                        
                        display_proj.at[idx, 'Pess. Change'] = f"{pess_change:+.1f}%"
                        display_proj.at[idx, 'Base Change'] = f"{base_change:+.1f}%"
                        display_proj.at[idx, 'Opt. Change'] = f"{opt_change:+.1f}%"
                    
                    st.dataframe(display_proj, use_container_width=True, hide_index=True)
                    
                    # Wykres prognozy
                    st.markdown("### 📈 Wizualizacja prognozy")
                    
                    fig_proj = go.Figure()
                    
                    # Linia historyczna
                    if len(yearly_stats) > 0:
                        fig_proj.add_trace(go.Scatter(
                            x=yearly_stats['Year'],
                            y=yearly_stats['End Capital'],
                            mode='lines+markers',
                            name='Historia',
                            line=dict(color='blue', width=3),
                            marker=dict(size=8)
                        ))
                    
                    # Dodaj aktualny punkt
                    current_year = datetime.now().year
                    fig_proj.add_trace(go.Scatter(
                        x=[current_year],
                        y=[final_capital],
                        mode='markers',
                        name='Obecny stan',
                        marker=dict(size=15, color='gold', symbol='star')
                    ))
                    
                    # Prognoza - scenariusze
                    proj_years = [current_year] + projection_df['Year'].tolist()
                    proj_base = [final_capital] + projection_df['Base'].tolist()
                    proj_pess = [final_capital] + projection_df['Pessimistic'].tolist()
                    proj_opt = [final_capital] + projection_df['Optimistic'].tolist()
                    
                    fig_proj.add_trace(go.Scatter(
                        x=proj_years,
                        y=proj_base,
                        mode='lines+markers',
                        name='Prognoza bazowa',
                        line=dict(color='green', width=2, dash='dash'),
                        marker=dict(size=6)
                    ))
                    
                    fig_proj.add_trace(go.Scatter(
                        x=proj_years,
                        y=proj_opt,
                        mode='lines',
                        name='Optymistyczna',
                        line=dict(color='lightgreen', width=1, dash='dot'),
                        fill='tonexty'
                    ))
                    
                    fig_proj.add_trace(go.Scatter(
                        x=proj_years,
                        y=proj_pess,
                        mode='lines',
                        name='Pesymistyczna',
                        line=dict(color='salmon', width=1, dash='dot')
                    ))
                    
                    fig_proj.update_layout(
                        title=f"Prognoza kapitału: {current_year}-{current_year+5}",
                        xaxis_title="Rok",
                        yaxis_title="Kapitał ($)",
                        height=500,
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig_proj, use_container_width=True)
                    
                    # Założenia prognozy
                    with st.expander("ℹ️ Założenia prognozy"):
                        st.markdown(f"""
                        **Metodologia:**
                        - Prognoza oparta na historycznych rocznych zwrotach
                        - **Średni roczny zwrot:** {avg_return*100:.2f}%
                        - **Odchylenie standardowe:** {std_return*100:.2f}%
                        
                        **Scenariusze:**
                        - **Pesymistyczny:** Średnia - 1 odchylenie std ({(avg_return - std_return)*100:.2f}% rocznie)
                        - **Bazowy:** Średnia historyczna ({avg_return*100:.2f}% rocznie)
                        - **Optymistyczny:** Średnia + 1 odchylenie std ({(avg_return + std_return)*100:.2f}% rocznie)
                        
                        ⚠️ **Uwaga:** Prognoza zakłada kontynuację historycznych wzorców. 
                        Rzeczywiste wyniki mogą się znacząco różnić.
                        """)
                
                # Szczegółowe statystyki (jak poprzednio)
                st.markdown("## 📊 Statystyki szczegółowe")
                
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
                
                if trade_direction_value in ["Both", "Short Only"] and len(short_trades) > 0:
                    with col2:
                        st.markdown(f"**📉 SHORT ({resistance_level})**")
                        st.write(f"Liczba: {len(short_trades)}")
                        short_wins = (short_trades['Profit'] > 0).sum()
                        st.write(f"Win rate: {short_wins / len(short_trades) * 100:.1f}%")
                        st.write(f"Avg profit: ${short_trades['Profit'].mean():.2f}")
                        st.write(f"Total profit: ${short_trades['Profit'].sum():.2f}")
                
                with col3:
                    st.markdown("**🛡️ EXIT**")
                    total_sl = len(trades_df[trades_df['Exit Reason'] == 'Stop Loss'])
                    time_exits = len(trades_df[trades_df['Exit Reason'] == 'Time exit'])
                    st.write(f"Stop Loss: {total_sl}")
                    st.write(f"Time exit: {time_exits}")
                
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
                
                st.dataframe(display, use_container_width=True)
                
                # Download
                csv = trades_df.to_csv(index=False)
                st.download_button(
                    "📥 Pobierz CSV",
                    csv,
                    f"backtest_{selected_symbol}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.warning("⚠️ Brak transakcji")
        else:
            st.error("❌ Za mało danych")
    else:
        st.error("❌ Nie udało się pobrać danych")

else:
    st.info("👈 Kliknij URUCHOM BACKTEST")

st.markdown("---")
st.markdown(f"**🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}** | ⚠️ Tylko edukacyjnie")
