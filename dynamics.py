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

# Choose Mode: Exporter or Importer
st.sidebar.header("Choose Strategy")
strategy = st.sidebar.radio(
    "Select Strategy Type:",
    options=["Exporter (Buy Put, Sell Call)", "Importer (Sell Put, Buy Call)"]
)

# Sidebar inputs
spot_rate = st.sidebar.number_input("Enter Spot Rate (EUR/PLN)", value=4.3150, step=0.0001, format="%.4f")
volatility = st.sidebar.number_input("Enter Volatility (annualized, %)", value=10.0, step=0.1) / 100
domestic_rate = st.sidebar.number_input("Polish 10-Year Bond Yield (Domestic Rate, %)", value=5.5, step=0.1) / 100
foreign_rate = st.sidebar.number_input("German 10-Year Bond Yield (Foreign Rate, %)", value=2.5, step=0.1) / 100

st.sidebar.header("Set Max and Min Prices")
max_price = st.sidebar.number_input("Enter Max Price Strike", value=spot_rate + 0.1, step=0.0001, format="%.4f")
min_price = st.sidebar.number_input("Enter Min Price Strike", value=spot_rate - 0.1, step=0.0001, format="%.4f")

flat_max_price = st.sidebar.checkbox("Flat Max Price")
flat_min_price = st.sidebar.checkbox("Flat Min Price")

increase_min_price = st.sidebar.checkbox("+1% Min Price from Month 7")
increase_max_price = st.sidebar.checkbox("+1% Max Price from Month 7")

notional = st.sidebar.number_input("Notional Amount", value=100000.0, step=1000.0)

# Dynamically Generate Trades
trades = []
for i in range(12):
    maturity_date = datetime.now() + timedelta(days=30 * (i + 1))
    if strategy == "Exporter (Buy Put, Sell Call)":
        # Exporter: Buy Put, Sell Call
        if flat_max_price and increase_min_price:
            min_price_adjusted = min_price * 1.01 if i + 1 >= 7 else min_price
            trades.append({"type": "Max Price", "action": "Sell", "strike": max_price, "maturity_months": i + 1, "maturity_date": maturity_date.strftime("%Y-%m-%d"), "notional": notional})
            trades.append({"type": "Min Price", "action": "Buy", "strike": min_price_adjusted, "maturity_months": i + 1, "maturity_date": maturity_date.strftime("%Y-%m-%d"), "notional": notional})
        else:
            trades.append({"type": "Max Price", "action": "Sell", "strike": max_price + (i * 0.01), "maturity_months": i + 1, "maturity_date": maturity_date.strftime("%Y-%m-%d"), "notional": notional})
            trades.append({"type": "Min Price", "action": "Buy", "strike": min_price + (i * 0.01), "maturity_months": i + 1, "maturity_date": maturity_date.strftime("%Y-%m-%d"), "notional": notional})
    elif strategy == "Importer (Sell Put, Buy Call)":
        # Importer: Sell Put, Buy Call
        if flat_min_price and increase_max_price:
            max_price_adjusted = max_price * 1.01 if i + 1 >= 7 else max_price
            trades.append({"type": "Max Price", "action": "Buy", "strike": max_price_adjusted, "maturity_months": i + 1, "maturity_date": maturity_date.strftime("%Y-%m-%d"), "notional": notional})
            trades.append({"type": "Min Price", "action": "Sell", "strike": min_price, "maturity_months": i + 1, "maturity_date": maturity_date.strftime("%Y-%m-%d"), "notional": notional})
        else:
            trades.append({"type": "Max Price", "action": "Buy", "strike": max_price + (i * 0.01), "maturity_months": i + 1, "maturity_date": maturity_date.strftime("%Y-%m-%d"), "notional": notional})
            trades.append({"type": "Min Price", "action": "Sell", "strike": min_price + (i * 0.01), "maturity_months": i + 1, "maturity_date": maturity_date.strftime("%Y-%m-%d"), "notional": notional})

# Calculate Net Premium
net_premium = 0
for trade in trades:
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

# Prepare data for the chart
max_prices = [trade["strike"] for trade in trades if trade["type"] == "Max Price"]
min_prices = [trade["strike"] for trade in trades if trade["type"] == "Min Price"]
max_maturities = [trade["maturity_months"] for trade in trades if trade["type"] == "Max Price"]
min_maturities = [trade["maturity_months"] for trade in trades if trade["type"] == "Min Price"]

# Plot the Chart
fig, ax = plt.subplots(figsize=(10, 6))
if strategy == "Exporter (Buy Put, Sell Call)":
    ax.step(max_maturities, max_prices, color="green", linestyle="--", label="Max Participation Price")
    ax.step(min_maturities, min_prices, color="red", linestyle="--", label="Hedged Price")
elif strategy == "Importer (Sell Put, Buy Call)":
    ax.step(max_maturities, min_prices, color="green", linestyle="--", label="Max Participation Price")
    ax.step(min_maturities, max_prices, color="red", linestyle="--", label="Hedged Price")

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

# Display Net Premium
st.write("### Net Premium")
if net_premium > 0:
    st.write(f"**Net Premium Received:** {net_premium:.2f} PLN")
else:
    st.write(f"**Net Premium Paid:** {abs(net_premium):.2f} PLN")

# Display Added Trades
st.write("### Current Trades")
for i, trade in enumerate(trades):
    st.write(f"**Trade {i + 1}:** {trade['action']} {trade['type']} at Strike {trade['strike']:.4f} "
             f"(Maturity: {trade['maturity_months']} months, Date: {trade['maturity_date']})")
