import streamlit as st
import pandas as pd

st.title("📉 FX Exposure & Risk")

st.markdown("Monitor your currency exposure by client and currency.")

# Dummy data for now
exposure_data = pd.DataFrame({
    "Client": ["Client A", "Client B", "Client C"],
    "Currency": ["EUR", "USD", "PLN"],
    "Open Position": [150000, -75000, 32000],
    "Budget Rate": [4.25, 3.90, 1.00],
    "Current Rate": [4.30, 4.00, 1.00],
})

exposure_data["Valuation Gap"] = (exposure_data["Current Rate"] - exposure_data["Budget Rate"]) * exposure_data["Open Position"]

st.dataframe(exposure_data.style.format({
    "Open Position": "{:,.0f}",
    "Budget Rate": "{:.4f}",
    "Current Rate": "{:.4f}",
    "Valuation Gap": "{:,.2f}"
}))
