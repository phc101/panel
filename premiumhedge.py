import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta

# Streamlit UI setup
st.title("FX Valuation & Backtesting Tool")

# Upload CSV files
st.sidebar.header("Upload Data")
currency_file = st.sidebar.file_uploader("Upload Currency Pair Data (CSV)", type=["csv"])
domestic_yield_file = st.sidebar.file_uploader("Upload Domestic Bond Yield Data (CSV)", type=["csv"])
foreign_yield_file = st.sidebar.file_uploader("Upload Foreign Bond Yield Data (CSV)", type=["csv"])

if currency_file and domestic_yield_file and foreign_yield_file:
    try:
        # Load Data
        currency_data = pd.read_csv(currency_file)
        domestic_yield = pd.read_csv(domestic_yield_file)
        foreign_yield = pd.read_csv(foreign_yield_file)
        
        # Display first rows for debugging
        st.subheader("Sample Data Preview")
        st.write("Currency Data:", currency_data.head())
        st.write("Domestic Bond Yield Data:", domestic_yield.head())
        st.write("Foreign Bond Yield Data:", foreign_yield.head())
        
        # Ensure proper column names exist
        if len(currency_data.columns) < 2:
            st.error("Error: Currency data must have at least two columns: Date and FX Rate.")
        else:
            currency_data.columns = ["Date", "FX Rate"]
            currency_data["Date"] = pd.to_datetime(currency_data["Date"], errors='coerce')
        
        if len(domestic_yield.columns) < 2:
            st.error("Error: Domestic bond yield data must have at least two columns: Date and Domestic Yield.")
        else:
            domestic_yield.columns = ["Date", "Domestic Yield"]
            domestic_yield["Date"] = pd.to_datetime(domestic_yield["Date"], errors='coerce')
        
        if len(foreign_yield.columns) < 2:
            st.error("Error: Foreign bond yield data must have at least two columns: Date and Foreign Yield.")
        else:
            foreign_yield.columns = ["Date", "Foreign Yield"]
            foreign_yield["Date"] = pd.to_datetime(foreign_yield["Date"], errors='coerce')
        
        # Merge data on Date
        data = currency_data.merge(domestic_yield, on="Date").merge(foreign_yield, on="Date")
        
        # Calculate bond yield spread
        data["Yield Spread"] = data["Domestic Yield"] - data["Foreign Yield"]
        
        # Estimate predictive price using a simple linear relationship
        beta = 0.1  # Arbitrary coefficient, can be optimized further
        data["Predictive Price"] = data["FX Rate"].shift(1) + beta * (data["Yield Spread"] - data["Yield Spread"].shift(1))
        
        # Generate trading signals
        data["Signal"] = np.where(data["FX Rate"] < data["Predictive Price"], "Buy", "Sell")
        data["Weekday"] = data["Date"].dt.weekday
        
        # Filter only Monday trades and set exit 30 days later
        trades = data[data["Weekday"] == 0].copy()
        trades["Exit Date"] = trades["Date"] + timedelta(days=30)
        trades = trades.merge(data[["Date", "FX Rate"]], left_on="Exit Date", right_on="Date", suffixes=("", "_Exit"))
        
        # Calculate P&L
        trades["PnL"] = np.where(trades["Signal"] == "Buy", 
                                  trades["FX Rate_Exit"] - trades["FX Rate"], 
                                  trades["FX Rate"] - trades["FX Rate_Exit"])
        
        # Display results
        st.subheader("Backtest Results")
        st.write(trades[["Date", "Signal", "FX Rate", "Predictive Price", "Exit Date", "FX Rate_Exit", "PnL"]])
        
        # Visualization
        st.subheader("Market Price vs. Predictive Price")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(data["Date"], data["FX Rate"], label="Market Price", color="blue")
        ax.plot(data["Date"], data["Predictive Price"], label="Predictive Price", linestyle="dashed", color="red")
        ax.legend()
        st.pyplot(fig)
        
        # Equity curve
        trades["Cumulative PnL"] = trades["PnL"].cumsum()
        st.subheader("Equity Curve")
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        ax2.plot(trades["Date"], trades["Cumulative PnL"], label="Cumulative P&L", color="green")
        ax2.axhline(y=0, color="black", linestyle="dotted")
        ax2.legend()
        st.pyplot(fig2)
    
    except Exception as e:
        st.error(f"An error occurred: {e}")
