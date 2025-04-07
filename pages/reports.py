import streamlit as st
import pandas as pd
from io import StringIO
from database import get_connection

st.title("📊 Reports & Export")

conn = get_connection()

# --- Fetch and display payments ---
st.subheader("💸 All Payments")

payments = pd.read_sql_query("SELECT * FROM payments ORDER BY payment_date DESC", conn)

if not payments.empty:
    st.dataframe(payments)
    csv = payments.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Payments CSV", csv, "payments.csv", "text/csv")
else:
    st.info("No payments to display.")

# --- Fetch and display hedges ---
st.subheader("🛡️ All Hedges")

hedges = pd.read_sql_query("SELECT * FROM hedges ORDER BY maturity ASC", conn)

if not hedges.empty:
    st.dataframe(hedges)
    csv2 = hedges.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Hedges CSV", csv2, "hedges.csv", "text/csv")
else:
    st.info("No hedging data yet.")
