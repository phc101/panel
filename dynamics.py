import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import io

# Page config
st.set_page_config(
    page_title="FX Spread Prognosis Tool - Universal",
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
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="main-header">Universal FX Spread Prognosis Tool 🌍</div>', unsafe_allow_html=True)
st.markdown("**Forecast any currency pair based on yield curve spread correlation**")

# Sidebar
with st.sidebar:
    st.header("📁 Data Configuration")
    
    # Currency pair selection
    st.subheader("🔹 Currency Pair")
    
    col1, col2 = st.columns(2)
    with col1:
        base_currency = st.text_input("Base Currency", value="EUR", max_chars=3).upper()
    with col2:
        quote_currency = st.text_input("Quote Currency", value="USD", max_chars=3).upper()
    
    currency_pair = f"{base_currency}/{quote_currency}"
    st.info(f"📊 Analyzing: **{currency_pair}**")
    
    # Treasury data
    st.subheader("🔹 Quote Currency Yields")
    st.caption(f"({quote_currency} government bonds)")
    
    short_term_label = st.text_input("Short-term Label", value="10Y", 
                                     help="e.g., 2Y, 5Y, 10Y")
    long_term_label = st.text_input("Long-term Label", value="30Y",
                                    help="e.g., 10Y, 20Y, 30Y")
    
    st.markdown("---")
    st.header("📂 File Upload")
    
    fx_file = st.file_uploader(f"{currency_pair} Historical Data", type=['csv'],
                               help="CSV format: Date, Close price")
    short_file = st.file_uploader(f"{quote_currency} {short_term_label} Yield", type=['csv'],
                                  help="CSV format: Date, Yield")
    long_file = st.file_uploader(f"{quote_currency} {long_term_label} Yield", type=['csv'],
                                 help="CSV format: Date, Yield")
    
    st.markdown("---")
    st.header("⚙️ Model Settings")
    
    auto_calculate_corr = st.checkbox("Auto-calculate Correlation", value=True,
                                      help="Calculate from data or use manual value")
    
    if not auto_calculate_corr:
        correlation = st.slider("Manual Correlation", 
                               min_value=-1.0, max_value=1.0, value=0.878, step=0.001)
    
    use_recent_corr = st.checkbox("Use Recent Period Only", 
                                  help="Use last 52 weeks instead of full period")
    
    if use_recent_corr:
        recent_period = st.slider("Recent Period (weeks)", 
                                 min_value=20, max_value=104, value=52, step=4)
    
    st.markdown("---")
    st.header("🎯 Data Format")
    
    data_format = st.selectbox(
        "FX Data Format",
        ["Investing.com (Polish)", "Investing.com (English)", "Yahoo Finance", "FRED", "Custom CSV"]
    )
    
    if data_format == "Custom CSV":
        st.info("Expected columns: Date, Close")
        date_format_fx = st.text_input("Date Format", value="%Y-%m-%d",
                                       help="e.g., %d.%m.%Y or %Y-%m-%d")
        decimal_sep_fx = st.selectbox("Decimal Separator", [",", "."])
    
    yield_format = st.selectbox(
        "Yield Data Format",
        ["FRED", "Custom CSV"]
    )

# Helper functions for parsing different formats
def parse_fx_data(file, data_format):
    """Parse FX data based on format"""
    if data_format == "Investing.com (Polish)":
        df = pd.read_csv(file, encoding='utf-8-sig')
        df.columns = ['Date', 'Close', 'Open', 'High', 'Low', 'Volume', 'Change']
        df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y', errors='coerce')
        df['Close'] = df['Close'].astype(str).str.replace(',', '.').astype(float)
    elif data_format == "Investing.com (English)":
        df = pd.read_csv(file)
        df.columns = ['Date', 'Close', 'Open', 'High', 'Low', 'Volume', 'Change']
        df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y', errors='coerce')
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    elif data_format == "Yahoo Finance":
        df = pd.read_csv(file)
        df = df.rename(columns={'Date': 'Date', 'Close': 'Close'})
        df['Date'] = pd.to_datetime(df['Date'])
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    elif data_format == "FRED":
        df = pd.read_csv(file)
        df.columns = ['Date', 'Close']
        df['Date'] = pd.to_datetime(df['Date'])
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    else:  # Custom
        df = pd.read_csv(file)
        if decimal_sep_fx == ',':
            df['Close'] = df['Close'].astype(str).str.replace(',', '.').astype(float)
        df['Date'] = pd.to_datetime(df['Date'], format=date_format_fx)
    
    return df.sort_values('Date')[['Date', 'Close']].dropna()

def parse_yield_data(file, yield_format):
    """Parse yield data based on format"""
    df = pd.read_csv(file)
    df.columns = ['Date', 'Yield']
    df['Date'] = pd.to_datetime(df['Date'])
    df['Yield'] = pd.to_numeric(df['Yield'], errors='coerce')
    return df.dropna()

def process_data(fx_df, short_df, long_df):
    """Merge FX and yield data"""
    # Merge yields
    yields = short_df.merge(long_df, on='Date', how='inner', suffixes=('_Short', '_Long'))
    
    # For each FX date, find closest yield
    merged_data = []
    for idx, row in fx_df.iterrows():
        fx_date = row['Date']
        
        # Find closest yields (within 7 days)
        yield_window = yields[abs(yields['Date'] - fx_date) <= timedelta(days=7)]
        if len(yield_window) > 0:
            closest_idx = (yield_window['Date'] - fx_date).abs().idxmin()
            closest_yields = yields.loc[closest_idx]
            
            merged_data.append({
                'Date': fx_date,
                'FX_Rate': row['Close'],
                'Short_Yield': closest_yields['Yield_Short'],
                'Long_Yield': closest_yields['Yield_Long']
            })
    
    df = pd.DataFrame(merged_data)
    
    # Calculate spread
    df['Spread'] = df['Long_Yield'] - df['Short_Yield']
    
    return df

def calculate_prognosis(df, target_spread, correlation_val, use_recent=False, recent_weeks=52):
    """Calculate fair value and prognosis"""
    if use_recent:
        recent_df = df.tail(recent_weeks)
        corr = recent_df['FX_Rate'].corr(recent_df['Spread'])
        base_data = recent_df
    else:
        if correlation_val is None:
            corr = df['FX_Rate'].corr(df['Spread'])
        else:
            corr = correlation_val
        base_data = df
    
    # Linear regression
    z = np.polyfit(base_data['Spread'], base_data['FX_Rate'], 1)
    slope, intercept = z[0], z[1]
    
    # Calculate fair value for all historical data
    df['Fair_Value'] = slope * df['Spread'] + intercept
    df['Deviation'] = df['FX_Rate'] - df['Fair_Value']
    df['Deviation_Pct'] = (df['Deviation'] / df['Fair_Value']) * 100
    
    # Predict FX for target spread
    predicted_fx = slope * target_spread + intercept
    
    # Current values
    current_spread = df['Spread'].iloc[-1]
    current_fx = df['FX_Rate'].iloc[-1]
    current_fair_value = df['Fair_Value'].iloc[-1]
    current_deviation = df['Deviation_Pct'].iloc[-1]
    
    # Change
    spread_change = target_spread - current_spread
    fx_change = predicted_fx - current_fx
    fx_change_pct = (fx_change / current_fx) * 100
    
    return {
        'predicted_fx': predicted_fx,
        'current_fx': current_fx,
        'current_fair_value': current_fair_value,
        'current_deviation': current_deviation,
        'current_spread': current_spread,
        'target_spread': target_spread,
        'spread_change': spread_change,
        'fx_change': fx_change,
        'fx_change_pct': fx_change_pct,
        'correlation': corr,
        'slope': slope,
        'intercept': intercept,
        'df_with_fv': df
    }

# Main app logic
if all([fx_file, short_file, long_file]):
    try:
        # Parse all files
        with st.spinner("Processing data..."):
            fx_df = parse_fx_data(fx_file, data_format)
            short_df = parse_yield_data(short_file, yield_format)
            long_df = parse_yield_data(long_file, yield_format)
            
            df = process_data(fx_df, short_df, long_df)
        
        if len(df) == 0:
            st.error("❌ No overlapping data found. Check date ranges.")
            st.stop()
        
        st.success(f"✅ Loaded {len(df)} observations from {df['Date'].min().date()} to {df['Date'].max().date()}")
        
        # Current values
        current = df.iloc[-1]
        
        # Display current metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(f"{currency_pair}", f"{current['FX_Rate']:.4f}")
        with col2:
            st.metric(f"{long_term_label}-{short_term_label} Spread", f"{current['Spread']:.2f}%")
        with col3:
            st.metric(f"{quote_currency} {short_term_label}", f"{current['Short_Yield']:.2f}%")
        with col4:
            st.metric(f"{quote_currency} {long_term_label}", f"{current['Long_Yield']:.2f}%")
        
        # Correlation calculation
        full_corr = df['FX_Rate'].corr(df['Spread'])
        recent_corr = df.tail(52)['FX_Rate'].corr(df.tail(52)['Spread'])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"📊 **Full Period Correlation:** {full_corr:+.3f}")
        with col2:
            st.info(f"📈 **Recent 52-Week Correlation:** {recent_corr:+.3f}")
        with col3:
            if abs(full_corr) > 0.7:
                st.success("✅ **Strong Correlation** - Model reliable")
            elif abs(full_corr) > 0.4:
                st.warning("⚠️ **Moderate Correlation** - Use with caution")
            else:
                st.error("❌ **Weak Correlation** - Model not recommended")
        
        # Model explanation box
        with st.expander("ℹ️ Understanding the Correlation"):
            if full_corr > 0:
                st.markdown(f"""
                **Positive Correlation ({full_corr:+.3f})**
                
                ✅ When {long_term_label}-{short_term_label} spread **WIDENS** → {currency_pair} typically **RISES** ({base_currency} strengthens)
                
                ✅ When {long_term_label}-{short_term_label} spread **NARROWS** → {currency_pair} typically **FALLS** ({base_currency} weakens)
                
                **Interpretation:**
                - Steeper {quote_currency} curve = {base_currency} appreciation
                - Flatter {quote_currency} curve = {base_currency} depreciation
                """)
            else:
                st.markdown(f"""
                **Negative Correlation ({full_corr:+.3f})**
                
                ✅ When {long_term_label}-{short_term_label} spread **WIDENS** → {currency_pair} typically **FALLS** ({base_currency} weakens)
                
                ✅ When {long_term_label}-{short_term_label} spread **NARROWS** → {currency_pair} typically **RISES** ({base_currency} strengthens)
                
                **Interpretation:**
                - Steeper {quote_currency} curve = {base_currency} depreciation
                - Flatter {quote_currency} curve = {base_currency} appreciation
                """)
        
        # Scenario setup
        st.markdown('<div class="sub-header">🎯 Prognosis Scenario</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            scenario = st.selectbox(
                "Select Scenario",
                ["Custom", "Steepening (+20%)", "Steepening (+50%)", "Flattening (-20%)", "Flattening (-50%)", "Current Stable"]
            )
            
            if scenario == "Custom":
                target_short = st.number_input(f"Target {short_term_label} Yield (%)", 
                                              value=float(current['Short_Yield']), 
                                              min_value=0.0, max_value=20.0, step=0.1)
                target_long = st.number_input(f"Target {long_term_label} Yield (%)", 
                                             value=float(current['Long_Yield']), 
                                             min_value=0.0, max_value=20.0, step=0.1)
            elif "Steepening" in scenario:
                pct = 0.2 if "20%" in scenario else 0.5
                target_short = float(current['Short_Yield'])
                target_long = float(current['Long_Yield']) + (current['Spread'] * pct)
                st.info(f"📈 Spread widens by {int(pct*100)}%: {short_term_label} stable, {long_term_label} rises")
            elif "Flattening" in scenario:
                pct = 0.2 if "20%" in scenario else 0.5
                target_short = float(current['Short_Yield'])
                target_long = float(current['Long_Yield']) - (current['Spread'] * pct)
                st.info(f"📉 Spread narrows by {int(pct*100)}%: {short_term_label} stable, {long_term_label} falls")
            else:  # Current Stable
                target_short = float(current['Short_Yield'])
                target_long = float(current['Long_Yield'])
                st.info("➡️ Yields stay at current levels")
        
        with col2:
            target_spread = target_long - target_short
            st.metric("Target Spread", f"{target_spread:.2f}%", 
                     delta=f"{target_spread - current['Spread']:.2f}%")
            
            spread_direction = "WIDENING" if target_spread > current['Spread'] else "NARROWING" if target_spread < current['Spread'] else "STABLE"
            
            if full_corr > 0:
                if target_spread > current['Spread']:
                    st.success(f"🟢 {spread_direction} → {currency_pair} likely UP")
                elif target_spread < current['Spread']:
                    st.error(f"🔴 {spread_direction} → {currency_pair} likely DOWN")
                else:
                    st.info(f"⚪ {spread_direction} → {currency_pair} likely FLAT")
            else:  # Negative correlation
                if target_spread > current['Spread']:
                    st.error(f"🔴 {spread_direction} → {currency_pair} likely DOWN")
                elif target_spread < current['Spread']:
                    st.success(f"🟢 {spread_direction} → {currency_pair} likely UP")
                else:
                    st.info(f"⚪ {spread_direction} → {currency_pair} likely FLAT")
        
        # Calculate prognosis
        corr_value = None if auto_calculate_corr else correlation
        recent_weeks = recent_period if use_recent_corr else 52
        prognosis = calculate_prognosis(df, target_spread, corr_value, use_recent_corr, recent_weeks)
        df = prognosis['df_with_fv']
        
        # Fair Value Analysis
        st.markdown('<div class="sub-header">⚖️ Fair Value Analysis</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f"### Actual {currency_pair}")
            st.markdown(f"## **{prognosis['current_fx']:.4f}**")
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
                signal = f"⚠️ {base_currency} OVERVALUED"
                color = "🔴"
            else:
                box_class = "success-box"
                signal = f"💎 {base_currency} UNDERVALUED"
                color = "🟢"
            
            st.markdown(f'<div class="{box_class}">', unsafe_allow_html=True)
            st.markdown("### Deviation")
            st.markdown(f"## **{deviation:+.2f}%**")
            st.markdown(f"**{color} {signal}**")
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Prognosis Results
        st.markdown('<div class="sub-header">📊 Prognosis Results</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="prognosis-box">', unsafe_allow_html=True)
            st.markdown(f"### Current {currency_pair}")
            st.markdown(f"## **{prognosis['current_fx']:.4f}**")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="prognosis-box">', unsafe_allow_html=True)
            st.markdown(f"### Predicted {currency_pair}")
            st.markdown(f"## **{prognosis['predicted_fx']:.4f}**")
            change_color = "🟢" if prognosis['fx_change'] > 0 else "🔴"
            st.markdown(f"{change_color} {prognosis['fx_change']:+.4f} ({prognosis['fx_change_pct']:+.2f}%)")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="prognosis-box">', unsafe_allow_html=True)
            st.markdown("### Direction")
            if prognosis['fx_change_pct'] > 2:
                st.markdown(f"## 🟢 **{base_currency} ↑**")
                st.markdown(f"{base_currency} strengthening")
            elif prognosis['fx_change_pct'] < -2:
                st.markdown(f"## 🔴 **{base_currency} ↓**")
                st.markdown(f"{base_currency} weakening")
            else:
                st.markdown("## ⚪ **NEUTRAL**")
                st.markdown("Range-bound")
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Detailed breakdown
        with st.expander("📋 Model Details"):
            st.markdown(f"""
            **Model Parameters:**
            - Correlation: {prognosis['correlation']:+.3f}
            - Slope: {prognosis['slope']:.4f}
            - Intercept: {prognosis['intercept']:.4f}
            
            **Formula:** {currency_pair} = {prognosis['slope']:.4f} × Spread + {prognosis['intercept']:.4f}
            
            **Current State:**
            - Spread: {prognosis['current_spread']:.2f}%
            - {currency_pair}: {prognosis['current_fx']:.4f}
            - Fair Value: {prognosis['current_fair_value']:.4f}
            - Deviation: {prognosis['current_deviation']:+.2f}%
            
            **Target State:**
            - Target Spread: {prognosis['target_spread']:.2f}%
            - Predicted {currency_pair}: {prognosis['predicted_fx']:.4f}
            
            **Changes:**
            - Spread: {prognosis['spread_change']:+.2f}%
            - {currency_pair}: {prognosis['fx_change']:+.4f} ({prognosis['fx_change_pct']:+.2f}%)
            """)
        
        # Visualization
        st.markdown('<div class="sub-header">📈 Charts</div>', unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["Fair Value Analysis", "Prognosis Scatter", "Historical Time Series"])
        
        with tab1:
            # Fair Value Chart
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=(f'{currency_pair}: Actual vs Fair Value', 'Deviation from Fair Value (%)'),
                vertical_spacing=0.15,
                row_heights=[0.6, 0.4]
            )
            
            # Actual vs Fair Value
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['FX_Rate'],
                name=f'Actual {currency_pair}',
                line=dict(color='#0051a5', width=2.5)
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Fair_Value'],
                name='Fair Value',
                line=dict(color='#ff7f0e', width=2, dash='dash')
            ), row=1, col=1)
            
            # Current points
            current_date = df['Date'].iloc[-1]
            fig.add_trace(go.Scatter(
                x=[current_date], y=[df['FX_Rate'].iloc[-1]],
                mode='markers',
                name='Current Actual',
                marker=dict(size=15, color='green', symbol='circle',
                           line=dict(color='black', width=2))
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=[current_date], y=[df['Fair_Value'].iloc[-1]],
                mode='markers',
                name='Current Fair Value',
                marker=dict(size=15, color='orange', symbol='square',
                           line=dict(color='black', width=2))
            ), row=1, col=1)
            
            # Deviation
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Deviation_Pct'],
                name='Deviation %',
                fill='tozeroy',
                fillcolor='rgba(128, 0, 128, 0.2)',
                line=dict(color='purple', width=2)
            ), row=2, col=1)
            
            fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, row=2, col=1)
            fig.add_hline(y=2, line_dash="dash", line_color="red", line_width=1, opacity=0.5, row=2, col=1)
            fig.add_hline(y=-2, line_dash="dash", line_color="green", line_width=1, opacity=0.5, row=2, col=1)
            
            fig.add_trace(go.Scatter(
                x=[current_date], y=[df['Deviation_Pct'].iloc[-1]],
                mode='markers',
                name='Current Deviation',
                marker=dict(size=15,
                           color='red' if df['Deviation_Pct'].iloc[-1] > 0 else 'green',
                           symbol='circle',
                           line=dict(color='black', width=2))
            ), row=2, col=1)
            
            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_yaxes(title_text=currency_pair, row=1, col=1)
            fig.update_yaxes(title_text="Deviation (%)", row=2, col=1)
            
            fig.update_layout(
                height=800,
                showlegend=True,
                hovermode='x unified',
                title_text=f'Fair Value Analysis | Deviation: {df["Deviation_Pct"].iloc[-1]:+.2f}% | Correlation: {prognosis["correlation"]:+.3f}'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Mean Deviation", f"{df['Deviation_Pct'].mean():+.2f}%")
            with col2:
                st.metric("Std Deviation", f"{df['Deviation_Pct'].std():.2f}%")
            with col3:
                recent_dev = df.tail(52)['Deviation_Pct'].mean()
                st.metric("Recent 52w Mean", f"{recent_dev:+.2f}%")
            with col4:
                max_dev = df['Deviation_Pct'].abs().max()
                st.metric("Max Deviation", f"{max_dev:.2f}%")
        
        with tab2:
            # Scatter plot
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df['Spread'],
                y=df['FX_Rate'],
                mode='markers',
                name='Historical',
                marker=dict(size=5, color='lightblue', opacity=0.5)
            ))
            
            recent = df.tail(52)
            fig.add_trace(go.Scatter(
                x=recent['Spread'],
                y=recent['FX_Rate'],
                mode='markers',
                name='Recent 52w',
                marker=dict(size=7, color='blue', opacity=0.7)
            ))
            
            # Regression line
            x_range = np.linspace(df['Spread'].min(), df['Spread'].max(), 100)
            y_pred = prognosis['slope'] * x_range + prognosis['intercept']
            fig.add_trace(go.Scatter(
                x=x_range,
                y=y_pred,
                mode='lines',
                name=f'Trend (r={prognosis["correlation"]:.3f})',
                line=dict(color='red', width=2, dash='dash')
            ))
            
            # Current and target
            fig.add_trace(go.Scatter(
                x=[prognosis['current_spread']],
                y=[prognosis['current_fx']],
                mode='markers+text',
                name='Current',
                marker=dict(size=15, color='green', symbol='star'),
                text=['NOW'],
                textposition='top center'
            ))
            
            fig.add_trace(go.Scatter(
                x=[prognosis['target_spread']],
                y=[prognosis['predicted_fx']],
                mode='markers+text',
                name='Target',
                marker=dict(size=15, color='orange', symbol='star'),
                text=['TARGET'],
                textposition='top center'
            ))
            
            fig.add_annotation(
                x=prognosis['target_spread'],
                y=prognosis['predicted_fx'],
                ax=prognosis['current_spread'],
                ay=prognosis['current_fx'],
                xref='x', yref='y',
                axref='x', ayref='y',
                showarrow=True,
                arrowhead=3,
                arrowsize=2,
                arrowwidth=2,
                arrowcolor='red'
            )
            
            fig.update_layout(
                title=f'{currency_pair} vs {long_term_label}-{short_term_label} Spread',
                xaxis_title=f'{long_term_label}-{short_term_label} Spread (%)',
                yaxis_title=currency_pair,
                height=600,
                hovermode='closest'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            # Time series
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=(currency_pair, f'{long_term_label}-{short_term_label} Spread'),
                vertical_spacing=0.15
            )
            
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['FX_Rate'],
                name=currency_pair,
                line=dict(color='#0051a5', width=2)
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Spread'],
                name='Spread',
                fill='tozeroy',
                line=dict(color='#2ca02c', width=2)
            ), row=2, col=1)
            
            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_yaxes(title_text=currency_pair, row=1, col=1)
            fig.update_yaxes(title_text="Spread (%)", row=2, col=1)
            
            fig.update_layout(height=700, hovermode='x unified')
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Export
        st.markdown('<div class="sub-header">💾 Export Results</div>', unsafe_allow_html=True)
        
        export_data = pd.DataFrame([{
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'Currency_Pair': currency_pair,
            'Current_FX': prognosis['current_fx'],
            'Fair_Value': prognosis['current_fair_value'],
            'Deviation_Pct': prognosis['current_deviation'],
            'Current_Spread': prognosis['current_spread'],
            f'Target_{short_term_label}': target_short,
            f'Target_{long_term_label}': target_long,
            'Target_Spread': prognosis['target_spread'],
            'Predicted_FX': prognosis['predicted_fx'],
            'Change_Absolute': prognosis['fx_change'],
            'Change_Percent': prognosis['fx_change_pct'],
            'Correlation': prognosis['correlation'],
            'Scenario': scenario
        }])
        
        csv = export_data.to_csv(index=False)
        st.download_button(
            label=f"📥 Download {currency_pair} Prognosis (CSV)",
            data=csv,
            file_name=f"{base_currency}{quote_currency}_prognosis_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.exception(e)

else:
    # Instructions
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown(f"""
    ### 👆 Getting Started
    
    **Configure in sidebar:**
    1. Set your currency pair (e.g., EUR/USD, GBP/USD, USD/JPY)
    2. Define yield labels (e.g., 10Y-30Y, 2Y-10Y, 5Y-20Y)
    3. Upload 3 CSV files
    
    **Upload required:**
    - Currency pair historical data
    - Quote currency short-term yield
    - Quote currency long-term yield
    """)
    st.markdown("</div>", unsafe_allow_html=True)
    
    with st.expander("📖 Universal Model Guide"):
        st.markdown("""
        ## How This Universal Model Works
        
        ### Concept
        
        This tool analyzes the relationship between **any currency pair** and the **yield curve spread** 
        of the quote currency (second currency in the pair).
        
        ### Examples
        
        **EUR/USD:**
        - Analyze EUR/USD vs US Treasury spread (10Y-30Y)
        - Quote currency = USD → Use US yields
        
        **GBP/USD:**
        - Analyze GBP/USD vs US Treasury spread
        - Quote currency = USD → Use US yields
        
        **EUR/GBP:**
        - Analyze EUR/GBP vs UK Gilt spread
        - Quote currency = GBP → Use UK yields
        
        **USD/JPY:**
        - Analyze USD/JPY vs Japanese JGB spread
        - Quote currency = JPY → Use Japanese yields
        
        ### Correlation Interpretation
        
        **Positive Correlation (+0.5 to +1.0):**
        - Wider spread → Currency pair RISES (base currency strengthens)
        - Narrower spread → Currency pair FALLS (base currency weakens)
        
        **Negative Correlation (-0.5 to -1.0):**
        - Wider spread → Currency pair FALLS (base currency weakens)
        - Narrower spread → Currency pair RISES (base currency strengthens)
        
        **Weak Correlation (-0.4 to +0.4):**
        - Model not reliable for this pair
        - Consider other factors or different yield maturities
        
        ### Data Sources
        
        **FX Data:**
        - Investing.com (various languages)
        - Yahoo Finance
        - FRED
        - Any CSV with Date, Close columns
        
        **Yield Data:**
        - FRED (US Treasuries)
        - National central bank websites
        - Bloomberg
        - Any CSV with Date, Yield columns
        
        ### Best Practices
        
        1. **Use at least 3 years of data** for reliable correlation
        2. **Check correlation strength** - aim for |r| > 0.6
        3. **Verify data alignment** - ensure dates overlap
        4. **Consider context** - correlation can break during regime changes
        5. **Combine with fundamental analysis** - model is just one tool
        
        ### Limitations
        
        - Historical correlation ≠ future relationship
        - Works best for liquid currency pairs
        - Central bank policy changes can break correlation
        - Geopolitical events may override spread dynamics
        """)

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <b>Universal FX Spread Prognosis Tool</b> | 
    Works with any currency pair and yield curve | 
    Fair value + Correlation-based forecast
</div>
""", unsafe_allow_html=True)
