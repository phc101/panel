import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import os

# Fix Matplotlib backend for Streamlit
matplotlib.use("agg")  # Use non-interactive backend for Streamlit

# Function to calculate forward rate for a given tenor
def calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, days):
    if days <= 0:
        return spot_rate
    years = days / 365
    return spot_rate * ((1 + domestic_rate) / (1 + foreign_rate)) ** years

# Initialize session state for monthly cashflows
if "monthly_cashflows" not in st.session_state:
    st.session_state.monthly_cashflows = {month: [] for month in range(1, 13)}

if "selected_month" not in st.session_state:
    st.session_state.selected_month = 1  # Default to January

# Define months for navigation
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June", 
    "July", "August", "September", "October", "November", "December"
]

# Display logo at the top
logo_path = "phc_logo.png"  # Replace with the actual file path
if os.path.exists(logo_path):
    st.image(logo_path, width=100)
else:
    st.warning("Logo not found. Please ensure 'phc_logo.png' is in the correct directory.")

# Title
st.title("FX Forward Rate Calculator")
st.write("### Select Month to Plan Cashflows")

# Global interest rates
with st.sidebar:
    st.header("Global Settings")
    global_domestic_rate = st.slider("Global Domestic Interest Rate (%)", 0.0, 10.0, 5.0, step=0.25) / 100
    global_foreign_rate = st.slider("Global Foreign Interest Rate (%)
