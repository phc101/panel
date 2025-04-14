import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page configuration with custom theme
st.set_page_config(
    page_title="Strategic FX Hedge Planner",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .subheader {
        font-size: 1.5rem;
        color: #1E3A8A;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #E5E7EB;
        padding-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #F3F4F6;
        border-radius: 0.5rem;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #1E3A8A;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #4B5563;
    }
    .sidebar-header {
        font-size: 1.2rem;
        font-weight: bold;
        color: #1E3A8A;
        margin-top: 1rem;
    }
    .stButton>button {
        background-color: #1E3A8A;
        color: white;
        width: 100%;
    }
    .warning {
        color: #DC2626;
        font-weight: bold;
    }
    .success {
        color: #10B981;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Page header
st.markdown('<p class="main-header">💱 Strategic FX Hedge Planner</p>', unsafe_allow_html=True)

# Create two columns for the intro section
intro_col1, intro_col2 = st.columns([2, 1])

with intro_col1:
    st.markdown("""
    Plan and optimize your foreign exchange hedging strategy with this interactive tool.
    Monitor your hedge portfolio performance, visualize rates across different maturities,
    and achieve your target weighted average hedge rate.
    """)

with intro_col2:
    st.markdown("""
    **Instructions:**
    1. Set your parameters in the sidebar
    2. Upload existing hedges (optional)
    3. Review the generated hedge plan
    4. Download your complete strategy
    """)

# --- Sidebar Inputs with improved organization ---
st.sidebar.markdown('<p class="sidebar-header">📊 Market Parameters</p>', unsafe_allow_html=True)

spot_rate = st.sidebar.number_input("Current Spot Rate (EUR/PLN)", 
                                    value=4.30, 
                                    step=0.0001,
                                    format="%.4f",
                                    help="The current exchange rate between EUR and PLN")

st.sidebar.markdown('<p class="sidebar-header">🎯 Strategy Settings</p>', unsafe_allow_html=True)

target_rate = st.sidebar.number_input("Target Weighted Avg Hedge Rate", 
                                      value=4.40, 
                                      step=0.0001,
                                      format="%.4f",
                                      help="Your desired weighted average hedge rate")

hedge_months = st.sidebar.slider("Hedging Horizon (Months)", 
                               min_value=1, 
                               max_value=24, 
                               value=6,
                               help="Number of months to plan your hedges for")

monthly_volume = st.sidebar.number_input("Monthly Hedge Volume (EUR)", 
                                         value=100_000, 
                                         step=10_000,
                                         format="%d",
                                         help="Amount in EUR to hedge each month")

st.sidebar.markdown('<p class="sidebar-header">📈 Forward Points</p>', unsafe_allow_html=True)

# More organized forward points input with collapsible section
with st.sidebar.expander("Forward Points (vs Spot, %)", expanded=False):
    forward_points_input = {}
    for m in range(1, hedge_months + 1):
        default_value = 0.01 * m  # Example progressive forward points
        forward_points_input[m] = st.number_input(
            f"{m}M Forward",
            value=default_value,
            step=0.0001,
            format="%.4f",
            key=f"fwd_pt_{m}"
        )

# --- Existing Hedges Section ---
st.markdown('<p class="subheader">📂 Existing Hedges (Optional)</p>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload CSV with columns: Maturity Date, Volume (EUR), Rate", 
                                type=["csv"],
                                help="Format: CSV with columns 'Maturity Date', 'Volume (EUR)', 'Rate'")

# Sample data option
show_sample = st.checkbox("Use sample data instead", value=False)

if uploaded_file:
    try:
        existing_hedges = pd.read_csv(uploaded_file, parse_dates=["Maturity Date"])
        st.success("✅ File successfully uploaded!")
    except Exception as e:
        st.error(f"Error loading file: {str(e)}. Please check the format.")
        existing_hedges = pd.DataFrame(columns=["Maturity Date", "Volume (EUR)", "Rate"])
elif show_sample:
    # Sample data for demonstration
    today = pd.Timestamp.today()
    sample_data = [
        {"Maturity Date": (today + pd.DateOffset(months=1)).replace(day=15), "Volume (EUR)": 50000, "Rate": 4.32},
        {"Maturity Date": (today + pd.DateOffset(months=2)).replace(day=15), "Volume (EUR)": 75000, "Rate": 4.33},
    ]
    existing_hedges = pd.DataFrame(sample_data)
    st.info("Using sample data for demonstration purposes.")
else:
    existing_hedges = pd.DataFrame(columns=["Maturity Date", "Volume (EUR)", "Rate"])

# Display existing hedges if available
if not existing_hedges.empty:
    st.markdown("### Current Hedge Portfolio")
    
    # Format the dataframe for display
    display_df = existing_hedges.copy()
    if 'Maturity Date' in display_df.columns:
        display_df['Maturity Date'] = display_df['Maturity Date'].dt.strftime('%Y-%m-%d')
    if 'Volume (EUR)' in display_df.columns:
        display_df['Volume (EUR)'] = display_df['Volume (EUR)'].apply(lambda x: f"{x:,.0f}")
    if 'Rate' in display_df.columns:
        display_df['Rate'] = display_df['Rate'].apply(lambda x: f"{x:.4f}")
    
    st.dataframe(display_df, use_container_width=True)

# --- New Hedges Calculation ---
today = pd.Timestamp.today()
new_hedges = []

for m in range(1, hedge_months + 1):
    maturity_date = (today + pd.DateOffset(months=m)).replace(day=10)
    fwd_multiplier = 1 + forward_points_input[m]
    forward_rate = spot_rate * fwd_multiplier
    new_hedges.append({
        "Maturity Date": maturity_date,
        "Volume (EUR)": monthly_volume,
        "Rate": forward_rate,
        "Type": "New Hedge"
    })

new_hedges_df = pd.DataFrame(new_hedges)

# Combine existing and new
if not existing_hedges.empty:
    existing_hedges["Type"] = "Existing Hedge"
    combined_df = pd.concat([existing_hedges, new_hedges_df], ignore_index=True)
else:
    combined_df = new_hedges_df

# --- Weighted Avg Calculation ---
total_volume = combined_df["Volume (EUR)"].sum()
weighted_avg = (combined_df["Volume (EUR)"] * combined_df["Rate"]).sum() / total_volume if total_volume else 0.0

# --- Dashboard Metrics ---
st.markdown('<p class="subheader">🔍 Portfolio Metrics</p>', unsafe_allow_html=True)

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    st.markdown('<div class="metric-card">'
                f'<div class="metric-value">{weighted_avg:.4f}</div>'
                '<div class="metric-label">Weighted Avg Rate</div>'
                '</div>', unsafe_allow_html=True)

with metric_col2:
    rate_diff = weighted_avg - target_rate
    color_class = "warning" if rate_diff < 0 else "success"
    st.markdown(f'<div class="metric-card">'
                f'<div class="metric-value {color_class}">{rate_diff:.4f}</div>'
                f'<div class="metric-label">vs Target ({target_rate:.4f})</div>'
                f'</div>', unsafe_allow_html=True)

with metric_col3:
    st.markdown('<div class="metric-card">'
                f'<div class="metric-value">{total_volume:,.0f}</div>'
                '<div class="metric-label">Total Volume (EUR)</div>'
                '</div>', unsafe_allow_html=True)

with metric_col4:
    hedge_period = (combined_df["Maturity Date"].max() - today).days
    st.markdown('<div class="metric-card">'
                f'<div class="metric-value">{hedge_period}</div>'
                '<div class="metric-label">Hedge Horizon (Days)</div>'
                '</div>', unsafe_allow_html=True)

# --- Hedge Portfolio Visualization ---
st.markdown('<p class="subheader">📈 Hedge Portfolio Visualization</p>', unsafe_allow_html=True)

# Modern Plotly chart 
fig = go.Figure()

# Add traces for each type of hedge
for hedge_type, data in combined_df.groupby("Type"):
    fig.add_trace(go.Scatter(
        x=data["Maturity Date"],
        y=data["Rate"],
        mode='markers+lines',
        name=hedge_type,
        marker=dict(
            size=data["Volume (EUR)"] / 10000, 
            sizemode='area',
            sizeref=2.*max(combined_df["Volume (EUR)"])/(40.**2),
            sizemin=5,
        ),
        hovertemplate='<b>Date:</b> %{x|%Y-%m-%d}<br>' +
                      '<b>Rate:</b> %{y:.4f}<br>' +
                      '<b>Volume:</b> %{text:,.0f} EUR<extra></extra>',
        text=data["Volume (EUR)"]
    ))

# Add target and weighted average lines
fig.add_trace(go.Scatter(
    x=[combined_df["Maturity Date"].min(), combined_df["Maturity Date"].max()],
    y=[weighted_avg, weighted_avg],
    mode='lines',
    name=f'Weighted Avg: {weighted_avg:.4f}',
    line=dict(color='red', width=2, dash='dash'),
))

fig.add_trace(go.Scatter(
    x=[combined_df["Maturity Date"].min(), combined_df["Maturity Date"].max()],
    y=[target_rate, target_rate],
    mode='lines',
    name=f'Target: {target_rate:.4f}',
    line=dict(color='green', width=2, dash='dash'),
))

# Update layout
fig.update_layout(
    title='EUR/PLN Hedge Portfolio',
    xaxis_title='Maturity Date',
    yaxis_title='Rate',
    legend_title='Hedge Type',
    hovermode='closest',
    template='plotly_white',
    height=500,
    xaxis=dict(
        tickformat='%b %d, %Y',
        tickangle=-45,
    ),
    yaxis=dict(
        tickformat='.4f',
    ),
)

st.plotly_chart(fig, use_container_width=True)

# --- Hedge Plan Table ---
st.markdown('<p class="subheader">📋 Complete Hedge Plan</p>', unsafe_allow_html=True)

# Prepare display dataframe with formatting
display_combined_df = combined_df.copy()
display_combined_df['Maturity Date'] = display_combined_df['Maturity Date'].dt.strftime('%Y-%m-%d')
display_combined_df['Volume (EUR)'] = display_combined_df['Volume (EUR)'].apply(lambda x: f"{x:,.0f}")
display_combined_df['Rate'] = display_combined_df['Rate'].apply(lambda x: f"{x:.4f}")

# Sort by maturity date
display_combined_df = display_combined_df.sort_values('Maturity Date')

# Display the hedge plan table
st.dataframe(display_combined_df, use_container_width=True)

# --- Monthly Results Analysis ---
st.markdown('<p class="subheader">📊 Monthly Analysis</p>', unsafe_allow_html=True)

# Extract month from maturity date for analysis
combined_df['Month'] = combined_df['Maturity Date'].dt.strftime('%Y-%m')

# Aggregated monthly data
monthly_analysis = combined_df.groupby('Month').agg(
    Volume=('Volume (EUR)', 'sum'),
    Weighted_Rate=lambda x: (combined_df.loc[x.index, 'Volume (EUR)'] * combined_df.loc[x.index, 'Rate']).sum() / combined_df.loc[x.index, 'Volume (EUR)'].sum()
).reset_index()

col1, col2 = st.columns([3, 2])

with col1:
    # Monthly volumes chart
    volume_fig = px.bar(
        monthly_analysis, 
        x='Month', 
        y='Volume',
        title='Monthly Hedge Volumes',
        labels={'Volume': 'Volume (EUR)', 'Month': 'Month'},
        text_auto='.2s',
        color='Volume',
        color_continuous_scale='Blues',
    )
    volume_fig.update_layout(height=400)
    st.plotly_chart(volume_fig, use_container_width=True)

with col2:
    # Monthly weighted rates
    rate_fig = px.line(
        monthly_analysis, 
        x='Month', 
        y='Weighted_Rate',
        title='Monthly Weighted Rates',
        labels={'Weighted_Rate': 'Weighted Rate', 'Month': 'Month'},
        markers=True,
    )
    rate_fig.add_hline(
        y=target_rate, 
        line_dash="dash", 
        line_color="green",
        annotation_text=f"Target: {target_rate:.4f}"
    )
    rate_fig.update_layout(height=400)
    rate_fig.update_traces(line=dict(width=3))
    st.plotly_chart(rate_fig, use_container_width=True)

# --- Download Section ---
st.markdown('<p class="subheader">📤 Export Options</p>', unsafe_allow_html=True)

download_col1, download_col2 = st.columns(2)

with download_col1:
    # Prepare the CSV for download - use original data not the display version
    download_df = combined_df.copy()
    download_df['Maturity Date'] = download_df['Maturity Date'].dt.strftime('%Y-%m-%d')
    
    st.download_button(
        "📥 Download Complete Hedge Plan (CSV)",
        data=download_df.to_csv(index=False),
        file_name=f"hedge_plan_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

with download_col2:
    # Generate an Excel report with multiple tabs
    try:
        import io
        from io import BytesIO
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write each dataframe to a different worksheet
            download_df.to_excel(writer, sheet_name='Complete Hedge Plan', index=False)
            monthly_analysis.to_excel(writer, sheet_name='Monthly Analysis', index=False)
            
            # Get the xlsx data
            writer.close()
            processed_data = output.getvalue()
            
        st.download_button(
            label="📊 Download Detailed Excel Report",
            data=processed_data,
            file_name=f"hedge_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.ms-excel"
        )
    except:
        st.warning("Excel export requires additional libraries. CSV download is always available.")

# Footer
st.markdown("""
---
*Strategic FX Hedge Planner - A treasury management tool for optimizing foreign exchange hedging strategies.*
""")
