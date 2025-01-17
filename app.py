import streamlit as st
import pandas as pd
import numpy as np

# Page Title
st.title("Startup Funding and Valuation Model")

# Input Section
st.header("Input Your Revenue and Costs")

# Revenue and Cost Inputs
data = {
    "Year": [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032],
    "Net Revenue (zł)": [-850800, -585325, 685475, 2537975, 4390475, 6242975, 8095475, 9947975],
    "Costs (zł)": [-850800, -1357200, -1568400, 0, 0, 0, 0, 0],
}

# Create DataFrame
financial_data = pd.DataFrame(data)
financial_data["Net Profit (zł)"] = financial_data["Net Revenue (zł)"] - financial_data["Costs (zł)"]

# Display Financial Data
st.subheader("Projected Financial Data")
st.write(financial_data)

# Assumptions
st.header("Key Assumptions")
profit_margin = st.slider("Expected Profit Margin (Year 8, %):", 10, 50, 20) / 100
pe_multiple = st.slider("Price-to-Earnings (P/E) Multiple:", 5, 25, 15)
discount_rate = st.slider("Discount Rate (%):", 10, 50, 30) / 100

year_8_revenue = financial_data[financial_data["Year"] == 2032]["Net Revenue (zł)"].values[0]

# Calculate Year 8 Valuation
year_8_profit = year_8_revenue * profit_margin
year_8_valuation = year_8_profit * pe_multiple

# Discount to Present Value
discount_factor = (1 + discount_rate) ** 8
present_value = year_8_valuation / discount_factor

# Funding Requirements and Equity
st.header("Funding Requirements")
total_costs = financial_data[financial_data["Year"] <= 2027]["Costs (zł)"].sum()
equity_offered = st.slider("Equity Offered (%):", 10, 50, 25) / 100
capital_raised = total_costs / equity_offered
post_money_valuation = capital_raised / equity_offered
pre_money_valuation = post_money_valuation - capital_raised

# Display Calculations
st.subheader("Results")
st.write(f"### Total Costs (First 3 Years): {total_costs:,.2f} zł")
st.write(f"### Year 8 Valuation: {year_8_valuation:,.2f} zł")
st.write(f"### Discounted Present Value: {present_value:,.2f} zł")
st.write(f"### Capital Raised: {capital_raised:,.2f} zł")
st.write(f"### Post-Money Valuation: {post_money_valuation:,.2f} zł")
st.write(f"### Pre-Money Valuation: {pre_money_valuation:,.2f} zł")

# Equity Ownership
founder_equity = 1 - equity_offered
st.subheader("Ownership Breakdown")
st.write(f"- Founders: {founder_equity * 100:.2f}%")
st.write(f"- Investors: {equity_offered * 100:.2f}%")

# ROI for Investors
investor_roi = year_8_valuation * equity_offered / capital_raised
st.subheader("Investor ROI")
st.write(f"### ROI Multiple: {investor_roi:.2f}x")

# Visualizations
st.header("Visualization")

# Revenue and Profit Chart
st.line_chart(financial_data.set_index("Year")["Net Revenue (zł)"], use_container_width=True)
st.line_chart(financial_data.set_index("Year")["Net Profit (zł)"], use_container_width=True)

# Capital Breakdown Pie Chart
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.pie([founder_equity, equity_offered], labels=["Founders", "Investors"], autopct="%1.1f%%", startangle=90)
ax.axis("equal")
st.pyplot(fig)

st.write("### Use this model to simulate various scenarios by adjusting inputs!")
