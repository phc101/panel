import streamlit as st
import matplotlib.pyplot as plt
from scipy.stats import norm
import numpy as np
from datetime import datetime, timedelta

# Black-Scholes Pricing Function with Barrier Adjustment
def barrier_option_pricer(
    spot, strike, volatility, domestic_rate, foreign_rate, time_to_maturity, option_type, barrier=None, barrier_type=None
):
    d1 = (np.log(spot / strike) + (domestic_rate - foreign_rate + 0.5 * volatility**2) * time_to_maturity) / (volatility * np.sqrt(time_to_maturity))
    d2 = d1 - volatility * np.sqrt(time_to_maturity)

    # Calculate standard option price
    if option_type.lower() == "call":
        price = np.exp(-foreign_rate * time_to_maturity) * spot * norm.cdf(d1) - np.exp(-domestic_rate * time_to_maturity) * strike * norm.cdf(d2)
    elif option_type.lower() == "put":
        price = np.exp(-domestic_rate * time_to_maturity) * strike * norm.cdf(-d2) - np.exp(-foreign_rate * time_to_maturity) * spot * norm.cdf(-d1)
    else:
        raise ValueError("Invalid option type. Use 'call' or 'put'.")

    # Adjust price for barriers
    if barrier is not None and barrier_type is not None:
        if barrier_type == "knock-in":
            if option_type.lower() == "call" and spot < barrier:
                price *= 0.8  # Adjust premium for knock-in condition (20% lower as an example)
            elif option_type.lower() == "put" and spot > barrier:
                price *= 0.8
        elif barrier_type == "knock-out":
            if option_type.lower() == "call" and spot >= barrier:
                price = 0  # Knock-out condition met
            elif option_type.lower() == "put" and spot <= barrier:
                price = 0

    return price

# Explanation of the trade
st.title("Barrier Option Pricing with Adjusted Premiums")
st.write("""
### Trade Explanation:
This is a **Barrier Option Trade** with the following terms:
1. **Yearly Notional Amount:** The total EUR volume for the year (e.g., 2,000,000 EUR) is divided equally across 12 monthly trades.
2. **Guaranteed Rate:** You will sell EUR at a guaranteed rate of 4.2000 PLN as long as the barrier condition is not triggered.
3. **Barrier Type:**
   - **Knock-In:** The option only becomes active if the barrier is breached (e.g., EUR/PLN goes below or above a specific level).
   - **Knock-Out:** The option ceases to exist if the barrier is breached.
4. **Premium Adjustment:**
   - The premium is adjusted dynamically based on whether the barrier condition is satisfied.
   - If the barrier condition is breached for a knock-in, the premium will reduce by 20%.
   - For a knock-out, the option is deactivated, and no premium is paid.
5. **Trade Parameters:** Each monthly trade matures at the end of the month, and premiums are calculated accordingly.

This tool allows you to visualize the trade conditions and calculate the net premium dynamically.
""")

# Streamlit Inputs
spot_rate = st.number_input("Enter Spot Rate (EUR/PLN)", value=4.2500, step=0.0001, format="%.4f")
strike_price = st.number_input("Enter Strike Price (Guaranteed Rate)", value=4.2000, step=0.0001, format="%.4f")
volatility = st.number_input("Enter Volatility (annualized, %)", value=10.0, step=0.1) / 100
domestic_rate = st.number_input("Enter Domestic Rate (10-Year Polish Bond, %)", value=5.0, step=0.1) / 100
foreign_rate = st.number_input("Enter Foreign Rate (10-Year German Bond, %)", value=2.5, step=0.1) / 100
yearly_notional = st.number_input("Enter Total Yearly Notional Amount (EUR)", value=2000000.0, step=1000.0)
barrier = st.number_input("Enter Barrier Level", value=4.5000, step=0.0001, format="%.4f")
barrier_type = st.selectbox("Select Barrier Type", ["knock-in", "knock-out"])

# Generate dates for the contractual period (monthly intervals)
start_date = datetime(2025, 2, 1)  # Contractual start date
dates = [start_date + timedelta(days=30 * i) for i in range(12)]
monthly_notional = yearly_notional / len(dates)  # Monthly notional amount

# Calculate premiums with barriers
premiums = []
for i in range(len(dates)):
    time_to_maturity = (dates[i] - datetime.now()).days / 365
    if time_to_maturity > 0:  # Ensure time to maturity is positive
        premium_per_eur = barrier_option_pricer(
            spot_rate, strike_price, volatility, domestic_rate, foreign_rate, time_to_maturity, "call", barrier, barrier_type
        )
        monthly_premium = premium_per_eur * monthly_notional
        premiums.append(monthly_premium)
    else:
        premiums.append(0)  # If time to maturity is zero or negative, no premium

# Calculate the net premium
net_premium = sum(premiums)

# Display the net premium
st.write("### Net Premium")
if net_premium > 0:
    st.write(f"**Net Premium Received:** {net_premium:.2f} PLN")
else:
    st.write(f"**Net Premium Paid:** {abs(net_premium):.2f} PLN")

# Plot the chart
fig, ax = plt.subplots(figsize=(12, 6))

# Plot the guaranteed rate
ax.plot(dates, [strike_price] * len(dates), linestyle="--", color="blue", label=f"Guaranteed Rate: {strike_price:.4f}")

# Plot the barrier
ax.plot(dates, [barrier] * len(dates), linestyle="-", color="red", label=f"{barrier_type.capitalize()} Barrier: {barrier:.4f}")

# Plot the premium values
ax.plot(dates, [p / monthly_notional for p in premiums], linestyle="--", color="green", label="Adjusted Premium (PLN per EUR)")

# Add labels and title
ax.set_title("Barrier Option Pricing with Adjusted Premiums", fontsize=14)
ax.set_xlabel("Date", fontsize=12)
ax.set_ylabel("Exchange Rate / Premium (PLN)", fontsize=12)
ax.set_ylim(4.0, 4.6)
ax.grid(alpha=0.3)

# Format x-axis for dates
plt.xticks(dates, [date.strftime("%b %Y") for date in dates], rotation=45)

# Add legend
ax.legend()

# Display the chart in Streamlit
st.pyplot(fig)
