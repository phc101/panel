import streamlit as st
import numpy as np
from scipy.stats import norm
import yfinance as yf

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

# Streamlit App
st.title("EUR/PLN FX Option Pricer")

# Fetch Spot Rate from Yahoo Finance
st.sidebar.header("Market Data")
spot_data = yf.download("EURPLN=X", period="1d")
spot_rate = spot_data['Close'].iloc[-1] if not spot_data.empty else 4.5  # Default spot rate fallback

st.sidebar.write(f"Current EUR/PLN Spot Rate: {spot_rate:.4f}")

# Input Parameters
st.sidebar.header("Option Parameters")
strike_price = st.sidebar.number_input("Strike Price", value=spot_rate)
volatility = st.sidebar.number_input("Volatility (annualized, %)", value=10.0) / 100
domestic_rate = st.sidebar.number_input("Domestic Risk-Free Rate (%)", value=2.0) / 100
foreign_rate = st.sidebar.number_input("Foreign Risk-Free Rate (%)", value=1.0) / 100
time_to_maturity = st.sidebar.number_input("Time to Maturity (in years)", value=0.25)
notional = st.sidebar.number_input("Notional Amount", value=100000.0)
option_type = st.sidebar.radio("Option Type", ["Call", "Put"], index=0)

# Calculate Option Price
if st.sidebar.button("Calculate Price"):
    option_price = fx_option_pricer(spot_rate, strike_price, volatility, domestic_rate, foreign_rate, time_to_maturity, notional, option_type)
    st.write(f"The price of the {option_type.lower()} option is: {option_price:.2f} PLN")

# Footer
st.write("Powered by Streamlit | Real Data from Yahoo Finance")
