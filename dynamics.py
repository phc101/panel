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
st.title("EUR/PLN FX Option Pricer with Flat Price Options")

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

# Dynamically Generate Trades
trades = []
for i in range(12):
    # Generate Max Price (Sell)
    trades.append({
        "type": "Max Price",
        "action": "Sell",
        "strike": max_price if flat_max_price else max_price + (i * 0.01),  # Keep flat or increment by 0.01
        "maturity_months": i + 1,  # Maturity from 1 month to 12 months
        "notional": notional
    })
    # Generate Min Price (Buy)
    trades.append({
        "type": "Min Price",
        "action": "Buy",
        "strike": min_price if flat_min_price else min_price + (i * 0.01),  # Keep flat or increment by 0.01
        "maturity_months": i + 1,  # Maturity from 1 month to 12 months
        "notional": notional
    })

# Plot the Chart at the Top
fig, ax = plt.subplots(figsize=(10, 6))

# Prepare data for stair-step plotting
sorted_trades = sorted(trades, key=lambda x: x["maturity_months"])
maturity_months = [0]  # Start from 0 months
max_prices = [spot_rate]  # Start with spot rate for max prices
min_prices = [spot_rate]  # Start with spot rate for min prices

for trade in sorted_trades:
    maturity_months.append(trade["maturity_months"])
    if trade["type"] == "Max Price":
        max_prices.append(trade["strike"])
        min_prices.append(min_prices[-1])  # Repeat the previous min price
    elif trade["type"] == "Min Price":
        min_prices.append(trade["strike"])
        max_prices.append(max_prices[-1])  # Repeat the previous max price

# Extend the last maturity point
maturity_months.append(maturity_months[-1] + 1)
max_prices.append(max_prices[-1])
min_prices.append(min_prices[-1])

# Plot the stair steps
ax.step(maturity_months, max_prices, color="green", linestyle="--", label="Max Price (Call)")
ax.step(maturity_months, min_prices, color="red", linestyle="--", label="Min Price (Put)")

# Configure chart
ax.set_title("Trades Visualization (Stair Step)")
ax.set_xlabel("Time to Maturity (Months)")
ax.set_ylabel("Strike Prices (PLN)")
ax.grid(True, linewidth=0.5, alpha=0.3)  # Thinner and barely visible grid
st.pyplot(fig)

# Display Added Trades
st.write("### Current Trades")
for i, trade in enumerate(sorted_trades):
    st.write(f"**Trade {i + 1}:** {trade['action']} {trade['type']} at Strike {trade['strike']:.4f} (Maturity: {trade['maturity_months']} months)")

# Calculate Net Premium and Display Below
net_premium = 0
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
