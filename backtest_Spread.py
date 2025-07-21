import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import io

# Streamlit app configuration
st.set_page_config(page_title="Momentum Pivot Points Trading Strategy (EUR/PLN)", layout="wide")
st.title("Momentum Pivot Points Trading Strategy (EUR/PLN)")
st.markdown("Backtest strategii momentum opartej na 7-dniowych punktach pivot dla danych EUR/PLN z Investing.com.")

# File upload
st.subheader("Wczytaj plik CSV")
st.markdown("Wczytaj plik CSV z danymi w formacie Investing.com (np. EUR_PLN Historical Data.csv). Wymagane kolumny: Date, Price, Open, High, Low.")
uploaded_file = st.file_uploader("Wybierz plik CSV", type=["csv"])

# Load and validate CSV data
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is None:
        st.warning("Proszę wczytać plik CSV, aby kontynuować.")
        return None
    
    try:
        df = pd.read_csv(uploaded_file)
        expected_columns = ['Date', 'Price', 'Open', 'High', 'Low']
        if not all(col in df.columns for col in expected_columns):
            st.error(f"Plik CSV musi zawierać kolumny: {', '.join(expected_columns)}")
            return None
        
        df = df.rename(columns={'Price': 'Close'})
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        if df['Date'].isna().any():
            st.warning("Niektóre daty w pliku CSV są nieprawidłowe i zostaną pominięte.")
            df = df.dropna(subset=['Date'])
        
        numeric_cols = ['Open', 'High', 'Low', 'Close']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if df[numeric_cols].isna().any().any():
            st.warning("Niektóre wartości cen w pliku CSV są nieprawidłowe i zostaną zastąpione zerami.")
            df[numeric_cols] = df[numeric_cols].fillna(0)
        
        df = df.sort_values('Date').reset_index(drop=True)
        return df[['Date', 'Open', 'High', 'Low', 'Close']]
    except Exception as e:
        st.error(f"Błąd podczas wczytywania pliku CSV: {str(e)}")
        return None

# Calculate pivot points and execute momentum trading strategy
def calculate_pivot_points_and_trades(df):
    pivot_data = []
    trades = []
    
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
    
    for i in range(7, len(df) - 3):
        row = df.iloc[i]
        open_price = row['Open']
        
        if pd.isna(row['S1']):
            continue
        
        # BUY: Open price between R1 and R2 (momentum upward)
        if row['R1'] < open_price < row['R2']:
            exit_close = df.iloc[i + 3]['Close']
            pnl = exit_close - open_price
            trades.append({
                'Entry Date': row['Date'],
                'Exit Date': df.iloc[i + 3]['Date'],
                'Direction': 'BUY',
                'Entry Price': open_price,
                'Exit Price': exit_close,
                'PnL': pnl,
                'PnL %': (pnl / open_price) * 100 if open_price != 0 else 0
            })
        
        # SELL: Open price between S1 and S2 (momentum downward)
        elif row['S2'] < open_price < row['S1']:
            exit_close = df.iloc[i + 3]['Close']
            pnl = open_price - exit_close
            trades.append({
                'Entry Date': row['Date'],
                'Exit Date': df.iloc[i + 3]['Date'],
                'Direction': 'SELL',
                'Entry Price': open_price,
                'Exit Price': exit_close,
                'PnL': pnl,
                'PnL %': (pnl / open_price) * 100 if open_price != 0 else 0
            })
    
    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df['Cumulative PnL'] = trades_df['PnL'].cumsum()
    
    return df, trades_df

# Calculate drawdown
def calculate_drawdown(trades_df):
    if trades_df.empty:
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
df = load_data(uploaded_file)
if df is None:
    st.stop()

# Calculate pivot points and trades
df, trades_df = calculate_pivot_points_and_trades(df)

# Calculate metrics
total_trades = len(trades_df)
buy_trades = len(trades_df[trades_df['Direction'] == 'BUY'])
sell_trades = len(trades_df[trades_df['Direction'] == 'SELL'])
winning_trades = len(trades_df[trades_df['PnL'] > 0]) if total_trades > 0 else 0
win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
total_pnl = trades_df['PnL'].sum() if total_trades > 0 else 0
total_pnl_percent = (total_pnl / trades_df['Entry Price'].mean() * 100) if total_trades > 0 else 0
max_drawdown, max_drawdown_percent = calculate_drawdown(trades_df)

# Annual PnL percentage
annual_pnl = []
if not trades_df.empty:
    trades_df['Year'] = trades_df['Exit Date'].dt.year
    for year in trades_df['Year'].unique():
        year_trades = trades_df[trades_df['Year'] == year]
        year_pnl = year_trades['PnL'].sum()
        year_avg_entry = year_trades['Entry Price'].mean()
        year_pnl_percent = (year_pnl / year_avg_entry * 100) if year_avg_entry != 0 else 0
        annual_pnl.append({'Year': year, 'PnL (PLN)': year_pnl, 'PnL %': year_pnl_percent})
annual_pnl_df = pd.DataFrame(annual_pnl)

# Display metrics
st.subheader("Metryki Strategii")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Całkowita liczba dni", len(df))
col2.metric("Dni handlowe", total_trades)
col3.metric("Wskaźnik wygranych", f"{win_rate:.1f}%")
col4.metric("Całkowity PnL (PLN)", f"{total_pnl:.4f}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Transakcje BUY", f"{buy_trades} ({(buy_trades/total_trades*100):.1f}%)" if total_trades > 0 else "0 (0%)")
col2.metric("Transakcje SELL", f"{sell_trades} ({(sell_trades/total_trades*100):.1f}%)" if total_trades > 0 else "0 (0%)")
col3.metric("Całkowity PnL %", f"{total_pnl_percent:.2f}%")
col4.metric("Maksymalny Drawdown (PLN)", f"{max_drawdown:.4f}")

col1, col2 = st.columns(2)
col1.metric("Dni bez handlu", len(df) - total_trades)
col2.metric("Maksymalny Drawdown %", f"{max_drawdown_percent:.2f}%")

# Annual PnL table
st.subheader("Roczny Wynik Procentowy")
if not annual_pnl_df.empty:
    annual_display = annual_pnl_df.copy()
    annual_display['PnL (PLN)'] = annual_display['PnL (PLN)'].round(4)
    annual_display['PnL %'] = annual_display['PnL %'].round(2)
    st.dataframe(annual_display, use_container_width=True)
else:
    st.write("Brak danych rocznych do wyświetlenia.")

# Strategy rules
st.subheader("Zasady Strategii Momentum")
st.markdown("""
- **Sygnał BUY**: Cena otwarcia między poziomami oporu R1 i R2 (momentum wzrostowe).
- **Sygnał SELL**: Cena otwarcia między poziomami wsparcia S1 i S2 (momentum spadkowe).
- **Zamknięcie pozycji**: Po 3 dniach od otwarcia, na cenie zamknięcia.
- **Obliczenie Pivot**: Średnia 7-dniowa (High + Low + Close) / 3.
- **Poziomy wsparcia/oporu**:
  - S2 = Pivot - (AvgHigh - AvgLow)
  - S1 = 2×Pivot - AvgHigh
  - R1 = 2×Pivot - AvgLow
  - R2 = Pivot + (AvgHigh - AvgLow)
- **Dane**: Pierwsze 7 dni i ostatnie 3 dni nie generują sygnałów handlowych.
""")

# Pivot points table
st.subheader("Tabela Punktów Pivot")
pivot_display = df[['Date', 'Pivot', 'S1', 'S2', 'R1', 'R2']].dropna().reset_index(drop=True)
pivot_display['Date'] = pivot_display['Date'].dt.strftime('%Y-%m-%d')
for col in ['Pivot', 'S1', 'S2', 'R1', 'R2']:
    pivot_display[col] = pivot_display[col].round(4)
st.dataframe(pivot_display, use_container_width=True)

# Trades table
st.subheader("Zrealizowane Transakcje")
if not trades_df.empty:
    trades_display = trades_df.copy()
    trades_display['Entry Date'] = trades_display['Entry Date'].dt.strftime('%Y-%m-%d')
    trades_display['Exit Date'] = trades_display['Exit Date'].dt.strftime('%Y-%m-%d')
    trades_display[['Entry Price', 'Exit Price', 'PnL']] = trades_display[['Entry Price', 'Exit Price', 'PnL']].round(4)
    trades_display['PnL %'] = trades_display['PnL %'].round(2)
    st.dataframe(trades_display, use_container_width=True)
else:
    st.write("Brak zrealizowanych transakcji.")

# Cumulative PnL plot with drawdown highlight
st.subheader("Wykres Skumulowanego PnL")
if not trades_df.empty:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(trades_df['Exit Date'], trades_df['Cumulative PnL'], marker='o', color='blue', label='Skumulowany PnL')
    
    # Highlight max drawdown
    if max_drawdown > 0:
        cumulative_pnl = trades_df['Cumulative PnL'].values
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
            ax.plot([trades_df['Exit Date'].iloc[peak_idx], trades_df['Exit Date'].iloc[trough_idx]],
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

# Data source and range
st.subheader("Źródło Danych")
if uploaded_file is not None:
    st.markdown(f"""
    - **Plik**: {uploaded_file.name}
    - **Przetworzone wiersze**: {len(df)}
    - **Zakres dat**: {df['Date'].min().strftime('%Y-%m-%d')} do {df['Date'].max().strftime('%Y-%m-%d')}
    - **Sygnały handlowe**: {total_trades}
    """)
else:
    st.markdown("Brak wczytanego pliku.")
