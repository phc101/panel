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
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="main-header">EUR/USD Spread Prognosis Tool 📊</div>', unsafe_allow_html=True)
st.markdown("**Forecast EUR/USD based on 30Y-10Y Treasury Spread (+0.878 Correlation)**")

# Sidebar
with st.sidebar:
    st.header("📁 Data Upload")
    st.markdown("Upload CSV files from Investing.com")
    
    eurusd_file = st.file_uploader("EUR/USD Historical Data", type=['csv'])
    ffr_file = st.file_uploader("Fed Funds Rate (FEDFUNDS)", type=['csv'])
    dgs10_file = st.file_uploader("10Y Treasury (DGS10)", type=['csv'])
    dgs30_file = st.file_uploader("30Y Treasury (DGS30)", type=['csv'])
    
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

# Main processing function
def process_data(eurusd_df, ffr_df, dgs10_df, dgs30_df):
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
            
            # Find FFR (monthly, more tolerance)
            ffr_before = ffr_df[ffr_df['Date'] <= eur_date]
            if len(ffr_before) > 0:
                ffr_val = ffr_before.iloc[-1]['Value']
                
                merged_data.append({
                    'Date': eur_date,
                    'EURUSD': row['Close'],
                    'FFR': ffr_val,
                    '10Y': closest_rates['Value_10Y'],
                    '30Y': closest_rates['Value_30Y']
                })
    
    df = pd.DataFrame(merged_data)
    
    # Calculate spreads
    df['Spread_10Y_FFR'] = df['10Y'] - df['FFR']
    df['Spread_30Y_FFR'] = df['30Y'] - df['FFR']
    df['Spread_30Y_10Y'] = df['30Y'] - df['10Y']
    
    return df

# Calculate prognosis
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
    
    # Predict EUR/USD for target spread
    predicted_eurusd = slope * target_spread + intercept
    
    # Current values
    current_spread = df['Spread_30Y_10Y'].iloc[-1]
    current_eurusd = df['EURUSD'].iloc[-1]
    
    # Change
    spread_change = target_spread - current_spread
    eurusd_change = predicted_eurusd - current_eurusd
    eurusd_change_pct = (eurusd_change / current_eurusd) * 100
    
    return {
        'predicted_eurusd': predicted_eurusd,
        'current_eurusd': current_eurusd,
        'current_spread': current_spread,
        'target_spread': target_spread,
        'spread_change': spread_change,
        'eurusd_change': eurusd_change,
        'eurusd_change_pct': eurusd_change_pct,
        'correlation': corr,
        'slope': slope,
        'intercept': intercept
    }

# Main app logic
if all([eurusd_file, ffr_file, dgs10_file, dgs30_file]):
    try:
        # Parse all files
        eurusd_df = parse_eurusd_investing(eurusd_file)
        ffr_df = parse_fred(ffr_file)
        dgs10_df = parse_fred(dgs10_file)
        dgs30_df = parse_fred(dgs30_file)
        
        # Process and merge
        with st.spinner("Processing data..."):
            df = process_data(eurusd_df, ffr_df, dgs10_df, dgs30_df)
        
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
            
            **Target State:**
            - Target Spread: {prognosis['target_spread']:.2f}%
            - Predicted EUR/USD: {prognosis['predicted_eurusd']:.4f}
            
            **Changes:**
            - Spread Change: {prognosis['spread_change']:+.2f}%
            - EUR/USD Change: {prognosis['eurusd_change']:+.4f} ({prognosis['eurusd_change_pct']:+.2f}%)
            """)
        
        # Visualization
        st.markdown('<div class="sub-header">📈 Visualization</div>', unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["Prognosis Chart", "Historical Correlation", "Scenario Analysis"])
        
        with tab1:
            # Create scatter plot with prognosis
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
        
        with tab2:
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
        
        with tab3:
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
            if abs(prognosis['eurusd_change_pct']) > 5:
                st.markdown('<div class="warning-box">', unsafe_allow_html=True)
                st.markdown("### 🔴 High Impact Scenario")
                st.markdown(f"Predicted change of **{prognosis['eurusd_change_pct']:+.2f}%** is significant.")
                st.markdown("**Recommendations:**")
                st.markdown("- Consider hedging FX exposure")
                st.markdown("- Use options for large moves")
                st.markdown("- Monitor Fed/ECB policy closely")
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown('<div class="success-box">', unsafe_allow_html=True)
                st.markdown("### 🟢 Moderate Impact Scenario")
                st.markdown(f"Predicted change of **{prognosis['eurusd_change_pct']:+.2f}%** is manageable.")
                st.markdown("**Recommendations:**")
                st.markdown("- Standard hedging appropriate")
                st.markdown("- Range-bound strategies work")
                st.markdown("- Monitor spread developments")
                st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 📌 Key Levels to Watch")
            
            resistance = prognosis['current_eurusd'] + 0.02
            support = prognosis['current_eurusd'] - 0.02
            
            st.markdown(f"""
            **Technical Levels:**
            - **Resistance:** {resistance:.4f}
            - **Current:** {prognosis['current_eurusd']:.4f}
            - **Support:** {support:.4f}
            - **Target:** {prognosis['predicted_eurusd']:.4f}
            
            **Spread Levels:**
            - **Current:** {prognosis['current_spread']:.2f}%
            - **Target:** {prognosis['target_spread']:.2f}%
            - **Critical:** 0.40% (flattening) / 0.90% (steep)
            """)
        
        # Download results
        st.markdown('<div class="sub-header">💾 Export Results</div>', unsafe_allow_html=True)
        
        # Prepare export data
        export_data = pd.DataFrame([{
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'Current_EURUSD': prognosis['current_eurusd'],
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
    st.info("👆 **Please upload all 4 CSV files from the sidebar to start**")
    
    with st.expander("📖 How to Use This Tool"):
        st.markdown("""
        ### Step 1: Get Data from Investing.com / FRED
        
        **EUR/USD Historical Data** (Investing.com):
        1. Go to https://www.investing.com/currencies/eur-usd-historical-data
        2. Select date range (suggest 5 years)
        3. Download CSV
        
        **US Treasury Data** (FRED):
        1. Fed Funds Rate: https://fred.stlouisfed.org/series/FEDFUNDS
        2. 10Y Treasury: https://fred.stlouisfed.org/series/DGS10
        3. 30Y Treasury: https://fred.stlouisfed.org/series/DGS30
        4. Download as CSV for each
        
        ### Step 2: Upload Files
        - Use the sidebar file uploaders
        - All 4 files are required
        
        ### Step 3: Set Your Scenario
        - Choose from preset scenarios or create custom
        - Set target 10Y and 30Y yields
        - Tool calculates expected EUR/USD
        
        ### Step 4: Analyze Results
        - View predicted EUR/USD rate
        - See impact of spread changes
        - Compare multiple scenarios
        - Export results
        
        ### 🎯 How It Works
        
        This tool uses the **+0.878 correlation** between EUR/USD and the 30Y-10Y Treasury spread:
        
        - **Spread WIDENS** → EUR/USD typically RISES (USD weakens)
        - **Spread NARROWS** → EUR/USD typically FALLS (USD strengthens)
        
        Based on your target yields, the model predicts where EUR/USD should trade.
        
        ### ⚠️ Important Notes
        
        - **Correlation is historical** - past performance doesn't guarantee future results
        - **Bear vs Bull steepener** - same spread can mean different things
        - **Use as guidance** - combine with other analysis and risk management
        - **For professional use** - suitable for FX hedging decisions
        """)
    
    with st.expander("📊 Example Scenarios"):
        st.markdown("""
        ### Bull Steepener (Growth Optimism)
        - 10Y: 4.2% → 4.5%
        - 30Y: 4.8% → 5.3%
        - Spread: 0.60% → 0.80%
        - **Expected:** EUR/USD rises (risk-on)
        
        ### Bear Steepener (Fiscal Crisis)
        - 10Y: 4.2% → 4.0%
        - 30Y: 4.8% → 5.5%
        - Spread: 0.60% → 1.50%
        - **Expected:** EUR/USD rises initially, but may reverse
        
        ### Flattening (Fed Tightening)
        - 10Y: 4.2% → 4.8%
        - 30Y: 4.8% → 5.0%
        - Spread: 0.60% → 0.20%
        - **Expected:** EUR/USD falls (USD strengthens)
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <b>EUR/USD Spread Prognosis Tool</b> | 
    Correlation-based forecast using 30Y-10Y Treasury spread | 
    For professional FX hedging decisions
</div>
""", unsafe_allow_html=True)
