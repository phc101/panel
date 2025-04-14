
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Strategic FX Hedge Planner", layout="wide")

st.title("💱 Strategic FX Hedge Planner")

# --- Sidebar Inputs ---
st.sidebar.header("📥 Inputs")

spot_rate = st.sidebar.number_input("Current Spot Rate (e.g. 4.30)", value=4.30, step=0.0001)
target_rate = st.sidebar.number_input("Target Weighted Avg Hedge Rate", value=4.40, step=0.0001)

hedge_months = st.sidebar.slider("Hedging Horizon (Months)", min_value=1, max_value=12, value=6)

st.sidebar.markdown("### 📈 Forward Points (vs Spot, %)")
forward_points_input = {}
for m in range(1, hedge_months + 1):
    forward_points_input[m] = st.sidebar.number_input(f"{m}M", value=0.01 * m, step=0.0001, format="%.4f")

st.sidebar.markdown("### 📊 Monthly Hedge Volume (EUR)")
monthly_volume = st.sidebar.number_input("Volume per Month", value=100_000, step=10_000)

# --- Existing Hedges (Optional Upload) ---
st.header("📂 Existing Hedges (Optional)")
uploaded_file = st.file_uploader("Upload CSV with columns: Maturity Date, Volume (EUR), Rate", type=["csv"])

if uploaded_file:
    existing_hedges = pd.read_csv(uploaded_file, parse_dates=["Maturity Date"])
else:
    existing_hedges = pd.DataFrame(columns=["Maturity Date", "Volume (EUR)", "Rate"])

# --- New Hedges Calculation ---
from datetime import datetime, timedelta

today = pd.Timestamp.today()
new_hedges = []

for m in range(1, hedge_months + 1):
    maturity_date = (today + pd.DateOffset(months=m)).replace(day=10)
    fwd_multiplier = 1 + forward_points_input[m]
    forward_rate = spot_rate * fwd_multiplier
    new_hedges.append({
        "Maturity Date": maturity_date,
        "Volume (EUR)": monthly_volume,
        "Rate": forward_rate,
        "Type": "New"
    })

new_hedges_df = pd.DataFrame(new_hedges)

# Combine existing and new
existing_hedges["Type"] = "Existing"
combined_df = pd.concat([existing_hedges, new_hedges_df], ignore_index=True)

# --- Weighted Avg Calculation ---
total_volume = combined_df["Volume (EUR)"].sum()
weighted_avg = (combined_df["Volume (EUR)"] * combined_df["Rate"]).sum() / total_volume if total_volume else 0.0

st.header("📈 Hedge Portfolio Overview")
st.write(f"**Weighted Avg Hedge Rate: {weighted_avg:.4f}** | **Target: {target_rate:.4f}** | **Total Volume: {total_volume:,.0f} EUR**")

# --- Chart ---
fig, ax = plt.subplots(figsize=(10, 5))
for key, grp in combined_df.groupby("Type"):
    ax.plot(grp["Maturity Date"], grp["Rate"], marker='o', label=key)
    for _, row in grp.iterrows():
        ax.annotate(f"{int(row['Volume (EUR)'])}", (row["Maturity Date"], row["Rate"]), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8)

ax.axhline(weighted_avg, color='red', linestyle='--', label=f"Weighted Avg: {weighted_avg:.4f}")
ax.axhline(target_rate, color='green', linestyle='--', label=f"Target: {target_rate:.4f}")
ax.set_xlabel("Maturity Date")
ax.set_ylabel("Rate")
ax.set_title("EUR/PLN Hedge Portfolio")
ax.grid(True)
ax.legend()
plt.xticks(rotation=45)
st.pyplot(fig)

# --- Download ---
st.download_button("📤 Download Hedge Plan CSV", data=combined_df.to_csv(index=False), file_name="hedge_plan.csv")
