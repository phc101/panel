import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import norm

# Black-Scholes Pricing Function
def fx_option_pricer(spot, strike, volatility, domestic_rate, foreign_rate, time_to_maturity, notional, option_type="call"):
    d1 = (np.log(spot / strike) + (domestic_rate - foreign_rate + 0.5 * volatility**2) * time_to_maturity) / (volatility * np.sqrt(time_to_maturity))
    d2 = d1 - volatility * np.sqrt(time_to_maturity)

    if option_type.lower() == "call":
        price = np.exp(-foreign_rate * time_to_maturity) * spot * norm.cdf(d1) - np.exp(-domestic_rate * time_to_maturity) * strike * norm.cdf(d2)
    elif option_type.lower() == "put":
        price = np.exp(-domestic_rate * time_to_maturity) * strike * norm.cdf(-d2) - np.exp(-foreign_rate * time_to_maturity) * spot * norm.cdf(-d1)
    else:
        raise ValueError("Invalid option type. Use 'call' or 'put'.")
    
    return price * notional

def calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, tenor):
    """Calculate forward rate based on interest rate parity."""
    return spot_rate * (1 + domestic_rate * tenor) / (1 + foreign_rate * tenor)

def plot_window_forward_curve(spot_rate, domestic_rate, foreign_rate, window_open_date, months):
    today = datetime.now().date()
    start_tenor = (window_open_date - today).days / 365 if window_open_date > today else 0

    maturity_dates = [(window_open_date + timedelta(days=30 * i)).strftime("%Y-%m-%d") for i in range(months)]
    tenors = [(start_tenor + i / 12) for i in range(months)]
    forward_rates = [calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, tenor) for tenor in tenors]

    forward_points = [rate - spot_rate for rate in forward_rates]
    fig, ax = plt.subplots()

    ax.step(maturity_dates, forward_rates, where='post', label="Forward Rate", linewidth=1, color="blue")
    for i, rate in enumerate(forward_rates):
        ax.text(maturity_dates[i], rate, f"{rate:.4f}", fontsize=8, ha="center", va="bottom", color="blue")

    ax.set_xlabel("Maturity Date")
    ax.set_ylabel("Forward Rate")
    ax.set_title("Step Chart of Forward Rates")
    ax.grid(True)
    plt.xticks(rotation=45)
    plt.legend()

    data = {
        "Tenor (Months)": [i + 1 for i in range(months)],
        "Maturity Date": maturity_dates,
        "Forward Rate": forward_rates,
        "Forward Points": forward_points
    }
    df = pd.DataFrame(data)

    return fig, df

# Main App
st.title("Choose the Forward Type")

# Choice Buttons
if st.button("Dynamic Forward"):
    st.title("EUR/PLN Dynamic Forward Pricer")
    spot_rate = st.sidebar.number_input("Enter Spot Rate (EUR/PLN)", value=4.3150, step=0.0001, format="%.4f")
    volatility = st.sidebar.number_input("Enter Volatility (annualized, %)", value=10.0, step=0.1) / 100
    domestic_rate = st.sidebar.number_input("Polish 10-Year Bond Yield (Domestic Rate, %)", value=5.5, step=0.1) / 100
    foreign_rate = st.sidebar.number_input("German 10-Year Bond Yield (Foreign Rate, %)", value=2.5, step=0.1) / 100

    st.sidebar.header("Set Max and Min Prices")
    max_price = st.sidebar.number_input("Enter Max Price Strike", value=spot_rate + 0.1, step=0.0001, format="%.4f")
    min_price = st.sidebar.number_input("Enter Min Price Strike", value=spot_rate - 0.1, step=0.0001, format="%.4f")

    flat_max_price = st.sidebar.checkbox("Flat Max Price", value=False)
    flat_min_price = st.sidebar.checkbox("Flat Min Price", value=False)
    notional = st.sidebar.number_input("Notional Amount", value=100000.0, step=1000.0)

    trades = []
    for i in range(12):
        maturity_date = datetime.now() + timedelta(days=30 * (i + 1))
        trades.append({
            "type": "Max Price",
            "action": "Sell",
            "strike": max_price if flat_max_price else max_price + (i * 0.01),
            "maturity_months": i + 1,
            "maturity_date": maturity_date.strftime("%Y-%m-%d"),
            "notional": notional
        })
        trades.append({
            "type": "Min Price",
            "action": "Buy",
            "strike": min_price if flat_min_price else min_price + (i * 0.01),
            "maturity_months": i + 1,
            "maturity_date": maturity_date.strftime("%Y-%m-%d"),
            "notional": notional
        })

    max_prices = [trade["strike"] for trade in trades if trade["type"] == "Max Price"]
    min_prices = [trade["strike"] for trade in trades if trade["type"] == "Min Price"]
    max_maturities = [trade["maturity_months"] for trade in trades if trade["type"] == "Max Price"]
    min_maturities = [trade["maturity_months"] for trade in trades if trade["type"] == "Min Price"]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.step(max_maturities, max_prices, color="green", linestyle="--", label="Max Price (Call)")
    ax.step(min_maturities, min_prices, color="red", linestyle="--", label="Min Price (Put)")

    ax.set_title("Trades Visualization (Stair Step)")
    ax.set_xlabel("Time to Maturity (Months)")
    ax.set_ylabel("Strike Prices (PLN)")
    st.pyplot(fig)

elif st.button("Window Forward"):
    st.title("Window Forward Rate Calculator")
    spot_rate = st.sidebar.number_input("Spot Rate", value=4.5, step=0.01)
    poland_rate = st.sidebar.number_input("Poland Interest Rate (%)", value=5.75, step=0.1) / 100
    foreign_rate = st.sidebar.number_input("Foreign Interest Rate (%)", value=3.0, step=0.1) / 100
    window_open_date = st.sidebar.date_input("Window Open Date", value=datetime.now().date())
    months = st.sidebar.number_input("Number of Months", value=12, step=1, min_value=1)

    if st.sidebar.button("Generate Window Forward Curve"):
        fig, df = plot_window_forward_curve(spot_rate, poland_rate, foreign_rate, window_open_date, months)
        st.write("### Step Chart of Forward Rates")
        st.pyplot(fig)
        st.write("### Forward Rate Table")
        st.dataframe(df)
