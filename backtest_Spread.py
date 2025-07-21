import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import os

# Streamlit app configuration
st.set_page_config(page_title="Pivot Points Trading Strategy", layout="wide")
st.title("Pivot Points Trading Strategy (EUR/PLN)")
st.markdown("Backtest strategii handlowej opartej na 7-dniowych punktach pivot dla EUR/PLN.")

# File path for CSV
csv_file = "EUR_PLN Historical Data.csv"

# Load and validate CSV data
@st.cache_data
def load_data(file_path):
    try:
        if not os.path.exists(file_path):
            st.error(f"Plik {file_path} nie istnieje. Upewnij się, że plik CSV znajduje się w odpowiednim katalogu.")
            return None
        
        df = pd.read_csv(file_path)
        expected_columns = ['Date', 'Close', 'Open', 'High', 'Low']
        if not all(col in df.columns for col in expected_columns):
            st.error(f"Plik CSV musi zawierać kolumny: {', '.join(expected_columns)}")
            return None
        
        # Convert Date to datetime
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        if df['Date'].isna().any():
            st.warning("Niektóre daty w pliku CSV są nieprawidłowe i zostaną pominięte.")
            df = df.dropna(subset=['Date'])
        
        # Convert numeric columns
        numeric_cols = ['Open', 'High', 'Low', 'Close']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if df[numeric_cols].isna().any().any():
            st.warning("Niektóre wartości cen w pliku CSV są nieprawidłowe i zostaną zastąpione zerami.")
            df[numeric_cols] = df[numeric_cols].fillna(0)
        
        # Sort by date and reset index
        df = df.sort_values('Date').reset_index(drop=True)
        return df[['Date', 'Open', 'High', 'Low', 'Close']]
    except Exception as e:
        st.error(f"Błąd podczas wczytywania pliku CSV: {str(e)}")
        return None

# Calculate pivot points and execute trading strategy
def calculate_pivot_points_and_trades(df):
    pivot_data = []
    trades = []
    
    # Calculate pivot points for each day after the first 7 days
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
    
    # Merge pivot points with main DataFrame
    pivot_df = pd.DataFrame(pivot_data)
    df = df.merge(pivot_df, on='Date', how='left')
    
    # Execute trading strategy
    for i in range(7, len(df) - 3):  # Ensure 3 days ahead for closing
        row = df.iloc[i]
        open_price = row['Open']
        
        if pd.isna(row['S1']):
            continue
        
        # BUY: Open price between S1 and S2
        if row['S2'] < open_price < row['S1']:
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
        
        # SELL: Open price between R1 and R2
        elif row['R1'] < open_price < row['R2']:
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

# Load data
df = load_data(csv_file)
if df is None:
    st.stop()

# Calculate pivot points and trades
df, trades_df = calculate_pivot_points_and_trades(df)

# Display metrics
st.subheader("Metryki Strategii")
total_trades = len(trades_df)
buy_trades = len(trades_df[trades_df['Direction'] == 'BUY'])
sell_trades = len(trades_df[trades_df['Direction'] == 'SELL'])
winning_trades = len(trades_df[trades_df['PnL'] > 0]) if total_trades > 0 else 0
win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
total_pnl = trades_df['PnL'].sum() if total_trades > 0 else 0
no_trade_days = len(df) - total_trades

col1, col2, col3, col4 = st.columns(4)
col1.metric("Całkowita liczba dni", len(df))
col2.metric("Dni handlowe", total_trades)
col3.metric("Wskaźnik wygranych", f"{win_rate:.1f}%")
col4.metric("Całkowity PnL", f"{total_pnl:.4f}")

col1, col2, col3 = st.columns(3)
col1.metric("Transakcje BUY", f"{buy_trades} ({(buy_trades/total_trades*100):.1f}%)" if total_trades > 0 else "0 (0%)")
col2.metric("Transakcje SELL", f"{sell_trades} ({(sell_trades/total_trades*100):.1f}%)" if total_trades > 0 else "0 (0%)")
col3.metric("Dni bez handlu", no_trade_days)

# Strategy rules
st.subheader("Zasady Strategii")
st.markdown("""
- **Sygnał BUY**: Cena otwarcia między poziomami wsparcia S1 i S2.
- **Sygnał SELL**: Cena otwarcia między poziomami oporu R1 i R2.
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

# Cumulative PnL plot
st.subheader("Wykres Skumulowanego PnL")
if not trades_df.empty:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(trades_df['Exit Date'], trades_df['Cumulative PnL'], marker='o', color='blue', label='Skumulowany PnL')
    ax.set_xlabel("Data Zamknięcia")
    ax.set_ylabel("Skumulowany Zysk/Strata (PnL)")
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)
else:
    st.write("Brak danych do wyświetlenia wykresu PnL.")

# Data source and range
st.subheader("Źródło Danych")
st.markdown(f"""
- **Plik**: {csv_file}
- **Przetworzone wiersze**: {len(df)}
- **Zakres dat**: {df['Date'].min().strftime('%Y-%m-%d')} do {df['Date'].max().strftime('%Y-%m-%d')}
- **Sygnały handlowe**: {total_trades}
""")
