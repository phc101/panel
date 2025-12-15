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

# Helper functions for parsing different formats
def parse_fx_data(file, data_format):
    """Parse FX data based on format"""
    try:
        if data_format == "Investing.com (Polish)":
            df = pd.read_csv(file, encoding='utf-8-sig')
            # Handle different possible column counts
            if len(df.columns) >= 2:
                df = df.iloc[:, [0, 1]]  # Take first two columns
                df.columns = ['Date', 'Close']
            df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y', errors='coerce')
            df['Close'] = df['Close'].astype(str).str.replace(',', '.').astype(float)
        elif data_format == "Investing.com (English)":
            df = pd.read_csv(file)
            if len(df.columns) >= 2:
                df = df.iloc[:, [0, 1]]
                df.columns = ['Date', 'Close']
            df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y', errors='coerce')
            df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        elif data_format == "Yahoo Finance":
            df = pd.read_csv(file)
            df = df[['Date', 'Close']]
            df['Date'] = pd.to_datetime(df['Date'])
            df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        elif data_format == "FRED":
            df = pd.read_csv(file)
            if len(df.columns) >= 2:
                df = df.iloc[:, [0, 1]]
                df.columns = ['Date', 'Close']
            df['Date'] = pd.to_datetime(df['Date'])
            df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        else:  # Custom
            df = pd.read_csv(file)
            if len(df.columns) >= 2:
                df = df.iloc[:, [0, 1]]
                df.columns = ['Date', 'Close']
            if decimal_sep_fx == ',':
                df['Close'] = df['Close'].astype(str).str.replace(',', '.').astype(float)
            df['Date'] = pd.to_datetime(df['Date'], format=date_format_fx)
        
        return df.sort_values('Date')[['Date', 'Close']].dropna()
    except Exception as e:
        st.error(f"Error parsing FX data: {str(e)}")
        st.stop()

def parse_yield_data(file):
    """Parse yield data - flexible format handling"""
    try:
        df = pd.read_csv(file)
        
        # Take only first 2 columns regardless of what they are
        if len(df.columns) >= 2:
            df = df.iloc[:, [0, 1]]
            df.columns = ['Date', 'Yield']
        else:
            raise ValueError(f"File must have at least 2 columns, found {len(df.columns)}")
        
        # Parse date
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # Parse yield (handle commas as decimal separator)
        if df['Yield'].dtype == 'object':
            df['Yield'] = df['Yield'].astype(str).str.replace(',', '.').astype(float, errors='ignore')
        df['Yield'] = pd.to_numeric(df['Yield'], errors='coerce')
        
        # Drop NaN
        df = df.dropna()
        
        if len(df) == 0:
            raise ValueError("No valid data after cleaning")
        
        return df
    except Exception as e:
        st.error(f"Error parsing yield data: {str(e)}")
        st.error("Expected format: First column = Date, Second column = Yield value")
        st.stop()

def process_data(fx_df, short_df, long_df):
    """Merge FX and yield data"""
    # Merge yields
    yields = short_df.merge(long_df, on='Date', how='inner', suffixes=('_Short', '_Long'))
    
    if len(yields) == 0:
        raise ValueError("No overlapping dates between short and long yield data")
    
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
    
    if len(merged_data) == 0:
        raise ValueError("No overlapping dates between FX and yield data")
    
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
            short_df = parse_yield_data(short_file)
            long_df = parse_yield_data(long_file)
            
            # Show data info
            with st.expander("📊 Data Summary"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**{currency_pair} Data:**")
                    st.write(f"- Records: {len(fx_df)}")
                    st.write(f"- From: {fx_df['Date'].min().date()}")
                    st.write(f"- To: {fx_df['Date'].max().date()}")
                with col2:
                    st.write(f"**{short_term_label} Yield:**")
                    st.write(f"- Records: {len(short_df)}")
                    st.write(f"- From: {short_df['Date'].min().date()}")
                    st.write(f"- To: {short_df['Date'].max().date()}")
                with col3:
                    st.write(f"**{long_term_label} Yield:**")
                    st.write(f"- Records: {len(long_df)}")
                    st.write(f"- From: {long_df['Date'].min().date()}")
                    st.write(f"- To: {long_df['Date'].max().date()}")
            
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
        
        # Visualization - simplified to avoid errors
        st.markdown('<div class="sub-header">📈 Charts</div>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Fair Value Analysis", "Prognosis Scatter"])
        
        with tab1:
            # Fair Value Chart
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=(f'{currency_pair}: Actual vs Fair Value', 'Deviation from Fair Value (%)'),
                vertical_spacing=0.15,
                row_heights=[0.6, 0.4]
            )
            
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
            
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Deviation_Pct'],
                name='Deviation %',
                fill='tozeroy',
                line=dict(color='purple', width=2)
            ), row=2, col=1)
            
            fig.add_hline(y=0, line_dash="solid", line_color="black", row=2, col=1)
            fig.add_hline(y=2, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
            fig.add_hline(y=-2, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)
            
            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_yaxes(title_text=currency_pair, row=1, col=1)
            fig.update_yaxes(title_text="Deviation (%)", row=2, col=1)
            
            fig.update_layout(height=800, showlegend=True, hovermode='x unified')
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            # Scatter plot
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df['Spread'], y=df['FX_Rate'],
                mode='markers',
                name='Historical',
                marker=dict(size=5, color='lightblue', opacity=0.5)
            ))
            
            # Regression line
            x_range = np.linspace(df['Spread'].min(), df['Spread'].max(), 100)
            y_pred = prognosis['slope'] * x_range + prognosis['intercept']
            fig.add_trace(go.Scatter(
                x=x_range, y=y_pred,
                mode='lines',
                name=f'Trend (r={prognosis["correlation"]:.3f})',
                line=dict(color='red', width=2, dash='dash')
            ))
            
            fig.add_trace(go.Scatter(
                x=[prognosis['current_spread']], y=[prognosis['current_fx']],
                mode='markers',
                name='Current',
                marker=dict(size=15, color='green', symbol='star')
            ))
            
            fig.add_trace(go.Scatter(
                x=[prognosis['target_spread']], y=[prognosis['predicted_fx']],
                mode='markers',
                name='Target',
                marker=dict(size=15, color='orange', symbol='star')
            ))
            
            fig.update_layout(
                title=f'{currency_pair} vs {long_term_label}-{short_term_label} Spread',
                xaxis_title=f'Spread (%)',
                yaxis_title=currency_pair,
                height=600
            )
            
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
            'Change_Percent': prognosis['fx_change_pct'],
            'Correlation': prognosis['correlation']
        }])
        
        csv = export_data.to_csv(index=False)
        st.download_button(
            label=f"📥 Download Results",
            data=csv,
            file_name=f"{base_currency}{quote_currency}_prognosis_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        with st.expander("🔍 Debug Info"):
            st.exception(e)

else:
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown(f"""
    ### 👆 Getting Started
    
    **Configure in sidebar:**
    1. Set your currency pair (default: EUR/USD)
    2. Define yield labels (default: 10Y-30Y)
    3. Upload 3 CSV files
    
    **File format requirements:**
    - **FX data**: First 2 columns = Date, Close price
    - **Yield data**: First 2 columns = Date, Yield value
    - Other columns will be ignored
    
    **Supported formats:**
    - Investing.com (Polish/English)
    - Yahoo Finance
    - FRED
    - Custom CSV
    """)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <b>Universal FX Spread Prognosis Tool</b> | 
    Works with any currency pair and yield curve
</div>
""", unsafe_allow_html=True)
