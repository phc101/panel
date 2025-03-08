import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

# Streamlit App
def main():
    st.title("FX Portfolio Backtesting Tool")
    
    # File Uploads
    st.sidebar.header("Upload Data")
    fx_files = st.sidebar.file_uploader("Upload Currency Pair Prices (5 CSVs)", type=["csv"], accept_multiple_files=True)
    dom_yield_files = st.sidebar.file_uploader("Upload Domestic Bond Yields (5 CSVs)", type=["csv"], accept_multiple_files=True)
    for_yield_file = st.sidebar.file_uploader("Upload Foreign Bond Yield (CSV)", type=["csv"])
    
    # Strategy Selection
    strategy = st.sidebar.radio("Select Strategy", ["Exporter (SELL Only)", "Importer (BUY Only)", "Both (BUY & SELL)"])
    
    # Stop Loss Input
    stop_loss_pct = st.sidebar.slider("Stop Loss (%)", min_value=0.0, max_value=10.0, value=1.5, step=0.1)
    
    if fx_files and dom_yield_files and for_yield_file:
        # Load Foreign Bond Yield
        for_yield_data = pd.read_csv(for_yield_file, parse_dates=["Date"], dayfirst=True)
        for_yield_data["Date"] = pd.to_datetime(for_yield_data["Date"], errors="coerce")
        
        # Load Domestic Bond Yields
        dom_yield_data = None
        for file in dom_yield_files:
            temp_df = pd.read_csv(file, parse_dates=["Date"], dayfirst=True)
            temp_df["Date"] = pd.to_datetime(temp_df["Date"], errors="coerce")
            dom_yield_data = temp_df if dom_yield_data is None else dom_yield_data.merge(temp_df, on="Date")
        
        # Load FX Data
        fx_data = None
        for file in fx_files:
            temp_df = pd.read_csv(file, parse_dates=["Date"], dayfirst=True)
            temp_df["Date"] = pd.to_datetime(temp_df["Date"], errors="coerce")
            fx_data = temp_df if fx_data is None else fx_data.merge(temp_df, on="Date")
        
        # Merge Data
        data = fx_data.merge(dom_yield_data, on="Date").merge(for_yield_data, on="Date").sort_values(by="Date")
        
        # Check if Date is still not recognized as datetime
        if not np.issubdtype(data["Date"].dtype, np.datetime64):
            st.error("Error: Date column is not in datetime format. Please check your input files.")
            return
        
        # Calculate Yield Spreads (Each Domestic Yield - Foreign Yield)
        for i in range(1, 6):  # Assuming 5 domestic yields
            data[f"Yield Spread {i}"] = data.iloc[:, i] - data.iloc[:, -1]
        
        # Train Linear Regression Models for Each Currency Pair
        for i in range(1, 6):  # Assuming 5 currency pairs
            model = LinearRegression()
            model.fit(data[[f"Yield Spread {i}"]], data.iloc[:, i + 5])
            data[f"Predictive Price {i}"] = model.predict(data[[f"Yield Spread {i}"]])
            
            # Establish Trading Strategy
            if strategy == "Importer (BUY Only)":
                data[f"Signal {i}"] = np.where(data.iloc[:, i + 5] < data[f"Predictive Price {i}"], "BUY", np.nan)
            elif strategy == "Exporter (SELL Only)":
                data[f"Signal {i}"] = np.where(data.iloc[:, i + 5] > data[f"Predictive Price {i}"], "SELL", np.nan)
            else:
                data[f"Signal {i}"] = np.where(data.iloc[:, i + 5] < data[f"Predictive Price {i}"], "BUY", "SELL")
            
        data["Weekday"] = data["Date"].dt.weekday
        data = data[data["Weekday"] == 0]  # Filter only Mondays
        data["Exit Date"] = data["Date"] + pd.DateOffset(days=30)
        
        # Calculate Returns for Portfolio
        portfolio_results = []
        for i in range(1, 6):  # Each Currency Pair
            pair_results = []
            for j, row in data.iterrows():
                exit_row = fx_data[fx_data["Date"] == row["Exit Date"]]
                if not exit_row.empty:
                    exit_price = exit_row.iloc[0, i + 1]
                    entry_price = row.iloc[i + 5]
                    stop_loss_price = entry_price * (1 - stop_loss_pct / 100) if row[f"Signal {i}"] == "BUY" else entry_price * (1 + stop_loss_pct / 100)
                    
                    if row[f"Signal {i}"] == "BUY":
                        if exit_price < stop_loss_price:
                            exit_price = stop_loss_price  # Enforce stop loss
                        revenue = (exit_price - entry_price) / entry_price * 100
                    else:
                        if exit_price > stop_loss_price:
                            exit_price = stop_loss_price  # Enforce stop loss
                        revenue = (entry_price - exit_price) / entry_price * 100
                    
                    pair_results.append(revenue)
            portfolio_results.append(pair_results)
        
        # Aggregate Portfolio Performance
        portfolio_returns = np.mean(portfolio_results, axis=0)
        portfolio_cumulative_returns = np.cumsum(portfolio_returns)
        drawdown = np.maximum.accumulate(portfolio_cumulative_returns) - portfolio_cumulative_returns
        
        # Display Results
        st.subheader("Portfolio Backtest Results")
        portfolio_df = pd.DataFrame({"Date": data["Date"], "Portfolio Return %": portfolio_returns, "Cumulative Return %": portfolio_cumulative_returns, "Drawdown %": drawdown})
        st.dataframe(portfolio_df)
        
        # Plot Cumulative Portfolio Revenue
        fig, ax = plt.subplots()
        ax.plot(portfolio_df["Date"], portfolio_df["Cumulative Return %"], marker='o', linestyle='-', label="Cumulative Portfolio Return")
        ax.set_title("Cumulative Portfolio Return Over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Cumulative Return %")
        ax.legend()
        st.pyplot(fig)
        
        # Plot Negative Drawdown
        fig, ax = plt.subplots()
        ax.plot(portfolio_df["Date"], -portfolio_df["Drawdown %"], color='red', linestyle='-', label="Negative Drawdown")
        ax.set_title("Negative Drawdown Over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Drawdown %")
        ax.legend()
        st.pyplot(fig)

if __name__ == "__main__":
    main()
