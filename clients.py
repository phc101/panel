import streamlit as st

st.title("👤 Clients")

st.markdown("Here you will be able to manage all your client information.")

with st.form("add_client"):
    name = st.text_input("Client Name")
    base_currency = st.selectbox("Base Currency", ["EUR", "USD", "PLN", "GBP"])
    industry = st.text_input("Industry")
    submitted = st.form_submit_button("Add Client")
    if submitted:
        st.success(f"Added client: {name} ({base_currency})")
