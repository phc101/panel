import streamlit as st
from datetime import datetime
import pandas as pd

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

# Form to add new cashflow
st.sidebar.header("Add New Cashflow")
currency = st.sidebar.selectbox("Currency", ["EUR", "USD"], key="currency")
amount = st.sidebar.number_input("Cashflow Amount", min_value=0.0, value=1000.0, step=100.0, key="amount")
future_date = st.sidebar.date_input("Future Date", min_value=datetime.today(), key="future_date")
domestic_rate = st.sidebar.slider("Domestic Interest Rate (%)", 0.0, 10.0, 5.0, step=0.25, key="domestic_rate") / 100
foreign_rate = st.sidebar.slider("Foreign Interest Rate (%)", 0.0, 10.0, 3.0, step=0.25, key="foreign_rate") / 100
spot_rate = st.sidebar.number_input("Spot Rate", min_value=0.0, value=4.5, step=0.01, key="spot_rate")

if st.sidebar.button("Add Cashflow"):
    st.session_state.cashflows.append({
        "Currency": currency,
        "Amount": amount,
        "Future Date": future_date,
        "Domestic Rate (%)": domestic_rate * 100,
        "Foreign Rate (%)": foreign_rate * 100,
        "Spot Rate": spot_rate,
    })

# Display and edit cashflows
st.header("Cashflow Records")
if len(st.session_state.cashflows) > 0:
    # Editable table simulation
    edited_cashflows = []
    for i, cashflow in enumerate(st.session_state.cashflows):
        st.write(f"**Record {i+1}**")
        currency = st.selectbox(f"Currency for Record {i+1}", ["EUR", "USD"], index=["EUR", "USD"].index(cashflow["Currency"]), key=f"currency_{i}")
        amount = st.number_input(f"Amount for Record {i+1}", value=cashflow["Amount"], step=100.0, key=f"amount_{i}")
        future_date = st.date_input(f"Future Date for Record {i+1}", value=cashflow["Future Date"], key=f"future_date_{i}")
        domestic_rate = st.slider(f"Domestic Interest Rate (%) for Record {i+1}", 0.0, 10.0, value=cashflow["Domestic Rate (%)"], step=0.25, key=f"domestic_rate_{i}") / 100
        foreign_rate = st.slider(f"Foreign Interest Rate (%) for Record {i+1}", 0.0, 10.0, value=cashflow["Foreign Rate (%)"], step=0.25, key=f"foreign_rate_{i}") / 100
        spot_rate = st.number_input(f"Spot Rate for Record {i+1}", value=cashflow["Spot Rate"], step=0.01, key=f"spot_rate_{i}")
        edited_cashflows.append({
            "Currency": currency,
            "Amount": amount,
            "Future Date": future_date,
            "Domestic Rate (%)": domestic_rate * 100,
            "Foreign Rate (%)": foreign_rate * 100,
            "Spot Rate": spot_rate,
        })

    # Update session state with edited data
    st.session_state.cashflows = edited_cashflows

    # Calculate forward rate and PLN value for each record
    results = []
    for cashflow in st.session_state.cashflows:
        days = (cashflow["Future Date"] - datetime.today().date()).days
        forward_rate = calculate_forward_rate(
            cashflow["Spot Rate"], cashflow["Domestic Rate (%)"] / 100, cashflow["Foreign Rate (%)"] / 100, days
        )
        pln_value = forward_rate * cashflow["Amount"]
        results.append({"Forward Rate": round(forward_rate, 4), "PLN Value": round(pln_value, 2)})

    # Add results to DataFrame and display
    df = pd.DataFrame(st.session_state.cashflows)
    results_df = pd.DataFrame(results)
    final_df = pd.concat([df, results_df], axis=1)
    st.table(final_df)
else:
    st.info("No cashflow records added yet. Use the sidebar to add records.")

# Footer
st.markdown("---")
st.caption("Developed using Streamlit")
