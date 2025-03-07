import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
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
        
        # Show detected column names for debugging
        st.subheader("Column Names in Uploaded Files")
        st.write("Currency Data Columns:", currency_data.columns.tolist())
        st.write("Domestic Yield Data Columns:", domestic_yield.columns.tolist())
        st.write("Foreign Yield Data Columns:", foreign_yield.columns.tolist())
        
        # Detect column names and select relevant ones
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
        
        # Display first few rows for debugging
        st.subheader("Merged Data Preview Before Processing")
        st.write(data.head())
        
        # Forward fill missing values
        data.fillna(method="ffill", inplace=True)
        
        # Ensure dataset is not empty after preprocessing
        if data.empty:
            st.error("Error: No valid data available after preprocessing. Check uploaded files.")
        else:
            data["Yield Spread"] = data["Domestic Yield"] - data["Foreign Yield"]
            
            # Predictive Price using Regression
            model = LinearRegression()
            model.fit(data[["Yield Spread"]], data["FX Rate"])
            data["Predictive Price"] = model.predict(data[["Yield Spread"]])
            
            # Trading Strategy
            data["Weekday"] = data["Date"].dt.weekday
            data["Signal"] = np.where(data["FX Rate"] < data["Predictive Price"], "Buy", 
                                       np.where(data["FX Rate"] > data["Predictive Price"], "Sell", "Hold"))
            
            trades = data[(data["Weekday"] == 0) & (data["Signal"] != "Hold")].copy()
            trades["Exit Date"] = trades["Date"] + timedelta(days=30)
            trades = trades.merge(data[["Date", "FX Rate"]], left_on="Exit Date", right_on="Date", suffixes=("", "_Exit"))
            
            trades["PnL"] = np.where(trades["Signal"] == "Buy", 
                                      trades["FX Rate_Exit"] - trades["FX Rate"], 
                                      trades["FX Rate"] - trades["FX Rate_Exit"])
            trades["Cumulative PnL"] = trades["PnL"].cumsum()
            
            # Performance Metrics
            sharpe_ratio = trades["PnL"].mean() / trades["PnL"].std()
            sortino_ratio = trades["PnL"].mean() / trades["PnL"][trades["PnL"] < 0].std()
            win_rate = len(trades[trades["PnL"] > 0]) / len(trades)
            risk_of_ruin = len(trades[trades["PnL"].cumsum() < -0.5 * trades["PnL"].sum()]) / len(trades)
            
            st.subheader("Performance Metrics")
            st.write(f"Sharpe Ratio: {sharpe_ratio:.2f}")
            st.write(f"Sortino Ratio: {sortino_ratio:.2f}")
            st.write(f"Win Rate: {win_rate:.2%}")
            st.write(f"Risk of Ruin: {risk_of_ruin:.2%}")
            
            # Cumulative P&L Chart
            st.subheader("Cumulative P&L")
            fig, ax = plt.subplots()
            ax.plot(trades["Date"], trades["Cumulative PnL"], label="Cumulative P&L", color="green")
            ax.axhline(y=0, color="black", linestyle="dotted")
            ax.legend()
            st.pyplot(fig)
            
            # Separate Charts for Buy and Sell Strategies
            st.subheader("Buy-Only Strategy P&L")
            buy_trades = trades[trades["Signal"] == "Buy"]
            fig, ax = plt.subplots()
            ax.plot(buy_trades["Date"], buy_trades["Cumulative PnL"], label="Buy-Only Cumulative P&L", color="blue")
            ax.legend()
            st.pyplot(fig)
            
            st.subheader("Sell-Only Strategy P&L")
            sell_trades = trades[trades["Signal"] == "Sell"]
            fig, ax = plt.subplots()
            ax.plot(sell_trades["Date"], sell_trades["Cumulative PnL"], label="Sell-Only Cumulative P&L", color="red")
            ax.legend()
            st.pyplot(fig)
    
    except Exception as e:
        st.error(f"An error occurred: {e}")
