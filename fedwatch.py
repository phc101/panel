import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def calculate_binomial_tree(prices, days=5):
    """
    Calculate a binomial tree based on the last 20 prices dynamically using volatility.
    """
    # Ensure prices are valid and positive
    prices = np.array(prices)
    if np.any(prices <= 0):
        raise ValueError("Prices must be positive and non-zero for log calculations.")

    # Calculate daily log returns and volatility
    log_returns = np.log(prices[1:] / prices[:-1])
    sigma = np.std(log_returns)  # Volatility
    dt = 1 / 252  # One trading day

    # Calculate up, down factors, and probabilities
    up = np.exp(sigma * np.sqrt(dt))
    down = 1 / up
    p_up = 0.5  # Assuming equal probability for simplicity

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
                probabilities[j, i] += probabilities[j, i - 1] * (1 - p_up)

    return tree, probabilities, up, down, p_up

# Streamlit UI
st.title("EUR/PLN Binomial Tree Price Forecaster")

# File uploader
uploaded_file = st.file_uploader("Upload a CSV file with historical EUR/PLN prices", type="csv")

if uploaded_file is not None:
    # Load the data
    data = pd.read_csv(uploaded_file)
    st.write("Uploaded Data:", data.head())

    # Ensure the data has a 'Date' column and convert it to datetime
    if 'Date' in data.columns and 'Close' in data.columns:
        data['Date'] = pd.to_datetime(data['Date'])

        # Replace commas with dots and convert 'Close' to numeric
        data['Close'] = data['Close'].str.replace(',', '.').astype(float)

        # Drop rows with missing values
        data = data.dropna(subset=['Close'])

        # Exclude weekends (Saturday = 5, Sunday = 6)
        data = data[data['Date'].dt.weekday < 5]

        # Sort data by date and get the last 20 prices
        data = data.sort_values(by='Date')
        if len(data) < 20:
            st.error("Not enough data. Please provide at least 20 valid weekday prices.")
        else:
            prices = data['Close'].tail(20).values  # Select only the last 20 prices

            try:
                # Calculate binomial tree
                tree, probabilities, up, down, p_up = calculate_binomial_tree(prices)

                # Display results
                st.subheader("Binomial Tree")
                st.write("Up Factor (u):", round(up, 6))
                st.write("Down Factor (d):", round(down, 6))
                st.write("Probability of Up Movement (p):", round(p_up, 4))

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

                ax.set_title("Binomial Tree Price Forecast")
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
    st.info("Please upload a CSV file to proceed.")
