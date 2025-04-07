import streamlit as st
import datetime

st.title("🛡️ Hedging Simulation")

st.markdown("Simulate FX hedging strategies for each client.")

with st.form("hedge_form"):
    client_name = st.text_input("Client Name")
    hedge_type = st.selectbox("Hedge Type", ["Forward", "Call Option", "Put Option", "Synthetic Forward"])
    notional = st.number_input("Notional Amount", step=1000.0)
    currency = st.selectbox("Currency", ["EUR", "USD", "PLN", "GBP"])
    strike = st.number_input("Strike Rate", step=0.0001, format="%.4f")
    maturity = st.date_input("Maturity Date", min_value=datetime.date.today())
    premium = st.number_input("Option Premium (if applicable)", step=0.01)

    submitted = st.form_submit_button("Add Hedge")
    if submitted:
        st.success(f"{hedge_type} added for {client_name} - {notional} {currency} @ {strike:.4f}, matures {maturity}")
