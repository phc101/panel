import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Define API Key
api_key = "e9626f65ccba8349ed8f9a3b9fbb448092d151f7d8998df5a8bc4c354c85e31a"

# Define API URL for EUR/PLN
url = f"https://serpapi.com/search?api_key={api_key}&engine=google_finance&q=EURPLN"

# Fetch data
response = requests.get(url)
data = response.json()

# Check if data exists
if "graph" in data:
    # Extract timestamps & prices
    timestamps = [point["timestamp"] for point in data["graph"]]
    prices = [point["price"] for point in data["graph"]]

    # Convert timestamps to readable dates
    dates = [datetime.utcfromtimestamp(ts) for ts in timestamps]

    # Create DataFrame
    df = pd.DataFrame({"Date": dates, "EUR/PLN": prices})
    df.set_index("Date", inplace=True)

    # Plot the time-series chart
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df["EUR/PLN"], label="EUR/PLN", color="blue")
    plt.xlabel("Date")
    plt.ylabel("Exchange Rate")
    plt.title("EUR/PLN Exchange Rate - Last 12 Months")
    plt.legend()
    plt.grid(True)
    plt.show()

else:
    print("Error: No graph data available. Check API response.")
