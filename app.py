
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
    ticker = "EURPLN=X"  # Yahoo Finance ticker for EUR/PLN
    data = yf.download(ticker, period="1y", interval="1d")
    data['Date'] = data.index
    return data

# Calculate signals based on Z-score
def calculate_signals(data, window=20):
    data['Mean'] = data['Close'].rolling(window=window).mean()
    data['StdDev'] = data['Close'].rolling(window=window).std()
    data['Z-Score'] = (data['Close'] - data['Mean']) / data['StdDev']
    data['Signal'] = np.where(data['Z-Score'] < -2, 'Buy',
                     np.where(data['Z-Score'] > 2, 'Sell', 'Hold'))
    return data

# Plot the price chart with buy/sell signals
def plot_chart(data):
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

# Main logic
data = fetch_data()
data = calculate_signals(data)

# Display data and chart
st.write("### EUR/PLN Historical Data (Last 12 Months)")
st.dataframe(data[['Date', 'Close', 'Signal']])

st.write("### Price Chart with Signals")
plot_chart(data)
