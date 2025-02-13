from serpapi import GoogleSearch

params = {
    "api_key": api_key,
    "engine": "google_finance",
    "q": "EURPLN"
}

search = GoogleSearch(params)
results = search.get_dict()
print(results)  # Print raw results to debug
