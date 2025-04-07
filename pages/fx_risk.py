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
    SELECT client_name, currency, notional, maturity
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
    current_rate = 1.00  # placeholder
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

# --- Risk Threshold Inputs ---
st.sidebar.header("⚠️ Risk Alerts Settings")
exposure_limit = st.sidebar.number_input("Max Open Exposure", value=50000.0, step=1000.0)
valuation_limit = st.sidebar.number_input("Max Valuation Gap", value=10000.0, step=500.0)

# --- Risk Alerts ---
st.subheader("⚠️ Risk Alerts")

if not summary_df.empty:
    alerts = summary_df[
        (summary_df["Open Exposure"].abs() > exposure_limit) |
        (summary_df["Valuation Gap"].abs() > valuation_limit)
    ]
    if not alerts.empty:
        st.warning("⚠️ Clients breaching risk thresholds:")
        st.dataframe(alerts.style.format({
            "Open Exposure": "{:,.2f}",
            "Valuation Gap": "{:,.2f}"
        }))
    else:
        st.success("✅ No clients breaching risk thresholds.")
else:
    st.info("No exposure data to evaluate.")

# --- Chart Selector ---
st.subheader("📊 Exposure Chart by Client")
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

# --- Timeline Chart ---
st.subheader("📆 Timeline Chart by Payment Date")

if not payments_df.empty:
    payments_df["payment_date"] = pd.to_datetime(payments_df["payment_date"])
    payments_df["net_amount"] = payments_df.apply(
        lambda row: row["amount"] if row["direction"] == "Incoming" else -row["amount"], axis=1
    )

    timeline = (
        payments_df.groupby("payment_date")["net_amount"]
        .sum()
        .reset_index()
        .rename(columns={"net_amount": "Net Payments"})
    )

    timeline["Open Exposure"] = timeline["Net Payments"].cumsum()

    if chart_option not in timeline.columns:
        timeline[chart_option] = timeline["Open Exposure"]

    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.plot(timeline["payment_date"], timeline[chart_option], marker='o')
    ax2.set_title(f"{chart_option} Over Time")
    ax2.set_ylabel(chart_option)
    ax2.set_xlabel("Payment Date")
    ax2.grid(True, linestyle="--", linewidth=0.3)
    fig2.autofmt_xdate(rotation=45)
    st.pyplot(fig2)
else:
    st.info("No unpaid payments with valid dates to plot.")

# --- Hedge Maturity Calendar ---
st.subheader("📅 Hedge Maturity Calendar")

if not hedges_df.empty:
    hedges_df["maturity"] = pd.to_datetime(hedges_df["maturity"])
    maturity_summary = (
        hedges_df.groupby(pd.Grouper(key="maturity", freq="M"))["notional"]
        .sum()
        .reset_index()
    )

    fig3, ax3 = plt.subplots(figsize=(10, 4))
    ax3.bar(maturity_summary["maturity"].dt.strftime("%Y-%m"), maturity_summary["notional"])
    ax3.set_title("Hedge Maturities by Month")
    ax3.set_ylabel("Notional Amount")
    ax3.set_xlabel("Maturity Month")
    ax3.grid(True, linestyle="--", linewidth=0.3)
    fig3.autofmt_xdate(rotation=45)
    st.pyplot(fig3)
else:
    st.info("No hedge data with maturity dates.")
