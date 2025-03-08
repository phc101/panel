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
        for_yield_data = for_yield_data.dropna(subset=["Date"])  # Ensure no missing dates
        for_yield_data = for_yield_data.rename(columns={for_yield_data.columns[-1]: "Foreign Bond Yield"})  # Explicit naming
        for_yield_data["Foreign Bond Yield"] = pd.to_numeric(for_yield_data["Foreign Bond Yield"], errors="coerce")
        
        # Load Domestic Bond Yields
        dom_yield_data = None
        for i, file in enumerate(dom_yield_files, start=1):
            temp_df = pd.read_csv(file, parse_dates=["Date"], dayfirst=True)
            temp_df["Date"] = pd.to_datetime(temp_df["Date"], errors="coerce")
            temp_df = temp_df.dropna(subset=["Date"])  # Ensure no missing dates
            temp_df = temp_df.rename(columns={temp_df.columns[-1]: f"Domestic Yield {i}"})  # Rename column
            temp_df[f"Domestic Yield {i}"] = pd.to_numeric(temp_df[f"Domestic Yield {i}"], errors="coerce")
            dom_yield_data = temp_df if dom_yield_data is None else dom_yield_data.merge(temp_df, on="Date", how="outer", suffixes=(None, f"_{i}"))
        
        # Load FX Data
        fx_data = None
        for i, file in enumerate(fx_files, start=1):
            temp_df = pd.read_csv(file, parse_dates=["Date"], dayfirst=True)
            temp_df["Date"] = pd.to_datetime(temp_df["Date"], errors="coerce")
            temp_df = temp_df.dropna(subset=["Date"])  # Ensure no missing dates
            temp_df = temp_df.rename(columns={temp_df.columns[-1]: f"FX Pair {i}"})  # Rename column
            fx_data = temp_df if fx_data is None else fx_data.merge(temp_df, on="Date", how="outer", suffixes=(None, f"_{i}"))
        
        # Merge Data
        data = fx_data.merge(dom_yield_data, on="Date", how="outer").merge(for_yield_data, on="Date", how="outer").sort_values(by="Date")
        
        # Check if Date is still not recognized as datetime
        if not np.issubdtype(data["Date"].dtype, np.datetime64):
            st.error("Error: Date column is not in datetime format. Please check your input files.")
            return
        
        # Forward fill missing data to align time series
        data = data.ffill()
        
        # Ensure Foreign Bond Yield exists before computing spreads
        if "Foreign Bond Yield" not in data.columns:
            st.error("Error: Foreign Bond Yield column is missing. Ensure correct file upload.")
            return
        
        # Calculate Yield Spreads (Each Domestic Yield - Foreign Yield)
        for i in range(1, 6):  # Assuming 5 domestic yields
            if f"Domestic Yield {i}" in data.columns:
                data[f"Yield Spread {i}"] = data[f"Domestic Yield {i}"].astype(float) - data["Foreign Bond Yield"].astype(float)
        
        # Train Linear Regression Models for Each Currency Pair
        for i in range(1, 6):  # Assuming 5 currency pairs
            if f"FX Pair {i}" in data.columns:
                valid_data = data[[f"Yield Spread {i}", f"FX Pair {i}"]].dropna()
                if not valid_data.empty:
                    model = LinearRegression()
                    model.fit(valid_data[[f"Yield Spread {i}"]], valid_data[f"FX Pair {i}"])
                    data[f"Predictive Price {i}"] = model.predict(data[[f"Yield Spread {i}"]].fillna(method='ffill'))
                
                # Establish Trading Strategy
                if strategy == "Importer (BUY Only)":
                    data[f"Signal {i}"] = np.where(data[f"FX Pair {i}"] < data[f"Predictive Price {i}"], "BUY", np.nan)
                elif strategy == "Exporter (SELL Only)":
                    data[f"Signal {i}"] = np.where(data[f"FX Pair {i}"] > data[f"Predictive Price {i}"], "SELL", np.nan)
                else:
                    data[f"Signal {i}"] = np.where(data[f"FX Pair {i}"] < data[f"Predictive Price {i}"], "BUY", "SELL")
            
        data["Weekday"] = data["Date"].dt.weekday
        data = data[data["Weekday"] == 0]  # Filter only Mondays
        data["Exit Date"] = data["Date"] + pd.DateOffset(days=30)
        
        # Display Results
        st.subheader("Portfolio Backtest Results")
        st.dataframe(data.head())

if __name__ == "__main__":
    main()
