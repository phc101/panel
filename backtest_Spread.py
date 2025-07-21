import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- Wczytaj dane ---
uploaded_file = st.file_uploader("Wgraj plik CSV z danymi EUR/PLN", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()

    # Upewnij się, że dane są posortowane rosnąco wg daty
    df['Date'] = pd.to_datetime(df['Date'])
    df.sort_values('Date', inplace=True)

    # Oblicz Pivot Points
    df['Pivot'] = (df['High'] + df['Low'] + df['Price']) / 3
    df['R1'] = 2 * df['Pivot'] - df['Low']
    df['S1'] = 2 * df['Pivot'] - df['High']
    df['R2'] = df['Pivot'] + (df['High'] - df['Low'])
    df['S2'] = df['Pivot'] - (df['High'] - df['Low'])

    # Logika transakcji
    trades = []
    for i in range(len(df) - 3):  # Musimy mieć 3 dni później
        row = df.iloc[i]
        open_price = row['Open']

        if row['S2'] <= open_price <= row['S1']:
            # BUY logic
            entry_date = row['Date']
            exit_date = df.iloc[i + 3]['Date']
            entry_price = open_price
            exit_price = df.iloc[i + 3]['Price']
            pnl = exit_price - entry_price
            trades.append({
                'Direction': 'BUY',
                'Entry Date': entry_date,
                'Exit Date': exit_date,
                'Entry': entry_price,
                'Exit': exit_price,
                'PnL': pnl
            })

        elif row['R1'] <= open_price <= row['R2']:
            # SELL logic
            entry_date = row['Date']
            exit_date = df.iloc[i + 3]['Date']
            entry_price = open_price
            exit_price = df.iloc[i + 3]['Price']
            pnl = entry_price - exit_price
            trades.append({
                'Direction': 'SELL',
                'Entry Date': entry_date,
                'Exit Date': exit_date,
                'Entry': entry_price,
                'Exit': exit_price,
                'PnL': pnl
            })

    results = pd.DataFrame(trades)

    st.subheader("📈 Wyniki transakcji")
    st.write(results)

    st.subheader("💰 Suma zysków/strat")
    total_pnl = results['PnL'].sum()
    st.metric("Łączny wynik strategii", f"{total_pnl:.4f} PLN")

    # Wykres equity curve
    results['Cumulative PnL'] = results['PnL'].cumsum()
    fig, ax = plt.subplots()
    ax.plot(results['Exit Date'], results['Cumulative PnL'], marker='o')
    ax.set_title("Krzywa kapitału strategii")
    ax.set_xlabel("Data")
    ax.set_ylabel("Cumulative PnL (PLN)")
    st.pyplot(fig)
