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
        
        # Detect and rename columns
        currency_data.rename(columns={currency_data.columns[0]: "Date", currency_data.columns[1]: "FX Rate"}, inplace=True)
        domestic_yield.rename(columns={domestic_yield.columns[0]: "Date", domestic_yield.columns[1]: "Domestic Yield"}, inplace=True)
        foreign_yield.rename(columns={foreign_yield.columns[0]: "Date", foreign_yield.columns[1]: "Foreign Yield"}, inplace=True)
        
        # Convert Date columns
        currency_data["Date"] = pd.to_datetime(currency_data["Date"], errors='coerce')
        domestic_yield["Date"] = pd.to_datetime(domestic_yield["Date"], errors='coerce')
        foreign_yield["Date"] = pd.to_datetime(foreign_yield["Date"], errors='coerce')
        
        # Merge data
        data = currency_data.merge(domestic_yield, on="Date", how="outer").merge(foreign_yield, on="Date", how="outer")
        data.sort_values(by="Date", inplace=True)
        data.fillna(method="ffill", inplace=True)  # Forward fill missing values
        data.dropna(inplace=True)  # Drop any remaining NaNs
        
        # Calculate bond yield spread
        data["Yield Spread"] = data["Domestic Yield"] - data["Foreign Yield"]
        
        # Predictive Price using Linear Regression
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        valid_data = data.dropna()
        if not valid_data.empty:
            model.fit(valid_data[["Yield Spread"]], valid_data["FX Rate"])
            data["Predictive Price"] = model.predict(data[["Yield Spread"]])
        else:
            data["Predictive Price"] = np.nan
        
        # Generate trading signals
        data.dropna(inplace=True)  # Ensure no NaNs remain
        data["Weekday"] = data["Date"].dt.weekday
        data["Signal"] = np.where(data["FX Rate"] < data["Predictive Price"], "Buy", 
                                   np.where(data["FX Rate"] > data["Predictive Price"], "Sell", "Hold"))
        
        trades = data[(data["Weekday"] == 0) & (data["Signal"] != "Hold")].copy()
        trades["Exit Date"] = trades["Date"] + timedelta(days=30)
        trades = trades.merge(data[["Date", "FX Rate"]], left_on="Exit Date", right_on="Date", suffixes=("", "_Exit"))
        
        # Calculate P&L
        trades["PnL"] = np.where(trades["Signal"] == "Buy", 
                                  trades["FX Rate_Exit"] - trades["FX Rate"], 
                                  trades["FX Rate"] - trades["FX Rate_Exit"])
        trades["Cumulative PnL"] = trades["PnL"].cumsum()
        
        # Display results
        st.subheader("Backtest Results")
        st.write(trades[["Date", "Signal", "FX Rate", "Predictive Price", "Exit Date", "FX Rate_Exit", "PnL", "Cumulative PnL"]])
        
        # Visualization
        st.subheader("Market Price vs. Predictive Price")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(data["Date"], data["FX Rate"], label="Market Price", color="blue")
        ax.plot(data["Date"], data["Predictive Price"], label="Predictive Price (Regression Model)", linestyle="dashed", color="red")
        ax.legend()
        st.pyplot(fig)
        
        # Cumulative P&L Chart
        st.subheader("Cumulative P&L")
        fig2, ax2 = plt.subplots()
        ax2.plot(trades["Date"], trades["Cumulative PnL"], label="Cumulative P&L", color="green")
        ax2.axhline(y=0, color="black", linestyle="dotted")
        ax2.legend()
        st.pyplot(fig2)
        
        # Additional FX Price vs Predictive Price Chart
        st.subheader("Additional Market Price vs. Predictive Price Chart")
        fig3, ax3 = plt.subplots(figsize=(10, 5))
        ax3.plot(data["Date"], data["FX Rate"], label="Market Price", color="blue")
        ax3.plot(data["Date"], data["Predictive Price"], label="Predictive Price", linestyle="dotted", color="orange")
        ax3.legend()
        st.pyplot(fig3)
    
    except Exception as e:
        st.error(f"An error occurred: {e}")
