import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

def calculate_volatility(prices):
    """
    Calculate the volatility based on the last 20 days of prices.
    Volatility is calculated as the standard deviation of percentage changes, annualized.
    """
    percentage_changes = prices[1:] / prices[:-1] - 1  # Daily percentage changes
    std_dev = np.std(percentage_changes)  # Standard deviation of daily returns
    annualized_volatility = std_dev * np.sqrt(252) * 100  # Annualized volatility in percentage
    return annualized_volatility

def calculate_binomial_tree(prices, days=5):
    """
    Calculate a binomial tree using dynamically computed volatility.
    """
    # Ensure prices are valid and positive
    prices = np.array(prices)
    if np.any(prices <= 0):
        raise ValueError("Prices must be positive and non-zero for log calculations.")

    # Calculate volatility dynamically
    volatility = calculate_volatility(prices)
    sigma = volatility / 100  # Convert percentage to decimal
    dt = 1 / 252  # One trading day

    # Calculate up, down factors, and probabilities
    up = np.exp(sigma * np.sqrt(dt))
    down = 1 / up
    p_up = (np.exp((sigma ** 2) * dt) - down) / (up - down)  # Up probability
    p_down = 1 - p_up  # Down probability

    # Initialize the binomial tree and probability tree
    tree = np.zeros((days + 1, days + 1))
    probabilities = np.zeros((days + 1, days + 1))
    tree[0, 0] = prices[-1]
    probabilities[0, 0] = 1  # Starting node has 100% probability

    # Build the tree
    for i in range(1, days + 1):
        for j in range(i + 1):
            tree[j, i] = prices[-1] * (up ** (i - j)) * (down ** j)
            if j > 0:
                probabilities[j, i] += probabilities[j - 1, i - 1] * p_up
            if j < i:
                probabilities[j, i] += probabilities[j, i - 1] * p_down

    return tree, probabilities, up, down, p_up, volatility

# Streamlit UI
st.title("Binomial Tree Price Forecaster")

# Tab selection for EUR/PLN and USD/PLN
tab1, tab2 = st.tabs(["EUR/PLN", "USD/PLN"])

for tab, pair in zip([tab1, tab2], ["EUR/PLN", "USD/PLN"]):
    with tab:
        st.header(f"{pair} Binomial Tree")

        # File uploader
        uploaded_file = st.file_uploader(f"Upload a file with historical {pair} prices", type=["csv", "xlsx"], key=pair)

        if uploaded_file is not None:
            # Load the data based on file type
            if uploaded_file.name.endswith(".csv"):
                data = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith(".xlsx"):
                data = pd.read_excel(uploaded_file)
            else:
                st.error("Unsupported file format. Please upload a CSV or Excel file.")
                continue

            st.write("Uploaded Data:", data.head())

            # Display column names for debugging
            st.write("Columns in the uploaded file:", data.columns.tolist())

            # Normalize column names to handle potential mismatches
            data.columns = data.columns.str.strip().str.lower()

            # Allow user to map columns if required ones are missing
            if 'date' not in data.columns or 'close' not in data.columns:
                st.warning("The required columns 'Date' and 'Close' were not found. Please map them below:")
                date_col = st.selectbox("Select the Date column:", data.columns, key=f"{pair}_date")
                close_col = st.selectbox("Select the Close column:", data.columns, key=f"{pair}_close")
                data = data.rename(columns={date_col: 'date', close_col: 'close'})

            if 'date' in data.columns and 'close' in data.columns:
                data['date'] = pd.to_datetime(data['date'])

                # Replace commas with dots and convert 'close' to numeric if necessary
                data['close'] = data['close'].astype(str).str.replace(',', '.').astype(float)

                # Drop rows with missing values
                data = data.dropna(subset=['close'])

                # Exclude weekends (Saturday = 5, Sunday = 6)
                data = data[data['date'].dt.weekday < 5]

                # Sort data by date and get the last 20 prices
                data = data.sort_values(by='date')
                if len(data) < 20:
                    st.error("Not enough data. Please provide at least 20 valid weekday prices.")
                else:
                    prices = data['close'].tail(20).values  # Select only the last 20 prices

                    try:
                        # Calculate binomial tree
                        tree, probabilities, up, down, p_up, volatility = calculate_binomial_tree(prices)

                        # Display results
                        st.subheader("Binomial Tree")
                        st.write("Up Factor (u):", round(up, 6))
                        st.write("Down Factor (d):", round(down, 6))
                        st.write("Probability of Up Movement (p):", round(p_up, 4))
                        st.write("Volatility (Annualized, %):", round(volatility, 4))

                        # Convert tree to DataFrame for better display
                        tree_df = pd.DataFrame(tree)
                        tree_df.index.name = "Down Steps"
                        tree_df.columns.name = "Days"

                        st.write("Binomial Tree Table:")
                        st.dataframe(tree_df.style.format(precision=4))

                        # Convert probabilities to DataFrame for better display
                        prob_df = pd.DataFrame(probabilities)
                        prob_df.index.name = "Down Steps"
                        prob_df.columns.name = "Days"

                        st.write("Probability Tree Table:")
                        st.dataframe(prob_df.style.format(precision=4))

                        # Identify the most probable path
                        most_probable_path = [np.argmax(probabilities[:, i]) for i in range(probabilities.shape[1])]
                        most_probable_prices = [tree[most_probable_path[i], i] for i in range(len(most_probable_path))]

                        st.subheader("Most Probable Path")
                        st.write("Most probable prices:", most_probable_prices)

                        # Plot the tree
                        st.subheader("Binomial Tree Chart")

                        fig, ax = plt.subplots(figsize=(12, 8))
                        for i in range(tree.shape[1]):
                            x = [i] * (i + 1)
                            y = tree[:i + 1, i]
                            ax.plot(x, y, 'o-', label=f"Day {i}")

                            # Add price labels to nodes
                            for j in range(i + 1):
                                ax.text(i, tree[j, i], f"{tree[j, i]:.2f}", fontsize=8, ha='center', va='bottom')

                        # Highlight the most probable path
                        x_path = list(range(len(most_probable_path)))
                        ax.plot(x_path, most_probable_prices, 'r-o', label="Most Probable Path")

                        ax.set_title(f"{pair} Binomial Tree Price Forecast")
                        ax.set_xlabel("Days")
                        ax.set_ylabel("Price")
                        ax.grid(True, linestyle='--', alpha=0.7)
                        ax.legend()
                        st.pyplot(fig)
                    except ValueError as e:
                        st.error(f"Error in calculation: {e}")
            else:
                st.error("The uploaded file does not contain the required 'Date' and 'Close' columns.")
        else:
            st.info(f"Please upload a file for {pair} to proceed.")
