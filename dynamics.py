import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

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

# Streamlit App
st.title("EUR/PLN FX Option Pricer with Trade Stacking")

# Allow user to manually input the spot rate
spot_rate = st.sidebar.number_input("Enter Spot Rate (EUR/PLN)", value=4.5, step=0.01)

# Allow user to manually input volatility
volatility = st.sidebar.number_input("Enter Volatility (annualized, %)", value=10.0, step=0.1) / 100

# Manual Bond Yields Input
domestic_rate = st.sidebar.number_input("Polish 10-Year Bond Yield (Domestic Rate, %)", value=5.5, step=0.1) / 100
foreign_rate = st.sidebar.number_input("German 10-Year Bond Yield (Foreign Rate, %)", value=2.5, step=0.1) / 100

# Trades Storage
if "trades" not in st.session_state:
    st.session_state.trades = []

# Input Parameters for a Single Trade
st.sidebar.header("Add a Trade")
trade_type = st.sidebar.radio("Trade Type", ["Call", "Put"])
action = st.sidebar.radio("Action", ["Buy", "Sell"])
strike_price = st.sidebar.number_input(f"{trade_type} Strike Price", value=float(spot_rate), step=0.01)
time_to_maturity_months = st.sidebar.number_input("Time to Maturity (in months)", value=3, step=1)
time_to_maturity_years = time_to_maturity_months / 12  # Convert to years
notional = st.sidebar.number_input("Notional Amount", value=100000.0, step=1000.0)

# Add Trade Button
if st.sidebar.button("Add Trade"):
    if len(st.session_state.trades) < 12:
        st.session_state.trades.append({
            "type": trade_type,
            "action": action,
            "strike": strike_price,
            "maturity": time_to_maturity_months,
            "notional": notional
        })
        st.success(f"{action} {trade_type} at Strike {strike_price:.2f} added!")
    else:
        st.warning("You can only add up to 12 trades.")

# Display Added Trades
st.write("### Current Trades")
for i, trade in enumerate(st.session_state.trades):
    st.write(f"**Trade {i + 1}:** {trade['action']} {trade['type']} at Strike {trade['strike']} (Maturity: {trade['maturity']} months)")

# Calculate Net Premium and Plot Trades
if st.session_state.trades:
    net_premium = 0
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot each trade
    for trade in st.session_state.trades:
        # Calculate option premium
        price = fx_option_pricer(
            spot_rate,
            trade["strike"],
            volatility,
            domestic_rate,
            foreign_rate,
            trade["maturity"] / 12,  # Convert months to years
            trade["notional"],
            trade["type"].lower()
        )
        premium = -price if trade["action"] == "Buy" else price
        net_premium += premium

        # Plot strike price as a horizontal line
        color = "green" if trade["type"] == "Call" else "red"
        label = f"{trade['type']} {trade['action']} (Strike: {trade['strike']}, Maturity: {trade['maturity']} months)"
        ax.hlines(
            trade["strike"], xmin=0, xmax=trade["maturity"], color=color, linestyle="--", label=label
        )

    # Configure chart
    ax.set_title("Trades Visualization")
    ax.set_xlabel("Time to Maturity (Months)")
    ax.set_ylabel("Strike Prices (PLN)")
    ax.legend()
    st.pyplot(fig)

    # Display Net Premium
    st.write("### Net Premium")
    if net_premium > 0:
        st.write(f"**Net Premium Received:** {net_premium:.2f} PLN")
    else:
        st.write(f"**Net Premium Paid:** {abs(net_premium):.2f} PLN")
