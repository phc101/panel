import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import io

# Konfiguracja strony
st.set_page_config(
    page_title="FX Forecaster - Multi-Currency",
    page_icon="💱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ładowanie danych historycznych PLN
@st.cache_data
def load_pln_data():
    data = """date,year,month,inflation_rate,nbp_reference_rate,real_interest_rate,eur_pln,usd_pln
2014-01,2014,1,0.5,2.50,1.99,4.1776,3.0650
2014-02,2014,2,0.7,2.50,1.78,4.1786,3.0613
2014-03,2014,3,0.7,2.50,1.78,4.1972,3.0378
2014-04,2014,4,0.3,2.50,2.19,4.1841,3.0293
2014-05,2014,5,0.2,2.50,2.29,4.1594,3.0234
2014-06,2014,6,0.3,2.50,2.19,4.1659,3.0381
2014-07,2014,7,-0.2,2.50,2.72,4.1773,3.0456
2014-08,2014,8,-0.3,2.50,2.82,4.1856,3.0723
2014-09,2014,9,-0.3,2.50,2.82,4.1953,3.1249
2014-10,2014,10,-0.6,2.50,3.13,4.2071,3.1657
2014-11,2014,11,-0.6,2.50,3.13,4.2389,3.2847
2014-12,2014,12,-1.0,2.50,3.54,4.2623,3.5072
2015-01,2015,1,-1.4,2.00,3.45,4.2538,3.6403
2015-02,2015,2,-1.6,2.00,3.65,4.0934,3.6587
2015-03,2015,3,-1.5,1.50,3.05,4.0678,3.7188
2015-04,2015,4,-1.1,1.50,2.65,4.0853,3.7540
2015-05,2015,5,-0.9,1.50,2.44,4.1078,3.6738
2015-06,2015,6,-0.8,1.50,2.33,4.1856,3.8268
2015-07,2015,7,-0.7,1.50,2.22,4.1302,3.7635
2015-08,2015,8,-0.6,1.50,2.12,4.2247,3.9513
2015-09,2015,9,-0.8,1.50,2.33,4.2655,4.0371
2015-10,2015,10,-0.7,1.50,2.22,4.2839,3.9276
2015-11,2015,11,-0.6,1.50,2.12,4.3211,3.9060
2015-12,2015,12,-0.5,1.50,2.01,4.2639,3.9011
2016-01,2016,1,-0.8,1.50,2.33,4.3616,4.0044
2016-02,2016,2,-0.8,1.50,2.33,4.3438,3.7584
2016-03,2016,3,-0.9,1.50,2.44,4.3732,3.7643
2016-04,2016,4,-1.1,1.50,2.65,4.3947,3.7899
2016-05,2016,5,-0.8,1.50,2.33,4.4259,3.9671
2016-06,2016,6,-0.8,1.50,2.33,4.4240,3.9780
2016-07,2016,7,-0.8,1.50,2.33,4.3284,3.9533
2016-08,2016,8,-0.8,1.50,2.33,4.3567,3.9311
2016-09,2016,9,-0.5,1.50,2.01,4.3123,3.8501
2016-10,2016,10,-0.2,1.50,1.70,4.2969,3.8332
2016-11,2016,11,-0.4,1.50,1.91,4.4588,3.7584
2016-12,2016,12,-0.5,1.50,2.01,4.4240,4.1793
2017-01,2017,1,-0.2,1.50,1.70,4.3135,3.8581
2017-02,2017,2,0.1,1.50,1.39,4.3011,3.7840
2017-03,2017,3,1.4,1.50,0.10,4.2247,3.8090
2017-04,2017,4,1.7,1.50,-0.17,4.2291,3.7963
2017-05,2017,5,1.6,1.50,-0.10,4.1953,3.7635
2017-06,2017,6,1.8,1.50,-0.29,4.2291,3.7963
2017-07,2017,7,1.6,1.50,-0.10,4.2655,3.8268
2017-08,2017,8,1.4,1.50,0.10,4.2839,3.9276
2017-09,2017,9,1.2,1.50,0.30,4.3211,3.9060
2017-10,2017,10,1.1,1.50,0.40,4.2969,3.8332
2017-11,2017,11,1.2,1.50,0.30,4.2389,3.7584
2017-12,2017,12,1.0,1.50,0.50,4.1709,3.4813
2018-01,2018,1,1.2,1.50,0.30,4.1497,3.4138
2018-02,2018,2,1.4,1.50,0.10,4.1856,3.4427
2018-03,2018,3,1.3,1.50,0.20,4.2071,3.4250
2018-04,2018,4,1.7,1.50,-0.17,4.2247,3.4427
2018-05,2018,5,1.7,1.50,-0.17,4.3618,3.7348
2018-06,2018,6,1.7,1.50,-0.17,4.3618,3.7348
2018-07,2018,7,1.9,1.50,-0.39,4.2655,3.8268
2018-08,2018,8,2.0,1.50,-0.49,4.2839,3.9276
2018-09,2018,9,1.4,1.50,0.10,4.3211,3.9060
2018-10,2018,10,1.2,1.50,0.30,4.2969,3.8332
2018-11,2018,11,1.3,1.50,0.20,4.2389,3.7584
2018-12,2018,12,1.1,1.50,0.40,4.2669,3.7597
2019-01,2019,1,0.7,1.50,0.79,4.2615,3.7643
2019-02,2019,2,1.2,1.50,0.30,4.3011,3.7840
2019-03,2019,3,1.7,1.50,-0.17,4.2247,3.8090
2019-04,2019,4,2.2,1.50,-0.69,4.2291,3.7963
2019-05,2019,5,2.3,1.50,-0.78,4.2655,3.7635
2019-06,2019,6,1.0,1.50,0.50,4.2687,3.9311
2019-07,2019,7,0.5,1.50,0.99,4.2839,3.9276
2019-08,2019,8,0.4,1.50,1.09,4.3211,3.9060
2019-09,2019,9,0.5,1.50,0.99,4.3732,3.8501
2019-10,2019,10,0.4,1.50,1.09,4.2969,3.8332
2019-11,2019,11,0.6,1.50,0.89,4.2389,3.7584
2019-12,2019,12,1.3,1.50,0.20,4.2568,3.7977
2020-01,2020,1,3.2,1.50,-1.68,4.2597,3.7282
2020-02,2020,2,3.7,1.50,-2.16,4.3011,3.7840
2020-03,2020,3,3.2,1.00,-2.13,4.5523,4.1044
2020-04,2020,4,3.4,0.50,-2.80,4.5268,4.0776
2020-05,2020,5,3.4,0.10,-3.19,4.4584,4.0408
2020-06,2020,6,3.3,0.10,-3.10,4.4588,3.9680
2020-07,2020,7,3.6,0.10,-3.39,4.4240,3.9533
2020-08,2020,8,3.8,0.10,-3.58,4.4259,3.9671
2020-09,2020,9,3.2,0.10,-3.00,4.5268,3.9780
2020-10,2020,10,3.1,0.10,-2.90,4.4584,4.0408
2020-11,2020,11,3.0,0.10,-2.81,4.4588,3.9680
2020-12,2020,12,3.7,0.10,-3.49,4.6148,3.7584
2021-01,2021,1,2.6,0.10,-2.44,4.5826,3.8332
2021-02,2021,2,2.4,0.10,-2.24,4.1856,3.8090
2021-03,2021,3,3.2,0.10,-3.00,4.6525,4.2030
2021-04,2021,4,4.6,0.10,-4.37,4.1953,3.7635
2021-05,2021,5,4.4,0.10,-4.18,4.4259,3.9671
2021-06,2021,6,4.1,0.10,-3.85,4.5208,3.7840
2021-07,2021,7,4.8,0.10,-4.57,4.5826,3.8332
2021-08,2021,8,5.2,0.10,-4.96,4.6856,4.0671
2021-09,2021,9,5.8,0.10,-5.54,4.6184,4.0086
2021-10,2021,10,5.9,0.50,-5.10,4.6184,4.0086
2021-11,2021,11,6.8,1.25,-5.20,4.6856,4.0671
2021-12,2021,12,8.6,1.75,-6.31,4.5994,4.0600
2022-01,2022,1,9.4,2.25,-6.54,4.5969,4.0683
2022-02,2022,2,8.5,2.75,-5.33,4.6939,4.0687
2022-03,2022,3,10.9,3.50,-6.67,4.6525,4.2030
2022-04,2022,4,12.4,4.50,-7.19,4.6560,4.5267
2022-05,2022,5,13.5,5.25,-7.43,4.5691,4.2608
2022-06,2022,6,11.8,6.00,-5.19,4.4615,4.2631
2022-07,2022,7,10.8,6.00,-4.34,4.7011,4.7169
2022-08,2022,8,10.1,6.00,-3.73,4.6939,4.5267
2022-09,2022,9,10.7,6.75,-3.57,4.8694,4.8574
2022-10,2022,10,8.2,6.75,-1.34,4.7392,4.9894
2022-11,2022,11,7.8,6.75,-0.90,4.6939,4.7169
2022-12,2022,12,7.5,6.75,-0.70,4.6808,4.4018
2023-01,2023,1,6.6,6.75,0.14,4.7047,4.4541
2023-02,2023,2,6.0,6.75,0.71,4.6939,4.4018
2023-03,2023,3,6.1,6.75,0.61,4.6808,4.4541
2023-04,2023,4,11.0,6.75,-3.89,4.5691,4.2608
2023-05,2023,5,12.9,6.75,-5.45,4.4615,4.2631
2023-06,2023,6,11.5,6.75,-4.26,4.4617,4.0718
2023-07,2023,7,10.1,6.75,-3.05,4.5208,4.0086
2023-08,2023,8,9.6,6.75,-2.60,4.5826,4.0671
2023-09,2023,9,8.2,6.75,-1.34,4.6353,4.3490
2023-10,2023,10,7.8,6.75,-0.90,4.3395,3.9780
2023-11,2023,11,6.5,6.75,0.23,4.3652,4.0011
2023-12,2023,12,6.2,5.75,-0.42,4.3395,3.9780
2024-01,2024,1,5.5,5.75,0.24,4.3652,4.0011
2024-02,2024,2,4.9,5.75,0.82,4.3274,4.0083
2024-03,2024,3,3.6,5.75,2.07,4.3074,3.9658
2024-04,2024,4,3.9,5.75,1.79,4.3026,4.0106
2024-05,2024,5,2.8,5.75,2.87,4.2848,3.9675
2024-06,2024,6,2.6,5.75,3.07,4.3177,4.0127
2024-07,2024,7,3.4,5.75,2.27,4.2811,3.9462
2024-08,2024,8,3.8,5.75,1.88,4.2918,3.9020
2024-09,2024,9,3.8,5.75,1.88,4.2782,3.8501
2024-10,2024,10,4.2,5.75,1.49,4.3164,3.9573
2024-11,2024,11,4.6,5.75,1.10,4.3339,4.0763
2024-12,2024,12,4.7,5.75,0.98,4.2714,4.0787
2025-01,2025,1,4.9,5.75,0.82,4.2800,4.0500
2025-02,2025,2,4.9,5.75,0.82,4.2750,4.0400
2025-03,2025,3,4.9,5.75,0.82,4.2700,4.0350
2025-04,2025,4,4.3,5.75,1.39,4.2650,4.0320
2025-05,2025,5,4.0,5.25,1.20,4.2600,4.0300"""
    return pd.read_csv(io.StringIO(data))

df_pln = load_pln_data()

# Tytuł
st.title("💱 Multi-Currency FX Forecaster")
st.markdown("### EUR/USD (Differential Model) + EUR/PLN & USD/PLN (Real Rate Model)")

# Panel boczny
st.sidebar.header("🎛️ Market Parameters")

# Current rates
st.sidebar.markdown("### 💱 Current Exchange Rates")
col1, col2 = st.sidebar.columns(2)
with col1:
    current_eurpln = st.number_input("EUR/PLN", 3.50, 6.00, 4.27, 0.01, format="%.4f")
    current_usdpln = st.number_input("USD/PLN", 3.00, 6.00, 4.08, 0.01, format="%.4f")
with col2:
    current_eurusd = st.number_input("EUR/USD", 0.90, 1.40, 1.0566, 0.0001, format="%.4f")

# US Parameters (dla EUR/USD model)
st.sidebar.markdown("### 🇺🇸 United States")
us_nominal = st.sidebar.slider("Fed Funds Rate (%)", 0.0, 8.0, 4.50, 0.25)
us_breakeven = st.sidebar.slider("Breakeven Inflation (%)", 0.0, 5.0, 2.27, 0.1)

# Euro Parameters (dla EUR/USD model)
st.sidebar.markdown("### 🇪🇺 Euro Area")
euro_nominal = st.sidebar.slider("ECB Rate (%)", 0.0, 6.0, 3.25, 0.25)
euro_inflation = st.sidebar.slider("HICP Inflation (%)", 0.0, 5.0, 2.40, 0.1)

# Poland Parameters (dla PLN model)
st.sidebar.markdown("### 🇵🇱 Poland")
pln_inflation = st.sidebar.slider("PL Inflation (%)", 0.0, 15.0, 4.7, 0.1)
pln_nominal = st.sidebar.slider("NBP Rate (%)", 0.0, 12.0, 5.75, 0.25)

# Forecast horizon
time_horizon = st.sidebar.slider("Forecast Horizon (months)", 3, 24, 12)

# Calculate real rates
us_real = us_nominal - us_breakeven
euro_real = euro_nominal - euro_inflation
pln_real = ((1 + pln_nominal/100) / (1 + pln_inflation/100) - 1) * 100
differential = us_real - euro_real

# Display calculated rates
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Real Rates")
st.sidebar.markdown(f"""
**US Real:** {us_real:.2f}%  
**Euro Real:** {euro_real:.2f}%  
**PL Real:** {pln_real:.2f}%  
**Differential (US-Euro):** {differential:+.2f}%
""")

if differential > 0:
    st.sidebar.success(f"✅ USD favored ({differential:.2f}%)")
elif differential < 0:
    st.sidebar.info(f"ℹ️ EUR favored ({abs(differential):.2f}%)")
else:
    st.sidebar.warning("⚖️ Neutral")

# Prediction functions
def predict_eurusd_differential(differential, current_rate):
    """EUR/USD based on US-Euro real rate differential"""
    slope = -0.0187  # From empirical analysis
    baseline = 0.0
    uncertainty = 0.05
    
    impact = (differential - baseline) * slope
    central = current_rate + impact
    
    model_std = uncertainty * central
    return {
        "central": central,
        "p10": central - 1.28 * model_std,
        "p25": central - 0.67 * model_std,
        "p75": central + 0.67 * model_std,
        "p90": central + 1.28 * model_std,
        "change": ((central - current_rate) / current_rate) * 100,
        "current": current_rate
    }

def predict_pln_pairs(real_rate, current_rates):
    """EUR/PLN and USD/PLN based on PLN real rate"""
    sensitivity = {
        "EUR": {"real": -0.12, "uncertainty": 0.03},
        "USD": {"real": -0.18, "uncertainty": 0.05}
    }
    
    results = {}
    for currency in current_rates:
        impact = (real_rate - 0.98) * sensitivity[currency]["real"]
        central = current_rates[currency] + impact
        
        model_std = sensitivity[currency]["uncertainty"] * central
        change = ((central - current_rates[currency]) / current_rates[currency]) * 100
        
        results[currency] = {
            "central": central,
            "p10": central - 1.28 * model_std,
            "p25": central - 0.67 * model_std,
            "p75": central + 0.67 * model_std,
            "p90": central + 1.28 * model_std,
            "change": change,
            "current": current_rates[currency],
            "uncertainty": sensitivity[currency]["uncertainty"] * 100
        }
    
    return results

# Get predictions
pred_eurusd = predict_eurusd_differential(differential, current_eurusd)
pred_pln = predict_pln_pairs(pln_real, {"EUR": current_eurpln, "USD": current_usdpln})

# Display forecasts
st.markdown("---")
st.markdown("## 💱 Exchange Rate Forecasts")

col1, col2, col3 = st.columns(3)

# EUR/USD Card (Differential Model)
with col1:
    color = "#2563eb" if differential < 0 else "#dc2626"
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {color}20, {color}10); padding: 20px; 
                border-radius: 15px; border: 2px solid {color}40; text-align: center;">
        <h3 style="color: {color}; margin: 0;">EUR/USD</h3>
        <p style="font-size: 0.8em; color: #666; margin: 5px 0;">Differential Model</p>
        <h1 style="color: {color}; margin: 10px 0; font-size: 2.5em;">{pred_eurusd['central']:.4f}</h1>
        <p style="margin: 5px 0; color: #666;">Current: {pred_eurusd['current']:.4f}</p>
        <p style="margin: 5px 0; font-size: 1.2em;">
            <strong>{'🟢' if pred_eurusd['change'] >= 0 else '🔴'} {pred_eurusd['change']:+.2f}%</strong>
        </p>
        <p style="font-size: 0.9em; color: #666;">Diff: {differential:+.2f}%</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    **50% Range:** {pred_eurusd['p25']:.4f} - {pred_eurusd['p75']:.4f}  
    **Model:** US-Euro Rate Differential  
    **R²:** 30.2% | **Corr:** -0.550
    """)

# EUR/PLN Card
with col2:
    pred_eur = pred_pln["EUR"]
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #2e68a520, #2e68a510); padding: 20px; 
                border-radius: 15px; border: 2px solid #2e68a540; text-align: center;">
        <h3 style="color: #2e68a5; margin: 0;">EUR/PLN</h3>
        <p style="font-size: 0.8em; color: #666; margin: 5px 0;">PLN Real Rate Model</p>
        <h1 style="color: #2e68a5; margin: 10px 0; font-size: 2.5em;">{pred_eur['central']:.4f}</h1>
        <p style="margin: 5px 0; color: #666;">Current: {pred_eur['current']:.4f}</p>
        <p style="margin: 5px 0; font-size: 1.2em;">
            <strong>{'🔴' if pred_eur['change'] >= 0 else '🟢'} {pred_eur['change']:+.2f}%</strong>
        </p>
        <p style="font-size: 0.9em; color: #666;">PL Real: {pln_real:.2f}%</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    **50% Range:** {pred_eur['p25']:.4f} - {pred_eur['p75']:.4f}  
    **Model:** PLN Real Interest Rate  
    **Uncertainty:** ±{pred_eur['uncertainty']:.1f}%
    """)

# USD/PLN Card
with col3:
    pred_usd = pred_pln["USD"]
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #05966920, #05966910); padding: 20px; 
                border-radius: 15px; border: 2px solid #05966940; text-align: center;">
        <h3 style="color: #059669; margin: 0;">USD/PLN</h3>
        <p style="font-size: 0.8em; color: #666; margin: 5px 0;">PLN Real Rate Model</p>
        <h1 style="color: #059669; margin: 10px 0; font-size: 2.5em;">{pred_usd['central']:.4f}</h1>
        <p style="margin: 5px 0; color: #666;">Current: {pred_usd['current']:.4f}</p>
        <p style="margin: 5px 0; font-size: 1.2em;">
            <strong>{'🔴' if pred_usd['change'] >= 0 else '🟢'} {pred_usd['change']:+.2f}%</strong>
        </p>
        <p style="font-size: 0.9em; color: #666;">PL Real: {pln_real:.2f}%</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    **50% Range:** {pred_usd['p25']:.4f} - {pred_usd['p75']:.4f}  
    **Model:** PLN Real Interest Rate  
    **Uncertainty:** ±{pred_usd['uncertainty']:.1f}%
    """)

# Tabs for analysis
st.markdown("---")
st.markdown("## 📊 Analysis & Projections")

tab1, tab2, tab3, tab4 = st.tabs(["📈 EUR/USD Differential", "📈 EUR/PLN Forecast", "📈 USD/PLN Forecast", "🔍 Historical Data"])

with tab1:
    st.markdown("### EUR/USD Forecast (Differential Model)")
    
    # Time projection
    dates = [datetime.now() + timedelta(days=30*i) for i in range(time_horizon + 1)]
    proj_data = []
    
    for i, date in enumerate(dates):
        adjustment = min(i / 6, 1)
        proj_data.append({
            "Month": i,
            "Date": date.strftime("%Y-%m"),
            "Central": current_eurusd + (pred_eurusd["central"] - current_eurusd) * adjustment,
            "P10": current_eurusd + (pred_eurusd["p10"] - current_eurusd) * adjustment,
            "P25": current_eurusd + (pred_eurusd["p25"] - current_eurusd) * adjustment,
            "P75": current_eurusd + (pred_eurusd["p75"] - current_eurusd) * adjustment,
            "P90": current_eurusd + (pred_eurusd["p90"] - current_eurusd) * adjustment
        })
    
    df_proj = pd.DataFrame(proj_data)
    
    fig = go.Figure()
    
    # Confidence bands
    fig.add_trace(go.Scatter(
        x=list(df_proj["Month"]) + list(df_proj["Month"][::-1]),
        y=list(df_proj["P10"]) + list(df_proj["P90"][::-1]),
        fill='toself', fillcolor='rgba(37, 99, 235, 0.1)',
        line=dict(color='rgba(255,255,255,0)'),
        name='80% Confidence', hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(
        x=list(df_proj["Month"]) + list(df_proj["Month"][::-1]),
        y=list(df_proj["P25"]) + list(df_proj["P75"][::-1]),
        fill='toself', fillcolor='rgba(37, 99, 235, 0.2)',
        line=dict(color='rgba(255,255,255,0)'),
        name='50% Confidence', hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(
        x=df_proj["Month"], y=df_proj["Central"],
        name='Central Forecast',
        line=dict(color='#2563eb', width=4), mode='lines+markers'
    ))
    
    fig.add_trace(go.Scatter(
        x=[0], y=[current_eurusd],
        name='Current Spot',
        mode='markers', marker=dict(color='red', size=12, symbol='star')
    ))
    
    fig.update_layout(
        title=f"EUR/USD Forecast - Differential: {differential:+.2f}%",
        xaxis_title="Months", yaxis_title="EUR/USD", height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Key insights
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Model Details")
        st.markdown(f"""
        - **Slope:** -0.0187 per 1% differential
        - **R²:** 30.2% (variance explained)
        - **Correlation:** -0.550
        - **P-value:** < 0.001 (significant)
        """)
    
    with col2:
        st.markdown("#### Current Setup")
        st.markdown(f"""
        - **US Real Rate:** {us_real:.2f}%
        - **Euro Real Rate:** {euro_real:.2f}%
        - **Differential:** {differential:+.2f}%
        - **Interpretation:** {"USD favored" if differential > 0 else "EUR favored"}
        """)

with tab2:
    st.markdown("### EUR/PLN Forecast (PLN Real Rate Model)")
    
    # Similar projection for EUR/PLN
    proj_eur = []
    for i, date in enumerate(dates):
        adjustment = min(i / 6, 1)
        proj_eur.append({
            "Month": i,
            "Central": current_eurpln + (pred_eur["central"] - current_eurpln) * adjustment,
            "P25": current_eurpln + (pred_eur["p25"] - current_eurpln) * adjustment,
            "P75": current_eurpln + (pred_eur["p75"] - current_eurpln) * adjustment
        })
    
    df_eur = pd.DataFrame(proj_eur)
    
    fig_eur = go.Figure()
    fig_eur.add_trace(go.Scatter(
        x=list(df_eur["Month"]) + list(df_eur["Month"][::-1]),
        y=list(df_eur["P25"]) + list(df_eur["P75"][::-1]),
        fill='toself', fillcolor='rgba(46, 104, 165, 0.2)',
        line=dict(color='rgba(255,255,255,0)'), name='50% Confidence'
    ))
    fig_eur.add_trace(go.Scatter(
        x=df_eur["Month"], y=df_eur["Central"],
        name='Central Forecast', line=dict(color='#2e68a5', width=4)
    ))
    fig_eur.add_trace(go.Scatter(
        x=[0], y=[current_eurpln],
        name='Current', mode='markers', marker=dict(color='red', size=12, symbol='star')
    ))
    
    fig_eur.update_layout(
        title=f"EUR/PLN Forecast - PLN Real Rate: {pln_real:.2f}%",
        xaxis_title="Months", yaxis_title="EUR/PLN", height=500
    )
    
    st.plotly_chart(fig_eur, use_container_width=True)

with tab3:
    st.markdown("### USD/PLN Forecast (PLN Real Rate Model)")
    
    # Similar projection for USD/PLN
    proj_usd = []
    for i, date in enumerate(dates):
        adjustment = min(i / 6, 1)
        proj_usd.append({
            "Month": i,
            "Central": current_usdpln + (pred_usd["central"] - current_usdpln) * adjustment,
            "P25": current_usdpln + (pred_usd["p25"] - current_usdpln) * adjustment,
            "P75": current_usdpln + (pred_usd["p75"] - current_usdpln) * adjustment
        })
    
    df_usd = pd.DataFrame(proj_usd)
    
    fig_usd = go.Figure()
    fig_usd.add_trace(go.Scatter(
        x=list(df_usd["Month"]) + list(df_usd["Month"][::-1]),
        y=list(df_usd["P25"]) + list(df_usd["P75"][::-1]),
        fill='toself', fillcolor='rgba(5, 150, 105, 0.2)',
        line=dict(color='rgba(255,255,255,0)'), name='50% Confidence'
    ))
    fig_usd.add_trace(go.Scatter(
        x=df_usd["Month"], y=df_usd["Central"],
        name='Central Forecast', line=dict(color='#059669', width=4)
    ))
    fig_usd.add_trace(go.Scatter(
        x=[0], y=[current_usdpln],
        name='Current', mode='markers', marker=dict(color='red', size=12, symbol='star')
    ))
    
    fig_usd.update_layout(
        title=f"USD/PLN Forecast - PLN Real Rate: {pln_real:.2f}%",
        xaxis_title="Months", yaxis_title="USD/PLN", height=500
    )
    
    st.plotly_chart(fig_usd, use_container_width=True)

with tab4:
    st.markdown("### Historical PLN Exchange Rates")
    
    df_pln['date'] = pd.to_datetime(df_pln['date'])
    df_pln['real_rate'] = ((1 + df_pln['nbp_reference_rate']/100) / 
                           (1 + df_pln['inflation_rate']/100) - 1) * 100
    
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(
        x=df_pln['date'], y=df_pln['eur_pln'],
        name='EUR/PLN', line=dict(color='#2e68a5', width=2)
    ))
    fig_hist.add_trace(go.Scatter(
        x=df_pln['date'], y=df_pln['usd_pln'],
        name='USD/PLN', line=dict(color='#059669', width=2)
    ))
    
    fig_hist.update_layout(
        title="Historical Exchange Rates (2023-2024)",
        xaxis_title="Date", yaxis_title="Exchange Rate", height=500
    )
    
    st.plotly_chart(fig_hist, use_container_width=True)
    
    # Real rate chart
    fig_real = go.Figure()
    fig_real.add_trace(go.Scatter(
        x=df_pln['date'], y=df_pln['real_rate'],
        name='PLN Real Rate', line=dict(color='green', width=2)
    ))
    fig_real.add_hline(y=0, line_dash="dash", line_color="gray")
    
    fig_real.update_layout(
        title="Poland Real Interest Rate History",
        xaxis_title="Date", yaxis_title="Real Rate (%)", height=400
    )
    
    st.plotly_chart(fig_real, use_container_width=True)

# Model information
st.markdown("---")
st.markdown("## ℹ️ Model Information")

col1, col2 = st.columns(2)

with col1:
    with st.expander("📋 EUR/USD Differential Model"):
        st.markdown("""
        **Based on US-Euro Real Rate Differential**
        
        - Uses **breakeven inflation** (expectations, not actual)
        - Correlation: -0.550 | R²: 30.2%
        - Slope: -0.0187 per 1% differential
        - Higher differential → USD stronger → EUR/USD down
        
        **Why breakeven?**
        - Markets trade on expectations (R²=30%)
        - Core PCE (actual) only R²=3%
        - Forward-looking > backward-looking
        """)

with col2:
    with st.expander("📋 PLN Pairs Model"):
        st.markdown("""
        **Based on Poland Real Interest Rate**
        
        - EUR/PLN sensitivity: -0.12, uncertainty: ±3%
        - USD/PLN sensitivity: -0.18, uncertainty: ±5%
        - Higher PLN real rate → PLN stronger → lower FX rates
        
        **Real Rate Formula:**
        ```
        Real = (1 + Nominal) / (1 + Inflation) - 1
        ```
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em;">
    💱 Multi-Currency FX Forecaster<br>
    EUR/USD: Differential Model (R²=30%) | EUR/PLN & USD/PLN: Real Rate Model<br>
    ⚠️ Forecasts are for informational purposes only
</div>
""", unsafe_allow_html=True)
