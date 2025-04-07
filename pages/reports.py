import streamlit as st
import pandas as pd
from io import BytesIO

st.title("📊 Reports & Exports")

st.markdown("View and download summary reports per client or globally.")

# Dummy report data
df = pd.DataFrame({
    "Client": ["Client A", "Client B", "Client C"],
    "Total Payments": [120000, 80000, 95000],
    "Net FX Exposure": [50000, -20000, 12000],
    "Hedged Amount": [30000, 0, 12000],
    "Remaining Exposure": [20000, -20000, 0],
})

st.dataframe(df.style.format({
    "Total Payments": "{:,.0f}",
    "Net FX Exposure": "{:,.0f}",
    "Hedged Amount": "{:,.0f}",
    "Remaining Exposure": "{:,.0f}",
}))

# Download button
csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Download CSV Report",
    data=csv,
    file_name="fx_treasury_report.csv",
    mime="text/csv"
)
