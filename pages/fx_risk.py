import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from database import get_connection
from datetime import datetime

st.title("📉 FX Exposure & Risk Dashboard")

conn = get_connection()

# --- Load Data ---
clients_df = pd.read_sql_query("SELECT name, base_currency, budget_rate FROM clients", conn)
payments_df = pd.read_sql_query("""
    SELECT client_name, currency, direction, amount, payment_date
    FROM payments
    WHERE status = 'Unpaid'
""", conn)
hedges_df = pd.read_sql_query("""
    SELECT client_name, currency, notional, maturity
    FROM hedges
""", conn)

if clients_df.empty or payments_df.empty:
    st.warning("Please add clients and unpaid payments first.")
    st.stop()

# --- Preprocess Dates ---
payments_df["payment_date"] = pd.to_datetime(payments_df["payment_date"])
hedges_df["maturity"] = pd.to_datetime(hedges_df["maturity"])

# --- Calculate Exposure Records Per Payment ---
kanban_records = []

for _, payment in payments_df.iterrows():
    client_name = payment["client_name"]
    direction = payment["direction"]
    amount = payment["amount"]
    date = payment["payment_date"].date()

    signed_amount = amount if direction == "Incoming" else -amount

    # Client profile
    client_row = clients_df[clients_df["name"] == client_name]
    if client_row.empty:
        continue

    budget_rate = client_row.iloc[0]["budget_rate"]
    base_currency = client_row.iloc[0]["base_currency"]

    # Hedge matched to date (same month)
    hedge_amount = hedges_df[
        (hedges_df["client_name"] == client_name) &
        (hedges_df["maturity"].dt.to_period("M") == pd.to_datetime(date).to_period("M"))
    ]["notional"].sum()

    open_exposure = signed_amount - hedge_amount
    current_rate = 1.00
    valuation_gap = (current_rate - budget_rate) * open_exposure if budget_rate else 0

    kanban_records.append({
        "Date": date,
        "Client": client_name,
        "Currency": base_currency,
        "Payment": signed_amount,
        "Hedged": hedge_amount,
        "Open Exposure": open_exposure,
        "Valuation Gap": valuation_gap
    })

# --- Organize by Date ---
kanban_df = pd.DataFrame(kanban_records)
if kanban_df.empty:
    st.info("No data to display.")
    st.stop()

grouped = kanban_df.groupby("Date")

# --- Kanban View ---
st.subheader("🗂️ Exposure Timeline (Kanban Style)")

for date, group in grouped:
    st.markdown(f"### 🗓️ {date.strftime('%Y-%m-%d')}")
    for _, row in group.iterrows():
        st.markdown(f"""
        **👤 {row['Client']}** ({row['Currency']})  
        - 💸 Payment: `{row['Payment']:,.2f}`  
        - 🛡️ Hedged: `{row['Hedged']:,.2f}`  
        - 📉 Open Exposure: `{row['Open Exposure']:,.2f}`  
        - ⚠️ Valuation Gap: `{row['Valuation Gap']:,.2f}`  
        ---
        """)
