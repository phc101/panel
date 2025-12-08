import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import io

# Konfiguracja strony
st.set_page_config(
    page_title="EUR/USD Rate Differential Forecaster",
    page_icon="💱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tytuł
st.title("💱 EUR/USD Forecaster - Real Rate Differential Model")
st.markdown("### Based on US-Euro Real Interest Rate Differential")

# Panel boczny
st.sidebar.header("🎛️ Model Parameters")

# Current spot rates
st.sidebar.markdown("### 💱 Current Exchange Rates")
current_eurusd = st.sidebar.number_input(
    "EUR/USD Spot", 
    min_value=0.9000, 
    max_value=1.4000, 
    value=1.0566, 
    step=0.0001, 
    format="%.4f",
    help="Current EUR/USD exchange rate"
)

# US Parameters
st.sidebar.markdown("### 🇺🇸 United States")
us_nominal = st.sidebar.slider(
    "Fed Funds Rate (%)", 
    0.0, 8.0, 4.50, 0.25,
    help="Federal Reserve policy rate"
)
us_breakeven = st.sidebar.slider(
    "US Breakeven Inflation (%)", 
    0.0, 5.0, 2.27, 0.1,
    help="Market-implied inflation expectations (T10YIE)"
)

# Euro Parameters  
st.sidebar.markdown("### 🇪🇺 Euro Area")
euro_nominal = st.sidebar.slider(
    "ECB Rate (%)",
    0.0, 6.0, 3.25, 0.25,
    help="European Central Bank policy rate"
)
euro_inflation = st.sidebar.slider(
    "Euro HICP Inflation (%)",
    0.0, 5.0, 2.40, 0.1,
    help="Euro area inflation"
)

# Forecast horizon
time_horizon = st.sidebar.slider(
    "Forecast Horizon (months)",
    3, 24, 12,
    help="Length of forecast"
)

# Calculate real rates
us_real = us_nominal - us_breakeven
euro_real = euro_nominal - euro_inflation
differential = us_real - euro_real

# Display in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Calculated Rates")
st.sidebar.markdown(f"""
**US Real Rate:** {us_real:.2f}%  
**Euro Real Rate:** {euro_real:.2f}%  
**Differential (US-Euro):** {differential:+.2f}%
""")

if differential > 0:
    st.sidebar.success(f"✅ USD favored by {differential:.2f}%")
else:
    st.sidebar.warning(f"⚠️ EUR favored by {abs(differential):.2f}%")

# Prediction function based on real rate differential
def predict_eurusd(differential, current_rate):
    """
    Model based on empirical analysis:
    - Correlation: -0.550 (from our analysis)
    - R²: 0.302 (30% variance explained)
    - Slope: -0.0187 per 1% differential
    """
    
    # Model parameters from analysis
    slope = -0.0187  # EUR/USD change per 1% differential
    baseline_diff = 0.0  # Neutral differential
    uncertainty = 0.05  # 5% model uncertainty
    
    # Calculate impact
    impact = (differential - baseline_diff) * slope
    central = current_rate + impact
    
    # Confidence bands
    model_std = uncertainty * central
    p10 = central - 1.28 * model_std
    p25 = central - 0.67 * model_std  
    p75 = central + 0.67 * model_std
    p90 = central + 1.28 * model_std
    
    # Calculate change
    change = ((central - current_rate) / current_rate) * 100
    
    return {
        "central": central,
        "p10": p10,
        "p25": p25,
        "p75": p75,
        "p90": p90,
        "change": change,
        "current": current_rate,
        "differential": differential
    }

# Get prediction
prediction = predict_eurusd(differential, current_eurusd)

# Beautiful prediction card
st.markdown("---")
st.markdown("## 💱 EUR/USD Forecast")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    # Main forecast card
    color = "#2563eb" if differential < 0 else "#dc2626"
    
    card_html = f"""
    <div style="
        background: linear-gradient(135deg, {color}20, {color}10);
        padding: 30px;
        border-radius: 15px;
        border: 2px solid {color}40;
        text-align: center;
    ">
        <h2 style="color: {color}; margin: 0;">EUR/USD Forecast</h2>
        <h1 style="color: {color}; margin: 15px 0; font-size: 3.5em;">
            {prediction['central']:.4f}
        </h1>
        <p style="margin: 5px 0; font-size: 1.2em; color: #666;">
            Current: {prediction['current']:.4f}
        </p>
        <p style="margin: 10px 0; font-size: 1.5em;">
            <strong>Change: {'🟢' if prediction['change'] >= 0 else '🔴'} {prediction['change']:+.2f}%</strong>
        </p>
        <p style="margin: 10px 0; font-size: 1em; color: #666;">
            Based on {differential:+.2f}% rate differential
        </p>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
    
    # Confidence ranges
    st.markdown(f"""
    #### 🎯 Confidence Ranges
    
    **50% Confidence:** {prediction['p25']:.4f} - {prediction['p75']:.4f}  
    **80% Confidence:** {prediction['p10']:.4f} - {prediction['p90']:.4f}
    
    **Model Details:**
    - Slope: -0.0187 (per 1% differential)
    - R²: 30.2% (variance explained)
    - Correlation: -0.550
    """)

with col2:
    st.markdown("#### 🇺🇸 US Metrics")
    st.metric("Nominal Rate", f"{us_nominal:.2f}%")
    st.metric("Breakeven Infl.", f"{us_breakeven:.2f}%")
    st.metric("Real Rate", f"{us_real:.2f}%", 
             delta=None if us_real >= 0 else "Negative")

with col3:
    st.markdown("#### 🇪🇺 Euro Metrics")
    st.metric("ECB Rate", f"{euro_nominal:.2f}%")
    st.metric("HICP Inflation", f"{euro_inflation:.2f}%")
    st.metric("Real Rate", f"{euro_real:.2f}%",
             delta=None if euro_real >= 0 else "Negative")

# Tabs for analysis
st.markdown("---")
st.markdown("## 📊 Analysis & Scenarios")

tab1, tab2, tab3 = st.tabs(["📈 Time Projection", "📊 Sensitivity Analysis", "🎯 Scenarios"])

with tab1:
    st.markdown("### EUR/USD Forecast Over Time")
    
    # Generate time projection
    dates = [datetime.now() + timedelta(days=30*i) for i in range(time_horizon + 1)]
    projection_data = []
    
    for i, date in enumerate(dates):
        # Gradual adjustment to target (reach target in 6 months)
        adjustment = min(i / 6, 1)
        
        projection_data.append({
            "Month": i,
            "Date": date.strftime("%Y-%m"),
            "Central": current_eurusd + (prediction["central"] - current_eurusd) * adjustment,
            "P10": current_eurusd + (prediction["p10"] - current_eurusd) * adjustment,
            "P25": current_eurusd + (prediction["p25"] - current_eurusd) * adjustment,
            "P75": current_eurusd + (prediction["p75"] - current_eurusd) * adjustment,
            "P90": current_eurusd + (prediction["p90"] - current_eurusd) * adjustment
        })
    
    df_proj = pd.DataFrame(projection_data)
    
    # Create chart
    fig = go.Figure()
    
    # Confidence bands
    fig.add_trace(go.Scatter(
        x=list(df_proj["Month"]) + list(df_proj["Month"][::-1]),
        y=list(df_proj["P10"]) + list(df_proj["P90"][::-1]),
        fill='toself',
        fillcolor='rgba(37, 99, 235, 0.1)',
        line=dict(color='rgba(255,255,255,0)'),
        name='80% Confidence',
        showlegend=True,
        hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(
        x=list(df_proj["Month"]) + list(df_proj["Month"][::-1]),
        y=list(df_proj["P25"]) + list(df_proj["P75"][::-1]),
        fill='toself',
        fillcolor='rgba(37, 99, 235, 0.2)',
        line=dict(color='rgba(255,255,255,0)'),
        name='50% Confidence',
        showlegend=True,
        hoverinfo='skip'
    ))
    
    # Central forecast line
    fig.add_trace(go.Scatter(
        x=df_proj["Month"],
        y=df_proj["Central"],
        name='Central Forecast',
        line=dict(color='#2563eb', width=4),
        mode='lines+markers'
    ))
    
    # Current spot
    fig.add_trace(go.Scatter(
        x=[0],
        y=[current_eurusd],
        name='Current Spot',
        mode='markers',
        marker=dict(color='red', size=12, symbol='star')
    ))
    
    fig.update_layout(
        title=f"EUR/USD Forecast - {time_horizon} Months (Differential: {differential:+.2f}%)",
        xaxis_title="Months from Now",
        yaxis_title="EUR/USD Exchange Rate",
        height=600,
        hovermode='x unified',
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor="rgba(255,255,255,0.8)"
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Data table
    st.markdown("#### Forecast Data")
    display_df = df_proj.copy()
    for col in ["Central", "P10", "P25", "P75", "P90"]:
        display_df[col] = display_df[col].round(4)
    
    display_df = display_df.rename(columns={
        "Month": "Month",
        "Date": "Date",
        "Central": "Central Forecast",
        "P10": "Lower 80%",
        "P25": "Lower 50%",
        "P75": "Upper 50%",
        "P90": "Upper 80%"
    })
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

with tab2:
    st.markdown("### Sensitivity to Rate Differential")
    
    # Generate sensitivity data
    diff_range = np.arange(-3.0, 4.0, 0.1)
    sensitivity_data = []
    
    for diff in diff_range:
        temp_pred = predict_eurusd(diff, current_eurusd)
        sensitivity_data.append({
            "Differential": diff,
            "EUR_USD": temp_pred["central"]
        })
    
    df_sens = pd.DataFrame(sensitivity_data)
    
    # Create sensitivity chart
    fig_sens = go.Figure()
    
    fig_sens.add_trace(go.Scatter(
        x=df_sens["Differential"],
        y=df_sens["EUR_USD"],
        name="EUR/USD",
        line=dict(color='#2563eb', width=3),
        mode='lines'
    ))
    
    # Add current position
    fig_sens.add_vline(
        x=differential,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Current: {differential:+.2f}%"
    )
    
    # Add parity line
    fig_sens.add_vline(
        x=0,
        line_dash="dot",
        line_color="gray",
        annotation_text="Parity (0%)"
    )
    
    fig_sens.update_layout(
        title="EUR/USD Sensitivity to Real Rate Differential",
        xaxis_title="Real Rate Differential (US - Euro) [%]",
        yaxis_title="EUR/USD Exchange Rate",
        height=500
    )
    
    st.plotly_chart(fig_sens, use_container_width=True)
    
    # Key insights
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📉 If Differential Widens")
        wider_diff = differential + 1.0
        wider_pred = predict_eurusd(wider_diff, current_eurusd)
        st.markdown(f"""
        **Differential: {wider_diff:+.2f}%**
        - EUR/USD: {wider_pred['central']:.4f}
        - Change: {wider_pred['change']:+.2f}%
        - USD strengthens (more attractive)
        """)
    
    with col2:
        st.markdown("#### 📈 If Differential Narrows")
        narrower_diff = differential - 1.0
        narrower_pred = predict_eurusd(narrower_diff, current_eurusd)
        st.markdown(f"""
        **Differential: {narrower_diff:+.2f}%**
        - EUR/USD: {narrower_pred['central']:.4f}
        - Change: {narrower_pred['change']:+.2f}%
        - EUR strengthens (more competitive)
        """)

with tab3:
    st.markdown("### Key Scenarios")
    
    # Define scenarios
    scenarios = [
        {
            "name": "Fed Aggressive Cuts",
            "us_nominal": 3.0,
            "us_breakeven": 2.2,
            "euro_nominal": 3.25,
            "euro_inflation": 2.4
        },
        {
            "name": "ECB Aggressive Cuts",
            "us_nominal": 4.5,
            "us_breakeven": 2.27,
            "euro_nominal": 2.0,
            "euro_inflation": 2.4
        },
        {
            "name": "Both Hold Current",
            "us_nominal": us_nominal,
            "us_breakeven": us_breakeven,
            "euro_nominal": euro_nominal,
            "euro_inflation": euro_inflation
        },
        {
            "name": "Inflation Spike",
            "us_nominal": 5.5,
            "us_breakeven": 3.5,
            "euro_nominal": 4.0,
            "euro_inflation": 3.5
        },
        {
            "name": "Fed Pause, ECB Cuts",
            "us_nominal": 4.5,
            "us_breakeven": 2.3,
            "euro_nominal": 2.5,
            "euro_inflation": 2.4
        }
    ]
    
    # Calculate each scenario
    scenario_results = []
    for scenario in scenarios:
        s_us_real = scenario["us_nominal"] - scenario["us_breakeven"]
        s_euro_real = scenario["euro_nominal"] - scenario["euro_inflation"]
        s_diff = s_us_real - s_euro_real
        s_pred = predict_eurusd(s_diff, current_eurusd)
        
        scenario_results.append({
            "Scenario": scenario["name"],
            "US Real (%)": f"{s_us_real:.2f}",
            "Euro Real (%)": f"{s_euro_real:.2f}",
            "Differential (%)": f"{s_diff:+.2f}",
            "EUR/USD": f"{s_pred['central']:.4f}",
            "Change (%)": f"{s_pred['change']:+.2f}"
        })
    
    df_scenarios = pd.DataFrame(scenario_results)
    st.dataframe(df_scenarios, use_container_width=True, hide_index=True)
    
    # Scenario chart
    fig_scen = go.Figure(data=[
        go.Bar(
            x=[s["Scenario"] for s in scenario_results],
            y=[float(s["Change (%)"].replace("+", "")) for s in scenario_results],
            marker_color=['green' if float(s["Change (%)"].replace("+", "")) > 0 else 'red' 
                         for s in scenario_results]
        )
    ])
    
    fig_scen.update_layout(
        title="EUR/USD Change by Scenario",
        xaxis_title="Scenario",
        yaxis_title="Change from Current (%)",
        height=400
    )
    
    st.plotly_chart(fig_scen, use_container_width=True)

# Model information
st.markdown("---")
st.markdown("## ℹ️ Model Information")

col1, col2 = st.columns(2)

with col1:
    with st.expander("📋 Model Methodology"):
        st.markdown("""
        **Real Rate Differential Model**
        
        This model forecasts EUR/USD based on the differential between US and Euro real interest rates.
        
        **Formula:**
        ```
        Real Rate = Nominal Rate - Inflation
        Differential = US Real Rate - Euro Real Rate
        EUR/USD Impact = Differential × Slope
        ```
        
        **Parameters:**
        - Slope: -0.0187 (per 1% differential)
        - R²: 0.302 (30% variance explained)
        - Correlation: -0.550
        
        **Data Source:**
        - Empirical analysis of 10 years historical data
        - US: Fed Funds + Breakeven Inflation (T10YIE)
        - Euro: ECB Rate + HICP Inflation
        """)

with col2:
    with st.expander("📊 Key Insights"):
        st.markdown("""
        **How It Works:**
        
        1. **Higher US-Euro Differential** → USD more attractive → EUR/USD **DOWN**
        2. **Lower US-Euro Differential** → EUR more competitive → EUR/USD **UP**
        
        **Why Breakeven vs Actual Inflation?**
        - Markets trade on **expectations**, not reality
        - Breakeven inflation (R² = 30%) >> Core PCE (R² = 3%)
        - Forward-looking > backward-looking
        
        **Model Limitations:**
        - Explains 30% of variance (other factors: growth, risk, politics)
        - Based on normal market conditions
        - Crisis periods may behave differently
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em;">
    💱 EUR/USD Forecaster | Model: Real Rate Differential Analysis<br>
    Based on empirical relationship: Corr = -0.550, R² = 0.302<br>
    ⚠️ Forecasts are for informational purposes only and do not constitute investment advice
</div>
""", unsafe_allow_html=True)
