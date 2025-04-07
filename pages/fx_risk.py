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
    current_rate = 1.00  # placeholder for real FX rate
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

# --- UI: Select Metric to Plot ---
st.subheader("📊 Bar Chart by Client")
chart_option = st.selectbox("Select Metric to Plot", ["Open Exposure", "Net Payments", "Hedged", "Valuation Gap"])

if not summary_df.empty:
    st.dataframe(summary_df.style.format({
        "Net Payments": "{:,.2f}",
        "Hedged": "{:,.2f}",
        "Open Exposure": "{:,.2f}",
        "Budget Rate": "{:.4f}",
        "Valuation Gap": "{:,.2f}"
    }))

    # Bar Chart
    fig1, ax1 = plt.subplots()
    ax1.bar(summary_df["Client"], summary_df[chart_option])
    ax1.set_ylabel(chart_option)
    ax1.set_title(f"{chart_option} by Client")
    ax1.grid(True, linestyle="--", linewidth=0.3)
    st.pyplot(fig1)

# --- Timeline Chart (Payment-Based) ---
st.subheader("📆 Timeline Chart by Payment Date")

if not payments_df.empty:
    payments_df["payment_date"] = pd.to_datetime(payments_df["payment_date"])

    # Apply direction to amounts
    payments_df["net_amount"] = payments_df.apply(
        lambda row: row["amount"] if row["direction"] == "Incoming" else -row["amount"], axis=1
    )

    timeline = (
        payments_df.groupby("payment_date")["net_amount"]
        .sum()
        .reset_index()
        .rename(columns={"net_amount": "Net Payments"})
    )

    # Cumulative Exposure
    timeline["Open Exposure"] = timeline["Net Payments"].cumsum()

    # Placeholder for other metrics if needed
    if chart_option not in timeline.columns:
        timeline[chart_option] = timeline["Open Exposure"]

    fig2, ax2 = plt.subplots()
    ax2.plot(timeline["payment_date"], timeline[chart_option], marker='o')
    ax2.set_title(f"{chart_option} Over Time")
    ax2.set_ylabel(chart_option)
    ax2.set_xlabel("Payment Date")
    ax2.grid(True, linestyle="--", linewidth=0.3)
    st.pyplot(fig2)
else:
    st.info("No unpaid payments with valid dates to plot.")
