import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import json

st.set_page_config(page_title="CME FedWatch Z-Score Tracker", layout="wide", page_icon="📊")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #ffc107;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📊 CME FedWatch Z-Score Tracker</div>', unsafe_allow_html=True)

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")

data_source = st.sidebar.radio(
    "Data Source",
    ["Manual Input", "CSV Upload", "API (Requires Key)"],
    help="Choose how to input FedWatch data"
)

# Initialize session state
if 'fed_data' not in st.session_state:
    st.session_state.fed_data = pd.DataFrame()

# Function to calculate z-scores
def calculate_zscore(data, column, window=20):
    """Calculate rolling z-score for a given column"""
    rolling_mean = data[column].rolling(window=window).mean()
    rolling_std = data[column].rolling(window=window).std()
    zscore = (data[column] - rolling_mean) / rolling_std
    return zscore

# Function to scrape FedWatch data (placeholder - actual implementation would need API)
def fetch_fedwatch_data():
    """
    Placeholder function for FedWatch data fetching
    Note: Real implementation requires CME API subscription
    """
    st.info("📌 Note: Direct scraping of FedWatch is complex. Using API or manual input is recommended.")
    return None

# Manual Input Section
if data_source == "Manual Input":
    st.sidebar.subheader("📝 Enter FedWatch Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        meeting_date = st.date_input("FOMC Meeting Date", datetime.now() + timedelta(days=30))
        reporting_date = st.date_input("Reporting Date", datetime.now())
    
    with col2:
        rate_range = st.text_input("Rate Range (e.g., 4.25-4.50)", "4.25-4.50")
        probability = st.number_input("Probability (%)", 0.0, 100.0, 50.0, 0.1)
    
    if st.sidebar.button("➕ Add Data Point"):
        new_data = pd.DataFrame({
            'meeting_date': [meeting_date],
            'reporting_date': [reporting_date],
            'rate_range': [rate_range],
            'probability': [probability],
            'timestamp': [datetime.now()]
        })
        
        if st.session_state.fed_data.empty:
            st.session_state.fed_data = new_data
        else:
            st.session_state.fed_data = pd.concat([st.session_state.fed_data, new_data], ignore_index=True)
        
        st.success("✅ Data point added!")

# CSV Upload Section
elif data_source == "CSV Upload":
    st.sidebar.subheader("📁 Upload CSV File")
    st.sidebar.markdown("""
    **Expected CSV format:**
    - meeting_date (YYYY-MM-DD)
    - reporting_date (YYYY-MM-DD)
    - rate_range (e.g., 4.25-4.50)
    - probability (0-100)
    """)
    
    uploaded_file = st.sidebar.file_uploader("Choose CSV file", type=['csv'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            df['meeting_date'] = pd.to_datetime(df['meeting_date'])
            df['reporting_date'] = pd.to_datetime(df['reporting_date'])
            st.session_state.fed_data = df
            st.success(f"✅ Loaded {len(df)} data points!")
        except Exception as e:
            st.error(f"❌ Error loading CSV: {e}")

# API Section
elif data_source == "API (Requires Key)":
    st.sidebar.subheader("🔑 API Configuration")
    
    api_key = st.sidebar.text_input("CME API Key", type="password", help="Enter your CME Group API key")
    api_endpoint = st.sidebar.text_input(
        "API Endpoint",
        "https://api.cmegroup.com/fedwatch/v1/forecasts",
        help="CME FedWatch API endpoint"
    )
    
    if st.sidebar.button("🔄 Fetch Data"):
        if not api_key:
            st.error("❌ Please enter your API key")
        else:
            try:
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                }
                
                response = requests.get(api_endpoint, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    # Process API response (structure depends on actual API)
                    st.success("✅ Data fetched successfully!")
                    st.json(data)  # Display raw data for inspection
                else:
                    st.error(f"❌ API Error: {response.status_code}")
                    st.error(f"Response: {response.text}")
            except Exception as e:
                st.error(f"❌ Error fetching data: {e}")

# Main dashboard area
if not st.session_state.fed_data.empty:
    df = st.session_state.fed_data.copy()
    
    # Convert dates if needed
    if 'meeting_date' in df.columns:
        df['meeting_date'] = pd.to_datetime(df['meeting_date'])
        df['reporting_date'] = pd.to_datetime(df['reporting_date'])
    
    # Sort by reporting date
    df = df.sort_values('reporting_date')
    
    # Analysis parameters
    st.sidebar.header("📈 Analysis Parameters")
    zscore_window = st.sidebar.slider("Z-Score Window", 5, 50, 20, help="Rolling window for z-score calculation")
    zscore_threshold = st.sidebar.slider("Z-Score Threshold", 1.0, 3.0, 2.0, 0.1, help="Threshold for extreme readings")
    
    # Calculate z-scores
    df['zscore'] = calculate_zscore(df, 'probability', window=zscore_window)
    df['zscore_abs'] = df['zscore'].abs()
    
    # Calculate moving averages
    df['prob_ma_5'] = df['probability'].rolling(window=5).mean()
    df['prob_ma_20'] = df['probability'].rolling(window=20).mean()
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Z-Score Analysis", "📉 Probability Trends", "📋 Data Table"])
    
    with tab1:
        st.subheader("Current Market Snapshot")
        
        col1, col2, col3, col4 = st.columns(4)
        
        latest_prob = df['probability'].iloc[-1]
        latest_zscore = df['zscore'].iloc[-1] if not pd.isna(df['zscore'].iloc[-1]) else 0
        avg_prob = df['probability'].mean()
        
        with col1:
            st.metric(
                "Latest Probability",
                f"{latest_prob:.1f}%",
                delta=f"{latest_prob - df['probability'].iloc[-2]:.1f}%" if len(df) > 1 else None
            )
        
        with col2:
            st.metric(
                "Current Z-Score",
                f"{latest_zscore:.2f}",
                delta="Extreme" if abs(latest_zscore) > zscore_threshold else "Normal",
                delta_color="inverse" if abs(latest_zscore) > zscore_threshold else "normal"
            )
        
        with col3:
            st.metric(
                "Average Probability",
                f"{avg_prob:.1f}%"
            )
        
        with col4:
            extreme_readings = len(df[df['zscore_abs'] > zscore_threshold])
            st.metric(
                "Extreme Readings",
                f"{extreme_readings}",
                delta=f"{(extreme_readings/len(df)*100):.1f}% of data"
            )
        
        # Quick chart
        st.subheader("Probability Over Time")
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['reporting_date'],
            y=df['probability'],
            mode='lines+markers',
            name='Probability',
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            title="Rate Probability Timeline",
            xaxis_title="Reporting Date",
            yaxis_title="Probability (%)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Z-Score Analysis")
        
        # Create subplot figure
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Probability with Moving Averages', 'Z-Score'),
            vertical_spacing=0.12,
            row_heights=[0.5, 0.5]
        )
        
        # Top plot - Probability
        fig.add_trace(
            go.Scatter(
                x=df['reporting_date'],
                y=df['probability'],
                mode='lines+markers',
                name='Probability',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6)
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df['reporting_date'],
                y=df['prob_ma_5'],
                mode='lines',
                name='MA(5)',
                line=dict(color='orange', width=1, dash='dash')
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df['reporting_date'],
                y=df['prob_ma_20'],
                mode='lines',
                name='MA(20)',
                line=dict(color='red', width=1, dash='dot')
            ),
            row=1, col=1
        )
        
        # Bottom plot - Z-Score
        colors = ['red' if abs(z) > zscore_threshold else 'gray' for z in df['zscore']]
        
        fig.add_trace(
            go.Bar(
                x=df['reporting_date'],
                y=df['zscore'],
                name='Z-Score',
                marker=dict(color=colors)
            ),
            row=2, col=1
        )
        
        # Add threshold lines
        fig.add_hline(y=zscore_threshold, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=-zscore_threshold, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="black", row=2, col=1)
        
        fig.update_xaxes(title_text="Reporting Date", row=2, col=1)
        fig.update_yaxes(title_text="Probability (%)", row=1, col=1)
        fig.update_yaxes(title_text="Z-Score", row=2, col=1)
        
        fig.update_layout(
            height=700,
            showlegend=True,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Z-Score distribution
        st.subheader("Z-Score Distribution")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Histogram(
                x=df['zscore'].dropna(),
                nbinsx=30,
                name='Z-Score',
                marker=dict(color='#1f77b4', line=dict(color='white', width=1))
            ))
            
            fig_hist.add_vline(x=zscore_threshold, line_dash="dash", line_color="red", annotation_text="Threshold")
            fig_hist.add_vline(x=-zscore_threshold, line_dash="dash", line_color="red")
            
            fig_hist.update_layout(
                title="Z-Score Distribution",
                xaxis_title="Z-Score",
                yaxis_title="Frequency",
                height=350
            )
            
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Extreme readings table
            extreme_df = df[df['zscore_abs'] > zscore_threshold][['reporting_date', 'probability', 'zscore', 'rate_range']]
            
            st.markdown("**🚨 Extreme Z-Score Readings**")
            if not extreme_df.empty:
                st.dataframe(
                    extreme_df.sort_values('zscore_abs', ascending=False),
                    use_container_width=True,
                    height=300
                )
            else:
                st.info("No extreme readings found with current threshold")
    
    with tab3:
        st.subheader("Probability Trends by Rate Range")
        
        # Group by rate range
        if 'rate_range' in df.columns:
            fig_range = go.Figure()
            
            for rate_range in df['rate_range'].unique():
                mask = df['rate_range'] == rate_range
                fig_range.add_trace(go.Scatter(
                    x=df[mask]['reporting_date'],
                    y=df[mask]['probability'],
                    mode='lines+markers',
                    name=rate_range,
                    line=dict(width=2),
                    marker=dict(size=6)
                ))
            
            fig_range.update_layout(
                title="Probability by Rate Range Over Time",
                xaxis_title="Reporting Date",
                yaxis_title="Probability (%)",
                hovermode='x unified',
                height=500
            )
            
            st.plotly_chart(fig_range, use_container_width=True)
        
        # Change analysis
        st.subheader("Period-over-Period Changes")
        
        df['prob_change'] = df['probability'].diff()
        df['prob_pct_change'] = df['probability'].pct_change() * 100
        
        fig_change = go.Figure()
        
        fig_change.add_trace(go.Bar(
            x=df['reporting_date'],
            y=df['prob_change'],
            name='Absolute Change',
            marker=dict(
                color=df['prob_change'],
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="Change")
            )
        ))
        
        fig_change.update_layout(
            title="Probability Changes",
            xaxis_title="Reporting Date",
            yaxis_title="Change in Probability (%)",
            height=400
        )
        
        st.plotly_chart(fig_change, use_container_width=True)
    
    with tab4:
        st.subheader("📋 Complete Data Table")
        
        # Display options
        col1, col2 = st.columns([2, 1])
        
        with col1:
            show_columns = st.multiselect(
                "Select columns to display",
                df.columns.tolist(),
                default=['reporting_date', 'meeting_date', 'rate_range', 'probability', 'zscore']
            )
        
        with col2:
            download_format = st.selectbox("Download format", ["CSV", "Excel"])
        
        # Display filtered dataframe
        display_df = df[show_columns].copy()
        
        st.dataframe(
            display_df.sort_values('reporting_date', ascending=False),
            use_container_width=True,
            height=400
        )
        
        # Download button
        if download_format == "CSV":
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"fedwatch_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            # For Excel, need to use BytesIO
            from io import BytesIO
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                display_df.to_excel(writer, index=False, sheet_name='FedWatch Data')
            
            st.download_button(
                label="📥 Download Excel",
                data=buffer.getvalue(),
                file_name=f"fedwatch_data_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # Sidebar statistics
    st.sidebar.header("📊 Statistics")
    st.sidebar.metric("Total Data Points", len(df))
    st.sidebar.metric("Date Range", f"{df['reporting_date'].min().strftime('%Y-%m-%d')} to {df['reporting_date'].max().strftime('%Y-%m-%d')}")
    st.sidebar.metric("Avg Z-Score", f"{df['zscore'].mean():.2f}" if not df['zscore'].isna().all() else "N/A")
    st.sidebar.metric("Max Z-Score", f"{df['zscore'].max():.2f}" if not df['zscore'].isna().all() else "N/A")
    st.sidebar.metric("Min Z-Score", f"{df['zscore'].min():.2f}" if not df['zscore'].isna().all() else "N/A")

else:
    st.info("👆 Please add data using the sidebar options to begin analysis")
    
    # Show example data format
    st.markdown("### 📝 Example Data Format")
    
    example_df = pd.DataFrame({
        'meeting_date': [datetime.now() + timedelta(days=30)]*5,
        'reporting_date': [datetime.now() - timedelta(days=i) for i in range(5)],
        'rate_range': ['4.25-4.50']*5,
        'probability': [45.2, 47.8, 51.3, 48.9, 50.1]
    })
    
    st.dataframe(example_df)
    
    st.markdown("""
    ### 🔍 How to Use This Dashboard
    
    1. **Data Input**: Choose your preferred method in the sidebar:
       - **Manual Input**: Enter data points one by one
       - **CSV Upload**: Upload a prepared CSV file
       - **API**: Connect with your CME API key (requires subscription)
    
    2. **Analysis**: Once data is loaded, explore:
       - **Overview**: Current snapshot and timeline
       - **Z-Score Analysis**: Statistical deviation from mean
       - **Probability Trends**: Track changes over time
       - **Data Table**: View and download complete dataset
    
    3. **Interpretation**:
       - **Z-Score > 2**: Unusually high probability (potential overpricing)
       - **Z-Score < -2**: Unusually low probability (potential underpricing)
       - **Z-Score ≈ 0**: Probability near historical average
    
    ### 📌 Note on CME FedWatch API
    
    Direct API access requires a CME Group subscription ($25/month minimum). 
    Visit [CME Market Data APIs](https://www.cmegroup.com/market-data/market-data-api.html) to subscribe.
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>📊 CME FedWatch Z-Score Tracker | Data visualization for FOMC rate probability analysis</p>
    <p><small>Disclaimer: This tool is for informational purposes only. Not investment advice.</small></p>
</div>
""", unsafe_allow_html=True)
