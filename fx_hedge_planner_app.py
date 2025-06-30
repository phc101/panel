import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# FRED API Configuration
FRED_API_KEY = "50813725c0bfaadbc44a16ef28b0e894"  # You can use "demo" or get free API key from https://fred.stlouisfed.org/docs/api/api_key.html

# FRED Series IDs for bonds and rates
FRED_SERIES = {
    # Government Bond Yields (10-Year)
    'US_10Y': 'DGS10',                    # US 10-Year Treasury
    'DE_10Y': 'IRLTLT01DEM156N',          # Germany 10-Year Government Bond
    'PL_10Y': 'IRLTLT01PLM156N',          # Poland 10-Year Government Bond
    'EU_10Y': 'IRLTLT01EZM156N',          # Euro Area 10-Year Government Bond
    
    # Short-term rates (2-Year approximation)
    'US_2Y': 'DGS2',                      # US 2-Year Treasury
    'DE_2Y': 'IRLTLT01DEM156N',           # Germany (using 10Y, will adjust)
    
    # Interest Rate Benchmarks
    'EURIBOR_3M': 'EUR3MTD156N',          # 3-Month EURIBOR
    'FED_FUNDS': 'FEDFUNDS',              # Federal Funds Rate
    'ECB_RATE': 'IRSTCB01EZM156N',        # ECB Main Refinancing Rate
    
    # Exchange Rates
    'EUR_USD': 'DEXUSEU',                 # EUR/USD Exchange Rate
}

class FREDAPIClient:
    """FRED API client for fetching economic data"""
    
    def __init__(self, api_key=FRED_API_KEY):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred"
    
    def get_series_data(self, series_id, limit=1, sort_order='desc'):
        """Get latest data for a specific FRED series"""
        url = f"{self.base_url}/series/observations"
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json',
            'limit': limit,
            'sort_order': sort_order
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'observations' in data and data['observations']:
                latest = data['observations'][0]
                if latest['value'] != '.':  # FRED uses '.' for missing data
                    return {
                        'value': float(latest['value']),
                        'date': latest['date'],
                        'series_id': series_id,
                        'source': 'FRED'
                    }
            return None
        except Exception as e:
            st.warning(f"FRED API error for {series_id}: {e}")
            return None
    
    def get_multiple_series(self, series_dict):
        """Get data for multiple FRED series"""
        results = {}
        for name, series_id in series_dict.items():
            data = self.get_series_data(series_id)
            if data:
                results[name] = data
        return results
    
    def get_series_info(self, series_id):
        """Get metadata about a FRED series"""
        url = f"{self.base_url}/series"
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if 'seriess' in data:
                return data['seriess'][0]
        except Exception as e:
            st.warning(f"FRED series info error: {e}")
        return None

# Initialize FRED client
fred_client = FREDAPIClient()

# Streamlit App Configuration
st.set_page_config(
    page_title="FRED API Forward Calculator",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Forward Calculator with FRED API")
st.markdown("*Using Federal Reserve Economic Data for real-time bond yields and interest rates*")

# Cached functions for FRED data
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_fred_bond_data():
    """Get government bond yields from FRED"""
    bond_series = {
        'Poland_10Y': 'IRLTLT01PLM156N',
        'Germany_10Y': 'IRLTLT01DEM156N',
        'US_10Y': 'DGS10',
        'US_2Y': 'DGS2',
        'Euro_Area_10Y': 'IRLTLT01EZM156N'
    }
    
    data = fred_client.get_multiple_series(bond_series)
    
    # Interpolate German short-term rates
    if 'Germany_10Y' in data:
        # Estimate 9-month German yield (typically 20-30 bp below 10Y)
        de_10y = data['Germany_10Y']['value']
        data['Germany_9M'] = {
            'value': max(de_10y - 0.25, 0.1),  # 25bp below 10Y, minimum 0.1%
            'date': data['Germany_10Y']['date'],
            'series_id': 'Interpolated',
            'source': 'FRED + Interpolation'
        }
    
    return data

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_fred_rates_data():
    """Get interest rate benchmarks from FRED"""
    rates_series = {
        'EURIBOR_3M': 'EUR3MTD156N',
        'Fed_Funds': 'FEDFUNDS',
        'ECB_Rate': 'IRSTCB01EZM156N'
    }
    
    return fred_client.get_multiple_series(rates_series)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_eur_pln_rate():
    """Get EUR/PLN from NBP API"""
    try:
        url = "https://api.nbp.pl/api/exchangerates/rates/a/eur/"
        response = requests.get(url, timeout=10)
        data = response.json()
        return {
            'rate': data['rates'][0]['mid'],
            'date': data['rates'][0]['effectiveDate'],
            'source': 'NBP'
        }
    except Exception as e:
        st.warning(f"NBP API error: {e}")
        return {'rate': 4.25, 'date': 'Fallback', 'source': 'Estimated'}

# Forward calculation functions
def calculate_forward_rate(spot_rate, domestic_yield, foreign_yield, days):
    """Calculate forward rate using bond yields"""
    T = days / 365.0
    forward_rate = spot_rate * (1 + domestic_yield/100 * T) / (1 + foreign_yield/100 * T)
    return forward_rate

def calculate_forward_points(spot_rate, forward_rate):
    """Calculate forward points in pips"""
    return (forward_rate - spot_rate) * 10000

# Load data with spinner
with st.spinner("📡 Fetching real-time data from FRED API..."):
    bond_data = get_fred_bond_data()
    rates_data = get_fred_rates_data()
    forex_data = get_eur_pln_rate()

# Display data status
st.subheader("📊 Real-Time Market Data")

# Main metrics row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "EUR/PLN Spot", 
        f"{forex_data['rate']:.4f}",
        help=f"Source: {forex_data['source']} | Date: {forex_data['date']}"
    )

with col2:
    if 'Poland_10Y' in bond_data:
        pl_yield = bond_data['Poland_10Y']['value']
        pl_date = bond_data['Poland_10Y']['date']
        st.metric(
            "Poland 10Y Bond", 
            f"{pl_yield:.2f}%",
            help=f"FRED Series: IRLTLT01PLM156N | Date: {pl_date}"
        )
    else:
        st.metric("Poland 10Y Bond", "N/A", help="Data not available from FRED")

with col3:
    if 'Germany_9M' in bond_data:
        de_yield = bond_data['Germany_9M']['value']
        st.metric(
            "Germany 9M Bond", 
            f"{de_yield:.2f}%",
            help="Interpolated from 10Y German bond (FRED: IRLTLT01DEM156N)"
        )
    elif 'Germany_10Y' in bond_data:
        de_yield = bond_data['Germany_10Y']['value']
        st.metric(
            "Germany 10Y Bond", 
            f"{de_yield:.2f}%",
            help=f"FRED Series: IRLTLT01DEM156N"
        )
    else:
        st.metric("Germany Bond", "N/A", help="Data not available from FRED")

with col4:
    if 'Poland_10Y' in bond_data and 'Germany_9M' in bond_data:
        spread = bond_data['Poland_10Y']['value'] - bond_data['Germany_9M']['value']
        st.metric(
            "PL-DE Spread", 
            f"{spread:.2f} pp",
            help="Poland 10Y minus Germany 9M (interpolated)"
        )

# FRED API Status
with st.expander("🔍 FRED API Data Details"):
    if bond_data:
        st.write("**Available Bond Data:**")
        for name, data in bond_data.items():
            if name != 'Germany_9M':  # Skip interpolated data
                st.write(f"- **{name}**: {data['value']:.3f}% (Date: {data['date']}, Series: {data['series_id']})")
        
        if 'Germany_9M' in bond_data:
            st.write(f"- **Germany 9M**: {bond_data['Germany_9M']['value']:.3f}% (Interpolated from 10Y)")
    
    if rates_data:
        st.write("**Available Interest Rates:**")
        for name, data in rates_data.items():
            st.write(f"- **{name}**: {data['value']:.3f}% (Date: {data['date']}, Series: {data['series_id']})")

# Calculator Interface
st.markdown("---")
st.header("⚙️ Forward Rate Calculator")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📊 Input Parameters")
    
    # Spot rate
    spot_rate = st.number_input(
        "EUR/PLN Spot Rate:",
        value=forex_data['rate'],
        min_value=3.0,
        max_value=6.0,
        step=0.01,
        format="%.4f",
        help="Current EUR/PLN exchange rate"
    )
    
    # Bond yields
    st.write("**Government Bond Yields:**")
    
    col_pl, col_de = st.columns(2)
    
    with col_pl:
        if 'Poland_10Y' in bond_data:
            default_pl = bond_data['Poland_10Y']['value']
        else:
            default_pl = 5.70
        
        pl_yield = st.number_input(
            "Poland Yield (%):",
            value=default_pl,
            min_value=0.0,
            max_value=20.0,
            step=0.01,
            format="%.2f",
            help="Polish government bond yield from FRED"
        )
    
    with col_de:
        if 'Germany_9M' in bond_data:
            default_de = bond_data['Germany_9M']['value']
        elif 'Germany_10Y' in bond_data:
            default_de = bond_data['Germany_10Y']['value'] - 0.25
        else:
            default_de = 2.35
        
        de_yield = st.number_input(
            "Germany Yield (%):",
            value=default_de,
            min_value=-2.0,
            max_value=10.0,
            step=0.01,
            format="%.2f",
            help="German government bond yield (9M interpolated)"
        )
    
    # Time period
    st.write("**Forward Period:**")
    period_choice = st.selectbox(
        "Select Period:",
        ["1M", "3M", "6M", "9M", "1Y", "2Y", "Custom Days"]
    )
    
    if period_choice == "Custom Days":
        days = st.number_input("Days:", value=365, min_value=1, max_value=1825)
    else:
        period_days = {"1M": 30, "3M": 90, "6M": 180, "9M": 270, "1Y": 365, "2Y": 730}
        days = period_days[period_choice]

with col2:
    st.subheader("💰 Calculation Results")
    
    # Calculate forward rate
    forward_rate = calculate_forward_rate(spot_rate, pl_yield, de_yield, days)
    forward_points = calculate_forward_points(spot_rate, forward_rate)
    
    # Display results
    result_col1, result_col2 = st.columns(2)
    
    with result_col1:
        st.metric(
            "Forward Rate",
            f"{forward_rate:.4f}",
            delta=f"{forward_rate - spot_rate:.4f}"
        )
    
    with result_col2:
        st.metric(
            "Forward Points",
            f"{forward_points:.2f} pips"
        )
    
    # Analysis
    annualized_premium = ((forward_rate / spot_rate) - 1) * (365 / days) * 100
    
    if forward_rate > spot_rate:
        st.success(f"🔺 EUR trades at **{annualized_premium:.2f}% premium** annually")
    else:
        st.error(f"🔻 EUR trades at **{abs(annualized_premium):.2f}% discount** annually")
    
    # Detailed metrics
    with st.expander("📈 Detailed Analysis"):
        st.write(f"**Calculation Details:**")
        st.write(f"- Spot Rate: {spot_rate:.4f}")
        st.write(f"- Forward Rate: {forward_rate:.4f}")
        st.write(f"- Time to Maturity: {days} days ({days/365:.2f} years)")
        st.write(f"- Poland Yield: {pl_yield:.2f}%")
        st.write(f"- Germany Yield: {de_yield:.2f}%")
        st.write(f"- Yield Spread: {pl_yield - de_yield:.2f} pp")
        st.write(f"- Forward Premium: {((forward_rate/spot_rate)-1)*100:.4f}%")

# Forward curve table
st.markdown("---")
st.header("📅 Forward Rate Table")

# Generate forward rates for different periods
periods = [30, 90, 180, 270, 365, 730, 1095]
period_names = ["1M", "3M", "6M", "9M", "1Y", "2Y", "3Y"]

forward_table_data = []
for i, period_days in enumerate(periods):
    fw_rate = calculate_forward_rate(spot_rate, pl_yield, de_yield, period_days)
    fw_points = calculate_forward_points(spot_rate, fw_rate)
    annual_premium = ((fw_rate / spot_rate - 1) * (365 / period_days) * 100)
    
    forward_table_data.append({
        "Period": period_names[i],
        "Days": period_days,
        "Forward Rate": f"{fw_rate:.4f}",
        "Forward Points": f"{fw_points:.2f}",
        "Annual Premium": f"{annual_premium:.2f}%",
        "Spread vs Spot": f"{(fw_rate - spot_rate)*10000:.1f} pips"
    })

df = pd.DataFrame(forward_table_data)
st.dataframe(df, use_container_width=True)

# Forward curve chart
st.markdown("---")
st.header("📊 Forward Curve Visualization")

# Generate smooth curve data
curve_days = np.linspace(30, 1095, 100)
curve_forwards = [calculate_forward_rate(spot_rate, pl_yield, de_yield, d) for d in curve_days]
curve_points = [calculate_forward_points(spot_rate, fw) for fw in curve_forwards]

# Create subplots
fig = make_subplots(
    rows=2, cols=1,
    subplot_titles=("EUR/PLN Forward Curve", "Forward Points"),
    vertical_spacing=0.12,
    row_heights=[0.7, 0.3]
)

# Forward curve
fig.add_trace(go.Scatter(
    x=curve_days,
    y=curve_forwards,
    mode='lines',
    name='Forward Curve',
    line=dict(color='blue', width=3),
    hovertemplate='%{x} days<br>Rate: %{y:.4f}<extra></extra>'
), row=1, col=1)

# Spot rate line
fig.add_hline(y=spot_rate, line_dash="dash", line_color="red", 
              annotation_text=f"Spot: {spot_rate:.4f}", row=1)

# Standard period points
fig.add_trace(go.Scatter(
    x=periods,
    y=[calculate_forward_rate(spot_rate, pl_yield, de_yield, d) for d in periods],
    mode='markers+text',
    name='Standard Periods',
    marker=dict(color='orange', size=10),
    text=period_names,
    textposition="top center",
    hovertemplate='%{text}<br>%{x} days<br>Rate: %{y:.4f}<extra></extra>'
), row=1, col=1)

# Forward points
fig.add_trace(go.Scatter(
    x=curve_days,
    y=curve_points,
    mode='lines',
    name='Forward Points',
    line=dict(color='green', width=3),
    showlegend=False,
    hovertemplate='%{x} days<br>Points: %{y:.2f} pips<extra></extra>'
), row=2, col=1)

# Zero line
fig.add_hline(y=0, line_dash="dot", line_color="gray", row=2)

fig.update_layout(
    title="EUR/PLN Forward Analysis (Based on FRED Bond Data)",
    height=700,
    hovermode='closest'
)

fig.update_xaxes(title_text="Days to Maturity", row=2, col=1)
fig.update_yaxes(title_text="EUR/PLN Rate", row=1, col=1)
fig.update_yaxes(title_text="Forward Points (pips)", row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

# Data refresh section
st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("🔄 Refresh FRED Data"):
        st.cache_data.clear()
        st.rerun()

with col2:
    if st.button("📊 View FRED Series"):
        st.write("**FRED Series Used:**")
        for name, series_id in FRED_SERIES.items():
            st.write(f"- {name}: {series_id}")

with col3:
    if st.button("ℹ️ About FRED API"):
        st.info("""
        **Federal Reserve Economic Data (FRED)**
        - Free API access to 500,000+ economic time series
        - Real-time government bond yields
        - Official central bank interest rates
        - Historical data back to 1900s
        - No API key required (demo mode) or free registration
        """)

# Footer
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: gray; font-size: 0.8em;'>
    🏛️ <strong>Forward Calculator powered by FRED API</strong><br>
    📊 Data: Federal Reserve Economic Data | NBP API<br>
    ⏰ Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
    🔗 FRED API: <a href="https://fred.stlouisfed.org/docs/api/" target="_blank">Documentation</a> | 
    Free API Key: <a href="https://fred.stlouisfed.org/docs/api/api_key.html" target="_blank">Register</a>
    </div>
    """, 
    unsafe_allow_html=True
)
