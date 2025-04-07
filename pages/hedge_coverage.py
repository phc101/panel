import streamlit as st
import pandas as pd
import numpy as np
from database import get_connection

st.title("📅 Hedge Coverage Overview")

conn = get_connection()

# --- Load Data ---
payments_df = pd.read_sql_query("""
    SELECT client_name, amount, currency, direction, payment_date, status
    FROM payments
    WHERE status = 'Unpaid'
""", conn)

hedges_df = pd.read_sql_query("""
    SELECT client_name, currency, strike, notional, maturity
    FROM hedges
""", conn)

# --- Preprocess Dates ---
payments_df["payment_date"] = pd.to_datetime(payments_df["payment_date"])
hedges_df["maturity"] = pd.to_datetime(hedges_df["maturity"])

# --- Create Month Column ---
payments_df["month"] = payments_df["payment_date"].dt.to_period("M").dt.to_timestamp()
hedges_df["month"] = hedges_df["maturity"].dt.to_period("M").dt.to_timestamp()

# --- Calculate Net Payment Exposure ---
payments_df["signed_amount"] = payments_df.apply(
    lambda row: row["amount"] if row["direction"] == "Incoming" else -row["amount"], axis=1
)
exposure = payments_df.groupby(["client_name", "month"])["signed_amount"].sum().reset_index()
exposure.rename(columns={"signed_amount": "fx_need"}, inplace=True)

# --- Calculate Hedge Totals ---
hedged = hedges_df.groupby(["client_name", "month"]).agg({
    "notional": "sum",
    "strike": "mean"
}).reset_index().rename(columns={
    "notional": "hedged_volume",
    "strike": "avg_rate"
})

# --- Merge and Fill ---
coverage = pd.merge(exposure, hedged, on=["client_name", "month"], how="outer")
coverage["fx_need"] = coverage["fx_need"].fillna(0)
coverage["hedged_volume"] = coverage["hedged_volume"].fillna(0)
coverage["avg_rate"] = coverage["avg_rate"].fillna(np.nan)

# --- Calculate Metrics ---
coverage["coverage_pct"] = np.where(
    coverage["fx_need"] != 0,
    (coverage["hedged_volume"] / coverage["fx_need"]) * 100,
    0
)
coverage["to_hedge"] = coverage["fx_need"] - coverage["hedged_volume"]

# --- Reshape Summary Vertically ---
summary = coverage.melt(
    id_vars=["client_name", "month"],
    value_vars=["fx_need", "hedged_volume", "to_hedge", "coverage_pct"],
    var_name="category",
    value_name="value"
).sort_values(by=["client_name", "month", "category"])

# --- Display ---
st.subheader("📊 Monthly Hedge Volumes (Hedged Notional)")
pivoted = coverage.pivot_table(
    index="client_name",
    columns="month",
    values="hedged_volume",
    aggfunc="sum",
    fill_value=0
)
st.dataframe(pivoted.style.format("{:,.0f}"))

st.subheader("📈 Vertical Summary by Client and Month")
st.dataframe(summary.style.format({"value": "{:,.2f}"}))
