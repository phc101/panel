#!/usr/bin/env python3
"""
MT5 Pivot Strategy Backtester - Multi-Currency
Strategia: Poniedziałkowe sygnały + analiza roczna + prognoza
Multi-currency: Do 5 par jednocześnie (Yahoo Finance lub CSV)
+ Management Fee + Success Fee (FULLY CORRECTED P&L IN BASE CURRENCY)
Pivot Period: 3-21 dni
Holding: 1-120 dni

POPRAWKA P&L:
- Wynik transakcji = (close - open) * wolumen = wynik w WALUCIE KWOTOWANEJ
- Kapitał jest w walucie BAZOWEJ
- Więc wynik trzeba przeliczyć: profit_base = profit_quoted / exit_price
- Przykład EURPLN: kupujesz 100k EUR po 4.21, sprzedajesz po 4.22
  → profit = 0.01 * 100,000 = 1,000 PLN (kwotowana)
  → profit w EUR = 1,000 / 4.22 = 236.97 EUR (bazowa)
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
    page_title="Forex Pivot Strategy Backtester - Multi-Currency",
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
    .fee-info {
        background: #fff3cd;
        border: 2px solid #ffc107;
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
        """Załaduj dane z pliku CSV"""
        try:
            df = None
            successful_config = None

            for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                for sep in [',', ';', '\t']:
                    try:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, sep=sep, encoding=encoding, thousands=',')
                        if len(df.columns) >= 5:
                            successful_config = f"{encoding} + sep '{sep}'"
                            break
                    except:
                        continue
                if df is not None and len(df.columns) >= 5:
                    break

            if df is None or len(df.columns) < 5:
                return None, "Nie można odczytać pliku"

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

            required = ['Date', 'Open', 'High', 'Low', 'Close']
            missing = [col for col in required if col not in column_mapping]

            if missing:
                return None, f"Brakujące kolumny: {', '.join(missing)}"

            new_df = pd.DataFrame()
            for target, source in column_mapping.items():
                new_df[target] = df[source].copy()

            try:
                new_df['Date'] = pd.to_datetime(new_df['Date'], errors='coerce')

                if new_df['Date'].isna().sum() > len(new_df) * 0.5:
                    date_formats = [
                        '%m/%d/%Y', '%d/%m/%Y', '%b %d, %Y', '%B %d, %Y',
                        '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d', '%d-%m-%Y'
                    ]

                    for date_format in date_formats:
                        try:
                            clean_dates = df[column_mapping['Date']].astype(str).str.strip()
                            new_df['Date'] = pd.to_datetime(clean_dates, format=date_format, errors='coerce')
                            if new_df['Date'].notna().sum() > len(new_df) * 0.5:
                                break
                        except:
                            continue
            except:
                pass

            new_df = new_df.dropna(subset=['Date'])

            for col in ['Open', 'High', 'Low', 'Close']:
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
                            new_df[col] = new_df[col].str.replace(',', '.')

                        new_df[col] = new_df[col].str.replace('%', '').str.replace(' ', '')

                    new_df[col] = pd.to_numeric(new_df[col], errors='coerce')
                except Exception as e:
                    return None, f"Błąd konwersji kolumny {col}"

            new_df = new_df.dropna(subset=['Open', 'High', 'Low', 'Close'])
            new_df = new_df.sort_values('Date').reset_index(drop=True)

            if len(new_df) == 0:
                return None, "Brak prawidłowych danych"

            return new_df, f"OK: {len(new_df)} wierszy"

        except Exception as e:
            return None, f"Błąd: {str(e)}"

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
                'Close': data['Close'].astype(float)
            }).reset_index(drop=True)

            df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])

            return df

        except Exception as e:
            return None

    def calculate_pivot_points(self, df):
        """Oblicz punkty pivot"""
        if len(df) < self.lookback_days:
            return df

        df = df.reset_index(drop=True)
        pivot_data = []

        for i in range(self.lookback_days, len(df)):
            window = df.iloc[i - self.lookback_days:i]
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

    def run_backtest(self, df, symbol, initial_capital=10000, volume=100000,
                     spread_value=0.0002, holding_days=5, stop_loss_pct=None,
                     support_level='S3', resistance_level='R3',
                     trade_direction='Both', leverage=1):
        """
        Uruchom backtest strategii - POPRAWIONA KALKULACJA P&L + LEVERAGE

        Logika P&L:
        - Wynik transakcji w pipsach: (exit_price - entry_price) dla long
        - Wynik w walucie KWOTOWANEJ: pips_diff * volume
          np. EURPLN: (4.22 - 4.21) * 100,000 = 1,000 PLN
        - Przeliczenie na walutę BAZOWĄ: profit_quoted / exit_price
          np. 1,000 PLN / 4.22 = 236.97 EUR

        Leverage:
        - Efektywny wolumen = volume * leverage
        - Margin (depozyt) = volume / leverage (ile kapitału blokujemy)
        - P&L liczone od efektywnego wolumenu
        - Stop loss / margin call jeśli strata > margin

        Kapitał i wyniki są w walucie BAZOWEJ pary.
        """

        trades = []
        capital = initial_capital  # w walucie bazowej
        open_positions = []
        effective_volume = volume * leverage  # wolumen z dźwignią

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

                # ============================================
                # POPRAWIONA KALKULACJA P&L + LEVERAGE
                # ============================================
                if pos['type'] == 'long':
                    exit_price = exit_price_raw - spread_value
                    price_diff = exit_price - pos['entry_price']
                else:
                    exit_price = exit_price_raw + spread_value
                    price_diff = pos['entry_price'] - exit_price

                # Wynik w walucie KWOTOWANEJ = różnica * efektywny wolumen (z dźwignią!)
                profit_quoted = price_diff * effective_volume

                # Przeliczenie na walutę BAZOWĄ
                if exit_price != 0:
                    profit_base = profit_quoted / exit_price
                else:
                    profit_base = 0

                # Margin (depozyt) = nominalna pozycja / leverage
                margin_used = volume  # nominalna pozycja bazowa bez dźwigni

                # P&L % vs margin (depozyt), nie vs cały kapitał
                pnl_pct = (profit_base / capital) * 100 if capital != 0 else 0

                # ROI on margin - zwrot na depozycie
                roi_on_margin = (profit_base / margin_used) * 100 if margin_used != 0 else 0

                # Pips
                pip_value = 0.0001
                if 'JPY' in symbol:
                    pip_value = 0.01
                pips_gained = price_diff / pip_value

                capital += profit_base

                days_held = (current_date - pos['entry_date']).days

                trades.append({
                    'Symbol': symbol,
                    'Entry Date': pos['entry_date'],
                    'Exit Date': current_date,
                    'Type': pos['type'].upper(),
                    'Entry Price': pos['entry_price'],
                    'Exit Price': exit_price,
                    'Entry Level': pos['entry_level_name'],
                    'Entry Level Value': pos['entry_level_value'],
                    'Price Diff': price_diff,
                    'Pips': pips_gained,
                    'Profit (quoted)': profit_quoted,
                    'Profit (base)': profit_base,
                    'P&L %': pnl_pct,
                    'ROI Margin %': roi_on_margin,
                    'Capital': capital,
                    'Volume': volume,
                    'Eff. Volume': effective_volume,
                    'Leverage': leverage,
                    'Duration': days_held,
                    'Exit Reason': exit_reason
                })

            # Otwieranie pozycji w poniedziałek
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
                            'volume': volume
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
                            'volume': volume
                        })

        # Zamknij otwarte pozycje na końcu danych
        last_row = df.iloc[-1]
        for pos in open_positions:

            if pos['type'] == 'long':
                exit_price = last_row['Close'] - spread_value
                price_diff = exit_price - pos['entry_price']
            else:
                exit_price = last_row['Close'] + spread_value
                price_diff = pos['entry_price'] - exit_price

            profit_quoted = price_diff * effective_volume
            if exit_price != 0:
                profit_base = profit_quoted / exit_price
            else:
                profit_base = 0

            pnl_pct = (profit_base / capital) * 100 if capital != 0 else 0

            margin_used = volume
            roi_on_margin = (profit_base / margin_used) * 100 if margin_used != 0 else 0

            pip_value = 0.0001
            if 'JPY' in symbol:
                pip_value = 0.01
            pips_gained = price_diff / pip_value

            capital += profit_base

            days_held = (last_row['Date'] - pos['entry_date']).days

            trades.append({
                'Symbol': symbol,
                'Entry Date': pos['entry_date'],
                'Exit Date': last_row['Date'],
                'Type': pos['type'].upper(),
                'Entry Price': pos['entry_price'],
                'Exit Price': exit_price,
                'Entry Level': pos['entry_level_name'],
                'Entry Level Value': pos['entry_level_value'],
                'Price Diff': price_diff,
                'Pips': pips_gained,
                'Profit (quoted)': profit_quoted,
                'Profit (base)': profit_base,
                'P&L %': pnl_pct,
                'ROI Margin %': roi_on_margin,
                'Capital': capital,
                'Volume': volume,
                'Eff. Volume': effective_volume,
                'Leverage': leverage,
                'Duration': days_held,
                'Exit Reason': 'End of data'
            })

        return pd.DataFrame(trades), capital


def calculate_yearly_stats_with_fees(trades_df, initial_capital, management_fee_pct=1.5, success_fee_pct=12.0):
    """Oblicz statystyki roczne Z FEES"""
    if len(trades_df) == 0:
        return pd.DataFrame(), pd.DataFrame()

    trades_df = trades_df.sort_values('Exit Date').reset_index(drop=True)
    trades_df['Year'] = trades_df['Exit Date'].dt.year

    yearly_stats_before_fees = []
    yearly_stats_after_fees = []

    capital_after_fees_tracking = initial_capital

    for year in sorted(trades_df['Year'].unique()):
        year_trades = trades_df[trades_df['Year'] == year]

        # PRZED FEES
        if year == trades_df['Year'].min():
            start_capital_before = initial_capital
        else:
            prev_year_trades = trades_df[trades_df['Year'] < year]
            if len(prev_year_trades) > 0:
                start_capital_before = prev_year_trades.iloc[-1]['Portfolio Capital']
            else:
                start_capital_before = initial_capital

        end_capital_before = year_trades.iloc[-1]['Portfolio Capital']
        profit_before = end_capital_before - start_capital_before
        profit_pct_before = (profit_before / start_capital_before) * 100 if start_capital_before != 0 else 0

        # PO FEES
        start_capital_after = capital_after_fees_tracking

        management_fee = start_capital_after * (management_fee_pct / 100)
        capital_after_mgmt_fee = start_capital_after - management_fee

        return_pct_this_year = profit_before / start_capital_before if start_capital_before != 0 else 0
        profit_after_mgmt_fee = capital_after_mgmt_fee * return_pct_this_year

        capital_before_success_fee = capital_after_mgmt_fee + profit_after_mgmt_fee

        if profit_after_mgmt_fee > 0:
            success_fee = profit_after_mgmt_fee * (success_fee_pct / 100)
        else:
            success_fee = 0

        total_fees = management_fee + success_fee

        end_capital_after = capital_before_success_fee - success_fee
        profit_after = end_capital_after - start_capital_after
        profit_pct_after = (profit_after / start_capital_after) * 100 if start_capital_after != 0 else 0

        capital_after_fees_tracking = end_capital_after

        # Statystyki
        total_trades = len(year_trades)
        winning_trades = len(year_trades[year_trades['Profit (base)'] > 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        year_capital_series = year_trades['Portfolio Capital'].values
        running_max = np.maximum.accumulate(year_capital_series)
        drawdown = (year_capital_series - running_max) / running_max * 100
        max_dd_before = drawdown.min() if len(drawdown) > 0 else 0

        fee_ratio = end_capital_after / end_capital_before if end_capital_before != 0 else 1
        year_capital_after_fees_sim = year_capital_series * fee_ratio
        running_max_after = np.maximum.accumulate(year_capital_after_fees_sim)
        drawdown_after = (year_capital_after_fees_sim - running_max_after) / running_max_after * 100
        max_dd_after = drawdown_after.min() if len(drawdown_after) > 0 else 0

        if len(year_trades) > 1:
            returns = year_trades['P&L %'].values / 100
            if len(returns) > 0 and returns.std() != 0:
                sharpe = (returns.mean() / returns.std()) * np.sqrt(len(returns))
            else:
                sharpe = 0
        else:
            sharpe = 0

        yearly_stats_before_fees.append({
            'Year': year,
            'Start Capital': start_capital_before,
            'End Capital': end_capital_before,
            'Profit (base)': profit_before,
            'Profit (%)': profit_pct_before,
            'Trades': total_trades,
            'Win Rate (%)': win_rate,
            'Max DD (%)': max_dd_before,
            'Sharpe Ratio': sharpe,
            'Total Pips': year_trades['Pips'].sum()
        })

        yearly_stats_after_fees.append({
            'Year': year,
            'Start Capital': start_capital_after,
            'Management Fee': management_fee,
            'After Mgmt Fee': capital_after_mgmt_fee,
            'Trading Profit': profit_after_mgmt_fee,
            'Before Success Fee': capital_before_success_fee,
            'Success Fee': success_fee,
            'End Capital': end_capital_after,
            'Total Fees': total_fees,
            'Net Profit (base)': profit_after,
            'Net Profit (%)': profit_pct_after,
            'Trades': total_trades,
            'Win Rate (%)': win_rate,
            'Max DD (%)': max_dd_after,
            'Sharpe Ratio': sharpe,
            'Total Pips': year_trades['Pips'].sum()
        })

    return pd.DataFrame(yearly_stats_before_fees), pd.DataFrame(yearly_stats_after_fees)


def calculate_projection(trades_df, initial_capital, years_ahead=5):
    """Prognoza na kolejne lata"""
    if len(trades_df) == 0:
        return None, 0, 0

    trades_df = trades_df.sort_values('Exit Date').reset_index(drop=True)
    trades_df['Year'] = trades_df['Exit Date'].dt.year

    yearly_returns = []

    for year in sorted(trades_df['Year'].unique()):
        year_trades = trades_df[trades_df['Year'] == year]

        if year == trades_df['Year'].min():
            start_cap = initial_capital
        else:
            prev_trades = trades_df[trades_df['Year'] < year]
            start_cap = prev_trades.iloc[-1]['Portfolio Capital'] if len(prev_trades) > 0 else initial_capital

        end_cap = year_trades.iloc[-1]['Portfolio Capital']
        annual_return = (end_cap - start_cap) / start_cap
        yearly_returns.append(annual_return)

    avg_annual_return = np.mean(yearly_returns)
    std_annual_return = np.std(yearly_returns) if len(yearly_returns) > 1 else 0

    current_capital = trades_df.iloc[-1]['Portfolio Capital']
    projections = []

    for year in range(1, years_ahead + 1):
        pessimistic_return = avg_annual_return - std_annual_return
        pessimistic_capital = current_capital * ((1 + pessimistic_return) ** year)

        base_capital = current_capital * ((1 + avg_annual_return) ** year)

        optimistic_return = avg_annual_return + std_annual_return
        optimistic_capital = current_capital * ((1 + optimistic_return) ** year)

        projections.append({
            'Year': datetime.now().year + year,
            'Pessimistic': pessimistic_capital,
            'Base': base_capital,
            'Optimistic': optimistic_capital
        })

    return pd.DataFrame(projections), avg_annual_return, std_annual_return


# ============================================
# STREAMLIT UI
# ============================================

st.title("📊 Forex Pivot Strategy Backtester - Multi-Currency")
st.markdown("**P&L w walucie BAZOWEJ | Leverage x1-x20 | Hold 1-120d**")

# SIDEBAR
st.sidebar.header("⚙️ Konfiguracja")

data_source = st.sidebar.radio(
    "📂 Źródło danych:",
    ["🌐 Yahoo Finance", "📥 Upload CSV (do 5 plików)"]
)

selected_symbols = []
csv_files = {}

if data_source == "📥 Upload CSV (do 5 plików)":
    st.sidebar.markdown("### 📤 Upload plików CSV")

    num_files = st.sidebar.number_input("Liczba par", min_value=1, max_value=5, value=1, step=1)

    for i in range(num_files):
        st.sidebar.markdown(f"**Para #{i + 1}:**")

        col1, col2 = st.sidebar.columns([2, 1])

        with col1:
            uploaded_file = st.file_uploader(
                f"Plik CSV #{i + 1}",
                type=['csv'],
                key=f"csv_upload_{i}"
            )

        with col2:
            symbol_name = st.text_input(
                f"Nazwa",
                value=f"PAIR{i + 1}",
                key=f"symbol_name_{i}"
            )

        if uploaded_file is not None:
            csv_files[symbol_name] = uploaded_file
            if symbol_name not in selected_symbols:
                selected_symbols.append(symbol_name)

    if len(csv_files) > 0:
        st.sidebar.success(f"✅ Załadowano: {len(csv_files)} plików CSV")
    else:
        st.sidebar.warning("⚠️ Wgraj co najmniej 1 plik CSV")

else:
    st.sidebar.markdown("### 💱 Wybór par walutowych")

    available_pairs = list(FOREX_SYMBOLS.keys())

    selected_symbols = st.sidebar.multiselect(
        "Wybierz pary (max 5):",
        available_pairs,
        default=['EURUSD'],
        max_selections=5
    )

    if len(selected_symbols) > 0:
        st.sidebar.success(f"✅ Wybrano: {len(selected_symbols)} par")
    else:
        st.sidebar.warning("⚠️ Wybierz co najmniej 1 parę")

st.sidebar.markdown("### 💰 Parametry")

initial_capital = st.sidebar.number_input(
    "Kapitał początkowy (waluta bazowa)",
    min_value=1000,
    value=10000,
    step=1000,
    format="%d",
    help="Kapitał w walucie BAZOWEJ pary (np. EUR dla EURPLN)"
)

volume = st.sidebar.number_input(
    "Wolumen (jednostki waluty bazowej)",
    min_value=1000,
    max_value=10000000,
    value=100000,
    step=10000,
    format="%d",
    help="Ile jednostek waluty bazowej kupujesz/sprzedajesz (np. 100,000 EUR)"
)

leverage = st.sidebar.select_slider(
    "⚡ Leverage (dźwignia)",
    options=[1, 5, 10, 15, 20],
    value=1,
    help="Mnożnik dźwigni. x10 = kontrolujesz 10× więcej niż depozyt"
)

effective_volume_display = volume * leverage
margin_display = volume  # depozyt = nominalna pozycja

if leverage > 1:
    st.sidebar.warning(
        f"⚡ **Leverage x{leverage}**\n\n"
        f"Nominalna pozycja: {volume:,}\n\n"
        f"Efektywny wolumen: **{effective_volume_display:,}**\n\n"
        f"⚠️ Zyski i straty × {leverage}"
    )
else:
    st.sidebar.info(f"Wolumen: {volume:,} (bez dźwigni)")

spread_value = st.sidebar.number_input(
    "Spread (format 0.0000)",
    min_value=0.0000,
    max_value=0.1000,
    value=0.0002,
    step=0.0001,
    format="%.4f"
)

st.sidebar.markdown("### 💸 Fee Structure")
management_fee_pct = st.sidebar.number_input(
    "Management Fee (%/rok)",
    min_value=0.0,
    max_value=5.0,
    value=1.5,
    step=0.1,
    help="Pobierany NA POCZĄTKU każdego roku z rzeczywistego kapitału"
)

success_fee_pct = st.sidebar.number_input(
    "Success Fee (% od zysku)",
    min_value=0.0,
    max_value=50.0,
    value=12.0,
    step=1.0,
    help="Pobierany NA KOŃCU roku tylko od wygenerowanego zysku"
)

st.sidebar.info(f"💡 Mgmt: {management_fee_pct}% (start) + Success: {success_fee_pct}% (end)")

st.sidebar.markdown("### 📅 Strategia")
if data_source == "🌐 Yahoo Finance":
    backtest_days = st.sidebar.slider("Dni historii", 365, 3650, 1825)

lookback_days = st.sidebar.slider(
    "Okres pivot (dni)",
    min_value=3,
    max_value=21,
    value=7,
    help="Liczba dni do obliczania średnich dla pivot points (3-21)"
)

holding_days = st.sidebar.slider(
    "Holding period (dni)",
    min_value=1,
    max_value=120,  # WYDŁUŻONE do 120
    value=5,
    help="Ile dni trzymamy pozycję (1-120)"
)

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

can_run = len(selected_symbols) > 0

if st.sidebar.button("🚀 URUCHOM BACKTEST", type="primary", disabled=not can_run):

    backtester = PivotBacktester(lookback_days=lookback_days)

    capital_per_pair = initial_capital / len(selected_symbols)

    all_trades = []
    results_per_symbol = {}

    if data_source == "📥 Upload CSV (do 5 plików)":
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, (symbol, uploaded_file) in enumerate(csv_files.items()):
            status_text.text(f"Przetwarzam {symbol}... ({idx + 1}/{len(csv_files)})")

            df, load_status = backtester.load_csv_data(uploaded_file)

            if df is not None and len(df) > 0:
                st.info(f"✅ {symbol}: {load_status}")

                df = backtester.calculate_pivot_points(df)

                trades_df, final_cap = backtester.run_backtest(
                    df, symbol, capital_per_pair, volume, spread_value,
                    holding_days, stop_loss_pct, support_level, resistance_level, trade_direction_value,
                    leverage
                )

                all_trades.append(trades_df)
                results_per_symbol[symbol] = {
                    'trades': trades_df,
                    'final_capital': final_cap,
                    'initial_capital': capital_per_pair
                }
            else:
                st.error(f"❌ {symbol}: {load_status}")

            progress_bar.progress((idx + 1) / len(csv_files))

        status_text.empty()
        progress_bar.empty()

    else:
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, symbol in enumerate(selected_symbols):
            status_text.text(f"Przetwarzam {symbol}... ({idx + 1}/{len(selected_symbols)})")

            df = backtester.get_forex_data(symbol, backtest_days)

            if df is not None and len(df) > 0:
                df = backtester.calculate_pivot_points(df)

                trades_df, final_cap = backtester.run_backtest(
                    df, symbol, capital_per_pair, volume, spread_value,
                    holding_days, stop_loss_pct, support_level, resistance_level, trade_direction_value,
                    leverage
                )

                all_trades.append(trades_df)
                results_per_symbol[symbol] = {
                    'trades': trades_df,
                    'final_capital': final_cap,
                    'initial_capital': capital_per_pair
                }
            else:
                st.warning(f"⚠️ Nie udało się pobrać danych dla {symbol}")

            progress_bar.progress((idx + 1) / len(selected_symbols))

        status_text.empty()
        progress_bar.empty()

    if len(all_trades) > 0:
        combined_trades = pd.concat(all_trades, ignore_index=True)
        combined_trades = combined_trades.sort_values('Exit Date').reset_index(drop=True)

        # Portfolio capital tracking
        combined_trades['Portfolio Capital'] = initial_capital
        for i in range(len(combined_trades)):
            if i > 0:
                combined_trades.at[i, 'Portfolio Capital'] = combined_trades.at[i - 1, 'Portfolio Capital'] + \
                                                              combined_trades.at[i, 'Profit (base)']
            else:
                combined_trades.at[0, 'Portfolio Capital'] = initial_capital + combined_trades.at[0, 'Profit (base)']

        final_portfolio_capital = combined_trades.iloc[-1]['Portfolio Capital']

        # ============================================
        # INFO BOX: P&L EXPLANATION
        # ============================================
        st.markdown("## ℹ️ Logika kalkulacji P&L")
        leverage_text = f" × leverage x{leverage} = **{volume * leverage:,}**" if leverage > 1 else ""
        st.markdown(f"""
        <div class="fee-info">
        <b>KALKULACJA P&L (waluta bazowa) + LEVERAGE:</b><br>
        1. Różnica kursowa: <code>exit_price - entry_price</code> (long) lub odwrotnie (short)<br>
        2. Efektywny wolumen: <code>{volume:,}{' × ' + str(leverage) + ' = ' + f'{volume*leverage:,}' if leverage > 1 else ''}</code><br>
        3. Wynik w walucie <b>kwotowanej</b>: <code>różnica × efektywny wolumen</code><br>
        4. Przeliczenie na walutę <b>bazową</b>: <code>wynik_kwotowany / kurs_zamknięcia</code><br><br>
        <b>Przykład EURPLN (wolumen {volume:,}, leverage x{leverage}):</b><br>
        Long entry: 4.2100, exit: 4.2200, efektywny wolumen: {volume*leverage:,}<br>
        → Wynik PLN = 0.0100 × {volume*leverage:,} = <b>{0.01 * volume * leverage:,.0f} PLN</b><br>
        → Wynik EUR = {0.01 * volume * leverage:,.0f} / 4.2200 = <b>{0.01 * volume * leverage / 4.22:,.2f} EUR</b><br><br>
        {'⚡ <b>UWAGA: Leverage x' + str(leverage) + ' oznacza ' + str(leverage) + '× większe zyski ALE też ' + str(leverage) + '× większe straty!</b><br>' if leverage > 1 else ''}
        Kapitał i wyniki w <b>walucie bazowej</b> pary.
        </div>
        """, unsafe_allow_html=True)

        # WYNIKI ZBIORCZE
        st.markdown(f"## 📊 Podsumowanie Portfolio (przed fees) {'| ⚡ Leverage x' + str(leverage) if leverage > 1 else ''}")

        col1, col2, col3, col4, col5 = st.columns(5)

        total_return_before = final_portfolio_capital - initial_capital
        return_pct_before = (total_return_before / initial_capital) * 100

        with col1:
            st.metric("Kapitał końcowy (base)", f"{final_portfolio_capital:,.2f}", f"{total_return_before:+,.2f}")
        with col2:
            st.metric("Zwrot %", f"{return_pct_before:.2f}%")
        with col3:
            st.metric("Leverage", f"x{leverage}")
        with col4:
            st.metric("Liczba par", len(results_per_symbol))
        with col5:
            st.metric("Łączne transakcje", len(combined_trades))

        # FEES
        st.markdown("## 💸 Analiza Fees")

        yearly_before, yearly_after = calculate_yearly_stats_with_fees(
            combined_trades, initial_capital, management_fee_pct, success_fee_pct
        )

        if len(yearly_after) > 0:
            total_management_fees = yearly_after['Management Fee'].sum()
            total_success_fees = yearly_after['Success Fee'].sum()
            total_fees = yearly_after['Total Fees'].sum()

            final_capital_after_fees = yearly_after.iloc[-1]['End Capital']
            total_return_after = final_capital_after_fees - initial_capital
            return_pct_after = (total_return_after / initial_capital) * 100

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("💰 Management Fees", f"{total_management_fees:,.2f}")
            with col2:
                st.metric("🎯 Success Fees", f"{total_success_fees:,.2f}")
            with col3:
                st.metric("💸 Total Fees", f"{total_fees:,.2f}")
            with col4:
                fees_pct = (total_fees / final_portfolio_capital) * 100 if final_portfolio_capital != 0 else 0
                st.metric("Fees % kapitału", f"{fees_pct:.2f}%")

            # PORÓWNANIE
            st.markdown("## 📊 Kapitał: Przed vs Po Fees")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 🟢 Przed Fees")
                st.metric("Kapitał końcowy", f"{final_portfolio_capital:,.2f}")
                st.metric("Zwrot", f"{total_return_before:+,.2f}")
                st.metric("Zwrot %", f"{return_pct_before:+.2f}%")

            with col2:
                st.markdown("### 🔴 Po Fees")
                st.metric("Kapitał końcowy", f"{final_capital_after_fees:,.2f}")
                st.metric("Zwrot", f"{total_return_after:+,.2f}")
                st.metric("Zwrot %", f"{return_pct_after:+.2f}%")

            difference = final_portfolio_capital - final_capital_after_fees
            impact_pct = (difference / final_portfolio_capital) * 100 if final_portfolio_capital != 0 else 0
            st.error(f"💵 **Fees Impact:** {difference:,.2f} ({impact_pct:.2f}% kapitału przed fees)")

            # Fee Flow
            if len(yearly_after) > 0:
                st.markdown("### 💸 Fee Flow (przykład pierwszego roku)")
                example_year = yearly_after.iloc[0]

                col1, col2, col3, col4, col5 = st.columns(5)

                with col1:
                    st.metric("1️⃣ Start", f"{example_year['Start Capital']:,.0f}")
                with col2:
                    st.metric("2️⃣ - Mgmt Fee", f"-{example_year['Management Fee']:,.0f}", delta_color="inverse")
                with col3:
                    st.metric("3️⃣ Trading", f"+{example_year['Trading Profit']:,.0f}")
                with col4:
                    st.metric("4️⃣ - Success Fee", f"-{example_year['Success Fee']:,.0f}", delta_color="inverse")
                with col5:
                    st.metric("5️⃣ End → Next", f"{example_year['End Capital']:,.0f}")

        # WYNIKI PER PARA
        st.markdown("## 💱 Wyniki per para")

        summary_data = []

        for symbol, result in results_per_symbol.items():
            trades = result['trades']
            final_cap = result['final_capital']
            initial_cap = result['initial_capital']

            if len(trades) > 0:
                profit = final_cap - initial_cap
                profit_pct = (profit / initial_cap) * 100
                win_rate = (trades['Profit (base)'] > 0).sum() / len(trades) * 100
                total_pips = trades['Pips'].sum()
                total_profit_quoted = trades['Profit (quoted)'].sum()
                total_profit_base = trades['Profit (base)'].sum()
                avg_holding = trades['Duration'].mean()

                summary_data.append({
                    'Symbol': symbol,
                    'Initial Capital': initial_cap,
                    'Final Capital': final_cap,
                    'Profit (base)': profit,
                    'Profit (%)': profit_pct,
                    'Total P&L (quoted)': total_profit_quoted,
                    'Total P&L (base)': total_profit_base,
                    'Trades': len(trades),
                    'Win Rate (%)': win_rate,
                    'Total Pips': total_pips,
                    'Avg Holding (days)': avg_holding
                })

        summary_df = pd.DataFrame(summary_data)

        if len(summary_df) > 0:
            display_summary = summary_df.copy()
            display_summary['Initial Capital'] = display_summary['Initial Capital'].apply(lambda x: f"{x:,.2f}")
            display_summary['Final Capital'] = display_summary['Final Capital'].apply(lambda x: f"{x:,.2f}")
            display_summary['Profit (base)'] = display_summary['Profit (base)'].apply(lambda x: f"{x:+,.2f}")
            display_summary['Profit (%)'] = display_summary['Profit (%)'].apply(lambda x: f"{x:+.2f}%")
            display_summary['Total P&L (quoted)'] = display_summary['Total P&L (quoted)'].apply(
                lambda x: f"{x:+,.2f}")
            display_summary['Total P&L (base)'] = display_summary['Total P&L (base)'].apply(lambda x: f"{x:+,.2f}")
            display_summary['Win Rate (%)'] = display_summary['Win Rate (%)'].apply(lambda x: f"{x:.1f}%")
            display_summary['Total Pips'] = display_summary['Total Pips'].apply(lambda x: f"{x:.1f}")
            display_summary['Avg Holding (days)'] = display_summary['Avg Holding (days)'].apply(lambda x: f"{x:.1f}")

            st.dataframe(display_summary, use_container_width=True, hide_index=True)

            # Wykres porównawczy
            st.markdown("### 📊 Porównanie zwrotów per para")

            fig_comparison = go.Figure()

            colors = ['green' if x > 0 else 'red' for x in summary_df['Profit (%)']]

            fig_comparison.add_trace(go.Bar(
                x=summary_df['Symbol'],
                y=summary_df['Profit (%)'],
                marker_color=colors,
                text=summary_df['Profit (%)'].apply(lambda x: f"{x:+.1f}%"),
                textposition='outside'
            ))

            fig_comparison.update_layout(
                title="Zwrot % per para (waluta bazowa)",
                xaxis_title="Para",
                yaxis_title="Zwrot (%)",
                height=400,
                showlegend=False
            )

            st.plotly_chart(fig_comparison, use_container_width=True)

            # Krzywa kapitału
            st.markdown("### 💹 Krzywa kapitału portfolio")

            fig_portfolio = go.Figure()

            fig_portfolio.add_trace(go.Scatter(
                x=combined_trades['Exit Date'],
                y=combined_trades['Portfolio Capital'],
                mode='lines',
                name='Portfolio (przed fees)',
                line=dict(color='blue', width=2),
                fill='tonexty',
                fillcolor='rgba(31, 119, 180, 0.1)'
            ))

            fig_portfolio.add_hline(y=initial_capital, line_dash='dash', line_color='gray',
                                    annotation_text='Start')

            fig_portfolio.update_layout(
                title=f"Rozwój kapitału ({len(selected_symbols)} par) - Pivot {lookback_days}d, Hold {holding_days}d, Lev x{leverage}",
                xaxis_title="Data",
                yaxis_title="Kapitał (waluta bazowa)",
                height=500,
                hovermode='x unified'
            )

            st.plotly_chart(fig_portfolio, use_container_width=True)

            # ANALIZA ROCZNA
            st.markdown("## 📅 Analiza roczna portfolio")

            tab1, tab2 = st.tabs(["🟢 Przed Fees", "🔴 Po Fees"])

            with tab1:
                st.markdown("### Statystyki roczne (przed fees)")

                if len(yearly_before) > 0:
                    display_yearly_before = yearly_before.copy()
                    display_yearly_before['Start Capital'] = display_yearly_before['Start Capital'].apply(
                        lambda x: f"{x:,.2f}")
                    display_yearly_before['End Capital'] = display_yearly_before['End Capital'].apply(
                        lambda x: f"{x:,.2f}")
                    display_yearly_before['Profit (base)'] = display_yearly_before['Profit (base)'].apply(
                        lambda x: f"{x:+,.2f}")
                    display_yearly_before['Profit (%)'] = display_yearly_before['Profit (%)'].apply(
                        lambda x: f"{x:+.2f}%")
                    display_yearly_before['Win Rate (%)'] = display_yearly_before['Win Rate (%)'].apply(
                        lambda x: f"{x:.1f}%")
                    display_yearly_before['Max DD (%)'] = display_yearly_before['Max DD (%)'].apply(
                        lambda x: f"{x:.2f}%")
                    display_yearly_before['Sharpe Ratio'] = display_yearly_before['Sharpe Ratio'].apply(
                        lambda x: f"{x:.2f}")
                    display_yearly_before['Total Pips'] = display_yearly_before['Total Pips'].apply(
                        lambda x: f"{x:.1f}")

                    st.dataframe(display_yearly_before, use_container_width=True, hide_index=True)

                    fig_yearly_before = go.Figure()
                    colors_before = ['green' if x > 0 else 'red' for x in yearly_before['Profit (%)']]

                    fig_yearly_before.add_trace(go.Bar(
                        x=yearly_before['Year'],
                        y=yearly_before['Profit (%)'],
                        marker_color=colors_before,
                        text=yearly_before['Profit (%)'].apply(lambda x: f"{x:+.1f}%"),
                        textposition='outside'
                    ))

                    fig_yearly_before.update_layout(
                        title="Roczne zwroty (przed fees)",
                        xaxis_title="Rok",
                        yaxis_title="Zwrot (%)",
                        height=400
                    )

                    st.plotly_chart(fig_yearly_before, use_container_width=True)

            with tab2:
                st.markdown("### Statystyki roczne (po fees)")

                if len(yearly_after) > 0:
                    display_yearly_after = yearly_after.copy()
                    display_yearly_after['Start Capital'] = display_yearly_after['Start Capital'].apply(
                        lambda x: f"{x:,.2f}")
                    display_yearly_after['Management Fee'] = display_yearly_after['Management Fee'].apply(
                        lambda x: f"{x:,.2f}")
                    display_yearly_after['After Mgmt Fee'] = display_yearly_after['After Mgmt Fee'].apply(
                        lambda x: f"{x:,.2f}")
                    display_yearly_after['Trading Profit'] = display_yearly_after['Trading Profit'].apply(
                        lambda x: f"{x:+,.2f}")
                    display_yearly_after['Before Success Fee'] = display_yearly_after['Before Success Fee'].apply(
                        lambda x: f"{x:,.2f}")
                    display_yearly_after['Success Fee'] = display_yearly_after['Success Fee'].apply(
                        lambda x: f"{x:,.2f}")
                    display_yearly_after['End Capital'] = display_yearly_after['End Capital'].apply(
                        lambda x: f"{x:,.2f}")
                    display_yearly_after['Total Fees'] = display_yearly_after['Total Fees'].apply(
                        lambda x: f"{x:,.2f}")
                    display_yearly_after['Net Profit (base)'] = display_yearly_after['Net Profit (base)'].apply(
                        lambda x: f"{x:+,.2f}")
                    display_yearly_after['Net Profit (%)'] = display_yearly_after['Net Profit (%)'].apply(
                        lambda x: f"{x:+.2f}%")
                    display_yearly_after['Win Rate (%)'] = display_yearly_after['Win Rate (%)'].apply(
                        lambda x: f"{x:.1f}%")
                    display_yearly_after['Max DD (%)'] = display_yearly_after['Max DD (%)'].apply(
                        lambda x: f"{x:.2f}%")
                    display_yearly_after['Sharpe Ratio'] = display_yearly_after['Sharpe Ratio'].apply(
                        lambda x: f"{x:.2f}")
                    display_yearly_after['Total Pips'] = display_yearly_after['Total Pips'].apply(
                        lambda x: f"{x:.1f}")

                    st.dataframe(display_yearly_after, use_container_width=True, hide_index=True)

                    st.success("✅ **Start Capital w roku N = End Capital z roku N-1** (fees odejmowane!)")

                    fig_yearly_after = go.Figure()
                    colors_after = ['green' if x > 0 else 'red' for x in yearly_after['Net Profit (%)']]

                    fig_yearly_after.add_trace(go.Bar(
                        x=yearly_after['Year'],
                        y=yearly_after['Net Profit (%)'],
                        marker_color=colors_after,
                        text=yearly_after['Net Profit (%)'].apply(lambda x: f"{x:+.1f}%"),
                        textposition='outside'
                    ))

                    fig_yearly_after.update_layout(
                        title="Roczne zwroty netto (po fees)",
                        xaxis_title="Rok",
                        yaxis_title="Zwrot Netto (%)",
                        height=400
                    )

                    st.plotly_chart(fig_yearly_after, use_container_width=True)

                    # Fees breakdown
                    st.markdown("### 💸 Szczegóły fees per rok")

                    fig_fees = go.Figure()

                    fig_fees.add_trace(go.Bar(
                        x=yearly_after['Year'],
                        y=yearly_after['Management Fee'],
                        name='Management Fee (start)',
                        marker_color='orange'
                    ))

                    fig_fees.add_trace(go.Bar(
                        x=yearly_after['Year'],
                        y=yearly_after['Success Fee'],
                        name='Success Fee (end)',
                        marker_color='red'
                    ))

                    fig_fees.update_layout(
                        title="Breakdown fees per rok",
                        xaxis_title="Rok",
                        yaxis_title="Fees (waluta bazowa)",
                        barmode='stack',
                        height=400
                    )

                    st.plotly_chart(fig_fees, use_container_width=True)

            # PROGNOZA
            st.markdown("## 🔮 Prognoza 5-letnia (przed fees)")

            projection_df, avg_return, std_return = calculate_projection(combined_trades, initial_capital, 5)

            if projection_df is not None:

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Średni roczny zwrot", f"{avg_return * 100:.2f}%")
                with col2:
                    st.metric("Odchylenie std", f"{std_return * 100:.2f}%")
                with col3:
                    final_projected = projection_df.iloc[-1]['Base']
                    projected_gain = final_projected - final_portfolio_capital
                    st.metric("Prognoza za 5 lat", f"{final_projected:,.0f}", f"+{projected_gain:,.0f}")

                st.warning("⚠️ **Prognoza pokazuje zwroty PRZED fees.**")

                fig_proj = go.Figure()

                if len(yearly_before) > 0:
                    fig_proj.add_trace(go.Scatter(
                        x=yearly_before['Year'],
                        y=yearly_before['End Capital'],
                        mode='lines+markers',
                        name='Historia (przed fees)',
                        line=dict(color='blue', width=3)
                    ))

                current_year = datetime.now().year
                proj_years = [current_year] + projection_df['Year'].tolist()
                proj_base = [final_portfolio_capital] + projection_df['Base'].tolist()
                proj_pess = [final_portfolio_capital] + projection_df['Pessimistic'].tolist()
                proj_opt = [final_portfolio_capital] + projection_df['Optimistic'].tolist()

                fig_proj.add_trace(go.Scatter(
                    x=proj_years, y=proj_base,
                    mode='lines+markers', name='Prognoza bazowa',
                    line=dict(color='green', width=2, dash='dash')
                ))

                fig_proj.add_trace(go.Scatter(
                    x=proj_years, y=proj_opt,
                    mode='lines', name='Optymistyczna',
                    line=dict(color='lightgreen', width=1, dash='dot'),
                    fill='tonexty'
                ))

                fig_proj.add_trace(go.Scatter(
                    x=proj_years, y=proj_pess,
                    mode='lines', name='Pesymistyczna',
                    line=dict(color='salmon', width=1, dash='dot')
                ))

                fig_proj.update_layout(
                    title="Prognoza kapitału (przed fees)",
                    xaxis_title="Rok",
                    yaxis_title="Kapitał (waluta bazowa)",
                    height=500,
                    hovermode='x unified'
                )

                st.plotly_chart(fig_proj, use_container_width=True)

            # STATYSTYKI SZCZEGÓŁOWE
            st.markdown("## 📊 Statystyki szczegółowe portfolio")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**📈 LONG**")
                long_trades = combined_trades[combined_trades['Type'] == 'LONG']
                if len(long_trades) > 0:
                    st.write(f"Liczba: {len(long_trades)}")
                    st.write(
                        f"Win rate: {(long_trades['Profit (base)'] > 0).sum() / len(long_trades) * 100:.1f}%")
                    st.write(f"Total profit (base): {long_trades['Profit (base)'].sum():,.2f}")
                    st.write(f"Total profit (quoted): {long_trades['Profit (quoted)'].sum():,.2f}")

            with col2:
                st.markdown("**📉 SHORT**")
                short_trades = combined_trades[combined_trades['Type'] == 'SHORT']
                if len(short_trades) > 0:
                    st.write(f"Liczba: {len(short_trades)}")
                    st.write(
                        f"Win rate: {(short_trades['Profit (base)'] > 0).sum() / len(short_trades) * 100:.1f}%")
                    st.write(f"Total profit (base): {short_trades['Profit (base)'].sum():,.2f}")
                    st.write(f"Total profit (quoted): {short_trades['Profit (quoted)'].sum():,.2f}")

            with col3:
                st.markdown("**🛡️ EXIT**")
                st.write(
                    f"Stop Loss: {len(combined_trades[combined_trades['Exit Reason'] == 'Stop Loss'])}")
                st.write(
                    f"Time exit: {len(combined_trades[combined_trades['Exit Reason'] == 'Time exit'])}")
                st.write(f"Avg holding: {combined_trades['Duration'].mean():.1f} dni")

            # Historia transakcji
            st.markdown("### 📝 Historia transakcji portfolio")

            display = combined_trades.copy()
            display['Entry Date'] = display['Entry Date'].dt.strftime('%Y-%m-%d')
            display['Exit Date'] = display['Exit Date'].dt.strftime('%Y-%m-%d')
            for col in ['Entry Price', 'Exit Price', 'Entry Level Value', 'Price Diff']:
                display[col] = display[col].round(5)
            display['Pips'] = display['Pips'].round(1)
            display['Profit (quoted)'] = display['Profit (quoted)'].round(2)
            display['Profit (base)'] = display['Profit (base)'].round(2)
            display['P&L %'] = display['P&L %'].round(2)
            display['ROI Margin %'] = display['ROI Margin %'].round(2)
            display['Portfolio Capital'] = display['Portfolio Capital'].round(2)

            st.dataframe(display, use_container_width=True)

            # Download
            csv = combined_trades.to_csv(index=False)
            symbols_str = "_".join(list(results_per_symbol.keys())[:3])
            if len(results_per_symbol) > 3:
                symbols_str += f"_plus{len(results_per_symbol) - 3}"

            st.download_button(
                "📥 Pobierz wyniki portfolio (CSV)",
                csv,
                f"portfolio_{symbols_str}_P{lookback_days}d_H{holding_days}d_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )

    else:
        st.error("❌ Nie udało się wykonać backtestingu")

else:
    st.info("👈 Wybierz źródło danych i kliknij URUCHOM BACKTEST")

    st.markdown(f"""
    ## 📖 Multi-Currency Backtesting - P&L in Base Currency + Leverage

    **🔑 Kalkulacja P&L (waluta bazowa):**
    - Wynik transakcji: `(exit - entry) × efektywny_wolumen` = wynik w **walucie kwotowanej**
    - Przeliczenie na bazową: `wynik_kwotowany / kurs_zamknięcia` = wynik w **walucie bazowej**
    - Kapitał i wszystkie wyniki wyrażone w walucie **bazowej** pary

    **⚡ Leverage (dźwignia):**
    - Dostępne: x1 (bez), x5, x10, x15, x20
    - Efektywny wolumen = wolumen × leverage
    - Zyski i straty pomnożone przez dźwignię
    - Przykład: 100k EUR × x10 = kontrolujesz 1M EUR pozycję

    **Przykład EURPLN (wolumen 100,000 EUR, leverage x10):**
    - Long entry: 4.2100, exit: 4.2200, eff. volume: 1,000,000
    - Wynik PLN = 0.0100 × 1,000,000 = **10,000 PLN** (kwotowana)
    - Wynik EUR = 10,000 / 4.2200 = **2,369.67 EUR** (bazowa)

    **Pivot Points:** 3-21 dni | **Holding:** 1-120 dni

    **Fee Structure:**
    - Management Fee {management_fee_pct}% (start roku z rzeczywistego kapitału)
    - Success Fee {success_fee_pct}% (koniec roku, tylko od zysku)
    """)

st.markdown("---")
st.markdown(
    f"**🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}** | 💱 Multi-Currency | P&L Base Currency | Leverage x1-x20 | Hold 1-120d")
