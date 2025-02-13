import streamlit as st
import requests
import random
import time
from bs4 import BeautifulSoup
import tldextract

# SerpAPI Key (replace with your key)
SERPAPI_KEY = "e9626f65ccba8349ed8f9a3b9fbb448092d151f7d8998df5a8bc4c354c85e31a"

# Industry filter dictionary
INDUSTRY_OPTIONS = {
    "Manufacturing": "manufacturing OR produkcja OR fabryka OR zakład produkcyjny",
    "Food & Beverages": "food OR beverages OR żywność OR napoje OR eksport żywności",
    "Automotive": "automotive OR car parts OR motoryzacja OR części samochodowe OR pojazdy",
    "Textiles": "textiles OR clothing OR odzież OR tkaniny OR moda OR produkcja odzieży",
    "Chemicals": "chemicals OR chemical industry OR chemia OR przemysł chemiczny OR substancje chemiczne",
    "Electronics": "electronics OR electrical components OR elektronika OR sprzęt elektryczny"
}

# SerpAPI endpoint
API_URL = "https://serpapi.com/search.json"

# Set session state to track searches and previous results
if "search_count" not in st.session_state:
    st.session_state.search_count = 0
if "previous_results" not in st.session_state:
    st.session_state.previous_results = set()

st.title("🔍 Find Polish Exporters to the UK")
st.write("Select an industry and click the button to find **10 different Polish exporters**.")

# Dropdown to select an industry
industry = st.selectbox("Select Industry", list(INDUSTRY_OPTIONS.keys()))

# Function to check if a website contains KRS or NIP (indicating a real business)
def is_valid_company_website(url):
    try:
        response = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            return False

        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text().lower()

        # Check for KRS or NIP number (business registration)
        if "krs" in page_text or "nip" in page_text:
            return True
    except requests.RequestException:
        return False
    return False

# Function to extract the main domain from a URL
def get_domain(url):
    ext = tldextract.extract(url)
    return f"{ext.domain}.{ext.suffix}"

# Button to search for companies
if st.session_state.search_count < 10:
    if st.button("Find 10 Companies 🚀"):
        query = f"site:.pl export to UK OR eksport do UK OR eksport Wielka Brytania {INDUSTRY_OPTIONS[industry]}"
        
        params = {
            "q": query,
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

            # Remove government websites, news articles, and previously found results
            non_gov_results = [
                url for url in all_results if ".gov.pl" not in url and "news" not in url and "blog" not in url
            ]
            new_results = list(set(non_gov_results) - st.session_state.previous_results)

            valid_companies = []
            seen_domains = set()

            st.write("🔄 **Scanning websites for company details...**")

            # Validate companies by checking for KRS or NIP
            for url in new_results:
                if len(valid_companies) >= 10:
                    break  # Stop at exactly 10 companies

                domain = get_domain(url)

                if domain in seen_domains:
                    continue  # Skip duplicate domains

                st.write(f"Checking: {url}...")
                
                if is_valid_company_website(url):
                    valid_companies.append(url)
                    seen_domains.add(domain)  # Track domain to avoid duplicates

            if valid_companies:
                st.session_state.previous_results.update(valid_companies)
                st.session_state.search_count += 1
                st.success(f"✅ Found {len(valid_companies)} companies in {industry}!")

                for company_url in valid_companies:
                    st.markdown(f"🔗 **[Company Website]({company_url})** – {company_url}")

            else:
                st.warning(f"No valid {industry} company websites found. Try again.")

        except requests.exceptions.RequestException as e:
            st.error(f"❌ Error fetching data: {e}")

else:
    st.error("🚫 You've reached the **10 searches limit** for this session.")
