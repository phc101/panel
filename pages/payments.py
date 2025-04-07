import streamlit as st
import datetime

st.title("💸 Payments")

st.markdown("Track incoming and outgoing payments here.")

with st.form("add_payment"):
    client_name = st.text_input("Client Name")
    amount = st.number_input("Amount", step=0.01)
    currency = st.selectbox("Currency", ["EUR", "USD", "PLN", "GBP"])
    direction = st.radio("Direction", ["Incoming", "Outgoing"])
    payment_date = st.date_input("Payment Date", value=datetime.date.today())
    notes = st.text_area("Notes")
    
    submitted = st.form_submit_button("Add Payment")
    if submitted:
        st.success(f"Logged {direction.lower()} payment of {amount} {currency} for {client_name}")
