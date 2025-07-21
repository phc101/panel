import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Wczytaj dane
uploaded_file = st.file_uploader("Wczytaj plik CSV z danymi EUR/PLN", type=["csv"])
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.strip() for c in df.columns]
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    df.set_index('Date', inplace=True)

    # Przekształć dane na float
    for col in ['Open', 'High', 'Low', 'Price']:
        df[col] = df[col].astype(str).str.replace(',', '.').astype(float)

    # Oblicz Pivot Points na podstawie 7-dniowej średniej (rolling)
    df['PP'] = ((df['High'] + df['Low'] + df['Price']) / 3).rolling(window=7).mean()
    df['R1'] = (2 * df['PP']) - df['Low'].rolling(window=7).mean()
    df['S1'] = (2 * df['PP']) - df['High'].rolling(window=7).mean()
    df['R2'] = df['PP'] + (df['High'].rolling(window=7).mean() - df['Low'].rolling(window=7).mean())
    df['S2'] = df['PP'] - (df['High'].rolling(window=7).mean() - df['Low'].rolling(window=7).mean())

    df = df.dropna()

    # Logika strategii
    trades = []
    for i in range(len(df) - 3):  # -3 bo zamykamy 3 dni później
        row = df.iloc[i]
        open_price = row['Open']
        s1, s2, r1, r2 = row['S1'], row['S2'], row['R1'], row['R2']
        date = df.index[i]

        close_price_3d = df.iloc[i + 3]['Price']

        if s2 < open_price < s1:
            profit = close_price_3d - open_price
            trades.append({'Date': date, 'Type': 'BUY', 'Entry': open_price, 'Exit': close_price_3d, 'PnL': profit})
        elif r1 < open_price < r2:
            profit = open_price - close_price_3d
            trades.append({'Date': date, 'Type': 'SELL', 'Entry': open_price, 'Exit': close_price_3d, 'PnL': profit})

    trades_df = pd.DataFrame(trades)

    # Wyświetl tabele
    st.subheader("Tabela transakcji")
    st.dataframe(trades_df)

    # Pokaż punkty pivot w tabeli
    st.subheader("Dane z Pivot Points")
    st.dataframe(df[['Open', 'Price', 'PP', 'S2', 'S1', 'R1', 'R2']].tail(15))

    # Equity curve
    st.subheader("Equity Curve")
    trades_df['Cumulative PnL'] = trades_df['PnL'].cumsum()
    fig, ax = plt.subplots()
    ax.plot(trades_df['Date'], trades_df['Cumulative PnL'], label='Equity Curve')
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Profit")
    ax.set_title("Wynik strategii Pivot Points")
    ax.grid()
    st.pyplot(fig)

    # Suma zysków
    total_pnl = trades_df['PnL'].sum()
    st.metric("Suma PnL (łącznie)", f"{total_pnl:.4f} PLN")
