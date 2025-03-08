import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

# Streamlit App
def main():
    st.title("FX Valuation Backtesting Tool")
    
    # File Uploads
    st.sidebar.header("Upload Data")
    fx_file = st.sidebar.file_uploader("Upload Currency Pair Prices (CSV)", type=["csv"])
    dom_yield_file = st.sidebar.file_uploader("Upload Domestic Bond Yields (CSV)", type=["csv"])
    for_yield_file = st.sidebar.file_uploader("Upload Foreign Bond Yields (CSV)", type=["csv"])
    
    # Strategy Selection
    strategy = st.sidebar.radio("Select Strategy", ["Exporter (SELL Only)", "Importer (BUY Only)", "Both (BUY & SELL)"])
    
    # Stop Loss Input
    stop_loss_pct = st.sidebar.slider("Stop Loss (%)", min_value=0.0, max_value=10.0, value=1.5, step=0.1)
    
    if fx_file and dom_yield_file and for_yield_file:
        # Ensure Date column is correctly parsed as datetime
        fx_data = pd.read_csv(fx_file, parse_dates=["Date"], dayfirst=True)
        dom_yield_data = pd.read_csv(dom_yield_file, parse_dates=["Date"], dayfirst=True)
        for_yield_data = pd.read_csv(for_yield_file, parse_dates=["Date"], dayfirst=True)

        # Convert Date column to datetime (if it isn't already)
        fx_data["Date"] = pd.to_datetime(fx_data["Date"], errors="coerce")
        dom_yield_data["Date"] = pd.to_datetime(dom_yield_data["Date"], errors="coerce")
        for_yield_data["Date"] = pd.to_datetime(for_yield_data["Date"], errors="coerce")

        # Merge Data
        data = fx_data.merge(dom_yield_data, on="Date").merge(for_yield_data, on="Date").sort_values(by="Date")

        # Check if Date is still not recognized as datetime
        if not np.issubdtype(data["Date"].dtype, np.datetime64):
            st.error("Error: Date column is not in datetime format. Please check your input files.")
            return

        data["Yield Spread"] = data.iloc[:, 1] - data.iloc[:, 2]
        
        # Train Linear Regression Model
        model = LinearRegression()
        model.fit(data[["Yield Spread"]], data.iloc[:, 3])
        data["Predictive Price"] = model.predict(data[["Yield Spread"]])
        
        # Establish Trading Strategy
        if strategy == "Importer (BUY Only)":
            data = data[data.iloc[:, 3] < data["Predictive Price"]]
            data["Signal"] = "BUY"
        elif strategy == "Exporter (SELL Only)":
            data = data[data.iloc[:, 3] > data["Predictive Price"]]
            data["Signal"] = "SELL"
        else:
            data["Signal"] = np.where(data.iloc[:, 3] < data["Predictive Price"], "BUY", "SELL")
        
        data["Weekday"] = data["Date"].dt.weekday
        data = data[data["Weekday"] == 0]  # Filter only Mondays
        data["Exit Date"] = data["Date"] + pd.DateOffset(days=30)
        
        # Calculate Returns
        results = []
        
        for i, row in data.iterrows():
            exit_row = fx_data[fx_data["Date"] == row["Exit Date"]]
            if not exit_row.empty:
                exit_price = exit_row.iloc[0, 1]
                entry_price = row.iloc[3]
                stop_loss_price = entry_price * (1 - stop_loss_pct / 100) if row["Signal"] == "BUY" else entry_price * (1 + stop_loss_pct / 100)
                
                if row["Signal"] == "BUY":
                    if exit_price < stop_loss_price:
                        exit_price = stop_loss_price  # Enforce stop loss
                    revenue = (exit_price - entry_price) / entry_price * 100
                else:
                    if exit_price > stop_loss_price:
                        exit_price = stop_loss_price  # Enforce stop loss
                    revenue = (entry_price - exit_price) / entry_price * 100
                
                results.append([row["Date"], row["Exit Date"], row["Signal"], entry_price, exit_price, revenue])
        
        result_df = pd.DataFrame(results, columns=["Entry Date", "Exit Date", "Signal", "Entry Price", "Exit Price", "Revenue %"])
        result_df["Cumulative Revenue %"] = result_df["Revenue %"].cumsum()
        result_df["Drawdown %"] = result_df["Cumulative Revenue %"].cummax() - result_df["Cumulative Revenue %"]
        
        # Calculate Yearly Performance Metrics
        result_df["Year"] = pd.to_datetime(result_df["Entry Date"]).dt.year
        yearly_performance = result_df.groupby("Year").agg({
            "Revenue %": ["sum", "count", "max", "min", "mean"],
            "Drawdown %": "mean"
        })
        yearly_performance.columns = ["Total Return %", "Number of Trades", "Best Trade %", "Worst Trade %", "Average Return %", "Average Drawdown %"]
        
        # Display Yearly Performance Table
        st.subheader("Yearly Performance Table")
        st.dataframe(yearly_performance)
        
        # Plot Yearly Performance Bar Chart
        fig, ax = plt.subplots()
        yearly_performance["Total Return %"].plot(kind='bar', ax=ax, color='blue')
        ax.set_title("Yearly Total Return")
        ax.set_xlabel("Year")
        ax.set_ylabel("Total Return %")
        st.pyplot(fig)

if __name__ == "__main__":
    main()
