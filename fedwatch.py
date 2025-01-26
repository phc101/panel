import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

def calculate_binomial_tree(prices, volatility, days=5):
    """
    Calculate a binomial tree using provided volatility for formula.
    """
    # Ensure prices are valid and positive
    prices = np.array(prices)
    if np.any(prices <= 0):
        raise ValueError("Prices must be positive and non-zero for log calculations.")

    # Convert volatility to decimal
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

    return tree, probabilities, up, down, p_up

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
            if 'date' not in data.columns or 'close' not in data.columns or 'volatility for formula' not in data.columns:
                st.warning("The required columns 'Date', 'Close', and 'Volatility for Formula' were not found. Please map them below:")
                date_col = st.selectbox("Select the Date column:", data.columns, key=f"{pair}_date")
                close_col = st.selectbox("Select the Close column:", data.columns, key=f"{pair}_close")
                vol_col = st.selectbox("Select the Volatility for Formula column:", data.columns, key=f"{pair}_vol")
                data = data.rename(columns={date_col: 'date', close_col: 'close', vol_col: 'volatility for formula'})

            if 'date' in data.columns and 'close' in data.columns and 'volatility for formula' in data.columns:
                data['date'] = pd.to_datetime(data['date'])

                # Replace commas with dots and convert 'close' to numeric if necessary
                data['close'] = data['close'].astype(str).str.replace(',', '.').astype(float)
                data['volatility for formula'] = data['volatility for formula'].astype(str).str.replace(',', '.').astype(float)

                # Drop rows with missing values
                data = data.dropna(subset=['close', 'volatility for formula'])

                # Exclude weekends (Saturday = 5, Sunday = 6)
                data = data[data['date'].dt.weekday < 5]

                # Sort data by date and get the last 20 prices and volatility
                data = data.sort_values(by='date')
                if len(data) < 20:
                    st.error("Not enough data. Please provide at least 20 valid weekday prices.")
                else:
                    prices = data['close'].tail(20).values  # Select only the last 20 prices
                    volatility = data['volatility for formula'].iloc[-1]  # Use the latest volatility

                    try:
                        # Calculate binomial tree
                        tree, probabilities, up, down, p_up = calculate_binomial_tree(prices, volatility)

                        # Display results
                        st.subheader("Binomial Tree")
                        st.write("Up Factor (u):", round(up, 6))
                        st.write("Down Factor (d):", round(down, 6))
                        st.write("Probability of Up Movement (p):", round(p_up, 4))
                        st.write("Volatility for Formula (%):", round(volatility, 4))

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

                        fig, ax = plt.subplots(figsize=(10, 6))
                        for i in range(tree.shape[1]):
                            x = [i] * (i + 1)
                            y = tree[:i + 1, i]
                            ax.plot(x, y, 'o-', label=f"Day {i}")

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
                st.error("The uploaded file does not contain the required 'Date', 'Close', and 'Volatility for Formula' columns.")
        else:
            st.info(f"Please upload a file for {pair} to proceed.")
