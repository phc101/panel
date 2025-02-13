import streamlit as st
import requests
import random

# SerpAPI Key
SERPAPI_KEY = "e9626f65ccba8349ed8f9a3b9fbb448092d151f7d8998df5a8bc4c354c85e31a"

# Google search query for Polish (.pl) exporters to the UK
QUERY = "site:.pl export to UK OR eksport do UK OR eksport Wielka Brytania"

# SerpAPI endpoint
API_URL = "https://serpapi.com/search.json"

# Set session state for tracking searches
if "search_count" not in st.session_state:
    st.session_state.search_count = 0
if "previous_results" not in st.session_state:
    st.session_state.previous_results = set()

st.title("🔍 Find Polish Exporters to the UK")
st.write("Click the button below to find **10 different companies** exporting from Poland to the UK.")

# Button to search for companies
if st.session_state.search_count < 10:
    if st.button("Find 10 Companies 🚀"):
        params = {
            "q": QUERY,
            "engine": "google",
            "api_key": SERPAPI_KEY,
            "num": 50,  # Fetch more to avoid duplicates
            "hl": "pl",
        }

        try:
            response = requests.get(API_URL, params=params)
            response.raise_for_status()

            data = response.json()
            all_results = {result["link"] for result in data.get("organic_results", [])}

            # Remove previously found results to avoid duplicates
            new_results = list(all_results - st.session_state.previous_results)

            if len(new_results) >= 10:
                selected_results = random.sample(new_results, 10)
            else:
                selected_results = new_results  # Show whatever remains

            # Update session state to prevent duplicates in future searches
            st.session_state.previous_results.update(selected_results)
            st.session_state.search_count += 1

            if selected_results:
                st.success(f"✅ Found {len(selected_results)} companies!")
                for url in selected_results:
                    st.markdown(f"🔗 [Company Website]({url})")
            else:
                st.warning("No new companies found. Try again later.")

        except requests.exceptions.RequestException as e:
            st.error(f"❌ Error fetching data: {e}")

else:
    st.error("🚫 You've reached the **10 searches limit** for this session.")

