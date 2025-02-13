from serpapi import GoogleSearch

params = {
    "api_key": e9626f65ccba8349ed8f9a3b9fbb448092d151f7d8998df5a8bc4c354c85e31a,
    "engine": "google_finance",
    "q": "EURPLN"
}

search = GoogleSearch(params)
results = search.get_dict()
print(results)  # Print raw results to debug
