import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

# Title and description
st.title("EUR/PLN and USD/PLN Z-Score Signal Generator")
st.write("This app calculates Z-scores based on the last 20 days of close prices and generates buy/sell signals with multiple settlement strategies.")

# Load data from uploaded file
def load_data(file_path):
    try:
        data = pd.read_excel(file_path)
        if 'Date' in data.columns and 'Close' in data.columns:
            data['Date'] = pd.to_datetime(data['Date'])
            return data[['Date', 'Close']]
        else:
            st.error("The uploaded file must contain 'Date' and 'Close' columns.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Function to process and visualize data with multiple settlement strategies
def process_and_visualize(data, pair):
    # Data preparation
    data = data.sort_values(by='Date')

    # Keep only the last 12 months of data
    data = data.tail(252).reset_index(drop=True)  # Approx. 252 trading days in a year

    # Rolling calculations
    data['Mean_20'] = data['Close'].rolling(window=20).mean()
    data['Std_20'] = data['Close'].rolling(window=20).std()

    # Filter rows with valid rolling calculations
    data = data[data['Mean_20'].notna() & data['Std_20'].notna()]

    # Calculate Z-Score
    data['Z_Score'] = (data['Close'] - data['Mean_20']) / data['Std_20']
    data['Z_Score'] = data['Z_Score'].replace([np.inf, -np.inf], np.nan).fillna(0)

    # Signal generation based on Z-Score
    data['Signal'] = np.where(data['Z_Score'] < -2, 'Buy',
                              np.where(data['Z_Score'] > 2, 'Sell', 'Hold'))

    # Backtesting strategies for Buy and Sell signals separately
    results = {}
    for strategy in ['Buy', 'Sell']:
        strategy_data = data[data['Signal'] == strategy].copy()
        strategy_results = {}
        for days in [30, 60, 90]:
            settlement_col = f'Settlement_Close_{days}'
            return_col = f'Return_{days}'
            cumulative_col = f'Cumulative_Return_{days}'

            strategy_data[f'Settlement_Date_{days}'] = strategy_data['Date'].shift(-days)
            strategy_data[settlement_col] = strategy_data['Close'].shift(-days)

            if strategy == 'Buy':
                strategy_data[return_col] = (strategy_data[settlement_col] - strategy_data['Close']) / strategy_data['Close']
            elif strategy == 'Sell':
                strategy_data[return_col] = (strategy_data['Close'] - strategy_data[settlement_col]) / strategy_data['Close']

            strategy_data[cumulative_col] = (1 + strategy_data[return_col]).cumprod()
            strategy_results[days] = strategy_data[cumulative_col].iloc[-1] if not strategy_data[cumulative_col].empty else 1

        results[strategy] = strategy_results

    # Display performance rankings
    rankings = pd.DataFrame(results)
    rankings.index = ["30 Days", "60 Days", "90 Days"]
    st.subheader(f"Performance Rankings for {pair}")
    st.write(rankings)

    # Visualization of cumulative returns for all strategies
    st.subheader(f"Cumulative Returns of {pair} Strategy")
    plt.figure(figsize=(10, 6))
    for strategy in ['Buy', 'Sell']:
        for days in [30, 60, 90]:
            label = f'{strategy} {days} Days'
            cumulative_col = f'Cumulative_Return_{days}'
            if cumulative_col in data.columns:
                plt.plot(data['Date'], data[cumulative_col], label=label)
    plt.title(f"Cumulative Returns for {pair}")
    plt.legend()
    plt.grid()
    st.pyplot(plt)

    st.subheader(f"Download Results for {pair}")
    csv = data.to_csv(index=False)
    st.download_button(f"Download CSV for {pair}", data=csv, file_name=f"zscore_strategy_results_{pair}.csv", mime="text/csv")

# Load and process EUR/PLN data
st.subheader("Upload EUR/PLN Data")
eurpln_file = st.file_uploader("Upload EUR/PLN Excel file:", type=["xlsx"])
if eurpln_file:
    eurpln_data = load_data(eurpln_file)
    if not eurpln_data.empty:
        process_and_visualize(eurpln_data, "EUR/PLN")

# Load and process USD/PLN data
st.subheader("Upload USD/PLN Data")
usdpln_file = st.file_uploader("Upload USD/PLN Excel file:", type=["xlsx"])
if usdpln_file:
    usdpln_data = load_data(usdpln_file)
    if not usdpln_data.empty:
        process_and_visualize(usdpln_data, "USD/PLN")
