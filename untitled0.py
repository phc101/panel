import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

# Title and description
st.title("EUR/PLN and USD/PLN Z-Score Signal Generator")
st.write("This app calculates Z-scores based on the last 20 days of close prices and generates buy/sell signals with multiple settlement strategies, including a combined strategy.")

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
def process_and_visualize(data, pair):
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

    # Backtesting strategies
    for days in [30, 60, 90]:
        settlement_col = f'settlement_close_{days}'
        return_col = f'return_{days}'

        data[f'settlement_date_{days}'] = data['date'].shift(-days)
        data[settlement_col] = data['close'].shift(-days)

        data[return_col] = np.where(data['signal'] == 'Buy',
                                     (data[settlement_col] - data['close']) / data['close'],
                                     np.where(data['signal'] == 'Sell',
                                              (data['close'] - data[settlement_col]) / data['close'],
                                              0))

    # Combined strategy: Open positions for 30, 60, and 90 days simultaneously
    data['combined_return'] = (
        data['return_30'] + data['return_60'] + data['return_90']) / 3
    data['combined_cumulative'] = (1 + data['combined_return']).cumprod()

    # Separate Buy and Sell strategies for combined
    buy_combined = data[data['signal'] == 'Buy'][['date', 'combined_return']].copy()
    sell_combined = data[data['signal'] == 'Sell'][['date', 'combined_return']].copy()
    buy_combined['cumulative'] = (1 + buy_combined['combined_return']).cumprod()
    sell_combined['cumulative'] = (1 + sell_combined['combined_return']).cumprod()

    # Risk assessment
    strategies = ['return_30', 'return_60', 'return_90', 'combined_return']
    assessments = []
    for strategy in strategies:
        avg_drawdown = data[data['signal'] != 'Hold'].groupby('signal')[strategy].apply(lambda x: (x[x < 0]).mean())
        avg_gain_loss = data[data['signal'] != 'Hold'].groupby('signal')[strategy].mean()
        num_positive = data[data['signal'] != 'Hold'].groupby('signal')[strategy].apply(lambda x: (x > 0).sum())
        num_negative = data[data['signal'] != 'Hold'].groupby('signal')[strategy].apply(lambda x: (x < 0).sum())
        assessments.append(pd.DataFrame({
            'Strategy': strategy,
            'Avg Drawdown': avg_drawdown,
            'Avg Gain/Loss': avg_gain_loss,
            'Num Positive Trades': num_positive,
            'Num Negative Trades': num_negative
        }))

    combined_assessment = pd.concat(assessments)
    st.subheader(f"Risk Assessment for {pair}")
    st.write(combined_assessment)

    # Visualize cumulative returns
    st.subheader(f"Cumulative Returns of {pair} Strategy")
    plt.figure(figsize=(10, 6))
    for days in [30, 60, 90]:
        cumulative_col = f'cumulative_return_{days}'
        data[cumulative_col] = (1 + data[f'return_{days}']).cumprod()
        plt.plot(data['date'], data[cumulative_col], label=f'{days} Days')
    plt.plot(data['date'], data['combined_cumulative'], label='Combined Strategy', linewidth=2, linestyle='--', color='black')
    plt.title(f"Cumulative Returns for {pair}")
    plt.legend()
    plt.grid()
    st.pyplot(plt)

    # Separate plots for Buy and Sell combined strategies
    st.subheader(f"Buy Combined Strategy Cumulative Returns for {pair}")
    plt.figure(figsize=(10, 6))
    plt.plot(buy_combined['date'], buy_combined['cumulative'], label='Buy Combined', color='green')
    plt.title(f"Buy Combined Strategy Cumulative Returns for {pair}")
    plt.legend()
    plt.grid()
    st.pyplot(plt)

    st.subheader(f"Sell Combined Strategy Cumulative Returns for {pair}")
    plt.figure(figsize=(10, 6))
    plt.plot(sell_combined['date'], sell_combined['cumulative'], label='Sell Combined', color='red')
    plt.title(f"Sell Combined Strategy Cumulative Returns for {pair}")
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
