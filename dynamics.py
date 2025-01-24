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

# Streamlit App
st.title("EUR/PLN FX Option Pricer with Trade Stacking")

# Today's Date
today = datetime.today()

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
trade_type = st.sidebar.radio("Trade Type", ["Max Price", "Min Price"])
action = st.sidebar.radio("Action", ["Buy", "Sell"])
strike_price = st.sidebar.number_input(f"{trade_type} Strike Price", value=float(spot_rate), step=0.01)
time_to_maturity_months = st.sidebar.number_input("Time to Maturity (in months)", value=3, step=1, min_value=1)
time_to_maturity_date = today + timedelta(days=30 * time_to_maturity_months)
notional = st.sidebar.number_input("Notional Amount", value=100000.0, step=1000.0)

# Add Trade Button
if st.sidebar.button("Add Trade"):
    if len(st.session_state.trades) < 12:
        st.session_state.trades.append({
            "type": trade_type,
            "action": action,
            "strike": strike_price,
            "maturity_months": time_to_maturity_months,
            "maturity_date": time_to_maturity_date.strftime('%Y-%m-%d'),
            "notional": notional
        })
        st.success(f"{action} {trade_type} at Strike {strike_price:.2f} added!")
    else:
        st.warning("You can only add up to 12 trades.")

# Display Added Trades
st.write("### Current Trades")
for i, trade in enumerate(st.session_state.trades):
    maturity_date = trade.get("maturity_date", "Unknown Date")
    st.write(f"**Trade {i + 1}:** {trade['action']} {trade['type']} at Strike {trade['strike']} (Maturity: {trade['maturity_months']} months, Date: {maturity_date})")

# Calculate Net Premium and Plot Trades
if st.session_state.trades:
    net_premium = 0
    fig, ax = plt.subplots(figsize=(10, 6))

    # Prepare data for stair-step plotting
    sorted_trades = sorted(st.session_state.trades, key=lambda x: x["maturity_months"])
    maturity_dates = [today]  # Start from today's date
    max_prices = [None]  # Placeholder for max prices
    min_prices = [None]  # Placeholder for min prices

    for trade in sorted_trades:
        maturity_dates.append(datetime.strptime(trade["maturity_date"], '%Y-%m-%d'))
        if trade["type"] == "Max Price":
            max_prices[-1] = trade["strike"]
            min_prices.append(min_prices[-1] if min_prices[-1] is not None else trade["strike"])
        elif trade["type"] == "Min Price":
            min_prices[-1] = trade["strike"]
            max_prices.append(max_prices[-1] if max_prices[-1] is not None else trade["strike"])

    # Fill placeholders for the last step
    maturity_dates.append(maturity_dates[-1] + timedelta(days=30))
    max_prices.append(max_prices[-1])
    min_prices.append(min_prices[-1])

    # Replace None values with appropriate starting points
    max_prices[0] = max_prices[1]
    min_prices[0] = min_prices[1]

    # Plot the stair steps
    ax.step(maturity_dates, max_prices, color="green", linestyle="--", label="Max Price (Call)")
    ax.step(maturity_dates, min_prices, color="red", linestyle="--", label="Min Price (Put)")

    # Configure chart
    ax.set_title("Trades Visualization (Stair Step)")
    ax.set_xlabel("Strike Date")
    ax.set_ylabel("Strike Prices (PLN)")
    ax.grid(True)
    st.pyplot(fig)

    # Display Net Premium
    for trade in sorted_trades:
        price = fx_option_pricer(
            spot_rate,
            trade["strike"],
            volatility,
            domestic_rate,
            foreign_rate,
            trade["maturity_months"] / 12,  # Convert months to years
            trade["notional"],
            "call" if trade["type"] == "Max Price" else "put"
        )
        premium = -price if trade["action"] == "Buy" else price
        net_premium += premium

    st.write("### Net Premium")
    if net_premium > 0:
        st.write(f"**Net Premium Received:** {net_premium:.2f} PLN")
    else:
        st.write(f"**Net Premium Paid:** {abs(net_premium):.2f} PLN")
