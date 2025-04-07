import streamlit as st
import pandas as pd
from database import get_connection

st.title("📊 Reports & Export")

conn = get_connection()

# --- Payments Report ---
st.subheader("💸 All Payments")

try:
    payments = pd.read_sql_query("SELECT * FROM payments ORDER BY payment_date DESC", conn)

    if not payments.empty:
        st.dataframe(payments)
        csv = payments.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Payments CSV",
            data=csv,
            file_name="payments_report.csv",
            mime="text/csv"
        )
    else:
        st.info("No payments available.")
except Exception as e:
    st.error(f"Error loading payments data: {e}")

# --- Hedges Report ---
st.subheader("🛡️ All Hedges")

try:
    hedges = pd.read_sql_query("SELECT * FROM hedges ORDER BY maturity ASC", conn)

    if not hedges.empty:
        st.dataframe(hedges)
        csv2 = hedges.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Hedges CSV",
            data=csv2,
            file_name="hedges_report.csv",
            mime="text/csv"
        )
    else:
        st.info("No hedge data available.")
except Exception as e:
    st.error(f"Error loading hedging data: {e}")
