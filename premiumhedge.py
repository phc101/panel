import requests

# SerpAPI Key (Replace with your actual key)
SERPAPI_KEY = "e9626f65ccba8349ed8f9a3b9fbb448092d151f7d8998df5a8bc4c354c85e31a"

# Google search query for Polish (.pl) websites exporting to the UK
QUERY = "site:.pl export to UK OR eksport do UK OR eksport Wielka Brytania"

# SerpAPI endpoint
API_URL = "https://serpapi.com/search.json"

def get_polish_exporters_to_uk():
    params = {
        "q": QUERY,             # Search query
        "engine": "google",     # Use Google search
        "api_key": SERPAPI_KEY, # SerpAPI Key
        "num": 20,              # Number of results to fetch
        "hl": "pl",             # Language: Polish
    }

    print("🔍 Searching for Polish companies exporting to the UK...")

    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()  # Raises error for non-200 responses

        data = response.json()

        # Extract and print website links from search results
        company_urls = [result["link"] for result in data.get("organic_results", [])]

        if company_urls:
            print("\n✅ Found Polish exporters to the UK:")
            for url in company_urls:
                print(url)
        else:
            print("❌ No relevant company websites found.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data: {e}")

if __name__ == "__main__":
    get_polish_exporters_to_uk()
