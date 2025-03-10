import streamlit as st

def calculate_savings(transaction_volume, avg_transaction, current_fee_pct, current_fixed_fee, new_fee_pct, new_fixed_fee):
    total_transactions = transaction_volume / avg_transaction
    
    current_total_fees = (transaction_volume * (current_fee_pct / 100)) + (total_transactions * current_fixed_fee)
    new_total_fees = (transaction_volume * (new_fee_pct / 100)) + (total_transactions * new_fixed_fee)
    
    savings = current_total_fees - new_total_fees
    revenue_for_us = new_total_fees
    
    return current_total_fees, new_total_fees, savings, revenue_for_us

st.title("Micropayment Savings Calculator")

# User Inputs
transaction_volume = st.number_input("Total Monthly Microtransaction Volume ($/€)", min_value=0.0, value=100000.0, step=1000.0)
avg_transaction = st.number_input("Average Transaction Size ($/€)", min_value=0.01, value=5.0, step=0.1)

st.subheader("Current Provider Fees")
current_fee_pct = st.number_input("Current Provider Percentage Fee (%)", min_value=0.0, value=5.0, step=0.1)
current_fixed_fee = st.number_input("Current Fixed Fee per Transaction ($/€)", min_value=0.0, value=0.30, step=0.01)

st.subheader("Your Blockchain Solution Fees")
new_fee_pct = st.number_input("New Provider Percentage Fee (%)", min_value=0.0, value=1.0, step=0.1)
new_fixed_fee = st.number_input("New Fixed Fee per Transaction ($/€)", min_value=0.0, value=0.05, step=0.01)

if st.button("Calculate Savings"):
    current_total_fees, new_total_fees, savings, revenue_for_us = calculate_savings(
        transaction_volume, avg_transaction, current_fee_pct, current_fixed_fee, new_fee_pct, new_fixed_fee)
    
    st.success(f"Estimated Monthly Fees with Current Provider: ${current_total_fees:,.2f}")
    st.success(f"Estimated Monthly Fees with Your Solution: ${new_total_fees:,.2f}")
    st.success(f"Total Savings for Client: ${savings:,.2f}")
    st.info(f"Potential Monthly Revenue for Your Company: ${revenue_for_us:,.2f}")
