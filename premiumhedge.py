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
        
        # Debugging: Print columns to detect differences in BTC/USD files
        st.write("Detected Columns:", data.columns.tolist())
        
        # Identify numeric columns for price and yield spread calculation
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 3:
            st.error("Error: Not enough numeric columns detected. Check the uploaded files.")
            return
        
        # Compute Yield Spread dynamically
        data["Yield Spread"] = data[numeric_cols[0]] - data[numeric_cols[1]]
        
        # Train Linear Regression Model
        model = LinearRegression()
        valid_data = data[["Yield Spread", numeric_cols[2]]].dropna()
        if valid_data.empty:
            st.error("Error: No valid data available for training. Check your input files.")
            return
        model.fit(valid_data[["Yield Spread"]], valid_data[numeric_cols[2]])
        data["Predictive Price"] = model.predict(data[["Yield Spread"]].fillna(method='ffill'))
        
        # Establish Trading Strategy
        data["Signal"] = np.where(data[numeric_cols[2]] < data["Predictive Price"], "BUY", "SELL")
        data["Weekday"] = data["Date"].dt.weekday
        data = data[data["Weekday"] == 0]  # Filter only Mondays
        data["Exit Date"] = data["Date"] + pd.DateOffset(days=30)
        
        # Calculate Returns
        results = []
        stop_loss_pct = st.sidebar.slider("Stop Loss (%)", min_value=0.0, max_value=10.0, value=1.5, step=0.5)
        
        for i, row in data.iterrows():
            revenue = np.nan  # Initialize revenue to avoid UnboundLocalError
            exit_row = fx_data[fx_data["Date"] == row["Exit Date"]]
            if not exit_row.empty:
                exit_price = pd.to_numeric(exit_row.iloc[0, 1], errors='coerce')
                entry_price = row[numeric_cols[2]]
                stop_loss_price = pd.to_numeric(entry_price * (1 - stop_loss_pct / 100) if row["Signal"] == "BUY" else entry_price * (1 + stop_loss_pct / 100), errors='coerce')
                
                if row["Signal"] == "BUY" and not np.isnan(exit_price) and not np.isnan(stop_loss_price):
                    if exit_price < stop_loss_price:
                        exit_price = stop_loss_price  # Enforce stop loss
                    revenue = (exit_price - entry_price) / entry_price * 100
                elif not np.isnan(exit_price) and not np.isnan(stop_loss_price):
                    if exit_price > stop_loss_price:
                        exit_price = stop_loss_price  # Enforce stop loss
                    revenue = (entry_price - exit_price) / entry_price * 100
                
                if not np.isnan(revenue):
                    results.append([row["Date"], row["Exit Date"], row["Signal"], entry_price, exit_price, revenue])
        
        result_df = pd.DataFrame(results, columns=["Entry Date", "Exit Date", "Signal", "Entry Price", "Exit Price", "Revenue %"])
        result_df["Cumulative Revenue %"] = result_df["Revenue %"].cumsum()
        result_df["Drawdown %"] = result_df["Cumulative Revenue %"].cummax() - result_df["Cumulative Revenue %"]
        
        # Display Results
        st.subheader("Backtest Results")
        st.dataframe(result_df)

if __name__ == "__main__":
    main()
