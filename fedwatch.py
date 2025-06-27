import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta
import io

# Page configuration
st.set_page_config(
    page_title="Exchange Rate Simulator",
    page_icon="💱",
    layout="wide"
)

# Load data function
@st.cache_data
def load_data():
    data = """date,year,month,inflation_rate,nbp_reference_rate,real_interest_rate,eur_pln,usd_pln,gbp_pln
2014-01,2014,1,0.5,2.50,1.99,4.1776,3.0650,5.0507
2015-01,2015,1,-1.4,2.00,3.45,4.2538,3.6403,5.4537
2020-05,2020,5,3.4,0.10,-3.19,4.4584,4.0408,4.9519
2022-05,2022,5,13.5,5.25,-7.43,4.5691,4.2608,5.3329
2024-12,2024,12,4.7,5.75,0.98,4.2714,4.0787,5.1535
2025-05,2025,5,4.0,5.25,1.20,4.2600,4.0300,5.1000"""
    return pd.read_csv(io.StringIO(data))

# Load data
df = load_data()

# Title
st.title("💱 Exchange Rate Simulator")

# Sidebar
st.sidebar.header("Controls")

# Input current rates
current_eur = st.sidebar.number_input("EUR/PLN", value=4.27, format="%.4f")
current_usd = st.sidebar.number_input("USD/PLN", value=4.08, format="%.4f")
current_gbp = st.sidebar.number_input("GBP/PLN", value=5.15, format="%.4f")

# Input parameters
inflation_rate = st.sidebar.slider("Inflation (%)", -3.0, 15.0, 4.0, 0.1)
nominal_rate = st.sidebar.slider("NBP Rate (%)", 0.0, 12.0, 5.75, 0.25)
time_horizon = st.sidebar.slider("Months", 3, 24, 12)

# Calculate real rate
real_rate = ((1 + nominal_rate/100) / (1 + inflation_rate/100) - 1) * 100

st.sidebar.markdown(f"**Real Rate: {real_rate:.2f}%**")

# Prediction function
def predict_rates(real_rate, current_rates):
    sensitivity = {"EUR": -0.12, "USD": -0.18, "GBP": -0.15}
    uncertainty = {"EUR": 0.03, "USD": 0.05, "GBP": 0.04}
    
    results = {}
    for currency in current_rates:
        impact = (real_rate - 0.98) * sensitivity[currency]
        central = current_rates[currency] + impact
        
        model_std = uncertainty[currency] * central
        p25 = central - 0.67 * model_std
        p75 = central + 0.67 * model_std
        
        change = ((central - current_rates[currency]) / current_rates[currency]) * 100
        
        results[currency] = {
            "central": central,
            "p25": p25,
            "p75": p75,
            "change": change,
            "current": current_rates[currency]
        }
    
    return results

# Get predictions
current_rates = {"EUR": current_eur, "USD": current_usd, "GBP": current_gbp}
predictions = predict_rates(real_rate, current_rates)

# Display predictions
st.markdown("## Predictions")

col1, col2, col3 = st.columns(3)
currencies = ["EUR", "USD", "GBP"]
colors = ["blue", "green", "red"]

for i, currency in enumerate(currencies):
    with [col1, col2, col3][i]:
        pred = predictions[currency]
        st.metric(
            f"{currency}/PLN",
            f"{pred['central']:.4f}",
            f"{pred['change']:+.1f}%"
        )
        st.write(f"Range: {pred['p25']:.4f} - {pred['p75']:.4f}")

# Time series chart
st.markdown("## Forecast")

dates = [datetime.now() + timedelta(days=30*i) for i in range(time_horizon + 1)]
projection_data = []

for i, date in enumerate(dates):
    adjustment = min(i / 6, 1)
    projection_data.append({
        "Month": i,
        "EUR": current_eur + (predictions["EUR"]["central"] - current_eur) * adjustment,
        "USD": current_usd + (predictions["USD"]["central"] - current_usd) * adjustment,
        "GBP": current_gbp + (predictions["GBP"]["central"] - current_gbp) * adjustment
    })

df_proj = pd.DataFrame(projection_data)

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_proj["Month"], y=df_proj["EUR"], name="EUR/PLN", line=dict(color="blue")))
fig.add_trace(go.Scatter(x=df_proj["Month"], y=df_proj["USD"], name="USD/PLN", line=dict(color="green")))
fig.add_trace(go.Scatter(x=df_proj["Month"], y=df_proj["GBP"], name="GBP/PLN", line=dict(color="red")))

fig.update_layout(
    title="Exchange Rate Forecast",
    xaxis_title="Months",
    yaxis_title="Rate (PLN)",
    height=400
)

st.plotly_chart(fig, use_container_width=True)

# Historical data
st.markdown("## Historical Data")
st.dataframe(df)

st.markdown("---")
st.markdown("**Model**: Real rate sensitivity with uncertainty bands")
st.markdown("**Formula**: Real Rate = (1 + nominal) / (1 + inflation) - 1")
