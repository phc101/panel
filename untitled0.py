import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import yfinance as yf

# Title and description
st.title("EUR/PLN Z-Score Signal Generator")
st.write("This app calculates Z-scores based on the last 20 days of EUR/PLN close prices and generates buy/sell signals.")

# Fetch live data
def fetch_live_data():
    ticker = "EURPLN=X"
    data = yf.download(ticker, period="6mo", interval="1d")
    data = data.reset_index()
    data = data.rename(columns={"Date": "Date", "Close": "Close"})
    return data[["Date", "Close"]]

# Load data
data = fetch_live_data()

if data.empty:
    st.error("Failed to fetch live data. Please try again later.")
else:
    # Data preparation
    data['Date'] = pd.to_datetime(data['Date'])
    data = data.sort_values(by='Date')

    # Apply 1-month delay
    data = data.iloc[30:].reset_index(drop=True)

    # Rolling calculations
    data['Mean_20'] = data['Close'].rolling(window=20).mean()
    data['Std_20'] = data['Close'].rolling(window=20).std()

    # Debug: Check rolling calculations
    st.write("Rolling Calculations Preview:")
    st.write(data[['Date', 'Close', 'Mean_20', 'Std_20']].tail(20))

    # Filter rows with sufficient data for rolling calculations
    data = data[data['Mean_20'].notna() & data['Std_20'].notna()]

    # Avoid division by zero or invalid operations
    data = data[data['Std_20'] > 0]

    # Calculate Z-Score and probabilities
    data['Z_Score'] = (data['Close'] - data['Mean_20']) / data['Std_20']
    data['Z_Score'].replace([np.inf, -np.inf], np.nan, inplace=True)
    data['Z_Score'].fillna(0, inplace=True)

    data['Up_Probability'] = 1 - (1 - np.abs(data['Z_Score']).map(lambda x: min(0.5 + 0.5 * np.tanh(x / 2), 1)))

    # Signal generation
    data['Signal'] = np.where((data['Z_Score'] < -2) & (data['Up_Probability'] > 0.95), 'Buy',
                              np.where((data['Z_Score'] > 2) & (data['Up_Probability'] < 0.05), 'Sell', 'Hold'))

    # Debugging: Check Z-Score and Signal columns
    st.subheader("Debugging Z-Score and Signals")
    st.write("Z-Score and Signal Preview:")
    st.write(data[['Date', 'Close', 'Z_Score', 'Up_Probability', 'Signal']].tail(20))

    # Display results
    st.subheader("Data Preview")
    st.write(data[['Date', 'Close', 'Mean_20', 'Std_20', 'Z_Score', 'Up_Probability', 'Signal']].tail(20))

    # Display signals as a table
    st.subheader("Buy and Sell Signals")
    signal_data = data[data['Signal'].isin(['Buy', 'Sell'])][['Date', 'Close', 'Signal']]
    st.write(signal_data)

    # Visualization
    st.subheader("Z-Score and Signals")
    plt.figure(figsize=(10, 6))
    plt.plot(data['Date'], data['Close'], label='Close Price', alpha=0.7)
    plt.scatter(data['Date'][data['Signal'] == 'Buy'], data['Close'][data['Signal'] == 'Buy'], label='Buy Signal', color='green', marker='^')
    plt.scatter(data['Date'][data['Signal'] == 'Sell'], data['Close'][data['Signal'] == 'Sell'], label='Sell Signal', color='red', marker='v')
    plt.title("EUR/PLN Close Price and Signals")
    plt.legend()
    plt.grid()
    st.pyplot(plt)

    st.subheader("Download Results")
    csv = data.to_csv(index=False)
    st.download_button("Download CSV", data=csv, file_name="zscore_signals.csv", mime="text/csv")
