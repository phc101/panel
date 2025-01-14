import streamlit as st
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

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

# Streamlit App
st.title("FX Forward Rate Calculator with Margins")

st.markdown("""
This app allows you to calculate forward rates with automatic margins for multiple future cashflows in EUR or USD and see their equivalent values in PLN. You can also view the profit from margins.
""")

# Placeholder for cashflows
if "cashflows" not in st.session_state:
    st.session_state.cashflows = []

# Sidebar for managing cashflows
with st.sidebar:
    st.header("Add New Cashflow")
    currency = st.selectbox("Currency", ["EUR", "USD"], key="currency")
    amount = st.number_input("Cashflow Amount", min_value=0.0, value=1000.0, step=100.0, key="amount")
    future_date = st.date_input("Future Date", min_value=datetime.today(), key="future_date")
    domestic_rate = st.slider("Domestic Interest Rate (%)", 0.0, 10.0, 5.0, step=0.25, key="domestic_rate") / 100
    foreign_rate = st.slider("Foreign Interest Rate (%)", 0.0, 10.0, 3.0, step=0.25, key="foreign_rate") / 100
    spot_rate = st.number_input("Spot Rate", min_value=0.0, value=4.5, step=0.01, key="spot_rate")

    if st.button("Add Cashflow"):
        st.session_state.cashflows.append({
            "Currency": currency,
            "Amount": amount,
            "Future Date": future_date,
            "Domestic Rate (%)": domestic_rate * 100,
            "Foreign Rate (%)": foreign_rate * 100,
            "Spot Rate": spot_rate,
        })

# Main panel for displaying and editing cashflows
st.header("Cashflow Records")
if len(st.session_state.cashflows) > 0:
    # Editable table simulation
    edited_cashflows = []
    for i, cashflow in enumerate(st.session_state.cashflows):
        with st.expander(f"Edit Record {i + 1}"):
            currency = st.selectbox(f"Currency for Record {i + 1}", ["EUR", "USD"], index=["EUR", "USD"].index(cashflow["Currency"]), key=f"currency_{i}")
            amount = st.number_input(f"Amount for Record {i + 1}", value=cashflow["Amount"], step=100.0, key=f"amount_{i}")
            future_date = st.date_input(f"Future Date for Record {i + 1}", value=cashflow["Future Date"], key=f"future_date_{i}")
            domestic_rate = st.slider(f"Domestic Interest Rate (%) for Record {i + 1}", 0.0, 10.0, value=cashflow["Domestic Rate (%)"], step=0.25, key=f"domestic_rate_{i}") / 100
            foreign_rate = st.slider(f"Foreign Interest Rate (%) for Record {i + 1}", 0.0, 10.0, value=cashflow["Foreign Rate (%)"], step=0.25, key=f"foreign_rate_{i}") / 100
            spot_rate = st.number_input(f"Spot Rate for Record {i + 1}", value=cashflow["Spot Rate"], step=0.01, key=f"spot_rate_{i}")
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

    # Calculate forward rate, PLN value, and profit for each record
    results = []
    total_profit = 0
    monthly_profits = {}
    for cashflow in st.session_state.cashflows:
        days = (cashflow["Future Date"] - datetime.today().date()).days
        forward_rate = calculate_forward_rate(
            cashflow["Spot Rate"], cashflow["Domestic Rate (%)"] / 100, cashflow["Foreign Rate (%)"] / 100, days
        )
        margin = calculate_margin(days)
        forward_rate_with_margin = forward_rate * (1 + margin)
        pln_value = forward_rate_with_margin * cashflow["Amount"]
        profit = (forward_rate_with_margin - forward_rate) * cashflow["Amount"]
        total_profit += profit

        # Track monthly profit
        months = days // 30
        if months not in monthly_profits:
            monthly_profits[months] = 0
        monthly_profits[months] += profit

        results.append({
            "Forward Rate": round(forward_rate, 4),
            "Forward Rate (with Margin)": round(forward_rate_with_margin, 4),
            "PLN Value": round(pln_value, 2),
            "Profit from Margin": round(profit, 2),
        })

    # Add results to DataFrame and display
    df = pd.DataFrame(st.session_state.cashflows)
    results_df = pd.DataFrame(results)
    final_df = pd.concat([df, results_df], axis=1)
    st.table(final_df)

    # Display total profit
    st.header("Total Profit")
    st.success(f"Total Profit from Margins: PLN {round(total_profit, 2)}")

    # Plot monthly profit distribution
    st.header("Monthly Profit Distribution")
    if monthly_profits:
        months = list(monthly_profits.keys())
        profits = list(monthly_profits.values())
        plt.bar(months, profits)
        plt.xlabel("Months from Today")
        plt.ylabel("Profit (PLN)")
        plt.title("Profit from Margins by Month")
        st.pyplot(plt)
else:
    st.info("No cashflow records added yet. Use the sidebar to add records.")

# Footer
st.markdown("---")
st.caption("Developed using Streamlit")
