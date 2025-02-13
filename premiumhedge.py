from serpapi import GoogleSearch
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Your SerpApi key
api_key = 'e9626f65ccba8349ed8f9a3b9fbb448092d151f7d8998df5a8bc4c354c85e31a'

# Function to fetch data for a given currency pair
def fetch_currency_data(pair):
    params = {
        'api_key': api_key,
        'engine': 'google_finance',
        'q': pair,
        'window': '1Y',  # 1 Year window
        'hl': 'en'
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    return results.get('graph', [])

# Currency pairs to fetch
currency_pairs = ['EURPLN', 'USDPLN', 'GBPPLN', 'EURUSD']

# Dictionary to hold data
data = {}

# Fetch data for each pair
for pair in currency_pairs:
    graph_data = fetch_currency_data(pair)
    if graph_data:
        dates = [datetime.utcfromtimestamp(point['timestamp']) for point in graph_data]
        prices = [point['price'] for point in graph_data]
        data[pair] = pd.Series(prices, index=dates)

# Create a DataFrame
df = pd.DataFrame(data)

# Plotting
plt.figure(figsize=(14, 7))
for column in df.columns:
    plt.plot(df.index, df[column], label=column)
plt.title('Currency Exchange Rates Over the Last 12 Months')
plt.xlabel('Date')
plt.ylabel('Exchange Rate')
plt.legend()
plt.grid(True)
plt.show()
