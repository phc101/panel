import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Title
st.title("EUR/PLN Tail Risk Capital Simulation")

# Sidebar Inputs
st.sidebar.header("Market Inputs")
spot_rate = st.sidebar.number_input("Current Spot Rate (EUR/PLN)", value=4.30, format="%.4f")
predicted_move_pct = st.sidebar.number_input("Expected % Move in 30 Days", value=1.35, format="%.2f")
predicted_spot = spot_rate * (1 + predicted_move_pct / 100)

# Exporter Exposure
st.sidebar.header("Exporter Exposure")
exposure_eur = st.sidebar.number_input("Exporter Exposure (EUR)", value=100000000, format="%d")

# Risk Capital Inputs
st.sidebar.header("Tail Risk Capital Requirements")
client_deposit_pct = st.sidebar.slider("Client Deposit (%)", min_value=0.5, max_value=5.0, value=1.0, step=0.1)
broker_margin_pct = st.sidebar.slider("Broker Margin Requirement (%)", min_value=1.0, max_value=10.0, value=5.0, step=0.5)

# Extreme Scenario Simulation
extreme_move = st.sidebar.slider("Extreme EUR/PLN Move (%)", min_value=2.0, max_value=20.0, value=10.0, step=0.5)
extreme_spot = spot_rate * (1 + extreme_move / 100)

# Calculating Capital Needs
client_deposit = (exposure_eur * spot_rate * client_deposit_pct) / 100
broker_margin = (exposure_eur * spot_rate * broker_margin_pct) / 100
tail_risk_loss = exposure_eur * (extreme_spot - spot_rate)
additional_capital_needed = max(tail_risk_loss - client_deposit, 0)

# Simulation Plot
spot_prices = np.linspace(spot_rate, extreme_spot, 100)
losses = [exposure_eur * (s - spot_rate) for s in spot_prices]
fig, ax = plt.subplots()
ax.plot(spot_prices, losses, label="Tail Risk Loss", color='red')
ax.axhline(client_deposit, color='blue', linestyle='dashed', label="Client Deposit")
ax.axhline(broker_margin, color='green', linestyle='dotted', label="Broker Margin Requirement")
ax.axhline(additional_capital_needed, color='purple', linestyle='dashed', label="Additional Capital Needed")
ax.legend()
ax.set_xlabel("EUR/PLN Spot Price")
ax.set_ylabel("Potential Loss (PLN)")
st.pyplot(fig)

# Display Results
st.write("### Summary of Capital Requirements")
st.write(f"- **Predicted Spot in 30 Days:** {predicted_spot:.4f}")
st.write(f"- **Extreme Move Spot (EUR/PLN {extreme_move}% increase):** {extreme_spot:.4f}")
st.write(f"- **Client Deposit Collected:** {client_deposit:,.0f} PLN")
st.write(f"- **Broker Margin Required:** {broker_margin:,.0f} PLN")
st.write(f"- **Tail Risk Loss Estimate:** {tail_risk_loss:,.0f} PLN")
st.write(f"- **Additional Capital Needed:** {additional_capital_needed:,.0f} PLN")

st.write("### Risk Notes:")
st.write("- If EUR/PLN rises significantly, you may need additional capital beyond the client deposit.")
st.write("- Adjusting client deposit % and broker margin % changes capital requirements.")
st.write("- Extreme market moves (tail risks) require a strong capital buffer to avoid liquidation.")
