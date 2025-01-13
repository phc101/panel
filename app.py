
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# App title
st.title("EUR/PLN Buy/Sell Recommendations")

# Fetch live EUR/PLN data
@st.cache
def fetch_data():
    try:
        ticker = "EURPLN=X"  # Yahoo Finance ticker for EUR/PLN
        data = yf.download(ticker, period="1y", interval="1d")
        data['Date'] = data.index
        st.write("Data successfully fetched!")
        return data
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# Calculate signals based on Z-score
def calculate_signals(data, window=20):
    try:
        # Check if 'Close' column exists
        if 'Close' not in data.columns:
            st.error("The 'Close' column is missing from the data.")
            return data

        # Calculate rolling mean and standard deviation
        data['Mean'] = data['Close'].rolling(window=window).mean()
        data['StdDev'] = data['Close'].rolling(window=window).std()

        # Check for valid rolling calculations
        if data['Mean'].isnull().all() or data['StdDev'].isnull().all():
            st.error("Rolling calculations failed. Data might be insufficient.")
            return data

        # Calculate Z-Score and handle NaN values
        data['Z-Score'] = (data['Close'] - data['Mean']) / data['StdDev']
        data['Z-Score'] = data['Z-Score'].fillna(0)  # Fill NaN Z-Scores with 0

        # Generate signals
        data['Signal'] = np.where(data['Z-Score'] < -2, 'Buy',
                         np.where(data['Z-Score'] > 2, 'Sell', 'Hold'))

        st.write("Signals successfully calculated!")
        return data
    except Exception as e:
        st.error(f"Error in calculate_signals: {e}")
        return data

# Plot the price chart with buy/sell signals
def plot_chart(data):
    try:
        if data.empty:
            st.error("Data is empty, cannot plot chart.")
            return
        
        plt.figure(figsize=(12, 6))
        plt.plot(data['Date'], data['Close'], label="EUR/PLN Close Price", color="blue", alpha=0.6)
        buy_signals = data[data['Signal'] == 'Buy']
        sell_signals = data[data['Signal'] == 'Sell']
        plt.scatter(buy_signals['Date'], buy_signals['Close'], color='green', label='Buy Signal', marker='^', alpha=1)
        plt.scatter(sell_signals['Date'], sell_signals['Close'], color='red', label='Sell Signal', marker='v', alpha=1)
        plt.title("EUR/PLN with Buy/Sell Signals")
        plt.xlabel("Date")
        plt.ylabel("Price (PLN)")
        plt.legend()
        plt.grid()
        st.pyplot(plt)
    except Exception as e:
        st.error(f"Error plotting chart: {e}")

# Main logic
data = fetch_data()
data = calculate_signals(data)

if not data.empty:
    if 'Signal' in data.columns:
        st.write("### EUR/PLN Historical Data (Last 12 Months)")
        st.dataframe(data[['Date', 'Close', 'Signal']])
    else:
        st.error("The 'Signal' column is missing in the data.")

    st.write("### Price Chart with Signals")
    plot_chart(data)
