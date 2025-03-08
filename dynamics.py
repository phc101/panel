import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Title
st.title("EUR/PLN Risk Management Model")

# Sidebar Inputs
st.sidebar.header("Market Inputs")
spot_rate = st.sidebar.number_input("Current Spot Rate (EUR/PLN)", value=4.30, format="%.4f")
predicted_move_pct = st.sidebar.number_input("Expected % Move in 30 Days", value=1.35, format="%.2f")
predicted_spot = spot_rate * (1 + predicted_move_pct / 100)

# Option Parameters
st.sidebar.header("Option Chain")
strike = st.sidebar.number_input("Option Strike Price", value=4.35, format="%.4f")
put_premium = st.sidebar.number_input("Put Option Premium", value=0.02, format="%.4f")
call_premium = st.sidebar.number_input("Call Option Premium", value=0.02, format="%.4f")

# Forward Rate Adjustment
st.sidebar.header("Forward Hedging")
forward_adjustment = st.sidebar.slider("Discount to Client (PLN)", min_value=0.0000, max_value=0.0100, value=0.0020, step=0.0001)
effective_forward_rate = strike - forward_adjustment

# Position Size
st.sidebar.header("Leverage & Margin")
notional_amount = st.sidebar.number_input("Notional Hedge Size (EUR)", value=100000)
margin_ratio = st.sidebar.slider("Margin Required (%)", min_value=1.0, max_value=10.0, value=1.0, step=0.1)
margin_required = (notional_amount * spot_rate * margin_ratio) / 100

# Risk Management
st.sidebar.header("Risk Controls")
stop_loss_level = st.sidebar.number_input("Stop Loss Level (EUR/PLN)", value=4.20, format="%.4f")
take_profit_level = st.sidebar.number_input("Take Profit Level (EUR/PLN)", value=4.45, format="%.4f")

# P&L Simulation
def calculate_pnl(spot_prices, strike, put_premium, call_premium, effective_forward_rate):
    pnl = []
    for spot in spot_prices:
        put_value = max(strike - spot, 0) - put_premium
        call_value = max(spot - strike, 0) - call_premium
        pnl.append((put_value + call_value) * notional_amount)
    return pnl

spot_prices = np.linspace(spot_rate * 0.95, spot_rate * 1.05, 100)
pnl = calculate_pnl(spot_prices, strike, put_premium, call_premium, effective_forward_rate)

# Plot P&L
fig, ax = plt.subplots()
ax.plot(spot_prices, pnl, label="P&L vs. Spot Price", color='blue')
ax.axhline(0, color='black', linestyle='dashed')
ax.axvline(spot_rate, color='gray', linestyle='dotted', label="Current Spot")
ax.axvline(effective_forward_rate, color='green', linestyle='dotted', label="Offered Forward Rate")
ax.axvline(stop_loss_level, color='red', linestyle='dashed', label="Stop Loss")
ax.axvline(take_profit_level, color='green', linestyle='dashed', label="Take Profit")
ax.legend()
ax.set_xlabel("EUR/PLN Spot Price")
ax.set_ylabel("Profit/Loss (PLN)")
st.pyplot(fig)

# Display Key Metrics
st.write("### Summary")
st.write(f"- **Predicted Spot in 30 Days:** {predicted_spot:.4f}")
st.write(f"- **Effective Forward Rate to Client:** {effective_forward_rate:.4f}")
st.write(f"- **Initial Premium Collected (PLN):** {(put_premium + call_premium) * notional_amount:.2f}")
st.write(f"- **Margin Required:** {margin_required:.2f} PLN")

st.write("### Risk Notes:")
st.write("- If EUR/PLN falls below the stop loss, risk increases significantly.")
st.write("- The margin requirement ensures you have capital buffer against market moves.")
st.write("- Offering a discount to clients impacts profitability but increases competitiveness.")
