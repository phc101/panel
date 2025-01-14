import streamlit as st
from datetime import datetime
import pandas as pd
from streamlit.components.v1 import html

# Function to calculate forward rate
def calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, days):
    if days <= 0:
        return 0
    years = days / 365
    return spot_rate * ((1 + domestic_rate) / (1 + foreign_rate)) ** years

# Function to calculate margin
def calculate_margin(days):
    months = days // 30
    base_margin = 0.002  # 0.20%
    additional_margin = 0.001 * months  # +0.10% per month
    return base_margin + additional_margin

# Initialize session state for monthly cashflows
if "monthly_cashflows" not in st.session_state:
    st.session_state.monthly_cashflows = {month: [] for month in range(1, 13)}

if "selected_month" not in st.session_state:
    st.session_state.selected_month = 1  # Default to January

# Define months for navigation
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June", 
    "July", "August", "September", "October", "November", "December"
]

# Global interest rates
with st.sidebar:
    st.header("Global Settings")
    global_domestic_rate = st.slider("Global Domestic Interest Rate (%)", 0.0, 10.0, 5.0, step=0.25) / 100
    global_foreign_rate = st.slider("Global Foreign Interest Rate (%)", 0.0, 10.0, 3.0, step=0.25) / 100

# Horizontal bookmarks for month navigation
st.write("### Select Month to Plan Cashflows")
selected_month = st.radio(
    "Months", MONTH_NAMES, index=st.session_state.selected_month - 1, horizontal=True
)
st.session_state.selected_month = MONTH_NAMES.index(selected_month) + 1

# Sidebar for managing cashflows
with st.sidebar:
    st.header(f"Add Cashflow for {selected_month}")
    currency = st.selectbox("Currency", ["EUR", "USD"], key="currency")
    amount = st.number_input("Cashflow Amount", min_value=0.0, value=1000.0, step=100.0, key="amount")
    future_date = st.date_input("Future Date", min_value=datetime.today(), key="future_date")
    spot_rate = st.number_input("Spot Rate", min_value=0.0, value=4.5, step=0.01, key="spot_rate")

    # Automatically update the selected month based on future date
    future_month = future_date.month
    if st.session_state.selected_month != future_month:
        st.session_state.selected_month = future_month

    if st.button("Add Cashflow"):
        st.session_state.monthly_cashflows[future_month].append({
            "Currency": currency,
            "Amount": amount,
            "Future Date": future_date,
            "Spot Rate": spot_rate,
        })

# Display and edit cashflows for the selected month
st.header(f"Cashflow Records for {selected_month}")
if len(st.session_state.monthly_cashflows[st.session_state.selected_month]) > 0:
    # Editable table simulation
    edited_cashflows = []
    for i, cashflow in enumerate(st.session_state.monthly_cashflows[st.session_state.selected_month]):
        with st.expander(f"Edit Record {i + 1}"):
            currency = st.selectbox(f"Currency for Record {i + 1}", ["EUR", "USD"], index=["EUR", "USD"].index(cashflow["Currency"]), key=f"currency_{i}")
            amount = st.number_input(f"Amount for Record {i + 1}", value=cashflow["Amount"], step=100.0, key=f"amount_{i}")
            future_date = st.date_input(f"Future Date for Record {i + 1}", value=cashflow["Future Date"], key=f"future_date_{i}")
            spot_rate = st.number_input(f"Spot Rate for Record {i + 1}", value=cashflow["Spot Rate"], step=0.01, key=f"spot_rate_{i}")
            delete_key = f"delete_{selected_month}_{i}"
            if st.button("🗑 Delete", key=delete_key):
                del st.session_state.monthly_cashflows[st.session_state.selected_month][i]
                st.experimental_rerun()  # Refresh the page after deletion
            edited_cashflows.append({
                "Currency": currency,
                "Amount": amount,
                "Future Date": future_date,
                "Spot Rate": spot_rate,
            })

    # Update session state with edited data
    st.session_state.monthly_cashflows[st.session_state.selected_month] = edited_cashflows

    # Calculate forward rate, PLN value, and profit for each record
    results = []
    total_profit = 0
    for cashflow in st.session_state.monthly_cashflows[st.session_state.selected_month]:
        days = (cashflow["Future Date"] - datetime.today().date()).days
        forward_rate = calculate_forward_rate(
            cashflow["Spot Rate"], global_domestic_rate, global_foreign_rate, days
        )
        margin = calculate_margin(days)
        forward_rate_with_margin = forward_rate * (1 + margin)
        pln_value = forward_rate_with_margin * cashflow["Amount"]
        profit = (forward_rate_with_margin - forward_rate) * cashflow["Amount"]
        total_profit += profit
        results.append({
            "Forward Rate": round(forward_rate, 4),
            "Forward Rate (with Margin)": round(forward_rate_with_margin, 4),
            "PLN Value": round(pln_value, 2),
            "Profit from Margin": round(profit, 2),
        })

    # Add results to DataFrame and display
    df = pd.DataFrame(st.session_state.monthly_cashflows[st.session_state.selected_month])
    results_df = pd.DataFrame(results)
    final_df = pd.concat([df, results_df], axis=1)
    st.table(final_df)

    # Display total profit for the selected month
    st.header(f"Total Profit for {selected_month}")
    st.success(f"Total Profit from Margins: PLN {round(total_profit, 2)}")
else:
    st.info(f"No cashflow records added for {selected_month}. Use the sidebar to add records.")

# Aggregated view of all positions
st.header("Aggregated Cashflow Summary")
all_results = []
for month, cashflows in st.session_state.monthly_cashflows.items():
    for cashflow in cashflows:
        days = (cashflow["Future Date"] - datetime.today().date()).days
        forward_rate = calculate_forward_rate(
            cashflow["Spot Rate"], global_domestic_rate, global_foreign_rate, days
        )
        margin = calculate_margin(days)
        forward_rate_with_margin = forward_rate * (1 + margin)
        pln_value = forward_rate_with_margin * cashflow["Amount"]
        profit = (forward_rate_with_margin - forward_rate) * cashflow["Amount"]
        all_results.append({
            "Month": MONTH_NAMES[month - 1],
            "Currency": cashflow["Currency"],
            "Amount": cashflow["Amount"],
            "Future Date": cashflow["Future Date"],
            "Spot Rate": cashflow["Spot Rate"],
            "Forward Rate": round(forward_rate, 4),
            "Forward Rate (with Margin)": round(forward_rate_with_margin, 4),
            "PLN Value": round(pln_value, 2),
            "Profit from Margin": round(profit, 2),
        })

# Display aggregated table
if all_results:
    aggregated_df = pd.DataFrame(all_results)
    st.table(aggregated_df)
else:
    st.info("No cashflows added yet.")

# Footer
st.markdown("---")
st.caption("Developed using Streamlit")
