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
        font-weight: 700;
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(135deg, #0051a5 0%, #003366 100%);
        color: white;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0, 51, 102, 0.3);
    }
    .metric-card {
        background: linear-gradient(145deg, #f8f9fa 0%, #ffffff 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #0051a5;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
    }
    .correlation-box {
        background: linear-gradient(145deg, #e8f4f8 0%, #f0f8ff 100%);
        padding: 1.2rem;
        border-radius: 10px;
        text-align: center;
        font-size: 1.3rem;
        border: 2px solid #0051a5;
        margin: 0.5rem 0;
    }
    .reversion-card {
        background: linear-gradient(145deg, #fff8e1 0%, #fffde7 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #ff9800;
        box-shadow: 0 2px 8px rgba(255, 152, 0, 0.15);
        margin-bottom: 1rem;
    }
    .reversion-stat {
        background: linear-gradient(145deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 0.3rem;
        border: 1px solid #1976d2;
    }
    .reversion-stat-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1565c0;
    }
    .reversion-stat-label {
        font-size: 0.85rem;
        color: #424242;
        margin-top: 0.3rem;
    }
    .stDownloadButton>button {
        background: linear-gradient(135deg, #0051a5 0%, #003366 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stDownloadButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 51, 102, 0.4);
    }
    .footer {
        text-align: center;
        padding: 1.5rem;
        color: #666;
        font-size: 0.9rem;
        border-top: 1px solid #e0e0e0;
        margin-top: 2rem;
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
    
    if 'Price' in df.columns:
        df = df.rename(columns={'Price': 'Close'})
    
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


def analyze_mean_reversion(df, threshold_pct=1.0):
    """
    Analyze mean reversion - how many days to return to FV after deviation exceeds threshold.
    
    Returns:
    - reversion_events: list of dicts with details of each event
    - stats: summary statistics
    """
    df = df.copy().reset_index(drop=True)
    reversion_events = []
    
    i = 0
    while i < len(df):
        # Check if deviation exceeds threshold
        if abs(df.loc[i, 'Deviation_Pct']) >= threshold_pct:
            event_start = i
            start_date = df.loc[i, 'Date']
            start_deviation = df.loc[i, 'Deviation_Pct']
            start_fx = df.loc[i, 'FX_Rate']
            start_fv = df.loc[i, 'Fair_Value']
            direction = 'overvalued' if start_deviation > 0 else 'undervalued'
            
            # Find return to FV (deviation < threshold/2 or sign change)
            days_to_reversion = None
            end_date = None
            end_fx = None
            peak_deviation = start_deviation
            
            for j in range(i + 1, len(df)):
                current_dev = df.loc[j, 'Deviation_Pct']
                
                # Track peak deviation during event
                if abs(current_dev) > abs(peak_deviation):
                    peak_deviation = current_dev
                
                # Check if reverted (crossed zero or below threshold/2)
                if (start_deviation > 0 and current_dev <= threshold_pct / 2) or \
                   (start_deviation < 0 and current_dev >= -threshold_pct / 2):
                    days_to_reversion = j - i
                    end_date = df.loc[j, 'Date']
                    end_fx = df.loc[j, 'FX_Rate']
                    i = j  # Move to end of this event
                    break
            else:
                # Never reverted (ongoing)
                days_to_reversion = None
                end_date = None
                end_fx = None
                i = len(df)  # Exit loop
            
            reversion_events.append({
                'start_date': start_date,
                'end_date': end_date,
                'start_deviation_pct': start_deviation,
                'peak_deviation_pct': peak_deviation,
                'direction': direction,
                'days_to_reversion': days_to_reversion,
                'start_fx': start_fx,
                'end_fx': end_fx,
                'start_fv': start_fv,
                'reverted': days_to_reversion is not None
            })
        else:
            i += 1
    
    # Calculate statistics
    completed_events = [e for e in reversion_events if e['reverted']]
    
    if completed_events:
        days_list = [e['days_to_reversion'] for e in completed_events]
        stats = {
            'total_events': len(reversion_events),
            'completed_events': len(completed_events),
            'ongoing_events': len(reversion_events) - len(completed_events),
            'mean_days': np.mean(days_list),
            'median_days': np.median(days_list),
            'min_days': np.min(days_list),
            'max_days': np.max(days_list),
            'std_days': np.std(days_list),
            'overvalued_events': len([e for e in completed_events if e['direction'] == 'overvalued']),
            'undervalued_events': len([e for e in completed_events if e['direction'] == 'undervalued']),
            'avg_overvalued_days': np.mean([e['days_to_reversion'] for e in completed_events if e['direction'] == 'overvalued']) if [e for e in completed_events if e['direction'] == 'overvalued'] else None,
            'avg_undervalued_days': np.mean([e['days_to_reversion'] for e in completed_events if e['direction'] == 'undervalued']) if [e for e in completed_events if e['direction'] == 'undervalued'] else None,
        }
    else:
        stats = {
            'total_events': len(reversion_events),
            'completed_events': 0,
            'ongoing_events': len(reversion_events),
            'mean_days': None,
            'median_days': None,
            'min_days': None,
            'max_days': None,
            'std_days': None,
            'overvalued_events': 0,
            'undervalued_events': 0,
            'avg_overvalued_days': None,
            'avg_undervalued_days': None,
        }
    
    return reversion_events, stats


def create_reversion_chart(df, events, pair_name, threshold):
    """Create chart showing reversion events"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(f'{pair_name}: Deviation with Reversion Events', 'Days to Reversion Distribution'),
        vertical_spacing=0.15,
        row_heights=[0.65, 0.35]
    )
    
    # Deviation line
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Deviation_Pct'],
        name='Deviation %',
        line=dict(color='#1565c0', width=2),
        fill='tozeroy',
        fillcolor='rgba(21, 101, 192, 0.1)'
    ), row=1, col=1)
    
    # Threshold lines
    fig.add_hline(y=threshold, line_dash="dash", line_color="red", 
                  annotation_text=f"+{threshold}%", row=1, col=1)
    fig.add_hline(y=-threshold, line_dash="dash", line_color="green", 
                  annotation_text=f"-{threshold}%", row=1, col=1)
    fig.add_hline(y=0, line_dash="solid", line_color="black", opacity=0.5, row=1, col=1)
    
    # Mark reversion events
    colors = {'overvalued': 'rgba(244, 67, 54, 0.3)', 'undervalued': 'rgba(76, 175, 80, 0.3)'}
    
    for event in events:
        if event['end_date'] is not None:
            fig.add_vrect(
                x0=event['start_date'],
                x1=event['end_date'],
                fillcolor=colors[event['direction']],
                layer="below",
                line_width=0,
                row=1, col=1
            )
    
    # Histogram of days to reversion
    completed_events = [e for e in events if e['reverted']]
    if completed_events:
        days_data = [e['days_to_reversion'] for e in completed_events]
        
        fig.add_trace(go.Histogram(
            x=days_data,
            name='Days to Reversion',
            marker_color='#ff9800',
            opacity=0.75,
            nbinsx=min(20, max(5, len(days_data) // 3))
        ), row=2, col=1)
        
        # Add mean line
        mean_days = np.mean(days_data)
        fig.add_vline(x=mean_days, line_dash="dash", line_color="red",
                      annotation_text=f"Mean: {mean_days:.0f} days", row=2, col=1)
    
    fig.update_xaxes(title_text="Date", row=1, col=1)
    fig.update_xaxes(title_text="Days to Reversion", row=2, col=1)
    fig.update_yaxes(title_text="Deviation (%)", row=1, col=1)
    fig.update_yaxes(title_text="Frequency", row=2, col=1)
    
    fig.update_layout(
        height=700,
        showlegend=True,
        hovermode='x unified',
        title_text=f'{pair_name} Mean Reversion Analysis | Threshold: ±{threshold}%'
    )
    
    return fig


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
                    <div class="correlation-box">
                        <strong>{name}</strong><br>
                        Correlation: {data['corr']:+.3f}<br>
                        <small>{corr_strength}</small>
                    </div>
                """, unsafe_allow_html=True)
        
        # =====================================================
        # MEAN REVERSION ANALYSIS SECTION
        # =====================================================
        st.markdown("## ⏱️ Mean Reversion Analysis")
        st.markdown("""
        <div class="reversion-card">
            <strong>📈 O co chodzi?</strong><br>
            Analiza mean reversion pokazuje ile dni historycznie zajmuje powrót kursu FX do fair value 
            po odchyleniu przekraczającym zadany próg. Pomaga to w prognozowaniu czasu trwania obecnych odchyleń.
        </div>
        """, unsafe_allow_html=True)
        
        # Threshold selector
        col1, col2 = st.columns([1, 3])
        with col1:
            reversion_threshold = st.selectbox(
                "Próg odchylenia (%)",
                options=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
                index=1,
                help="Minimalne odchylenie od FV, które rozpoczyna zdarzenie mean reversion"
            )
        
        # Analyze each pair
        for name, data in pairs.items():
            st.markdown(f"### {name}")
            
            events, stats = analyze_mean_reversion(data['df'], threshold_pct=reversion_threshold)
            
            if stats['total_events'] > 0:
                # Summary statistics
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.markdown(f"""
                        <div class="reversion-stat">
                            <div class="reversion-stat-value">{stats['total_events']}</div>
                            <div class="reversion-stat-label">Wszystkich zdarzeń</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if stats['mean_days'] is not None:
                        st.markdown(f"""
                            <div class="reversion-stat">
                                <div class="reversion-stat-value">{stats['mean_days']:.0f}</div>
                                <div class="reversion-stat-label">Średnia dni do powrotu</div>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                            <div class="reversion-stat">
                                <div class="reversion-stat-value">-</div>
                                <div class="reversion-stat-label">Średnia dni do powrotu</div>
                            </div>
                        """, unsafe_allow_html=True)
                
                with col3:
                    if stats['median_days'] is not None:
                        st.markdown(f"""
                            <div class="reversion-stat">
                                <div class="reversion-stat-value">{stats['median_days']:.0f}</div>
                                <div class="reversion-stat-label">Mediana dni</div>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                            <div class="reversion-stat">
                                <div class="reversion-stat-value">-</div>
                                <div class="reversion-stat-label">Mediana dni</div>
                            </div>
                        """, unsafe_allow_html=True)
                
                with col4:
                    if stats['min_days'] is not None:
                        st.markdown(f"""
                            <div class="reversion-stat">
                                <div class="reversion-stat-value">{stats['min_days']:.0f} - {stats['max_days']:.0f}</div>
                                <div class="reversion-stat-label">Zakres (min-max)</div>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                            <div class="reversion-stat">
                                <div class="reversion-stat-value">-</div>
                                <div class="reversion-stat-label">Zakres (min-max)</div>
                            </div>
                        """, unsafe_allow_html=True)
                
                with col5:
                    st.markdown(f"""
                        <div class="reversion-stat">
                            <div class="reversion-stat-value">{stats['ongoing_events']}</div>
                            <div class="reversion-stat-label">Trwające odchylenia</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                # Direction breakdown
                if stats['completed_events'] > 0:
                    st.markdown("#### Breakdown by direction")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if stats['avg_overvalued_days'] is not None:
                            st.markdown(f"""
                                🔴 **Overvalued (PLN słabszy od FV)**
                                - Zdarzeń: {stats['overvalued_events']}
                                - Średni czas powrotu: **{stats['avg_overvalued_days']:.0f} dni**
                            """)
                        else:
                            st.markdown("🔴 **Overvalued**: Brak zdarzeń")
                    
                    with col2:
                        if stats['avg_undervalued_days'] is not None:
                            st.markdown(f"""
                                🟢 **Undervalued (PLN mocniejszy od FV)**
                                - Zdarzeń: {stats['undervalued_events']}
                                - Średni czas powrotu: **{stats['avg_undervalued_days']:.0f} dni**
                            """)
                        else:
                            st.markdown("🟢 **Undervalued**: Brak zdarzeń")
                
                # Current status
                current_dev = data['df'].iloc[-1]['Deviation_Pct']
                if abs(current_dev) >= reversion_threshold:
                    ongoing = [e for e in events if not e['reverted']]
                    if ongoing:
                        latest = ongoing[-1]
                        days_ongoing = (data['df'].iloc[-1]['Date'] - latest['start_date']).days
                        
                        direction_text = "powyżej" if current_dev > 0 else "poniżej"
                        
                        st.warning(f"""
                            ⚠️ **Aktualnie trwa odchylenie!**
                            
                            Kurs {name} jest {abs(current_dev):.2f}% {direction_text} fair value od **{days_ongoing} dni** 
                            (start: {latest['start_date'].strftime('%Y-%m-%d')}).
                            
                            Na podstawie historii, oczekiwany czas do powrotu: **{stats['median_days']:.0f} dni** (mediana)
                            lub **{stats['mean_days']:.0f} dni** (średnia).
                        """)
                else:
                    st.success(f"✅ Kurs {name} jest obecnie w granicach ±{reversion_threshold}% od fair value")
                
                # Chart
                fig = create_reversion_chart(data['df'], events, name, reversion_threshold)
                st.plotly_chart(fig, use_container_width=True)
                
                # Events table
                with st.expander(f"📋 Lista zdarzeń mean reversion ({name})"):
                    events_df = pd.DataFrame(events)
                    events_df['start_date'] = pd.to_datetime(events_df['start_date']).dt.strftime('%Y-%m-%d')
                    events_df['end_date'] = events_df['end_date'].apply(
                        lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else 'Ongoing'
                    )
                    events_df = events_df.rename(columns={
                        'start_date': 'Start',
                        'end_date': 'End',
                        'start_deviation_pct': 'Start Dev %',
                        'peak_deviation_pct': 'Peak Dev %',
                        'direction': 'Direction',
                        'days_to_reversion': 'Days',
                        'reverted': 'Completed'
                    })
                    st.dataframe(
                        events_df[['Start', 'End', 'Start Dev %', 'Peak Dev %', 'Direction', 'Days', 'Completed']],
                        use_container_width=True
                    )
            else:
                st.info(f"Brak zdarzeń przekraczających próg ±{reversion_threshold}% dla {name}")
        
        st.markdown("---")
        
        # =====================================================
        # SCENARIO ANALYSIS (original)
        # =====================================================
        st.markdown("## 🎯 Prognosis Scenario")
        
        current = list(pairs.values())[0]['df'].iloc[-1]
        
        col1, col2 = st.columns(2)
        
        with col1:
            scenario = st.selectbox(
                "Scenario",
                ["Custom", "Steepening (+20%)", "Steepening (+50%)", "Flattening (-20%)", "Flattening (-50%)", "Current"]
            )
            
            if scenario == "Custom":
                target_10y = st.number_input("Target 10Y (%)", value=float(current['10Y']), min_value=0.0, max_value=10.0, step=0.1)
                target_30y = st.number_input("Target 30Y (%)", value=float(current['30Y']), min_value=0.0, max_value=10.0, step=0.1)
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
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
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
                name='Actual',
                line=dict(color='#0051a5', width=2.5)
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Fair_Value'],
                name='Fair Value',
                line=dict(color='#ff7f0e', width=2, dash='dash')
            ), row=1, col=1)
            
            # Deviation
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Deviation_Pct'],
                name='Deviation',
                fill='tozeroy',
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
            
            # Get reversion stats
            _, stats = analyze_mean_reversion(data['df'], threshold_pct=reversion_threshold)
            
            export_data[f'{name}_Current'] = current_rate
            export_data[f'{name}_Target'] = target_rate
            export_data[f'{name}_Change_%'] = change_pct
            export_data[f'{name}_Correlation'] = data['corr']
            export_data[f'{name}_Reversion_Threshold_%'] = reversion_threshold
            export_data[f'{name}_Mean_Days_to_Reversion'] = stats['mean_days']
            export_data[f'{name}_Median_Days_to_Reversion'] = stats['median_days']
        
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
    - **NEW:** Analyzes mean reversion time after deviations from fair value
    
    **Data Sources:**
    - FRED: https://fred.stlouisfed.org
    - Investing.com: Historical FX data
    """)

st.markdown("---")
st.markdown('<div class="footer">FX Spread Prognosis Tool | Mean Reversion Analysis</div>', unsafe_allow_html=True)
