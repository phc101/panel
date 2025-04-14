import pandas as pd
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import get_connection

# Page configuration with custom theme
st.set_page_config(
    page_title="Strategic FX Hedge Planner",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ensure the clients table exists (shared setup)
conn = get_connection()
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        base_currency TEXT,
        industry TEXT,
        payment_terms TEXT,
        budget_rate REAL,
        risk_profile TEXT,
        tags TEXT,
        notes TEXT
    )
""")
conn.commit()

# Load client data
try:
    clients_df = pd.read_sql_query("SELECT name, base_currency, budget_rate FROM clients", conn)
except Exception:
    clients_df = pd.DataFrame(columns=["name", "base_currency", "budget_rate"])

# --- Sidebar Inputs ---
st.sidebar.markdown("<h2 style='color:#1E3A8A;'>⚙️ Hedge Settings</h2>", unsafe_allow_html=True)

spot_rate = st.sidebar.number_input("Current Spot Rate (EUR/PLN)", value=4.30, step=0.0001)
target_rate = st.sidebar.number_input("Target Weighted Avg Hedge Rate", value=4.40, step=0.0001)
hedge_months = st.sidebar.slider("Hedging Horizon (Months)", min_value=1, max_value=24, value=6)
monthly_volume = st.sidebar.number_input("Monthly Hedge Volume (EUR)", value=100_000, step=10_000)

st.sidebar.markdown("### 📈 Forward Points (% above spot)")
forward_points_input = {
    m: st.sidebar.number_input(f"{m}M", value=0.01 * m, step=0.0001, format="%.4f", key=f"fwd_{m}")
    for m in range(1, hedge_months + 1)
}

# Optional file upload or sample data
st.markdown("### 📂 Existing Hedges")
uploaded_file = st.file_uploader("Upload CSV with columns: Maturity Date, Volume (EUR), Rate", type=["csv"])
show_sample = st.checkbox("Use sample data instead", value=False)

if uploaded_file:
    existing_hedges = pd.read_csv(uploaded_file, parse_dates=["Maturity Date"])
elif show_sample:
    today = pd.Timestamp.today()
    existing_hedges = pd.DataFrame({
        "Maturity Date": [today + pd.DateOffset(months=i) for i in [1, 2]],
        "Volume (EUR)": [50_000, 75_000],
        "Rate": [4.32, 4.33]
    })
else:
    existing_hedges = pd.DataFrame(columns=["Maturity Date", "Volume (EUR)", "Rate"])

# Generate new hedge plan
today = pd.Timestamp.today()
new_hedges = []
for m in range(1, hedge_months + 1):
    maturity_date = (today + pd.DateOffset(months=m)).replace(day=10)
    forward_rate = spot_rate * (1 + forward_points_input[m])
    new_hedges.append({
        "Maturity Date": maturity_date,
        "Volume (EUR)": monthly_volume,
        "Rate": forward_rate,
        "Type": "New Hedge"
    })
new_hedges_df = pd.DataFrame(new_hedges)

# Combine with existing
type_labeled_existing = existing_hedges.copy()
type_labeled_existing["Type"] = "Existing Hedge"
combined_df = pd.concat([type_labeled_existing, new_hedges_df], ignore_index=True)

# Weighted average
total_volume = combined_df["Volume (EUR)"].sum()
weighted_avg = (combined_df["Volume (EUR)"] * combined_df["Rate"]).sum() / total_volume if total_volume else 0.0

# Display portfolio
st.markdown(f"## 📊 Hedge Portfolio Overview")
st.metric("Weighted Avg Rate", f"{weighted_avg:.4f}")
st.metric("Target Rate", f"{target_rate:.4f}")
st.metric("Total Volume (EUR)", f"{int(total_volume):,}")

# Chart
fig = go.Figure()
for hedge_type, data in combined_df.groupby("Type"):
    fig.add_trace(go.Scatter(
        x=data["Maturity Date"],
        y=data["Rate"],
        mode='markers+lines',
        name=hedge_type,
        marker=dict(size=data["Volume (EUR)"] / 10000, sizemode='area')
    ))
fig.add_hline(y=weighted_avg, line=dict(color="red", dash="dash"), name="Weighted Avg")
fig.add_hline(y=target_rate, line=dict(color="green", dash="dot"), name="Target")
fig.update_layout(title="EUR/PLN Hedge Structure", xaxis_title="Maturity Date", yaxis_title="Rate")
st.plotly_chart(fig, use_container_width=True)

# Table
st.markdown("### 📋 Full Hedge Plan")
st.dataframe(combined_df.sort_values("Maturity Date"), use_container_width=True)

# Export
csv = combined_df.to_csv(index=False)
st.download_button("📥 Download Hedge Plan", csv, file_name="hedge_plan.csv")
