import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

def main():
    st.title("FX Valuation Backtesting Tool")

    # File Uploads
    st.sidebar.header("Upload Data")
    fx_file = st.sidebar.file_uploader("Upload Currency Pair Prices (CSV)", type=["csv"])
    dom_yield_file = st.sidebar.file_uploader("Upload Domestic Bond Yields (CSV)", type=["csv"])
    for_yield_file = st.sidebar.file_uploader("Upload Foreign Bond Yields (CSV)", type=["csv"])

    if fx_file and dom_yield_file and for_yield_file:
        # Load Data
        fx_data = pd.read_csv(fx_file, parse_dates=["Date"], dayfirst=True)
        dom_yield_data = pd.read_csv(dom_yield_file, parse_dates=["Date"], dayfirst=True)
        for_yield_data = pd.read_csv(for_yield_file, parse_dates=["Date"], dayfirst=True)

        # Convert Date column to datetime
        for df in [fx_data, dom_yield_data, for_yield_data]:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        # Merge Data
        data = fx_data.merge(dom_yield_data, on="Date").merge(for_yield_data, on="Date").sort_values(by="Date")

        if not np.issubdtype(data["Date"].dtype, np.datetime64):
            st.error("Error: Date column is not in datetime format. Please check your input files.")
            return

        # Compute Yield Spread
        data["Yield Spread"] = data.iloc[:, 1] - data.iloc[:, 2]

        # Train Linear Regression Model
        model = LinearRegression()
        model.fit(data[["Yield Spread"]], data.iloc[:, 3])
        data["Predictive Price"] = model.predict(data[["Yield Spread"]])

        # Leverage selection
        leverage = st.sidebar.slider("Leverage (x)", min_value=1, max_value=20, value=1)
        stop_loss_pct = st.sidebar.slider("Stop Loss (%)", min_value=0.0, max_value=10.0, value=1.5, step=0.5)

        # Strategy selection
        strategy = st.sidebar.selectbox("Strategy Mode", ("Both", "Buy Only", "Sell Only", "Stablecoin Yield"))

        # Establish Trading Strategy
        data["Signal"] = np.where(data.iloc[:, 3] < data["Predictive Price"], "BUY", "SELL")
        data["Weekday"] = data["Date"].dt.weekday
        data = data[data["Weekday"] == 0]
        data["Exit Date"] = data["Date"] + pd.DateOffset(days=30)

        if strategy == "Buy Only":
            data = data[data["Signal"] == "BUY"]
        elif strategy == "Sell Only":
            data = data[data["Signal"] == "SELL"]

        # Calculate Returns
        results = []
        for i, row in data.iterrows():
            exit_row = fx_data[fx_data["Date"] == row["Exit Date"]]
            if not exit_row.empty:
                exit_price = exit_row.iloc[0, 1]
                entry_price = row.iloc[3]
                stop_loss_price = entry_price * (1 - stop_loss_pct / 100) if row["Signal"] == "BUY" else entry_price * (1 + stop_loss_pct / 100)

                if strategy == "Stablecoin Yield":
                    revenue = (0.40 / 12) * 100  # 0.40% annual, converted to monthly
                elif row["Signal"] == "BUY":
                    if exit_price < stop_loss_price:
                        exit_price = stop_loss_price
                    revenue = (exit_price - entry_price) / entry_price * 100 * leverage
                else:
                    if exit_price > stop_loss_price:
                        exit_price = stop_loss_price
                    revenue = (entry_price - exit_price) / entry_price * 100 * leverage

                results.append([row["Date"], row["Exit Date"], row["Signal"], entry_price, exit_price, revenue])

        result_df = pd.DataFrame(results, columns=["Entry Date", "Exit Date", "Signal", "Entry Price", "Exit Price", "Revenue %"])
        result_df["Cumulative Revenue %"] = result_df["Revenue %"].cumsum()
        result_df["Drawdown %"] = result_df["Cumulative Revenue %"].cummax() - result_df["Cumulative Revenue %"]

        # Display Results
        st.subheader("Backtest Results")

        # Plot Currency Price vs Predictive Price
        fig, ax = plt.subplots()
        ax.plot(data["Date"], data.iloc[:, 3], linestyle='-', linewidth=1, color='blue', label="Actual Price")
        ax.plot(data["Date"], data["Predictive Price"], linestyle='--', linewidth=1, color='orange', label="Predictive Price")
        ax.set_title("Actual vs Predictive Price Over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price")
        ax.legend()
        st.pyplot(fig)
        st.dataframe(result_df)

        # Plot Cumulative Revenue
        fig, ax = plt.subplots()
        ax.plot(result_df["Entry Date"], result_df["Cumulative Revenue %"], linestyle='-', linewidth=1, color='blue', label="Cumulative Revenue")
        ax.set_title("Cumulative Revenue Over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Cumulative Revenue %")
        ax.legend()
        st.pyplot(fig)

        # Plot Negative Drawdown
        fig, ax = plt.subplots()
        ax.plot(result_df["Entry Date"], -result_df["Drawdown %"], color='red', linestyle='-', linewidth=1, label="Negative Drawdown")
        ax.set_title("Negative Drawdown Over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Drawdown %")
        ax.legend()
        st.pyplot(fig)

if __name__ == "__main__":
    main()
