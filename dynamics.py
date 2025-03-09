import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------- Streamlit UI Setup ----------
st.set_page_config(page_title="EUR/PLN Risk Model", layout="wide")
st.title("📊 EUR/PLN Risk Management Model")

# ---------- Sidebar Inputs ----------
st.sidebar.header("⚙️ Market Inputs")
spot_rate = st.sidebar.number_input("Spot Rate (EUR/PLN)", value=4.30, format="%.4f")
predicted_move_pct = st.sidebar.number_input("Expected Move in 30 Days (%)", value=1.35, format="%.2f")
predicted_spot = spot_rate * (1 + predicted_move_pct / 100)

st.sidebar.header("🏢 Exporter Exposure")
exposure_eur = st.sidebar.number_input("Exposure Amount (€)", value=100_000_000, format="%d")

st.sidebar.header("💰 Risk Capital Requirements")
client_deposit_pct = st.sidebar.slider("Client Deposit (%)", 0.5, 5.0, 1.0, step=0.1)
broker_margin_pct = st.sidebar.slider("Broker Margin (%)", 1.0, 10.0, 5.0, step=0.5)

st.sidebar.header("⚠️ Extreme Scenario Simulation")
extreme_move = st.sidebar.slider("Extreme EUR/PLN Move (%)", 2.0, 20.0, 10.0, step=0.5)
extreme_spot = spot_rate * (1 + extreme_move / 100)

# ---------- Functions for Calculations ----------
def calculate_capital_requirements(spot_rate, exposure_eur, client_deposit_pct, broker_margin_pct, extreme_spot):
    """Calculates client deposit, broker margin, and tail risk loss."""
    client_deposit = (exposure_eur * spot_rate * client_deposit_pct) / 100
    broker_margin = (exposure_eur * spot_rate * broker_margin_pct) / 100
    tail_risk_loss = max(exposure_eur * (extreme_spot - spot_rate), 0)
    additional_capital_needed = max(tail_risk_loss - client_deposit, 0)
    
    return client_deposit, broker_margin, tail_risk_loss, additional_capital_needed

client_deposit, broker_margin, tail_risk_loss, additional_capital_needed = calculate_capital_requirements(
    spot_rate, exposure_eur, client_deposit_pct, broker_margin_pct, extreme_spot
)

# ---------- Data Simulation for Visualization ----------
spot_prices = np.linspace(spot_rate * 0.9, extreme_spot * 1.1, 100)
losses = np.maximum(exposure_eur * (spot_prices - spot_rate), 0)

# ---------- Layout Setup ----------
col1, col2 = st.columns(2)

# ---------- Display Capital Requirements ----------
with col1:
    st.subheader("💡 Capital Requirements Summary")
    st.write(f"**📉 Predicted Spot in 30 Days:** {predicted_spot:.4f}")
    st.write(f"**⚠️ Extreme Move Spot (EUR/PLN {extreme_move}% increase):** {extreme_spot:.4f}")
    st.write(f"**💰 Client Deposit Collected:** {client_deposit:,.0f} PLN")
    st.write(f"**🏦 Broker Margin Required:** {broker_margin:,.0f} PLN")
    st.write(f"**📉 Tail Risk Loss Estimate:** {tail_risk_loss:,.0f} PLN")
    st.write(f"**⚠️ Additional Capital Needed:** {additional_capital_needed:,.0f} PLN")

# ---------- Risk Simulation Plot ----------
with col2:
    st.subheader("📈 Risk Simulation Chart")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(spot_prices, losses, label="Tail Risk Loss", color='red')
    ax.axhline(client_deposit, color='blue', linestyle='dashed', label="Client Deposit")
    ax.axhline(broker_margin, color='green', linestyle='dotted', label="Broker Margin")
    ax.axhline(additional_capital_needed, color='purple', linestyle='dashed', label="Additional Capital Needed")
    ax.legend()
    ax.set_xlabel("EUR/PLN Spot Price")
    ax.set_ylabel("Potential Loss (PLN)")
    st.pyplot(fig)

# ---------- Risk Notes ----------
st.subheader("📝 Risk Notes")
st.write("- If EUR/PLN rises significantly, you may need additional capital beyond the client deposit.")
st.write("- Adjusting client deposit % and broker margin % affects capital requirements.")
st.write("- Extreme market movements require a strong capital buffer to avoid liquidation.")
