import requests

# Your SerpAPI Key
api_key = "e9626f65ccba8349ed8f9a3b9fbb448092d151f7d8998df5a8bc4c354c85e31a"

# Test URL for EUR/PLN
url = f"https://serpapi.com/search?api_key={api_key}&engine=google_finance&q=EURPLN"

# Fetch data
response = requests.get(url)

# Print response
print(response.json())
