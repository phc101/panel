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

def monte_carlo_barrier(S, K, T, rd, rf, sigma, barrier, option_type, paths):
    dt = T / 252  # Daily steps
    prices = np.zeros(paths)

    for i in range(paths):
        path = [S]
        for _ in range(int(T / dt)):
            dS = path[-1] * (rd - rf) * dt + sigma * path[-1] * np.sqrt(dt) * np.random.normal()
            path.append(path[-1] + dS)

            if (option_type == "knock-out" and path[-1] >= barrier) or \
               (option_type == "knock-in" and path[-1] <= barrier):
                path[-1] = 0
                break

        payoff = max(0, path[-1] - K) if option_type == "call" else max(0, K - path[-1])
        prices[i] = payoff

    return np.exp(-rd * T) * np.mean(prices)

def main():
    st.title("EUR/PLN Barrier Option Pricer")

    st.sidebar.header("Option Parameters")
    spot_price = st.sidebar.number_input("Spot Price (EUR/PLN)", value=4.21, step=0.01)
    strike_price = st.sidebar.number_input("Strike Price", value=4.30, step=0.01)
    domestic_rate = st.sidebar.number_input("Domestic Risk-Free Rate (%)", value=6.0, step=0.1) / 100
    foreign_rate = st.sidebar.number_input("Foreign Risk-Free Rate (%)", value=2.5, step=0.1) / 100
    volatility = st.sidebar.number_input("Volatility (%)", value=15.0, step=0.1) / 100
    maturity = st.sidebar.number_input("Time to Maturity (Years)", value=0.5, step=0.1)

    st.sidebar.header("Barrier Settings")
    barrier_type = st.sidebar.selectbox("Barrier Type", ["knock-in", "knock-out"])
    barrier_level = st.sidebar.number_input("Barrier Level", value=4.50, step=0.01)

    st.sidebar.header("Monte Carlo Settings")
    paths = st.sidebar.number_input("Simulation Paths", value=10000, step=1000)

    option_type = st.selectbox("Option Type", ["call", "put"])

    if st.button("Calculate Price"):
        analytical_price = garman_kohlhagen(spot_price, strike_price, maturity, domestic_rate, foreign_rate, volatility, option_type)
        monte_carlo_price = monte_carlo_barrier(spot_price, strike_price, maturity, domestic_rate, foreign_rate, volatility, barrier_level, barrier_type, paths)

        st.write(f"### Analytical Price: {analytical_price:.4f}")
        st.write(f"### Monte Carlo Price: {monte_carlo_price:.4f}")

        st.write("#### Price Sensitivity Chart")
        strikes = np.linspace(strike_price * 0.8, strike_price * 1.2, 50)
        prices = [garman_kohlhagen(spot_price, K, maturity, domestic_rate, foreign_rate, volatility, option_type) for K in strikes]
        
        fig, ax = plt.subplots()
        ax.plot(strikes, prices, label="Analytical Price")
        ax.axvline(x=strike_price, color='red', linestyle='--', label="Strike Price")
        ax.set_xlabel("Strike Price")
        ax.set_ylabel("Option Price")
        ax.legend()
        st.pyplot(fig)

if __name__ == "__main__":
    main()
