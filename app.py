
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Placeholder for fetching live data (replace with real API calls)
def fetch_data():
    # Simulate 10Y yield and EUR/USD data for demonstration
    np.random.seed(42)
    dates = pd.date_range(datetime.now() - timedelta(days=365), periods=52, freq='W-FRI')
    yields = 1.5 + np.cumsum(np.random.normal(0, 0.05, len(dates)))
    eur_usd = 1.1 + np.cumsum(np.random.normal(0, 0.01, len(dates)))
    return pd.DataFrame({'Date': dates, '10Y Yield': yields, 'EUR/USD': eur_usd})

# Calculate Z-scores for the last 4 weeks
def calculate_signals(data):
    data['Z-Score'] = data['10Y Yield'].rolling(window=4).apply(
        lambda x: (x.iloc[-1] - x.mean()) / x.std(), raw=False
    )
    data['Signal'] = data['Z-Score'].apply(
        lambda z: 1 if z < -1 else -1 if z > 1 else 0
    )
    return data

# Streamlit app
st.title("Real-Time Trade Signal Indicator")

# Fetch and process data
data = fetch_data()
data = calculate_signals(data)

# Display data table
st.subheader("Latest Data")
st.dataframe(data.tail(10))

# Plot EUR/USD prices with signals
fig = go.Figure()
fig.add_trace(go.Scatter(x=data['Date'], y=data['EUR/USD'], mode='lines', name='EUR/USD'))

# Add buy signals
buy_signals = data[data['Signal'] == 1]
fig.add_trace(go.Scatter(
    x=buy_signals['Date'], 
    y=buy_signals['EUR/USD'], 
    mode='markers', 
    marker=dict(color='green', size=10), 
    name='Buy Signal'
))

# Add sell signals
sell_signals = data[data['Signal'] == -1]
fig.add_trace(go.Scatter(
    x=sell_signals['Date'], 
    y=sell_signals['EUR/USD'], 
    mode='markers', 
    marker=dict(color='red', size=10), 
    name='Sell Signal'
))

# Update layout
fig.update_layout(
    title="EUR/USD with Trade Signals",
    xaxis_title="Date",
    yaxis_title="EUR/USD Price",
    legend_title="Legend",
    template="plotly_white"
)

st.plotly_chart(fig)

# Alarm notifications
st.subheader("Trade Signal Alerts")
latest_signal = data.iloc[-1]
if latest_signal['Signal'] == 1:
    st.success(f"Buy Signal detected on {latest_signal['Date'].date()} at EUR/USD: {latest_signal['EUR/USD']:.4f}")
elif latest_signal['Signal'] == -1:
    st.error(f"Sell Signal detected on {latest_signal['Date'].date()} at EUR/USD: {latest_signal['EUR/USD']:.4f}")
else:
    st.info("No trade signal at the moment.")
