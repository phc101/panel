import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

# Function to calculate historical VaR and CVaR
def calculate_var_cvar(returns, confidence_level=0.95):
    var = np.percentile(returns, (1 - confidence_level) * 100)
    cvar = returns[returns <= var].mean()
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

        # User input for VaR parameters
        confidence_level = st.slider("Select Confidence Level for VaR & CVaR", 0.90, 0.99, 0.95)
        time_horizons = [21, 42, 63, 126]  # Approx. 1M, 2M, 3M, 6M in trading days
        
        # Calculate VaR & CVaR
        results = {}
        for t in time_horizons:
            var, cvar = calculate_var_cvar(df["Returns"].dropna(), confidence_level)
            results[f"{t} Days"] = {"VaR": var * np.sqrt(t), "CVaR": cvar * np.sqrt(t)}
        
        risk_df = pd.DataFrame(results).T
        risk_df.index.name = "Time Horizon"
        risk_df.columns = ["VaR", "CVaR"]
        
        # Display risk metrics
        st.subheader("Risk Estimates (VaR & CVaR)")
        st.dataframe(risk_df)
        
        # User input for forward contract
        st.subheader("Forward Contract Inputs")
        strike_price = st.number_input("Forward Strike Price", value=4.30, step=0.01)
        notional = st.number_input("Notional Amount (EUR)", value=100000, step=1000)
        settlement_price = st.number_input("Settlement Spot Price", value=4.21, step=0.01)
        direction = st.radio("Contract Type", ["Sell", "Buy"], index=0)
        
        # Allow user to set forward settlement dates for comparison
        settlement_dates = st.multiselect("Select Settlement Dates", df.index.strftime('%Y-%m-%d').tolist(), default=df.index.strftime('%Y-%m-%d').tolist()[:6])
        settlement_results = {}
        for date in settlement_dates:
            date_obj = pd.to_datetime(date)
            if date_obj in df.index:
                settlement_price = df.loc[date_obj, "Close"]
                net_margin = calculate_net_margin(strike_price, settlement_price, notional, direction)
                settlement_results[date] = net_margin
        
        # Display settlement results
        settlement_df = pd.DataFrame.from_dict(settlement_results, orient='index', columns=["Net Margin"])
        st.subheader("Net Margin for Selected Settlement Dates")
        st.dataframe(settlement_df)
        
        # Visualization
        st.subheader("Comparison: VaR & CVaR vs. Net Margin")
        fig, ax = plt.subplots()
        ax.bar(risk_df.index, risk_df["VaR"], label="VaR", alpha=0.7)
        ax.bar(risk_df.index, risk_df["CVaR"], label="CVaR", alpha=0.7)
        for date, margin in settlement_results.items():
            ax.axhline(y=margin, linestyle='--', label=f'Net Margin {date}')
        ax.set_ylabel("PLN")
        ax.set_title("VaR, CVaR vs. Net Margin")
        ax.legend()
        st.pyplot(fig)
