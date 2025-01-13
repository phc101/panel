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
        "Tenor": ["1M", "3M", "6M", "1Y"],
        "Forward Rate": [4.5678, 4.6012, 4.6500, 4.7200],
    }
    df = pd.DataFrame(data)
    return df

def plot_forward_rates(df):
    """Plot forward rates."""
    fig, ax = plt.subplots()
    ax.plot(df["Tenor"], df["Forward Rate"], marker="o")
    ax.set_title("EUR/PLN Forward Rates")
    ax.set_xlabel("Tenor")
    ax.set_ylabel("Forward Rate")
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

    st.write("### Forward Rates Chart")
    chart = plot_forward_rates(df)
    st.pyplot(chart)

if __name__ == "__main__":
    main()
