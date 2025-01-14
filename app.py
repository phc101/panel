import streamlit as st
from datetime import datetime
import requests

# Mocked function to get spot rate
def get_spot_rate(currency):
    # Replace with a real API for live rates
    spot_rates = {'EUR': 4.5, 'USD': 4.0}  # Example static data
    return spot_rates.get(currency, 0)

# Function to calculate forward rate
def calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, days):
    years = days / 365
    return spot_rate * ((1 + domestic_rate) / (1 + foreign_rate)) ** years

# Streamlit App
st.title("FX Forward Rate Calculator")

st.markdown("""
This app allows you to calculate the forward rate for future cashflows in EUR or USD and see the equivalent value in PLN.
""")

# User Input
st.sidebar.header("Inputs")
currency = st.sidebar.selectbox("Select Currency", ["EUR", "USD"])
amount = st.sidebar.number_input("Enter Cashflow Amount", min_value=0.0, value=1000.0, step=100.0)
future_date = st.sidebar.date_input("Select Future Date", min_value=datetime.today())
domestic_rate = st.sidebar.slider("Domestic Interest Rate (%)", min_value=0.0, max_value=10.0, value=5.0) / 100
foreign_rate = st.sidebar.slider("Foreign Interest Rate (%)", min_value=0.0, max_value=10.0, value=3.0) / 100

# Calculate Forward Rate
st.header("Results")
if st.button("Calculate Forward Rate"):
    spot_rate = get_spot_rate(currency)
    days = (future_date - datetime.today().date()).days

    if spot_rate > 0 and days > 0:
        forward_rate = calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, days)
        pln_value = forward_rate * amount
        st.success(f"Forward Rate: {forward_rate:.4f}")
        st.success(f"Guaranteed Value in PLN: {pln_value:.2f}")
    else:
        st.error("Invalid input. Please check your entries.")

# Footer
st.markdown("---")
st.caption("Developed using Streamlit")
