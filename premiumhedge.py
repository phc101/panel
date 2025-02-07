import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import requests

# Function to fetch bond yields with timeout and fallback to manual input
def fetch_bond_yield(url, default_value):
    try:
        response = requests.get(url, timeout=5)  # Timeout after 5 seconds
        response.raise_for_status()
        return float(response.text.strip().replace(',', '.'))
    except requests.RequestException:
        st.warning(f"Unable to fetch bond yield from {url}. Please enter manually.")
        return default_value

# Streamlit UI
st.title("EUR/PLN Forward Points Calculation")

# Function to update bond yields
if st.button("Update Live Rates"):
    polish_bond = fetch_bond_yield("https://stooq.pl/q/?s=10yply.b", 5.82)
    german_bond = fetch_bond_yield("https://stooq.pl/q/?s=10ydey.b", 2.37)
else:
    polish_bond = st.number_input("Enter Polish 10Y Bond Yield (%)", value=5.82, step=0.01)
    german_bond = st.number_input("Enter German 10Y Bund Yield (%)", value=2.37, step=0.01)

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

# Forward Rates Chart
st.subheader("EUR/PLN Forward Points")
fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(eurpln_fwd_data["Tenor"], eurpln_fwd_data["Forward Points"], color="lightblue")
for i, val in enumerate(eurpln_fwd_data["Forward Points"]):
    ax.text(i, val + 0.002, f"{val:.4f}", ha="center", fontsize=10)
ax.set_title("EUR/PLN Forward Points for Next 12 Months")
ax.set_ylabel("Forward Points")
ax.set_xticklabels(eurpln_fwd_data["Tenor"], rotation=45)
ax.grid(axis="y", linestyle="--", alpha=0.5)

st.pyplot(fig)

# Forward Rate Table
st.subheader("Forward Points Table")
st.dataframe(eurpln_fwd_data)
