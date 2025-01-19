import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import requests
import io

# Title and description
st.title("EUR/PLN and USD/PLN Z-Score Signal Generator")
st.write("This app calculates Z-scores based on the last 20 days of close prices and generates buy/sell signals with multiple settlement strategies.")

# Fetch live data from Alpha Vantage
def fetch_live_data(api_key, from_symbol, to_symbol):
    url = f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={from_symbol}&to_symbol={to_symbol}&apikey={api_key}&outputsize=full&datatype=csv"
    response = requests.get(url)
    if response.status_code == 200:
        try:
            data = pd.read_csv(io.StringIO(response.text))
            st.write("API Response Preview:", data.head())  # Debugging: Show API response
            if 'timestamp' in data.columns and 'close' in data.columns:
                data = data.rename(columns={"timestamp": "Date", "close": "Close"})
                data['Date'] = pd.to_datetime(data['Date'])
                return data[['Date', 'Close']]
            else:
                st.error("Expected columns not found in API response.")
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error parsing API response: {e}")
            return pd.DataFrame()
    else:
        st.error(f"Failed to fetch live data for {from_symbol}/{to_symbol}. HTTP Status Code: {response.status_code}")
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

# Enter your Alpha Vantage API key
api_key = st.text_input("Enter your Alpha Vantage API key:", type="password")

if api_key:
    # Fetch and process EUR/PLN data
    st.subheader("EUR/PLN Analysis")
    eurpln_data = fetch_live_data(api_key, "EUR", "PLN")
    if not eurpln_data.empty:
        process_and_visualize(eurpln_data, "EUR/PLN")

    # Fetch and process USD/PLN data
    st.subheader("USD/PLN Analysis")
    usdpln_data = fetch_live_data(api_key, "USD", "PLN")
    if not usdpln_data.empty:
        process_and_visualize(usdpln_data, "USD/PLN")
