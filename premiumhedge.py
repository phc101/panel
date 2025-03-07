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
    strategy = st.sidebar.radio("Select Strategy", ["Exporter (SELL Only)", "Importer (BUY Only)"])
    
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
        else:
            data = data[data.iloc[:, 3] > data["Predictive Price"]]
            data["Signal"] = "SELL"
        
        data["Weekday"] = data["Date"].dt.weekday
        data = data[data["Weekday"] == 0]  # Filter only Mondays
        data["Exit Date"] = data["Date"] + pd.DateOffset(days=30)
        
        # Calculate Returns
        results = []
        stop_loss_pct = 1.5  # Set stop loss at 1.5%
        
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
        
        # Display Results
        st.subheader("Backtest Results")
        st.dataframe(result_df)
        
        # Plot Cumulative Revenue
        fig, ax = plt.subplots()
        ax.plot(result_df["Entry Date"], result_df["Cumulative Revenue %"], marker='o', linestyle='-')
        ax.set_title(f"Cumulative Revenue Over Time ({strategy})")
        ax.set_xlabel("Date")
        ax.set_ylabel("Cumulative Revenue %")
        st.pyplot(fig)
        
        # Calculate Yearly Returns
        result_df["Year"] = pd.to_datetime(result_df["Entry Date"]).dt.year
        yearly_returns = result_df.groupby("Year")["Revenue %"].sum()
        
        # Plot Yearly Returns Bar Chart
        fig, ax = plt.subplots()
        yearly_returns.plot(kind='bar', ax=ax)
        ax.set_title(f"Yearly Returns ({strategy})")
        ax.set_xlabel("Year")
        ax.set_ylabel("Total Revenue %")
        st.pyplot(fig)

if __name__ == "__main__":
    main()
