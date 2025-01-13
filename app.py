import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

def fetch_forward_rates():
    """Fetch forward rates data from Investing.com."""
    url = "https://pl.investing.com/currencies/eur-pln-forward-rates"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        table = soup.find("table", {"class": "genTbl closedTbl forward_ratesTbl"})
        rows = table.find_all("tr")

        data = {"Tenor": [], "Bid": [], "Ask": []}

        for row in rows[1:]:  # Skip the header row
            cells = row.find_all("td")
            if len(cells) >= 3:
                data["Tenor"].append(cells[0].text.strip())
                data["Bid"].append(float(cells[1].text.strip().replace(',', '')))
                data["Ask"].append(float(cells[2].text.strip().replace(',', '')))

        df = pd.DataFrame(data)

    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        df = pd.DataFrame({"Tenor": [], "Bid": [], "Ask": []})

    return df

def plot_bid_rates(df):
    """Plot bid rates."""
    if "Bid" not in df.columns:
        st.error("'Bid' column is missing in the data.")
        return None

    fig, ax = plt.subplots()
    ax.plot(df["Tenor"], df["Bid"], marker="o", label="Bid")
    ax.set_title("EUR/PLN Bid Points")
    ax.set_xlabel("Tenor")
    ax.set_ylabel("Rate")
    ax.legend()
    return fig

def plot_ask_rates(df):
    """Plot ask rates."""
    if "Ask" not in df.columns:
        st.error("'Ask' column is missing in the data.")
        return None

    fig, ax = plt.subplots()
    ax.plot(df["Tenor"], df["Ask"], marker="o", label="Ask")
    ax.set_title("EUR/PLN Ask Points")
    ax.set_xlabel("Tenor")
    ax.set_ylabel("Rate")
    ax.legend()
    return fig

def main():
    st.title("EUR/PLN Forward Rates")

    st.sidebar.header("Options")
    refresh = st.sidebar.button("Refresh Data")

    if refresh or "data" not in st.session_state:
        with st.spinner("Fetching forward rates..."):
            df = fetch_forward_rates()
            st.session_state["data"] = df
    else:
        df = st.session_state["data"]

    st.write("### Forward Rates Data")
    st.write("Debugging DataFrame:", df)  # Debugging output
    st.dataframe(df)

    st.write("### Bid Points Chart")
    bid_chart = plot_bid_rates(df)
    if bid_chart:
        st.pyplot(bid_chart)

    st.write("### Ask Points Chart")
    ask_chart = plot_ask_rates(df)
    if ask_chart:
        st.pyplot(ask_chart)

if __name__ == "__main__":
    main()
