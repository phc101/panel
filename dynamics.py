import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import io

# Page config
st.set_page_config(
    page_title="FX Spread Prognosis - PLN Enhanced",
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
    .info-box {
        background-color: #e1f5ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #0288d1;
        margin: 1rem 0;
    }
    .pln-box {
        background-color: #fff3e0;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 2px solid #ff9800;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="main-header">FX Spread Prognosis - PLN Enhanced 🇵🇱</div>', unsafe_allow_html=True)
st.markdown("**Forecast EUR/USD → derive USD/PLN & EUR/PLN using cross-rate relationships**")

# Sidebar
with st.sidebar:
    st.header("📁 Required Data Files")
    
    st.subheader("🔹 Primary Pair")
    eurusd_file = st.file_uploader("EUR/USD Historical Data", type=['csv'],
                                   help="From Investing.com")
    
    st.subheader("🔹 US Treasury Yields")
    dgs10_file = st.file_uploader("US 10Y Treasury", type=['csv'],
                                  help="From FRED (DGS10)")
    dgs30_file = st.file_uploader("US 30Y Treasury", type=['csv'],
                                  help="From FRED (DGS30)")
    
    st.subheader("🔹 PLN Pairs (for cross-rate)")
    usdpln_file = st.file_uploader("USD/PLN Historical Data", type=['csv'],
                                   help="From Investing.com")
    eurpln_file = st.file_uploader("EUR/PLN Historical Data", type=['csv'],
                                   help="From Investing.com")
    
    st.markdown("---")
    st.header("⚙️ Model Settings")
    
    use_recent_corr = st.checkbox("Use Recent 52w Correlation", value=False,
                                  help="Use last 52 weeks instead of full period")
    
    st.markdown("---")
    st.header("📊 Cross-Rate Method")
    
    method = st.radio(
        "PLN Prognosis Method",
        ["Direct Correlation", "Cross-Rate Calculation", "Hybrid (Best of Both)"],
        help="""
        Direct: Use spread correlation for each pair
        Cross-Rate: EUR/USD → USD/PLN → EUR/PLN
        Hybrid: Combine both methods
        """
    )
    
    if method == "Hybrid (Best of Both)":
        weight_direct = st.slider("Direct Model Weight", 0.0, 1.0, 0.5, 0.1)
        weight_cross = 1.0 - weight_direct

# Helper functions
def parse_fx_investing_polish(file):
    """Parse Investing.com Polish format"""
    try:
        df = pd.read_csv(file, encoding='utf-8-sig')
        if len(df.columns) >= 2:
            df = df.iloc[:, [0, 1]]
            df.columns = ['Date', 'Close']
        df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y', errors='coerce')
        df['Close'] = df['Close'].astype(str).str.replace(',', '.').astype(float)
        return df.sort_values('Date')[['Date', 'Close']].dropna()
    except Exception as e:
        st.error(f"Error parsing FX data: {str(e)}")
        st.stop()

def parse_yield_fred(file):
    """Parse FRED yield data"""
    try:
        df = pd.read_csv(file)
        if len(df.columns) >= 2:
            df = df.iloc[:, [0, 1]]
            df.columns = ['Date', 'Yield']
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        if df['Yield'].dtype == 'object':
            df['Yield'] = df['Yield'].astype(str).str.replace(',', '.').astype(float, errors='ignore')
        df['Yield'] = pd.to_numeric(df['Yield'], errors='coerce')
        return df.dropna()
    except Exception as e:
        st.error(f"Error parsing yield data: {str(e)}")
        st.stop()

def process_data(fx_df, short_df, long_df):
    """Merge FX and yield data"""
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

def calculate_fair_value_model(df, use_recent=False):
    """Calculate fair value model with regression"""
    if use_recent:
        recent_df = df.tail(52)
        corr = recent_df['FX_Rate'].corr(recent_df['Spread'])
        base_data = recent_df
    else:
        corr = df['FX_Rate'].corr(df['Spread'])
        base_data = df
    
    z = np.polyfit(base_data['Spread'], base_data['FX_Rate'], 1)
    slope, intercept = z[0], z[1]
    
    df['Fair_Value'] = slope * df['Spread'] + intercept
    df['Deviation'] = df['FX_Rate'] - df['Fair_Value']
    df['Deviation_Pct'] = (df['Deviation'] / df['Fair_Value']) * 100
    
    return df, corr, slope, intercept

def calculate_cross_rate_correlation(eurusd_df, usdpln_df):
    """Calculate correlation between EUR/USD and USD/PLN"""
    merged = eurusd_df.merge(usdpln_df, on='Date', suffixes=('_EURUSD', '_USDPLN'))
    corr = merged['FX_Rate_EURUSD'].corr(merged['FX_Rate_USDPLN'])
    return corr, merged

def predict_pln_pairs(eurusd_current, eurusd_target, usdpln_current, eurpln_current, 
                     eurusd_usdpln_corr, method='Cross-Rate'):
    """Predict USD/PLN and EUR/PLN based on EUR/USD prognosis"""
    
    eurusd_change_pct = ((eurusd_target - eurusd_current) / eurusd_current) * 100
    
    if method == "Cross-Rate Calculation":
        # Pure mathematical cross-rate
        # EUR/USD ↑ 1% → USD weaker → USD/PLN ↓ ~1%
        usdpln_change_pct = -eurusd_change_pct  # Inverse relationship
        usdpln_target = usdpln_current * (1 + usdpln_change_pct / 100)
        
        # EUR/PLN = EUR/USD × USD/PLN
        eurpln_target = eurusd_target * usdpln_target
        eurpln_change_pct = ((eurpln_target - eurpln_current) / eurpln_current) * 100
        
    elif method == "Direct Correlation":
        # Use historical correlation with dampening
        dampening_factor = 0.8  # Correlation isn't perfect
        usdpln_change_pct = -eurusd_change_pct * dampening_factor
        usdpln_target = usdpln_current * (1 + usdpln_change_pct / 100)
        
        # EUR/PLN typically moves with EUR/USD but less volatile
        eurpln_change_pct = eurusd_change_pct * 0.6  # EUR/PLN less volatile
        eurpln_target = eurpln_current * (1 + eurpln_change_pct / 100)
        
    else:  # Hybrid
        # Average of both methods
        # Method 1: Cross-rate
        usdpln_cross = usdpln_current * (1 - eurusd_change_pct / 100)
        eurpln_cross = eurusd_target * usdpln_cross
        
        # Method 2: Correlation
        usdpln_corr = usdpln_current * (1 - eurusd_change_pct * 0.8 / 100)
        eurpln_corr = eurpln_current * (1 + eurusd_change_pct * 0.6 / 100)
        
        # Weighted average (default 50/50)
        usdpln_target = (usdpln_cross * 0.5 + usdpln_corr * 0.5)
        eurpln_target = (eurpln_cross * 0.5 + eurpln_corr * 0.5)
        
        usdpln_change_pct = ((usdpln_target - usdpln_current) / usdpln_current) * 100
        eurpln_change_pct = ((eurpln_target - eurpln_current) / eurpln_current) * 100
    
    return {
        'usdpln_target': usdpln_target,
        'usdpln_change_pct': usdpln_change_pct,
        'eurpln_target': eurpln_target,
        'eurpln_change_pct': eurpln_change_pct
    }

# Main app logic
if all([eurusd_file, dgs10_file, dgs30_file]):
    try:
        # Parse primary data
        with st.spinner("Loading primary data (EUR/USD + US yields)..."):
            eurusd_df = parse_fx_investing_polish(eurusd_file)
            dgs10_df = parse_yield_fred(dgs10_file)
            dgs30_df = parse_yield_fred(dgs30_file)
            
            df_eurusd = process_data(eurusd_df, dgs10_df, dgs30_df)
        
        # Parse PLN pairs if available
        has_pln_data = usdpln_file is not None and eurpln_file is not None
        
        if has_pln_data:
            with st.spinner("Loading PLN pairs data..."):
                usdpln_df = parse_fx_investing_polish(usdpln_file)
                eurpln_df = parse_fx_investing_polish(eurpln_file)
                
                # Process PLN pairs with same yield data
                df_usdpln = process_data(usdpln_df, dgs10_df, dgs30_df)
                df_eurpln = process_data(eurpln_df, dgs10_df, dgs30_df)
        
        st.success(f"✅ Loaded {len(df_eurusd)} EUR/USD observations" + 
                  (f" + {len(df_usdpln)} USD/PLN + {len(df_eurpln)} EUR/PLN" if has_pln_data else ""))
        
        # Calculate models
        df_eurusd, corr_eurusd, slope_eurusd, intercept_eurusd = calculate_fair_value_model(
            df_eurusd, use_recent_corr)
        
        if has_pln_data:
            df_usdpln, corr_usdpln, slope_usdpln, intercept_usdpln = calculate_fair_value_model(
                df_usdpln, use_recent_corr)
            df_eurpln, corr_eurpln, slope_eurpln, intercept_eurpln = calculate_fair_value_model(
                df_eurpln, use_recent_corr)
            
            # Calculate cross-rate correlation
            eurusd_usdpln_corr, merged_cross = calculate_cross_rate_correlation(
                df_eurusd[['Date', 'FX_Rate']], df_usdpln[['Date', 'FX_Rate']])
        
        # Current values
        current_eurusd = df_eurusd.iloc[-1]
        if has_pln_data:
            current_usdpln = df_usdpln.iloc[-1]
            current_eurpln = df_eurpln.iloc[-1]
        
        # Display current metrics
        st.markdown('<div class="sub-header">📊 Current Market Data</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("EUR/USD", f"{current_eurusd['FX_Rate']:.4f}",
                     delta=f"{current_eurusd['Deviation_Pct']:+.2f}% vs FV")
        with col2:
            st.metric("30Y-10Y Spread", f"{current_eurusd['Spread']:.2f}%")
        with col3:
            if has_pln_data:
                st.metric("USD/PLN", f"{current_usdpln['FX_Rate']:.4f}",
                         delta=f"{current_usdpln['Deviation_Pct']:+.2f}% vs FV")
            else:
                st.info("Upload USD/PLN data")
        with col4:
            if has_pln_data:
                st.metric("EUR/PLN", f"{current_eurpln['FX_Rate']:.4f}",
                         delta=f"{current_eurpln['Deviation_Pct']:+.2f}% vs FV")
            else:
                st.info("Upload EUR/PLN data")
        
        # Correlation summary
        st.markdown('<div class="sub-header">🔗 Correlation Analysis</div>', unsafe_allow_html=True)
        
        cols = st.columns(4 if has_pln_data else 2)
        
        with cols[0]:
            st.info(f"**EUR/USD vs Spread**\n\n{corr_eurusd:+.3f}")
        with cols[1]:
            if has_pln_data:
                st.info(f"**EUR/USD vs USD/PLN**\n\n{eurusd_usdpln_corr:+.3f}")
        if has_pln_data:
            with cols[2]:
                st.info(f"**USD/PLN vs Spread**\n\n{corr_usdpln:+.3f}")
            with cols[3]:
                st.info(f"**EUR/PLN vs Spread**\n\n{corr_eurpln:+.3f}")
        
        # Scenario setup
        st.markdown('<div class="sub-header">🎯 EUR/USD Prognosis Scenario</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            scenario = st.selectbox(
                "Select Scenario",
                ["Custom", "Steepening (+20%)", "Steepening (+50%)", "Flattening (-20%)", 
                 "Flattening (-50%)", "Current Stable"]
            )
            
            if scenario == "Custom":
                target_10y = st.number_input("Target 10Y Yield (%)", 
                                           value=float(current_eurusd['10Y']), 
                                           min_value=0.0, max_value=10.0, step=0.1)
                target_30y = st.number_input("Target 30Y Yield (%)", 
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
            
            # Calculate EUR/USD target
            eurusd_target = slope_eurusd * target_spread + intercept_eurusd
            eurusd_change_pct = ((eurusd_target - current_eurusd['FX_Rate']) / 
                                current_eurusd['FX_Rate']) * 100
            
            st.metric("EUR/USD Target", f"{eurusd_target:.4f}",
                     delta=f"{eurusd_change_pct:+.2f}%")
        
        # EUR/USD Prognosis
        st.markdown('<div class="sub-header">📈 EUR/USD Prognosis</div>', unsafe_allow_html=True)
        
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
            elif eurusd_change_pct < -2:
                st.markdown("## 🔴 **EUR ↓**")
            else:
                st.markdown("## ⚪ **FLAT**")
            st.markdown("</div>", unsafe_allow_html=True)
        
        # PLN Pairs Prognosis
        if has_pln_data:
            st.markdown('<div class="sub-header">🇵🇱 PLN Pairs Prognosis</div>', unsafe_allow_html=True)
            
            # Calculate PLN predictions
            pln_pred = predict_pln_pairs(
                current_eurusd['FX_Rate'],
                eurusd_target,
                current_usdpln['FX_Rate'],
                current_eurpln['FX_Rate'],
                eurusd_usdpln_corr,
                method
            )
            
            # Display PLN prognosis
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="pln-box">', unsafe_allow_html=True)
                st.markdown("### USD/PLN Prognosis")
                st.markdown(f"**Current:** {current_usdpln['FX_Rate']:.4f}")
                st.markdown(f"**Target:** {pln_pred['usdpln_target']:.4f}")
                change_color = "🟢" if pln_pred['usdpln_change_pct'] < 0 else "🔴"  # Lower USD/PLN = PLN stronger
                st.markdown(f"**Change:** {change_color} {pln_pred['usdpln_change_pct']:+.2f}%")
                
                if pln_pred['usdpln_change_pct'] < -1:
                    st.markdown("✅ **PLN strengthens vs USD**")
                elif pln_pred['usdpln_change_pct'] > 1:
                    st.markdown("⚠️ **PLN weakens vs USD**")
                else:
                    st.markdown("➡️ **PLN stable vs USD**")
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="pln-box">', unsafe_allow_html=True)
                st.markdown("### EUR/PLN Prognosis")
                st.markdown(f"**Current:** {current_eurpln['FX_Rate']:.4f}")
                st.markdown(f"**Target:** {pln_pred['eurpln_target']:.4f}")
                change_color = "🟢" if pln_pred['eurpln_change_pct'] < 0 else "🔴"  # Lower EUR/PLN = PLN stronger
                st.markdown(f"**Change:** {change_color} {pln_pred['eurpln_change_pct']:+.2f}%")
                
                if pln_pred['eurpln_change_pct'] < -1:
                    st.markdown("✅ **PLN strengthens vs EUR**")
                elif pln_pred['eurpln_change_pct'] > 1:
                    st.markdown("⚠️ **PLN weakens vs EUR**")
                else:
                    st.markdown("➡️ **PLN stable vs EUR**")
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Explanation
            with st.expander("ℹ️ How PLN Prognosis Works"):
                if method == "Cross-Rate Calculation":
                    st.markdown("""
                    **Cross-Rate Method (Mathematical):**
                    
                    1. EUR/USD forecast: {:.4f} → {:.4f} ({:+.2f}%)
                    2. USD/PLN inverse relationship: USD weakens → USD/PLN falls
                    3. USD/PLN target: {:.4f} → {:.4f} ({:+.2f}%)
                    4. EUR/PLN = EUR/USD × USD/PLN
                    5. EUR/PLN target: {:.4f}
                    
                    **Logic:** EUR/USD and USD/PLN have high inverse correlation (~-0.8 to -0.9)
                    When EUR strengthens vs USD, USD typically weakens vs PLN proportionally.
                    """.format(
                        current_eurusd['FX_Rate'], eurusd_target, eurusd_change_pct,
                        current_usdpln['FX_Rate'], pln_pred['usdpln_target'], pln_pred['usdpln_change_pct'],
                        pln_pred['eurpln_target']
                    ))
                elif method == "Direct Correlation":
                    st.markdown("""
                    **Direct Correlation Method:**
                    
                    Uses historical correlation between each pair and US yield spread:
                    - USD/PLN vs Spread: {:.3f}
                    - EUR/PLN vs Spread: {:.3f}
                    
                    Each pair's prognosis calculated independently based on spread change.
                    Applied dampening factor (0.8) since correlation isn't perfect.
                    """.format(corr_usdpln, corr_eurpln))
                else:
                    st.markdown("""
                    **Hybrid Method (Best of Both):**
                    
                    Combines two approaches:
                    1. **Cross-Rate** (mathematical relationship)
                    2. **Direct Correlation** (historical spread correlation)
                    
                    Weight: {:.0f}% Direct + {:.0f}% Cross-Rate
                    
                    Provides more robust forecast by averaging different methodologies.
                    """.format(weight_direct * 100, weight_cross * 100))
        
        # Visualization
        st.markdown('<div class="sub-header">📊 Charts</div>', unsafe_allow_html=True)
        
        tabs = ["EUR/USD Fair Value", "PLN Pairs Analysis"] if has_pln_data else ["EUR/USD Fair Value"]
        tab_objects = st.tabs(tabs)
        
        with tab_objects[0]:
            # EUR/USD Fair Value Chart
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('EUR/USD: Actual vs Fair Value', 'Deviation (%)'),
                vertical_spacing=0.15,
                row_heights=[0.6, 0.4]
            )
            
            fig.add_trace(go.Scatter(
                x=df_eurusd['Date'], y=df_eurusd['FX_Rate'],
                name='EUR/USD Actual',
                line=dict(color='#0051a5', width=2.5)
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df_eurusd['Date'], y=df_eurusd['Fair_Value'],
                name='Fair Value',
                line=dict(color='#ff7f0e', width=2, dash='dash')
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df_eurusd['Date'], y=df_eurusd['Deviation_Pct'],
                name='Deviation',
                fill='tozeroy',
                line=dict(color='purple', width=2)
            ), row=2, col=1)
            
            fig.add_hline(y=0, line_dash="solid", line_color="black", row=2, col=1)
            fig.add_hline(y=2, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
            fig.add_hline(y=-2, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)
            
            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_yaxes(title_text="EUR/USD", row=1, col=1)
            fig.update_yaxes(title_text="Deviation (%)", row=2, col=1)
            
            fig.update_layout(height=800, showlegend=True, hovermode='x unified',
                            title_text=f'EUR/USD Analysis | Correlation: {corr_eurusd:+.3f}')
            
            st.plotly_chart(fig, use_container_width=True)
        
        if has_pln_data:
            with tab_objects[1]:
                # PLN Pairs Comparison
                fig = make_subplots(
                    rows=3, cols=1,
                    subplot_titles=('EUR/USD vs USD/PLN', 'USD/PLN Fair Value', 'EUR/PLN Fair Value'),
                    vertical_spacing=0.1,
                    row_heights=[0.33, 0.33, 0.34]
                )
                
                # Panel 1: EUR/USD vs USD/PLN (inverse relationship)
                fig.add_trace(go.Scatter(
                    x=df_eurusd['Date'], y=df_eurusd['FX_Rate'],
                    name='EUR/USD',
                    line=dict(color='#0051a5', width=2)
                ), row=1, col=1)
                
                fig.add_trace(go.Scatter(
                    x=df_usdpln['Date'], y=df_usdpln['FX_Rate'],
                    name='USD/PLN',
                    line=dict(color='#d62728', width=2),
                    yaxis='y2'
                ), row=1, col=1)
                
                # Panel 2: USD/PLN
                fig.add_trace(go.Scatter(
                    x=df_usdpln['Date'], y=df_usdpln['FX_Rate'],
                    name='USD/PLN Actual',
                    line=dict(color='#d62728', width=2.5)
                ), row=2, col=1)
                
                fig.add_trace(go.Scatter(
                    x=df_usdpln['Date'], y=df_usdpln['Fair_Value'],
                    name='USD/PLN Fair Value',
                    line=dict(color='#ff7f0e', width=2, dash='dash')
                ), row=2, col=1)
                
                # Panel 3: EUR/PLN
                fig.add_trace(go.Scatter(
                    x=df_eurpln['Date'], y=df_eurpln['FX_Rate'],
                    name='EUR/PLN Actual',
                    line=dict(color='#2ca02c', width=2.5)
                ), row=3, col=1)
                
                fig.add_trace(go.Scatter(
                    x=df_eurpln['Date'], y=df_eurpln['Fair_Value'],
                    name='EUR/PLN Fair Value',
                    line=dict(color='#ff7f0e', width=2, dash='dash')
                ), row=3, col=1)
                
                fig.update_xaxes(title_text="Date", row=3, col=1)
                fig.update_yaxes(title_text="EUR/USD", row=1, col=1)
                fig.update_yaxes(title_text="USD/PLN", row=2, col=1)
                fig.update_yaxes(title_text="EUR/PLN", row=3, col=1)
                
                fig.update_layout(height=1000, showlegend=True, hovermode='x unified',
                                title_text=f'PLN Pairs Analysis | EUR/USD vs USD/PLN Corr: {eurusd_usdpln_corr:+.3f}')
                
                st.plotly_chart(fig, use_container_width=True)
        
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
            'EURUSD_Correlation': corr_eurusd
        }
        
        if has_pln_data:
            export_dict.update({
                'USDPLN_Current': current_usdpln['FX_Rate'],
                'USDPLN_Target': pln_pred['usdpln_target'],
                'USDPLN_Change_Pct': pln_pred['usdpln_change_pct'],
                'EURPLN_Current': current_eurpln['FX_Rate'],
                'EURPLN_Target': pln_pred['eurpln_target'],
                'EURPLN_Change_Pct': pln_pred['eurpln_change_pct'],
                'Method': method
            })
        
        export_data = pd.DataFrame([export_dict])
        csv = export_data.to_csv(index=False)
        
        st.download_button(
            label="📥 Download Prognosis Results (CSV)",
            data=csv,
            file_name=f"fx_prognosis_pln_{datetime.now().strftime('%Y%m%d')}.csv",
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
    
    **Minimum Required (EUR/USD only):**
    1. EUR/USD historical data (Investing.com)
    2. US 10Y Treasury (FRED)
    3. US 30Y Treasury (FRED)
    
    **For PLN Prognosis (Recommended):**
    4. USD/PLN historical data (Investing.com)
    5. EUR/PLN historical data (Investing.com)
    
    **How it works:**
    - Forecast EUR/USD based on US yield curve spread (+0.878 correlation)
    - Use EUR/USD forecast to derive USD/PLN and EUR/PLN via:
      - **Cross-Rate:** Mathematical relationship (EUR/USD × USD/PLN = EUR/PLN)
      - **Direct Correlation:** Each pair's own spread correlation
      - **Hybrid:** Weighted average of both methods
    """)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <b>FX Spread Prognosis - PLN Enhanced</b> | 
    EUR/USD → USD/PLN → EUR/PLN cross-rate analysis
</div>
""", unsafe_allow_html=True)
