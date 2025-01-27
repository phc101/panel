import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Function to determine the rate based on barrier conditions
def calculate_rate(spot, upper_barrier, lower_barrier, guaranteed_rate, breached_rate):
    if spot >= upper_barrier or spot <= lower_barrier:
        return breached_rate  # Barrier breached
    return guaranteed_rate  # No barrier breach

# Explanation of the trade
st.title("Barrier Option Pricing with Net Position")
st.write("""
### Trade Explanation:
1. **Guaranteed Rate:** The client can sell EUR/PLN at a rate of 4.30 as long as no barriers are breached at expiry.
2. **Barriers:**
   - **Upper Barrier:** 4.50
   - **Lower Barrier:** 3.95
3. **Breached Rate:** If any barrier is breached, the selling rate is reduced to 4.15.
4. **Spot Rate at Expiry:** Determines whether the barriers are breached.
5. **Net Position:** Shows the overall outcome of the trade, including proceeds from the final rate compared to the market value at the spot rate.
""")

# Streamlit Inputs
spot_rate = st.number_input("Enter Spot Rate at Expiry (EUR/PLN)", value=4.2100, step=0.0001, format="%.4f")
upper_barrier = st.number_input("Enter Upper Barrier", value=4.5000, step=0.0001, format="%.4f")
lower_barrier = st.number_input("Enter Lower Barrier", value=3.9500, step=0.0001, format="%.4f")
guaranteed_rate = st.number_input("Enter Guaranteed Rate", value=4.3000, step=0.0001, format="%.4f")
breached_rate = st.number_input("Enter Breached Rate", value=4.1500, step=0.0001, format="%.4f")
yearly_notional = st.number_input("Enter Total Yearly Notional Amount (EUR)", value=2000000.0, step=1000.0)

# Calculate the rate based on barriers
final_rate = calculate_rate(spot_rate, upper_barrier, lower_barrier, guaranteed_rate, breached_rate)

# Calculate proceeds from the trade
proceeds = final_rate * yearly_notional

# Calculate market value at spot
market_value = spot_rate * yearly_notional

# Calculate net position
net_position = proceeds - market_value

# Generate dates for the contractual period (monthly intervals)
start_date = datetime(2025, 2, 1)  # Contractual start date
dates = [start_date + timedelta(days=30 * i) for i in range(12)]

# Chart Data
rate_values = [guaranteed_rate if spot_rate < upper_barrier and spot_rate > lower_barrier else breached_rate] * len(dates)
upper_barrier_values = [upper_barrier] * len(dates)
lower_barrier_values = [lower_barrier] * len(dates)
breached_rate_values = [breached_rate] * len(dates)

# Plot the chart
fig, ax = plt.subplots(figsize=(12, 6))

# Plot the guaranteed rate or breached rate
if spot_rate >= upper_barrier or spot_rate <= lower_barrier:
    ax.step(dates, breached_rate_values, linestyle="--", color="purple", label=f"Breached Rate: {breached_rate:.4f}")
else:
    ax.step(dates, [guaranteed_rate] * len(dates), linestyle="--", color="blue", label=f"Guaranteed Rate: {guaranteed_rate:.4f}")

# Plot the barriers
ax.plot(dates, upper_barrier_values, linestyle="-", color="red", label=f"Upper Barrier: {upper_barrier:.4f}")
ax.plot(dates, lower_barrier_values, linestyle="-", color="green", label=f"Lower Barrier: {lower_barrier:.4f}")

# Annotate the breached rate on the chart
if spot_rate >= upper_barrier or spot_rate <= lower_barrier:
    ax.annotate(f"Breached Rate: {breached_rate:.4f}", xy=(len(dates) - 1, breached_rate), xytext=(len(dates), breached_rate),
                color="purple", fontsize=10, ha="left", va="center", arrowprops=dict(facecolor="purple", arrowstyle="->"))

# Add labels and title
ax.set_title("Barrier Option Pricing with Net Position", fontsize=14)
ax.set_xlabel("Date", fontsize=12)
ax.set_ylabel("Exchange Rate (EUR/PLN)", fontsize=12)
ax.grid(alpha=0.3)

# Format x-axis for dates
plt.xticks(dates, [date.strftime("%b %Y") for date in dates], rotation=45)

# Add legend
ax.legend()

# Display the chart in Streamlit
st.pyplot(fig)

# Display the final rate, proceeds, market value, and net position
st.write("### Results")
st.write(f"**Final Selling Rate:** {final_rate:.4f} EUR/PLN")
st.write(f"**Proceeds from Trade:** {proceeds:,.2f} PLN")
st.write(f"**Market Value at Spot:** {market_value:,.2f} PLN")
if net_position > 0:
    st.write(f"**Net Position (Profit):** {net_position:,.2f} PLN")
else:
    st.write(f"**Net Position (Loss):** {abs(net_position):,.2f} PLN")
