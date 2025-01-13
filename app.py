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

def plot_window_forward_curve(spot_rate, domestic_rate, foreign_rate, window_start, window_end):
    """Plot forward rate curve for a window forward contract."""
    window_days = (window_end - window_start).days
    days = [i for i in range(0, window_days + 1, 30)]  # Monthly intervals within the window
    tenors = [day / 365 for day in days]  # Convert days to years

    forward_rates = [
        calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, tenor) for tenor in tenors
    ]

    # Calculate forward points
    forward_points = [rate - spot_rate for rate in forward_rates]

    # Generate maturity dates
    maturity_dates = [(window_start + timedelta(days=day)).strftime("%Y-%m-%d") for day in days]

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

    fig.suptitle("Window Forward Rate Curve")
    fig.autofmt_xdate(rotation=45)

    # Create a DataFrame for the table
    data = {
        "Tenor (Days)": days,
        "Maturity Date": maturity_dates,
        "Forward Rate": [f"{rate:.4f}" for rate in forward_rates],
        "Forward Points": [f"{point:.4f}" for point in forward_points]
    }
    df = pd.DataFrame(data)

    return fig, df, forward_rates, forward_points

def plot_loss_due_to_fixed_rate(fixed_rate, forward_rates, forward_points, maturity_dates):
    """Plot the client's loss due to holding fixed at window open rate."""
    losses = [fixed_rate - rate for rate in forward_rates]

    fig, ax = plt.subplots()
    ax.plot(maturity_dates, losses, marker="o", label="Loss")
    ax.set_xlabel("Maturity Date")
    ax.set_ylabel("Loss in Forward Points")
    ax.set_title("Loss Due to Fixed Rate")
    ax.grid(True)

    for i, loss in enumerate(losses):
        ax.text(maturity_dates[i], losses[i], f"{loss:.4f}", ha="center", va="bottom", fontsize=7)

    return fig

def main():
    st.title("Window Forward Rate Calculator")

    st.sidebar.header("Inputs")
    spot_rate = st.sidebar.number_input("Spot Rate", value=4.5, step=0.01)

    # Domestic rate set to Poland interest rate
    poland_rate = st.sidebar.number_input("Poland Interest Rate (%)", value=5.75, step=0.1) / 100

    # Manual foreign interest rate input
    foreign_rate = st.sidebar.number_input("Foreign Interest Rate (%)", value=3.0, step=0.1) / 100

    # Window forward inputs
    window_start = st.sidebar.date_input("Window Start Date", value=datetime.now().date())
    window_end = st.sidebar.date_input("Window End Date", value=(datetime.now() + timedelta(days=90)).date())

    if st.sidebar.button("Generate Window Forward Curve"):
        if window_start >= window_end:
            st.error("Window End Date must be after Window Start Date.")
        else:
            st.write("### Window Forward Rate Curve")
            forward_curve, forward_table, forward_rates, forward_points = plot_window_forward_curve(spot_rate, poland_rate, foreign_rate, window_start, window_end)
            st.pyplot(forward_curve)

            st.write("### Window Forward Rates Table")
            st.dataframe(forward_table)

            fixed_rate = forward_rates[0]  # Assume fixed rate is the first forward rate in the window
            st.write(f"### Loss Analysis (Fixed Rate: {fixed_rate:.4f})")
            loss_curve = plot_loss_due_to_fixed_rate(fixed_rate, forward_rates, forward_points, forward_table["Maturity Date"].tolist())
            st.pyplot(loss_curve)

if __name__ == "__main__":
    main()
