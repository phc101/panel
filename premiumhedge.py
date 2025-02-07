import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup

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
st.title("FX Dashboard - EUR/PLN & USD/PLN")

# File uploader
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

if uploaded_file is not None:
    xls = pd.ExcelFile(uploaded_file)
    dane_df = pd.read_excel(xls, sheet_name="dane")
    dashboard_df = pd.read_excel(xls, sheet_name="Dashboard")

    # Extract historical data for EUR/PLN and USD/PLN
    eurpln_data = dane_df.iloc[1:, [0, 1, 2]].copy()
    eurpln_data.columns = ["Date", "Close", "Z-score"]
    eurpln_data["Date"] = pd.to_datetime(eurpln_data["Date"])
    eurpln_data["Close"] = pd.to_numeric(eurpln_data["Close"], errors="coerce")

    usdpln_data = dane_df.iloc[1:, [9, 10, 11]].copy()
    usdpln_data.columns = ["Date", "Close", "Z-score"]
    usdpln_data["Date"] = pd.to_datetime(usdpln_data["Date"])
    usdpln_data["Close"] = pd.to_numeric(usdpln_data["Close"], errors="coerce")

    # Calculate forward points from bond yields if available
    if domestic_yield is not None and foreign_yield is not None:
        spot_rate = eurpln_data["Close"].iloc[-1]  # Latest close as spot rate
        tenor_months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        eurpln_fwd_data = pd.DataFrame({
            "Tenor": [f"{m}M" for m in tenor_months],
            "Spot": spot_rate,
            "Points": [spot_rate * ((domestic_yield - foreign_yield) / 12) * m / 100 for m in tenor_months],
        })
        eurpln_fwd_data["Forward"] = eurpln_fwd_data["Spot"] + eurpln_fwd_data["Points"]
    else:
        eurpln_fwd_data = pd.DataFrame(columns=["Tenor", "Spot", "Points", "Forward"])

    # Volatility Charts
    st.subheader("Volatility Charts")
    fig, axes = plt.subplots(2, 1, figsize=(8, 6))
    axes[0].plot(eurpln_data["Date"], eurpln_data["Z-score"], label="EUR/PLN Z-score")
    axes[0].axhline(0, color='black', linestyle='--', linewidth=1)
    axes[0].set_title("Volatility EUR/PLN")
    axes[0].grid(True, linestyle="--", alpha=0.5)

    axes[1].plot(usdpln_data["Date"], usdpln_data["Z-score"], label="USD/PLN Z-score")
    axes[1].axhline(0, color='black', linestyle='--', linewidth=1)
    axes[1].set_title("Volatility USD/PLN")
    axes[1].grid(True, linestyle="--", alpha=0.5)

    st.pyplot(fig)

    # Forward Rates Charts
    st.subheader("Outright Forward Rates")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(eurpln_fwd_data["Tenor"], eurpln_fwd_data["Points"], color="lightblue")
    for i, val in enumerate(eurpln_fwd_data["Points"]):
        ax.text(i, val + 0.002, f"{val:.4f}", ha="center", fontsize=10)
    ax.set_title("Outright EUR/PLN")
    ax.set_ylabel("Forward Points")
    ax.set_xticklabels(eurpln_fwd_data["Tenor"], rotation=45)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    st.pyplot(fig)

    # Forward Rate Table
    st.subheader("Forward Rate Table")
    st.dataframe(eurpln_fwd_data)
else:
    st.warning("Please upload an Excel file to proceed.")
