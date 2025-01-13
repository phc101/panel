import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

def fetch_forward_rates():
    """Fetch forward rates data from FX Empire or other sources."""
    url = "https://www.fxempire.com/currencies/eur-pln/forward-rates"
    # Example: If FX Empire has an API or returns JSON, parse accordingly
    # response = requests.get(url)
    # forward_rates = response.json() or pd.read_html(response.text)[0]
    # For simplicity, replace this with your data-fetching logic.

    # Simulating data
    data = {
        "Tenor": ["1M", "3M", "6M", "1Y", "2Y", "5Y"],
        "Bid": [4.5500, 4.5800, 4.6200, 4.6900, 4.8000, 5.0000],
        "Ask": [4.5700, 4.6000, 4.6400, 4.7100, 4.8200, 5.0200],
    }
    df = pd.DataFrame(data)
    return df

def plot_bid_rates(df):
    """Plot bid rates."""
    fig, ax = plt.subplots()
    ax.plot(df["Tenor"], df["Bid"], marker="o", label="Bid")
    ax.set_title("EUR/PLN Bid Points")
    ax.set_xlabel("Tenor")
    ax.set_ylabel("Rate")
    ax.legend()
    return fig

def plot_ask_rates(df):
    """Plot ask rates."""
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
    st.dataframe(df)

    st.write("### Bid Points Chart")
    bid_chart = plot_bid_rates(df)
    st.pyplot(bid_chart)

    st.write("### Ask Points Chart")
    ask_chart = plot_ask_rates(df)
    st.pyplot(ask_chart)

if __name__ == "__main__":
    main()
