import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

# Function to calculate historical VaR and CVaR
def calculate_var_cvar(returns, confidence_level=0.95, time_horizon=21, notional=100000):
    if len(returns) >= time_horizon:
        var = np.percentile(returns, (1 - confidence_level) * 100) * np.sqrt(time_horizon) * notional
        cvar = returns[returns <= var / notional].mean() * np.sqrt(time_horizon) * notional
    else:
        var, cvar = np.nan, np.nan
    return var, cvar

# Function to calculate forward price
def calculate_forward_price(spot_price, domestic_rate, foreign_rate, days):
    return spot_price * np.exp((domestic_rate - foreign_rate) * days / 365)

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
        
        # User selects a start date for the forward strip
        start_date = pd.Timestamp(st.date_input("Select Start Date for Forward Strip", df.index.min().date()))
        if start_date not in df.index:
            st.error("Selected date is not in the dataset. Please select a valid date.")
        else:
            spot_price = df.loc[start_date, "Close"]
            
            # User inputs interest rates for forward calculation
            st.subheader("Interest Rate Inputs")
            domestic_rate = st.number_input("Domestic Interest Rate (Annual, %)", value=5.0, step=0.1) / 100
            foreign_rate = st.number_input("Foreign Interest Rate (Annual, %)", value=3.0, step=0.1) / 100
            
            # Generate 12-month forward strip
            settlement_results = {}
            for months in range(1, 13):
                forward_start = start_date + pd.DateOffset(months=months)
                month_end_dates = df[df.index.to_period("M") == forward_start.to_period("M")].index
                settlement_date = month_end_dates.max() if not month_end_dates.empty else None
                
                if settlement_date and settlement_date in df.index:
                    days_to_settlement = (settlement_date - start_date).days
                    forward_price = calculate_forward_price(spot_price, domestic_rate, foreign_rate, days_to_settlement)
                    settlement_price = df.loc[settlement_date, "Close"]
                    net_margin = calculate_net_margin(forward_price, settlement_price, 100000, "Sell")
                    var, cvar = calculate_var_cvar(df["Returns"].dropna(), 0.95, time_horizon=months * 21, notional=100000)
                    net_impact = net_margin - var
                    settlement_results[f"{months}M"] = {
                        "Forward Price": forward_price,
                        "Settlement Price": settlement_price,
                        "Net Margin": net_margin,
                        "VaR (PLN)": var,
                        "CVaR (PLN)": cvar,
                        "Net Impact": net_impact
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
                if "VaR (PLN)" in settlement_df.columns and "CVaR (PLN)" in settlement_df.columns:
                    ax.bar(settlement_df.index.astype(str), settlement_df["VaR (PLN)"], label="VaR (PLN)", alpha=0.7)
                    ax.bar(settlement_df.index.astype(str), settlement_df["CVaR (PLN)"], label="CVaR (PLN)", alpha=0.7)
                ax.plot(settlement_df.index.astype(str), settlement_df["Net Margin"], marker='o', linestyle='-', color='red', label="Net Margin")
                ax.bar(settlement_df.index.astype(str), settlement_df["Net Impact"], color=["green" if x > 0 else "red" for x in settlement_df["Net Impact"]], alpha=0.6, label="Net Impact")
                ax.set_ylabel("PLN")
                ax.set_title("VaR, CVaR vs. Net Margin Over Time")
                ax.legend()
                st.pyplot(fig)
                
                # Display total outcome in PLN
                total_outcome = settlement_df["Net Margin"].sum()
                total_net_impact = settlement_df["Net Impact"].sum()
                st.subheader("Total Net Margin and Net Impact Outcome")
                st.metric("Total Net Margin (PLN)", f"{total_outcome:,.2f}")
                st.metric("Total Net Impact (PLN)", f"{total_net_impact:,.2f}")
            else:
                st.error("No valid data found for Net Margin. Please check your input data.")
