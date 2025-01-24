from alpha_vantage.foreignexchange import ForeignExchange
from alpha_vantage.timeseries import TimeSeries
import numpy as np
import streamlit as st

# Alpha Vantage API Key
API_KEY = "YOUR_ALPHA_VANTAGE_API_KEY"

# Initialize Alpha Vantage Clients
fx = ForeignExchange(key=API_KEY)
ts = TimeSeries(key=API_KEY, output_format="pandas")

# Function to fetch real-time spot rates
def get_fx_rate(from_currency, to_currency):
    try:
        data, _ = fx.get_currency_exchange_rate(from_currency, to_currency)
        return float(data["5. Exchange Rate"])
    except Exception as e:
        st.error(f"Error fetching FX rate: {e}")
        return None

# Function to fetch historical volatility
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

# Bond Yield Input (Manual for now)
domestic_rate = st.sidebar.number_input("Polish 10-Year Bond Yield (Domestic Rate, %)", value=5.5, step=0.1) / 100
foreign_rate = st.sidebar.number_input("German 10-Year Bond Yield (Foreign Rate, %)", value=2.5, step=0.1) / 100

# Remaining Code: Strike Prices, Premium Calculation, etc.
# (The rest of the code remains the same as before, dynamically updating net premium.)
