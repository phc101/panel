import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

# Title and description
st.title("EUR/PLN Z-Score Strategy Comparison")
st.write("This app calculates Z-scores based on the last 20 days of close prices and compares buy, sell, and combined strategies with settlement periods of 30, 60, and 90 days.")

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
    data['signal'] = np.where(data['z_score'] < -2, 'Buy',
                              np.where(data['z_score'] > 2, 'Sell', 'Hold'))

    # Backtesting buy, sell, and combined strategies
    strategies = {'Buy': data[data['signal'] == 'Buy'].copy(),
                  'Sell': data[data['signal'] == 'Sell'].copy()}

    for strategy, strategy_data in strategies.items():
        for days in [30, 60, 90]:
            settlement_col = f'settlement_close_{days}'
            return_col = f'return_{days}'

            strategy_data[f'settlement_date_{days}'] = strategy_data['date'].shift(-days)
            strategy_data[settlement_col] = strategy_data['close'].shift(-days)

            if strategy == 'Buy':
                strategy_data[return_col] = (strategy_data[settlement_col] - strategy_data['close']) / strategy_data['close']
            elif strategy == 'Sell':
                strategy_data[return_col] = (strategy_data['close'] - strategy_data[settlement_col]) / strategy_data['close']

        strategies[strategy] = strategy_data

    # Combined strategy
    combined_data = pd.concat([strategies['Buy'], strategies['Sell']]).sort_values(by='date')
    combined_data['combined_return'] = (
        combined_data['return_30'] + combined_data['return_60'] + combined_data['return_90']) / 3
    combined_data['combined_cumulative'] = (1 + combined_data['combined_return']).cumprod()

    # Cumulative returns for visualization
    for strategy, strategy_data in strategies.items():
        strategy_data['cumulative_return'] = (1 + strategy_data['return_30']).cumprod()

    # Visualization of cumulative returns
    st.subheader("Cumulative Returns")
    plt.figure(figsize=(12, 6))
    plt.plot(strategies['Buy']['date'], strategies['Buy']['cumulative_return'], label='Buy Strategy', color='green')
    plt.plot(strategies['Sell']['date'], strategies['Sell']['cumulative_return'], label='Sell Strategy', color='red')
    plt.plot(combined_data['date'], combined_data['combined_cumulative'], label='Combined Strategy', color='blue', linestyle='--')
    plt.title("Cumulative Returns: Buy, Sell, and Combined Strategies")
    plt.xlabel("Date")
    plt.ylabel("Cumulative Return")
    plt.legend()
    plt.grid()
    st.pyplot(plt)

    # Annual returns and drawdowns for all strategies
    st.subheader("Annual Returns and Drawdowns")
    for strategy_name, strategy_data in strategies.items():
        strategy_data['year'] = strategy_data['date'].dt.year
        annual_returns = strategy_data.groupby('year')[[f'return_{days}' for days in [30, 60, 90]]].sum()

        strategy_data['drawdown'] = strategy_data['cumulative_return'] / strategy_data['cumulative_return'].cummax() - 1
        annual_drawdowns = strategy_data.groupby('year')['drawdown'].min()

        st.write(f"{strategy_name} Strategy Annual Returns")
        st.write(annual_returns)

        st.write(f"{strategy_name} Strategy Annual Drawdowns")
        st.write(annual_drawdowns)

    # Combined strategy annual performance
    combined_data['year'] = combined_data['date'].dt.year
    combined_annual_returns = combined_data.groupby('year')['combined_return'].sum()
    combined_annual_drawdowns = combined_data.groupby('year')['combined_cumulative'].apply(lambda x: (x / x.cummax() - 1).min())

    st.write("Combined Strategy Annual Returns")
    st.write(combined_annual_returns)

    st.write("Combined Strategy Annual Drawdowns")
    st.write(combined_annual_drawdowns)

    # Download data
    st.subheader("Download Strategy Data")
    for strategy_name, strategy_data in strategies.items():
        csv = strategy_data.to_csv(index=False)
        st.download_button(f"Download {strategy_name} Strategy Data", data=csv, file_name=f"{strategy_name.lower()}_strategy_results.csv", mime="text/csv")

    combined_csv = combined_data.to_csv(index=False)
    st.download_button("Download Combined Strategy Data", data=combined_csv, file_name="combined_strategy_results.csv", mime="text/csv")

# Load and process EUR/PLN data
st.subheader("Upload EUR/PLN Data")
eurpln_file = st.file_uploader("Upload EUR/PLN Excel file:", type=["xlsx"])
if eurpln_file:
    eurpln_data = load_data(eurpln_file)
    if not eurpln_data.empty:
        process_and_visualize(eurpln_data)
