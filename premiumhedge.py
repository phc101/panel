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
        
        # Display first rows for debugging
        st.subheader("Sample Data Preview")
        st.write("Currency Data:", currency_data.head())
        st.write("Domestic Bond Yield Data:", domestic_yield.head())
        st.write("Foreign Bond Yield Data:", foreign_yield.head())
        
        # Detect column names and select relevant ones
        if "Date" not in currency_data.columns:
            currency_data.rename(columns={currency_data.columns[0]: "Date"}, inplace=True)
        currency_data["Date"] = pd.to_datetime(currency_data["Date"], errors='coerce')
        currency_data = currency_data[["Date", currency_data.columns[1]]]
        currency_data.columns = ["Date", "FX Rate"]
        
        if "Date" not in domestic_yield.columns:
            domestic_yield.rename(columns={domestic_yield.columns[0]: "Date"}, inplace=True)
        domestic_yield["Date"] = pd.to_datetime(domestic_yield["Date"], errors='coerce')
        domestic_yield = domestic_yield[["Date", domestic_yield.columns[1]]]
        domestic_yield.columns = ["Date", "Domestic Yield"]
        
        if "Date" not in foreign_yield.columns:
            foreign_yield.rename(columns={foreign_yield.columns[0]: "Date"}, inplace=True)
        foreign_yield["Date"] = pd.to_datetime(foreign_yield["Date"], errors='coerce')
        foreign_yield = foreign_yield[["Date", foreign_yield.columns[1]]]
        foreign_yield.columns = ["Date", "Foreign Yield"]
        
        # Merge data on Date
        data = currency_data.merge(domestic_yield, on="Date").merge(foreign_yield, on="Date")
        
        # Calculate bond yield spread
        data["Yield Spread"] = data["Domestic Yield"] - data["Foreign Yield"]
        
        # Linear Regression Model for Predictive Price
        model = LinearRegression()
        valid_data = data.dropna()
        X = valid_data[["Yield Spread"]]
        y = valid_data["FX Rate"]
        model.fit(X, y)
        
        # Predictive price using regression model
        data["Predictive Price"] = model.predict(data[["Yield Spread"]])
        
        # Trading strategy: Buy/Sell every Monday, exit after 30 days
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
        
        # Save extracted data to CSV
        output_csv = data[["Date", "FX Rate", "Yield Spread", "Predictive Price"]]
        csv_filename = "fx_spread_analysis.csv"
        output_csv.to_csv(csv_filename, index=False)
        
        # Provide download link
        st.subheader("Download Processed Data")
        st.download_button(label="Download CSV", data=output_csv.to_csv(index=False), file_name=csv_filename, mime="text/csv")
        
        # Visualization
        st.subheader("Market Price vs. Predictive Price")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(data["Date"], data["FX Rate"], label="Market Price", color="blue")
        ax.plot(data["Date"], data["Predictive Price"], label="Predictive Price (Regression)", linestyle="dashed", color="red")
        ax.legend()
        st.pyplot(fig)
    
    except Exception as e:
        st.error(f"An error occurred: {e}")
