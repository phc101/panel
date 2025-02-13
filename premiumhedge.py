import requests
import json

# Replace with your SerpAPI key
SERPAPI_KEY = "your_serpapi_key"

# Google search query to find Polish exporters to the UK
QUERY = "site:.pl export to UK OR exporting to UK OR eksport do UK OR eksport Wielka Brytania"

# SerpAPI endpoint
API_URL = "https://serpapi.com/search.json"

def get_polish_exporters_to_uk():
    params = {
        "q": QUERY,       # Search query
        "engine": "google",  # Use Google search engine
        "api_key": SERPAPI_KEY,  # Your API key
        "num": 20,        # Number of results to fetch
        "hl": "pl",       # Polish language results
    }

    print("Fetching search results from SerpAPI...")

    try:
        response = requests.get(API_URL, params=params)
