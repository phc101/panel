import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="USD/PLN Forward Rates", layout="wide")
st.title("📈 USD/PLN Forward Rates (in pips)")

@st.cache_data(ttl=3600)
def scrape_with_selenium():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

    url = "https://www.investing.com/currencies/usd-pln-forward-rates"
    driver.get(url)
    time.sleep(5)  # Allow JS to load the table

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    table = soup.find("table", {"class": "genTbl closedTbl crossRatesTbl"})
    if table is None:
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

df = scrape_with_selenium()

if df.empty:
    st.warning("⚠️ No data found. The table might not have loaded.")
else:
    st.dataframe(df, use_container_width=True)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(df["Tenor"], df["Bid (pips)"], label="Bid", width=0.4)
    ax.bar(df["Tenor"], df["Ask (pips)"], label="Ask", width=0.4, align='edge')
    plt.xticks(rotation=45)
    ax.set_ylabel("Forward Points (pips)")
    ax.set_title("USD/PLN Forward Curve")
    ax.legend()
    st.pyplot(fig)
    import subprocess

subprocess.run(["git", "add", "usdpln_forward_rates.csv"])
subprocess.run(["git", "commit", "-m", "Update forward rates"])
subprocess.run(["git", "push", "origin", "main"])

