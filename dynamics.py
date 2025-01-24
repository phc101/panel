import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from datetime import datetime, timedelta

# Black-Scholes Pricing Function
def fx_option_pricer(spot, strike, volatility, domestic_rate, foreign_rate, time_to_maturity, notional, option_type="call"):
    d1 = (np.log(spot / strike) + (domestic_rate - foreign_rate + 0.5 * volatility**2) * time_to_maturity) / (volatility * np.sqrt(time_to_maturity))
    d2 = d1 - volatility * np.sqrt(time_to_maturity)

    if option_type.lower() == "call":
        price = np.exp(-foreign_rate * time_to_maturity) * spot * norm.cdf(d1) - np.exp(-domestic_rate * time_to_maturity) * strike * norm.cdf(d2)
    elif option_type.lower() == "put":
        price = np.exp(-domestic_rate * time_to_maturity) * strike * norm.cdf(-d2) - np.exp(-foreign_rate * time_to_maturity) * spot * norm.cdf(-d1)
    else:
        raise ValueError("Invalid option type. Use 'call' or 'put'.")
    
    return price * notional

# Main App Content
st.title("EUR/PLN Dynamic Forward Pricer")

# Initialize trades in session state
if "trades" not in st.session_state:
    st.session_state.trades = []

# Allow user to manually input the spot rate
spot_rate = st.sidebar.number_input("Enter Spot Rate (EUR/PLN)", value=4.3150, step=0.0001, format="%.4f")

# Allow user to manually input volatility
volatility = st.sidebar.number_input("Enter Volatility (annualized, %)", value=10.0, step=0.1) / 100

# Manual Bond Yields Input
domestic_rate = st.sidebar.number_input("Polish 10-Year Bond Yield (Domestic Rate, %)", value=5.5, step=0.1) / 100
foreign_rate = st.sidebar.number_input("German 10-Year Bond Yield (Foreign Rate, %)", value=2.5, step=0.1) / 100

# Input Parameters for Max and Min Prices
st.sidebar.header("Set Max and Min Prices")
max_price = st.sidebar.number_input("Enter Max Price Strike", value=float(spot_rate + 0.1), step=0.0001, format="%.4f")
min_price = st.sidebar.number_input("Enter Min Price Strike", value=float(spot_rate - 0.1), step=0.0001, format="%.4f")

# Toggles for Flat Prices
flat_max_price = st.sidebar.checkbox("Flat Max Price", value=False)
flat_min_price = st.sidebar.checkbox("Flat Min Price", value=False)

notional = st.sidebar.number_input("Notional Amount", value=100000.0, step=1000.0)

# Dynamically Generate Trades Button
if st.sidebar.button("Generate Trades"):
    for i in range(12):
        maturity_date = datetime.now() + timedelta(days=30 * (i + 1))
        st.session_state.trades.append({
            "type": "Max Price",
            "action": "Sell",
            "strike": max_price if flat_max_price else max_price + (i * 0.01),
            "maturity_months": i + 1,
            "maturity_date": maturity_date.strftime("%Y-%m-%d"),
            "notional": notional
        })
        st.session_state.trades.append({
            "type": "Min Price",
            "action": "Buy",
            "strike": min_price if flat_min_price else min_price + (i * 0.01),
            "maturity_months": i + 1,
            "maturity_date": maturity_date.strftime("%Y-%m-%d"),
            "notional": notional
        })

# Clear All Trades Button
if st.sidebar.button("Clear All Trades"):
    st.session_state.trades = []

# Prepare data for the chart if trades exist
if st.session_state.trades:
    max_prices = [trade["strike"] for trade in st.session_state.trades if trade["type"] == "Max Price"]
    min_prices = [trade["strike"] for trade in st.session_state.trades if trade["type"] == "Min Price"]
    max_maturities = [trade["maturity_months"] for trade in st.session_state.trades if trade["type"] == "Max Price"]
    min_maturities = [trade["maturity_months"] for trade in st.session_state.trades if trade["type"] == "Min Price"]

    # Plot the Chart
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.step(max_maturities, max_prices, color="green", linestyle="--", label="Max Price (Call)")
    ax.step(min_maturities, min_prices, color="red", linestyle="--", label="Min Price (Put)")

    ax.annotate("Max Participation Price", xy=(12, max_prices[-1]), xytext=(13, max_prices[-1]),
                color="green", fontsize=10, ha="left", va="center")
    ax.annotate("Hedged Price", xy=(12, min_prices[-1]), xytext=(13, min_prices[-1]),
                color="red", fontsize=10, ha="left", va="center")
    ax.annotate("Spot Price", xy=(0, spot_rate), xytext=(-1.0, spot_rate),
                color="blue", fontsize=10, ha="right", va="center")

    ax.set_title("Trades Visualization (Stair Step)")
    ax.set_xlabel("Time to Maturity (Months)")
    ax.set_ylabel("Strike Prices (PLN)")
    ax.grid(True, linewidth=0.5, alpha=0.3)
    ax.set_xlim(left=0, right=13)
    ax.set_ylim(min(min_prices) - 0.01, max(max_prices) + 0.01)
    st.pyplot(fig)

    # Display Added Trades
    st.write("### Current Trades")
    for i, trade in enumerate(st.session_state.trades):
        st.write(f"**Trade {i + 1}:** {trade['action']} {trade['type']} at Strike {trade['strike']:.4f} "
                 f"(Maturity: {trade['maturity_months']} months, Date: {trade['maturity_date']})")
else:
    st.write("### No trades available. Generate trades using the sidebar.")
