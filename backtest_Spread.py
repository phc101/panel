import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import io

# Streamlit app configuration
st.set_page_config(page_title="Portfolio Momentum Pivot Points Trading Strategy", layout="wide")
st.title("Portfolio Momentum Pivot Points Trading Strategy")
st.markdown("Backtest strategii momentum dla maksymalnie 5 par walutowych w formacie Investing.com. Wyniki prezentowane jako portfel z równą alokacją.")

# File upload
st.subheader("Wczytaj pliki CSV (maks. 5 par walutowych)")
st.markdown("Wczytaj pliki CSV z danymi w formacie Investing.com (np. EUR_PLN Historical Data.csv). Wymagane kolumny: Date, Price, Open, High, Low.")
uploaded_files = st.file_uploader("Wybierz pliki CSV", type=["csv"], accept_multiple_files=True)

# Trading parameters
st.subheader("Parametry Handlowe")
holding_days = st.slider("Liczba dni trzymania pozycji", min_value=1, max_value=10, value=3, step=1)
stop_loss_percent = st.number_input("Stop Loss (%):", min_value=0.0, max_value=10.0, value=2.0, step=0.1)
no_overlap = st.checkbox("Brak nakładających się pozycji", value=True, help="Jeśli zaznaczone, nowa transakcja może być otwarta tylko po zamknięciu poprzedniej")
dynamic_leverage = st.checkbox("Dynamiczne dźwignia finansowa", value=False, help="5x leverage po zyskownej transakcji, brak dźwigni po stratnej")

# Load and validate CSV data
@st.cache_data
def load_data(uploaded_files):
    if not uploaded_files:
        st.warning("Proszę wczytać przynajmniej jeden plik CSV, aby kontynuować.")
        return None
    
    if len(uploaded_files) > 5:
        st.error("Można wczytać maksymalnie 5 plików CSV.")
        return None
    
    dfs = {}
    for file in uploaded_files:
        try:
            df = pd.read_csv(file)
            expected_columns = ['Date', 'Price', 'Open', 'High', 'Low']
            if not all(col in df.columns for col in expected_columns):
                st.error(f"Plik {file.name} musi zawierać kolumny: {', '.join(expected_columns)}")
                return None
            
            df = df.rename(columns={'Price': 'Close'})
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            if df['Date'].isna().any():
                st.warning(f"Niektóre daty w pliku {file.name} są nieprawidłowe i zostaną pominięte.")
                df = df.dropna(subset=['Date'])
            
            numeric_cols = ['Open', 'High', 'Low', 'Close']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            if df[numeric_cols].isna().any().any():
                st.warning(f"Niektóre wartości cen w pliku {file.name} są nieprawidłowe i zostaną zastąpione zerami.")
                df[numeric_cols] = df[numeric_cols].fillna(0)
            
            df = df.sort_values('Date').reset_index(drop=True)
            dfs[file.name] = df[['Date', 'Open', 'High', 'Low', 'Close']]
        except Exception as e:
            st.error(f"Błąd podczas wczytywania pliku {file.name}: {str(e)}")
            return None
    
    return dfs

# Calculate pivot points and execute momentum trading strategy for a single pair
def calculate_pivot_points_and_trades(df, holding_days, stop_loss_percent, pair_name, no_overlap=True, dynamic_leverage=False):
    pivot_data = []
    trades = []
    last_exit_index = -1  # Track when the last trade was closed
    last_trade_pnl = None  # Track PnL of last trade for leverage calculation
    current_leverage = 1.0  # Start with no leverage
    
    for i in range(7, len(df)):
        window = df.iloc[i-7:i]
        avg_high = window['High'].mean()
        avg_low = window['Low'].mean()
        avg_close = window['Close'].mean()
        
        pivot = (avg_high + avg_low + avg_close) / 3
        r1 = 2 * pivot - avg_low
        r2 = pivot + (avg_high - avg_low)
        s1 = 2 * pivot - avg_high
        s2 = pivot - (avg_high - avg_low)
        
        pivot_data.append({
            'Date': df.loc[i, 'Date'],
            'Pivot': pivot,
            'R1': r1,
            'R2': r2,
            'S1': s1,
            'S2': s2,
        })
    
    pivot_df = pd.DataFrame(pivot_data)
    df = df.merge(pivot_df, on='Date', how='left')
    
    for i in range(7, len(df) - holding_days):
        row = df.iloc[i]
        open_price = row['Open']
        
        if pd.isna(row.get('S1')):
            continue
        
        # Skip if we're in no_overlap mode and still within a previous trade period
        if no_overlap and i <= last_exit_index:
            continue
        
        # Update leverage based on last trade result
        if dynamic_leverage and last_trade_pnl is not None:
            if last_trade_pnl > 0:
                current_leverage = 5.0  # 5x leverage after profitable trade
            else:
                current_leverage = 1.0  # No leverage after losing trade
        else:
            current_leverage = 1.0  # Default no leverage
        
        trade_opened = False
        
        # BUY: Open price below S2
        if open_price < row['S2']:
            for j in range(1, holding_days + 1):
                if i + j >= len(df):
                    break
                close_price = df.iloc[i + j]['Close']
                raw_pnl = close_price - open_price
                leveraged_pnl = raw_pnl * current_leverage
                # Stop loss check on leveraged loss percentage
                raw_loss_percent = ((open_price - close_price) / open_price) * 100
                leveraged_loss_percent = raw_loss_percent * current_leverage
                if leveraged_loss_percent >= stop_loss_percent:
                    trades.append({
                        'Pair': pair_name,
                        'Entry Date': row['Date'],
                        'Exit Date': df.iloc[i + j]['Date'],
                        'Direction': 'BUY',
                        'Entry Price': open_price,
                        'Exit Price': close_price,
                        'PnL': leveraged_pnl,
                        'Raw PnL': raw_pnl,
                        'Leverage': current_leverage,
                        'PnL %': ((close_price - open_price) / open_price) * 100 * current_leverage if open_price != 0 else 0,
                        'Exit Reason': 'Stop Loss'
                    })
                    last_exit_index = i + j
                    last_trade_pnl = leveraged_pnl
                    trade_opened = True
                    break
            else:
                exit_close = df.iloc[i + holding_days]['Close']
                raw_pnl = exit_close - open_price
                leveraged_pnl = raw_pnl * current_leverage
                trades.append({
                    'Pair': pair_name,
                    'Entry Date': row['Date'],
                    'Exit Date': df.iloc[i + holding_days]['Date'],
                    'Direction': 'BUY',
                    'Entry Price': open_price,
                    'Exit Price': exit_close,
                    'PnL': leveraged_pnl,
                    'Raw PnL': raw_pnl,
                    'Leverage': current_leverage,
                    'PnL %': ((exit_close - open_price) / open_price) * 100 * current_leverage if open_price != 0 else 0,
                    'Exit Reason': 'Holding Period'
                })
                last_exit_index = i + holding_days
                last_trade_pnl = leveraged_pnl
                trade_opened = True
        
        # SELL: Open price above R2
        elif open_price > row['R2']:
            for j in range(1, holding_days + 1):
                if i + j >= len(df):
                    break
                close_price = df.iloc[i + j]['Close']
                raw_pnl = open_price - close_price
                leveraged_pnl = raw_pnl * current_leverage
                # Stop loss check on leveraged loss percentage  
                raw_loss_percent = ((close_price - open_price) / open_price) * 100
                leveraged_loss_percent = raw_loss_percent * current_leverage
                if leveraged_loss_percent >= stop_loss_percent:
                    trades.append({
                        'Pair': pair_name,
                        'Entry Date': row['Date'],
                        'Exit Date': df.iloc[i + j]['Date'],
                        'Direction': 'SELL',
                        'Entry Price': open_price,
                        'Exit Price': close_price,
                        'PnL': leveraged_pnl,
                        'Raw PnL': raw_pnl,
                        'Leverage': current_leverage,
                        'PnL %': ((open_price - close_price) / open_price) * 100 * current_leverage if open_price != 0 else 0,
                        'Exit Reason': 'Stop Loss'
                    })
                    last_exit_index = i + j
                    last_trade_pnl = leveraged_pnl
                    trade_opened = True
                    break
            else:
                exit_close = df.iloc[i + holding_days]['Close']
                raw_pnl = open_price - exit_close
                leveraged_pnl = raw_pnl * current_leverage
                trades.append({
                    'Pair': pair_name,
                    'Entry Date': row['Date'],
                    'Exit Date': df.iloc[i + holding_days]['Date'],
                    'Direction': 'SELL',
                    'Entry Price': open_price,
                    'Exit Price': exit_close,
                    'PnL': leveraged_pnl,
                    'Raw PnL': raw_pnl,
                    'Leverage': current_leverage,
                    'PnL %': ((open_price - exit_close) / open_price) * 100 * current_leverage if open_price != 0 else 0,
                    'Exit Reason': 'Holding Period'
                })
                last_exit_index = i + holding_days
                last_trade_pnl = leveraged_pnl
                trade_opened = True
    
    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df['Cumulative PnL'] = trades_df['PnL'].cumsum()
    
    return df, trades_df

# Calculate portfolio metrics
def calculate_portfolio_metrics(dfs, holding_days, stop_loss_percent, no_overlap=True, dynamic_leverage=False):
    all_trades = []
    pair_metrics = []
    weight = 1.0 / len(dfs) if dfs else 1.0
    
    for pair_name, df in dfs.items():
        df, trades_df = calculate_pivot_points_and_trades(df, holding_days, stop_loss_percent, pair_name, no_overlap, dynamic_leverage)
        if not trades_df.empty:
            total_trades_pair = len(trades_df)
            buy_trades = len(trades_df[trades_df['Direction'] == 'BUY'])
            sell_trades = len(trades_df[trades_df['Direction'] == 'SELL'])
            winning_trades = len(trades_df[trades_df['PnL'] > 0])
            win_rate = (winning_trades / total_trades_pair * 100) if total_trades_pair > 0 else 0
            total_pnl_pair = trades_df['PnL'].sum()
            avg_entry_price = trades_df['Entry Price'].mean()
            total_pnl_percent_pair = (total_pnl_pair / avg_entry_price * 100) if avg_entry_price != 0 else 0
            max_drawdown_pair, max_drawdown_percent_pair = calculate_drawdown(trades_df)
            
            pair_metrics.append({
                'Pair': pair_name,
                'Total Trades': total_trades_pair,
                'Buy Trades': buy_trades,
                'Sell Trades': sell_trades,
                'Win Rate (%)': win_rate,
                'PnL (PLN)': total_pnl_pair,
                'PnL %': total_pnl_percent_pair,
                'Max Drawdown (PLN)': max_drawdown_pair,
                'Max Drawdown %': max_drawdown_percent_pair
            })
            all_trades.append(trades_df)
        else:
            pair_metrics.append({
                'Pair': pair_name,
                'Total Trades': 0,
                'Buy Trades': 0,
                'Sell Trades': 0,
                'Win Rate (%)': 0,
                'PnL (PLN)': 0,
                'PnL %': 0,
                'Max Drawdown (PLN)': 0,
                'Max Drawdown %': 0
            })
    
    # Combine trades for portfolio
    if all_trades:
        portfolio_trades = pd.concat(all_trades, ignore_index=True)
    else:
        # Create empty DataFrame with expected columns if no trades
        portfolio_trades = pd.DataFrame(columns=['Pair', 'Entry Date', 'Exit Date', 'Direction', 'Entry Price', 'Exit Price', 'PnL', 'PnL %', 'Exit Reason', 'Cumulative PnL'])
    
    # Calculate portfolio cumulative PnL
    if not portfolio_trades.empty:
        # Group by Exit Date to sum daily PnLs
        daily_pnl = portfolio_trades.groupby('Exit Date')['PnL'].sum().reset_index()
        daily_pnl = daily_pnl.sort_values('Exit Date')
        daily_pnl['Cumulative PnL'] = daily_pnl['PnL'].cumsum() * weight
        portfolio_trades = portfolio_trades.drop(columns=['Cumulative PnL'], errors='ignore')  # Remove old column if exists
        portfolio_trades = portfolio_trades.merge(daily_pnl[['Exit Date', 'Cumulative PnL']], on='Exit Date', how='left')
        portfolio_trades['Cumulative PnL'] = portfolio_trades['Cumulative PnL'].fillna(method='ffill').fillna(0)
    
    # Portfolio metrics
    total_trades = len(portfolio_trades)
    buy_trades = len(portfolio_trades[portfolio_trades['Direction'] == 'BUY']) if total_trades > 0 else 0
    sell_trades = len(portfolio_trades[portfolio_trades['Direction'] == 'SELL']) if total_trades > 0 else 0
    winning_trades = len(portfolio_trades[portfolio_trades['PnL'] > 0]) if total_trades > 0 else 0
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_pnl = portfolio_trades['PnL'].sum() * weight if total_trades > 0 else 0
    avg_entry_price = portfolio_trades['Entry Price'].mean() if total_trades > 0 else 0
    total_pnl_percent = (total_pnl / avg_entry_price * 100) if avg_entry_price != 0 else 0
    max_drawdown, max_drawdown_percent = calculate_drawdown(portfolio_trades) if not portfolio_trades.empty else (0, 0)
    
    # Annual portfolio PnL
    annual_pnl = []
    if not portfolio_trades.empty:
        portfolio_trades['Year'] = portfolio_trades['Exit Date'].dt.year
        for year in portfolio_trades['Year'].unique():
            year_trades = portfolio_trades[portfolio_trades['Year'] == year]
            year_pnl = year_trades['PnL'].sum() * weight
            year_avg_entry = year_trades['Entry Price'].mean() if not year_trades.empty else 0
            year_pnl_percent = (year_pnl / year_avg_entry * 100) if year_avg_entry != 0 else 0
            annual_pnl.append({'Year': year, 'PnL (PLN)': year_pnl, 'PnL %': year_pnl_percent})
    
    return dfs, portfolio_trades, pair_metrics, annual_pnl, {
        'Total Trades': total_trades,
        'Buy Trades': buy_trades,
        'Sell Trades': sell_trades,
        'Win Rate (%)': win_rate,
        'Total PnL (PLN)': total_pnl,
        'Total PnL %': total_pnl_percent,
        'Max Drawdown (PLN)': max_drawdown,
        'Max Drawdown %': max_drawdown_percent
    }

# Calculate drawdown
def calculate_drawdown(trades_df):
    if trades_df.empty or 'Cumulative PnL' not in trades_df.columns:
        return 0, 0
    
    cumulative_pnl = trades_df['Cumulative PnL'].values
    peak = cumulative_pnl[0]
    max_drawdown = 0
    peak_value = peak
    
    for value in cumulative_pnl:
        if value > peak:
            peak = value
            peak_value = peak
        drawdown = peak - value
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    max_drawdown_percent = (max_drawdown / peak_value * 100) if peak_value != 0 else 0
    return max_drawdown, max_drawdown_percent

# Load data
dfs = load_data(uploaded_files)
if dfs is None:
    st.stop()

# Calculate portfolio results
dfs, portfolio_trades, pair_metrics, annual_pnl, portfolio_metrics = calculate_portfolio_metrics(dfs, holding_days, stop_loss_percent, no_overlap, dynamic_leverage)

# Display portfolio metrics
st.subheader("Metryki Portfela")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Całkowita liczba dni", len(dfs[list(dfs.keys())[0]]) if dfs else 0)
col2.metric("Całkowita liczba transakcji", portfolio_metrics['Total Trades'])
col3.metric("Wskaźnik wygranych", f"{portfolio_metrics['Win Rate (%)']:.1f}%")
col4.metric("Całkowity PnL (PLN)", f"{portfolio_metrics['Total PnL (PLN)']:.4f}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Transakcje BUY", f"{portfolio_metrics['Buy Trades']} ({(portfolio_metrics['Buy Trades']/portfolio_metrics['Total Trades']*100):.1f}%)" if portfolio_metrics['Total Trades'] > 0 else "0 (0%)")
col2.metric("Transakcje SELL", f"{portfolio_metrics['Sell Trades']} ({(portfolio_metrics['Sell Trades']/portfolio_metrics['Total Trades']*100):.1f}%)" if portfolio_metrics['Total Trades'] > 0 else "0 (0%)")
col3.metric("Całkowity PnL %", f"{portfolio_metrics['Total PnL %']:.2f}%")
col4.metric("Maksymalny Drawdown (PLN)", f"{portfolio_metrics['Max Drawdown (PLN)']:.4f}")

col1, col2 = st.columns(2)
col1.metric("Dni bez handlu", len(dfs[list(dfs.keys())[0]]) - portfolio_metrics['Total Trades'] if dfs else 0)
col2.metric("Maksymalny Drawdown %", f"{portfolio_metrics['Max Drawdown %']:.2f}%")

# Per-currency metrics
st.subheader("Metryki dla Poszczególnych Par Walutowych")
if pair_metrics:
    pair_metrics_df = pd.DataFrame(pair_metrics)
    pair_metrics_df['PnL (PLN)'] = pair_metrics_df['PnL (PLN)'].round(4)
    pair_metrics_df['PnL %'] = pair_metrics_df['PnL %'].round(2)
    pair_metrics_df['Max Drawdown (PLN)'] = pair_metrics_df['Max Drawdown (PLN)'].round(4)
    pair_metrics_df['Max Drawdown %'] = pair_metrics_df['Max Drawdown %'].round(2)
    pair_metrics_df['Win Rate (%)'] = pair_metrics_df['Win Rate (%)'].round(1)
    st.dataframe(pair_metrics_df, use_container_width=True)
else:
    st.write("Brak danych dla par walutowych.")

# Annual portfolio PnL
st.subheader("Roczny Wynik Procentowy Portfela")
if annual_pnl:
    annual_pnl_df = pd.DataFrame(annual_pnl)
    annual_pnl_df['PnL (PLN)'] = annual_pnl_df['PnL (PLN)'].round(4)
    annual_pnl_df['PnL %'] = annual_pnl_df['PnL %'].round(2)
    st.dataframe(annual_pnl_df, use_container_width=True)
else:
    st.write("Brak danych rocznych do wyświetlenia.")

# Strategy rules
st.subheader("Zasady Strategii Momentum")
st.markdown(f"""
- **Sygnał BUY**: Cena otwarcia poniżej poziomu wsparcia S2 (silne momentum spadkowe).
- **Sygnał SELL**: Cena otwarcia powyżej poziomu oporu R2 (silne momentum wzrostowe).
- **Zamknięcie pozycji**: Po {holding_days} dniach od otwarcia na cenie zamknięcia lub wcześniej, jeśli strata przekroczy {stop_loss_percent}% (stop loss).
- **Obliczenie Pivot**: Średnia 7-dniowa (High + Low + Close) / 3.
- **Poziomy wsparcia/oporu**:
  - S2 = Pivot - (AvgHigh - AvgLow)
  - S1 = 2×Pivot - AvgHigh
  - R1 = 2×Pivot - AvgLow
  - R2 = Pivot + (AvgHigh - AvgLow)
- **Portfel**: Równa alokacja dla każdej pary walutowej (np. 20% dla 5 par).
- **Nakładające się pozycje**: {'Dozwolone' if not no_overlap else 'Zabronione - nowa pozycja może być otwarta tylko po zamknięciu poprzedniej'}
- **Dynamiczna dźwignia**: {'Wyłączona (1x)' if not dynamic_leverage else 'Włączona (5x po zysku, 1x po stracie)'}
- **Dane**: Pierwsze 7 dni i ostatnie {holding_days} dni nie generują sygnałów handlowych.
""")

# Portfolio cumulative PnL plot
st.subheader("Wykres Skumulowanego PnL Portfela")
if not portfolio_trades.empty and 'Cumulative PnL' in portfolio_trades.columns:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(portfolio_trades['Exit Date'], portfolio_trades['Cumulative PnL'], marker='o', color='blue', label='Skumulowany PnL Portfela')
    
    # Highlight max drawdown
    if portfolio_metrics['Max Drawdown (PLN)'] > 0:
        cumulative_pnl = portfolio_trades['Cumulative PnL'].values
        peak_idx = 0
        peak_value = cumulative_pnl[0]
        trough_idx = 0
        max_drawdown_temp = 0
        
        for i, value in enumerate(cumulative_pnl):
            if value > peak_value:
                peak_value = value
                peak_idx = i
            drawdown = peak_value - value
            if drawdown > max_drawdown_temp:
                max_drawdown_temp = drawdown
                trough_idx = i
        
        if max_drawdown_temp > 0:
            ax.plot([portfolio_trades['Exit Date'].iloc[peak_idx], portfolio_trades['Exit Date'].iloc[trough_idx]],
                    [cumulative_pnl[peak_idx], cumulative_pnl[trough_idx]], 'r--', label='Maksymalny Drawdown')
    
    ax.set_xlabel("Data Zamknięcia")
    ax.set_ylabel("Skumulowany Zysk/Strata (PLN)")
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)
else:
    st.write("Brak danych do wyświetlenia wykresu PnL.")

# Individual pair results
for pair_name, df in dfs.items():
    st.subheader(f"Wyniki dla {pair_name}")
    
    # Check if pivot columns exist before displaying
    pivot_columns = ['Pivot', 'S1', 'S2', 'R1', 'R2']
    existing_pivot_columns = [col for col in pivot_columns if col in df.columns]
    
    if existing_pivot_columns:
        # Pivot points table
        st.markdown("**Tabela Punktów Pivot**")
        columns_to_display = ['Date'] + existing_pivot_columns
        pivot_display = df[columns_to_display].dropna().reset_index(drop=True)
        
        if not pivot_display.empty:
            pivot_display['Date'] = pivot_display['Date'].dt.strftime('%Y-%m-%d')
            for col in existing_pivot_columns:
                pivot_display[col] = pivot_display[col].round(4)
            st.dataframe(pivot_display, use_container_width=True)
        else:
            st.write("Brak danych pivot points (za mało danych historycznych - wymagane minimum 7 dni).")
    else:
        st.write("Brak danych pivot points (za mało danych historycznych - wymagane minimum 7 dni).")
    
    # Trades table
    st.markdown("**Zrealizowane Transakcje**")
    trades_df = portfolio_trades[portfolio_trades['Pair'] == pair_name] if not portfolio_trades.empty else pd.DataFrame()
    if not trades_df.empty:
        trades_display = trades_df.copy()
        trades_display['Entry Date'] = trades_display['Entry Date'].dt.strftime('%Y-%m-%d')
        trades_display['Exit Date'] = trades_display['Exit Date'].dt.strftime('%Y-%m-%d')
        trades_display[['Entry Price', 'Exit Price', 'PnL']] = trades_display[['Entry Price', 'Exit Price', 'PnL']].round(4)
        if 'Raw PnL' in trades_display.columns:
            trades_display['Raw PnL'] = trades_display['Raw PnL'].round(4)
        if 'Leverage' in trades_display.columns:
            trades_display['Leverage'] = trades_display['Leverage'].round(1)
        trades_display['PnL %'] = trades_display['PnL %'].round(2)
        st.dataframe(trades_display, use_container_width=True)
    else:
        st.write("Brak zrealizowanych transakcji.")

# Data source and range
st.subheader("Źródło Danych")
if uploaded_files:
    for file in uploaded_files:
        df = dfs.get(file.name, pd.DataFrame())
        if not df.empty:
            trade_count = len(portfolio_trades[portfolio_trades['Pair'] == file.name]) if not portfolio_trades.empty else 0
            st.markdown(f"""
            - **Plik**: {file.name}
            - **Przetworzone wiersze**: {len(df)}
            - **Zakres dat**: {df['Date'].min().strftime('%Y-%m-%d')} do {df['Date'].max().strftime('%Y-%m-%d')}
            - **Sygnały handlowe**: {trade_count}
            """)
else:
    st.markdown("Brak wczytanych plików.")
