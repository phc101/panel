import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

def garman_kohlhagen(S, K, T, rd, rf, sigma, option_type):
    d1 = (np.log(S / K) + (rd - rf + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "call":
        price = np.exp(-rf * T) * S * norm.cdf(d1) - np.exp(-rd * T) * K * norm.cdf(d2)
    elif option_type == "put":
        price = np.exp(-rd * T) * K * norm.cdf(-d2) - np.exp(-rf * T) * S * norm.cdf(-d1)
    else:
        raise ValueError("Invalid option type. Use 'call' or 'put'.")
    return price

def monte_carlo_double_barrier(S, K, T, rd, rf, sigma, upper_barrier, lower_barrier, adjusted_strike, option_type, paths):
    dt = T / 252  # Daily steps
    prices = np.zeros(paths)

    for i in range(paths):
        path = [S]
        breached = False
        for _ in range(int(T / dt)):
            dS = path[-1] * (rd - rf) * dt + sigma * path[-1] * np.sqrt(dt) * np.random.normal()
            path.append(path[-1] + dS)

            if path[-1] >= upper_barrier or path[-1] <= lower_barrier:
                breached = True

        final_strike = adjusted_strike if breached else K
        payoff = max(0, path[-1] - final_strike) if option_type == "call" else max(0, final_strike - path[-1])
        prices[i] = payoff

    return np.exp(-rd * T) * np.mean(prices)

def calculate_net_premium(S, transactions, rd, rf, T, sigma):
    total_premium = 0
    for transaction in transactions:
        type_, K, option_type, position = transaction
        price = garman_kohlhagen(S, K, T, rd, rf, sigma, option_type)
        total_premium += price if position == "buy" else -price
    return total_premium * S  # Convert to PLN

def main():
    st.title("EUR/PLN Double Barrier Option Pricer")

    st.sidebar.header("Option Parameters")
    spot_price = st.sidebar.number_input("Spot Price (EUR/PLN)", value=4.21, step=0.01)
    strike_price = st.sidebar.number_input("Strike Price", value=4.30, step=0.01)
    domestic_rate = st.sidebar.number_input("Domestic Risk-Free Rate (%)", value=6.0, step=0.1) / 100
    foreign_rate = st.sidebar.number_input("Foreign Risk-Free Rate (%)", value=2.5, step=0.1) / 100
    volatility = st.sidebar.number_input("Volatility (%)", value=15.0, step=0.1) / 100
    maturity = st.sidebar.number_input("Time to Maturity (Years)", value=0.5, step=0.1)

    st.sidebar.header("Barrier Settings")
    upper_barrier = st.sidebar.number_input("Upper Barrier", value=4.50, step=0.01)
    lower_barrier = st.sidebar.number_input("Lower Barrier", value=3.95, step=0.01)
    adjusted_strike = st.sidebar.number_input("Adjusted Strike (if barrier breached)", value=4.15, step=0.01)

    st.sidebar.header("Transactions")
    transaction_count = st.sidebar.radio("Number of Transactions", [6, 12])
    transactions = []
    for i in range(transaction_count):
        st.sidebar.subheader(f"Transaction {i + 1}")
        option_type = st.sidebar.selectbox(f"Option Type (Transaction {i + 1})", ["call", "put"], key=f"type_{i}")
        position = st.sidebar.selectbox(f"Position (Transaction {i + 1})", ["buy", "sell"], key=f"position_{i}")
        strike = st.sidebar.number_input(f"Strike Price (Transaction {i + 1})", value=4.30 + i * 0.01, step=0.01, key=f"strike_{i}")
        transactions.append((f"Transaction {i + 1}", strike, option_type, position))

    st.sidebar.header("Monte Carlo Settings")
    paths = st.sidebar.number_input("Simulation Paths", value=10000, step=1000)

    if st.button("Calculate"):
        monte_carlo_price = monte_carlo_double_barrier(spot_price, strike_price, maturity, domestic_rate, foreign_rate, volatility, upper_barrier, lower_barrier, adjusted_strike, "call", paths)
        net_premium = calculate_net_premium(spot_price, transactions, domestic_rate, foreign_rate, maturity, volatility)

        st.write(f"### Monte Carlo Double Barrier Price: {monte_carlo_price:.4f} EUR")
        st.write(f"### Net Premium: {net_premium:.2f} PLN")

        st.write("#### Transaction Details")
        for transaction in transactions:
            st.write(f"- {transaction[0]}: {transaction[3]} {transaction[2]} at strike {transaction[1]} EUR")

        st.write("#### Payoff Chart")
        fig, ax = plt.subplots()
        strikes = [trans[1] for trans in transactions]
        premiums = [garman_kohlhagen(spot_price, trans[1], maturity, domestic_rate, foreign_rate, volatility, trans[2]) for trans in transactions]
        ax.bar(strikes, premiums, color=["green" if trans[3] == "buy" else "red" for trans in transactions])
        ax.set_xlabel("Strike Price")
        ax.set_ylabel("Premium (EUR)")
        ax.set_title("Transaction Payoffs")
        st.pyplot(fig)

if __name__ == "__main__":
    main()
