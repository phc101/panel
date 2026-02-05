import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests

# Page config
st.set_page_config(
    page_title="FX-Yield Spread Analyzer",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
    
    .stApp {
        font-family: 'IBM Plex Sans', sans-serif;
    }
    
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        text-align: center;
        padding: 1.5rem 2rem;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        color: #e94560;
        border-radius: 0;
        margin: -1rem -1rem 2rem -1rem;
        border-bottom: 3px solid #e94560;
        letter-spacing: -0.5px;
    }
    
    .main-header span {
        color: #ffffff;
        font-weight: 400;
    }
    
    .metric-panel {
        background: linear-gradient(145deg, #1a1a2e 0%, #16213e 100%);
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #0f3460;
        margin-bottom: 1rem;
        color: white;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #e94560;
        font-family: 'IBM Plex Mono', monospace;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #a0a0a0;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }
    
    .metric-delta {
        font-size: 1rem;
        font-family: 'IBM Plex Mono', monospace;
    }
    
    .metric-delta.positive { color: #00d26a; }
    .metric-delta.negative { color: #e94560; }
    
    .forecast-box {
        background: linear-gradient(145deg, #0f3460 0%, #1a1a2e 100%);
        padding: 2rem;
        border-radius: 8px;
        border: 2px solid #e94560;
        text-align: center;
        margin: 1rem 0;
    }
    
    .forecast-value {
        font-size: 3.5rem;
        font-weight: 700;
        color: #ffffff;
        font-family: 'IBM Plex Mono', monospace;
    }
    
    .forecast-change {
        font-size: 1.5rem;
        font-family: 'IBM Plex Mono', monospace;
        margin-top: 0.5rem;
    }
    
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .stat-card {
        background: #16213e;
        padding: 1rem;
        border-radius: 6px;
        text-align: center;
        border-left: 3px solid #e94560;
    }
    
    .stat-value {
        font-size: 1.4rem;
        font-weight: 600;
        color: #ffffff;
        font-family: 'IBM Plex Mono', monospace;
    }
    
    .stat-label {
        font-size: 0.75rem;
        color: #808080;
        margin-top: 0.3rem;
    }
    
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #e94560;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #0f3460;
    }
    
    .data-status {
        background: #0f3460;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        color: #00d26a;
        display: inline-block;
        margin: 0.5rem 0;
    }
    
    .slider-container {
        background: #16213e;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    /* Streamlit overrides */
    .stSlider label {
        color: #ffffff !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
    }
    
    div[data-testid="stMetricValue"] {
        font-family: 'IBM Plex Mono', monospace !important;
    }
</style>
""", unsafe_allow_html=True)


# =====================================================
# DATA FETCHING FUNCTIONS
# =====================================================

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_fred_data(series_id, start_date="2010-01-01"):
    """Fetch data from FRED API (no key required for basic access)"""
    try:
        # Use FRED's public CSV endpoint
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start_date}"
        df = pd.read_csv(url)
        df.columns = ['Date', 'Value']
        df['Date'] = pd.to_datetime(df['Date'])
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        df = df.dropna()
        return df
    except Exception as e:
        st.error(f"Error fetching FRED data ({series_id}): {e}")
        return None


@st.cache_data(ttl=3600)
def fetch_yahoo_data(symbol, period="10y"):
    """Fetch data from Yahoo Finance"""
    try:
        # Calculate timestamps
        end_ts = int(datetime.now().timestamp())
        if period == "10y":
            start_ts = int((datetime.now() - timedelta(days=365*10)).timestamp())
        elif period == "5y":
            start_ts = int((datetime.now() - timedelta(days=365*5)).timestamp())
        else:
            start_ts = int((datetime.now() - timedelta(days=365*15)).timestamp())
        
        url = f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}"
        params = {
            'period1': start_ts,
            'period2': end_ts,
            'interval': '1d',
            'events': 'history'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))
        df['Date'] = pd.to_datetime(df['Date'])
        df = df[['Date', 'Close']].rename(columns={'Close': 'Value'})
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        df = df.dropna()
        return df
    except Exception as e:
        st.error(f"Error fetching Yahoo data ({symbol}): {e}")
        return None


def merge_datasets(df1, df2, df3=None):
    """Merge datasets on date"""
    merged = df1.merge(df2, on='Date', suffixes=('_1', '_2'))
    if df3 is not None:
        merged = merged.merge(df3, on='Date')
        merged.columns = ['Date', 'Y10', 'Y30', 'FX']
    else:
        merged.columns = ['Date', 'Spread', 'FX']
    return merged.sort_values('Date')


def calculate_regression(x, y):
    """Calculate linear regression and statistics"""
    mask = ~(np.isnan(x) | np.isnan(y))
    x_clean, y_clean = x[mask], y[mask]
    
    # Linear regression
    z = np.polyfit(x_clean, y_clean, 1)
    slope, intercept = z[0], z[1]
    
    # Predictions and residuals
    y_pred = slope * x_clean + intercept
    residuals = y_clean - y_pred
    
    # R-squared
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y_clean - np.mean(y_clean))**2)
    r_squared = 1 - (ss_res / ss_tot)
    
    # Correlation
    correlation = np.corrcoef(x_clean, y_clean)[0, 1]
    
    # Standard error of estimate
    std_error = np.std(residuals)
    
    return {
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_squared,
        'correlation': correlation,
        'std_error': std_error,
        'n_obs': len(x_clean)
    }


# =====================================================
# MAIN APP
# =====================================================

st.markdown('<div class="main-header">FX-Yield Spread <span>Analyzer</span></div>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    fx_pair = st.selectbox(
        "FX Pair",
        ["EURUSD=X", "USDPLN=X", "EURPLN=X", "GBPUSD=X", "USDJPY=X"],
        index=0,
        help="Select currency pair from Yahoo Finance"
    )
    
    fx_pair_display = fx_pair.replace("=X", "").replace("USD", "/USD").replace("EUR", "EUR/").replace("GBP", "GBP/").replace("JPY", "/JPY")
    if fx_pair == "EURUSD=X":
        fx_pair_display = "EUR/USD"
    elif fx_pair == "USDPLN=X":
        fx_pair_display = "USD/PLN"
    elif fx_pair == "EURPLN=X":
        fx_pair_display = "EUR/PLN"
    
    data_period = st.selectbox(
        "Data Period",
        ["5y", "10y", "15y"],
        index=1
    )
    
    regression_window = st.selectbox(
        "Regression Window",
        ["All data", "Last 52 weeks", "Last 104 weeks", "Last 3 years"],
        index=0
    )
    
    st.markdown("---")
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Fetch data
with st.spinner("📡 Fetching data from FRED and Yahoo Finance..."):
    # FRED: 10Y and 30Y Treasury yields
    y10_df = fetch_fred_data("DGS10", "2010-01-01")
    y30_df = fetch_fred_data("DGS30", "2010-01-01")
    
    # Yahoo: FX pair
    fx_df = fetch_yahoo_data(fx_pair, data_period)

if y10_df is not None and y30_df is not None and fx_df is not None:
    
    # Merge yield data first
    yields_df = y10_df.merge(y30_df, on='Date', suffixes=('_10Y', '_30Y'))
    yields_df['Spread'] = yields_df['Value_30Y'] - yields_df['Value_10Y']
    yields_df = yields_df[['Date', 'Value_10Y', 'Value_30Y', 'Spread']]
    yields_df.columns = ['Date', 'Y10', 'Y30', 'Spread']
    
    # Merge with FX
    df = yields_df.merge(fx_df, on='Date', how='inner')
    df.columns = ['Date', 'Y10', 'Y30', 'Spread', 'FX']
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Apply regression window
    if regression_window == "Last 52 weeks":
        reg_df = df.tail(252)
    elif regression_window == "Last 104 weeks":
        reg_df = df.tail(504)
    elif regression_window == "Last 3 years":
        reg_df = df.tail(756)
    else:
        reg_df = df
    
    # Calculate regression
    stats = calculate_regression(reg_df['Spread'].values, reg_df['FX'].values)
    
    # Fair value for full dataset
    df['Fair_Value'] = stats['slope'] * df['Spread'] + stats['intercept']
    df['Deviation'] = df['FX'] - df['Fair_Value']
    df['Deviation_Pct'] = (df['Deviation'] / df['Fair_Value']) * 100
    
    # Current values
    current = df.iloc[-1]
    
    # Data status
    st.markdown(f"""
        <div class="data-status">
            ✓ Loaded {len(df):,} observations | {df['Date'].min().strftime('%Y-%m-%d')} → {df['Date'].max().strftime('%Y-%m-%d')}
        </div>
    """, unsafe_allow_html=True)
    
    # =====================================================
    # CURRENT MARKET DATA
    # =====================================================
    st.markdown('<div class="section-header">📊 Current Market Data</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="metric-panel">
                <div class="metric-label">10Y Treasury</div>
                <div class="metric-value">{current['Y10']:.2f}%</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-panel">
                <div class="metric-label">30Y Treasury</div>
                <div class="metric-value">{current['Y30']:.2f}%</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="metric-panel">
                <div class="metric-label">30Y-10Y Spread</div>
                <div class="metric-value">{current['Spread']:.2f}%</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        delta_class = "positive" if current['Deviation_Pct'] < 0 else "negative"
        st.markdown(f"""
            <div class="metric-panel">
                <div class="metric-label">{fx_pair_display} Spot</div>
                <div class="metric-value">{current['FX']:.4f}</div>
                <div class="metric-delta {delta_class}">{current['Deviation_Pct']:+.2f}% vs FV</div>
            </div>
        """, unsafe_allow_html=True)
    
    # =====================================================
    # FORECAST SLIDERS
    # =====================================================
    st.markdown('<div class="section-header">🎯 Yield Forecast → FX Prognosis</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="slider-container">', unsafe_allow_html=True)
        
        # Calculate reasonable ranges
        y10_min = max(0.0, float(df['Y10'].min()) - 1)
        y10_max = float(df['Y10'].max()) + 1
        y30_min = max(0.0, float(df['Y30'].min()) - 1)
        y30_max = float(df['Y30'].max()) + 1
        
        target_10y = st.slider(
            "📉 Target 10Y Yield (%)",
            min_value=y10_min,
            max_value=y10_max,
            value=float(current['Y10']),
            step=0.05,
            format="%.2f"
        )
        
        target_30y = st.slider(
            "📈 Target 30Y Yield (%)",
            min_value=y30_min,
            max_value=y30_max,
            value=float(current['Y30']),
            step=0.05,
            format="%.2f"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Quick scenarios
        st.markdown("**Quick Scenarios:**")
        scen_col1, scen_col2, scen_col3 = st.columns(3)
        with scen_col1:
            if st.button("📈 Steepening", use_container_width=True):
                st.session_state['target_10y'] = float(current['Y10']) - 0.25
                st.session_state['target_30y'] = float(current['Y30']) + 0.25
                st.rerun()
        with scen_col2:
            if st.button("📉 Flattening", use_container_width=True):
                st.session_state['target_10y'] = float(current['Y10']) + 0.25
                st.session_state['target_30y'] = float(current['Y30']) - 0.25
                st.rerun()
        with scen_col3:
            if st.button("⬆️ Parallel +50bp", use_container_width=True):
                st.session_state['target_10y'] = float(current['Y10']) + 0.5
                st.session_state['target_30y'] = float(current['Y30']) + 0.5
                st.rerun()
    
    with col2:
        # Calculate forecast
        target_spread = target_30y - target_10y
        spread_change = target_spread - current['Spread']
        forecast_fx = stats['slope'] * target_spread + stats['intercept']
        fx_change = forecast_fx - current['FX']
        fx_change_pct = (fx_change / current['FX']) * 100
        
        # Forecast display
        change_color = "#00d26a" if fx_change < 0 else "#e94560"
        
        st.markdown(f"""
            <div class="forecast-box">
                <div class="metric-label">FORECAST {fx_pair_display}</div>
                <div class="forecast-value">{forecast_fx:.4f}</div>
                <div class="forecast-change" style="color: {change_color}">
                    {fx_change:+.4f} ({fx_change_pct:+.2f}%)
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Spread info
        spread_direction = "STEEPENING" if spread_change > 0 else "FLATTENING" if spread_change < 0 else "UNCHANGED"
        spread_color = "#00d26a" if spread_change > 0 else "#e94560" if spread_change < 0 else "#808080"
        
        st.markdown(f"""
            <div style="text-align: center; margin-top: 1rem;">
                <div class="metric-label">Target Spread</div>
                <div style="font-size: 1.8rem; font-family: 'IBM Plex Mono', monospace; color: white;">
                    {target_spread:.2f}% <span style="color: {spread_color};">({spread_change:+.2f}%)</span>
                </div>
                <div style="color: {spread_color}; font-weight: 600; margin-top: 0.5rem;">
                    {spread_direction}
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # =====================================================
    # REGRESSION STATISTICS
    # =====================================================
    st.markdown('<div class="section-header">📐 Model Statistics</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{stats['correlation']:+.3f}</div>
                <div class="stat-label">Correlation</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{stats['r_squared']:.1%}</div>
                <div class="stat-label">R-Squared</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{stats['slope']:.4f}</div>
                <div class="stat-label">Slope (β)</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">±{stats['std_error']:.4f}</div>
                <div class="stat-label">Std Error</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Interpretation
    st.markdown(f"""
        **Model Interpretation:** For every 1% increase in the 30Y-10Y spread, {fx_pair_display} changes by 
        **{stats['slope']:+.4f}** on average. Current deviation from fair value: **{current['Deviation_Pct']:+.2f}%**
    """)
    
    # =====================================================
    # SCATTER PLOT
    # =====================================================
    st.markdown('<div class="section-header">📈 Spread vs FX Relationship</div>', unsafe_allow_html=True)
    
    # Create scatter plot
    fig = go.Figure()
    
    # Historical points with color gradient by date
    fig.add_trace(go.Scatter(
        x=df['Spread'],
        y=df['FX'],
        mode='markers',
        marker=dict(
            size=6,
            color=df.index,
            colorscale='Viridis',
            opacity=0.6,
            colorbar=dict(
                title="Time",
                ticktext=[df['Date'].iloc[0].strftime('%Y'), df['Date'].iloc[-1].strftime('%Y')],
                tickvals=[df.index[0], df.index[-1]]
            )
        ),
        text=df['Date'].dt.strftime('%Y-%m-%d'),
        hovertemplate="<b>Date:</b> %{text}<br>" +
                      "<b>Spread:</b> %{x:.2f}%<br>" +
                      "<b>FX:</b> %{y:.4f}<extra></extra>",
        name='Historical'
    ))
    
    # Regression line
    x_line = np.linspace(df['Spread'].min() - 0.5, df['Spread'].max() + 0.5, 100)
    y_line = stats['slope'] * x_line + stats['intercept']
    
    fig.add_trace(go.Scatter(
        x=x_line,
        y=y_line,
        mode='lines',
        line=dict(color='#e94560', width=3),
        name=f'Regression (R²={stats["r_squared"]:.2f})'
    ))
    
    # Confidence bands (±1 std error)
    fig.add_trace(go.Scatter(
        x=np.concatenate([x_line, x_line[::-1]]),
        y=np.concatenate([y_line + stats['std_error'], (y_line - stats['std_error'])[::-1]]),
        fill='toself',
        fillcolor='rgba(233, 69, 96, 0.1)',
        line=dict(color='rgba(233, 69, 96, 0)'),
        name='±1 Std Error'
    ))
    
    # Current point
    fig.add_trace(go.Scatter(
        x=[current['Spread']],
        y=[current['FX']],
        mode='markers',
        marker=dict(size=18, color='#00d26a', symbol='star', line=dict(width=2, color='white')),
        name=f'Current ({current["Date"].strftime("%Y-%m-%d")})'
    ))
    
    # Target point
    fig.add_trace(go.Scatter(
        x=[target_spread],
        y=[forecast_fx],
        mode='markers',
        marker=dict(size=18, color='#ffd700', symbol='diamond', line=dict(width=2, color='white')),
        name=f'Forecast'
    ))
    
    # Arrow from current to target
    if abs(spread_change) > 0.01:
        fig.add_annotation(
            x=target_spread,
            y=forecast_fx,
            ax=current['Spread'],
            ay=current['FX'],
            xref='x',
            yref='y',
            axref='x',
            ayref='y',
            showarrow=True,
            arrowhead=2,
            arrowsize=1.5,
            arrowwidth=2,
            arrowcolor='#ffd700'
        )
    
    fig.update_layout(
        title=dict(
            text=f'{fx_pair_display} vs 30Y-10Y Treasury Spread',
            font=dict(size=20)
        ),
        xaxis_title='30Y-10Y Spread (%)',
        yaxis_title=fx_pair_display,
        template='plotly_dark',
        height=600,
        hovermode='closest',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor='rgba(26, 26, 46, 0.8)'
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # =====================================================
    # TIME SERIES CHART
    # =====================================================
    st.markdown('<div class="section-header">📉 Historical Time Series</div>', unsafe_allow_html=True)
    
    fig2 = make_subplots(
        rows=3, cols=1,
        subplot_titles=(f'{fx_pair_display}: Actual vs Fair Value', '30Y-10Y Spread', 'Deviation from Fair Value (%)'),
        vertical_spacing=0.08,
        row_heights=[0.4, 0.3, 0.3]
    )
    
    # FX actual vs fair value
    fig2.add_trace(go.Scatter(
        x=df['Date'], y=df['FX'],
        name='Actual',
        line=dict(color='#00d26a', width=2)
    ), row=1, col=1)
    
    fig2.add_trace(go.Scatter(
        x=df['Date'], y=df['Fair_Value'],
        name='Fair Value',
        line=dict(color='#e94560', width=2, dash='dash')
    ), row=1, col=1)
    
    # Spread
    fig2.add_trace(go.Scatter(
        x=df['Date'], y=df['Spread'],
        name='30Y-10Y Spread',
        line=dict(color='#ffd700', width=2),
        fill='tozeroy',
        fillcolor='rgba(255, 215, 0, 0.1)'
    ), row=2, col=1)
    
    fig2.add_hline(y=0, line_dash="solid", line_color="white", opacity=0.3, row=2, col=1)
    
    # Deviation
    colors = ['#00d26a' if x < 0 else '#e94560' for x in df['Deviation_Pct']]
    fig2.add_trace(go.Bar(
        x=df['Date'], y=df['Deviation_Pct'],
        name='Deviation',
        marker_color=colors,
        opacity=0.7
    ), row=3, col=1)
    
    fig2.add_hline(y=0, line_dash="solid", line_color="white", opacity=0.5, row=3, col=1)
    fig2.add_hline(y=2, line_dash="dash", line_color="#e94560", opacity=0.5, row=3, col=1)
    fig2.add_hline(y=-2, line_dash="dash", line_color="#00d26a", opacity=0.5, row=3, col=1)
    
    fig2.update_layout(
        template='plotly_dark',
        height=800,
        showlegend=True,
        hovermode='x unified'
    )
    
    fig2.update_yaxes(title_text=fx_pair_display, row=1, col=1)
    fig2.update_yaxes(title_text="Spread (%)", row=2, col=1)
    fig2.update_yaxes(title_text="Deviation (%)", row=3, col=1)
    
    st.plotly_chart(fig2, use_container_width=True)
    
    # =====================================================
    # MEAN REVERSION ANALYSIS
    # =====================================================
    st.markdown('<div class="section-header">⏱️ Mean Reversion Analysis</div>', unsafe_allow_html=True)
    
    threshold = st.select_slider(
        "Deviation Threshold (%)",
        options=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
        value=1.0
    )
    
    # Find reversion events
    events = []
    i = 0
    while i < len(df):
        if abs(df.iloc[i]['Deviation_Pct']) >= threshold:
            start_idx = i
            start_date = df.iloc[i]['Date']
            start_dev = df.iloc[i]['Deviation_Pct']
            direction = 'overvalued' if start_dev > 0 else 'undervalued'
            
            # Find return to threshold/2
            for j in range(i + 1, len(df)):
                if (start_dev > 0 and df.iloc[j]['Deviation_Pct'] <= threshold/2) or \
                   (start_dev < 0 and df.iloc[j]['Deviation_Pct'] >= -threshold/2):
                    days = j - i
                    events.append({
                        'Start': start_date,
                        'End': df.iloc[j]['Date'],
                        'Days': days,
                        'Direction': direction,
                        'Start_Dev': start_dev
                    })
                    i = j
                    break
            else:
                # Ongoing
                days_ongoing = len(df) - i
                events.append({
                    'Start': start_date,
                    'End': None,
                    'Days': None,
                    'Direction': direction,
                    'Start_Dev': start_dev,
                    'Ongoing': True
                })
                i = len(df)
        else:
            i += 1
    
    completed = [e for e in events if e.get('Days') is not None]
    
    if completed:
        days_list = [e['Days'] for e in completed]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Events", len(events))
        with col2:
            st.metric("Avg Days to Revert", f"{np.mean(days_list):.0f}")
        with col3:
            st.metric("Median Days", f"{np.median(days_list):.0f}")
        with col4:
            st.metric("Range", f"{min(days_list)} - {max(days_list)}")
        
        # Check current status
        if abs(current['Deviation_Pct']) >= threshold:
            ongoing = [e for e in events if e.get('Ongoing')]
            if ongoing:
                days_ongoing = (current['Date'] - ongoing[-1]['Start']).days
                st.warning(f"""
                    ⚠️ **Current deviation exceeds {threshold}%!**  
                    {fx_pair_display} has been {abs(current['Deviation_Pct']):.2f}% from fair value for **{days_ongoing} days**.  
                    Based on history, expect reversion in approximately **{np.median(days_list):.0f} days** (median).
                """)
        else:
            st.success(f"✅ {fx_pair_display} is within ±{threshold}% of fair value")
    else:
        st.info(f"No completed reversion events found at ±{threshold}% threshold")
    
    # =====================================================
    # EXPORT
    # =====================================================
    st.markdown('<div class="section-header">💾 Export Data</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = df.to_csv(index=False)
        st.download_button(
            "📥 Download Full Dataset (CSV)",
            data=csv_data,
            file_name=f"fx_yield_data_{fx_pair.replace('=X', '')}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col2:
        summary = {
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'FX_Pair': fx_pair_display,
            'Current_FX': current['FX'],
            'Current_10Y': current['Y10'],
            'Current_30Y': current['Y30'],
            'Current_Spread': current['Spread'],
            'Fair_Value': current['Fair_Value'],
            'Deviation_Pct': current['Deviation_Pct'],
            'Target_10Y': target_10y,
            'Target_30Y': target_30y,
            'Target_Spread': target_spread,
            'Forecast_FX': forecast_fx,
            'Forecast_Change_Pct': fx_change_pct,
            'Correlation': stats['correlation'],
            'R_Squared': stats['r_squared'],
            'Slope': stats['slope'],
            'Intercept': stats['intercept']
        }
        csv_summary = pd.DataFrame([summary]).to_csv(index=False)
        st.download_button(
            "📥 Download Forecast Summary (CSV)",
            data=csv_summary,
            file_name=f"fx_forecast_{fx_pair.replace('=X', '')}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

else:
    st.error("""
        ### ❌ Failed to load data
        
        Please check your internet connection and try again.
        
        **Data Sources:**
        - FRED: US Treasury yields (10Y, 30Y)
        - Yahoo Finance: FX rates
        
        Click **🔄 Refresh Data** in the sidebar to retry.
    """)

st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #808080; font-size: 0.85rem;">
        FX-Yield Spread Analyzer | Data: FRED, Yahoo Finance | Updated: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """
    </div>
""", unsafe_allow_html=True)
