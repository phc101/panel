import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import os

# Fix Matplotlib backend for Streamlit
matplotlib.use("agg")  # Use non-interactive backend for Streamlit

# Function to calculate forward rate for a given tenor
def calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, days):
    if days <= 0:
        return spot_rate
    years = days / 365
    return spot_rate * ((1 + domestic_rate) / (1 + foreign_rate)) ** years

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
    window_tenor = st.number_input("Window Tenor (in months)", min_value=1, value=1, step=1, key="window_tenor")
    spot_rate = st.number_input("Spot Rate", min_value=0.0, value=4.5, step=0.0001, key="spot_rate")
    points_adjustment = st.slider(
        "Adjust Forward Points up to Window Open Date (%)", 
        0.0, 1.30, 1.0, step=0.01
    )

    # Ensure the tab corresponds to the month of the Window Open Date
    if window_open_date.month != st.session_state.selected_month:
        st.session_state.selected_month = window_open_date.month

    # Calculate maturity date
    maturity_date = window_open_date + timedelta(days=30 * window_tenor)

    if st.button("Add Cashflow"):
        st.session_state.monthly_cashflows[st.session_state.selected_month].append({
            "Currency": currency,
            "Amount": amount,
            "Window Open Date": str(window_open_date),  # Convert to string to ensure persistence
            "Window Tenor (months)": window_tenor,
            "Maturity Date": str(maturity_date),  # Convert to string to ensure persistence
            "Spot Rate": spot_rate,
            "Points Adjustment": points_adjustment,  # Save the points adjustment
        })

# Display and edit cashflows for the selected month
st.header(f"Cashflow Records for {selected_month}")

if len(st.session_state.monthly_cashflows[st.session_state.selected_month]) > 0:
    # Button to delete all records
    if st.button("Delete All"):
        st.session_state.monthly_cashflows[st.session_state.selected_month] = []

    # Editable table simulation with delete buttons
    for idx, cashflow in enumerate(st.session_state.monthly_cashflows[st.session_state.selected_month], start=1):
        st.write(f"Record {idx}:")
        col1, col2 = st.columns([9, 1])
        with col1:
            st.write(f"""
            - Currency: {cashflow['Currency']}
            - Amount: {cashflow['Amount']}
            - Window Open Date: {cashflow['Window Open Date']}
            - Window Tenor: {cashflow['Window Tenor (months)']} months
            - Maturity Date: {cashflow['Maturity Date']}
            - Spot Rate: {cashflow['Spot Rate']}
            - Forward Points Adjustment: {cashflow['Points Adjustment'] * 100:.2f}%
            """)
        with col2:
            if st.button("🗑", key=f"delete_{idx}"):
                st.session_state.monthly_cashflows[st.session_state.selected_month].pop(idx - 1)

# Generate a chart for all records across months
st.header("Forward Window Overview")
all_cashflows = [
    cashflow for cashflows in st.session_state.monthly_cashflows.values() for cashflow in cashflows
]
if all_cashflows:
    all_cashflows_df = pd.DataFrame(all_cashflows)
    # Ensure 'Window Open Date' and 'Maturity Date' are datetime objects
    all_cashflows_df["Window Open Date"] = pd.to_datetime(all_cashflows_df["Window Open Date"])
    all_cashflows_df["Maturity Date"] = pd.to_datetime(all_cashflows_df["Maturity Date"])

    # Calculate forward rates
    all_cashflows_df["Forward Rate (Window Open Date)"] = all_cashflows_df.apply(
        lambda row: row["Spot Rate"] + (
            (calculate_forward_rate(
                row["Spot Rate"], global_domestic_rate, global_foreign_rate,
                (row["Window Open Date"] - datetime.today()).days
            ) - row["Spot Rate"]) * row["Points Adjustment"]
        ),
        axis=1
    )
    all_cashflows_df["Forward Rate (Maturity Date)"] = all_cashflows_df.apply(
        lambda row: calculate_forward_rate(
            row["Spot Rate"], global_domestic_rate, global_foreign_rate,
            (row["Maturity Date"] - datetime.today()).days
        ),
        axis=1
    )
    all_cashflows_df["Remaining Points"] = (
        all_cashflows_df["Forward Rate (Maturity Date)"] - all_cashflows_df["Forward Rate (Window Open Date)"]
    )
    all_cashflows_df["Profit in PLN"] = (
        all_cashflows_df["Remaining Points"] * all_cashflows_df["Amount"]
    )

    # Additional Table: Remaining Points and Profit
    st.header("Remaining Points and Profit Summary")
    points_profit_summary = all_cashflows_df[[
        "Currency", "Amount", "Remaining Points", "Profit in PLN"
    ]]
    points_profit_summary["Remaining Points"] = points_profit_summary["Remaining Points"].round(4)
    points_profit_summary["Profit in PLN"] = points_profit_summary["Profit in PLN"].round(2)
    st.table(points_profit_summary)

# Footer
st.markdown("---")
st.caption("Developed using Streamlit")
