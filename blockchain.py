import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

st.set_page_config(page_title="USD/PLN Forward Rates", layout="wide")
st.title("📈 USD/PLN Forward Rates (in pips)")

@st.cache_data(ttl=3600)
def scrape_forward_rates():
    url = "https://www.investing.com/currencies/usd-pln-forward-rates"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        st.error(f"❌ Failed to fetch data. Status code: {response.status_code}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", {"class": "genTbl closedTbl crossRatesTbl"})

    if table is None:
        st.error("❌ Could not find forward rate table.")
        return pd.DataFrame()

    rows = table.find_all("tr")[1:]
    data = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        try:
            tenor = cols[0].text.strip()
            bid = float(cols[1].text.strip().replace(",", "")) / 10000
            ask = float(cols[2].text.strip().replace(",", "")) / 10000
            change = cols[3].text.strip()
            data.append({
                "Tenor": tenor,
                "Bid (pips)": bid,
                "Ask (pips)": ask,
                "Change": change
            })
        except:
            continue

    return pd.DataFrame(data)

# Fetch data
df = scrape_forward_rates()

# Debugging helper
if df.empty:
    st.warning("⚠️ No data was returned. Please check the source or structure.")
else:
    st.write("✅ Scraped Columns:", df.columns)
    st.dataframe(df)

    # Plot chart
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(df["Tenor"], df["Bid (pips)"], label="Bid", width=0.4)
    ax.bar(df["Tenor"], df["Ask (pips)"], label="Ask", width=0.4, align='edge')
    ax.set_ylabel("Forward Points (pips)")
    ax.set_title("USD/PLN Forward Curve")
    plt.xticks(rotation=45)
    ax.legend()
    st.pyplot(fig)
