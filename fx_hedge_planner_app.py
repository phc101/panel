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

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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

# ============================================================================
# FRED API CLIENT CLASS
# ============================================================================

class FREDAPIClient:
    """FRED API client for fetching economic data"""
    
    def __init__(self, api_key=FRED_API_KEY):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"
    
    def get_series_data(self, series_id, limit=1, sort_order='desc'):
        """Get latest data for a specific FRED series"""
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
            data = response.json()
            
            if 'observations' in data and data['observations']:
                latest = data['observations'][0]
                if latest['value'] != '.':
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
    
    def get_historical_data(self, series_id, start_date, end_date):
        """Get historical data from FRED API"""
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json',
            'start_date': start_date,
            'end_date': end_date,
            'frequency': 'd',
            'aggregation_method': 'avg'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=15)
            data = response.json()
            
            if 'observations' in data:
                df_data = []
                for obs in data['observations']:
                    if obs['value'] != '.':
                        df_data.append({
                            'date': pd.to_datetime(obs['date']),
                            'value': float(obs['value'])
                        })
                return pd.DataFrame(df_data).set_index('date')
            return pd.DataFrame()
        except Exception as e:
            st.warning(f"FRED historical data error for {series_id}: {e}")
            return pd.DataFrame()

# ============================================================================
# FX BOND SPREAD DASHBOARD CLASS
# ============================================================================

class FXBondSpreadDashboard:
    def __init__(self):
        self.fred_client = FREDAPIClient()
    
    def get_nbp_historical_data(self, start_date, end_date, currency='eur'):
        """Get historical currency/PLN from NBP API"""
        try:
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            url = f"https://api.nbp.pl/api/exchangerates/rates/a/{currency.lower()}/{start_str}/{end_str}/"
            response = requests.get(url, timeout=15)
            data = response.json()
            
            df_data = []
            for rate in data['rates']:
                df_data.append({
                    'date': pd.to_datetime(rate['effectiveDate']),
                    'value': rate['mid']
                })
            
            return pd.DataFrame(df_data).set_index('date')
        except Exception as e:
            st.warning(f"NBP historical data error for {currency.upper()}: {e}")
            return self.generate_sample_fx_data(start_date, end_date, currency)
    
    def calculate_predicted_fx_rate(self, pl_yield, foreign_yield, base_rate, currency='EUR'):
        """Calculate predicted FX rate based on bond yield spread"""
        yield_spread = pl_yield - foreign_yield
        # Different sensitivity for EUR vs USD
        spread_sensitivity = 0.15 if currency == 'EUR' else 0.18  # USD is slightly more sensitive
        predicted_rate = base_rate * (1 + yield_spread * spread_sensitivity / 100)
        return predicted_rate
    
    def generate_sample_fx_data(self, start_date, end_date, currency='eur'):
        """Generate sample currency/PLN data"""
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        np.random.seed(42)
        
        if currency.lower() == 'eur':
            base_rate = 4.24
            volatility = 0.003
        else:  # USD
            base_rate = 3.85
            volatility = 0.004  # USD typically more volatile vs PLN
        
        trend = np.linspace(0, 0.02, len(dates))
        noise = np.cumsum(np.random.randn(len(dates)) * volatility)
        values = base_rate + trend + noise
        return pd.DataFrame({'value': values}, index=dates)

# ============================================================================
# WINDOW FORWARD CALCULATOR CLASS
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
                "mid": mid_points
            }
        
        return points_data
    
    def calculate_forward_rate(self, spot_rate, domestic_yield, foreign_yield, days):
        """Calculate forward rate using bond yields"""
        T = days / 365.0
        forward_rate = spot_rate * (1 + domestic_yield/100 * T) / (1 + foreign_yield/100 * T)
        return forward_rate
    
    def calculate_months_to_period(self, days):
        """Calculate months from days"""
        return days / 30.0
    
    def calculate_closing_cost(self, ask_points, months_to_maturity):
        """Calculate closing cost: Ask * months to maturity"""
        return ask_points * months_to_maturity
    
    def calculate_swap_risk(self, closing_cost, points_to_window):
        """Calculate swap risk: closing cost - points to window"""
        return closing_cost - points_to_window
    
    def calculate_forward_client(self, spot_rate, forward_points_to_maturity, swap_risk, points_factor=0.70, risk_factor=0.4):
        """Calculate forward rate for client using correct dealer formula"""
        # Correct Formula: Spot + (Forward_Points_to_maturity × 0.70) - (Swap_Risk × 0.4-0.65)
        # We give client 70% of forward points but compensate for swap risk
        points_for_client = forward_points_to_maturity * points_factor
        swap_risk_compensation = swap_risk * risk_factor
        return spot_rate + points_for_client - swap_risk_compensation
    
    def calculate_forward_to_window(self, spot_rate, forward_points_to_maturity):
        """Calculate theoretical forward rate to maturity (full points)"""
        return spot_rate + forward_points_to_maturity
    
    def calculate_profit_to_window(self, fwd_theoretical, fwd_client):
        """Calculate dealer profit margin"""
        # Profit is the difference between theoretical forward and client rate
        return fwd_theoretical - fwd_client
    
    def calculate_profit_percentage(self, profit_absolute, fwd_client):
        """Calculate profit as percentage of client rate"""
        return (profit_absolute / fwd_client) * 100
    
    def calculate_net_worst(self, profit_to_window, swap_profit=0, swap_risk_calc=0):
        """Calculate net worst case scenario"""
        return profit_to_window + swap_profit + swap_risk_calc
    
    def calculate_net_worst_nominal(self, net_worst, nominal_amount):
        """Calculate net worst in nominal terms"""
        return nominal_amount * net_worst
    
    def calculate_potential_profit(self, net_worst_nominal, leverage_factor=1.5):
        """Calculate potential profit with leverage"""
        return net_worst_nominal * leverage_factor

# ============================================================================
# CALCULATION FUNCTIONS
# ============================================================================

def calculate_forward_rate(spot_rate, domestic_yield, foreign_yield, days):
    """Calculate forward rate using bond yields"""
    T = days / 365.0
    forward_rate = spot_rate * (1 + domestic_yield/100 * T) / (1 + foreign_yield/100 * T)
    return forward_rate

def calculate_convergence_days(df, actual_col, predicted_col, tolerance=0.001):
    """
    Calculate how many days it takes for actual price to reach predicted price
    
    Parameters:
    - df: DataFrame with actual and predicted prices
    - actual_col: column name for actual prices
    - predicted_col: column name for predicted prices  
    - tolerance: acceptable difference (default 0.1%)
    
    Returns:
    - dict with convergence statistics
    """
    convergence_events = []
    
    for i in range(1, len(df)):
        current_actual = df[actual_col].iloc[i]
        current_predicted = df[predicted_col].iloc[i]
        
        # Look back to find when prediction was made
        for lookback in range(1, min(i+1, 30)):  # Max 30 days lookback
            past_predicted = df[predicted_col].iloc[i-lookback]
            
            # Check if current actual price is within tolerance of past prediction
            price_diff = abs(current_actual - past_predicted) / past_predicted
            
            if price_diff <= tolerance:
                convergence_events.append({
                    'date': df.index[i],
                    'days_to_convergence': lookback,
                    'predicted_price': past_predicted,
                    'actual_price': current_actual,
                    'accuracy': (1 - price_diff) * 100
                })
                break
    
    if convergence_events:
        avg_days = np.mean([event['days_to_convergence'] for event in convergence_events])
        median_days = np.median([event['days_to_convergence'] for event in convergence_events])
        avg_accuracy = np.mean([event['accuracy'] for event in convergence_events])
        convergence_rate = len(convergence_events) / len(df) * 100
        
        return {
            'avg_convergence_days': avg_days,
            'median_convergence_days': median_days,
            'avg_accuracy': avg_accuracy,
            'convergence_rate': convergence_rate,
            'total_events': len(convergence_events),
            'events': convergence_events
        }
    else:
        return {
            'avg_convergence_days': None,
            'median_convergence_days': None,
            'avg_accuracy': None,
            'convergence_rate': 0,
            'total_events': 0,
            'events': []
        }

def calculate_forward_points(spot_rate, forward_rate):
    """Calculate forward points in pips"""
    return (forward_rate - spot_rate) * 10000

# ============================================================================
# CACHED DATA FUNCTIONS
# ============================================================================

@st.cache_data(ttl=3600)
def get_fred_bond_data():
    """Get government bond yields from FRED"""
    fred_client = FREDAPIClient()
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
        de_10y = data['Germany_10Y']['value']
        data['Germany_9M'] = {
            'value': max(de_10y - 0.25, 0.1),
            'date': data['Germany_10Y']['date'],
            'series_id': 'Interpolated',
            'source': 'FRED + Interpolation'
        }
    
    return data

@st.cache_data(ttl=3600)
def get_fred_rates_data():
    """Get interest rate benchmarks from FRED"""
    fred_client = FREDAPIClient()
    rates_series = {
        'EURIBOR_3M': 'EUR3MTD156N',
        'Fed_Funds': 'FEDFUNDS',
        'ECB_Rate': 'IRSTCB01EZM156N'
    }
    return fred_client.get_multiple_series(rates_series)

@st.cache_data(ttl=300)
def get_eur_pln_rate():
    """Get current EUR/PLN from NBP API"""
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

@st.cache_data(ttl=300)
def get_usd_pln_rate():
    """Get current USD/PLN from NBP API"""
    try:
        url = "https://api.nbp.pl/api/exchangerates/rates/a/usd/"
        response = requests.get(url, timeout=10)
        data = response.json()
        return {
            'rate': data['rates'][0]['mid'],
            'date': data['rates'][0]['effectiveDate'],
            'source': 'NBP'
        }
    except Exception as e:
        st.warning(f"NBP API error for USD: {e}")
        return {'rate': 3.85, 'date': 'Fallback', 'source': 'Estimated'}

# ============================================================================
# MAIN APPLICATION
# ============================================================================

# Header
st.markdown("""
<div style="display: flex; align-items: center; margin-bottom: 2rem;">
    <div style="background: linear-gradient(45deg, #667eea, #764ba2); width: 60px; height: 60px; border-radius: 10px; margin-right: 1rem; display: flex; align-items: center; justify-content: center;">
        <span style="font-size: 2rem;">💱</span>
    </div>
    <h1 style="margin: 0; color: #2c3e50;">Professional FX Trading Dashboard</h1>
</div>
""", unsafe_allow_html=True)

st.markdown("*Advanced Forward Rate Calculator & Bond Spread Analytics*")

# Load shared data
with st.spinner("📡 Loading market data..."):
    bond_data = get_fred_bond_data()
    rates_data = get_fred_rates_data()
    forex_data = get_eur_pln_rate()
    usd_forex_data = get_usd_pln_rate()

# Main tabs
tab1, tab2, tab3 = st.tabs(["🧮 Forward Rate Calculator", "📊 Bond Spread Dashboard", "💼 Window Forward Calculator"])

# ============================================================================
# TAB 1: FORWARD RATE CALCULATOR
# ============================================================================

with tab1:
    st.header("🧮 Forward Rate Calculator with FRED API")
    
    # Current market data display
    st.subheader("📊 Current Market Data")
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
            st.metric("Poland 10Y Bond", "N/A", help="Data not available")
    
    with col3:
        if 'Germany_9M' in bond_data:
            de_yield = bond_data['Germany_9M']['value']
            st.metric(
                "Germany 9M Bond", 
                f"{de_yield:.2f}%",
                help="Interpolated from 10Y German bond"
            )
        else:
            st.metric("Germany Bond", "N/A", help="Data not available")
    
    with col4:
        if 'Poland_10Y' in bond_data and 'Germany_9M' in bond_data:
            spread = bond_data['Poland_10Y']['value'] - bond_data['Germany_9M']['value']
            st.metric(
                "PL-DE Spread", 
                f"{spread:.2f} pp",
                help="Poland 10Y minus Germany 9M"
            )
    
    # Calculator interface
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("⚙️ Input Parameters")
        
        # Spot rate
        spot_rate = st.number_input(
            "EUR/PLN Spot Rate:",
            value=forex_data['rate'],
            min_value=3.0,
            max_value=6.0,
            step=0.01,
            format="%.4f"
        )
        
        # Bond yields
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
                format="%.2f"
            )
        
        with col_de:
            default_de = bond_data['Germany_9M']['value'] if 'Germany_9M' in bond_data else 2.35
            de_yield = st.number_input(
                "Germany Yield (%):",
                value=default_de,
                min_value=-2.0,
                max_value=10.0,
                step=0.01,
                format="%.2f"
            )
        
        # Time period
        st.write("**Forward Period:**")
        period_choice = st.selectbox(
            "Select Period:",
            ["1M", "3M", "6M", "9M", "1Y", "2Y", "Custom Days"]
        )
        
        if period_choice == "Custom Days":
            days = st.number_input("Days:", value=365, min_value=1, max_value=730, help="Maximum 2 years")
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
    
    # Forward curve table
    st.markdown("---")
    st.header("📅 Forward Rate Table (Max 2 Years)")
    
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
            "Spread vs Spot": f"{(fw_rate - spot_rate):.4f}"
        })
    
    df_forward = pd.DataFrame(forward_table_data)
    st.dataframe(df_forward, use_container_width=True)
    
    # Forward curve chart
    st.markdown("---")
    st.header("📊 Forward Curve Visualization")
    
    # Generate curve data
    curve_days = np.linspace(30, 730, 100)
    curve_forwards = [calculate_forward_rate(spot_rate, pl_yield, de_yield, d) for d in curve_days]
    curve_points = [calculate_forward_points(spot_rate, fw) for fw in curve_forwards]
    
    # Create chart
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("EUR/PLN Forward Curve", "Forward Points"),
        vertical_spacing=0.15,
        row_heights=[0.65, 0.35]
    )
    
    # Forward curve
    fig.add_trace(go.Scatter(
        x=curve_days,
        y=curve_forwards,
        mode='lines',
        name='Forward Curve',
        line=dict(color='#1f77b4', width=3),
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
        marker=dict(color='orange', size=12),
        text=period_names,
        textposition="top center"
    ), row=1, col=1)
    
    # Forward points
    fig.add_trace(go.Scatter(
        x=curve_days,
        y=curve_points,
        mode='lines',
        name='Forward Points',
        line=dict(color='green', width=3),
        showlegend=False
    ), row=2, col=1)
    
    fig.add_hline(y=0, line_dash="dot", line_color="gray", row=2)
    
    fig.update_layout(
        title="EUR/PLN Forward Analysis - Based on FRED Bond Data",
        height=600,
        hovermode='closest'
    )
    
    fig.update_xaxes(title_text="Days to Maturity", row=2, col=1)
    fig.update_yaxes(title_text="EUR/PLN Rate", row=1, col=1)
    fig.update_yaxes(title_text="Forward Points (pips)", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# TAB 2: BOND SPREAD DASHBOARD (SIMPLIFIED)
# ============================================================================

with tab2:
    st.header("📊 FX Bond Spread Dashboard")
    
    # Initialize dashboard
    dashboard = FXBondSpreadDashboard()
    
    # Generate historical data (6 months)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)
    
    # Simplified EUR/PLN section
    st.subheader("🇪🇺 EUR/PLN Bond Spread Analytics")
    
    try:
        # Get historical EUR/PLN
        eur_pln_data = dashboard.get_nbp_historical_data(start_date, end_date, 'eur')
        
        # Get bond yields
        pl_bonds = dashboard.fred_client.get_historical_data('IRLTLT01PLM156N', 
                                                           start_date.strftime('%Y-%m-%d'), 
                                                           end_date.strftime('%Y-%m-%d'))
        de_bonds = dashboard.fred_client.get_historical_data('IRLTLT01DEM156N', 
                                                           start_date.strftime('%Y-%m-%d'), 
                                                           end_date.strftime('%Y-%m-%d'))
        
        if not eur_pln_data.empty and not pl_bonds.empty and not de_bonds.empty:
            # Combine real data
            df = eur_pln_data.copy()
            df.columns = ['actual_eur_pln']
            df = df.join(pl_bonds.rename(columns={'value': 'pl_yield'}), how='left')
            df = df.join(de_bonds.rename(columns={'value': 'de_yield'}), how='left')
            df = df.fillna(method='ffill').fillna(method='bfill')
            
            # Calculate predicted rates
            df['predicted_eur_pln'] = df.apply(
                lambda row: dashboard.calculate_predicted_fx_rate(
                    row['pl_yield'], row['de_yield'], df['actual_eur_pln'].iloc[0], 'EUR'
                ), axis=1
            )
            df['yield_spread'] = df['pl_yield'] - df['de_yield']
            st.success("✅ Using real EUR market data")
        else:
            raise Exception("Insufficient EUR data")
            
    except Exception as e:
        st.info("📊 Using sample EUR data for demonstration")
        # Generate sample data
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        np.random.seed(42)
        
        # Sample EUR/PLN
        base_rate = 4.24
        trend = np.linspace(0, 0.02, len(dates))
        noise = np.cumsum(np.random.randn(len(dates)) * 0.003)
        actual_eur_pln = base_rate + trend + noise
        
        # Sample yields
        pl_yields = 5.7 + np.cumsum(np.random.randn(len(dates)) * 0.01)
        de_yields = 2.2 + np.cumsum(np.random.randn(len(dates)) * 0.008)
        
        predicted_eur_pln = []
        for i in range(len(dates)):
            pred_rate = dashboard.calculate_predicted_fx_rate(pl_yields[i], de_yields[i], base_rate, 'EUR')
            predicted_eur_pln.append(pred_rate)
        
        df = pd.DataFrame({
            'actual_eur_pln': actual_eur_pln,
            'predicted_eur_pln': predicted_eur_pln,
            'pl_yield': pl_yields,
            'de_yield': de_yields,
            'yield_spread': pl_yields - de_yields
        }, index=dates)

    # Current values
    current_actual = df['actual_eur_pln'].iloc[-1]
    current_predicted = df['predicted_eur_pln'].iloc[-1]
    difference_pct = ((current_predicted - current_actual) / current_actual) * 100
    current_spread = df['yield_spread'].iloc[-1]
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Actual EUR/PLN", f"{current_actual:.4f}")
    with col2:
        st.metric("Predicted EUR/PLN", f"{current_predicted:.4f}")
    with col3:
        st.metric("% Difference", f"{difference_pct:.2f}%")
    with col4:
        st.metric("Current Spread", f"{current_spread:.2f}pp")

# ============================================================================  
# TAB 3: WINDOW FORWARD DEALER CALCULATOR
# ============================================================================

with tab3:
    st.header("💼 Window Forward Dealer Calculator")
    st.markdown("*Professional window forward pricing tool using live bond spreads*")
    
    # Initialize calculator with FRED client
    wf_calc = WindowForwardCalculator(FREDAPIClient())
    
    # ============================================================================
    # CONFIGURATION SECTION
    # ============================================================================
    
    st.subheader("⚙️ Configuration Parameters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        spot_rate_wf = st.number_input(
            "EUR/PLN Spot Rate:",
            value=forex_data['rate'],
            min_value=3.0,
            max_value=6.0,
            step=0.0001,
            format="%.4f",
            key="wf_spot"
        )
    
    with col2:
        window_days = st.number_input(
            "Window Length (days):",
            value=90,
            min_value=30,
            max_value=365,
            step=1,
            key="wf_window"
        )
    
    with col3:
        nominal_amount = st.number_input(
            "Nominal Amount (EUR):",
            value=2_500_000,
            min_value=100_000,
            max_value=100_000_000,
            step=100_000,
            format="%d",
            key="wf_nominal"
        )
    
    with col4:
        bid_ask_spread = st.number_input(
            "Bid-Ask Spread (points):",
            value=0.002,
            min_value=0.001,
            max_value=0.010,
            step=0.001,
            format="%.3f",
            key="wf_spread"
        )
    
    # Get current bond yields for forward points generation
    default_pl_yield = bond_data['Poland_10Y']['value'] if 'Poland_10Y' in bond_data else 5.70
    default_de_yield = bond_data['Germany_9M']['value'] if 'Germany_9M' in bond_data else 2.35
    
    # ============================================================================
    # LIVE FORWARD POINTS GENERATION
    # ============================================================================
    
    st.markdown("---")
    st.subheader("📊 Live Forward Points (Generated from Bond Spreads)")
    
    # Generate forward points from current bond spreads
    forward_points_data = wf_calc.generate_forward_points_from_spreads(
        spot_rate_wf, 
        default_pl_yield, 
        default_de_yield, 
        bid_ask_spread
    )
    
    # Display current spread info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"🇵🇱 Poland 10Y: **{default_pl_yield:.2f}%**")
    with col2:
        st.info(f"🇩🇪 Germany 10Y: **{default_de_yield:.2f}%**")
    with col3:
        st.info(f"📊 Current Spread: **{(default_pl_yield - default_de_yield):.2f}pp**")
    
    # ============================================================================
    # CALCULATIONS SECTION
    # ============================================================================
    
    st.subheader("💰 Window Forward Pricing Table")
    
    # Calculate months for window
    months_to_window = wf_calc.calculate_months_to_period(window_days)
    
    # Prepare calculation results
    results = []
    
    for tenor in wf_calc.tenors:
        if tenor in forward_points_data:
            data = forward_points_data[tenor]
            tenor_months = wf_calc.tenor_months[tenor]
            
            # Calculate components using live data
            points_to_window = data["bid"]  # Using bid as points to window
            closing_cost = wf_calc.calculate_closing_cost(data["ask"], tenor_months)
            swap_risk = wf_calc.calculate_swap_risk(closing_cost, points_to_window)
            
            # Main calculations with corrected dealer logic
            window_factor = 0.75  # Can be made configurable
            risk_factor = 0.4     # Can be made configurable
            
            # Calculate forward rates using corrected logic
            fwd_to_window = wf_calc.calculate_forward_to_window(spot_rate_wf, points_to_window)  # Clean forward
            fwd_client = wf_calc.calculate_forward_client(spot_rate_wf, points_to_window, swap_risk, window_factor, risk_factor)  # Client rate
            
            # Calculate profits
            profit_absolute = wf_calc.calculate_profit_to_window(fwd_to_window, fwd_client)  # Absolute profit
            profit_percentage = wf_calc.calculate_profit_percentage(profit_absolute, fwd_client)  # Profit %
            
            # Risk calculations
            net_worst = profit_absolute  # Simplified - could add other risk factors
            net_worst_nominal = wf_calc.calculate_net_worst_nominal(profit_absolute, nominal_amount)
            potential_profit = wf_calc.calculate_potential_profit(net_worst_nominal)
            
            results.append({
                "Tenor": tenor,
                "Bid Points": data["bid"],
                "Ask Points": data["ask"],
                "Mid Points": data["mid"],
                "FWD Client": fwd_client,
                "FWD to Window": fwd_to_window,
                "Profit (Absolute)": profit_absolute,
                "Profit %": profit_percentage,
                "Closing Cost": closing_cost,
                "Swap Risk": swap_risk,
                "Net Worst": profit_absolute,
                "Net Worst (EUR)": net_worst_nominal,
                "Potential Profit (EUR)": potential_profit
            })
    
    # Display results table
    if results:
        df_results = pd.DataFrame(results)
        
        # Format columns for better display
        formatted_df = df_results.copy()
        formatted_df["Bid Points"] = formatted_df["Bid Points"].apply(lambda x: f"{x:.5f}")
        formatted_df["Ask Points"] = formatted_df["Ask Points"].apply(lambda x: f"{x:.5f}")
        formatted_df["Mid Points"] = formatted_df["Mid Points"].apply(lambda x: f"{x:.5f}")
        formatted_df["FWD Client"] = formatted_df["FWD Client"].apply(lambda x: f"{x:.4f}")
        formatted_df["FWD to Window"] = formatted_df["FWD to Window"].apply(lambda x: f"{x:.4f}")
        formatted_df["Profit (Absolute)"] = formatted_df["Profit (Absolute)"].apply(lambda x: f"{x:.5f}")
        formatted_df["Profit %"] = formatted_df["Profit %"].apply(lambda x: f"{x:.3f}%")
        formatted_df["Closing Cost"] = formatted_df["Closing Cost"].apply(lambda x: f"{x:.5f}")
        formatted_df["Swap Risk"] = formatted_df["Swap Risk"].apply(lambda x: f"{x:.5f}")
        formatted_df["Net Worst"] = formatted_df["Net Worst"].apply(lambda x: f"{x:.5f}")
        formatted_df["Net Worst (EUR)"] = formatted_df["Net Worst (EUR)"].apply(lambda x: f"{x:,.0f}")
        formatted_df["Potential Profit (EUR)"] = formatted_df["Potential Profit (EUR)"].apply(lambda x: f"{x:,.0f}")
        
        st.dataframe(formatted_df, use_container_width=True)
        
        # ============================================================================
        # VISUALIZATIONS
        # ============================================================================
        
        st.markdown("---")
        st.subheader("📈 Window Forward Analysis Charts")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Profit margin chart
            fig_profit = go.Figure()
            fig_profit.add_trace(go.Bar(
                x=df_results["Tenor"],
                y=df_results["Profit %"],
                name="Profit Margin %",
                marker_color='lightgreen',
                text=df_results["Profit %"].apply(lambda x: f"{x:.3f}%"),
                textposition='auto'
            ))
            
            fig_profit.update_layout(
                title="Dealer Profit Margin by Tenor",
                xaxis_title="Tenor",
                yaxis_title="Profit Margin (%)",
                height=400,
                xaxis_tickangle=-45
            )
            
            st.plotly_chart(fig_profit, use_container_width=True)
        
        with col2:
            # Net worst nominal chart
            fig_risk = go.Figure()
            
            colors = ['red' if x < 0 else 'green' for x in df_results["Net Worst (EUR)"]]
            
            fig_risk.add_trace(go.Bar(
                x=df_results["Tenor"],
                y=df_results["Net Worst (EUR)"],
                name="Net Worst (EUR)",
                marker_color=colors,
                text=df_results["Net Worst (EUR)"].apply(lambda x: f"{x:,.0f}"),
                textposition='auto'
            ))
            
            fig_risk.update_layout(
                title="Net Worst Case Scenario (EUR)",
                xaxis_title="Tenor",
                yaxis_title="Net Worst (EUR)",
                height=400,
                xaxis_tickangle=-45
            )
            
            st.plotly_chart(fig_risk, use_container_width=True)
        
        # Forward rates comparison chart
        st.subheader("💱 Forward Rates Comparison")
        
        fig_fwd = go.Figure()
        
        fig_fwd.add_trace(go.Scatter(
            x=df_results["Tenor"],
            y=df_results["FWD Client"],
            mode='lines+markers',
            name='Forward Client Rate',
            line=dict(color='blue', width=3),
            marker=dict(size=8)
        ))
        
        fig_fwd.add_trace(go.Scatter(
            x=df_results["Tenor"],
            y=df_results["FWD to Window"],
            mode='lines+markers',
            name='Forward to Window Rate',
            line=dict(color='red', width=3),
            marker=dict(size=8)
        ))
        
        # Add spot rate line
        fig_fwd.add_hline(
            y=spot_rate_wf,
            line_dash="dash",
            line_color="green",
            annotation_text=f"Spot Rate: {spot_rate_wf:.4f}"
        )
        
        fig_fwd.update_layout(
            title="Forward Rates: Clean vs Client (Corrected Dealer Logic)",
            xaxis_title="Tenor",
            yaxis_title="EUR/PLN Rate",
            height=500,
            xaxis_tickangle=-45,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_fwd, use_container_width=True)
        
        # ============================================================================
        # RISK ANALYSIS SECTION
        # ============================================================================
        
        st.markdown("---")
        st.subheader("⚠️ Risk Analysis Dashboard")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_exposure = nominal_amount * len(results)
        avg_profit_margin = df_results["Profit %"].mean()
        total_net_worst = df_results["Net Worst (EUR)"].sum()
        best_tenor = df_results.loc[df_results["Profit %"].idxmax(), "Tenor"]
        
        with col1:
            st.metric(
                "Total Exposure",
                f"€{total_exposure:,.0f}",
                help="Total nominal exposure across all tenors"
            )
        
        with col2:
            st.metric(
                "Avg Profit Margin",
                f"{avg_profit_margin:.3f}%",
                help="Average profit margin across all tenors"
            )
        
        with col3:
            st.metric(
                "Total Net Worst",
                f"€{total_net_worst:,.0f}",
                help="Sum of all net worst case scenarios"
            )
        
        with col4:
            st.metric(
                "Best Tenor",
                best_tenor,
                help="Tenor with highest profit margin"
            )
        
        # ============================================================================
        # SCENARIO ANALYSIS
        # ============================================================================
        
        st.markdown("---")
        st.subheader("🎯 Bond Spread Scenario Analysis")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            spread_change = st.slider(
                "Bond Spread Change (bp):",
                min_value=-100,
                max_value=100,
                value=0,
                step=5,
                key="scenario_spread",
                help="Change in PL-DE bond spread in basis points"
            )
        
        with col2:
            spot_change = st.slider(
                "Spot Rate Change (%):",
                min_value=-5.0,
                max_value=5.0,
                value=0.0,
                step=0.1,
                key="scenario_spot_wf"
            )
        
        with col3:
            nominal_change = st.slider(
                "Nominal Change (%):",
                min_value=-50,
                max_value=100,
                value=0,
                step=10,
                key="scenario_nominal"
            )
        
        # Calculate scenario results
        if st.button("🔄 Calculate Scenario Impact", key="calc_scenario_wf"):
            # Adjust parameters for scenario
            scenario_spot = spot_rate_wf * (1 + spot_change / 100)
            scenario_pl_yield = default_pl_yield + (spread_change / 10000)  # Convert bp to percentage
            scenario_de_yield = default_de_yield  # Keep German yield constant
            scenario_nominal = nominal_amount * (1 + nominal_change / 100)
            
            # Generate new forward points with scenario parameters
            scenario_points_data = wf_calc.generate_forward_points_from_spreads(
                scenario_spot, 
                scenario_pl_yield, 
                scenario_de_yield, 
                bid_ask_spread
            )
            
            scenario_results = []
            
            for i, result in enumerate(results):
                tenor = result["Tenor"]
                if tenor in scenario_points_data:
                    scenario_data = scenario_points_data[tenor]
                    tenor_months = wf_calc.tenor_months[tenor]
                    
                    # Recalculate with scenario parameters
                    points_to_window = scenario_data["bid"]
                    closing_cost = wf_calc.calculate_closing_cost(scenario_data["ask"], tenor_months)
                    swap_risk = wf_calc.calculate_swap_risk(closing_cost, points_to_window)
                    fwd_to_window = wf_calc.calculate_forward_to_window(scenario_spot, points_to_window)
                    fwd_client = wf_calc.calculate_forward_client(scenario_spot, points_to_window, swap_risk)
                    profit_absolute = wf_calc.calculate_profit_to_window(fwd_to_window, fwd_client)
                    profit_percentage = wf_calc.calculate_profit_percentage(profit_absolute, fwd_client)
                    net_worst_nominal = wf_calc.calculate_net_worst_nominal(profit_absolute, scenario_nominal)
                    
                    scenario_results.append({
                        "Tenor": tenor,
                        "Original Net Worst": result["Net Worst (EUR)"],
                        "Scenario Net Worst": net_worst_nominal,
                        "Impact": net_worst_nominal - result["Net Worst (EUR)"],
                        "Original Profit %": result["Profit %"],
                        "Scenario Profit %": profit_percentage,
                        "Profit Impact": profit_percentage - result["Profit %"]
                    })
            
            # Display scenario results
            if scenario_results:
                scenario_df = pd.DataFrame(scenario_results)
                
                # Impact summary
                total_impact = scenario_df["Impact"].sum()
                avg_profit_impact = scenario_df["Profit Impact"].mean()
                impact_color = "🟢" if total_impact >= 0 else "🔴"
                profit_impact_color = "🟢" if avg_profit_impact >= 0 else "🔴"
                
                st.markdown(f"""
                **Scenario Impact Summary:**
                - {impact_color} **Total Portfolio Impact**: €{total_impact:,.0f}
                - {profit_impact_color} **Average Profit Impact**: {avg_profit_impact:+.3f}%
                - **Scenario Parameters**: 
                  - Bond Spread: {spread_change:+}bp
                  - Spot Rate: {spot_change:+.1f}%
                  - Nominal: {nominal_change:+}%
                - **New Bond Spread**: {(scenario_pl_yield - scenario_de_yield):.2f}pp (was {(default_pl_yield - default_de_yield):.2f}pp)
                """)
        
        # ============================================================================
        # DEALER INSIGHTS
        # ============================================================================
        
        st.markdown("---")
        st.subheader("💡 Dealer Insights & Recommendations")
        
        # Generate insights based on calculations
        insights = []
        
        # Profitability insights
        profitable_tenors = df_results[df_results["Profit %"] > 0]
        if len(profitable_tenors) > 0:
            best_margin = profitable_tenors["Profit %"].max()
            best_tenor_name = profitable_tenors.loc[profitable_tenors["Profit %"].idxmax(), "Tenor"]
            insights.append(f"🎯 **Best Margin**: {best_tenor_name} offers the highest profit margin at {best_margin:.3f}%")
        
        # Risk insights
        risky_tenors = df_results[df_results["Net Worst (EUR)"] < 0]
        if len(risky_tenors) > 0:
            worst_risk = risky_tenors["Net Worst (EUR)"].min()
            worst_tenor_name = risky_tenors.loc[risky_tenors["Net Worst (EUR)"].idxmin(), "Tenor"]
            insights.append(f"⚠️ **Highest Risk**: {worst_tenor_name} has the worst case scenario of €{worst_risk:,.0f}")
        
        # Bond spread insights
        current_spread_bp = (default_pl_yield - default_de_yield) * 100
        insights.append(f"📊 **Current Bond Spread**: {current_spread_bp:.0f}bp provides {avg_profit_margin:.3f}% average margin")
        
        # Display insights
        for insight in insights:
            st.markdown(insight)
        
        # Trading recommendations
        st.markdown("### 📋 Trading Recommendations:")
        
        if len(profitable_tenors) > 0:
            st.success(f"✅ **RECOMMEND**: Focus on {best_tenor_name} for optimal profitability")
        
        if len(risky_tenors) > 0:
            st.warning(f"⚠️ **CAUTION**: Monitor {worst_tenor_name} closely due to negative net worst scenario")
        
        if total_net_worst > 0:
            st.info(f"💼 **PORTFOLIO**: Overall positive outlook with €{total_net_worst:,.0f} total net worst")
        else:
            st.error(f"🚨 **PORTFOLIO**: Overall negative exposure of €{total_net_worst:,.0f} - consider hedging")

# ============================================================================
# SHARED CONTROLS AND FOOTER
# ============================================================================

st.markdown("---")

# Refresh and info controls
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("🔄 Refresh All Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with col2:
    if st.button("📊 FRED Series Info", use_container_width=True):
        with st.expander("📋 FRED Series Used", expanded=True):
            st.markdown("""
            **Bond Yields:**
            - Poland 10Y: `IRLTLT01PLM156N`
            - Germany 10Y: `IRLTLT01DEM156N`
            - US 10Y: `DGS10`
            - US 2Y: `DGS2`
            
            **Interest Rates:**
            - EURIBOR 3M: `EUR3MTD156N`
            - Fed Funds: `FEDFUNDS`
            - ECB Rate: `IRSTCB01EZM156N`
            
            **FX Rates:**
            - EUR/PLN: NBP API
            - USD/PLN: NBP API
            """)

with col3:
    if st.button("ℹ️ Methodology", use_container_width=True):
        with st.expander("🔬 Calculation Methods", expanded=True):
            st.markdown("""
            **Forward Rate Formula:**
            ```
            Forward = Spot × (1 + r_PL × T) / (1 + r_Foreign × T)
            ```
            
            **Window Forward Dealer Formula (Corrected):**
            ```
            FWD_Clean = Spot + Forward_Points
            FWD_Client = FWD_Clean - Cost_Adjustments
            Dealer_Profit = FWD_Clean - FWD_Client
            ```
            
            **Forward Points Generation:**
            - Generated from live bond spreads (PL vs DE)
            - Bid = Theoretical_Points - (Spread/2)
            - Ask = Theoretical_Points + (Spread/2)
            
            **Data Sources:**
            - **FX Rates**: NBP API (Polish Central Bank)
            - **Bond Yields**: FRED API (Federal Reserve Economic Data)
            - **Forward Points**: Live generation from spreads
            
            **Update Frequency:**
            - Bond data: 1 hour cache
            - FX data: 5 minute cache
            - Forward points: Real-time calculation
            """)

# Performance note
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: gray; font-size: 0.8em; padding: 1rem; border-top: 1px solid #eee;'>
    💱 <strong>Professional FX Trading Dashboard</strong><br>
    📊 Real-time data: NBP API, FRED API | 🧮 Forward Calculator | 📈 Bond Spread Analytics | 💼 Window Forward Calculator<br>
    ⏰ Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
    🔗 <a href="https://fred.stlouisfed.org/docs/api/" target="_blank">FRED API Docs</a><br>
    ⚠️ <em>For educational and analytical purposes - not financial advice</em>
    </div>
    """, 
    unsafe_allow_html=True
)
