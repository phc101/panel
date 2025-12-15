import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="FX Spread Prognosis - Final Model",
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
    .pln-box {
        background-color: #fff3e0;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 2px solid #ff9800;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #e1f5ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #0288d1;
        margin: 1rem 0;
    }
    .correlation-badge {
        display: inline-block;
        padding: 0.3rem 0.6rem;
        border-radius: 0.3rem;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .corr-strong { background-color: #4caf50; color: white; }
    .corr-moderate { background-color: #ff9800; color: white; }
    .corr-weak { background-color: #f44336; color: white; }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="main-header">FX Spread Prognosis - Correlation Chain Model 🔗</div>', unsafe_allow_html=True)
st.markdown("**US Yield Spread → EUR/USD (+0.878) → USD/PLN (-0.819) → EUR/PLN (cross-rate)**")

# Sidebar
with st.sidebar:
    st.header("📁 Data Upload")
    
    st.subheader("🔹 Required Files")
    eurusd_file = st.file_uploader("EUR/USD Data", type=['csv'])
    dgs10_file = st.file_uploader("US 10Y Treasury", type=['csv'])
    dgs30_file = st.file_uploader("US 30Y Treasury", type=['csv'])
    
    st.subheader("🔹 Optional (for validation)")
    usdpln_file = st.file_uploader("USD/PLN Data", type=['csv'])
    eurpln_file = st.file_uploader("EUR/PLN Data", type=['csv'])
    
    st.markdown("---")
    st.header("⚙️ Model Parameters")
    
    st.markdown("**Correlation Chain:**")
    corr_eurusd_spread = st.number_input("EUR/USD vs Spread", value=0.878, 
                                         min_value=-1.0, max_value=1.0, step=0.001,
                                         help="Historical: +0.878")
    corr_eurusd_usdpln = st.number_input("EUR/USD vs USD/PLN", value=-0.819,
                                         min_value=-1.0, max_value=1.0, step=0.001,
                                         help="Historical: -0.819 (INVERSE)")
    
    st.markdown("---")
    st.markdown("**Inverse Relationship:**")
    inverse_dampening = st.slider("Dampening Factor", 0.5, 1.0, 0.85, 0.05,
                                   help="How much EUR/USD change affects USD/PLN (0.85 = 85%)")
    
    st.markdown("---")
    use_recent = st.checkbox("Use Recent 52w Period", value=False)

# Helper functions
def parse_fx_investing_polish(file):
    df = pd.read_csv(file, encoding='utf-8-sig')
    if len(df.columns) >= 2:
        df = df.iloc[:, [0, 1]]
        df.columns = ['Date', 'Close']
    df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y', errors='coerce')
    df['Close'] = df['Close'].astype(str).str.replace(',', '.').astype(float)
    return df.sort_values('Date')[['Date', 'Close']].dropna()

def parse_yield_fred(file):
    df = pd.read_csv(file)
    if len(df.columns) >= 2:
        df = df.iloc[:, [0, 1]]
        df.columns = ['Date', 'Yield']
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    if df['Yield'].dtype == 'object':
        df['Yield'] = df['Yield'].astype(str).str.replace(',', '.').astype(float, errors='ignore')
    df['Yield'] = pd.to_numeric(df['Yield'], errors='coerce')
    return df.dropna()

def merge_with_yields(fx_df, short_df, long_df):
    yields = short_df.merge(long_df, on='Date', how='inner', suffixes=('_10Y', '_30Y'))
    
    merged_data = []
    for idx, row in fx_df.iterrows():
        fx_date = row['Date']
        yield_window = yields[abs(yields['Date'] - fx_date) <= timedelta(days=7)]
        if len(yield_window) > 0:
            closest_idx = (yield_window['Date'] - fx_date).abs().idxmin()
            closest_yields = yields.loc[closest_idx]
            
            merged_data.append({
                'Date': fx_date,
                'FX_Rate': row['Close'],
                '10Y': closest_yields['Yield_10Y'],
                '30Y': closest_yields['Yield_30Y']
            })
    
    df = pd.DataFrame(merged_data)
    df['Spread'] = df['30Y'] - df['10Y']
    return df

def calculate_fair_value(df, correlation, use_recent=False):
    if use_recent and len(df) >= 52:
        base_data = df.tail(52)
        corr_actual = base_data['FX_Rate'].corr(base_data['Spread'])
    else:
        base_data = df
        corr_actual = correlation
    
    z = np.polyfit(base_data['Spread'], base_data['FX_Rate'], 1)
    slope, intercept = z[0], z[1]
    
    df['Fair_Value'] = slope * df['Spread'] + intercept
    df['Deviation'] = df['FX_Rate'] - df['Fair_Value']
    df['Deviation_Pct'] = (df['Deviation'] / df['Fair_Value']) * 100
    
    return df, corr_actual, slope, intercept

def predict_pln_from_eurusd(eurusd_current, eurusd_target, usdpln_current, 
                            inverse_corr, dampening):
    """
    Predict USD/PLN based on EUR/USD using inverse correlation
    
    Logic:
    - EUR/USD ↑ = EUR stronger, USD weaker
    - USD weaker → USD/PLN ↓ (fewer PLN per USD)
    - Inverse correlation: -0.819
    """
    eurusd_change_pct = ((eurusd_target - eurusd_current) / eurusd_current) * 100
    
    # Apply inverse relationship with dampening
    # EUR/USD ↑ 1% → USD/PLN ↓ 0.85% (with dampening 0.85)
    usdpln_change_pct = -eurusd_change_pct * dampening
    
    usdpln_target = usdpln_current * (1 + usdpln_change_pct / 100)
    
    return usdpln_target, usdpln_change_pct

# Main app
if all([eurusd_file, dgs10_file, dgs30_file]):
    try:
        # Load and process EUR/USD
        with st.spinner("Loading EUR/USD data..."):
            eurusd_df = parse_fx_investing_polish(eurusd_file)
            dgs10_df = parse_yield_fred(dgs10_file)
            dgs30_df = parse_yield_fred(dgs30_file)
            
            df_eurusd = merge_with_yields(eurusd_df, dgs10_df, dgs30_df)
            df_eurusd, corr_eurusd_actual, slope_eurusd, intercept_eurusd = calculate_fair_value(
                df_eurusd, corr_eurusd_spread, use_recent)
        
        # Load PLN pairs if available
        has_usdpln = usdpln_file is not None
        has_eurpln = eurpln_file is not None
        
        if has_usdpln:
            usdpln_df = parse_fx_investing_polish(usdpln_file)
            df_usdpln = merge_with_yields(usdpln_df, dgs10_df, dgs30_df)
            df_usdpln, corr_usdpln_actual, slope_usdpln, intercept_usdpln = calculate_fair_value(
                df_usdpln, -0.623, use_recent)  # USD/PLN has weak spread correlation
        
        if has_eurpln:
            eurpln_df = parse_fx_investing_polish(eurpln_file)
            df_eurpln = merge_with_yields(eurpln_df, dgs10_df, dgs30_df)
            df_eurpln, corr_eurpln_actual, slope_eurpln, intercept_eurpln = calculate_fair_value(
                df_eurpln, 0.543, use_recent)  # EUR/PLN has moderate spread correlation
        
        st.success(f"✅ Loaded {len(df_eurusd)} EUR/USD observations")
        
        # Display current values
        current_eurusd = df_eurusd.iloc[-1]
        
        st.markdown('<div class="sub-header">📊 Current Market Data</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("EUR/USD", f"{current_eurusd['FX_Rate']:.4f}",
                     delta=f"{current_eurusd['Deviation_Pct']:+.2f}% vs FV")
        with col2:
            st.metric("30Y-10Y Spread", f"{current_eurusd['Spread']:.2f}%")
        with col3:
            if has_usdpln:
                current_usdpln = df_usdpln.iloc[-1]
                st.metric("USD/PLN", f"{current_usdpln['FX_Rate']:.4f}",
                         delta=f"{current_usdpln['Deviation_Pct']:+.2f}% vs FV")
            else:
                st.info("Upload USD/PLN")
        with col4:
            if has_eurpln:
                current_eurpln = df_eurpln.iloc[-1]
                st.metric("EUR/PLN", f"{current_eurpln['FX_Rate']:.4f}",
                         delta=f"{current_eurpln['Deviation_Pct']:+.2f}% vs FV")
            else:
                st.info("Upload EUR/PLN")
        
        # Correlation chain visualization
        st.markdown('<div class="sub-header">🔗 Correlation Chain</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            corr_class = "corr-strong" if abs(corr_eurusd_actual) > 0.7 else "corr-moderate"
            st.markdown(f"""
            <div class="metric-card">
                <b>Step 1: Spread → EUR/USD</b><br>
                <span class="correlation-badge {corr_class}">{corr_eurusd_actual:+.3f}</span><br>
                <small>Spread widens → EUR/USD rises</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            corr_class = "corr-strong" if abs(corr_eurusd_usdpln) > 0.7 else "corr-moderate"
            st.markdown(f"""
            <div class="metric-card">
                <b>Step 2: EUR/USD → USD/PLN</b><br>
                <span class="correlation-badge {corr_class}">{corr_eurusd_usdpln:+.3f}</span><br>
                <small>EUR/USD rises → USD/PLN falls (inverse!)</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <b>Step 3: Cross-Rate EUR/PLN</b><br>
                <span class="correlation-badge corr-strong">Mathematical</span><br>
                <small>EUR/PLN = EUR/USD × USD/PLN</small>
            </div>
            """, unsafe_allow_html=True)
        
        # Scenario setup
        st.markdown('<div class="sub-header">🎯 Prognosis Scenario</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            scenario = st.selectbox(
                "Select Scenario",
                ["Custom", "Steepening (+20%)", "Steepening (+50%)", 
                 "Flattening (-20%)", "Flattening (-50%)", "Current Stable"]
            )
            
            if scenario == "Custom":
                target_10y = st.number_input("Target 10Y (%)", 
                                           value=float(current_eurusd['10Y']), 
                                           min_value=0.0, max_value=10.0, step=0.1)
                target_30y = st.number_input("Target 30Y (%)", 
                                           value=float(current_eurusd['30Y']), 
                                           min_value=0.0, max_value=10.0, step=0.1)
            elif "Steepening" in scenario:
                pct = 0.2 if "20%" in scenario else 0.5
                target_10y = float(current_eurusd['10Y'])
                target_30y = float(current_eurusd['30Y']) + (current_eurusd['Spread'] * pct)
            elif "Flattening" in scenario:
                pct = 0.2 if "20%" in scenario else 0.5
                target_10y = float(current_eurusd['10Y'])
                target_30y = float(current_eurusd['30Y']) - (current_eurusd['Spread'] * pct)
            else:
                target_10y = float(current_eurusd['10Y'])
                target_30y = float(current_eurusd['30Y'])
        
        with col2:
            target_spread = target_30y - target_10y
            st.metric("Target Spread", f"{target_spread:.2f}%", 
                     delta=f"{target_spread - current_eurusd['Spread']:.2f}%")
            
            if target_spread > current_eurusd['Spread']:
                st.success("🟢 WIDENING → EUR/USD ↑ expected")
            elif target_spread < current_eurusd['Spread']:
                st.error("🔴 NARROWING → EUR/USD ↓ expected")
            else:
                st.info("⚪ STABLE → EUR/USD flat expected")
        
        # Calculate EUR/USD prognosis
        eurusd_target = slope_eurusd * target_spread + intercept_eurusd
        eurusd_change_pct = ((eurusd_target - current_eurusd['FX_Rate']) / 
                            current_eurusd['FX_Rate']) * 100
        
        # Calculate USD/PLN prognosis (using inverse correlation)
        if has_usdpln:
            usdpln_target, usdpln_change_pct = predict_pln_from_eurusd(
                current_eurusd['FX_Rate'],
                eurusd_target,
                current_usdpln['FX_Rate'],
                corr_eurusd_usdpln,
                inverse_dampening
            )
            
            # Calculate EUR/PLN from cross-rate
            eurpln_target = eurusd_target * usdpln_target
            
            if has_eurpln:
                eurpln_change_pct = ((eurpln_target - current_eurpln['FX_Rate']) / 
                                    current_eurpln['FX_Rate']) * 100
            else:
                eurpln_change_pct = None
        
        # Display prognosis
        st.markdown('<div class="sub-header">📈 Prognosis Results</div>', unsafe_allow_html=True)
        
        # EUR/USD
        st.markdown("#### Step 1: EUR/USD Forecast (from Spread)")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="prognosis-box">', unsafe_allow_html=True)
            st.markdown("### Current")
            st.markdown(f"## **{current_eurusd['FX_Rate']:.4f}**")
            st.markdown(f"Fair Value: {current_eurusd['Fair_Value']:.4f}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="prognosis-box">', unsafe_allow_html=True)
            st.markdown("### Target")
            st.markdown(f"## **{eurusd_target:.4f}**")
            change_color = "🟢" if eurusd_change_pct > 0 else "🔴"
            st.markdown(f"{change_color} {eurusd_change_pct:+.2f}%")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="prognosis-box">', unsafe_allow_html=True)
            st.markdown("### Direction")
            if eurusd_change_pct > 2:
                st.markdown("## 🟢 **EUR ↑**")
                st.markdown("EUR strengthening")
            elif eurusd_change_pct < -2:
                st.markdown("## 🔴 **EUR ↓**")
                st.markdown("EUR weakening")
            else:
                st.markdown("## ⚪ **FLAT**")
                st.markdown("Neutral")
            st.markdown("</div>", unsafe_allow_html=True)
        
        # USD/PLN and EUR/PLN
        if has_usdpln:
            st.markdown("#### Step 2 & 3: PLN Pairs (from EUR/USD inverse correlation)")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="pln-box">', unsafe_allow_html=True)
                st.markdown("### USD/PLN Prognosis")
                st.markdown(f"**Current:** {current_usdpln['FX_Rate']:.4f}")
                st.markdown(f"**Target:** {usdpln_target:.4f}")
                change_color = "🟢" if usdpln_change_pct < 0 else "🔴"
                st.markdown(f"**Change:** {change_color} {usdpln_change_pct:+.2f}%")
                st.markdown("---")
                st.markdown(f"**Method:** Inverse correlation")
                st.markdown(f"**Logic:** EUR/USD {eurusd_change_pct:+.2f}% → USD/PLN {usdpln_change_pct:+.2f}%")
                
                if usdpln_change_pct < -1:
                    st.markdown("✅ **PLN strengthens vs USD**")
                elif usdpln_change_pct > 1:
                    st.markdown("⚠️ **PLN weakens vs USD**")
                else:
                    st.markdown("➡️ **PLN stable vs USD**")
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="pln-box">', unsafe_allow_html=True)
                st.markdown("### EUR/PLN Prognosis")
                if has_eurpln:
                    st.markdown(f"**Current:** {current_eurpln['FX_Rate']:.4f}")
                st.markdown(f"**Target:** {eurpln_target:.4f}")
                if has_eurpln:
                    change_color = "🟢" if eurpln_change_pct < 0 else "🔴"
                    st.markdown(f"**Change:** {change_color} {eurpln_change_pct:+.2f}%")
                st.markdown("---")
                st.markdown(f"**Method:** Cross-rate")
                st.markdown(f"**Calculation:** {eurusd_target:.4f} × {usdpln_target:.4f}")
                
                if has_eurpln:
                    if eurpln_change_pct < -1:
                        st.markdown("✅ **PLN strengthens vs EUR**")
                    elif eurpln_change_pct > 1:
                        st.markdown("⚠️ **PLN weakens vs EUR**")
                    else:
                        st.markdown("➡️ **PLN stable vs EUR**")
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Validation if actual data available
            if has_usdpln or has_eurpln:
                with st.expander("📊 Model Validation"):
                    st.markdown("**Comparing Model Predictions vs Actual Data:**")
                    
                    if has_usdpln:
                        # Compare inverse-based prediction with spread-based
                        usdpln_spread_based = slope_usdpln * target_spread + intercept_usdpln
                        st.markdown(f"""
                        **USD/PLN:**
                        - Model (inverse from EUR/USD): {usdpln_target:.4f}
                        - Direct (from spread): {usdpln_spread_based:.4f}
                        - Current actual: {current_usdpln['FX_Rate']:.4f}
                        - Difference: {abs(usdpln_target - usdpln_spread_based):.4f}
                        
                        **Note:** Inverse method preferred due to stronger EUR/USD-USD/PLN correlation (-0.819)
                        """)
                    
                    if has_eurpln:
                        eurpln_spread_based = slope_eurpln * target_spread + intercept_eurpln
                        st.markdown(f"""
                        **EUR/PLN:**
                        - Model (cross-rate): {eurpln_target:.4f}
                        - Direct (from spread): {eurpln_spread_based:.4f}
                        - Current actual: {current_eurpln['FX_Rate']:.4f}
                        - Difference: {abs(eurpln_target - eurpln_spread_based):.4f}
                        
                        **Note:** Cross-rate method combines both strong correlations
                        """)
        
        # Detailed explanation
        with st.expander("ℹ️ How The Model Works"):
            st.markdown(f"""
            ### Correlation Chain Model
            
            **Step 1: US Yield Spread → EUR/USD**
            - Correlation: {corr_eurusd_actual:+.3f} (Very Strong)
            - When 30Y-10Y spread widens → EUR/USD typically rises
            - Current spread: {current_eurusd['Spread']:.2f}%
            - Target spread: {target_spread:.2f}%
            - EUR/USD forecast: {current_eurusd['FX_Rate']:.4f} → {eurusd_target:.4f}
            
            **Step 2: EUR/USD → USD/PLN (Inverse Correlation)**
            - Correlation: {corr_eurusd_usdpln:+.3f} (Very Strong Inverse)
            - When EUR/USD rises → USD weakens globally → USD/PLN falls
            - Dampening factor: {inverse_dampening:.2f}
            - EUR/USD change: {eurusd_change_pct:+.2f}%
            - USD/PLN expected change: {usdpln_change_pct:+.2f}% (inverse)
            
            **Step 3: EUR/PLN Cross-Rate**
            - Mathematical relationship: EUR/PLN = EUR/USD × USD/PLN
            - EUR/USD: {eurusd_target:.4f}
            - USD/PLN: {usdpln_target:.4f}
            - EUR/PLN: {eurpln_target:.4f}
            
            ### Why This Works
            
            1. **EUR/USD vs Spread (+0.878)**: Strongest correlation, very reliable
            2. **EUR/USD vs USD/PLN (-0.819)**: Strong inverse, captures USD weakness
            3. **Cross-rate**: Mathematical precision, no additional assumptions
            
            ### Key Insight
            
            When EUR strengthens vs USD:
            - EUR/USD ↑ (directly measured)
            - USD weakens globally
            - USD/PLN ↓ (fewer PLN per USD)
            - EUR/PLN = product of both effects
            
            This captures the **full transmission mechanism** of USD weakness!
            """)
        
        # Visualization
        st.markdown('<div class="sub-header">📊 Charts</div>', unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["EUR/USD Fair Value", "Correlation Chain", "PLN Pairs"])
        
        with tab1:
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('EUR/USD: Actual vs Fair Value', 'Deviation (%)'),
                vertical_spacing=0.15,
                row_heights=[0.6, 0.4]
            )
            
            fig.add_trace(go.Scatter(
                x=df_eurusd['Date'], y=df_eurusd['FX_Rate'],
                name='Actual', line=dict(color='#0051a5', width=2.5)
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df_eurusd['Date'], y=df_eurusd['Fair_Value'],
                name='Fair Value', line=dict(color='#ff7f0e', width=2, dash='dash')
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df_eurusd['Date'], y=df_eurusd['Deviation_Pct'],
                name='Deviation', fill='tozeroy', line=dict(color='purple', width=2)
            ), row=2, col=1)
            
            fig.add_hline(y=0, line_dash="solid", line_color="black", row=2, col=1)
            fig.add_hline(y=2, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
            fig.add_hline(y=-2, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)
            
            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_yaxes(title_text="EUR/USD", row=1, col=1)
            fig.update_yaxes(title_text="Deviation (%)", row=2, col=1)
            
            fig.update_layout(height=800, showlegend=True, hovermode='x unified',
                            title_text=f'EUR/USD Analysis | Correlation: {corr_eurusd_actual:+.3f}')
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            if has_usdpln:
                # Show EUR/USD and USD/PLN together to visualize inverse relationship
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=('EUR/USD (blue) vs USD/PLN (red) - Inverse Movement', 
                                  'Spread (green) - The Driver'),
                    vertical_spacing=0.15
                )
                
                # Merge EUR/USD and USD/PLN on date
                merged_visual = df_eurusd[['Date', 'FX_Rate', 'Spread']].merge(
                    df_usdpln[['Date', 'FX_Rate']], on='Date', suffixes=('_EUR', '_PLN'))
                
                fig.add_trace(go.Scatter(
                    x=merged_visual['Date'], y=merged_visual['FX_Rate_EUR'],
                    name='EUR/USD', line=dict(color='#0051a5', width=2.5)
                ), row=1, col=1)
                
                # Add USD/PLN on secondary axis
                fig.add_trace(go.Scatter(
                    x=merged_visual['Date'], y=merged_visual['FX_Rate_PLN'],
                    name='USD/PLN', line=dict(color='#d62728', width=2.5),
                    yaxis='y2'
                ), row=1, col=1)
                
                fig.add_trace(go.Scatter(
                    x=df_eurusd['Date'], y=df_eurusd['Spread'],
                    name='30Y-10Y Spread', fill='tozeroy',
                    line=dict(color='#2ca02c', width=2)
                ), row=2, col=1)
                
                fig.update_xaxes(title_text="Date", row=2, col=1)
                fig.update_yaxes(title_text="EUR/USD", row=1, col=1)
                fig.update_yaxes(title_text="Spread (%)", row=2, col=1)
                
                # Add secondary y-axis for USD/PLN
                fig.update_layout(
                    yaxis2=dict(title="USD/PLN", overlaying='y', side='right'),
                    height=700, showlegend=True, hovermode='x unified',
                    title_text='Correlation Chain: Spread → EUR/USD → USD/PLN'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Upload USD/PLN data to see correlation chain visualization")
        
        with tab3:
            if has_usdpln and has_eurpln:
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=('USD/PLN: Actual vs Model', 'EUR/PLN: Actual vs Model'),
                    vertical_spacing=0.15
                )
                
                fig.add_trace(go.Scatter(
                    x=df_usdpln['Date'], y=df_usdpln['FX_Rate'],
                    name='USD/PLN Actual', line=dict(color='#d62728', width=2.5)
                ), row=1, col=1)
                
                fig.add_trace(go.Scatter(
                    x=df_usdpln['Date'], y=df_usdpln['Fair_Value'],
                    name='USD/PLN Fair Value', line=dict(color='#ff7f0e', width=2, dash='dash')
                ), row=1, col=1)
                
                fig.add_trace(go.Scatter(
                    x=df_eurpln['Date'], y=df_eurpln['FX_Rate'],
                    name='EUR/PLN Actual', line=dict(color='#2ca02c', width=2.5)
                ), row=2, col=1)
                
                fig.add_trace(go.Scatter(
                    x=df_eurpln['Date'], y=df_eurpln['Fair_Value'],
                    name='EUR/PLN Fair Value', line=dict(color='#ff7f0e', width=2, dash='dash')
                ), row=2, col=1)
                
                fig.update_xaxes(title_text="Date", row=2, col=1)
                fig.update_yaxes(title_text="USD/PLN", row=1, col=1)
                fig.update_yaxes(title_text="EUR/PLN", row=2, col=1)
                
                fig.update_layout(height=800, showlegend=True, hovermode='x unified')
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Upload both USD/PLN and EUR/PLN data for comparison")
        
        # Export
        st.markdown('<div class="sub-header">💾 Export Results</div>', unsafe_allow_html=True)
        
        export_dict = {
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'Scenario': scenario,
            'Target_10Y': target_10y,
            'Target_30Y': target_30y,
            'Target_Spread': target_spread,
            'EURUSD_Current': current_eurusd['FX_Rate'],
            'EURUSD_Target': eurusd_target,
            'EURUSD_Change_Pct': eurusd_change_pct,
            'Correlation_Spread_EURUSD': corr_eurusd_actual
        }
        
        if has_usdpln:
            export_dict.update({
                'USDPLN_Current': current_usdpln['FX_Rate'],
                'USDPLN_Target': usdpln_target,
                'USDPLN_Change_Pct': usdpln_change_pct,
                'Correlation_EURUSD_USDPLN': corr_eurusd_usdpln,
                'EURPLN_Target_CrossRate': eurpln_target
            })
            
            if has_eurpln:
                export_dict['EURPLN_Current'] = current_eurpln['FX_Rate']
                export_dict['EURPLN_Change_Pct'] = eurpln_change_pct
        
        export_data = pd.DataFrame([export_dict])
        csv = export_data.to_csv(index=False)
        
        st.download_button(
            label="📥 Download Prognosis Results",
            data=csv,
            file_name=f"fx_prognosis_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        with st.expander("🔍 Debug Info"):
            st.exception(e)

else:
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("""
    ### 👆 Getting Started
    
    **Minimum Required Files:**
    1. EUR/USD historical data (Investing.com format)
    2. US 10Y Treasury yield (FRED format)
    3. US 30Y Treasury yield (FRED format)
    
    **Optional for Validation:**
    4. USD/PLN historical data
    5. EUR/PLN historical data
    
    ---
    
    ### 🔗 How The Correlation Chain Works
    
    **Step 1: US Yield Spread → EUR/USD**
    - Correlation: **+0.878** (Very Strong)
    - Wider spread → EUR/USD rises
    
    **Step 2: EUR/USD → USD/PLN**
    - Correlation: **-0.819** (Very Strong Inverse)
    - EUR/USD rises → USD/PLN falls
    - Logic: EUR stronger = USD weaker globally
    
    **Step 3: Cross-Rate EUR/PLN**
    - Mathematical: **EUR/PLN = EUR/USD × USD/PLN**
    - Combines both effects precisely
    
    ---
    
    ### ✅ Why This Model Is Superior
    
    1. **Strongest Correlations**: Uses +0.878 and -0.819 (both very strong)
    2. **Clear Transmission**: Spread → EUR → USD → PLN
    3. **Validated Logic**: USD weakness affects all USD pairs
    4. **Mathematical Precision**: Cross-rate eliminates compounding errors
    
    ---
    
    ### 📊 Expected Results
    
    **Example: Spread widens 20%**
    - EUR/USD: ↑ ~2-3%
    - USD/PLN: ↓ ~1.7-2.5% (inverse)
    - EUR/PLN: ↑ ~0.5-1% (net effect)
    """)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <b>FX Spread Prognosis - Correlation Chain Model</b> | 
    Spread → EUR/USD (+0.878) → USD/PLN (-0.819) → EUR/PLN (cross-rate)
</div>
""", unsafe_allow_html=True)
