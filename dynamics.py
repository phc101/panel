import matplotlib.pyplot as plt
from scipy.stats import norm
import numpy as np
from datetime import datetime, timedelta

# Black-Scholes Pricing Function with Barrier Adjustment
def barrier_option_pricer(
    spot, strike, volatility, domestic_rate, foreign_rate, time_to_maturity, notional, option_type, barrier=None, barrier_type=None
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

    return price * notional

# Contract Conditions
start_date = datetime(2025, 2, 1)  # Contractual start date
end_date = datetime(2026, 1, 31)  # Contractual end date
guaranteed_rate = 4.2000
spot_rate = 4.2500  # Current spot rate
volatility = 0.10  # Annualized volatility (10%)
domestic_rate = 0.05  # Polish 10-year bond yield (5%)
foreign_rate = 0.025  # German 10-year bond yield (2.5%)
notional_amount = 2000000  # Total notional amount
strike_price = guaranteed_rate  # Strike price at guaranteed rate
barrier = 4.5000  # Knock-in or knock-out barrier
barrier_type = "knock-in"  # Can be "knock-in" or "knock-out"

# Generate dates for the contractual period (monthly intervals)
dates = [start_date + timedelta(days=30 * i) for i in range(12)]

# Calculate premiums with barriers
premiums = []
for i in range(len(dates)):
    time_to_maturity = (dates[i] - datetime.now()).days / 365
    premium = barrier_option_pricer(
        spot_rate, strike_price, volatility, domestic_rate, foreign_rate, time_to_maturity, notional_amount, "call", barrier, barrier_type
    )
    premiums.append(premium)

# Plot the chart
fig, ax = plt.subplots(figsize=(12, 6))

# Plot the guaranteed rate
ax.plot(dates, [guaranteed_rate] * len(dates), linestyle="--", color="blue", label=f"Guaranteed Rate: {guaranteed_rate:.4f}")

# Plot the barrier
ax.plot(dates, [barrier] * len(dates), linestyle="-", color="red", label=f"{barrier_type.capitalize()} Barrier: {barrier:.4f}")

# Plot the premium values
ax.plot(dates, [p / notional_amount for p in premiums], linestyle="--", color="green", label="Adjusted Premium (PLN per EUR)")

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

# Show the plot
plt.tight_layout()
plt.show()
