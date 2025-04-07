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
    SELECT client_name, currency, direction, amount, payment_date
    FROM payments
    WHERE status = 'Unpaid'
""", conn)

# --- Load Hedges ---
hedges_df = pd.read_sql_query("""
    SELECT client_name, currency, notional
    FROM hedges
""", conn)

# --- Exposure Summary by Client ---
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
    current_rate = 1.00  # placeholder for FX rate
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

summary_df = pd_
