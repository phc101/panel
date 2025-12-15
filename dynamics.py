import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import io

# Page config
st.set_page_config(
    page_title="EUR/USD Spread Prognosis Tool",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #0051a5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2ca02c;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #0051a5;
    }
    .prognosis-box {
        background-color: #ffffcc;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 2px solid #ff7f0e;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #ffcccc;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #d62728;
    }
    .success-box {
        background-color: #ccffcc;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2ca02c;
    }
    .neutral-box {
        background-color: #e6e6fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #9467bd;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="main-header">EUR/USD Spread Prognosis Tool 📊</div>', unsafe_allow_html=True)
st.markdown("**Forecast EUR/USD based on 30Y-10Y Treasury Spread (+0.878 Correlation)**")

# Sidebar
with st.sidebar:
    st.header("📁 Data Upload")
    st.markdown("Upload CSV files from Investing.com / FRED")
    
    eurusd_file = st.file_uploader("EUR/USD Historical Data", type=['csv'], 
                                   help="From Investing.com")
    dgs10_file = st.file_uploader("10Y Treasury (DGS10)", type=['csv'],
                                  help="From FRED")
    dgs30_file = st.file_uploader("30Y Treasury (DGS30)", type=['csv'],
                                  help="From FRED")
    
    st.markdown("---")
    st.header("⚙️ Model Settings")
    
    correlation = st.slider("EUR/USD vs 30Y-10Y Correlation", 
                           min_value=0.0, max_value=1.0, value=0.878, step=0.001,
                           help="Historical correlation: +0.878")
    
    use_recent_corr = st.checkbox("Use Recent Correlation Only", 
                                  help="Use last 52 weeks instead of full period")
    
    st.markdown("---")
    st.header("🎯 Prognosis Scenarios")
    
    scenario = st.selectbox(
        "Select Scenario",
        ["Custom", "Bull Steepener", "Bear Steepener", "Flattening", "Current Stable"]
    )

# Helper function to parse Investing.com EUR/USD format
def parse_eurusd_investing(file):
    df = pd.read_csv(file, encoding='utf-8-sig')
    df.columns = ['Date', 'Close', 'Open', 'High', 'Low', 'Volume', 'Change']
    df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y', errors='coerce')
    df['Close'] = df['Close'].astype(str).str.replace(',', '.').astype(float)
    return df.sort_values('Date')[['Date', 'Close']].dropna()

# Helper function to parse FRED format
def parse_fred(file):
    df = pd.read_csv(file)
    df.columns = ['Date', 'Value']
    df['Date'] = pd.to_datetime(df['Date'])
    df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
    return df.dropna()

# Main processing function (without Fed Funds)
def process_data(eurusd_df, dgs10_df, dgs30_df):
    # Merge daily rates
    rates = dgs10_df.merge(dgs30_df, on='Date', how='inner', suffixes=('_10Y', '_30Y'))
    
    # For each EUR/USD date, find closest rate
    merged_data = []
    for idx, row in eurusd_df.iterrows():
        eur_date = row['Date']
        
        # Find closest rates (within 7 days)
        rate_window = rates[abs(rates['Date'] - eur_date) <= timedelta(days=7)]
        if len(rate_window) > 0:
            closest_idx = (rate_window['Date'] - eur_date).abs().idxmin()
            closest_rates = rates.loc[closest_idx]
            
            merged_data.append({
                'Date': eur_date,
                'EURUSD': row['Close'],
                '10Y': closest_rates['Value_10Y'],
                '30Y': closest_rates['Value_30Y']
            })
    
    df = pd.DataFrame(merged_data)
    
    # Calculate spreads
    df['Spread_30Y_10Y'] = df['30Y'] - df['10Y']
    
    return df

# Calculate prognosis and fair value
def calculate_prognosis(df, target_spread, correlation_val, use_recent=False):
    if use_recent:
        recent_df = df.tail(52)
        corr = recent_df['EURUSD'].corr(recent_df['Spread_30Y_10Y'])
        base_data = recent_df
    else:
        corr = correlation_val
        base_data = df
    
    # Linear regression
    z = np.polyfit(base_data['Spread_30Y_10Y'], base_data['EURUSD'], 1)
    slope, intercept = z[0], z[1]
    
    # Calculate fair value for all historical data
    df['Fair_Value'] = slope * df['Spread_30Y_10Y'] + intercept
    df['Deviation'] = df['EURUSD'] - df['Fair_Value']
    df['Deviation_Pct'] = (df['Deviation'] / df['Fair_Value']) * 100
    
    # Predict EUR/USD for target spread
    predicted_eurusd = slope * target_spread + intercept
    
    # Current values
    current_spread = df['Spread_30Y_10Y'].iloc[-1]
    current_eurusd = df['EURUSD'].iloc[-1]
    current_fair_value = df['Fair_Value'].iloc[-1]
    current_deviation = df['Deviation_Pct'].iloc[-1]
    
    # Change
    spread_change = target_spread - current_spread
    eurusd_change = predicted_eurusd - current_eurusd
    eurusd_change_pct = (eurusd_change / current_eurusd) * 100
    
    return {
        'predicted_eurusd': predicted_eurusd,
        'current_eurusd': current_eurusd,
        'current_fair_value': current_fair_value,
        'current_deviation': current_deviation,
        'current_spread': current_spread,
        'target_spread': target_spread,
        'spread_change': spread_change,
        'eurusd_change': eurusd_change,
        'eurusd_change_pct': eurusd_change_pct,
        'correlation': corr,
        'slope': slope,
        'intercept': intercept,
        'df_with_fv': df  # Return df with fair value calculated
    }

# Main app logic
if all([eurusd_file, dgs10_file, dgs30_file]):
    try:
        # Parse all files
        eurusd_df = parse_eurusd_investing(eurusd_file)
        dgs10_df = parse_fred(dgs10_file)
        dgs30_df = parse_fred(dgs30_file)
        
        # Process and merge (no Fed Funds needed)
        with st.spinner("Processing data..."):
            df = process_data(eurusd_df, dgs10_df, dgs30_df)
        
        if len(df) == 0:
            st.error("❌ No overlapping data found. Check date ranges.")
            st.stop()
        
        st.success(f"✅ Loaded {len(df)} observations from {df['Date'].min().date()} to {df['Date'].max().date()}")
        
        # Current values
        current = df.iloc[-1]
        
        # Display current metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("EUR/USD", f"{current['EURUSD']:.4f}")
        with col2:
            st.metric("30Y-10Y Spread", f"{current['Spread_30Y_10Y']:.2f}%")
        with col3:
            st.metric("10Y Treasury", f"{current['10Y']:.2f}%")
        with col4:
            st.metric("30Y Treasury", f"{current['30Y']:.2f}%")
        
        # Correlation calculation
        full_corr = df['EURUSD'].corr(df['Spread_30Y_10Y'])
        recent_corr = df.tail(52)['EURUSD'].corr(df.tail(52)['Spread_30Y_10Y'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"📊 **Full Period Correlation:** {full_corr:+.3f}")
        with col2:
            st.info(f"📈 **Recent 52-Week Correlation:** {recent_corr:+.3f}")
        
        # Scenario setup
        st.markdown('<div class="sub-header">🎯 Prognosis Scenario</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if scenario == "Custom":
                target_10y = st.number_input("Target 10Y Yield (%)", 
                                            value=float(current['10Y']), 
                                            min_value=0.0, max_value=10.0, step=0.1)
                target_30y = st.number_input("Target 30Y Yield (%)", 
                                            value=float(current['30Y']), 
                                            min_value=0.0, max_value=10.0, step=0.1)
            elif scenario == "Bull Steepener":
                st.info("📈 Growth optimism: Both rise, 30Y more")
                target_10y = st.slider("10Y", value=4.5, min_value=3.0, max_value=6.0, step=0.1)
                target_30y = target_10y + 0.8  # Wider spread
                st.write(f"Auto-calculated 30Y: {target_30y:.2f}%")
            elif scenario == "Bear Steepener":
                st.warning("⚠️ Fiscal crisis: 10Y stable, 30Y surges")
                target_10y = st.slider("10Y", value=4.1, min_value=3.0, max_value=5.0, step=0.1)
                target_30y = st.slider("30Y", value=5.2, min_value=4.5, max_value=6.5, step=0.1)
            elif scenario == "Flattening":
                st.info("📉 Fed tightening or recession fears")
                target_10y = st.slider("10Y", value=4.5, min_value=3.5, max_value=5.5, step=0.1)
                target_30y = target_10y + 0.3  # Narrow spread
                st.write(f"Auto-calculated 30Y: {target_30y:.2f}%")
            else:  # Current Stable
                st.info("➡️ Rates stay similar")
                target_10y = float(current['10Y'])
                target_30y = float(current['30Y'])
        
        with col2:
            target_spread = target_30y - target_10y
            st.metric("Target Spread", f"{target_spread:.2f}%", 
                     delta=f"{target_spread - current['Spread_30Y_10Y']:.2f}%")
            
            if target_spread > current['Spread_30Y_10Y']:
                st.success("🟢 SPREAD WIDENING → EUR/USD likely UP")
            elif target_spread < current['Spread_30Y_10Y']:
                st.error("🔴 SPREAD NARROWING → EUR/USD likely DOWN")
            else:
                st.info("⚪ SPREAD STABLE → EUR/USD likely FLAT")
        
        # Calculate prognosis
        prognosis = calculate_prognosis(df, target_spread, correlation, use_recent_corr)
        df = prognosis['df_with_fv']  # Get df with fair value
        
        # Fair Value Analysis Box
        st.markdown('<div class="sub-header">⚖️ Fair Value Analysis</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown("### Actual EUR/USD")
            st.markdown(f"## **{prognosis['current_eurusd']:.4f}**")
            st.markdown("*(Market Price)*")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown("### Fair Value")
            st.markdown(f"## **{prognosis['current_fair_value']:.4f}**")
            st.markdown("*(Model Based on Spread)*")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            deviation = prognosis['current_deviation']
            if abs(deviation) < 2:
                box_class = "neutral-box"
                signal = "✅ FAIR VALUED"
                color = "🟢"
            elif deviation > 2:
                box_class = "warning-box"
                signal = "⚠️ OVERVALUED"
                color = "🔴"
            else:
                box_class = "success-box"
                signal = "💎 UNDERVALUED"
                color = "🟢"
            
            st.markdown(f'<div class="{box_class}">', unsafe_allow_html=True)
            st.markdown("### Deviation")
            st.markdown(f"## **{deviation:+.2f}%**")
            st.markdown(f"**{color} {signal}**")
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Display prognosis
        st.markdown('<div class="sub-header">📊 Prognosis Results</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="prognosis-box">', unsafe_allow_html=True)
            st.markdown("### Current EUR/USD")
            st.markdown(f"## **{prognosis['current_eurusd']:.4f}**")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="prognosis-box">', unsafe_allow_html=True)
            st.markdown("### Predicted EUR/USD")
            st.markdown(f"## **{prognosis['predicted_eurusd']:.4f}**")
            change_color = "🟢" if prognosis['eurusd_change'] > 0 else "🔴"
            st.markdown(f"{change_color} {prognosis['eurusd_change']:+.4f} ({prognosis['eurusd_change_pct']:+.2f}%)")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="prognosis-box">', unsafe_allow_html=True)
            st.markdown("### Target Level")
            if prognosis['eurusd_change_pct'] > 2:
                st.markdown("## 🟢 **BULLISH EUR**")
                st.markdown("Consider EUR strength")
            elif prognosis['eurusd_change_pct'] < -2:
                st.markdown("## 🔴 **BEARISH EUR**")
                st.markdown("Consider EUR weakness")
            else:
                st.markdown("## ⚪ **NEUTRAL**")
                st.markdown("Range-bound expected")
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Detailed breakdown
        with st.expander("📋 Detailed Calculation"):
            st.markdown(f"""
            **Model Parameters:**
            - Correlation Used: {prognosis['correlation']:+.3f}
            - Regression Slope: {prognosis['slope']:.4f}
            - Regression Intercept: {prognosis['intercept']:.4f}
            
            **Formula:** EUR/USD = {prognosis['slope']:.4f} × Spread + {prognosis['intercept']:.4f}
            
            **Current State:**
            - Current Spread: {prognosis['current_spread']:.2f}%
            - Current EUR/USD: {prognosis['current_eurusd']:.4f}
            - Fair Value: {prognosis['current_fair_value']:.4f}
            - Deviation: {prognosis['current_deviation']:+.2f}%
            
            **Target State:**
            - Target Spread: {prognosis['target_spread']:.2f}%
            - Predicted EUR/USD: {prognosis['predicted_eurusd']:.4f}
            
            **Changes:**
            - Spread Change: {prognosis['spread_change']:+.2f}%
            - EUR/USD Change: {prognosis['eurusd_change']:+.4f} ({prognosis['eurusd_change_pct']:+.2f}%)
            """)
        
        # Visualization
        st.markdown('<div class="sub-header">📈 Visualization</div>', unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4 = st.tabs(["Fair Value", "Prognosis Chart", "Historical Correlation", "Scenario Analysis"])
        
        with tab1:
            # Fair Value Chart - NEW!
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('EUR/USD: Actual vs Fair Value', 'Deviation from Fair Value (%)'),
                vertical_spacing=0.15,
                row_heights=[0.6, 0.4]
            )
            
            # Top panel: Actual vs Fair Value
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['EURUSD'],
                name='Actual EUR/USD',
                line=dict(color='#0051a5', width=2.5),
                hovertemplate='%{x}<br>Actual: %{y:.4f}<extra></extra>'
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Fair_Value'],
                name='Fair Value',
                line=dict(color='#ff7f0e', width=2, dash='dash'),
                hovertemplate='%{x}<br>Fair Value: %{y:.4f}<extra></extra>'
            ), row=1, col=1)
            
            # Shade overvalued/undervalued
            overvalued = df['EURUSD'] > df['Fair_Value']
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['EURUSD'],
                fill='tonexty',
                fillcolor='rgba(255, 0, 0, 0.1)',
                line=dict(width=0),
                showlegend=False,
                hoverinfo='skip'
            ), row=1, col=1)
            
            # Current points
            current_date = df['Date'].iloc[-1]
            fig.add_trace(go.Scatter(
                x=[current_date], y=[df['EURUSD'].iloc[-1]],
                mode='markers',
                name='Current Actual',
                marker=dict(size=15, color='green', symbol='circle', 
                           line=dict(color='black', width=2)),
                hovertemplate='Current Actual<br>%{y:.4f}<extra></extra>'
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=[current_date], y=[df['Fair_Value'].iloc[-1]],
                mode='markers',
                name='Current Fair Value',
                marker=dict(size=15, color='orange', symbol='square',
                           line=dict(color='black', width=2)),
                hovertemplate='Current Fair Value<br>%{y:.4f}<extra></extra>'
            ), row=1, col=1)
            
            # Bottom panel: Deviation
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Deviation_Pct'],
                name='Deviation %',
                fill='tozeroy',
                fillcolor='rgba(128, 0, 128, 0.2)',
                line=dict(color='purple', width=2),
                hovertemplate='%{x}<br>Deviation: %{y:+.2f}%<extra></extra>'
            ), row=2, col=1)
            
            # Zero line
            fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, row=2, col=1)
            
            # +/- 2% bands
            fig.add_hline(y=2, line_dash="dash", line_color="red", line_width=1, 
                         opacity=0.5, row=2, col=1)
            fig.add_hline(y=-2, line_dash="dash", line_color="green", line_width=1,
                         opacity=0.5, row=2, col=1)
            
            # Current deviation
            fig.add_trace(go.Scatter(
                x=[current_date], y=[df['Deviation_Pct'].iloc[-1]],
                mode='markers',
                name='Current Deviation',
                marker=dict(size=15, 
                           color='red' if df['Deviation_Pct'].iloc[-1] > 0 else 'green',
                           symbol='circle',
                           line=dict(color='black', width=2)),
                hovertemplate='Current<br>%{y:+.2f}%<extra></extra>'
            ), row=2, col=1)
            
            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_yaxes(title_text="EUR/USD", row=1, col=1)
            fig.update_yaxes(title_text="Deviation (%)", row=2, col=1)
            
            fig.update_layout(
                height=800,
                showlegend=True,
                hovermode='x unified',
                title_text=f'Fair Value Analysis | Current Deviation: {df["Deviation_Pct"].iloc[-1]:+.2f}% | Correlation: {prognosis["correlation"]:+.3f}'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Fair value statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Mean Deviation", f"{df['Deviation_Pct'].mean():+.2f}%")
            with col2:
                st.metric("Std Deviation", f"{df['Deviation_Pct'].std():.2f}%")
            with col3:
                recent_dev = df.tail(52)['Deviation_Pct'].mean()
                st.metric("Recent 52w Mean", f"{recent_dev:+.2f}%")
        
        with tab2:
            # Original prognosis scatter plot
            fig = go.Figure()
            
            # Historical data
            fig.add_trace(go.Scatter(
                x=df['Spread_30Y_10Y'],
                y=df['EURUSD'],
                mode='markers',
                name='Historical',
                marker=dict(size=5, color='lightblue', opacity=0.5),
                hovertemplate='Spread: %{x:.2f}%<br>EUR/USD: %{y:.4f}<extra></extra>'
            ))
            
            # Recent data highlighted
            recent = df.tail(52)
            fig.add_trace(go.Scatter(
                x=recent['Spread_30Y_10Y'],
                y=recent['EURUSD'],
                mode='markers',
                name='Recent 52w',
                marker=dict(size=7, color='blue', opacity=0.7),
                hovertemplate='Spread: %{x:.2f}%<br>EUR/USD: %{y:.4f}<extra></extra>'
            ))
            
            # Regression line
            x_range = np.linspace(df['Spread_30Y_10Y'].min(), df['Spread_30Y_10Y'].max(), 100)
            y_pred = prognosis['slope'] * x_range + prognosis['intercept']
            fig.add_trace(go.Scatter(
                x=x_range,
                y=y_pred,
                mode='lines',
                name=f'Trend (r={prognosis["correlation"]:.3f})',
                line=dict(color='red', width=2, dash='dash')
            ))
            
            # Current point
            fig.add_trace(go.Scatter(
                x=[prognosis['current_spread']],
                y=[prognosis['current_eurusd']],
                mode='markers+text',
                name='Current',
                marker=dict(size=15, color='green', symbol='star'),
                text=['NOW'],
                textposition='top center',
                hovertemplate='Current<br>Spread: %{x:.2f}%<br>EUR/USD: %{y:.4f}<extra></extra>'
            ))
            
            # Target point
            fig.add_trace(go.Scatter(
                x=[prognosis['target_spread']],
                y=[prognosis['predicted_eurusd']],
                mode='markers+text',
                name='Target',
                marker=dict(size=15, color='orange', symbol='star'),
                text=['TARGET'],
                textposition='top center',
                hovertemplate='Target<br>Spread: %{x:.2f}%<br>EUR/USD: %{y:.4f}<extra></extra>'
            ))
            
            # Arrow from current to target
            fig.add_annotation(
                x=prognosis['target_spread'],
                y=prognosis['predicted_eurusd'],
                ax=prognosis['current_spread'],
                ay=prognosis['current_eurusd'],
                xref='x', yref='y',
                axref='x', ayref='y',
                showarrow=True,
                arrowhead=3,
                arrowsize=2,
                arrowwidth=2,
                arrowcolor='red'
            )
            
            fig.update_layout(
                title='EUR/USD Prognosis Based on 30Y-10Y Spread',
                xaxis_title='30Y-10Y Spread (%)',
                yaxis_title='EUR/USD',
                height=600,
                hovermode='closest',
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            # Time series
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('EUR/USD', '30Y-10Y Spread'),
                vertical_spacing=0.15,
                row_heights=[0.5, 0.5]
            )
            
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['EURUSD'],
                name='EUR/USD',
                line=dict(color='#0051a5', width=2)
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Spread_30Y_10Y'],
                name='30Y-10Y Spread',
                fill='tozeroy',
                line=dict(color='#2ca02c', width=2)
            ), row=2, col=1)
            
            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_yaxes(title_text="EUR/USD", row=1, col=1)
            fig.update_yaxes(title_text="Spread (%)", row=2, col=1)
            
            fig.update_layout(height=700, showlegend=True, hovermode='x unified')
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab4:
            # Multiple scenarios
            st.markdown("**Compare Multiple Scenarios:**")
            
            scenarios_data = []
            scenario_configs = {
                "Current": (current['10Y'], current['30Y']),
                "Bull Steepener": (4.2, 5.0),
                "Bear Steepener": (4.0, 5.5),
                "Flattening": (4.5, 4.8),
                "Normalization": (4.0, 4.6),
            }
            
            for scen_name, (y10, y30) in scenario_configs.items():
                spread = y30 - y10
                prog = calculate_prognosis(df, spread, correlation, use_recent_corr)
                scenarios_data.append({
                    'Scenario': scen_name,
                    '10Y': y10,
                    '30Y': y30,
                    'Spread': spread,
                    'EUR/USD': prog['predicted_eurusd'],
                    'Change %': prog['eurusd_change_pct']
                })
            
            scenarios_df = pd.DataFrame(scenarios_data)
            
            st.dataframe(
                scenarios_df.style.format({
                    '10Y': '{:.2f}%',
                    '30Y': '{:.2f}%',
                    'Spread': '{:.2f}%',
                    'EUR/USD': '{:.4f}',
                    'Change %': '{:+.2f}%'
                }).background_gradient(subset=['Change %'], cmap='RdYlGn', vmin=-10, vmax=10),
                use_container_width=True,
                hide_index=True
            )
            
            # Bar chart
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=scenarios_df['Scenario'],
                y=scenarios_df['Change %'],
                marker_color=['green' if x > 0 else 'red' for x in scenarios_df['Change %']],
                text=scenarios_df['Change %'].apply(lambda x: f'{x:+.1f}%'),
                textposition='outside'
            ))
            
            fig.update_layout(
                title='EUR/USD Change % Across Scenarios',
                xaxis_title='Scenario',
                yaxis_title='EUR/USD Change (%)',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Risk assessment
        st.markdown('<div class="sub-header">⚠️ Risk Assessment</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Fair value assessment
            if abs(prognosis['current_deviation']) > 2:
                st.markdown('<div class="warning-box">', unsafe_allow_html=True)
                if prognosis['current_deviation'] > 2:
                    st.markdown("### 🔴 EUR Overvalued")
                    st.markdown(f"EUR/USD is **{prognosis['current_deviation']:.2f}%** above fair value")
                    st.markdown("**Trading Signal:** Consider SELLING EUR")
                    st.markdown(f"**Target:** {prognosis['current_fair_value']:.4f} (fair value)")
                else:
                    st.markdown("### 🟢 EUR Undervalued")
                    st.markdown(f"EUR/USD is **{abs(prognosis['current_deviation']):.2f}%** below fair value")
                    st.markdown("**Trading Signal:** Consider BUYING EUR")
                    st.markdown(f"**Target:** {prognosis['current_fair_value']:.4f} (fair value)")
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown('<div class="success-box">', unsafe_allow_html=True)
                st.markdown("### ✅ EUR Fairly Valued")
                st.markdown(f"EUR/USD within ±2% of fair value ({prognosis['current_deviation']:+.2f}%)")
                st.markdown("**Trading Signal:** NEUTRAL / HOLD")
                st.markdown("**Recommendation:** Standard hedging appropriate")
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Prognosis impact
            if abs(prognosis['eurusd_change_pct']) > 5:
                st.markdown('<div class="warning-box">', unsafe_allow_html=True)
                st.markdown("### 🔴 High Impact Prognosis")
                st.markdown(f"Predicted change of **{prognosis['eurusd_change_pct']:+.2f}%** is significant.")
                st.markdown("**Recommendations:**")
                st.markdown("- Consider hedging FX exposure")
                st.markdown("- Use options for large moves")
                st.markdown("- Monitor spread developments")
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown('<div class="success-box">', unsafe_allow_html=True)
                st.markdown("### 🟢 Moderate Impact Prognosis")
                st.markdown(f"Predicted change of **{prognosis['eurusd_change_pct']:+.2f}%** is manageable.")
                st.markdown("**Recommendations:**")
                st.markdown("- Standard hedging appropriate")
                st.markdown("- Range-bound strategies work")
                st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 📌 Key Levels to Watch")
            
            resistance = prognosis['current_eurusd'] + 0.02
            support = prognosis['current_eurusd'] - 0.02
            
            st.markdown(f"""
            **Technical Levels:**
            - **Resistance:** {resistance:.4f}
            - **Current:** {prognosis['current_eurusd']:.4f}
            - **Fair Value:** {prognosis['current_fair_value']:.4f}
            - **Support:** {support:.4f}
            - **Target:** {prognosis['predicted_eurusd']:.4f}
            
            **Spread Levels:**
            - **Current:** {prognosis['current_spread']:.2f}%
            - **Target:** {prognosis['target_spread']:.2f}%
            - **Critical:** 0.40% (flattening) / 0.90% (steep)
            
            **Deviation Stats:**
            - **Current:** {prognosis['current_deviation']:+.2f}%
            - **Mean:** {df['Deviation_Pct'].mean():+.2f}%
            - **Std Dev:** {df['Deviation_Pct'].std():.2f}%
            """)
        
        # Download results
        st.markdown('<div class="sub-header">💾 Export Results</div>', unsafe_allow_html=True)
        
        # Prepare export data
        export_data = pd.DataFrame([{
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'Current_EURUSD': prognosis['current_eurusd'],
            'Fair_Value': prognosis['current_fair_value'],
            'Deviation_Pct': prognosis['current_deviation'],
            'Current_Spread': prognosis['current_spread'],
            'Target_10Y': target_10y,
            'Target_30Y': target_30y,
            'Target_Spread': prognosis['target_spread'],
            'Predicted_EURUSD': prognosis['predicted_eurusd'],
            'Change_Absolute': prognosis['eurusd_change'],
            'Change_Percent': prognosis['eurusd_change_pct'],
            'Correlation_Used': prognosis['correlation'],
            'Scenario': scenario
        }])
        
        csv = export_data.to_csv(index=False)
        st.download_button(
            label="📥 Download Prognosis Results (CSV)",
            data=csv,
            file_name=f"eurusd_prognosis_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"❌ Error processing data: {str(e)}")
        st.exception(e)

else:
    # Instructions when no files uploaded
    st.info("👆 **Please upload 3 CSV files from the sidebar to start**")
    
    with st.expander("📖 How to Use This Tool"):
        st.markdown("""
        ### Step 1: Get Data from Investing.com / FRED
        
        **EUR/USD Historical Data** (Investing.com):
        1. Go to: https://www.investing.com/currencies/eur-usd-historical-data
        2. Select date range (suggest 5 years)
        3. Download CSV
        
        **US Treasury Data** (FRED):
        1. 10Y Treasury: https://fred.stlouisfed.org/series/DGS10
        2. 30Y Treasury: https://fred.stlouisfed.org/series/DGS30
        3. Download each as CSV
        
        **Note:** Fed Funds Rate is NOT needed for this analysis!
        
        ### Step 2: Upload Files
        - Use the sidebar file uploaders
        - Only 3 files required: EUR/USD, 10Y, 30Y
        
        ### Step 3: Analyze Fair Value
        - See if EUR/USD is overvalued or undervalued vs spread-based model
        - Current deviation shown in % (above/below fair value)
        - Trading signals automatically generated
        
        ### Step 4: Set Your Scenario
        - Choose from preset scenarios or create custom
        - Set target 10Y and 30Y yields
        - Tool calculates expected EUR/USD
        
        ### Step 5: Review Results
        - View predicted EUR/USD rate
        - See fair value analysis
        - Compare multiple scenarios
        - Export results
        
        ### 🎯 Fair Value Model
        
        The tool calculates **fair value EUR/USD** based on the 30Y-10Y spread:
        
        - **Correlation:** +0.878 (very strong)
        - **Formula:** EUR/USD = 0.23 × Spread + 1.03
        - **Deviation > +2%:** EUR overvalued → Sell signal
        - **Deviation < -2%:** EUR undervalued → Buy signal
        - **Deviation ±2%:** Fair valued → Neutral
        
        ### 📊 Key Features
        
        1. **Fair Value Chart:** See actual vs model-predicted EUR/USD
        2. **Deviation Chart:** Track over/undervaluation over time
        3. **Prognosis:** Predict EUR/USD based on target spreads
        4. **Scenarios:** Compare multiple spread scenarios
        5. **Export:** Download results for reports
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <b>EUR/USD Spread Prognosis Tool v2</b> | 
    Fair value analysis + Correlation-based forecast | 
    For professional FX hedging decisions
</div>
""", unsafe_allow_html=True)
