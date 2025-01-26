import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def calculate_binomial_tree(prices, days=5, risk_free_rate=0.01):
    """
    Calculate a binomial tree based on the last 20 prices.
    """
    # Ensure prices are valid and positive
    prices = np.array(prices)
    if np.any(prices <= 0):
        raise ValueError("Prices must be positive and non-zero for log calculations.")

    log_returns = np.log(prices[1:] / prices[:-1])
    sigma = np.std(log_returns)
    dt = 1 / 252  # One trading day
    u = np.exp(sigma * np.sqrt(dt))
    d = 1 / u
    p = (np.exp(risk_free_rate * dt) - d) / (u - d)

    # Initialize the binomial tree
    tree = np.zeros((days + 1, days + 1))
    tree[0, 0] = prices[-1]

    # Build the tree
    for i in range(1, days + 1):
        for j in range(i + 1):
            tree[j, i] = prices[-1] * (u ** (i - j)) * (d ** j)

    return tree, p

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

        # Sort data by date and get the last 20 prices
        data = data.sort_values(by='Date')
        if len(data) < 20:
            st.error("Not enough data. Please provide at least 20 valid prices.")
        else:
            prices = data['Close'].tail(20).values  # Select only the last 20 prices

            try:
                # Calculate binomial tree
                tree, prob = calculate_binomial_tree(prices)

                # Display results
                st.subheader("Binomial Tree")
                st.write("Probability of Up Movement (p):", round(prob, 4))

                # Convert tree to DataFrame for better display
                tree_df = pd.DataFrame(tree)
                tree_df.index.name = "Down Steps"
                tree_df.columns.name = "Days"

                st.write("Binomial Tree Table:")
                st.dataframe(tree_df.style.format(precision=4))

                # Plot the tree
                st.subheader("Binomial Tree Chart")

                fig, ax = plt.subplots(figsize=(10, 6))
                for i in range(tree.shape[1]):
                    x = [i] * (i + 1)
                    y = tree[:i + 1, i]
                    ax.plot(x, y, 'o-', label=f"Day {i}")

                ax.set_title("Binomial Tree Price Forecast")
                ax.set_xlabel("Days")
                ax.set_ylabel("Price")
                ax.grid(True, linestyle='--', alpha=0.7)
                st.pyplot(fig)
            except ValueError as e:
                st.error(f"Error in calculation: {e}")
    else:
        st.error("The uploaded file does not contain the required 'Date' and 'Close' columns.")
else:
    st.info("Please upload a CSV file to proceed.")
