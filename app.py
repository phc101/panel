import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import os

# Function to calculate forward rate
def calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, days, margin):
    if days <= 0:
        return 0
    years = days / 365
    adjusted_spot_rate = spot_rate - (spot_rate * margin)  # Subtract margin from spot rate
    return adjusted_spot_rate * ((1 + domestic_rate) / (1 + foreign_rate)) ** years

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

# Display logo at the top
logo_path = "phc_logo.png"  # Replace with the actual file path
if os.path.exists(logo_path):
    st.image(logo_path, width=100)
else:
    st.warning("Logo not found. Please ensure 'phc_logo.png' is in the correct directory.")

# Title
st.title("FX Forward Rate Calculator")
st.write("### Select Month to Plan Cashflows")

# Global interest rates
with st.sidebar:
    st.header("Global Settings")
    global_domestic_rate = st.slider("Global Domestic Interest Rate (%)", 0.0, 10.0, 5.0, step=0.25) / 100
    global_foreign_rate = st.slider("Global Foreign Interest Rate (%)", 0.0, 10.0, 3.0, step=0.25) / 100

# Horizontal bookmarks for month navigation
selected_month = st.radio(
    "Months", MONTH_NAMES, index=st.session_state.selected_month - 1, horizontal=True
)
st.session_state.selected_month = MONTH_NAMES.index(selected_month) + 1

# Sidebar for managing cashflows
with st.sidebar:
    st.header(f"Add Cashflow for {selected_month}")
    currency = st.selectbox("Currency", ["EUR", "USD"], key="currency")
    amount = st.number_input("Cashflow Amount", min_value=0.0, value=1000.0, step=100.0, key="amount")
    window_open_date = st.date_input("Window Open Date", min_value=datetime.today(), key="window_open_date")
    months_to_maturity = st.number_input("Maturity (in months)", min_value=1, value=1, step=1, key="months_to_maturity")
    spot_rate = st.number_input("Spot Rate", min_value=0.0, value=4.5, step=0.01, key="spot_rate")

    # Calculate maturity date
    maturity_date = window_open_date + timedelta(days=30 * months_to_maturity)

    if st.button("Add Cashflow"):
        st.session_state.monthly_cashflows[st.session_state.selected_month].append({
            "Currency": currency,
            "Amount": amount,
            "Window Open Date": window_open_date,
            "Maturity Date": maturity_date,
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
            window_open_date = st.date_input(f"Window Open Date for Record {i + 1}", value=cashflow["Window Open Date"], key=f"window_open_date_{i}")
            months_to_maturity = st.number_input(f"Maturity (in months) for Record {i + 1}", value=(cashflow["Maturity Date"] - cashflow["Window Open Date"]).days // 30, step=1, key=f"maturity_{i}")
            maturity_date = window_open_date + timedelta(days=30 * months_to_maturity)
            spot_rate = st.number_input(f"Spot Rate for Record {i + 1}", value=cashflow["Spot Rate"], step=0.01, key=f"spot_rate_{i}")

            # Delete button
            if st.button(f"🗑 Delete Record {i + 1}", key=f"delete_{i}"):
                st.session_state.monthly_cashflows[st.session_state.selected_month].pop(i)
                st.experimental_set_query_params(refresh=True)  # Dynamic refresh
                st.stop()  # Stop rendering after deletion

            # Collect edited cashflows
            edited_cashflows.append({
                "Currency": currency,
                "Amount": amount,
                "Window Open Date": window_open_date,
                "Maturity Date": maturity_date,
                "Spot Rate": spot_rate,
            })

    # Update session state with edited data
    st.session_state.monthly_cashflows[st.session_state.selected_month] = edited_cashflows

    # Calculate forward rate, PLN value, and profit for each record
    results = []
    total_profit = 0
    for cashflow in st.session_state.monthly_cashflows[st.session_state.selected_month]:
        days = (cashflow["Maturity Date"] - cashflow["Window Open Date"]).days
        margin = calculate_margin(days)
        forward_rate = calculate_forward_rate(
            cashflow["Spot Rate"], global_domestic_rate, global_foreign_rate, days, margin
        )
        adjusted_spot_rate = cashflow["Spot Rate"] - (cashflow["Spot Rate"] * margin)
        pln_value = forward_rate * cashflow["Amount"]
        profit = (cashflow["Spot Rate"] - adjusted_spot_rate) * cashflow["Amount"]  # Profit from margin
        total_profit += profit
        results.append({
            "Forward Rate": round(forward_rate, 4),
            "Adjusted Spot Rate": round(adjusted_spot_rate, 4),
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
        days = (cashflow["Maturity Date"] - cashflow["Window Open Date"]).days
        margin = calculate_margin(days)
        forward_rate = calculate_forward_rate(
            cashflow["Spot Rate"], global_domestic_rate, global_foreign_rate, days, margin
        )
        adjusted_spot_rate = cashflow["Spot Rate"] - (cashflow["Spot Rate"] * margin)
        pln_value = forward_rate * cashflow["Amount"]
        profit = (cashflow["Spot Rate"] - adjusted_spot_rate) * cashflow["Amount"]
        all_results.append({
            "Month": MONTH_NAMES[month - 1],
            "Currency": cashflow["Currency"],
            "Amount": cashflow["Amount"],
            "Window Open Date": cashflow["Window Open Date"],
            "Maturity Date": cashflow["Maturity Date"],
            "Spot Rate": cashflow["Spot Rate"],
            "Forward Rate": round(forward_rate, 4),
            "Adjusted Spot Rate": round(adjusted_spot_rate, 4),
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
st.caption("Developed by Premium Hedge Consulting")
