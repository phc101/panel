import streamlit as st
import numpy as np
from scipy.stats import norm

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

# Allow user to input spot rate
st.sidebar.header("Market Data")
spot_rate = st.sidebar.number_input("Enter Spot Rate (EUR/PLN)", value=4.5, step=0.01)

# Allow user to manually input bond yields
st.sidebar.header("Bond Yields (Manual Input)")
domestic_rate = st.sidebar.number_input("Polish 10-Year Bond Yield (Domestic Rate, %)", value=5.5, step=0.1) / 100
foreign_rate = st.sidebar.number_input("German 10-Year Bond Yield (Foreign Rate, %)", value=2.5, step=0.1) / 100

# Display bond yields
st.sidebar.write(f"Domestic Risk-Free Rate: {domestic_rate * 100:.2f}%")
st.sidebar.write(f"Foreign Risk-Free Rate: {foreign_rate * 100:.2f}%")

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
st.write("Powered by Streamlit | All inputs are manual")
