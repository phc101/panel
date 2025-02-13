import requests

# Your SerpAPI Key
api_key = "e9626f65ccba8349ed8f9a3b9fbb448092d151f7d8998df5a8bc4c354c85e31a"

# Define the SerpAPI endpoint for Google Finance
url = f"https://serpapi.com/search?engine=google_finance&q=EURPLN&api_key={api_key}"

# Send request
response = requests.get(url)

# Print raw response
print(response.json())
