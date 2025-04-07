import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from database import get_connection

st.title("📉 FX Exposure & Risk Dashboard")

conn = get_connection()

# --- Load Clients ---
clients_df = pd.read_sql_query("SELECT name, base_currency, budget_rate FROM clients", conn)
if clients_df.empty:
    st.warning("No client data found.")
    st.stop()

# --- Load Payments ---
payments_df = pd.read_sql_query("""
    SELECT client_name, currency, direction, amount
    FROM payments
    WHERE status = 'Unpaid'
""", conn)

# --- Load Hedges ---
hedges_df = pd.read_sql_query("""
    SELECT client_name, currency, notional
    FROM hedges
""", conn)

# --- Calculate Exposure Summary ---
exposure_summary = []

for _, row in clients_df.iterrows():
    client = row["name"]
    base_currency = row["base_currency"]
    budget_rate = row["budget_rate"]
    
    client_payments = payments_df[payments_df["client_name"] == client]
    net_exposure = sum(
        p["amount"] if p["direction"] == "Incoming" else -p["amount"]
        for _, p in client_payments.iterrows()
    )

    client_hedges = hedges_df[hedges_df["client_name"] == client]
    total_hedged = client_hedges["notional"].sum() if not client_hedges.empty else 0

    open_exposure = net_exposure - total_hedged
    current_rate = 1.00  # Placeholder, could later be input or pulled live
    valuation_gap = (current_rate - budget_rate) * open_exposure if budget_rate else 0

    exposure_summary.append({
        "Client": client,
        "Currency": base_currency,
        "Net Payments": net_exposure,
        "Hedged": total_hedged,
        "Open Exposure": open_exposure,
        "Budget Rate": budget_rate,
        "Valuation Gap": valuation_gap
    })

summary_df = pd.DataFrame(exposure_summary)

# --- Chart Selector ---
st.subheader("📈 Exposure Chart")
chart_option = st.selectbox("Select Metric to Plot", ["Open Exposure", "Net Payments", "Hedged", "Valuation Gap"])

if not summary_df.empty:
    st.dataframe(summary_df.style.format({
        "Net Payments": "{:,.2f}",
        "Hedged": "{:,.2f}",
        "Open Exposure": "{:,.2f}",
        "Budget Rate": "{:.4f}",
        "Valuation Gap": "{:,.2f}"
    }))

    fig, ax = plt.subplots()
    ax.bar(summary_df["Client"], summary_df[chart_option])
    ax.set_ylabel(chart_option)
    ax.set_title(f"{chart_option} by Client")
    ax.grid(True, linestyle="--", linewidth=0.3)
    st.pyplot(fig)
else:
    st.info("No exposure data available.")
