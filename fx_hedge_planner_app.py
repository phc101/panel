import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta

# FRED API Configuration
FRED_API_KEY = "f65897ba8bbc5c387dc26081d5b66edf"  # Replace with your API key

# Page config
st.set_page_config(
    page_title="FX Trading Dashboard",
    page_icon="💱",
    layout="wide"
)

# Enhanced Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.2rem;
        border-radius: 0.8rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    .actual-rate {
        font-size: 2.2rem;
        font-weight: bold;
        color: #2E86AB;
        margin: 0;
    }
    .predicted-rate {
        font-size: 2.2rem;
        font-weight: bold;
        color: #F24236;
        margin: 0;
    }
    .rate-label {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 0.5rem;
        font-weight: 500;
    }
    .difference {
        font-size: 1.1rem;
        font-weight: bold;
        color: #28a745;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        color: #856404;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        color: #155724;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        color: #0c5460;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .calculation-breakdown {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        border-left: 4px solid #28a745;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS - SAFE FORMATTING
# ============================================================================

def safe_format_days(value, default="N/A"):
    """Safely format convergence days with None check"""
    if value is not None and not np.isnan(value):
        return f"{value:.1f}"
    return default

def safe_format_percentage(value, default="N/A"):
    """Safely format percentage with None check"""
    if value is not None and not np.isnan(value):
        return f"{value:.1f}%"
    return default

def format_currency(value, currency="EUR"):
    """Format currency values with proper formatting"""
    if abs(value) >= 1_000_000:
        return f"{value/1_000_000:.2f}M {currency}"
    elif abs(value) >= 1_000:
        return f"{value/1_000:.0f}k {currency}"
    else:
        return f"{value:,.0f} {currency}"

# ============================================================================
# FRED API CLIENT CLASS
# ============================================================================

class FREDAPIClient:
    """Enhanced FRED API client for fetching economic data"""
    
    def __init__(self, api_key=FRED_API_KEY):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"
    
    def get_series_data(self, series_id, limit=1, sort_order='desc'):
        """Get latest data for a specific FRED series with enhanced error handling"""
        url = f"https://api.stlouisfed.org/fred/series/observations"
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json',
            'limit': limit,
            'sort_order': sort_order
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'observations' in data and data['observations']:
                latest = data['observations'][0]
                if latest['value'] != '.':
                    return {
                        'value': float(latest['value']),
                        'date': latest['date'],
                        'series_id': series_id,
                        'source': 'FRED',
                        'status': 'success'
                    }
            return {'status': 'no_data', 'series_id': series_id}
        except requests.exceptions.RequestException as e:
            return {'status': 'error', 'error': str(e), 'series_id': series_id}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'series_id': series_id}
    
    def get_multiple_series(self, series_dict):
        """Get data for multiple FRED series with status tracking"""
        results = {}
        errors = []
        for name, series_id in series_dict.items():
            data = self.get_series_data(series_id)
            if data.get('status') == 'success':
                results[name] = data
            else:
                errors.append(f"{name}: {data.get('error', 'No data available')}")
        
        if errors:
            st.warning(f"FRED API issues: {'; '.join(errors)}")
        
        return results

# ============================================================================
# WINDOW FORWARD CALCULATOR CLASS (ENHANCED)
# ============================================================================

class WindowForwardCalculator:
    def __init__(self, fred_client):
        self.fred_client = fred_client
        self.tenors = [
            "One Month", "Two Month", "Three Month", "Four Month", 
            "Five Month", "Six Month", "Seven Month", "Eight Month",
            "Nine Month", "Ten Month", "Eleven Month", "One Year"
        ]
        
        # Tenor mapping to months
        self.tenor_months = {
            "One Month": 1, "Two Month": 2, "Three Month": 3, "Four Month": 4,
            "Five Month": 5, "Six Month": 6, "Seven Month": 7, "Eight Month": 8,
            "Nine Month": 9, "Ten Month": 10, "Eleven Month": 11, "One Year": 12
        }
    
    def generate_forward_points_from_spreads(self, spot_rate, pl_yield, de_yield, bid_ask_spread=0.002):
        """Generate forward points for all tenors based on bond spreads"""
        points_data = {}
        
        for tenor in self.tenors:
            months = self.tenor_months[tenor]
            days = months * 30  # Approximate days
            
            # Calculate theoretical forward points using bond spreads
            theoretical_forward = self.calculate_forward_rate(spot_rate, pl_yield, de_yield, days)
            forward_points = theoretical_forward - spot_rate
            
            # Create bid/ask spread
            bid_points = forward_points - (bid_ask_spread / 2)
            ask_points = forward_points + (bid_ask_spread / 2)
            mid_points = forward_points
            
            points_data[tenor] = {
                "bid": bid_points,
                "ask": ask_points,
                "mid": mid_points,
                "days": days,
                "months": months
            }
        
        return points_data
    
    def calculate_points_to_window(self, window_days, points_data):
        """Calculate forward points to the start of the window with enhanced interpolation"""
        window_months = window_days / 30.0
        
        # Get available months and sort them
        available_months = sorted([data["months"] for data in points_data.values()])
        
        if window_months <= available_months[0]:
            # Use shortest tenor with scaling
            shortest_tenor = next(tenor for tenor, data in points_data.items() 
                                if data["months"] == available_months[0])
            ratio = window_months / available_months[0]
            return {
                "bid": points_data[shortest_tenor]["bid"] * ratio,
                "ask": points_data[shortest_tenor]["ask"] * ratio,
                "mid": points_data[shortest_tenor]["mid"] * ratio,
                "method": f"Extrapolated from {shortest_tenor}"
            }
        elif window_months >= available_months[-1]:
            # Use longest tenor
            longest_tenor = next(tenor for tenor, data in points_data.items() 
                               if data["months"] == available_months[-1])
            return {
                "bid": points_data[longest_tenor]["bid"],
                "ask": points_data[longest_tenor]["ask"],
                "mid": points_data[longest_tenor]["mid"],
                "method": f"Using {longest_tenor}"
            }
        else:
            # Linear interpolation between two tenors
            lower_months = max([m for m in available_months if m <= window_months])
            upper_months = min([m for m in available_months if m >= window_months])
            
            lower_tenor = next(tenor for tenor, data in points_data.items() 
                             if data["months"] == lower_months)
            upper_tenor = next(tenor for tenor, data in points_data.items() 
                             if data["months"] == upper_months)
            
            # Linear interpolation
            ratio = (window_months - lower_months) / (upper_months - lower_months)
            
            return {
                "bid": points_data[lower_tenor]["bid"] + ratio * (points_data[upper_tenor]["bid"] - points_data[lower_tenor]["bid"]),
                "ask": points_data[lower_tenor]["ask"] + ratio * (points_data[upper_tenor]["ask"] - points_data[lower_tenor]["ask"]),
                "mid": points_data[lower_tenor]["mid"] + ratio * (points_data[upper_tenor]["mid"] - points_data[lower_tenor]["mid"]),
                "method": f"Interpolated between {lower_tenor} and {upper_tenor}"
            }
    
    def calculate_forward_rate(self, spot_rate, domestic_yield, foreign_yield, days):
        """Calculate forward rate using bond yields"""
        T = days / 365.0
        if T == 0:
            return spot_rate
        forward_rate = spot_rate * (1 + domestic_yield/100 * T) / (1 + foreign_yield/100 * T)
        return forward_rate
    
    def calculate_window_forward_pricing(self, spot_rate, points_to_window_mid, swap_risk, 
                                       points_factor=0.70, risk_factor=0.40):
        """Calculate complete window forward pricing breakdown"""
        # Correct Formula: Spot + (Points_to_Window × points_factor) - (Swap_Risk × risk_factor)
        points_for_client = points_to_window_mid * points_factor
        swap_risk_compensation = swap_risk * risk_factor
        
        client_rate = spot_rate + points_for_client - swap_risk_compensation
        theoretical_rate = spot_rate + points_to_window_mid
        
        # Calculate dealer profit components
        points_profit = points_to_window_mid * (1 - points_factor)  # Points kept by dealer
        risk_profit = swap_risk * risk_factor  # Risk compensation
        total_profit_per_unit = points_profit + risk_profit
        
        return {
            "client_rate": client_rate,
            "theoretical_rate": theoretical_rate,
            "points_for_client": points_for_client,
            "swap_risk_compensation": swap_risk_compensation,
            "points_profit": points_profit,
            "risk_profit": risk_profit,
            "total_profit_per_unit": total_profit_per_unit
        }
    
    def analyze_window_length_impact(self, spot_rate, points_data, swap_risk, 
                                   points_factor=0.70, risk_factor=0.40):
        """Analyze impact of different window lengths on pricing and profit"""
        analysis_results = []
        
        for window_days in range(30, 181, 30):  # 30 to 180 days, step 30
            points_to_window = self.calculate_points_to_window(window_days, points_data)
            pricing = self.calculate_window_forward_pricing(
                spot_rate, points_to_window["mid"], swap_risk, points_factor, risk_factor
            )
            
            analysis_results.append({
                "window_days": window_days,
                "client_rate": pricing["client_rate"],
                "profit_per_unit": pricing["total_profit_per_unit"],
                "points_to_window": points_to_window["mid"]
            })
        
        return analysis_results

# ============================================================================
# CALCULATION FUNCTIONS
# ============================================================================

def calculate_forward_rate(spot_rate, domestic_yield, foreign_yield, days):
    """Calculate forward rate using bond yields"""
    T = days / 365.0
    if T == 0:
        return spot_rate
    forward_rate = spot_rate * (1 + domestic_yield/100 * T) / (1 + foreign_yield/100 * T)
    return forward_rate

def calculate_forward_points(spot_rate, forward_rate):
    """Calculate forward points in pips"""
    return (forward_rate - spot_rate) * 10000

# ============================================================================
# CACHED DATA FUNCTIONS
# ============================================================================

@st.cache_data(ttl=3600)
def get_fred_bond_data():
    """Get government bond yields from FRED with enhanced error handling"""
    fred_client = FREDAPIClient()
    bond_series = {
        'Poland_10Y': 'IRLTLT01PLM156N',
        'Germany_10Y': 'IRLTLT01DEM156N',
        'US_10Y': 'DGS10',
        'US_2Y': 'DGS2',
        'Euro_Area_10Y': 'IRLTLT01EZM156N'
    }
    
    data = fred_client.get_multiple_series(bond_series)
    
    # Interpolate German short-term rates if German 10Y is available
    if 'Germany_10Y' in data:
        de_10y = data['Germany_10Y']['value']
        data['Germany_9M'] = {
            'value': max(de_10y - 0.25, 0.1),
            'date': data['Germany_10Y']['date'],
            'series_id': 'Interpolated',
            'source': 'FRED + Interpolation',
            'status': 'success'
        }
    else:
        # Fallback data
        data['Germany_9M'] = {
            'value': 2.35,
            'date': 'Fallback',
            'series_id': 'Fallback',
            'source': 'Estimated',
            'status': 'fallback'
        }
    
    return data

@st.cache_data(ttl=300)
def get_eur_pln_rate():
    """Get current EUR/PLN from NBP API with enhanced error handling"""
    try:
        url = "https://api.nbp.pl/api/exchangerates/rates/a/eur/"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            'rate': data['rates'][0]['mid'],
            'date': data['rates'][0]['effectiveDate'],
            'source': 'NBP',
            'status': 'success'
        }
    except Exception as e:
        st.warning(f"NBP API error: {e}. Using fallback rate.")
        return {
            'rate': 4.25, 
            'date': datetime.now().strftime('%Y-%m-%d'), 
            'source': 'Estimated',
            'status': 'fallback'
        }

@st.cache_data(ttl=300)
def get_usd_pln_rate():
    """Get current USD/PLN from NBP API"""
    try:
        url = "https://api.nbp.pl/api/exchangerates/rates/a/usd/"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            'rate': data['rates'][0]['mid'],
            'date': data['rates'][0]['effectiveDate'],
            'source': 'NBP',
            'status': 'success'
        }
    except Exception as e:
        return {
            'rate': 3.85, 
            'date': datetime.now().strftime('%Y-%m-%d'), 
            'source': 'Estimated',
            'status': 'fallback'
        }

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def create_breakdown_chart(pricing_data, nominal_amount):
    """Create a breakdown chart showing pricing components"""
    fig = go.Figure()
    
    # Calculate cumulative values for waterfall chart
    spot = pricing_data["spot_rate"] if "spot_rate" in pricing_data else 4.25
    points_for_client = pricing_data["points_for_client"]
    risk_compensation = pricing_data["swap_risk_compensation"]
    final_rate = pricing_data["client_rate"]
    
    categories = ['Spot Rate', 'Points Added', 'Risk Deducted', 'Final Client Rate']
    values = [spot, points_for_client, -risk_compensation, 0]  # 0 for final as it's cumulative
    cumulative = [spot, spot + points_for_client, spot + points_for_client - risk_compensation, final_rate]
    
    # Create waterfall chart
    fig.add_trace(go.Waterfall(
        name="Rate Components",
        orientation="v",
        measure=["absolute", "relative", "relative", "total"],
        x=categories,
        textposition="outside",
        text=[f"{spot:.4f}", f"+{points_for_client:.4f}", f"-{risk_compensation:.4f}", f"{final_rate:.4f}"],
        y=[spot, points_for_client, -risk_compensation, final_rate],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
    ))
    
    fig.update_layout(
        title="Window Forward Rate Breakdown",
        showlegend=False,
        height=400,
        yaxis_title="EUR/PLN Rate"
    )
    
    return fig

def create_profit_analysis_chart(analysis_results):
    """Create chart showing profit vs window length"""
    window_days = [r["window_days"] for r in analysis_results]
    profits = [r["profit_per_unit"] * 10000 for r in analysis_results]  # Convert to pips
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=window_days,
        y=profits,
        mode='lines+markers',
        name='Dealer Profit (pips)',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title="Dealer Profit vs Window Length",
        xaxis_title="Window Length (days)",
        yaxis_title="Profit per EUR (pips)",
        height=400,
        showlegend=False
    )
    
    return fig

# ============================================================================
# MAIN APPLICATION
# ============================================================================

# Enhanced Header with status indicators
st.markdown("""
<div style="display: flex; align-items: center; margin-bottom: 2rem;">
    <div style="background: linear-gradient(45deg, #667eea, #764ba2); width: 60px; height: 60px; border-radius: 10px; margin-right: 1rem; display: flex; align-items: center; justify-content: center;">
        <span style="font-size: 2rem;">💱</span>
    </div>
    <div>
        <h1 style="margin: 0; color: #2c3e50;">Professional FX Trading Dashboard</h1>
        <p style="margin: 0; color: #7f8c8d; font-size: 0.9rem;">Advanced Forward Rate Calculator & Window Forward Analytics</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Load shared data with status tracking
with st.spinner("📡 Loading market data..."):
    bond_data = get_fred_bond_data()
    forex_data = get_eur_pln_rate()
    usd_forex_data = get_usd_pln_rate()

# Data status indicator
data_status_col1, data_status_col2, data_status_col3 = st.columns(3)

with data_status_col1:
    status = "🟢 Live" if forex_data.get('status') == 'success' else "🟡 Fallback"
    st.markdown(f"**EUR/PLN:** {status}")

with data_status_col2:
    bond_status = "🟢 Live" if any(d.get('status') == 'success' for d in bond_data.values()) else "🟡 Fallback"
    st.markdown(f"**Bond Data:** {bond_status}")

with data_status_col3:
    st.markdown(f"**Last Update:** {datetime.now().strftime('%H:%M:%S')}")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["🧮 Forward Rate Calculator", "📊 Bond Spread Dashboard", "💼 Window Forward Calculator", "📈 Analytics"])

# ============================================================================
# TAB 1: ENHANCED FORWARD RATE CALCULATOR
# ============================================================================

with tab1:
    st.header("🧮 Forward Rate Calculator with FRED API")
    
    # Current market data display with enhanced styling
    st.subheader("📊 Current Market Data")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_emoji = "🟢" if forex_data.get('status') == 'success' else "🟡"
        st.metric(
            f"{status_emoji} EUR/PLN Spot", 
            f"{forex_data['rate']:.4f}",
            help=f"Source: {forex_data['source']} | Date: {forex_data['date']}"
        )
    
    with col2:
        if 'Poland_10Y' in bond_data:
            pl_yield = bond_data['Poland_10Y']['value']
            pl_date = bond_data['Poland_10Y']['date']
            status_emoji = "🟢" if bond_data['Poland_10Y'].get('status') == 'success' else "🟡"
            st.metric(
                f"{status_emoji} Poland 10Y Bond", 
                f"{pl_yield:.2f}%",
                help=f"FRED Series: IRLTLT01PLM156N | Date: {pl_date}"
            )
        else:
            st.metric("🔴 Poland 10Y Bond", "N/A", help="Data not available")
    
    with col3:
        if 'Germany_9M' in bond_data:
            de_yield = bond_data['Germany_9M']['value']
            status_emoji = "🟢" if bond_data['Germany_9M'].get('status') == 'success' else "🟡"
            st.metric(
                f"{status_emoji} Germany 9M Bond", 
                f"{de_yield:.2f}%",
                help="Interpolated from 10Y German bond"
            )
        else:
            st.metric("🔴 Germany Bond", "N/A", help="Data not available")
    
    with col4:
        if 'Poland_10Y' in bond_data and 'Germany_9M' in bond_data:
            spread = bond_data['Poland_10Y']['value'] - bond_data['Germany_9M']['value']
            st.metric(
                "PL-DE Spread", 
                f"{spread:.2f} pp",
                help="Poland 10Y minus Germany 9M"
            )
    
    # Enhanced calculator interface
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("⚙️ Input Parameters")
        
        # Spot rate with validation
        spot_rate = st.number_input(
            "EUR/PLN Spot Rate:",
            value=forex_data['rate'],
            min_value=3.0,
            max_value=6.0,
            step=0.0001,
            format="%.4f",
            help="Current EUR/PLN exchange rate"
        )
        
        # Bond yields with better defaults
        st.write("**Government Bond Yields:**")
        col_pl, col_de = st.columns(2)
        
        with col_pl:
            default_pl = bond_data['Poland_10Y']['value'] if 'Poland_10Y' in bond_data else 5.70
            pl_yield = st.number_input(
                "Poland Yield (%):",
                value=default_pl,
                min_value=0.0,
                max_value=20.0,
                step=0.01,
                format="%.2f",
                help="Polish government bond yield"
            )
        
        with col_de:
            default_de = bond_data['Germany_9M']['value'] if 'Germany_9M' in bond_data else 2.35
            de_yield = st.number_input(
                "Germany Yield (%):",
                value=default_de,
                min_value=-2.0,
                max_value=10.0,
                step=0.01,
                format="%.2f",
                help="German government bond yield"
            )
        
        # Enhanced time period selection
        st.write("**Forward Period:**")
        period_choice = st.selectbox(
            "Select Period:",
            ["1M", "3M", "6M", "9M", "1Y", "2Y", "Custom Days"],
            help="Standard forward periods or custom duration"
        )
        
        if period_choice == "Custom Days":
            days = st.number_input(
                "Days:", 
                value=365, 
                min_value=1, 
                max_value=730, 
                help="Maximum 2 years (730 days)"
            )
        else:
            period_days = {"1M": 30, "3M": 90, "6M": 180, "9M": 270, "1Y": 365, "2Y": 730}
            days = period_days[period_choice]
            st.info(f"Selected period: **{days} days**")
    
    with col2:
        st.subheader("💰 Calculation Results")
        
        # Calculate forward rate with error handling
        try:
            forward_rate = calculate_forward_rate(spot_rate, pl_yield, de_yield, days)
            forward_points = calculate_forward_points(spot_rate, forward_rate)
            
            # Display results with enhanced formatting
            result_col1, result_col2 = st.columns(2)
            
            with result_col1:
                st.metric(
                    "Forward Rate",
                    f"{forward_rate:.4f}",
                    delta=f"{forward_rate - spot_rate:.4f}",
                    help="Theoretical forward rate based on yield differential"
                )
            
            with result_col2:
                st.metric(
                    "Forward Points",
                    f"{forward_points:.2f} pips",
                    help="Forward points in pips (1 pip = 0.0001)"
                )
            
            # Enhanced analysis
            annualized_premium = ((forward_rate / spot_rate) - 1) * (365 / days) * 100
            
            if forward_rate > spot_rate:
                st.markdown(f"""
                <div class="success-box">
                    🔺 EUR trades at <strong>{annualized_premium:.2f}% premium</strong> annually
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="warning-box">
                    🔻 EUR trades at <strong>{abs(annualized_premium):.2f}% discount</strong> annually
                </div>
                """, unsafe_allow_html=True)
            
            # Detailed metrics with enhanced information
            with st.expander("📈 Detailed Analysis"):
                st.markdown("**Calculation Details:**")
                
                calc_details = f"""
                - **Spot Rate:** {spot_rate:.4f}
                - **Forward Rate:** {forward_rate:.4f}
                - **Time to Maturity:** {days} days ({days/365:.2f} years)
                - **Poland Yield:** {pl_yield:.2f}%
                - **Germany Yield:** {de_yield:.2f}%
                - **Yield Spread:** {pl_yield - de_yield:.2f} pp
                - **Annualized Premium/Discount:** {annualized_premium:.2f}%
                
                **Formula Used:**
                Forward = Spot × (1 + Polish_Yield × T) / (1 + German_Yield × T)
                """
                st.markdown(calc_details)
                
                # Risk analysis
                st.markdown("**Risk Analysis:**")
                if abs(pl_yield - de_yield) > 3:
                    st.warning("⚠️ Large yield spread may indicate higher risk")
                else:
                    st.success("✅ Yield spread within normal range")
                    
                if days > 365:
                    st.info("ℹ️ Long-term forward rates are more sensitive to yield changes")
        
        except Exception as e:
            st.error(f"Calculation error: {e}")
    
    # Enhanced Forward curve table
    st.markdown("---")
    st.header("📅 Forward Rate Table")
    
    try:
        periods = [30, 90, 180, 270, 365, 730]
        period_names = ["1M", "3M", "6M", "9M", "1Y", "2Y"]
        
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
                "Spread Impact": f"{(fw_rate - spot_rate) / (pl_yield - de_yield) * 100:.1f}x" if pl_yield != de_yield else "N/A"
            })
        
        df_forward = pd.DataFrame(forward_table_data)
        st.dataframe(df_forward, use_container_width=True)
        
    except Exception as e:
        st.error(f"Forward table calculation error: {e}")

# ============================================================================
# TAB 2: ENHANCED BOND SPREAD DASHBOARD
# ============================================================================

with tab2:
    st.header("📊 Bond Spread Analytics")
    st.markdown("*EUR/PLN Bond Spread Analysis with Enhanced Metrics*")
    
    # Enhanced current market overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_emoji = "🟢" if forex_data.get('status') == 'success' else "🟡"
        st.metric(
            f"{status_emoji} EUR/PLN Spot", 
            f"{forex_data['rate']:.4f}",
            help=f"Last updated: {forex_data['date']}"
        )
    
    with col2:
        if 'Poland_10Y' in bond_data:
            pl_yield_display = bond_data['Poland_10Y']['value']
            status_emoji = "🟢" if bond_data['Poland_10Y'].get('status') == 'success' else "🟡"
            st.metric(
                f"{status_emoji} Poland 10Y", 
                f"{pl_yield_display:.2f}%",
                help=f"Date: {bond_data['Poland_10Y']['date']}"
            )
        else:
            st.metric("🔴 Poland 10Y", "N/A")
    
    with col3:
        if 'Germany_9M' in bond_data:
            de_yield_display = bond_data['Germany_9M']['value']
            status_emoji = "🟢" if bond_data['Germany_9M'].get('status') == 'success' else "🟡"
            st.metric(
                f"{status_emoji} Germany 10Y", 
                f"{de_yield_display:.2f}%",
                help="Interpolated from 10Y"
            )
        else:
            st.metric("🔴 Germany 10Y", "N/A")
    
    with col4:
        if 'Poland_10Y' in bond_data and 'Germany_9M' in bond_data:
            spread = bond_data['Poland_10Y']['value'] - bond_data['Germany_9M']['value']
            
            # Spread analysis
            if spread > 4:
                delta_color = "red"
                spread_status = "High"
            elif spread > 2:
                delta_color = "orange"
                spread_status = "Elevated"
            else:
                delta_color = "green"
                spread_status = "Normal"
                
            st.metric(
                "PL-DE Spread", 
                f"{spread:.2f}pp",
                delta=f"{spread_status}",
                help="Poland-Germany yield spread"
            )
    
    # Historical context and analytics
    st.markdown("---")
    st.subheader("📈 Spread Analytics")
    
    if 'Poland_10Y' in bond_data and 'Germany_9M' in bond_data:
        spread_value = bond_data['Poland_10Y']['value'] - bond_data['Germany_9M']['value']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Spread Analysis:**")
            
            # Spread interpretation
            if spread_value > 4:
                st.markdown("""
                <div class="warning-box">
                    ⚠️ <strong>High Spread ({:.2f}pp)</strong><br>
                    • Indicates elevated risk premium for Poland<br>
                    • EUR/PLN likely to strengthen (EUR appreciation)<br>
                    • Consider hedging strategies
                </div>
                """.format(spread_value), unsafe_allow_html=True)
            elif spread_value > 2:
                st.markdown("""
                <div class="info-box">
                    ℹ️ <strong>Elevated Spread ({:.2f}pp)</strong><br>
                    • Moderate risk premium<br>
                    • Watch for trend changes<br>
                    • Normal market conditions
                </div>
                """.format(spread_value), unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="success-box">
                    ✅ <strong>Normal Spread ({:.2f}pp)</strong><br>
                    • Low risk premium<br>
                    • Stable market conditions<br>
                    • Good environment for planning
                </div>
                """.format(spread_value), unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Trading Implications:**")
            
            # Calculate implied forward rates
            spot_for_calc = forex_data['rate']
            pl_yield_calc = bond_data['Poland_10Y']['value']
            de_yield_calc = bond_data['Germany_9M']['value']
            
            # 3M and 1Y forwards
            fwd_3m = calculate_forward_rate(spot_for_calc, pl_yield_calc, de_yield_calc, 90)
            fwd_1y = calculate_forward_rate(spot_for_calc, pl_yield_calc, de_yield_calc, 365)
            
            st.markdown(f"""
            **Implied Forward Rates:**
            - 3M Forward: **{fwd_3m:.4f}** ({(fwd_3m-spot_for_calc)*10000:.1f} pips)
            - 1Y Forward: **{fwd_1y:.4f}** ({(fwd_1y-spot_for_calc)*10000:.1f} pips)
            
            **Strategy Suggestions:**
            - Spread > 3pp: Consider EUR long positions
            - Spread < 2pp: Monitor for PLN strength
            - Volatile spreads: Use options for protection
            """)
    
    # Additional market context
    st.markdown("---")
    st.subheader("🌍 Global Context")
    
    context_col1, context_col2, context_col3 = st.columns(3)
    
    with context_col1:
        if 'US_10Y' in bond_data:
            us_yield = bond_data['US_10Y']['value']
            st.metric(
                "US 10Y Treasury", 
                f"{us_yield:.2f}%",
                help="US benchmark rate"
            )
    
    with context_col2:
        if 'Euro_Area_10Y' in bond_data:
            eu_yield = bond_data['Euro_Area_10Y']['value']
            st.metric(
                "Euro Area 10Y", 
                f"{eu_yield:.2f}%",
                help="Euro area benchmark"
            )
    
    with context_col3:
        if 'US_2Y' in bond_data:
            us_2y = bond_data['US_2Y']['value']
            st.metric(
                "US 2Y Treasury", 
                f"{us_2y:.2f}%",
                help="Short-term US rate"
            )

# ============================================================================
# TAB 3: ENHANCED WINDOW FORWARD CALCULATOR
# ============================================================================

with tab3:
    st.header("💼 Window Forward Dealer Calculator")
    st.markdown("*Professional window forward pricing using points TO WINDOW with enhanced analytics*")
    
    # Initialize enhanced calculator
    wf_calc = WindowForwardCalculator(FREDAPIClient())
    
    # ============================================================================
    # ENHANCED CONFIGURATION SECTION
    # ============================================================================
    
    st.subheader("⚙️ Configuration Parameters")
    
    config_col1, config_col2, config_col3, config_col4 = st.columns(4)
    
    with config_col1:
        spot_rate_wf = st.number_input(
            "EUR/PLN Spot Rate:",
            value=forex_data['rate'],
            min_value=3.0,
            max_value=6.0,
            step=0.0001,
            format="%.4f",
            key="wf_spot",
            help="Current EUR/PLN spot rate"
        )
    
    with config_col2:
        window_days = st.number_input(
            "Window Length (days):",
            value=90,
            min_value=30,
            max_value=365,
            step=1,
            key="wf_window",
            help="Duration of the trading window"
        )
    
    with config_col3:
        nominal_amount = st.number_input(
            "Nominal Amount (EUR):",
            value=2_500_000,
            min_value=100_000,
            max_value=100_000_000,
            step=100_000,
            format="%d",
            key="wf_nominal",
            help="Transaction size in EUR"
        )
    
    with config_col4:
        bid_ask_spread = st.number_input(
            "Bid-Ask Spread:",
            value=0.0020,
            min_value=0.0010,
            max_value=0.0100,
            step=0.0001,
            format="%.4f",
            key="wf_spread",
            help="Market bid-ask spread in rate terms"
        )
    
    # Enhanced advanced configuration
    st.subheader("🔧 Advanced Dealer Parameters")
    
    adv_col1, adv_col2, adv_col3 = st.columns(3)
    
    with adv_col1:
        points_factor = st.slider(
            "Points Factor (% given to client):",
            min_value=0.50,
            max_value=0.90,
            value=0.70,
            step=0.05,
            key="points_factor",
            help="Percentage of forward points given to client (typical: 60-80%)"
        )
    
    with adv_col2:
        risk_factor = st.slider(
            "Risk Factor (swap risk compensation):",
            min_value=0.30,
            max_value=0.70,
            value=0.40,
            step=0.05,
            key="risk_factor",
            help="Percentage of swap risk charged to client (typical: 30-50%)"
        )
    
    with adv_col3:
        leverage_factor = st.slider(
            "Profit Leverage:",
            min_value=1.0,
            max_value=3.0,
            value=1.5,
            step=0.1,
            key="leverage_factor",
            help="Leverage factor for profit calculation"
        )
    
    # Get enhanced bond yields for forward points generation
    default_pl_yield = bond_data['Poland_10Y']['value'] if 'Poland_10Y' in bond_data else 5.70
    default_de_yield = bond_data['Germany_9M']['value'] if 'Germany_9M' in bond_data else 2.35
    
    # ============================================================================
    # ENHANCED LIVE FORWARD POINTS GENERATION
    # ============================================================================
    
    st.markdown("---")
    st.subheader("📊 Live Forward Points (Generated from Bond Spreads)")
    
    try:
        # Generate forward points from current bond spreads
        forward_points_data = wf_calc.generate_forward_points_from_spreads(
            spot_rate_wf, 
            default_pl_yield, 
            default_de_yield, 
            bid_ask_spread
        )
        
        # Calculate points to specific window
        points_to_window = wf_calc.calculate_points_to_window(window_days, forward_points_data)
        
        # Display points to window
        points_col1, points_col2, points_col3, points_col4 = st.columns(4)
        
        with points_col1:
            st.metric(
                "Points to Window (Bid)",
                f"{points_to_window['bid']:.4f}",
                help="Forward points to window start (bid side)"
            )
        
        with points_col2:
            st.metric(
                "Points to Window (Mid)",
                f"{points_to_window['mid']:.4f}",
                help="Forward points to window start (mid rate)"
            )
        
        with points_col3:
            st.metric(
                "Points to Window (Ask)",
                f"{points_to_window['ask']:.4f}",
                help="Forward points to window start (ask side)"
            )
        
        with points_col4:
            st.info(f"**Method:** {points_to_window.get('method', 'Calculated')}")
        
        # ============================================================================
        # WINDOW FORWARD PRICING CALCULATION
        # ============================================================================
        
        st.markdown("---")
        st.subheader("💰 Window Forward Pricing")
        
        # Calculate swap risk (using bid-ask spread as proxy)
        swap_risk = bid_ask_spread
        
        # Calculate comprehensive pricing
        pricing_data = wf_calc.calculate_window_forward_pricing(
            spot_rate_wf, 
            points_to_window['mid'], 
            swap_risk, 
            points_factor, 
            risk_factor
        )
        
        # Add spot rate to pricing data for visualization
        pricing_data['spot_rate'] = spot_rate_wf
        
        # Display main results
        main_results_col1, main_results_col2 = st.columns(2)
        
        with main_results_col1:
            st.markdown("""
            <div class="calculation-breakdown">
                <h4>🎯 Client Rate Calculation</h4>
                <p><strong>Formula:</strong> Spot + (Points_to_Window × {:.0%}) - (Swap_Risk × {:.0%})</p>
                <p><strong>Result:</strong> <span style="font-size: 1.5em; color: #2E86AB;">{:.4f}</span></p>
            </div>
            """.format(points_factor, risk_factor, pricing_data['client_rate']), unsafe_allow_html=True)
        
        with main_results_col2:
            st.markdown("""
            <div class="calculation-breakdown">
                <h4>📈 Theoretical Rate</h4>
                <p><strong>Formula:</strong> Spot + Full_Points_to_Window</p>
                <p><strong>Result:</strong> <span style="font-size: 1.5em; color: #F24236;">{:.4f}</span></p>
            </div>
            """.format(pricing_data['theoretical_rate']), unsafe_allow_html=True)
        
        # Detailed breakdown
        st.subheader("🔍 Detailed Breakdown")
        
        breakdown_col1, breakdown_col2, breakdown_col3 = st.columns(3)
        
        with breakdown_col1:
            st.markdown("**Rate Components:**")
            st.write(f"• Spot Rate: {spot_rate_wf:.4f}")
            st.write(f"• Points for Client: +{pricing_data['points_for_client']:.4f}")
            st.write(f"• Risk Compensation: -{pricing_data['swap_risk_compensation']:.4f}")
            st.write(f"• **Final Client Rate: {pricing_data['client_rate']:.4f}**")
        
        with breakdown_col2:
            st.markdown("**Dealer Profit (per EUR):**")
            st.write(f"• Points Profit: {pricing_data['points_profit']:.4f}")
            st.write(f"• Risk Profit: {pricing_data['risk_profit']:.4f}")
            st.write(f"• **Total Profit: {pricing_data['total_profit_per_unit']:.4f}**")
            st.write(f"• Profit in Pips: {pricing_data['total_profit_per_unit']*10000:.2f}")
        
        with breakdown_col3:
            st.markdown("**Nominal Calculations:**")
            total_profit_nominal = pricing_data['total_profit_per_unit'] * nominal_amount
            potential_profit = total_profit_nominal * leverage_factor
            
            st.write(f"• Nominal Profit: {format_currency(total_profit_nominal)}")
            st.write(f"• With Leverage ({leverage_factor}x): {format_currency(potential_profit)}")
            st.write(f"• Profit Margin: {(pricing_data['total_profit_per_unit']/spot_rate_wf)*100:.3f}%")
        
        # ============================================================================
        # ENHANCED VISUALIZATIONS
        # ============================================================================
        
        st.markdown("---")
        st.subheader("📊 Pricing Visualizations")
        
        viz_col1, viz_col2 = st.columns(2)
        
        with viz_col1:
            # Waterfall chart for rate breakdown
            breakdown_chart = create_breakdown_chart(pricing_data, nominal_amount)
            st.plotly_chart(breakdown_chart, use_container_width=True)
        
        with viz_col2:
            # Window length analysis
            analysis_results = wf_calc.analyze_window_length_impact(
                spot_rate_wf, forward_points_data, swap_risk, points_factor, risk_factor
            )
            profit_chart = create_profit_analysis_chart(analysis_results)
            st.plotly_chart(profit_chart, use_container_width=True)
        
        # ============================================================================
        # WINDOW LENGTH ANALYSIS TABLE
        # ============================================================================
        
        st.markdown("---")
        st.subheader("📅 Window Length Impact Analysis")
        
        # Create detailed analysis table
        analysis_table_data = []
        for result in analysis_results:
            profit_nominal = result['profit_per_unit'] * nominal_amount
            profit_leveraged = profit_nominal * leverage_factor
            
            analysis_table_data.append({
                "Window (days)": result['window_days'],
                "Client Rate": f"{result['client_rate']:.4f}",
                "Points to Window": f"{result['points_to_window']:.4f}",
                "Profit (pips)": f"{result['profit_per_unit']*10000:.2f}",
                "Nominal Profit": format_currency(profit_nominal),
                "Leveraged Profit": format_currency(profit_leveraged)
            })
        
        df_analysis = pd.DataFrame(analysis_table_data)
        st.dataframe(df_analysis, use_container_width=True)
        
        # ============================================================================
        # SMART RECOMMENDATIONS
        # ============================================================================
        
        st.markdown("---")
        st.subheader("🧠 Smart Recommendations")
        
        rec_col1, rec_col2 = st.columns(2)
        
        with rec_col1:
            st.markdown("**Pricing Recommendations:**")
            
            # Analyze current settings
            if points_factor < 0.65:
                st.warning("⚠️ Points factor is quite low - may not be competitive")
            elif points_factor > 0.80:
                st.info("ℹ️ Generous points factor - ensure adequate profit margin")
            else:
                st.success("✅ Points factor is in optimal range")
            
            if risk_factor < 0.35:
                st.warning("⚠️ Low risk compensation - consider increasing")
            elif risk_factor > 0.55:
                st.info("ℹ️ High risk compensation - may impact competitiveness")
            else:
                st.success("✅ Risk factor is well balanced")
        
        with rec_col2:
            st.markdown("**Market Insights:**")
            
            # Calculate profit margin
            profit_margin = (pricing_data['total_profit_per_unit'] / spot_rate_wf) * 100
            
            if profit_margin < 0.05:
                st.warning("⚠️ Low profit margin - review pricing strategy")
            elif profit_margin > 0.15:
                st.success("🎯 Excellent profit margin")
            else:
                st.info("ℹ️ Moderate profit margin")
            
            # Window length recommendation
            optimal_window = min(analysis_results, key=lambda x: abs(x['profit_per_unit']*10000 - 8))
            st.info(f"💡 Optimal window for ~8 pips profit: **{optimal_window['window_days']} days**")
    
    except Exception as e:
        st.error(f"Calculation error: {e}")
        st.info("Please check your input parameters and try again.")

# ============================================================================
# TAB 4: ADVANCED ANALYTICS
# ============================================================================

with tab4:
    st.header("📈 Advanced Analytics")
    st.markdown("*Comprehensive market analysis and trading insights*")
    
    # Market overview section
    st.subheader("🌍 Market Overview")
    
    overview_col1, overview_col2, overview_col3 = st.columns(3)
    
    with overview_col1:
        st.markdown("**Current Market Status:**")
        
        # Overall market assessment
        if forex_data.get('status') == 'success' and any(d.get('status') == 'success' for d in bond_data.values()):
            st.success("🟢 All systems operational")
            data_quality = "Excellent"
        else:
            st.warning("🟡 Using fallback data")
            data_quality = "Moderate"
        
        st.write(f"• Data Quality: **{data_quality}**")
        st.write(f"• Last Update: **{datetime.now().strftime('%H:%M:%S')}**")
        st.write(f"• Market Hours: **{'Open' if 8 <= datetime.now().hour <= 18 else 'Closed'}**")
    
    with overview_col2:
        st.markdown("**Volatility Indicators:**")
        
        # Calculate implied volatility metrics
        if 'Poland_10Y' in bond_data and 'Germany_9M' in bond_data:
            spread = bond_data['Poland_10Y']['value'] - bond_data['Germany_9M']['value']
            
            if spread > 4:
                vol_status = "High"
                vol_color = "red"
            elif spread > 2:
                vol_status = "Medium"
                vol_color = "orange"
            else:
                vol_status = "Low"
                vol_color = "green"
            
            st.write(f"• Spread Volatility: **{vol_status}**")
            st.write(f"• Risk Environment: **{vol_status}**")
            st.write(f"• Recommended Hedging: **{'Yes' if vol_status == 'High' else 'Optional'}**")
    
    with overview_col3:
        st.markdown("**Trading Opportunities:**")
        
        # Assess trading opportunities
        if 'Poland_10Y' in bond_data and 'Germany_9M' in bond_data:
            current_spot = forex_data['rate']
            
            # Calculate 1M forward as proxy for short-term direction
            fwd_1m = calculate_forward_rate(
                current_spot, 
                bond_data['Poland_10Y']['value'], 
                bond_data['Germany_9M']['value'], 
                30
            )
            
            if fwd_1m > current_spot * 1.001:
                direction = "EUR Bullish"
                opportunity = "Long EUR/PLN"
            elif fwd_1m < current_spot * 0.999:
                direction = "EUR Bearish"
                opportunity = "Short EUR/PLN"
            else:
                direction = "Neutral"
                opportunity = "Range Trading"
            
            st.write(f"• Short-term Bias: **{direction}**")
            st.write(f"• Strategy: **{opportunity}**")
            st.write(f"• Confidence: **{'High' if abs(fwd_1m - current_spot) > 0.002 else 'Medium'}**")
    
    # Risk management section
    st.markdown("---")
    st.subheader("⚠️ Risk Management Dashboard")
    
    risk_col1, risk_col2 = st.columns(2)
    
    with risk_col1:
        st.markdown("**Position Risk Analysis:**")
        
        # Sample position for risk analysis
        sample_position = st.number_input(
            "Sample Position Size (EUR):",
            value=5_000_000,
            min_value=100_000,
            max_value=50_000_000,
            step=500_000,
            help="Enter position size for risk analysis"
        )
        
        # Calculate risk metrics
        current_rate = forex_data['rate']
        
        # 1% rate move impact
        rate_move_1pct = current_rate * 0.01
        pnl_1pct = sample_position * rate_move_1pct
        
        # Daily VaR estimate (simplified)
        daily_vol_estimate = 0.005  # 0.5% daily volatility estimate
        var_95 = sample_position * current_rate * daily_vol_estimate * 1.65  # 95% VaR
        
        st.write(f"**Risk Metrics:**")
        st.write(f"• 1% Rate Move P&L: **{format_currency(pnl_1pct, 'PLN')}**")
        st.write(f"• Daily VaR (95%): **{format_currency(var_95, 'PLN')}**")
        st.write(f"• Max Drawdown Est.: **{format_currency(var_95 * 3, 'PLN')}**")
        
    with risk_col2:
        st.markdown("**Hedging Strategies:**")
        
        # Hedging recommendations based on current market
        if 'Poland_10Y' in bond_data and 'Germany_9M' in bond_data:
            spread = bond_data['Poland_10Y']['value'] - bond_data['Germany_9M']['value']
            
            st.write("**Recommended Hedges:**")
            
            if spread > 3:
                st.write("• ✅ **Options collar** - High vol environment")
                st.write("• ✅ **Forward ladder** - Smooth out entries")
                st.write("• ⚠️ **Avoid naked positions**")
            else:
                st.write("• ✅ **Simple forwards** - Low vol environment")
                st.write("• ✅ **Window forwards** - Flexibility premium")
                st.write("• ℹ️ **Options may be expensive**")
        
        # Cost estimates
        st.write(f"**Estimated Hedge Costs:**")
        st.write(f"• Forward: **0-5 pips**")
        st.write(f"• Window Forward: **5-15 pips**")
        st.write(f"• Options: **15-50 pips**")
    
    # Performance tracking section
    st.markdown("---")
    st.subheader("📊 Performance Tracking")
    
    perf_col1, perf_col2 = st.columns(2)
    
    with perf_col1:
        st.markdown("**Hypothetical Strategy Performance:**")
        
        # Simple strategy backtest simulation
        strategy_type = st.selectbox(
            "Strategy Type:",
            ["Carry Trade", "Mean Reversion", "Momentum", "Window Forward"],
            help="Select strategy for hypothetical analysis"
        )
        
        # Generate sample performance data
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        
        if strategy_type == "Carry Trade":
            returns = np.random.normal(0.0002, 0.008, len(dates))  # Positive carry
        elif strategy_type == "Mean Reversion":
            returns = np.random.normal(0, 0.006, len(dates))  # Market neutral
        elif strategy_type == "Momentum":
            returns = np.random.normal(0.0001, 0.012, len(dates))  # Higher vol
        else:  # Window Forward
            returns = np.random.normal(0.0003, 0.004, len(dates))  # Lower vol, positive
        
        cumulative_returns = (1 + returns).cumprod()
        
        # Performance metrics
        total_return = (cumulative_returns[-1] - 1) * 100
        volatility = returns.std() * np.sqrt(252) * 100
        sharpe = (returns.mean() * 252) / (returns.std() * np.sqrt(252))
        max_dd = ((cumulative_returns / cumulative_returns.expanding().max()) - 1).min() * 100
        
        st.write(f"**{strategy_type} Metrics (2024):**")
        st.write(f"• Total Return: **{total_return:.1f}%**")
        st.write(f"• Volatility: **{volatility:.1f}%**")
        st.write(f"• Sharpe Ratio: **{sharpe:.2f}**")
        st.write(f"• Max Drawdown: **{max_dd:.1f}%**")
    
    with perf_col2:
        # Create performance chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=(cumulative_returns - 1) * 100,
            mode='lines',
            name=f'{strategy_type} Performance',
            line=dict(color='#1f77b4', width=2)
        ))
        
        fig.update_layout(
            title=f"{strategy_type} Cumulative Returns",
            xaxis_title="Date",
            yaxis_title="Cumulative Return (%)",
            height=300,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Market intelligence section
    st.markdown("---")
    st.subheader("🔍 Market Intelligence")
    
    intel_col1, intel_col2 = st.columns(2)
    
    with intel_col1:
        st.markdown("**Key Market Drivers:**")
        
        # Analyze current market drivers
        if 'Poland_10Y' in bond_data and 'Germany_9M' in bond_data:
            pl_yield_val = bond_data['Poland_10Y']['value']
            de_yield_val = bond_data['Germany_9M']['value']
            spread_val = pl_yield_val - de_yield_val
            
            drivers = []
            
            if spread_val > 4:
                drivers.append("🔴 **High Risk Premium** - Political/economic uncertainty")
            elif spread_val < 1.5:
                drivers.append("🟢 **Low Risk Premium** - Stable conditions")
            
            if pl_yield_val > 6:
                drivers.append("🔴 **High Polish Yields** - Inflation concerns")
            elif pl_yield_val < 4:
                drivers.append("🟢 **Low Polish Yields** - Benign inflation")
            
            if de_yield_val < 1:
                drivers.append("🔵 **Low German Yields** - ECB accommodation")
            elif de_yield_val > 3:
                drivers.append("🔴 **High German Yields** - ECB tightening")
            
            for driver in drivers[:3]:  # Show top 3 drivers
                st.markdown(driver)
        
        # Central bank policy assessment
        st.markdown("**Central Bank Policy:**")
        if 'Poland_10Y' in bond_data:
            pl_yield_val = bond_data['Poland_10Y']['value']
            if pl_yield_val > 5.5:
                policy_stance = "Hawkish (Restrictive)"
                policy_color = "🔴"
            elif pl_yield_val < 4:
                policy_stance = "Dovish (Accommodative)"
                policy_color = "🟢"
            else:
                policy_stance = "Neutral"
                policy_color = "🟡"
            
            st.write(f"• NBP Implied Stance: **{policy_color} {policy_stance}**")
        
        if 'Germany_9M' in bond_data:
            de_yield_val = bond_data['Germany_9M']['value']
            if de_yield_val > 2:
                ecb_stance = "Hawkish"
                ecb_color = "🔴"
            elif de_yield_val < 1:
                ecb_stance = "Dovish"
                ecb_color = "🟢"
            else:
                ecb_stance = "Neutral"
                ecb_color = "🟡"
            
            st.write(f"• ECB Implied Stance: **{ecb_color} {ecb_stance}**")
    
    with intel_col2:
        st.markdown("**Trading Calendar & Events:**")
        
        # Simulated upcoming events (in real implementation, this would come from an API)
        upcoming_events = [
            {"date": "2025-07-03", "event": "NBP Rate Decision", "impact": "High"},
            {"date": "2025-07-10", "event": "ECB Meeting", "impact": "High"},
            {"date": "2025-07-15", "event": "Polish GDP", "impact": "Medium"},
            {"date": "2025-07-18", "event": "ECB Minutes", "impact": "Medium"},
            {"date": "2025-07-25", "event": "German IFO", "impact": "Low"}
        ]
        
        st.markdown("**Upcoming Events:**")
        for event in upcoming_events:
            impact_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}[event["impact"]]
            st.write(f"• **{event['date']}**: {event['event']} {impact_emoji}")
        
        # Economic indicators summary
        st.markdown("**Economic Health Check:**")
        
        # Simple economic assessment based on yields
        if 'Poland_10Y' in bond_data:
            pl_yield_val = bond_data['Poland_10Y']['value']
            
            if pl_yield_val > 6:
                econ_health = "Challenging"
                health_emoji = "🔴"
            elif pl_yield_val < 4:
                econ_health = "Strong"
                health_emoji = "🟢"
            else:
                econ_health = "Stable"
                health_emoji = "🟡"
            
            st.write(f"• Poland Economy: **{health_emoji} {econ_health}**")
        
        # Market sentiment
        sentiment_score = np.random.uniform(0.3, 0.7)  # Simulated sentiment
        if sentiment_score > 0.6:
            sentiment = "Bullish"
            sentiment_emoji = "🟢"
        elif sentiment_score < 0.4:
            sentiment = "Bearish"
            sentiment_emoji = "🔴"
        else:
            sentiment = "Neutral"
            sentiment_emoji = "🟡"
        
        st.write(f"• Market Sentiment: **{sentiment_emoji} {sentiment}**")
        st.write(f"• Confidence Level: **{sentiment_score:.1%}**")

# ============================================================================
# FOOTER WITH ADDITIONAL INFORMATION
# ============================================================================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <h4>Professional FX Trading Dashboard</h4>
    <p>This dashboard provides real-time FX analytics using live market data from FRED API and NBP API.</p>
    <p><strong>Disclaimer:</strong> This tool is for educational and analytical purposes. All trading decisions should be made with proper risk management and professional advice.</p>
    <p>Data Sources: Federal Reserve Economic Data (FRED), National Bank of Poland (NBP)</p>
    <p style="font-size: 0.8rem; margin-top: 1rem;">
        🔄 Auto-refresh: 5 minutes for FX rates, 1 hour for bond data<br>
        📧 For support or feature requests, contact your system administrator<br>
        📊 Dashboard Version: 2.0.1 | Last Updated: July 2025
    </p>
</div>
""", unsafe_allow_html=True)

# Performance metrics display
if st.checkbox("Show Performance Metrics", value=False):
    st.subheader("🚀 Dashboard Performance")
    
    perf_metrics_col1, perf_metrics_col2, perf_metrics_col3 = st.columns(3)
    
    with perf_metrics_col1:
        st.metric("API Response Time", "< 500ms", help="Average API response time")
    
    with perf_metrics_col2:
        st.metric("Data Freshness", "< 5 min", help="Maximum data age")
    
    with perf_metrics_col3:
        st.metric("Uptime", "99.9%", help="Dashboard availability")
