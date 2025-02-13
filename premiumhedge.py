import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
import tldextract

# SerpAPI Key (Replace with your actual key)
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

st.title("🔍 Find Polish Exporters to the UK")
st.write("Select an industry and click the button to find **10 different Polish exporters**.")

# Dropdown to select an industry
industry = st.selectbox("Select Industry", list(INDUSTRY_OPTIONS.keys()))

# Function to extract the main domain from a URL
def get_domain(url):
    ext = tldextract.extract(url)
    return f"{ext.domain}.{ext.suffix}"

# Function to check if a website is a real exporter
def is_valid_company_website(url):
    try:
        response = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            return False

        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text().lower()

        # Check for KRS or NIP number
        has_krs_or_nip = "krs" in page_text or "nip" in page_text

        # Check for English flag icon (common indicator of export businesses)
        has_english_flag = any(flag in response.text for flag in ["🇬🇧", "flag-en", "icon-uk", "flag_uk", "english"])

        # Check for "O nas" tab (indicating a real Polish business page)
        has_about_tab = "o nas" in page_text or "onas" in page_text

        return has_krs_or_nip and has_english_flag and has_about_tab

    except requests.RequestException:
        return False
    return False

# Button to search for companies
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

        # Remove unwanted sites (news, directories, government, blogs)
        filtered_results = [
            url for url in all_results if 
            not any(bad in url for bad in ["news", "blog", "directory", "aleo.com", "panoramafirm.pl", ".gov.pl"])
        ]

        valid_companies = []
        seen_domains = set()

        st.write("🔄 **Scanning websites for company details...**")

        # Validate companies by checking KRS/NIP, English flag, and "O nas"
        for url in filtered_results:
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
            st.success(f"✅ Found {len(valid_companies)} companies in {industry}!")

            for company_url in valid_companies:
                st.markdown(f"🔗 **[Company Website]({company_url})** – {company_url}")

        else:
            st.warning(f"No valid {industry} company websites found. Try again.")

    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error fetching data: {e}")
