import streamlit as st
import pandas as pd
from database import get_connection

st.title("📉 FX Exposure & Risk Dashboard")

conn = get_connection()

# --- Load client info ---
clients_df = pd.read_sql_query("SELECT name, base_currency, budget_rate FROM clients", conn)

if clients_df.empty:
    st.warning("No client data found.")
    st.stop()

# --- Load payments ---
payments_df = pd.read_sql_query("""
    SELECT client_name, currency, direction, amount
    FROM payments
    WHERE status = 'Unpaid'
""", conn)

# --- Load hedges ---
hedges_df = pd.read_sql_query("""
    SELECT client_name, currency, notional
    FROM hedges
""", conn)

# --- Calculate Exposure per Client ---
exposure_summary = []

for _, row in clients_df.iterrows():
    client = row["name"]
    base_currency = row["base_currency"]
    budget_rate = row["budget_rate"]

    # Total inflows/outflows
    client_payments = payments_df[payments_df["client_name"] == client]
    net_exposure = 0

    for _, p in client_payments.iterrows():
        direction = p["direction"]
        amount = p["amount"]
        net_exposure += amount if direction == "Incoming" else -amount

    # Hedge total
    client_hedges = hedges_df[hedges_df["client_name"] == client]
    total_hedged = client_hedges["notional"].sum() if not client_hedges.empty else 0

    # Net open exposure
    open_exposure = net_exposure - total_hedged

    # Valuation (assuming current rate = 1.00 for simplicity)
    current_rate = 4.29
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

# --- Display Table ---
summary_df = pd.DataFrame(exposure_summary)

if not summary_df.empty:
    st.dataframe(summary_df.style.format({
        "Net Payments": "{:,.2f}",
        "Hedged": "{:,.2f}",
        "Open Exposure": "{:,.2f}",
        "Budget Rate": "{:.4f}",
        "Valuation Gap": "{:,.2f}"
    }))
else:
    st.info("No exposure data available.")
