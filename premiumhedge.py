import streamlit as st
import requests
import random
import time
from bs4 import BeautifulSoup

# SerpAPI Key (replace with your key)
SERPAPI_KEY = "e9626f65ccba8349ed8f9a3b9fbb448092d151f7d8998df5a8bc4c354c85e31a"

# Google search query for Polish (.pl) exporters to the UK
QUERY = "site:.pl export to UK OR eksport do UK OR eksport Wielka Brytania"

# SerpAPI endpoint
API_URL = "https://serpapi.com/search.json"

# Set session state to track searches and previous results
if "search_count" not in st.session_state:
    st.session_state.search_count = 0
if "previous_results" not in st.session_state:
    st.session_state.previous_results = set()

st.title("🔍 Find Polish Exporters to the UK")
st.write("Click the button below to find **10 different companies** exporting from Poland to the UK.")

# Function to check if a website contains KRS or NIP
def is_valid_company_website(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return False

        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text().lower()

        # Check for KRS or NIP number pattern
        if "krs" in page_text or "nip" in page_text:
            return True
    except requests.RequestException:
        return False
    return False

# Button to search for companies
if st.session_state.search_count < 10:
    if st.button("Find 10 Companies 🚀"):
        params = {
            "q": QUERY,
            "engine": "google",
            "api_key": SERPAPI_KEY,
            "num": 50,  # Fetch more results to filter valid companies
            "hl": "pl",
        }

        try:
            response = requests.get(API_URL, params=params)
            response.raise_for_status()

            data = response.json()
            all_results = {result["link"] for result in data.get("organic_results", [])}

            # Remove government websites and previously found results
            non_gov_results = [url for url in all_results if ".gov.pl" not in url]
            new_results = list(set(non_gov_results) - st.session_state.previous_results)

            valid_companies = []
            st.write("🔄 **Scanning websites for company details...**")

            # Validate companies by checking for KRS or NIP
            for url in new_results:
                if len(valid_companies) >= 10:
                    break

                st.write(f"Checking: {url}...")
                time.sleep(1)  # Avoid overloading requests
                if is_valid_company_website(url):
                    valid_companies.append(url)

            if valid_companies:
                st.session_state.previous_results.update(valid_companies)
                st.session_state.search_count += 1
                st.success(f"✅ Found {len(valid_companies)} companies!")

                for company_url in valid_companies:
                    st.markdown(f"🔗 **[Company Website]({company_url})** – {company_url}")

            else:
                st.warning("No valid company websites found. Try again.")

        except requests.exceptions.RequestException as e:
            st.error(f"❌ Error fetching data: {e}")

else:
    st.error("🚫 You've reached the **10 searches limit** for this session.")
