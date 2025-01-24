import streamlit as st
import numpy as np
from scipy.stats import norm
import requests

# Black-Scholes Pricing Function for FX Options
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

# Fetch 10-year Bond Yields from Trading Economics
def get_bond_yield(country_code):
    """Fetches the 10-year government bond yield using Trading Economics API."""
    api_key = "YOUR_TRADING_ECONOMICS_API_KEY"  # Replace with your API key
    url = f"https://api.tradingeconomics.com/markets/bonds/{country_code}:10Y?c={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list):
            return float(data[0]["Last"]) / 100  # Convert from percentage to decimal
    except Exception as e:
        st.error(f"Error fetching bond yield for {country_code}: {e}")
        return None

# Streamlit App
st.title("EUR/PLN FX Option Pricer")

# Fetch Spot Rate (Default for Manual Input)
default_spot_rate = 4.5  # Replace with real live spot rate fetching logic if needed

# Allow user to input spot rate
st.sidebar.header("Market Data")
spot_rate = st.sidebar.number_input("Enter Spot Rate (EUR/PLN)", value=default_spot_rate, step=0.01)

# Fetch Bond Yields
domestic_rate = get_bond_yield("PL")  # 10-year Polish bond yield
foreign_rate = get_bond_yield("DE")  # 10-year German bond yield

# Handle missing data
if domestic_rate is None:
    domestic_rate = 0.055  # Default to 5.5% if live data is unavailable
if foreign_rate is None:
    foreign_rate = 0.025  # Default to 2.5% if live data is unavailable

# Display bond yields
st.sidebar.write(f"10-Year Polish Bond Yield (Domestic Rate): {domestic_rate * 100:.2f}%")
st.sidebar.write(f"10-Year German Bond Yield (Foreign Rate): {foreign_rate * 100:.2f}%")

# Input Parameters
st.sidebar.header("Option Parameters")
strike_price = st.sidebar.number_input("Strike Price", value=float(spot_rate), step=0.01)
volatility = st.sidebar.number_input("Volatility (annualized, %)", value=10.0, step=0.1) / 100
time_to_maturity = st.sidebar.number_input("Time to Maturity (in years)", value=0.25, step=0.01)
notional = st.sidebar.number_input("Notional Amount", value=100000.0, step=1000.0)
option_type = st.sidebar.radio("Option Type", ["Call", "Put"], index=0)

# Calculate Option Price
if st.sidebar.button("Calculate Price"):
    try:
        option_price = fx_option_pricer(spot_rate, strike_price, volatility, domestic_rate, foreign_rate, time_to_maturity, notional, option_type)
        st.write(f"The price of the {option_type.lower()} option is: **{option_price:.2f} PLN**")
    except Exception as e:
        st.error(f"Error in calculation: {e}")

# Footer
st.write("Powered by Streamlit | Bond yields fetched from Trading Economics")
