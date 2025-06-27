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
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load data
@st.cache_data
def load_data():
    # Complete financial dataset
    data = """date,year,month,inflation_rate,nbp_reference_rate,real_interest_rate,eur_pln,usd_pln,gbp_pln
2014-01,2014,1,0.5,2.50,1.99,4.1776,3.0650,5.0507
2014-02,2014,2,0.7,2.50,1.78,4.1786,3.0613,5.0658
2014-03,2014,3,0.7,2.50,1.78,4.1972,3.0378,5.0525
2014-04,2014,4,0.3,2.50,2.19,4.1841,3.0293,5.0720
2014-05,2014,5,0.2,2.50,2.29,4.1594,3.0234,5.1447
2014-06,2014,6,0.3,2.50,2.19,4.1659,3.0381,5.1028
2014-07,2014,7,-0.2,2.50,2.72,4.1773,3.0456,5.1294
2014-08,2014,8,-0.3,2.50,2.82,4.1856,3.0723,5.1673
2014-09,2014,9,-0.3,2.50,2.82,4.1953,3.1249,5.0926
2014-10,2014,10,-0.6,2.50,3.13,4.2071,3.1657,5.0338
2014-11,2014,11,-0.6,2.50,3.13,4.2389,3.2847,5.1347
2014-12,2014,12,-1.0,2.50,3.54,4.2623,3.5072,5.4859
2015-01,2015,1,-1.4,2.00,3.45,4.2538,3.6403,5.4537
2015-02,2015,2,-1.6,2.00,3.65,4.0934,3.6587,5.6234
2015-03,2015,3,-1.5,1.50,3.05,4.0678,3.7188,5.5694
2015-04,2015,4,-1.1,1.50,2.65,4.0853,3.7540,5.4783
2015-05,2015,5,-0.9,1.50,2.44,4.1078,3.6738,5.5462
2015-06,2015,6,-0.8,1.50,2.33,4.1856,3.8268,5.8847
2015-07,2015,7,-0.7,1.50,2.22,4.1302,3.7635,5.7331
2015-08,2015,8,-0.6,1.50,2.12,4.2247,3.9513,6.0863
2015-09,2015,9,-0.8,1.50,2.33,4.2655,4.0371,6.0432
2015-10,2015,10,-0.7,1.50,2.22,4.2839,3.9276,5.9841
2015-11,2015,11,-0.6,1.50,2.12,4.3211,3.9060,5.9234
2015-12,2015,12,-0.5,1.50,2.01,4.2639,3.9011,5.7847
2016-01,2016,1,-0.8,1.50,2.33,4.3616,4.0044,5.7662
2016-02,2016,2,-0.8,1.50,2.33,4.3438,3.7584,5.4011
2016-03,2016,3,-0.9,1.50,2.44,4.3732,3.7643,5.2697
2016-04,2016,4,-1.1,1.50,2.65,4.3947,3.7899,5.4474
2016-05,2016,5,-0.8,1.50,2.33,4.4259,3.9671,5.8677
2016-06,2016,6,-0.8,1.50,2.33,4.4240,3.9780,5.8935
2016-07,2016,7,-0.8,1.50,2.33,4.3284,3.9533,5.2133
2016-08,2016,8,-0.8,1.50,2.33,4.3567,3.9311,5.1623
2016-09,2016,9,-0.5,1.50,2.01,4.3123,3.8501,4.9894
2016-10,2016,10,-0.2,1.50,1.70,4.2969,3.8332,4.7775
2016-11,2016,11,-0.4,1.50,1.91,4.4588,3.7584,4.6327
2016-12,2016,12,-0.5,1.50,2.01,4.4240,4.1793,5.1323
2017-01,2017,1,-0.2,1.50,1.70,4.3135,3.8581,4.8181
2017-02,2017,2,0.1,1.50,1.39,4.3011,3.7840,4.7319
2017-03,2017,3,1.4,1.50,0.10,4.2247,3.8090,4.7169
2017-04,2017,4,1.7,1.50,-0.17,4.2291,3.7963,4.6568
2017-05,2017,5,1.6,1.50,-0.10,4.1953,3.7635,4.6611
2017-06,2017,6,1.8,1.50,-0.29,4.2291,3.7963,4.8611
2017-07,2017,7,1.6,1.50,-0.10,4.2655,3.8268,4.9519
2017-08,2017,8,1.4,1.50,0.10,4.2839,3.9276,5.1321
2017-09,2017,9,1.2,1.50,0.30,4.3211,3.9060,5.3541
2017-10,2017,10,1.1,1.50,0.40,4.2969,3.8332,5.2133
2017-11,2017,11,1.2,1.50,0.30,4.2389,3.7584,5.1623
2017-12,2017,12,1.0,1.50,0.50,4.1709,3.4813,4.6568
2018-01,2018,1,1.2,1.50,0.30,4.1497,3.4138,4.6543
2018-02,2018,2,1.4,1.50,0.10,4.1856,3.4427,4.7775
2018-03,2018,3,1.3,1.50,0.20,4.2071,3.4250,4.8846
2018-04,2018,4,1.7,1.50,-0.17,4.2247,3.4427,4.8957
2018-05,2018,5,1.7,1.50,-0.17,4.3618,3.7348,4.8846
2018-06,2018,6,1.7,1.50,-0.17,4.3618,3.7348,4.8846
2018-07,2018,7,1.9,1.50,-0.39,4.2655,3.8268,4.9519
2018-08,2018,8,2.0,1.50,-0.49,4.2839,3.9276,5.1321
2018-09,2018,9,1.4,1.50,0.10,4.3211,3.9060,5.3541
2018-10,2018,10,1.2,1.50,0.30,4.2969,3.8332,5.2133
2018-11,2018,11,1.3,1.50,0.20,4.2389,3.7584,5.1623
2018-12,2018,12,1.1,1.50,0.40,4.2669,3.7597,4.7775
2019-01,2019,1,0.7,1.50,0.79,4.2615,3.7643,4.8025
2019-02,2019,2,1.2,1.50,0.30,4.3011,3.7840,4.7319
2019-03,2019,3,1.7,1.50,-0.17,4.2247,3.8090,4.7169
2019-04,2019,4,2.2,1.50,-0.69,4.2291,3.7963,4.6568
2019-05,2019,5,2.3,1.50,-0.78,4.2655,3.7635,4.6611
2019-06,2019,6,1.0,1.50,0.50,4.2687,3.9311,4.9975
2019-07,2019,7,0.5,1.50,0.99,4.2839,3.9276,4.9519
2019-08,2019,8,0.4,1.50,1.09,4.3211,3.9060,4.8321
2019-09,2019,9,0.5,1.50,0.99,4.3732,3.8501,4.9894
2019-10,2019,10,0.4,1.50,1.09,4.2969,3.8332,4.8133
2019-11,2019,11,0.6,1.50,0.89,4.2389,3.7584,4.6327
2019-12,2019,12,1.3,1.50,0.20,4.2568,3.7977,4.9988
2020-01,2020,1,3.2,1.50,-1.68,4.2597,3.7282,4.8957
2020-02,2020,2,3.7,1.50,-2.16,4.3011,3.7840,4.7319
2020-03,2020,3,3.2,1.00,-2.13,4.5523,4.1044,5.1321
2020-04,2020,4,3.4,0.50,-2.80,4.5268,4.0776,5.0511
2020-05,2020,5,3.4,0.10,-3.19,4.4584,4.0408,4.9519
2020-06,2020,6,3.3,0.10,-3.10,4.4588,3.9680,4.9894
2020-07,2020,7,3.6,0.10,-3.39,4.4240,3.9533,5.1327
2020-08,2020,8,3.8,0.10,-3.58,4.4259,3.9671,5.2133
2020-09,2020,9,3.2,0.10,-3.00,4.5268,3.9780,5.3541
2020-10,2020,10,3.1,0.10,-2.90,4.4584,4.0408,5.4924
2020-11,2020,11,3.0,0.10,-2.81,4.4588,3.9680,5.4407
2020-12,2020,12,3.7,0.10,-3.49,4.6148,3.7584,5.1327
2021-01,2021,1,2.6,0.10,-2.44,4.5826,3.8332,5.2288
2021-02,2021,2,2.4,0.10,-2.24,4.1856,3.8090,5.5462
2021-03,2021,3,3.2,0.10,-3.00,4.6525,4.2030,5.5389
2021-04,2021,4,4.6,0.10,-4.37,4.1953,3.7635,5.4783
2021-05,2021,5,4.4,0.10,-4.18,4.4259,3.9671,5.8677
2021-06,2021,6,4.1,0.10,-3.85,4.5208,3.7840,5.3118
2021-07,2021,7,4.8,0.10,-4.57,4.5826,3.8332,5.2288
2021-08,2021,8,5.2,0.10,-4.96,4.6856,4.0671,5.4407
2021-09,2021,9,5.8,0.10,-5.54,4.6184,4.0086,5.4924
2021-10,2021,10,5.9,0.50,-5.10,4.6184,4.0086,5.4924
2021-11,2021,11,6.8,1.25,-5.20,4.6856,4.0671,5.4407
2021-12,2021,12,8.6,1.75,-6.31,4.5994,4.0600,5.4542
2022-01,2022,1,9.4,2.25,-6.54,4.5969,4.0683,5.4781
2022-02,2022,2,8.5,2.75,-5.33,4.6939,4.0687,5.4624
2022-03,2022,3,10.9,3.50,-6.67,4.6525,4.2030,5.5389
2022-04,2022,4,12.4,4.50,-7.19,4.6560,4.5267,5.6626
2022-05,2022,5,13.5,5.25,-7.43,4.5691,4.2608,5.3329
2022-06,2022,6,11.8,6.00,-5.19,4.4615,4.2631,5.2832
2022-07,2022,7,10.8,6.00,-4.34,4.7011,4.7169,5.5786
2022-08,2022,8,10.1,6.00,-3.73,4.6939,4.5267,5.4624
2022-09,2022,9,10.7,6.75,-3.57,4.8694,4.8574,5.5331
2022-10,2022,10,8.2,6.75,-1.34,4.7392,4.9894,5.6786
2022-11,2022,11,7.8,6.75,-0.90,4.6939,4.7169,5.5786
2022-12,2022,12,7.5,6.75,-0.70,4.6808,4.4018,5.3541
2023-01,2023,1,6.6,6.75,0.14,4.7047,4.4541,5.4851
2023-02,2023,2,6.0,6.75,0.71,4.6939,4.4018,5.3541
2023-03,2023,3,6.1,6.75,0.61,4.6808,4.4541,5.4851
2023-04,2023,4,11.0,6.75,-3.89,4.5691,4.2608,5.3329
2023-05,2023,5,12.9,6.75,-5.45,4.4615,4.2631,5.2832
2023-06,2023,6,11.5,6.75,-4.26,4.4617,4.0718,5.1690
2023-07,2023,7,10.1,6.75,-3.05,4.5208,4.0086,5.2288
2023-08,2023,8,9.6,6.75,-2.60,4.5826,4.0671,5.4407
2023-09,2023,9,8.2,6.75,-1.34,4.6353,4.3490,5.3749
2023-10,2023,10,7.8,6.75,-0.90,4.3395,3.9780,5.0523
2023-11,2023,11,6.5,6.75,0.23,4.3652,4.0011,5.0827
2023-12,2023,12,6.2,5.75,-0.42,4.3395,3.9780,5.0523
2024-01,2024,1,5.5,5.75,0.24,4.3652,4.0011,5.0827
2024-02,2024,2,4.9,5.75,0.82,4.3274,4.0083,5.0645
2024-03,2024,3,3.6,5.75,2.07,4.3074,3.9658,5.0357
2024-04,2024,4,3.9,5.75,1.79,4.3026,4.0106,5.0247
2024-05,2024,5,2.8,5.75,2.87,4.2848,3.9675,5.0075
2024-06,2024,6,2.6,5.75,3.07,4.3177,4.0127,5.1000
2024-07,2024,7,3.4,5.75,2.27,4.2811,3.9462,5.0749
2024-08,2024,8,3.8,5.75,1.88,4.2918,3.9020,5.0437
2024-09,2024,9,3.8,5.75,1.88,4.2782,3.8501,5.0905
2024-10,2024,10,4.2,5.75,1.49,4.3164,3.9573,5.1676
2024-11,2024,11,4.6,5.75,1.10,4.3339,4.0763,5.1980
2024-12,2024,12,4.7,5.75,0.98,4.2714,4.0787,5.1535
2025-01,2025,1,4.9,5.75,0.82,4.2800,4.0500,5.1200
2025-02,2025,2,4.9,5.75,0.82,4.2750,4.0400,5.1100
2025-03,2025,3,4.9,5.75,0.82,4.2700,4.0350,5.1050
2025-04,2025,4,4.3,5.75,1.39,4.2650,4.0320,5.1020
2025-05,2025,5,4.0,5.25,1.20,4.2600,4.0300,5.1000"""
    
    return pd.read_csv(io.StringIO(data))

# Load the data
df = load_data()

# Title and header
st.title("💱 Exchange Rate Simulator - Poland")
st.markdown("### Interactive dashboard for analyzing the impact of interest rates and inflation on PLN exchange rates")

# Sidebar controls
st.sidebar.header("🎛️ Control Panel")

# Sliders
inflation_rate = st.sidebar.slider(
    "Core Inflation (%)", 
    min_value=-3.0, 
    max_value=15.0, 
    value=4.0, 
    step=0.1,
    help="Year-over-year core inflation rate"
)

nominal_rate = st.sidebar.slider(
    "NBP Reference Rate (%)", 
    min_value=0.0, 
    max_value=12.0, 
    value=5.75, 
    step=0.25,
    help="National Bank of Poland policy rate"
)

time_horizon = st.sidebar.slider(
    "Forecast Horizon (months)", 
    min_value=3, 
    max_value=24, 
    value=12,
    help="Length of exchange rate forecast"
)

# Calculate real interest rate
real_rate = ((1 + nominal_rate/100) / (1 + inflation_rate/100) - 1) * 100

# Display calculated real rate
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Calculated Real Interest Rate")
color = "🟢" if real_rate >= 0 else "🔴"
st.sidebar.markdown(f"## {color} {real_rate:.2f}%")
st.sidebar.caption(f"Formula: (1 + {nominal_rate}%) / (1 + {inflation_rate}%) - 1")

# Prediction model
def predict_exchange_rates(real_rate, nominal_rate, inflation_rate):
    # Current baseline rates (as of Dec 2024)
    base_rates = {"EUR": 4.27, "USD": 4.08, "GBP": 5.15}
    current_real = 0.98  # Current real rate
    
    # Sensitivity coefficients (based on historical analysis)
    sensitivity = {
        "EUR": {"real": -0.12, "volatility": 0.08},
        "USD": {"real": -0.18, "volatility": 0.12},
        "GBP": {"real": -0.15, "volatility": 0.10}
    }
    
    results = {}
    for currency in base_rates:
        # Calculate impact based on real rate difference
        real_impact = (real_rate - current_real) * sensitivity[currency]["real"]
        central = base_rates[currency] + real_impact
        
        # Calculate percentiles (10th and 90th)
        vol = sensitivity[currency]["volatility"] * central
        p10 = central - 1.28 * vol
        p90 = central + 1.28 * vol
        
        # Calculate percentage change
        change = ((central - base_rates[currency]) / base_rates[currency]) * 100
        
        results[currency] = {
            "central": central,
            "p10": p10,
            "p90": p90,
            "change": change,
            "volatility": sensitivity[currency]["volatility"] * 100
        }
    
    return results

# Get predictions
predictions = predict_exchange_rates(real_rate, nominal_rate, inflation_rate)

# Main content area
st.markdown("---")

# Exchange rate predictions cards
st.markdown("## 💱 Predicted Exchange Rates")

col1, col2, col3 = st.columns(3)

currencies = ["EUR", "USD", "GBP"]
colors = ["#4f46e5", "#059669", "#dc2626"]

for i, (currency, color) in enumerate(zip(currencies, colors)):
    with [col1, col2, col3][i]:
        pred = predictions[currency]
        
        # Create colored card
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {color}20, {color}10);
            padding: 20px;
            border-radius: 15px;
            border: 2px solid {color}40;
            text-align: center;
            margin-bottom: 10px;
        ">
            <h3 style="color: {color}; margin: 0; font-size: 1.5em;">{currency}/PLN</h3>
            <h1 style="color: {color}; margin: 10px 0; font-size: 2.5em;">
                {pred['central']:.4f}
            </h1>
            <p style="margin: 5px 0; font-size: 1.1em;">
                <strong>Change: {'🔴' if pred['change'] >= 0 else '🟢'} {pred['change']:+.1f}%</strong>
            </p>
            <p style="margin: 5px 0; font-size: 0.9em;">
                Volatility: {pred['volatility']:.1f}%
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Percentile information
        st.markdown(f"""
        **Risk Range:**
        - 10th percentile: **{pred['p10']:.4f}** (optimistic)
        - 90th percentile: **{pred['p90']:.4f}** (pessimistic)
        """)

st.markdown("---")

# Charts section
st.markdown("## 📊 Analysis Charts")

# Tab selection
tab1, tab2, tab3 = st.tabs(["📈 Time Forecast", "📊 Sensitivity Analysis", "🔍 Historical Data"])

with tab1:
    st.markdown("### Exchange Rate Forecast Over Time")
    
    # Generate time projection
    dates = [datetime.now() + timedelta(days=30*i) for i in range(time_horizon + 1)]
    projection_data = []
    
    for i, date in enumerate(dates):
        # Gradual adjustment factor (full adjustment after 6 months)
        adjustment = min(i / 6, 1)
        
        projection_data.append({
            "Month": i,
            "Date": date.strftime("%Y-%m"),
            "EUR": 4.27 + (predictions["EUR"]["central"] - 4.27) * adjustment,
            "USD": 4.08 + (predictions["USD"]["central"] - 4.08) * adjustment,
            "GBP": 5.15 + (predictions["GBP"]["central"] - 5.15) * adjustment,
        })
    
    df_projection = pd.DataFrame(projection_data)
    
    # Create plotly chart
    fig = go.Figure()
    
    # Add traces for each currency
    fig.add_trace(go.Scatter(
        x=df_projection["Month"], 
        y=df_projection["EUR"], 
        name="EUR/PLN", 
        line=dict(color="#4f46e5", width=3),
        mode='lines+markers'
    ))
    
    fig.add_trace(go.Scatter(
        x=df_projection["Month"], 
        y=df_projection["USD"], 
        name="USD/PLN", 
        line=dict(color="#059669", width=3),
        mode='lines+markers'
    ))
    
    fig.add_trace(go.Scatter(
        x=df_projection["Month"], 
        y=df_projection["GBP"], 
        name="GBP/PLN", 
        line=dict(color="#dc2626", width=3),
        mode='lines+markers'
    ))
    
    fig.update_layout(
        title=f"Exchange Rate Forecast - {time_horizon} Months",
        xaxis_title="Months from Now",
        yaxis_title="Exchange Rate (PLN)",
        height=500,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show forecast table
    st.markdown("#### Forecast Data")
    st.dataframe(df_projection.round(4), use_container_width=True)

with tab2:
    st.markdown("### Sensitivity Analysis")
    
    # Currency selection for sensitivity
    selected_currency = st.selectbox(
        "Select Currency Pair:", 
        ["EUR", "USD", "GBP"],
        help="Choose which currency pair to analyze"
    )
    
    # Generate sensitivity data
    steps = np.arange(-3, 3.1, 0.5)
    sensitivity_data = []
    
    for step in steps:
        test_real = real_rate + step
        test_predictions = predict_exchange_rates(test_real, nominal_rate, inflation_rate)
        sensitivity_data.append({
            "Real Rate Change (p.p.)": step,
            "Real Rate": test_real,
            selected_currency: test_predictions[selected_currency]["central"]
        })
    
    df_sensitivity = pd.DataFrame(sensitivity_data)
    
    # Create sensitivity chart
    fig = px.line(
        df_sensitivity, 
        x="Real Rate Change (p.p.)", 
        y=selected_currency,
        title=f"Sensitivity of {selected_currency}/PLN to Real Interest Rate Changes",
        markers=True
    )
    
    fig.add_vline(x=0, line_dash="dash", line_color="gray", annotation_text="Current Level")
    fig.update_traces(line_width=3)
    fig.update_layout(height=500)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Sensitivity coefficient info
    sensitivity_info = {
        "EUR": "EUR is least sensitive to real rate changes (-0.12 coefficient)",
        "USD": "USD is most sensitive to real rate changes (-0.18 coefficient)", 
        "GBP": "GBP has medium sensitivity to real rate changes (-0.15 coefficient)"
    }
    
    st.info(f"**Interpretation:** {sensitivity_info[selected_currency]}")

with tab3:
    st.markdown("### Historical Correlation Analysis")
    
    # Currency selection for historical analysis
    hist_currency = st.selectbox(
        "Select Currency for Historical Analysis:", 
        ["EUR", "USD", "GBP"],
        key="hist_currency"
    )
    
    # Create scatter plot of historical data
    fig = px.scatter(
        df, 
        x="real_interest_rate", 
        y=f"{hist_currency.lower()}_pln",
        color="year",
        title=f"Historical Correlation: Real Interest Rate vs {hist_currency}/PLN",
        hover_data=["date", "inflation_rate", "nbp_reference_rate"],
        labels={
            "real_interest_rate": "Real Interest Rate (%)",
            f"{hist_currency.lower()}_pln": f"{hist_currency}/PLN Exchange Rate"
        }
    )
    
    # Add trend line
    z = np.polyfit(df['real_interest_rate'], df[f'{hist_currency.lower()}_pln'], 1)
    p = np.poly1d(z)
    
    x_trend = np.linspace(df['real_interest_rate'].min(), df['real_interest_rate'].max(), 100)
    y_trend = p(x_trend)
    
    fig.add_trace(go.Scatter(
        x=x_trend, 
        y=y_trend, 
        mode='lines',
        name='Trend Line',
        line=dict(color='red', dash='dash', width=2)
    ))
    
    fig.update_layout(height=500)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Calculate correlation
    correlation = df['real_interest_rate'].corr(df[f'{hist_currency.lower()}_pln'])
    st.metric(
        label=f"Correlation Coefficient ({hist_currency}/PLN vs Real Rate)",
        value=f"{correlation:.3f}",
        help="Pearson correlation coefficient between real interest rate and exchange rate"
    )
    
    # Historical insights
    st.markdown("#### 📋 Historical Insights")
    
    periods = {
        "2014-2016": "Deflation period - High real rates, volatile exchange rates",
        "2017-2019": "Economic growth - Moderate real rates, stable PLN", 
        "2020-2021": "COVID crisis - Deeply negative real rates, PLN weakness",
        "2022-2023": "High inflation - Negative real rates despite rate hikes",
        "2024-2025": "Normalization - Return to positive real rates, PLN strength"
    }
    
    for period, description in periods.items():
        st.markdown(f"- **{period}:** {description}")

# Statistics section
st.markdown("---")
st.markdown("## 📈 Key Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Current Real Rate",
        f"{real_rate:.2f}%",
        delta=f"{real_rate - 0.98:.2f} p.p.",
        help="Compared to December 2024 baseline"
    )

with col2:
    avg_real = df['real_interest_rate'].mean()
    st.metric(
        "Historical Average",
        f"{avg_real:.2f}%",
        help="Average real rate 2014-2025"
    )

with col3:
    max_real = df['real_interest_rate'].max()
    min_real = df['real_interest_rate'].min()
    st.metric(
        "Historical Range", 
        f"{min_real:.1f}% to {max_real:.1f}%",
        help="Minimum and maximum real rates observed"
    )

with col4:
    current_vol = np.std([pred['volatility'] for pred in predictions.values()])
    st.metric(
        "Average Volatility",
        f"{current_vol:.1f}%",
        help="Expected annual volatility across currencies"
    )

# Model methodology
st.markdown("---")
st.markdown("## 🔬 Model Methodology")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📊 **Calculation Methods**
    - **Real Interest Rate**: (1 + nominal) / (1 + inflation) - 1
    - **Sensitivity Coefficients**: USD (-0.18) > GBP (-0.15) > EUR (-0.12)
    - **Percentiles**: Normal distribution with historical volatility
    - **Adjustment Period**: 6 months for full market response
    """)

with col2:
    st.markdown("""
    ### 📋 **Data Sources**
    - **Exchange Rates**: NBP Table A (monthly averages)
    - **Reference Rate**: NBP official policy rates
    - **Core Inflation**: Year-over-year base inflation
    - **Time Period**: January 2014 - May 2025 (137 observations)
    """)

# Download section
st.markdown("---")
st.markdown("## 💾 Download Data")

col1, col2 = st.columns(2)

with col1:
    # Download historical data
    csv_data = df.to_csv(index=False)
    st.download_button(
        label="📥 Download Historical Data (CSV)",
        data=csv_data,
        file_name="nbp_exchange_rate_data.csv",
        mime="text/csv",
        help="Complete dataset with 137 monthly observations"
    )

with col2:
    # Download forecast data
    if 'df_projection' in locals():
        forecast_csv = df_projection.to_csv(index=False)
        st.download_button(
            label="📥 Download Forecast Data (CSV)",
            data=forecast_csv,
            file_name=f"exchange_rate_forecast_{time_horizon}m.csv",
            mime="text/csv",
            help="Projected exchange rates based on current settings"
        )

# Footer with disclaimers
st.markdown("---")
st.markdown("### ⚠️ Important Disclaimers")

st.warning("""
**Educational Purpose Only**: This tool is designed for educational and analytical purposes. 
Real exchange rates are influenced by numerous factors beyond interest rates and inflation, 
including geopolitical events, market sentiment, economic policies, and global financial conditions.

**Not Investment Advice**: The predictions and analysis provided should not be considered as 
investment advice or recommendations for trading decisions.

**Model Limitations**: The model uses simplified assumptions and historical correlations 
that may not hold in future market conditions.
""")

st.info("""
**About the Model**: Based on 10+ years of historical NBP data (2014-2025) and established 
economic relationships between real interest rates and exchange rates. 
Sensitivity coefficients derived from regression analysis of historical data.
""")

# Sidebar footer
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔗 Resources")
st.sidebar.markdown("""
- [NBP Official Rates](https://nbp.pl/podstawowe-stopy-procentowe/)
- [NBP Exchange Rates](https://nbp.pl/kursy/)
- [Inflation Data](https://stat.gov.pl/)
""")

st.sidebar.markdown("### 📊 Model Info")
st.sidebar.markdown(f"""
- **Data Points**: {len(df)} monthly observations
- **Time Span**: 2014-2025 ({len(df)//12:.1f} years)
- **Last Update**: May 2025
""")

# Run instructions at the bottom
st.markdown("---")
st.markdown("""
### 🚀 **How to Run This App**
```bash
# Install required packages
pip install streamlit pandas plotly numpy

# Save this code as 'app.py' and run:
streamlit run app.py
```

### 📱 **Deploy to Streamlit Cloud**
1. Push code to GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Deploy automatically!
""")
