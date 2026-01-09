import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="FX Spread Prognosis",
    page_icon="💹",
    layout="wide"
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
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #0051a5;
    }
    .prognosis-box {
        background-color: #fff3e0;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 2px solid #ff9800;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">FX Spread Prognosis Tool 📊</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("📁 Upload Data")
    
    st.subheader("Yield Data (Required)")
    dgs10_file = st.file_uploader("US 10Y Treasury", type=['csv'])
    dgs30_file = st.file_uploader("US 30Y Treasury", type=['csv'])
    
    st.subheader("FX Data")
    usdpln_file = st.file_uploader("USD/PLN", type=['csv'])
    eurpln_file = st.file_uploader("EUR/PLN", type=['csv'])
    
    st.markdown("---")
    use_recent = st.checkbox("Use Recent 52 weeks", value=False)

# Helper functions
def parse_fx_data(file):
    """Parse FX data from Investing.com"""
    df = pd.read_csv(file, encoding='utf-8-sig')
    
    # Get Date and Price columns
    if 'Date' in df.columns and 'Price' in df.columns:
        df = df[['Date', 'Price']].copy()
    else:
        df = df.iloc[:, [0, 1]].copy()
    
    df.columns = ['Date', 'Close']
    
    # Parse dates (auto-detect format)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # Clean price data
    if df['Close'].dtype == 'object':
        df['Close'] = df['Close'].astype(str).str.replace('"', '').str.replace(',', '.')
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    
    return df.dropna().sort_values('Date')

def parse_yield_data(file):
    """Parse FRED yield data"""
    df = pd.read_csv(file)
    df.columns = ['Date', 'Yield']
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Yield'] = pd.to_numeric(df['Yield'], errors='coerce')
    return df.dropna()

def merge_fx_with_yields(fx_df, y10_df, y30_df):
    """Merge FX data with yield data"""
    # Merge yields
    yields = y10_df.merge(y30_df, on='Date', suffixes=('_10Y', '_30Y'))
    
    result = []
    for _, row in fx_df.iterrows():
        fx_date = row['Date']
        # Find closest yield within 7 days
        yield_match = yields[abs(yields['Date'] - fx_date) <= timedelta(days=7)]
        
        if len(yield_match) > 0:
            closest = yield_match.iloc[(yield_match['Date'] - fx_date).abs().argmin()]
            result.append({
                'Date': fx_date,
                'FX_Rate': row['Close'],
                '10Y': closest['Yield_10Y'],
                '30Y': closest['Yield_30Y'],
                'Spread': closest['Yield_30Y'] - closest['Yield_10Y']
            })
    
    if not result:
        raise ValueError("No matching dates found between FX and yield data")
    
    return pd.DataFrame(result)

def calculate_model(df, use_recent=False):
    """Calculate fair value model"""
    data = df.tail(52) if use_recent and len(df) >= 52 else df
    
    # Linear regression
    z = np.polyfit(data['Spread'], data['FX_Rate'], 1)
    slope, intercept = z[0], z[1]
    
    # Calculate metrics
    df['Fair_Value'] = slope * df['Spread'] + intercept
    df['Deviation'] = df['FX_Rate'] - df['Fair_Value']
    df['Deviation_Pct'] = (df['Deviation'] / df['Fair_Value']) * 100
    
    correlation = data['FX_Rate'].corr(data['Spread'])
    
    return df, correlation, slope, intercept

# Main app
if all([dgs10_file, dgs30_file]) and (usdpln_file or eurpln_file):
    try:
        # Load yield data
        with st.spinner("Loading yield data..."):
            y10 = parse_yield_data(dgs10_file)
            y30 = parse_yield_data(dgs30_file)
        
        # Load FX pairs
        pairs = {}
        
        if usdpln_file:
            with st.spinner("Loading USD/PLN..."):
                fx_usdpln = parse_fx_data(usdpln_file)
                df_usdpln = merge_fx_with_yields(fx_usdpln, y10, y30)
                df_usdpln, corr_usdpln, slope_usdpln, int_usdpln = calculate_model(df_usdpln, use_recent)
                pairs['USD/PLN'] = {
                    'df': df_usdpln,
                    'corr': corr_usdpln,
                    'slope': slope_usdpln,
                    'intercept': int_usdpln
                }
                st.success(f"✅ Loaded {len(df_usdpln)} USD/PLN observations")
        
        if eurpln_file:
            with st.spinner("Loading EUR/PLN..."):
                fx_eurpln = parse_fx_data(eurpln_file)
                df_eurpln = merge_fx_with_yields(fx_eurpln, y10, y30)
                df_eurpln, corr_eurpln, slope_eurpln, int_eurpln = calculate_model(df_eurpln, use_recent)
                pairs['EUR/PLN'] = {
                    'df': df_eurpln,
                    'corr': corr_eurpln,
                    'slope': slope_eurpln,
                    'intercept': int_eurpln
                }
                st.success(f"✅ Loaded {len(df_eurpln)} EUR/PLN observations")
        
        # Current data
        st.markdown("## 📊 Current Market Data")
        
        cols = st.columns(len(pairs) + 1)
        
        with cols[0]:
            current = list(pairs.values())[0]['df'].iloc[-1]
            st.metric("30Y-10Y Spread", f"{current['Spread']:.2f}%")
        
        for idx, (name, data) in enumerate(pairs.items()):
            with cols[idx + 1]:
                current = data['df'].iloc[-1]
                st.metric(
                    name,
                    f"{current['FX_Rate']:.4f}",
                    delta=f"{current['Deviation_Pct']:+.2f}% vs FV"
                )
        
        # Correlation display
        st.markdown("## 🔗 Spread Correlation")
        
        cols = st.columns(len(pairs))
        for idx, (name, data) in enumerate(pairs.items()):
            with cols[idx]:
                corr_strength = "Strong" if abs(data['corr']) > 0.7 else "Moderate" if abs(data['corr']) > 0.5 else "Weak"
                st.markdown(f"""
                <div class="metric-card">
                    <b>{name}</b><br>
                    Correlation: <b>{data['corr']:+.3f}</b><br>
                    <small>{corr_strength}</small>
                </div>
                """, unsafe_allow_html=True)
        
        # Scenario analysis
        st.markdown("## 🎯 Prognosis Scenario")
        
        current = list(pairs.values())[0]['df'].iloc[-1]
        
        col1, col2 = st.columns(2)
        
        with col1:
            scenario = st.selectbox(
                "Scenario",
                ["Custom", "Steepening (+20%)", "Steepening (+50%)", 
                 "Flattening (-20%)", "Flattening (-50%)", "Current"]
            )
            
            if scenario == "Custom":
                target_10y = st.number_input("Target 10Y (%)", value=float(current['10Y']), 
                                           min_value=0.0, max_value=10.0, step=0.1)
                target_30y = st.number_input("Target 30Y (%)", value=float(current['30Y']), 
                                           min_value=0.0, max_value=10.0, step=0.1)
            elif "Steepening" in scenario:
                pct = 0.2 if "20%" in scenario else 0.5
                target_10y = float(current['10Y'])
                target_30y = float(current['30Y']) + (current['Spread'] * pct)
            elif "Flattening" in scenario:
                pct = 0.2 if "20%" in scenario else 0.5
                target_10y = float(current['10Y'])
                target_30y = float(current['30Y']) - (current['Spread'] * pct)
            else:
                target_10y = float(current['10Y'])
                target_30y = float(current['30Y'])
        
        with col2:
            target_spread = target_30y - target_10y
            spread_change = target_spread - current['Spread']
            
            st.metric("Target Spread", f"{target_spread:.2f}%", delta=f"{spread_change:.2f}%")
            
            if spread_change > 0.1:
                st.success("🟢 WIDENING")
            elif spread_change < -0.1:
                st.error("🔴 NARROWING")
            else:
                st.info("⚪ STABLE")
        
        # Forecasts
        st.markdown("## 📈 Forecasts")
        
        cols = st.columns(len(pairs))
        
        for idx, (name, data) in enumerate(pairs.items()):
            current_rate = data['df'].iloc[-1]['FX_Rate']
            target_rate = data['slope'] * target_spread + data['intercept']
            change_pct = ((target_rate - current_rate) / current_rate) * 100
            
            with cols[idx]:
                st.markdown('<div class="prognosis-box">', unsafe_allow_html=True)
                st.markdown(f"### {name}")
                st.markdown(f"**Current:** {current_rate:.4f}")
                st.markdown(f"**Target:** {target_rate:.4f}")
                
                color = "🟢" if change_pct < 0 else "🔴" if change_pct > 0 else "⚪"
                st.markdown(f"**Change:** {color} {change_pct:+.2f}%")
                st.markdown("---")
                
                if abs(change_pct) > 1:
                    direction = "strengthens" if change_pct < 0 else "weakens"
                    st.markdown(f"✅ **PLN {direction}**")
                else:
                    st.markdown("➡️ **PLN stable**")
                
                st.markdown("</div>", unsafe_allow_html=True)
        
        # Charts
        st.markdown("## 📊 Historical Analysis")
        
        for name, data in pairs.items():
            df = data['df']
            
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=(f'{name}: Actual vs Fair Value', 'Deviation (%)'),
                vertical_spacing=0.12,
                row_heights=[0.65, 0.35]
            )
            
            # Actual vs Fair Value
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['FX_Rate'],
                name='Actual', line=dict(color='#0051a5', width=2.5)
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Fair_Value'],
                name='Fair Value', line=dict(color='#ff7f0e', width=2, dash='dash')
            ), row=1, col=1)
            
            # Deviation
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Deviation_Pct'],
                name='Deviation', fill='tozeroy',
                line=dict(color='purple', width=2)
            ), row=2, col=1)
            
            fig.add_hline(y=0, line_dash="solid", line_color="black", row=2, col=1)
            fig.add_hline(y=2, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
            fig.add_hline(y=-2, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)
            
            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_yaxes(title_text=name, row=1, col=1)
            fig.update_yaxes(title_text="Deviation (%)", row=2, col=1)
            
            fig.update_layout(
                height=700,
                showlegend=True,
                hovermode='x unified',
                title_text=f'{name} Analysis | Correlation: {data["corr"]:+.3f}'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Export
        st.markdown("## 💾 Export")
        
        export_data = {
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'Scenario': scenario,
            'Target_Spread': target_spread,
            'Spread_Change': spread_change
        }
        
        for name, data in pairs.items():
            current_rate = data['df'].iloc[-1]['FX_Rate']
            target_rate = data['slope'] * target_spread + data['intercept']
            change_pct = ((target_rate - current_rate) / current_rate) * 100
            
            export_data[f'{name}_Current'] = current_rate
            export_data[f'{name}_Target'] = target_rate
            export_data[f'{name}_Change_%'] = change_pct
            export_data[f'{name}_Correlation'] = data['corr']
        
        csv = pd.DataFrame([export_data]).to_csv(index=False)
        
        st.download_button(
            "📥 Download Results CSV",
            data=csv,
            file_name=f"fx_prognosis_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        with st.expander("Debug Info"):
            st.exception(e)

else:
    st.info("""
    ### 👆 Getting Started
    
    **Upload Required Files:**
    1. US 10Y Treasury yield (from FRED)
    2. US 30Y Treasury yield (from FRED)
    3. At least one FX pair (USD/PLN or EUR/PLN from Investing.com)
    
    **How It Works:**
    - Analyzes correlation between US yield spread (30Y-10Y) and FX rates
    - Calculates fair value based on historical relationship
    - Projects future FX rates based on yield spread scenarios
    
    **Data Sources:**
    - FRED: https://fred.stlouisfed.org
    - Investing.com: Historical FX data
    """)

st.markdown("---")
st.markdown("<div style='text-align: center; color: #666;'>FX Spread Prognosis Tool</div>", 
            unsafe_allow_html=True)
