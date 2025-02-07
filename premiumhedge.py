import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Load the Excel file
def load_data():
    file_path = "Dashboard.xlsx"  # Ensure correct file path
    xls = pd.ExcelFile(file_path)
    
    # Load sheets
    dane_df = pd.read_excel(xls, sheet_name="dane")
    dashboard_df = pd.read_excel(xls, sheet_name="Dashboard")
    return dane_df, dashboard_df

dane_df, dashboard_df = load_data()

# Extract historical data for EUR/PLN and USD/PLN
eurpln_data = dane_df.iloc[1:, [0, 1, 2]].copy()
eurpln_data.columns = ["Date", "Close", "Z-score"]
eurpln_data["Date"] = pd.to_datetime(eurpln_data["Date"])
eurpln_data["Close"] = pd.to_numeric(eurpln_data["Close"], errors="coerce")

usdpln_data = dane_df.iloc[1:, [9, 10, 11]].copy()
usdpln_data.columns = ["Date", "Close", "Z-score"]
usdpln_data["Date"] = pd.to_datetime(usdpln_data["Date"])
usdpln_data["Close"] = pd.to_numeric(usdpln_data["Close"], errors="coerce")

# Extract forward rates
eurpln_fwd_data = dane_df.iloc[1:, [22, 23, 24, 25]].dropna().copy()
eurpln_fwd_data.columns = ["Tenor", "Spot", "Points", "Forward"]
eurpln_fwd_data["Points"] = pd.to_numeric(eurpln_fwd_data["Points"], errors="coerce")
eurpln_fwd_data["Forward"] = pd.to_numeric(eurpln_fwd_data["Forward"], errors="coerce")
eurpln_fwd_data["Tenor"] = ["1M", "2M", "3M", "4M", "5M", "6M", "7M", "8M", "9M", "10M", "11M", "12M"]

# Streamlit UI
st.title("FX Dashboard - EUR/PLN & USD/PLN")

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
