import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import requests
from datetime import datetime

# Function to fetch bond yields with timeout and fallback to manual input
def fetch_bond_yield(url):
    try:
        response = requests.get(url, timeout=5)  # Timeout after 5 seconds
        response.raise_for_status()
        return float(response.text.strip().replace(',', '.'))
    except requests.RequestException:
        return None

# Streamlit UI
st.title("EUR/PLN Forward Points Calculation Over Time")

# Function to update bond yields
if st.button("Update Live Rates"):
    polish_bond = fetch_bond_yield("https://stooq.pl/q/?s=10yply.b")
    german_bond = fetch_bond_yield("https://stooq.pl/q/?s=10ydey.b")
else:
    polish_bond = None
    german_bond = None

# Allow manual input if auto-fetching fails
if polish_bond is None:
    polish_bond = st.number_input("Enter Polish 10Y Bond Yield (%)", value=5.82, step=0.01)
if german_bond is None:
    german_bond = st.number_input("Enter German 10Y Bund Yield (%)", value=2.37, step=0.01)

# Store historical forward points
time_series_data = st.session_state.get("time_series_data", [])
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Calculate forward points using continuous compounding
spot_rate = 4.2065  # Example spot rate, can be replaced with real-time data
tenor_months = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])

# Convert yields to decimal
domestic_rate = polish_bond / 100
foreign_rate = german_bond / 100

# Calculate forward points using continuous compounding
forward_rates = spot_rate * np.exp((domestic_rate - foreign_rate) * tenor_months / 12)
forward_points = forward_rates - spot_rate

eurpln_fwd_data = pd.DataFrame({
    "Tenor": [f"{m}M" for m in tenor_months],
    "Forward Points": forward_points,
    "Forward Rate": forward_rates
})

# Store time-series data
time_series_data.append({"timestamp": current_time, "forward_points": list(forward_points)})
st.session_state["time_series_data"] = time_series_data

# Plot historical changes in forward points
st.subheader("Forward Points Over Time")
fig, ax = plt.subplots(figsize=(10, 6))
for entry in time_series_data:
    ax.plot(tenor_months, entry["forward_points"], marker='o', label=entry["timestamp"])
ax.set_title("EUR/PLN Forward Points Evolution")
ax.set_xlabel("Tenor (Months)")
ax.set_ylabel("Forward Points")
ax.legend(loc="upper left", fontsize="small")
ax.grid(True, linestyle="--", alpha=0.5)
st.pyplot(fig)

# Forward Rate Table
st.subheader("Current Forward Points Table")
st.dataframe(eurpln_fwd_data)
