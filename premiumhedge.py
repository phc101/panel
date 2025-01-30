import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

# Function to calculate historical VaR and CVaR
def calculate_var_cvar(returns, confidence_level=0.95, time_horizon=21):
    var = np.percentile(returns, (1 - confidence_level) * 100) * np.sqrt(time_horizon)
    cvar = returns[returns <= var].mean() * np.sqrt(time_horizon)
    return var, cvar

# Function to calculate net margin from forward settlement
def calculate_net_margin(strike_price, settlement_price, notional, direction="Sell"):
    if direction == "Sell":
        return (strike_price - settlement_price) * notional
    else:
        return (settlement_price - strike_price) * notional

# Streamlit UI
st.title("VaR & CVaR vs. Forward Settlement Net Margin")

# File upload for EUR/PLN historical data
uploaded_file = st.file_uploader("Upload Excel file with EUR/PLN Close Prices", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    
    # Ensure the "Date" column exists
    if "Date" not in df.columns:
        st.error("Excel file must contain a 'Date' column.")
    else:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df.dropna(subset=["Date"], inplace=True)
        df.sort_values(by="Date", inplace=True)
        df.set_index("Date", inplace=True)
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df.dropna(subset=["Close"], inplace=True)
        df["Returns"] = df["Close"].pct_change().dropna()
        df["Spot"] = df["Close"].shift(-1)  # Assume next day's price as the spot reference

        # User input for VaR parameters
        confidence_level = st.slider("Select Confidence Level for VaR & CVaR", 0.90, 0.99, 0.95)
        
        # User input for forward contract
        st.subheader("Forward Contract Inputs")
        strike_price = st.number_input("Forward Strike Price", value=4.30, step=0.01)
        notional = st.number_input("Notional Amount (EUR)", value=100000, step=1000)
        direction = st.radio("Contract Type", ["Sell", "Buy"], index=0)
        
        # Allow user to set custom start date for 6-month forward strip
        start_date = st.date_input("Select Start Date for Forward Strip", df.index.min().date())
        forward_dates = {i: start_date + pd.DateOffset(months=i) for i in range(1, 7)}
        settlement_results = {}
        
        for months, date in forward_dates.items():
            if date in df.index:
                settlement_price = df.loc[date, "Close"]
                spot_price = df.loc[date, "Spot"] if date in df.index else settlement_price
                net_margin = calculate_net_margin(strike_price, settlement_price, notional, direction)
                var, cvar = calculate_var_cvar(df["Returns"].dropna(), confidence_level, time_horizon=months * 21)
                settlement_results[f"{months}M"] = {
                    "Spot": spot_price,
                    "Net Margin": net_margin,
                    "VaR": var if var is not None else np.nan,
                    "CVaR": cvar if cvar is not None else np.nan
                }
        
        # Display settlement results
        settlement_df = pd.DataFrame.from_dict(settlement_results, orient='index')
        st.subheader("Net Margin vs. VaR & CVaR for Forward Strip")
        st.dataframe(settlement_df)
        
        # Ensure required columns exist
        if not settlement_df.empty and "Net Margin" in settlement_df.columns:
            # Visualization
            st.subheader("Comparison: VaR & CVaR vs. Net Margin")
            fig, ax = plt.subplots()
            if "VaR" in settlement_df.columns and "CVaR" in settlement_df.columns:
                ax.bar(settlement_df.index.astype(str), settlement_df["VaR"], label="VaR", alpha=0.7)
                ax.bar(settlement_df.index.astype(str), settlement_df["CVaR"], label="CVaR", alpha=0.7)
            else:
                st.warning("VaR or CVaR values are missing. Please check the input data.")
            ax.plot(settlement_df.index.astype(str), settlement_df["Net Margin"], marker='o', linestyle='-', color='red', label="Net Margin")
            ax.set_ylabel("PLN")
            ax.set_title("VaR, CVaR vs. Net Margin Over Time")
            ax.legend()
            ax.text(0.5, -0.2, "This chart compares Value at Risk (VaR) and Conditional Value at Risk (CVaR) with the net margin for each forward contract, ensuring accurate time horizon alignment.", ha='center', va='bottom', transform=ax.transAxes, fontsize=10)
            st.pyplot(fig)
            
            # Display total outcome in PLN
            total_outcome = settlement_df["Net Margin"].sum()
            st.subheader("Total Net Margin Outcome")
            st.metric("Total Net Margin (PLN)", f"{total_outcome:,.2f}")
        else:
            st.error("No valid data found for Net Margin. Please check your input data.")
