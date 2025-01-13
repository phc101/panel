import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

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

    # Calculate forward points
    forward_points = [rate - spot_rate for rate in forward_rates]

    # Generate maturity dates
    start_date = datetime.now()
    maturity_dates = [(start_date + timedelta(days=30 * month)).strftime("%Y-%m-%d") for month in months]

    fig, ax1 = plt.subplots()

    # Plot forward rates
    ax1.plot(maturity_dates, forward_rates, marker="o", label="Forward Rate")
    ax1.set_xlabel("Maturity Date")
    ax1.set_ylabel("Forward Rate", color="blue")
    ax1.tick_params(axis="y", labelcolor="blue")
    ax1.grid(True)

    # Annotate forward rates and move points next to the red line
    for i, (rate, point) in enumerate(zip(forward_rates, forward_points)):
        ax1.text(maturity_dates[i], rate, f"Rate: {rate:.4f}", 
                 ha="left", va="bottom", fontsize=7, color="blue")

    # Add secondary axis for forward points
    ax2 = ax1.twinx()
    ax2.plot(maturity_dates, forward_points, marker="x", color="red", label="Forward Points")
    ax2.set_ylabel("Forward Points", color="red")
    ax2.tick_params(axis="y", labelcolor="red")

    # Annotate forward points
    for i, point in enumerate(forward_points):
        ax2.text(maturity_dates[i], point, f"{point:.4f}", 
                 ha="right", va="bottom", fontsize=7, color="red")

    fig.suptitle("Forward Rate Curve (1-Year Tenor)")
    fig.autofmt_xdate(rotation=45)

    # Create a DataFrame for the table
    data = {
        "Tenor (Months)": months,
        "Maturity Date": maturity_dates,
        "Forward Rate": [f"{rate:.4f}" for rate in forward_rates],
        "Forward Points": [f"{point:.4f}" for point in forward_points]
    }
    df = pd.DataFrame(data)

    return fig, df

def main():
    st.title("Forward Rate Curve Calculator")

    st.sidebar.header("Inputs")
    spot_rate = st.sidebar.number_input("Spot Rate", value=4.5, step=0.01)

    # Domestic rate set to Poland interest rate
    poland_rate = st.sidebar.number_input("Poland Interest Rate (%)", value=5.75, step=0.1) / 100

    # Manual foreign interest rate input
    foreign_rate = st.sidebar.number_input("Foreign Interest Rate (%)", value=3.0, step=0.1) / 100

    if st.sidebar.button("Generate Forward Curve"):
        st.write("### Forward Rate Curve for 1-Year Tenor")
        forward_curve, forward_table = plot_forward_curve(spot_rate, poland_rate, foreign_rate)
        st.pyplot(forward_curve)

        st.write("### Forward Rates Table")
        st.dataframe(forward_table)

if __name__ == "__main__":
    main()
