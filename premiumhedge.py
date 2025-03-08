import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

# Streamlit App
def main():
    st.title("FX Options Backtesting Tool")
    
    # File Uploads
    st.sidebar.header("Upload Data")
    fx_file = st.sidebar.file_uploader("Upload Currency Pair Prices (CSV)", type=["csv"])
    option_chain_file = st.sidebar.file_uploader("Upload Option Chain (CSV)", type=["csv"])
    
    if fx_file and option_chain_file:
        # Load Data
        fx_data = pd.read_csv(fx_file, parse_dates=["Date"], dayfirst=True)
        option_chain = pd.read_csv(option_chain_file)
        
        # Convert Date column to datetime
        fx_data["Date"] = pd.to_datetime(fx_data["Date"], errors="coerce")
        
        # Ensure necessary columns exist in option chain
        required_cols = ["Strike", "Price", "Delta", "Type"]
        if not all(col in option_chain.columns for col in required_cols):
            st.error("Error: Option chain must contain 'Strike', 'Price', 'Delta', and 'Type' columns.")
            return
        
        # Train Linear Regression Model
        fx_data["Yield Spread"] = fx_data.iloc[:, 1] - fx_data.iloc[:, 2]
        model = LinearRegression()
        model.fit(fx_data[["Yield Spread"]], fx_data.iloc[:, 3])
        fx_data["Predictive Price"] = model.predict(fx_data[["Yield Spread"]])
        
        # Establish Trading Strategy (Option-Based)
        fx_data["Signal"] = np.where(fx_data.iloc[:, 3] < fx_data["Predictive Price"], "BUY", "SELL")
        fx_data["Weekday"] = fx_data["Date"].dt.weekday
        fx_data = fx_data[fx_data["Weekday"] == 0]  # Filter only Mondays
        fx_data["Exit Date"] = fx_data["Date"] + pd.DateOffset(days=30)
        
        # Calculate Returns (Using Options)
        results = []
        for i, row in fx_data.iterrows():
            signal = row["Signal"]
            strike = row.iloc[3]  # Using FX price as reference for option selection
            
            # Select closest strike option
            if signal == "BUY":
                option = option_chain[(option_chain["Strike"] >= strike) & (option_chain["Type"] == "CALL")].sort_values("Strike").head(1)
            else:
                option = option_chain[(option_chain["Strike"] <= strike) & (option_chain["Type"] == "PUT")].sort_values("Strike", ascending=False).head(1)
            
            if option.empty:
                continue  # Skip if no matching option found
            
            option_price = option["Price"].values[0]
            option_delta = option["Delta"].values[0]
            option_strike = option["Strike"].values[0]
            
            # Find exit price
            exit_row = fx_data[fx_data["Date"] == row["Exit Date"]]
            if exit_row.empty:
                continue
            
            exit_price = exit_row.iloc[0, 1]
            
            # Calculate option P&L at expiry
            if signal == "BUY":
                intrinsic_value = max(exit_price - option_strike, 0)
            else:
                intrinsic_value = max(option_strike - exit_price, 0)
            
            revenue = (intrinsic_value - option_price) * 100  # Assuming 100 contract multiplier
            
            results.append([row["Date"], row["Exit Date"], row["Signal"], option_strike, option_price, exit_price, revenue])
        
        result_df = pd.DataFrame(results, columns=["Entry Date", "Exit Date", "Signal", "Strike Price", "Option Price", "Exit Price", "Revenue %"])
        result_df["Cumulative Revenue %"] = result_df["Revenue %"].cumsum()
        result_df["Drawdown %"] = result_df["Cumulative Revenue %"].cummax() - result_df["Cumulative Revenue %"]
        
        # Display Results
        st.subheader("Options Backtest Results")
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
