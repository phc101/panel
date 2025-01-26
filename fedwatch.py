import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt

# Title of the app
st.title("CME FedWatch Tool Viewer")
st.markdown("This app displays data from the CME FedWatch Tool, showcasing probabilities of interest rate changes.")

# Function to fetch and parse data from CME FedWatch Tool
def fetch_fedwatch_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Find the data table (adjust the selector based on the webpage structure)
        table = soup.find("table")
        if not table:
            st.error("Could not find the data table on the webpage.")
            return None

        # Extract table headers and rows
        headers = [th.text.strip() for th in table.find_all("th")]
        rows = []
        for tr in table.find_all("tr")[1:]:  # Skip header row
            cells = [td.text.strip() for td in tr.find_all("td")]
            rows.append(cells)

        # Create a DataFrame
        data = pd.DataFrame(rows, columns=headers)
        return data

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return None

# URL for the CME FedWatch Tool
url = "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"

# Fetch data
st.subheader("Interest Rate Probabilities")
data = fetch_fedwatch_data(url)

if data is not None:
    # Display data
    st.dataframe(data)

    # Display probabilities as a bar chart
    try:
        probabilities = data.iloc[:, 1].str.replace('%', '').astype(float)  # Assuming second column holds probabilities
        labels = data.iloc[:, 0]  # Assuming first column holds labels

        plt.figure(figsize=(10, 6))
        plt.bar(labels, probabilities, color="skyblue")
        plt.title("Interest Rate Probabilities")
        plt.ylabel("Probability (%)")
        plt.xlabel("Rate")
        plt.xticks(rotation=45)
        st.pyplot(plt)
    except Exception as e:
        st.error(f"Error generating chart: {e}")

# Notes
st.markdown(
    """
    **Notes:**
    - Data is sourced directly from the [CME FedWatch Tool]({url}).
    - Ensure the structure of the webpage has not changed for accurate data parsing.
    """
)
