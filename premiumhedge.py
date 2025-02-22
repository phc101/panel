import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Set up Streamlit page configuration
st.set_page_config(page_title="FX Portfolio Risk Manager", layout="wide")

# Title
st.title("📊 FX Portfolio Risk Management & Stress Testing Tool")

# User Inputs: Portfolio Setup
st.sidebar.header("Portfolio Setup")

total_exposure = st.sidebar.number_input("Total EUR/PLN Exposure (€)", value=100_000_000, step=1_000_000)

exporter_share = st.sidebar.slider("Exporter Share (%)", min_value=0, max_value=100, value=70) / 100
importer_share = 1 - exporter_share

exporter_avg_sell_rate = st.sidebar.number_input("Exporter Forward Rate", value=4.30, step=0.01)
importer_avg_buy_rate = st.sidebar.number_input("Importer Forward Rate", value=4.25, step=0.01)

# Hedge Allocation & Yields
st.sidebar.header("Hedging & Yield Setup")
forward_yield = st.sidebar.slider("Forward Yield (%)", min_value=0.0, max_value=10.0, value=3.3) / 100
stablecoin_yield = st.sidebar.slider("Stablecoin Yield (%)", min_value=0.0, max_value=15.0, value=8.0) / 100

# Maturity Settings
st.sidebar.header("Maturity Structure")
exporter_maturity = st.sidebar.slider("Exporter Hedge Duration (Months)", min_value=1, max_value=12, value=6)
importer_maturity = st.sidebar.slider("Importer Hedge Duration (Months)", min_value=1, max_value=12, value=2)

# Stress Test: Future EUR/PLN Settlement Rates
st.sidebar.header("Stress Test Scenario")
min_settlement_rate = st.sidebar.number_input("Min EUR/PLN Rate", value=4.00, step=0.01)
max_settlement_rate = st.sidebar.number_input("Max EUR/PLN Rate", value=4.50, step=0.01)
num_scenarios = st.sidebar.slider("Number of Test Scenarios", min_value=3, max_value=10, value=5)

# Generate stress test scenarios
settlement_rates = np.linspace(min_settlement_rate, max_settlement_rate, num_scenarios)

# Calculate hedging values
exporter_exposure = total_exposure * exporter_share
importer_exposure = total_exposure * importer_share

exporter_forward_rate = exporter_avg_sell_rate * (1 + forward_yield * (exporter_maturity / 12))
importer_forward_rate = importer_avg_buy_rate * (1 + forward_yield * (importer_maturity / 12))

# Hedge amount in stablecoins
usdc_hedge_pln = (exporter_exposure * exporter_forward_rate) - (importer_exposure * importer_forward_rate)

# Stablecoin staking yield over 1 year
usdc_yield_earned = usdc_hedge_pln * stablecoin_yield

# Stress Test Calculations
stress_test_results = []
hedge_recommendations = []
for rate in settlement_rates:
    exporter_loss = (rate - exporter_forward_rate) * exporter_exposure
    importer_gain = (rate - importer_forward_rate) * importer_exposure
    net_profit = exporter_loss + importer_gain + usdc_yield_earned

    # Generate Hedge Recommendations
    if rate > exporter_forward_rate:
        recommendation = "⚠ Increase importer hedges, reduce exporter exposure"
    elif rate < importer_forward_rate:
        recommendation = "✅ Increase exporter hedges, reduce importer exposure"
    else:
        recommendation = "📊 Maintain current hedge ratios"

    stress_test_results.append([rate, exporter_loss, importer_gain, net_profit, recommendation])
    hedge_recommendations.append(recommendation)

# Convert to DataFrame
stress_test_df = pd.DataFrame(stress_test_results, columns=[
    "Settlement Rate (EUR/PLN)",
    "Exporter Loss (PLN)",
    "Importer Gain (PLN)",
    "Net Profit (PLN)",
    "Hedge Recommendation"
])

# Display Stress Test Results
st.header("📉 Portfolio Stress Test Results")
st.dataframe(stress_test_df)

# Visualization
st.subheader("📊 Impact of EUR/PLN Movements on Portfolio")
fig, ax = plt.subplots(figsize=(8, 5))

ax.plot(stress_test_df["Settlement Rate (EUR/PLN)"], stress_test_df["Exporter Loss (PLN)"], marker='o', linestyle='-', label="Exporter Loss", color="red")
ax.plot(stress_test_df["Settlement Rate (EUR/PLN)"], stress_test_df["Importer Gain (PLN)"], marker='s', linestyle='--', label="Importer Gain", color="green")
ax.plot(stress_test_df["Settlement Rate (EUR/PLN)"], stress_test_df["Net Profit (PLN)"], marker='^', linestyle='-', label="Net Profit (PLN)", color="blue")

ax.axhline(0, color="black", linestyle="--")  # Reference line at 0
ax.set_xlabel("Settlement Rate (EUR/PLN)")
ax.set_ylabel("PLN Amount")
ax.set_title("FX Portfolio Risk Impact: Exporters vs Importers & USDC Hedge")
ax.legend()
ax.grid(True)

st.pyplot(fig)

# Hedge Recommendation Section
st.subheader("📢 Automated Hedge Recommendations")
for rate, recommendation in zip(settlement_rates, hedge_recommendations):
    st.write(f"- If EUR/PLN reaches **{rate:.2f}**, recommended action: **{recommendation}**")
