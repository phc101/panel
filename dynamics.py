import streamlit as st
import numpy as np
from scipy.stats import norm
from alpha_vantage.foreignexchange import ForeignExchange
from alpha_vantage.timeseries import TimeSeries
pip install alpha_vantage
# Alpha Vantage API Key
API_KEY = "YOUR_ALPHA_VANTAGE_API_KEY"

# Initialize Alpha Vantage Clients
fx = ForeignExchange(key=API_KEY)
ts = TimeSeries(key=API_KEY, output_format="pandas")


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


# Fetch Real-Time Spot Rate
def get_fx_rate(from_currency, to_currency):
    try:
        data, _ = fx.get_currency_exchange_rate(from_currency, to_currency)
        return float(data["5. Exchange Rate"])
    except Exception as e:
        st.error(f"Error fetching FX rate: {e}")
        return None


# Fetch Historical Volatility
def calculate_historical_volatility(symbol):
    try:
        data, _ = ts.get_daily(symbol=symbol, outputsize="compact")
        returns = np.log(data["4. close"] / data["4. close"].shift(1)).dropna()
        return np.std(returns) * np.sqrt(252) * 100  # Annualized volatility in %
    except Exception as e:
        st.error(f"Error calculating historical volatility: {e}")
        return None


# Streamlit App
st.title("EUR/PLN FX Option Pricer with Alpha Vantage")

# Fetch Spot Rate
spot_rate = get_fx_rate("EUR", "PLN")
if spot_rate:
    st.sidebar.write(f"Real-Time Spot Rate (EUR/PLN): {spot_rate:.4f}")
else:
    spot_rate = st.sidebar.number_input("Enter Spot Rate (EUR/PLN)", value=4.5, step=0.01)

# Fetch Historical Volatility
volatility = calculate_historical_volatility("EURPLN=X")
if volatility:
    st.sidebar.write(f"Historical Volatility: {volatility:.2f}%")
else:
    volatility = st.sidebar.number_input("Enter Volatility (annualized, %)", value=10.0, step=0.1)

# Manual Bond Yields Input
domestic_rate = st.sidebar.number_input("Polish 10-Year Bond Yield (Domestic Rate, %)", value=5.5, step=0.1) / 100
foreign_rate = st.sidebar.number_input("German 10-Year Bond Yield (Foreign Rate, %)", value=2.5, step=0.1) / 100

# Input Parameters
st.sidebar.header("Option Parameters")
call_strike_price = st.sidebar.number_input("Call Strike Price", value=float(spot_rate), step=0.01)
put_strike_price = st.sidebar.number_input("Put Strike Price", value=float(spot_rate), step=0.01)
time_to_maturity_months = st.sidebar.number_input("Time to Maturity (in months)", value=3, step=1)
time_to_maturity_years = time_to_maturity_months / 12  # Convert to years
notional = st.sidebar.number_input("Notional Amount", value=100000.0, step=1000.0)

# Buy or Sell Selection
st.sidebar.header("Option Strategy")
call_action = st.sidebar.selectbox("Call Option", ["Buy", "Sell"], index=0)
put_action = st.sidebar.selectbox("Put Option", ["Buy", "Sell"], index=0)

# Calculate Option Prices and Net Premium Dynamically
try:
    # Calculate Call and Put Prices
    call_price = fx_option_pricer(spot_rate, call_strike_price, volatility / 100, domestic_rate, foreign_rate, time_to_maturity_years, notional, "call")
    put_price = fx_option_pricer(spot_rate, put_strike_price, volatility / 100, domestic_rate, foreign_rate, time_to_maturity_years, notional, "put")

    # Adjust Prices Based on Buy/Sell Action
    call_premium = -call_price if call_action == "Buy" else call_price
    put_premium = -put_price if put_action == "Buy" else put_price

    # Calculate Net Premium
    net_premium = call_premium + put_premium

    # Display Results
    st.write("### Option Prices")
    st.write(f"**Call Option ({call_action}) at Strike {call_strike_price:.2f}:** {call_price:.2f} PLN")
    st.write(f"**Put Option ({put_action}) at Strike {put_strike_price:.2f}:** {put_price:.2f} PLN")
    st.write("### Net Premium")
    if net_premium > 0:
        st.write(f"**Net Premium Received:** {net_premium:.2f} PLN")
    else:
        st.write(f"**Net Premium Paid:** {abs(net_premium):.2f} PLN")
except Exception as e:
    st.error(f"Error in calculation: {e}")

# Footer
st.write("Powered by Streamlit | Data from Alpha Vantage")
