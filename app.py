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
    today = datetime.now().date()
    start_tenor = (window_start - today).days / 365 if window_start > today else 0

    window_days = (window_end - window_start).days
    days = [i for i in range(0, window_days + 1, 30)]  # Monthly intervals within the window
    tenors = [(start_tenor + day / 365) for day in days]  # Adjust tenors based on start_tenor

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
        "Tenor (Days)": [int((start_tenor * 365) + day) for day in days],
        "Maturity Date": maturity_dates,
        "Forward Rate": forward_rates,
        "Forward Points": forward_points
    }
    df = pd.DataFrame(data)

    return fig, df, forward_rates, forward_points

def plot_gain_bar_chart(gain_table):
    """Plot a bar chart showing the gains over time with losses in red and a total bar at the end."""
    gain_table = gain_table[gain_table["Maturity Date"] != "Total"]  # Exclude the total row
    fig, ax = plt.subplots()
    colors = ["green" if x > 0 else "red" for x in gain_table["Gain from Points (PLN)"]]
    ax.bar(gain_table["Maturity Date"], gain_table["Gain from Points (PLN)"], color=colors, alpha=0.7)
    ax.set_xlabel("Maturity Date")
    ax.set_ylabel("Gain from Points (PLN)")
    ax.set_title("Gain Analysis")
    ax.tick_params(axis="x", rotation=45)

    # Add total bar
    total_gain = gain_table["Gain from Points (PLN)"].sum()
    ax.bar("Total", total_gain, color="blue", alpha=0.7)
    ax.text("Total", total_gain, f"{total_gain:.2f}", ha="center", va="bottom", fontsize=10)

    return fig

def calculate_gain_from_points(fixed_rate, forward_rates, maturity_dates, total_amount, monthly_closure):
    """Calculate gain from points in PLN given a fixed rate and monthly closures."""
    remaining_amount = total_amount
    gains = []

    for i, rate in enumerate(forward_rates):
        if remaining_amount <= 0:
            break

        close_amount = min(monthly_closure, remaining_amount)
        gain = (rate - fixed_rate) * close_amount
        gains.append({
            "Maturity Date": maturity_dates[i],
            "Remaining Amount (EUR)": remaining_amount,
            "Closure Amount (EUR)": close_amount,
            "Forward Rate": rate,
            "Gain from Points (PLN)": gain
        })
        remaining_amount -= close_amount

    df = pd.DataFrame(gains)
    df.loc["Total"] = df["Gain from Points (PLN)"].sum()
    df.loc["Total", "Maturity Date"] = "Total"
    df.loc["Total", "Remaining Amount (EUR)"] = "-"
    df.loc["Total", "Closure Amount (EUR)"] = "-"
    df.loc["Total", "Forward Rate"] = "-"

    return df

def calculate_average_rate_first_three(forward_rates):
    """Calculate the average rate for the first three forward rates."""
    return sum(forward_rates[:3]) / len(forward_rates[:3])

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

    total_amount = st.sidebar.number_input("Total Hedge Amount (EUR)", value=1000000, step=100000)
    monthly_closure = st.sidebar.number_input("Monthly Closure Amount (EUR)", value=100000, step=10000)

    # Option to use average price on open
    use_average_rate = st.sidebar.checkbox("Average Price on Open", value=False)

    if st.sidebar.button("Generate Window Forward Curve"):
        if window_start >= window_end:
            st.error("Window End Date must be after Window Start Date.")
        else:
            st.write("### Gain Analysis")
            forward_curve, forward_table, forward_rates, forward_points = plot_window_forward_curve(spot_rate, poland_rate, foreign_rate, window_start, window_end)

            # Determine the fixed rate based on the option
            if use_average_rate:
                fixed_rate = calculate_average_rate_first_three(forward_rates)
                st.write(f"Using Average Rate for First Three Forward Prices: {fixed_rate:.4f}")
            else:
                fixed_rate = forward_rates[0]  # Use the first forward rate as the fixed rate
                st.write(f"Using First Forward Rate as Fixed Rate: {fixed_rate:.4f}")

            gain_table = calculate_gain_from_points(fixed_rate, forward_rates, forward_table["Maturity Date"].tolist(), total_amount, monthly_closure)
            st.dataframe(gain_table)

            bar_chart = plot_gain_bar_chart(gain_table)
            st.pyplot(bar_chart)

            st.write("### Window Forward Rate Curve")
            st.pyplot(forward_curve)

            st.write("### Window Forward Rates Table")
            st.dataframe(forward_table)

if __name__ == "__main__":
    main()
