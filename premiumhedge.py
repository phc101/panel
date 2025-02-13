import requests
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# SerpApi key (replace with your own key)
SERPAPI_KEY = "e9626f65ccba8349ed8f9a3b9fbb448092d151f7d8998df5a8bc4c354c85e31a"

# Function to fetch bond yields from Google Finance via SerpApi
def fetch_bond_yield(country, maturity="2Y"):
    search_url = "https://serpapi.com/search"
    params = {
        "engine": "google_finance",
        "q": f"{country} {maturity} bond yield",
        "api_key": SERPAPI_KEY,
    }
    
    response = requests.get(search_url, params=params)
    data = response.json()
    
    # Extract bond yield from the response
    try:
        bond_yield = float(data["finance_results"]["market_summary"]["summary"][0]["value"])
        return bond_yield
    except (KeyError, IndexError, ValueError):
        return None

# Function to fetch EUR/PLN exchange rate
def fetch_eurpln_rate():
    search_url = "https://serpapi.com/search"
    params = {
        "engine": "google_finance",
        "q": "EUR/PLN",
        "api_key": SERPAPI_KEY,
    }
    
    response = requests.get(search_url, params=params)
    data = response.json()
    
    # Extract exchange rate from the response
    try:
        rate = float(data["finance_results"]["market_summary"]["summary"][0]["value"])
        return rate
    except (KeyError, IndexError, ValueError):
        return None

# Fetch live data
poland_2y_yield = fetch_bond_yield("Poland")
germany_2y_yield = fetch_bond_yield("Germany")
eurpln_rate = fetch_eurpln_rate()

# Print the fetched values
print(f"Poland 2Y Yield: {poland_2y_yield}%")
print(f"Germany 2Y Yield: {germany_2y_yield}%")
print(f"EUR/PLN Exchange Rate: {eurpln_rate}")

# Perform time-lag correlation analysis
if poland_2y_yield and germany_2y_yield and eurpln_rate:
    bond_spread = germany_2y_yield - poland_2y_yield
    
    # Simulate historical data (replace with actual data if available)
    time_lags = range(1, 91)  # Test from 1 to 90 days lag
    correlations = []
    
    np.random.seed(42)  # For reproducibility
    historical_spreads = np.linspace(bond_spread - 0.5, bond_spread + 0.5, num=100)  # Simulated bond spreads
    historical_eurpln = np.linspace(eurpln_rate - 0.05, eurpln_rate + 0.05, num=100)  # Simulated EUR/PLN rates
    
    for lag in time_lags:
        shifted_spread = np.roll(historical_spreads, lag)
        correlation = np.corrcoef(historical_eurpln, shifted_spread)[0, 1]
        correlations.append(correlation)

    # Find the best lag with highest correlation
    best_lag = time_lags[correlations.index(max(correlations))]
    best_correlation = max(correlations)

    # Plot correlation vs. time lag
    plt.figure(figsize=(10, 5))
    plt.plot(time_lags, correlations, marker='o', linestyle='-')
    plt.xlabel("Time Lag (Days)")
    plt.ylabel("Correlation")
    plt.title("Correlation Between EUR/PLN and 2Y Bond Spread at Different Time Lags")
    plt.axvline(best_lag, color='red', linestyle='dashed', label=f'Best Lag: {best_lag} days')
    plt.legend()
    plt.grid(True)
    plt.show()

    print(f"Best Time Lag: {best_lag} days, Correlation: {best_correlation}")
