import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup
import numpy as np

# Function to fetch bond yields from Stooq
def fetch_bond_yield(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    try:
        yield_value = soup.find("span", class_="q_ch_act").text.strip()
        return float(yield_value.replace(',', '.'))
    except:
        return None

# Get bond yields
domestic_yield = fetch_bond_yield("https://stooq.pl/q/?s=10yply.b")
foreign_yield = fetch_bond_yield("https://stooq.pl/q/?s=10ydey.b")

# Streamlit UI
st.title("EUR/PLN Forward Points Calculation")

# Calculate forward points using continuous compounding
if domestic_yield is not None and foreign_yield is not None:
    spot_rate = 4.2065  # Example spot rate, can be replaced with real-time data
    tenor_months = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    
    # Convert yields to decimal
    domestic_rate = domestic_yield / 100
    foreign_rate = foreign_yield / 100
    
    # Calculate forward points using continuous compounding
    forward_rates = spot_rate * np.exp((domestic_rate - foreign_rate) * tenor_months / 12)
    forward_points = forward_rates - spot_rate
    
    eurpln_fwd_data = pd.DataFrame({
        "Tenor": [f"{m}M" for m in tenor_months],
        "Forward Points": forward_points,
        "Forward Rate": forward_rates
    })
    
    # Forward Rates Charts
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
else:
    st.warning("Unable to fetch bond yields. Please check the data sources.")
