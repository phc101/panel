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

    fig, ax = plt.subplots()

    # Plot step chart for forward rates
    ax.step(maturity_dates, forward_rates, where='post', label="Forward Rate", linewidth=1, color="blue")

    # Annotate forward rates
    for i, rate in enumerate(forward_rates):
        ax.text(maturity_dates[i], rate, f"{rate:.4f}", fontsize=8, ha="center", va="bottom", color="blue")

    # Annotate maturity dates
    for i, date in enumerate(maturity_dates):
        ax.text(date, forward_rates[i], date, fontsize=8, ha="right", va="bottom", rotation=45, color="black")

    ax.set_xlabel("Maturity Date")
    ax.set_ylabel("Forward Rate")
    ax.set_title("Step Chart of Forward Rates")
    ax.grid(True)
    plt.xticks(rotation=45)
    plt.legend()

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

def calculate_gain_from_points(fixed_rate, forward_rates, maturity_dates, total_amount, monthly_closure, use_adjusted_rates=False):
    """Calculate gain from points in PLN given a fixed rate or adjusted rates and monthly closures."""
    remaining_amount = total_amount
    gains = []

    for i, rate in enumerate(forward_rates):
        if remaining_amount <= 0:
            break

        close_amount = min(monthly_closure, remaining_amount)

        if use_adjusted_rates:
            gain = (rate * (1 + fixed_rate)) * close_amount - fixed_rate * close_amount
        else:
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

    window_start = st.sidebar.date_input("Window Start Date", value=datetime.now().date())
    window_end = st.sidebar.date_input("Window End Date", value=(datetime.now() + timedelta(days=90)).date())

    total_amount = st.sidebar.number_input("Total Hedge Amount (EUR)", value=1000000, step=100000)
    monthly_closure = st.sidebar.number_input("Monthly Closure Amount (EUR)", value=100000, step=10000)

    # Option to use average price on open
    use_average_rate = st.sidebar.checkbox("Average Price on Open", value=False)

    # Option to add percentage of points to the fixed rate
    points_percentage = st.sidebar.number_input("Add % of Points to Fixed Rate", value=0, step=1, min_value=-100, max_value=100) / 100

    # Option to apply percentage to average or all forwards
    apply_to_average = st.sidebar.radio("Apply % of Points to:", ("Average Price on Open", "All Window Open Forwards"))

    if st.sidebar.button("Generate Window Forward Curve"):
        if window_start >= window_end:
            st.error("Window End Date must be after Window Start Date.")
        else:
            st.write("### Gain Analysis")
            forward_curve, forward_table, forward_rates, forward_points = plot_window_forward_curve(spot_rate, poland_rate, foreign_rate, window_start, window_end)

            # Determine the fixed rate based on the option
            if use_average_rate:
                base_fixed_rate = calculate_average_rate_first_three(forward_rates)
                st.write(f"Using Average Rate for First Three Forward Prices: {base_fixed_rate:.4f}")
            else:
                base_fixed_rate = forward_rates[0]  # Use the first forward rate as the fixed rate
                st.write(f"Using First Forward Rate as Fixed Rate: {base_fixed_rate:.4f}")

            # Adjust fixed rate by adding percentage of points
            if apply_to_average == "Average Price on Open":
                adjusted_fixed_rate = base_fixed_rate + (base_fixed_rate * points_percentage)
                st.write(f"Adjusted Fixed Rate (Average Price + {points_percentage * 100:.0f}%): {adjusted_fixed_rate:.4f}")

                gain_table = calculate_gain_from_points(adjusted_fixed_rate, forward_rates, forward_table["Maturity Date"].tolist(), total_amount, monthly_closure)
            else:
                adjusted_forward_rates = [rate + (rate * points_percentage) for rate in forward_rates]
                st.write(f"Adjusted Forward Rates (All Window Open + {points_percentage * 100:.0f}%):")
                for i, rate in enumerate(adjusted_forward_rates):
                    st.write(f"{forward_table['Maturity Date'][i]}: {rate:.4f}")

                gain_table = calculate_gain_from_points(points_percentage, adjusted_forward_rates, forward_table["Maturity Date"].tolist(), total_amount, monthly_closure, use_adjusted_rates=True)

            st.dataframe(gain_table)

            bar_chart = plot_gain_bar_chart(gain_table)
            st.pyplot(bar_chart)

            st.write("### Step Chart of Forward Rates")
            st.pyplot(forward_curve)
            st.dataframe(forward_table)

if __name__ == "__main__":
    main()
