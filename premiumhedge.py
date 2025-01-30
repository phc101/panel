import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

# Function to calculate historical VaR and CVaR
def calculate_var_cvar(returns, confidence_level=0.95, time_horizon=21):
    if len(returns) >= time_horizon:
        var = np.percentile(returns, (1 - confidence_level) * 100) * np.sqrt(time_horizon)
        cvar = returns[returns <= var].mean() * np.sqrt(time_horizon)
    else:
        var, cvar = np.nan, np.nan
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
        df["Spot"] = df["Close"].shift(-1)

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
        available_dates = df.index
        settlement_results = {}
        
        # Ensure forward dates align with available dates in the dataset
available_dates = df.index

for months, date in forward_dates.items():
    # Find the closest valid date in df.index
    if date in available_dates:
        nearest_date = date
    else:
        nearest_date = available_dates[available_dates.get_loc(date, method='nearest')] if not available_dates.empty else None

    if nearest_date and nearest_date in df.index:
        settlement_price = df.loc[nearest_date, "Close"]
        spot_price = df.loc[nearest_date, "Spot"] if nearest_date in df.index else settlement_price

        # Ensure we have enough historical data for VaR/CVaR calculation
        if len(df["Returns"].dropna()) >= months * 21:
            var, cvar = calculate_var_cvar(df["Returns"].dropna(), confidence_level, time_horizon=months * 21)
        else:
            var, cvar = np.nan, np.nan  # Assign NaN if not enough data

        net_margin = calculate_net_margin(strike_price, settlement_price, notional, direction)
        settlement_results[f"{months}M"] = {
            "Spot": spot_price,
            "Net Margin": net_margin,
            "VaR": var if not np.isnan(var) else None,
            "CVaR": cvar if not np.isnan(cvar) else None
        }
    else:
        st.warning(f"No available data for {months}M forward date. Skipping.")

# Display results
settlement_df = pd.DataFrame.from_dict(settlement_results, orient='index')

if not settlement_df.empty and "Net Margin" in settlement_df.columns:
    st.subheader("Net Margin vs. VaR & CVaR for Forward Strip")
    st.dataframe(settlement_df)

    # Visualization
    st.subheader("Comparison: VaR & CVaR vs. Net Margin")
    fig, ax = plt.subplots()
    if "VaR" in settlement_df.columns and "CVaR" in settlement_df.columns:
        ax.bar(settlement_df.index.astype(str), settlement_df["VaR"], label="VaR", alpha=0.7)
        ax.bar(settlement_df.index.astype(str), settlement_df["CVaR"], label="CVaR", alpha=0.7)
    ax.plot(settlement_df.index.astype(str), settlement_df["Net Margin"], marker='o', linestyle='-', color='red', label="Net Margin")
    ax.set_ylabel("PLN")
    ax.set_title("VaR, CVaR vs. Net Margin Over Time")
    ax.legend()
    st.pyplot(fig)

    # Display total outcome in PLN
    total_outcome = settlement_df["Net Margin"].sum()
    st.subheader("Total Net Margin Outcome")
    st.metric("Total Net Margin (PLN)", f"{total_outcome:,.2f}")

else:
    st.error("No valid data found for Net Margin. Please check your input data.")
