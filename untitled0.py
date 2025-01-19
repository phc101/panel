import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import requests

# Title and description
st.title("EUR/PLN Z-Score Signal Generator")
st.write("This app calculates Z-scores based on the last 20 days of EUR/PLN close prices and generates buy/sell signals.")

# Fetch live data from Alpha Vantage
def fetch_live_data(api_key):
    url = f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=EUR&to_symbol=PLN&apikey={api_key}&datatype=csv"
    response = requests.get(url)
    if response.status_code == 200:
        data = pd.read_csv(pd.compat.StringIO(response.text))
        data = data.rename(columns={"timestamp": "Date", "close": "Close"})
        data['Date'] = pd.to_datetime(data['Date'])
        return data[['Date', 'Close']]
    else:
        st.error("Failed to fetch live data. Please check your API key or try again later.")
        return pd.DataFrame()

# Enter your Alpha Vantage API key
api_key = st.text_input("Enter your Alpha Vantage API key:", type="password")

if api_key:
    # Load data
    data = fetch_live_data(api_key)

    if not data.empty:
        # Data preparation
        data = data.sort_values(by='Date')

        # Keep only the last 20 days
        data = data.tail(20).reset_index(drop=True)

        # Rolling calculations
        data['Mean_20'] = data['Close'].rolling(window=20).mean()
        data['Std_20'] = data['Close'].rolling(window=20).std()

        # Filter rows with valid rolling calculations
        data = data[data['Mean_20'].notna() & data['Std_20'].notna()]

        # Calculate Z-Score and probabilities
        data['Z_Score'] = (data['Close'] - data['Mean_20']) / data['Std_20']
        data['Z_Score'] = data['Z_Score'].replace([np.inf, -np.inf], np.nan).fillna(0)

        data['Up_Probability'] = 1 - (1 - np.abs(data['Z_Score']).map(lambda x: min(0.5 + 0.5 * np.tanh(x / 2), 1)))

        # Signal generation
        data['Signal'] = np.where((data['Z_Score'] < -2) & (data['Up_Probability'] > 0.95), 'Buy',
                                  np.where((data['Z_Score'] > 2) & (data['Up_Probability'] < 0.05), 'Sell', 'Hold'))

        # Display results
        st.subheader("Data Preview")
        st.write(data[['Date', 'Close', 'Mean_20', 'Std_20', 'Z_Score', 'Up_Probability', 'Signal']])

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
    else:
        st.error("No data available to process.")
