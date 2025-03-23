import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="USD/PLN Forward Rates", layout="wide")
st.title("📈 Live USD/PLN Forward Rates (from GitHub CSV)")

# 🔗 Replace with your actual GitHub raw CSV URL
csv_url = "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/usdpln_forward_rates.csv"

# Load CSV
try:
    df = pd.read_csv(csv_url)
    st.success("✅ Data loaded from GitHub")
except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
    st.stop()

# Show table
st.subheader("📊 Raw Forward Points Table")
st.dataframe(df, use_container_width=True)

# Plot chart
st.subheader("📈 Forward Curve (Bid & Ask in Pips)")
fig, ax = plt.subplots(figsize=(12, 6))
ax.bar(df["Tenor"], df["Bid (pips)"], width=0.4, label="Bid")
ax.bar(df["Tenor"], df["Ask (pips)"], width=0.4, label="Ask", align='edge')
ax.set_ylabel("Forward Points (pips)")
ax.set_title("USD/PLN Forward Curve (Bid vs Ask)")
ax.legend()
plt.xticks(rotation=45)
st.pyplot(fig)

# Footer
st.caption("Data source: Investing.com (scraped locally & synced via GitHub)")
