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
    data = yf.download(ticker, period="1mo", interval="1d")
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

    # Rolling calculations
    data['Mean_20'] = data['Close'].rolling(window=20).mean()
    data['Std_20'] = data['Close'].rolling(window=20).std()

    # Avoid NaN values for Z-Score calculation
    data['Z_Score'] = np.where(data['Std_20'] > 0, (data['Close'] - data['Mean_20']) / data['Std_20'], np.nan)
    data['Up_Probability'] = np.where(data['Z_Score'].notna(), 1 - (1 - np.abs(data['Z_Score']).map(lambda x: min(0.5 + 0.5 * np.tanh(x / 2), 1))), np.nan)

    # Signal generation
    data['Signal'] = np.where((data['Z_Score'] < -2) & (data['Up_Probability'] > 0.95), 'Buy',
                              np.where((data['Z_Score'] > 2) & (data['Up_Probability'] < 0.05), 'Sell', 'Hold'))

    # Debugging: Check column H (Up_Probability)
    st.subheader("Debugging Column H (Up_Probability)")
    st.write("Up_Probability Summary:")
    st.write(data['Up_Probability'].describe())
    st.write("Signals Generated:")
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
