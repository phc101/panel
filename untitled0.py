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

# Global slider for adjusting points up to window open dynamically
global_points_adjustment = st.sidebar.slider(
    "Adjust Forward Points Globally (% up to Window Open Date)", 0.0, 1.0, 0.5, step=0.01
)

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
    add_6_months = st.checkbox("Add 6-Month Strip Forward")
    add_12_months = st.checkbox("Add 12-Month Strip Forward")

    # Calculate maturity date
    maturity_date = window_open_date + timedelta(days=30 * window_tenor)

    if st.button("Add Cashflow"):
        if add_6_months or add_12_months:
            num_forwards = 6 if add_6_months else 12
            for i in range(num_forwards):
                start_date = window_open_date + timedelta(days=30 * i)
                maturity_date = start_date + timedelta(days=30 * window_tenor)
                st.session_state.monthly_cashflows[start_date.month].append({
                    "Currency": currency,
                    "Amount": amount,
                    "Window Open Date": str(start_date),  # Convert to string to ensure persistence
                    "Window Tenor (months)": window_tenor,
                    "Maturity Date": str(maturity_date),  # Convert to string to ensure persistence
                    "Spot Rate": spot_rate,
                })
        else:
            st.session_state.monthly_cashflows[window_open_date.month].append({
                "Currency": currency,
                "Amount": amount,
                "Window Open Date": str(window_open_date),  # Convert to string to ensure persistence
                "Window Tenor (months)": window_tenor,
                "Maturity Date": str(maturity_date),  # Convert to string to ensure persistence
                "Spot Rate": spot_rate,
            })

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

    # Calculate forward rates dynamically based on the global adjustment
    all_cashflows_df["Forward Rate (Window Open Date)"] = all_cashflows_df.apply(
        lambda row: row["Spot Rate"] + (
            (calculate_forward_rate(
                row["Spot Rate"], global_domestic_rate, global_foreign_rate,
                (row["Window Open Date"] - datetime.today()).days
            ) - row["Spot Rate"]) * global_points_adjustment
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
    all_cashflows_df["Points to Window Open"] = (
        (all_cashflows_df["Forward Rate (Window Open Date)"] - all_cashflows_df["Spot Rate"])
    )
    all_cashflows_df["Window Open Outright"] = (
        all_cashflows_df["Forward Rate (Window Open Date)"] - all_cashflows_df["Spot Rate"]
    )
    all_cashflows_df["Window Open Price"] = (
        all_cashflows_df["Spot Rate"] + all_cashflows_df["Window Open Outright"]
    )
    all_cashflows_df["Remaining Points"] = (
        all_cashflows_df["Window Open Price"] - all_cashflows_df["Window Open Outright"]
    )
    all_cashflows_df["Points from Window"] = (
        all_cashflows_df["Forward Rate (Maturity Date)"] - all_cashflows_df["Forward Rate (Window Open Date)"]
    )
    all_cashflows_df["Window Open Profit"] = (
        all_cashflows_df["Remaining Points"] * all_cashflows_df["Amount"]
    )
    all_cashflows_df["Maturity Profit"] = (
        (all_cashflows_df["Points from Window"] + all_cashflows_df["Remaining Points"])
        * all_cashflows_df["Amount"]
    )
    all_cashflows_df["Total Points"] = (
        all_cashflows_df["Points to Window Open"] + all_cashflows_df["Points from Window"]
    )
    all_cashflows_df["Profit in PLN"] = (
        all_cashflows_df["Total Points"] * all_cashflows_df["Amount"]
    )

    # Stair-Step Chart
    fig, ax = plt.subplots(figsize=(12, 6))

    for _, row in all_cashflows_df.iterrows():
        ax.step(
            [row["Window Open Date"], row["Maturity Date"]],
            [row["Forward Rate (Window Open Date)"], row["Forward Rate (Window Open Date)"]],
            where="post",
            color="blue",
            linewidth=1.5,
            alpha=0.7
        )
        ax.axvline(
            x=row["Window Open Date"],
            color="gray",
            linestyle="--",
            alpha=0.5
        )
        ax.scatter(
            row["Window Open Date"],
            row["Forward Rate (Window Open Date)"],
            color="orange",
            s=80
        )

    ax.set_title("Forward Windows with Stair-Step Representation", fontsize=16)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Forward Rate (PLN)", fontsize=12)
    ax.grid(color="gray", linestyle="--", linewidth=0.5, alpha=0.7)
    plt.tight_layout()
    st.pyplot(fig)

    # Points and Profit Summary
    st.header("Points and Profit Summary")
    points_profit_summary = all_cashflows_df[[
        "Currency", "Window Open Date", "Maturity Date", "Amount", "Spot Rate",
        "Window Open Outright", "Window Open Price", "Remaining Points", 
        "Points from Window", "Window Open Profit", "Maturity Profit",
        "Points to Window Open", "Total Points", "Profit in PLN"
    ]]
    points_profit_summary["Window Open Outright"] = points_profit_summary["Window Open Outright"].round(4)
    points_profit_summary["Window Open Price"] = points_profit_summary["Window Open Price"].round(4)
    points_profit_summary["Remaining Points"] = points_profit_summary["Remaining Points"].round(4)
    points_profit_summary["Points from Window"] = points_profit_summary["Points from Window"].round(4)
    points_profit_summary["Window Open Profit"] = points_profit_summary["Window Open Profit"].round(2)
    points_profit_summary["Maturity Profit"] = points_profit_summary["Maturity Profit"].round(2)
    points_profit_summary["Points to Window Open"] = points_profit_summary["Points to Window Open"].round(4)
    points_profit_summary["Total Points"] = points_profit_summary["Total Points"].round(4)
    points_profit_summary["Profit in PLN"] = points_profit_summary["Profit in PLN"].round(2)
    st.table(points_profit_summary)

    # Summary Section
    total_amount = all_cashflows_df["Amount"].sum()
    total_profit = all_cashflows_df["Profit in PLN"].sum()

    st.write("### Summary")
    st.write(f"**Total Amount:** {total_amount:,.2f}")
    st.write(f"**Total Profit in PLN:** {total_profit:,.2f}")

# Footer
st.markdown("---")
st.caption("Developed using Streamlit")
