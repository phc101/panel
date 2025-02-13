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
def is_valid_company
