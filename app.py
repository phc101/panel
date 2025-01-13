import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, tenor):
    """Calculate forward rate based on interest rate parity."""
    try:
        forward_rate = spot_rate * (1 + domestic_rate * tenor) / (1 + foreign_rate * tenor)
        return forward_rate
    except Exception as e:
        st.error(f"Error in forward rate calculation: {e}")
        return None

def plot_forward_curve(spot_rate, domestic_rate, foreign_rate):
    """Plot forward rate curve for a 1-year tenor on a monthly basis."""
    months = [i for i in range(1, 13)]  # 1 to 12 months
    forward_rates = [
        calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, month / 12) for month in months
    ]

    fig, ax = plt.subplots()
    ax.plot(months, forward_rates, marker="o")
    for i, rate in enumerate(forward_rates):
        ax.text(months[i], rate, f"{rate:.4f}", ha="left", va="bottom")
    ax.set_title("Forward Rate Curve (1-Year Tenor)")
    ax.set_xlabel("Months")
    ax.set_ylabel("Forward Rate")
    ax.grid(True)
    return fig

def main():
    st.title("Forward Rate Curve Calculator")

    st.sidebar.header("Inputs")
    spot_rate = st.sidebar.number_input("Spot Rate", value=4.5, step=0.01)
    domestic_rate = st.sidebar.number_input("Domestic Interest Rate (%)", value=1.5, step=0.1) / 100
    foreign_rate = st.sidebar.number_input("Foreign Interest Rate (%)", value=0.5, step=0.1) / 100

    if st.sidebar.button("Generate Forward Curve"):
        st.write("### Forward Rate Curve for 1-Year Tenor")
        forward_curve = plot_forward_curve(spot_rate, domestic_rate, foreign_rate)
        st.pyplot(forward_curve)

if __name__ == "__main__":
    main()
