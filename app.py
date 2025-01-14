import streamlit as st
from datetime import datetime
import pandas as pd

# Mocked function to get spot rate
def get_spot_rate(currency):
    # Replace with a real API for live rates
    spot_rates = {'EUR': 4.5, 'USD': 4.0}  # Example static data
    return spot_rates.get(currency, 0)

# Function to calculate forward rate
def calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, days):
    if days <= 0:
        return 0
    years = days / 365
    return spot_rate * ((1 + domestic_rate) / (1 + foreign_rate)) ** years

# Streamlit App
st.title("FX Forward Rate Calculator")

st.markdown("""
This app allows you to calculate forward rates for multiple future cashflows in EUR or USD and see their equivalent values in PLN. You can also edit existing records.
""")

# Placeholder for cashflows
if "cashflows" not in st.session_state:
    st.session_state.cashflows = []

# Form to add or edit cashflows
st.sidebar.header("Manage Cashflows")
currency = st.sidebar.selectbox("Currency", ["EUR", "USD"], key="currency")
amount = st.sidebar.number_input("Cashflow Amount", min_value=0.0, value=1000.0, step=100.0, key="amount")
future_date = st.sidebar.date_input("Future Date", min_value=datetime.today(), key="future_date")
domestic_rate = st.sidebar.slider("Domestic Interest Rate (%)", 0.0, 10.0, 5.0, step=0.25, key="domestic_rate") / 100
foreign_rate = st.sidebar.slider("Foreign Interest Rate (%)", 0.0, 10.0, 3.0, step=0.25, key="foreign_rate") / 100

# Add or Edit Cashflow
if st.sidebar.button("Add Cashflow"):
    st.session_state.cashflows.append({
        "Currency": currency,
        "Amount": amount,
        "Future Date": future_date,
        "Domestic Rate (%)": domestic_rate * 100,
        "Foreign Rate (%)": foreign_rate * 100,
    })

st.header("Cashflow Records")
if len(st.session_state.cashflows) > 0:
    # Convert to DataFrame
    df = pd.DataFrame(st.session_state.cashflows)
    
    # Editable Table
    edited_df = st.experimental_data_editor(df, num_rows="dynamic", key="edited_df")
    
    # Update session state with edited data
    st.session_state.cashflows = edited_df.to_dict("records")
    
    # Calculate forward rate and PLN value for each record
    results = []
    for i, row in edited_df.iterrows():
        spot_rate = get_spot_rate(row["Currency"])
        days = (row["Future Date"] - datetime.today().date()).days
        forward_rate = calculate_forward_rate(
            spot_rate, row["Domestic Rate (%)"] / 100, row["Foreign Rate (%)"] / 100, days
        )
        pln_value = forward_rate * row["Amount"]
        results.append({"Forward Rate": round(forward_rate, 4), "PLN Value": round(pln_value, 2)})
    
    # Add results to DataFrame
    results_df = pd.DataFrame(results)
    final_df = pd.concat([edited_df, results_df], axis=1)
    
    # Display results table
    st.table(final_df)
else:
    st.info("No cashflow records added yet. Use the sidebar to add records.")

# Footer
st.markdown("---")
st.caption("Developed using Streamlit")
