import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

# Title and description
st.title("EUR/PLN Z-Score Sell Strategy")
st.write("This app calculates Z-scores based on the last 20 days of close prices and evaluates the sell strategy with settlement periods of 30, 60, and 90 days.")

# Load data from uploaded file
def load_data(file_path):
    try:
        data = pd.read_excel(file_path)
        data.columns = data.columns.str.strip().str.lower()  # Normalize column names
        if 'date' in data.columns and 'close' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
            return data[['date', 'close']]
        else:
            st.error("The uploaded file must contain 'Date' and 'Close' columns.")
            st.write("Detected columns:", data.columns.tolist())  # Debugging output
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Function to process and visualize data
def process_and_visualize(data):
    # Data preparation
    data = data.sort_values(by='date')

    # Rolling calculations
    data['mean_20'] = data['close'].rolling(window=20).mean()
    data['std_20'] = data['close'].rolling(window=20).std()

    # Filter rows with valid rolling calculations
    data = data[data['mean_20'].notna() & data['std_20'].notna()]

    # Calculate Z-Score
    data['z_score'] = (data['close'] - data['mean_20']) / data['std_20']
    data['z_score'] = data['z_score'].replace([np.inf, -np.inf], np.nan).fillna(0)

    # Signal generation based on Z-Score
    data['signal'] = np.where(data['z_score'] > 2, 'Sell', 'Hold')

    # Backtesting sell strategy
    sell_data = data[data['signal'] == 'Sell'].copy()
    for days in [30, 60, 90]:
        settlement_col = f'settlement_close_{days}'
        return_col = f'return_{days}'

        sell_data[f'settlement_date_{days}'] = sell_data['date'].shift(-days)
        sell_data[settlement_col] = sell_data['close'].shift(-days)

        sell_data[return_col] = (sell_data['close'] - sell_data[settlement_col]) / sell_data['close']

    # Calculate total annual returns and drawdowns
    sell_data['year'] = sell_data['date'].dt.year
    annual_returns = sell_data.groupby('year')[[f'return_{days}' for days in [30, 60, 90]]].sum()

    # Calculate drawdowns
    sell_data['cumulative_return'] = (1 + sell_data['return_30']).cumprod()
    sell_data['drawdown'] = sell_data['cumulative_return'] / sell_data['cumulative_return'].cummax() - 1

    # Visualization of annual returns with drawdowns
    st.subheader("Annual Returns and Drawdowns")
    plt.figure(figsize=(12, 6))
    for days in [30, 60, 90]:
        plt.bar(annual_returns.index, annual_returns[f'return_{days}'], label=f'{days}-Day Returns', alpha=0.7)
    plt.plot(sell_data['year'], sell_data.groupby('year')['drawdown'].min(), label='Max Drawdown', color='red', linestyle='--')
    plt.axhline(0, color='black', linewidth=0.8, linestyle='--')
    plt.title("Annual Returns and Maximum Drawdowns")
    plt.xlabel("Year")
    plt.ylabel("Returns / Drawdowns")
    plt.legend()
    plt.grid()
    st.pyplot(plt)

    # Display data
    st.subheader("Sell Strategy Data")
    st.write(sell_data[['date', 'close', 'z_score', 'signal', 'cumulative_return', 'drawdown'] + \
                       [f'return_{days}' for days in [30, 60, 90]]])

    # Download data
    st.subheader("Download Sell Strategy Data")
    csv = sell_data.to_csv(index=False)
    st.download_button("Download CSV", data=csv, file_name="sell_strategy_results.csv", mime="text/csv")

# Load and process EUR/PLN data
st.subheader("Upload EUR/PLN Data")
eurpln_file = st.file_uploader("Upload EUR/PLN Excel file:", type=["xlsx"])
if eurpln_file:
    eurpln_data = load_data(eurpln_file)
    if not eurpln_data.empty:
        process_and_visualize(eurpln_data)
