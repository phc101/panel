import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Wczytaj dane
df = pd.read_csv("/mnt/data/EUR_PLN Historical Data (20).csv")
df.columns = ['Date', 'Close', 'Open', 'High', 'Low', 'Change %']
df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values('Date')
df = df[['Date', 'Open', 'High', 'Low', 'Close']].reset_index(drop=True)

# Oblicz Pivot Points z ostatnich 7 dni
pivot_data = []
for i in range(7, len(df)):
    window = df.iloc[i-7:i]
    high = window['High'].max()
    low = window['Low'].min()
    close = window['Close'].iloc[-1]

    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    r2 = pivot + (high - low)
    s1 = 2 * pivot - high
    s2 = pivot - (high - low)

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

# Strategia: Otwórz pozycję BUY lub SELL, zamknij po 3 dniach
trades = []

for i in range(len(df) - 3):
    row = df.iloc[i]
    open_price = row['Open']

    if pd.isna(row['S1']):
        continue

    # BUY signal
    if row['S2'] < open_price < row['S1']:
        exit_close = df.iloc[i + 3]['Close']
        pnl = exit_close - open_price
        trades.append({
            'Entry Date': row['Date'],
            'Exit Date': df.iloc[i + 3]['Date'],
            'Direction': 'BUY',
            'Entry Price': open_price,
            'Exit Price': exit_close,
            'PnL': pnl
        })

    # SELL signal
    elif row['R1'] < open_price < row['R2']:
        exit_close = df.iloc[i + 3]['Close']
        pnl = open_price - exit_close
        trades.append({
            'Entry Date': row['Date'],
            'Exit Date': df.iloc[i + 3]['Date'],
            'Direction': 'SELL',
            'Entry Price': open_price,
            'Exit Price': exit_close,
            'PnL': pnl
        })

trades_df = pd.DataFrame(trades)
trades_df['Cumulative PnL'] = trades_df['PnL'].cumsum()

# Streamlit App
st.title("Backtest Strategii Pivot Points (EUR/PLN)")
st.subheader("Tabela Pivot Points")
st.dataframe(df[['Date', 'Pivot', 'S1', 'S2', 'R1', 'R2']].dropna().reset_index(drop=True))

st.subheader("Zrealizowane Transakcje")
st.dataframe(trades_df)

st.subheader("Wykres Skumulowanego PnL")
fig, ax = plt.subplots()
ax.plot(trades_df['Exit Date'], trades_df['Cumulative PnL'], marker='o')
ax.set_xlabel("Data Zamknięcia")
ax.set_ylabel("Skumulowany Zysk/Strata (PnL)")
ax.grid(True)
st.pyplot(fig)
