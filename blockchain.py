# main.py
import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

st.set_page_config(page_title="USD/PLN Forward Rates", layout="wide")
st.title("📈 USD/PLN Forward Rates (in pips)")

@st.cache_data(ttl=3600)
def scrape_forward_rates():
    st.write("Scraped columns:", df.columns)
st.write(df)

    url = "https://www.investing.com/currencies/usd-pln-forward-rates"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")

    table = soup.find("table", {"class": "genTbl closedTbl crossRatesTbl"})
    rows = table.find_all("tr")[1:]

    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        name = cols[0].text.strip()
        try:
            bid = float(cols[1].text.strip().replace(",", "")) / 10000
            ask = float(cols[2].text.strip().replace(",", "")) / 10000
        except ValueError:
            continue
        change = cols[3].text.strip()
        data.append({
            "Tenor": name,
            "Bid (pips)": bid,
            "Ask (pips)": ask,
            "Change": change
        })

    return pd.DataFrame(data)

# Run scraper
df = scrape_forward_rates()
st.dataframe(df, use_container_width=True)

# Plot
fig, ax = plt.subplots(figsize=(12, 6))
x = df["Tenor"]
ax.bar(x, df["Bid (pips)"], width=0.4, label="Bid (pips)", align='center')
ax.bar(x, df["Ask (pips)"], width=0.4, label="Ask (pips)", align='edge')
plt.xticks(rotation=45, ha='right')
ax.set_ylabel("Forward Points (pips)")
ax.set_title("USD/PLN Forward Curve")
ax.legend()
st.pyplot(fig)
