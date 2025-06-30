import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta

# FRED API Configuration
FRED_API_KEY = "50813725c0bfaadbc44a16ef28b0e894"  # Replace with your API key

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
tab1, tab2 = st.tabs(["🧮 Forward Rate Calculator", "📊 Bond Spread Dashboard (EUR/PLN + USD/PLN)"])

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
# TAB 2: BOND SPREAD DASHBOARD (COMPLETE FIXED VERSION)
# ============================================================================

with tab2:
    st.header("📊 FX Bond Spread Dashboard")
    
    # Initialize dashboard
    dashboard = FXBondSpreadDashboard()
    
    # Generate historical data (6 months)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)
    
    # ============================================================================
    # EUR/PLN SECTION
    # ============================================================================
    
    st.subheader("🇪🇺 EUR/PLN Bond Spread Analytics")
    
    with st.spinner("📊 Loading EUR historical data..."):
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
    
    # Latest FX vs Predicted metrics
    st.subheader("💰 Latest EUR/PLN vs Predicted")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="rate-label">Actual EUR/PLN</div>
            <div class="actual-rate">{current_actual:.4f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="rate-label">Predicted EUR/PLN</div>
            <div class="predicted-rate">{current_predicted:.4f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        difference_color = "#28a745" if abs(difference_pct) < 1 else "#dc3545"
        st.markdown(f"""
        <div class="metric-card">
            <div class="rate-label">% Difference</div>
            <div class="difference" style="color: {difference_color}">{difference_pct:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="rate-label">Current Spread</div>
            <div class="difference">{current_spread:.2f}pp</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Charts side by side with better visibility
    st.subheader("📈 EUR/PLN Historical Analysis (Last 6 Months)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**EUR/PLN: Historical vs Predicted**")
        
        # Create dual-axis subplot
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Actual EUR/PLN (left axis)
        fig1.add_trace(go.Scatter(
            x=df.index,
            y=df['actual_eur_pln'],
            mode='lines',
            name='EUR/PLN (Actual)',
            line=dict(color='#2E86AB', width=2),
            hovertemplate='Actual: %{y:.4f}<br>%{x}<extra></extra>'
        ), secondary_y=False)
        
        # Predicted EUR/PLN (right axis) 
        fig1.add_trace(go.Scatter(
            x=df.index,
            y=df['predicted_eur_pln'],
            mode='lines',
            name='EUR/PLN (Predicted)',
            line=dict(color='#F24236', width=2),
            hovertemplate='Predicted: %{y:.4f}<br>%{x}<extra></extra>'
        ), secondary_y=True)
        
        # Update axes
        fig1.update_yaxes(
            title_text="Actual EUR/PLN Rate", 
            title_font_color="#2E86AB",
            tickfont_color="#2E86AB",
            secondary_y=False
        )
        fig1.update_yaxes(
            title_text="Predicted EUR/PLN Rate",
            title_font_color="#F24236", 
            tickfont_color="#F24236",
            secondary_y=True
        )
        
        fig1.update_layout(
            height=450,
            showlegend=True,
            legend=dict(x=0.02, y=0.98, bgcolor='rgba(255,255,255,0.8)'),
            xaxis_title="Date",
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        # Add grid
        fig1.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.markdown("**Bond Yield Spread (PL 10Y - DE 10Y)**")
        
        fig2 = go.Figure()
        
        fig2.add_trace(go.Scatter(
            x=df.index,
            y=df['yield_spread'],
            mode='lines',
            name='PL-DE Spread',
            line=dict(color='#A8E6CF', width=2),
            fill='tozeroy',
            fillcolor='rgba(168, 230, 207, 0.3)',
            hovertemplate='Spread: %{y:.2f}pp<br>%{x}<extra></extra>'
        ))
        
        # Current spread line
        fig2.add_hline(y=current_spread, line_dash="dot", line_color="red", line_width=2,
                       annotation_text=f"Current: {current_spread:.2f}pp",
                       annotation_position="top right")
        
        # Auto-scale y-axis to data range with some padding
        spread_min = df['yield_spread'].min()
        spread_max = df['yield_spread'].max()
        spread_range = spread_max - spread_min
        padding = spread_range * 0.1  # 10% padding
        
        fig2.update_layout(
            height=450,
            xaxis_title="Date",
            yaxis_title="Yield Spread (pp)",
            yaxis=dict(
                range=[spread_min - padding, spread_max + padding]
            ),
            hovermode='x',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        # Add grid
        fig2.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig2.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        st.plotly_chart(fig2, use_container_width=True)
    
    # Statistical Analysis
    st.subheader("📊 EUR/PLN Model Performance Analytics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Calculate metrics
        correlation = df['actual_eur_pln'].corr(df['predicted_eur_pln'])
        rmse = np.sqrt(np.mean((df['actual_eur_pln'] - df['predicted_eur_pln'])**2))
        mae = np.mean(np.abs(df['actual_eur_pln'] - df['predicted_eur_pln']))
        
        st.markdown(f"""
        **EUR Model Accuracy:**
        - **Correlation**: {correlation:.3f}
        - **RMSE**: {rmse:.4f}
        - **MAE**: {mae:.4f}
        - **Current Error**: {abs(current_actual - current_predicted):.4f}
        """)
    
    with col2:
        # Recent trends
        recent_df = df.tail(30)
        recent_actual_change = recent_df['actual_eur_pln'].iloc[-1] - recent_df['actual_eur_pln'].iloc[0]
        recent_spread_change = recent_df['yield_spread'].iloc[-1] - recent_df['yield_spread'].iloc[0]
        
        st.markdown(f"""
        **EUR 30-Day Trends:**
        - **EUR/PLN Change**: {recent_actual_change:.4f}
        - **Spread Change**: {recent_spread_change:.2f}pp
        - **Avg Error**: {np.mean(np.abs(recent_df['actual_eur_pln'] - recent_df['predicted_eur_pln'])):.4f}
        """)
    
    with col3:
        # Error distribution chart
        errors = df['actual_eur_pln'] - df['predicted_eur_pln']
        
        fig3 = go.Figure()
        fig3.add_trace(go.Histogram(
            x=errors,
            nbinsx=15,
            name='EUR Prediction Errors',
            marker_color='lightblue',
            opacity=0.7
        ))
        
        fig3.update_layout(
            title="EUR Error Distribution",
            xaxis_title="Error (Actual - Predicted)",
            yaxis_title="Frequency",
            height=250,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig3, use_container_width=True)
    
    # EUR Convergence Analysis - FIXED VERSION
    st.subheader("⏱️ EUR/PLN Prediction Convergence Analysis")
    
    # Calculate convergence for EUR
    eur_convergence = calculate_convergence_days(df, 'actual_eur_pln', 'predicted_eur_pln')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Avg Days to Target",
            safe_format_days(eur_convergence['avg_convergence_days']),
            help="Average days for actual price to reach predicted price"
        )
    
    with col2:
        st.metric(
            "Median Days to Target", 
            safe_format_days(eur_convergence['median_convergence_days']),
            help="Median time for price convergence"
        )
    
    with col3:
        st.metric(
            "Convergence Rate",
            f"{eur_convergence['convergence_rate']:.1f}%",
            help="% of predictions that eventually converged"
        )
    
    with col4:
        st.metric(
            "Avg Accuracy",
            safe_format_percentage(eur_convergence['avg_accuracy']),
            help="Average accuracy when convergence occurs"
        )
    
    # EUR convergence insights
    if eur_convergence['total_events'] > 0:
        avg_days_str = safe_format_days(eur_convergence['avg_convergence_days'])
        accuracy_str = safe_format_percentage(eur_convergence['avg_accuracy'])
        
        st.markdown(f"""
        **💡 EUR/PLN Prediction Insights:**
        - Model predictions converge to actual prices in **{avg_days_str} days** on average
        - **{eur_convergence['convergence_rate']:.1f}%** of predictions eventually reach target accuracy (within 0.1%)
        - When convergence occurs, average accuracy is **{accuracy_str}**
        - Total convergence events detected: **{eur_convergence['total_events']}** out of {len(df)} data points
        """)
    else:
        st.info("📊 No clear convergence patterns detected in the current dataset. This may indicate high market volatility or model adjustment needs.")

    # ============================================================================
    # USD/PLN SECTION
    # ============================================================================
    
    st.markdown("---")
    st.markdown("---")
    st.subheader("🇺🇸 USD/PLN Bond Spread Analytics")
    st.markdown("*Same methodology applied to USD/PLN using US Treasury yields*")
    
    # Current market data for USD
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "USD/PLN Spot", 
            f"{usd_forex_data['rate']:.4f}",
            help=f"Source: {usd_forex_data['source']} | Date: {usd_forex_data['date']}"
        )
    
    with col2:
        if 'Poland_10Y' in bond_data:
            pl_yield = bond_data['Poland_10Y']['value']
            st.metric(
                "Poland 10Y Bond", 
                f"{pl_yield:.2f}%",
                help="Polish government bond yield from FRED"
            )
        else:
            st.metric("Poland 10Y Bond", "N/A")
    
    with col3:
        if 'US_10Y' in bond_data:
            us_yield = bond_data['US_10Y']['value']
            st.metric(
                "US 10Y Treasury", 
                f"{us_yield:.2f}%",
                help="US Treasury yield from FRED"
            )
        else:
            st.metric("US 10Y Treasury", "N/A")
    
    with col4:
        if 'Poland_10Y' in bond_data and 'US_10Y' in bond_data:
            usd_spread = bond_data['Poland_10Y']['value'] - bond_data['US_10Y']['value']
            st.metric(
                "PL-US Spread", 
                f"{usd_spread:.2f} pp",
                help="Poland 10Y minus US 10Y"
            )
    
    # Generate USD historical data (same timeframe as EUR)
    with st.spinner("📊 Loading USD historical data..."):
        try:
            # Get historical USD/PLN
            usd_pln_data = dashboard.get_nbp_historical_data(start_date, end_date, 'usd')
            
            # Get US bond yields
            us_bonds = dashboard.fred_client.get_historical_data('DGS10', 
                                                               start_date.strftime('%Y-%m-%d'), 
                                                               end_date.strftime('%Y-%m-%d'))
            
            if not usd_pln_data.empty and not pl_bonds.empty and not us_bonds.empty:
                # Combine real data
                df_usd = usd_pln_data.copy()
                df_usd.columns = ['actual_usd_pln']
                df_usd = df_usd.join(pl_bonds.rename(columns={'value': 'pl_yield'}), how='left')
                df_usd = df_usd.join(us_bonds.rename(columns={'value': 'us_yield'}), how='left')
                df_usd = df_usd.fillna(method='ffill').fillna(method='bfill')
                
                # Calculate predicted USD rates
                df_usd['predicted_usd_pln'] = df_usd.apply(
                    lambda row: dashboard.calculate_predicted_fx_rate(
                        row['pl_yield'], row['us_yield'], df_usd['actual_usd_pln'].iloc[0], 'USD'
                    ), axis=1
                )
                df_usd['yield_spread'] = df_usd['pl_yield'] - df_usd['us_yield']
                st.success("✅ Using real USD market data")
            else:
                raise Exception("Insufficient USD data")
                
        except Exception as e:
            st.info("📊 Using sample USD data for demonstration")
            # Generate sample USD data
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            np.random.seed(43)  # Different seed for USD
            
            # Sample USD/PLN
            base_rate = 3.85
            trend = np.linspace(0, 0.015, len(dates))
            noise = np.cumsum(np.random.randn(len(dates)) * 0.004)
            actual_usd_pln = base_rate + trend + noise
            
            # Sample yields
            pl_yields_usd = 5.7 + np.cumsum(np.random.randn(len(dates)) * 0.01)
            us_yields = 4.5 + np.cumsum(np.random.randn(len(dates)) * 0.012)
            
            predicted_usd_pln = []
            for i in range(len(dates)):
                pred_rate = dashboard.calculate_predicted_fx_rate(pl_yields_usd[i], us_yields[i], base_rate, 'USD')
                predicted_usd_pln.append(pred_rate)
            
            df_usd = pd.DataFrame({
                'actual_usd_pln': actual_usd_pln,
                'predicted_usd_pln': predicted_usd_pln,
                'pl_yield': pl_yields_usd,
                'us_yield': us_yields,
                'yield_spread': pl_yields_usd - us_yields
            }, index=dates)
    
    # USD Current values
    current_actual_usd = df_usd['actual_usd_pln'].iloc[-1]
    current_predicted_usd = df_usd['predicted_usd_pln'].iloc[-1]
    difference_pct_usd = ((current_predicted_usd - current_actual_usd) / current_actual_usd) * 100
    current_spread_usd = df_usd['yield_spread'].iloc[-1]
    
    # USD Latest FX vs Predicted metrics
    st.subheader("💰 Latest USD/PLN vs Predicted")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="rate-label">Actual USD/PLN</div>
            <div class="actual-rate">{current_actual_usd:.4f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="rate-label">Predicted USD/PLN</div>
            <div class="predicted-rate">{current_predicted_usd:.4f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        difference_color_usd = "#28a745" if abs(difference_pct_usd) < 1 else "#dc3545"
        st.markdown(f"""
        <div class="metric-card">
            <div class="rate-label">% Difference USD</div>
            <div class="difference" style="color: {difference_color_usd}">{difference_pct_usd:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="rate-label">PL-US Spread</div>
            <div class="difference">{current_spread_usd:.2f}pp</div>
        </div>
        """, unsafe_allow_html=True)
    
    # USD Charts side by side with EUR pattern
    st.subheader("📈 USD/PLN Historical Analysis (Last 6 Months)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**USD/PLN: Historical vs Predicted**")
        
        # Create dual-axis subplot
        fig_usd1 = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Actual USD/PLN (left axis)
        fig_usd1.add_trace(go.Scatter(
            x=df_usd.index,
            y=df_usd['actual_usd_pln'],
            mode='lines',
            name='USD/PLN (Actual)',
            line=dict(color='#FF6B35', width=2),
            hovertemplate='Actual: %{y:.4f}<br>%{x}<extra></extra>'
        ), secondary_y=False)
        
        # Predicted USD/PLN (right axis)
        fig_usd1.add_trace(go.Scatter(
            x=df_usd.index,
            y=df_usd['predicted_usd_pln'],
            mode='lines',
            name='USD/PLN (Predicted)',
            line=dict(color='#004E89', width=2),
            hovertemplate='Predicted: %{y:.4f}<br>%{x}<extra></extra>'
        ), secondary_y=True)
        
        # Update axes
        fig_usd1.update_yaxes(
            title_text="Actual USD/PLN Rate",
            title_font_color="#FF6B35",
            tickfont_color="#FF6B35", 
            secondary_y=False
        )
        fig_usd1.update_yaxes(
            title_text="Predicted USD/PLN Rate",
            title_font_color="#004E89",
            tickfont_color="#004E89",
            secondary_y=True
        )
        
        fig_usd1.update_layout(
            height=450,
            showlegend=True,
            legend=dict(x=0.02, y=0.98, bgcolor='rgba(255,255,255,0.8)'),
            xaxis_title="Date",
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        # Add grid
        fig_usd1.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        st.plotly_chart(fig_usd1, use_container_width=True)
    
    with col2:
        st.markdown("**Bond Yield Spread (PL 10Y - US 10Y)**")
        
        fig_usd2 = go.Figure()
        
        fig_usd2.add_trace(go.Scatter(
            x=df_usd.index,
            y=df_usd['yield_spread'],
            mode='lines',
            name='PL-US Spread',
            line=dict(color='#FFB3BA', width=2),
            fill='tozeroy',
            fillcolor='rgba(255, 179, 186, 0.3)',
            hovertemplate='Spread: %{y:.2f}pp<br>%{x}<extra></extra>'
        ))
        
        # Current spread line
        fig_usd2.add_hline(y=current_spread_usd, line_dash="dot", line_color="red", line_width=2,
                           annotation_text=f"Current: {current_spread_usd:.2f}pp",
                           annotation_position="top right")
        
        # Auto-scale y-axis to data range with some padding
        usd_spread_min = df_usd['yield_spread'].min()
        usd_spread_max = df_usd['yield_spread'].max()
        usd_spread_range = usd_spread_max - usd_spread_min
        usd_padding = usd_spread_range * 0.1  # 10% padding
        
        fig_usd2.update_layout(
            height=450,
            xaxis_title="Date",
            yaxis_title="Yield Spread (pp)",
            yaxis=dict(
                range=[usd_spread_min - usd_padding, usd_spread_max + usd_padding]
            ),
            hovermode='x',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        # Add grid
        fig_usd2.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig_usd2.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        st.plotly_chart(fig_usd2, use_container_width=True)
    
    # USD Model Performance
    st.subheader("📊 USD/PLN Model Performance Analytics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # USD Calculate metrics
        usd_correlation = df_usd['actual_usd_pln'].corr(df_usd['predicted_usd_pln'])
        usd_rmse = np.sqrt(np.mean((df_usd['actual_usd_pln'] - df_usd['predicted_usd_pln'])**2))
        usd_mae = np.mean(np.abs(df_usd['actual_usd_pln'] - df_usd['predicted_usd_pln']))
        
        st.markdown(f"""
        **USD Model Accuracy:**
        - **Correlation**: {usd_correlation:.3f}
        - **RMSE**: {usd_rmse:.4f}
        - **MAE**: {usd_mae:.4f}
        - **Current Error**: {abs(current_actual_usd - current_predicted_usd):.4f}
        """)
    
    with col2:
        # USD Recent trends
        recent_df_usd = df_usd.tail(30)
        recent_actual_change_usd = recent_df_usd['actual_usd_pln'].iloc[-1] - recent_df_usd['actual_usd_pln'].iloc[0]
        recent_spread_change_usd = recent_df_usd['yield_spread'].iloc[-1] - recent_df_usd['yield_spread'].iloc[0]
        
        st.markdown(f"""
        **USD 30-Day Trends:**
        - **USD/PLN Change**: {recent_actual_change_usd:.4f}
        - **Spread Change**: {recent_spread_change_usd:.2f}pp
        - **Avg Error**: {np.mean(np.abs(recent_df_usd['actual_usd_pln'] - recent_df_usd['predicted_usd_pln'])):.4f}
        """)
    
    with col3:
        # USD Error distribution chart
        errors_usd = df_usd['actual_usd_pln'] - df_usd['predicted_usd_pln']
        
        fig_usd3 = go.Figure()
        fig_usd3.add_trace(go.Histogram(
            x=errors_usd,
            nbinsx=15,
            name='USD Prediction Errors',
            marker_color='lightcoral',
            opacity=0.7
        ))
        
        fig_usd3.update_layout(
            title="USD Error Distribution",
            xaxis_title="Error (Actual - Predicted)",
            yaxis_title="Frequency",
            height=250,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig_usd3, use_container_width=True)
    
    # USD Convergence Analysis - FIXED VERSION
    st.subheader("⏱️ USD/PLN Prediction Convergence Analysis")
    
    # Calculate convergence for USD
    usd_convergence = calculate_convergence_days(df_usd, 'actual_usd_pln', 'predicted_usd_pln')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Avg Days to Target",
            safe_format_days(usd_convergence['avg_convergence_days']),
            help="Average days for actual USD/PLN to reach predicted price"
        )
    
    with col2:
        st.metric(
            "Median Days to Target",
            safe_format_days(usd_convergence['median_convergence_days']),
            help="Median time for USD price convergence"
        )
    
    with col3:
        st.metric(
            "Convergence Rate",
            f"{usd_convergence['convergence_rate']:.1f}%",
            help="% of USD predictions that eventually converged"
        )
    
    with col4:
        st.metric(
            "Avg Accuracy",
            safe_format_percentage(usd_convergence['avg_accuracy']),
            help="Average accuracy when USD convergence occurs"
        )
    
    # USD convergence insights - FIXED VERSION
    if usd_convergence['total_events'] > 0:
        usd_avg_days_str = safe_format_days(usd_convergence['avg_convergence_days'])
        usd_accuracy_str = safe_format_percentage(usd_convergence['avg_accuracy'])
        
        st.markdown(f"""
        **💡 USD/PLN Prediction Insights:**
        - USD Model predictions converge to actual prices in **{usd_avg_days_str} days** on average
        - **{usd_convergence['convergence_rate']:.1f}%** of USD predictions eventually reach target accuracy (within 0.1%)
        - When USD convergence occurs, average accuracy is **{usd_accuracy_str}**
        - Total USD convergence events detected: **{usd_convergence['total_events']}** out of {len(df_usd)} data points
        """)
    else:
        st.info("📊 No clear USD convergence patterns detected in the current dataset. USD/PLN may be more volatile than EUR/PLN.")
    
    # EUR vs USD Comparison Section - FIXED VERSION
    st.markdown("---")
    st.subheader("⚖️ EUR/PLN vs USD/PLN Side-by-Side Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 EUR/PLN Performance Summary**")
        eur_avg_conv = safe_format_days(eur_convergence['avg_convergence_days'])
        st.markdown(f"""
        - **Current Actual**: {current_actual:.4f}
        - **Current Predicted**: {current_predicted:.4f}
        - **Model Error**: {difference_pct:.2f}%
        - **Current Spread**: {current_spread:.2f}pp (PL-DE)
        - **Model Correlation**: {correlation:.3f}
        - **Avg Convergence**: {eur_avg_conv} days
        """)
    
    with col2:
        st.markdown("**🇺🇸 USD/PLN Performance Summary**")
        usd_avg_conv = safe_format_days(usd_convergence['avg_convergence_days'])
        st.markdown(f"""
        - **Current Actual**: {current_actual_usd:.4f}
        - **Current Predicted**: {current_predicted_usd:.4f}
        - **Model Error**: {difference_pct_usd:.2f}%
        - **Current Spread**: {current_spread_usd:.2f}pp (PL-US)
        - **Model Correlation**: {usd_correlation:.3f}
        - **Avg Convergence**: {usd_avg_conv} days
        """)
    
    # Convergence Comparison - FIXED VERSION
    st.subheader("⚖️ EUR vs USD Convergence Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # EUR vs USD convergence metrics
        if eur_convergence['avg_convergence_days'] is not None and usd_convergence['avg_convergence_days'] is not None:
            faster_currency = "EUR" if eur_convergence['avg_convergence_days'] < usd_convergence['avg_convergence_days'] else "USD"
            speed_diff = abs(eur_convergence['avg_convergence_days'] - usd_convergence['avg_convergence_days'])
            
            st.markdown(f"""
            **🏃‍♂️ Convergence Speed Comparison:**
            - **EUR/PLN**: {safe_format_days(eur_convergence['avg_convergence_days'])} days average
            - **USD/PLN**: {safe_format_days(usd_convergence['avg_convergence_days'])} days average
            - **Faster Model**: {faster_currency} by {speed_diff:.1f} days
            - **EUR Convergence Rate**: {eur_convergence['convergence_rate']:.1f}%
            - **USD Convergence Rate**: {usd_convergence['convergence_rate']:.1f}%
            """)
        else:
            st.markdown("""
            **🏃‍♂️ Convergence Speed Comparison:**
            - **EUR/PLN**: N/A days average  
            - **USD/PLN**: N/A days average
            - **Faster Model**: Cannot determine
            - **EUR Convergence Rate**: {:.1f}%
            - **USD Convergence Rate**: {:.1f}%
            """.format(eur_convergence['convergence_rate'], usd_convergence['convergence_rate']))
        
    with col2:
        # Convergence rate comparison chart
        if eur_convergence['total_events'] > 0 or usd_convergence['total_events'] > 0:
            eur_avg = eur_convergence.get('avg_convergence_days', 0) or 0
            usd_avg = usd_convergence.get('avg_convergence_days', 0) or 0
            
            fig_conv = go.Figure(data=[
                go.Bar(
                    x=['EUR/PLN', 'USD/PLN'],
                    y=[eur_avg, usd_avg],
                    marker_color=['#2E86AB', '#FF6B35'],
                    text=[safe_format_days(eur_avg) + "d", safe_format_days(usd_avg) + "d"],
                    textposition='auto'
                )
            ])
            
            fig_conv.update_layout(
                title="Average Days to Price Convergence",
                yaxis_title="Days",
                height=300,
                showlegend=False
            )
            
            st.plotly_chart(fig_conv, use_container_width=True)
    
    # Combined comparison chart
    st.subheader("📊 Complete EUR/PLN vs USD/PLN Analysis")
    
    fig_comparison = make_subplots(
        rows=2, cols=2,
        subplot_titles=("EUR/PLN vs USD/PLN Rates", "Bond Spreads Comparison", 
                       "Prediction Accuracy", "Recent Trends"),
        specs=[[{"secondary_y": True}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Chart 1: FX Rates comparison
    fig_comparison.add_trace(
        go.Scatter(x=df.index, y=df['actual_eur_pln'], 
                  name="EUR/PLN", line=dict(color='#2E86AB', width=2)),
        row=1, col=1
    )
    fig_comparison.add_trace(
        go.Scatter(x=df_usd.index, y=df_usd['actual_usd_pln'], 
                  name="USD/PLN", line=dict(color='#FF6B35', width=2)),
        row=1, col=1, secondary_y=True
    )
    
    # Chart 2: Spreads comparison
    fig_comparison.add_trace(
        go.Scatter(x=df.index, y=df['yield_spread'], 
                  name="PL-DE Spread", line=dict(color='#A8E6CF', width=2)),
        row=1, col=2
    )
    fig_comparison.add_trace(
        go.Scatter(x=df_usd.index, y=df_usd['yield_spread'], 
                  name="PL-US Spread", line=dict(color='#FFB3BA', width=2)),
        row=1, col=2
    )
    
    # Chart 3: Prediction errors
    fig_comparison.add_trace(
        go.Scatter(x=df.index, y=abs(df['actual_eur_pln'] - df['predicted_eur_pln']), 
                  name="EUR Error", line=dict(color='#2E86AB', width=2)),
        row=2, col=1
    )
    fig_comparison.add_trace(
        go.Scatter(x=df_usd.index, y=abs(df_usd['actual_usd_pln'] - df_usd['predicted_usd_pln']), 
                  name="USD Error", line=dict(color='#FF6B35', width=2)),
        row=2, col=1
    )
    
    # Chart 4: 30-day rolling correlation
    if len(df) > 30 and len(df_usd) > 30:
        # Calculate rolling correlation between the two pairs
        common_dates = df.index.intersection(df_usd.index)
        if len(common_dates) > 30:
            eur_common = df.loc[common_dates, 'actual_eur_pln']
            usd_common = df_usd.loc[common_dates, 'actual_usd_pln']
            rolling_corr = eur_common.rolling(30).corr(usd_common)
            
            fig_comparison.add_trace(
                go.Scatter(x=rolling_corr.index, y=rolling_corr, 
                          name="EUR-USD Correlation", line=dict(color='purple', width=2)),
                row=2, col=2
            )
    
    # Update layout for comparison chart
    fig_comparison.update_layout(height=600, title_text="Complete EUR/PLN vs USD/PLN Analysis")
    fig_comparison.update_yaxes(title_text="EUR/PLN Rate", row=1, col=1, secondary_y=False)
    fig_comparison.update_yaxes(title_text="USD/PLN Rate", row=1, col=1, secondary_y=True)
    fig_comparison.update_yaxes(title_text="Yield Spread (pp)", row=1, col=2)
    fig_comparison.update_yaxes(title_text="Absolute Error", row=2, col=1)
    fig_comparison.update_yaxes(title_text="Correlation", row=2, col=2)
    
    st.plotly_chart(fig_comparison, use_container_width=True)

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
            **Forward Rate Formula (Both Currencies):**
            ```
            Forward = Spot × (1 + r_PL × T) / (1 + r_Foreign × T)
            ```
            
            **Bond Spread Models:**
            ```
            EUR: Predicted_FX = Base_Rate × (1 + Spread × 0.15)
            USD: Predicted_FX = Base_Rate × (1 + Spread × 0.18)
            ```
            
            **Data Sources:**
            - **EUR/PLN & USD/PLN**: NBP API (Polish Central Bank)
            - **Bond Yields**: FRED API (Federal Reserve Economic Data)
            - **Interpolation**: German 9M = German 10Y - 25bp
            
            **Model Differences:**
            - **EUR Model**: 15% sensitivity (more stable)
            - **USD Model**: 18% sensitivity (more volatile)
            - **Base Rates**: EUR ~4.24, USD ~3.85
            
            **Update Frequency:**
            - Bond data: 1 hour cache
            - FX data: 5 minute cache
            - Historical: Daily
            
            **Convergence Analysis:**
            - Tracks when actual FX rates reach predicted levels
            - Uses 0.1% tolerance for convergence detection
            - Analyzes up to 30-day prediction windows
            """)

# Performance note
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: gray; font-size: 0.8em; padding: 1rem; border-top: 1px solid #eee;'>
    💱 <strong>Professional FX Trading Dashboard</strong><br>
    📊 Real-time data: NBP API, FRED API | 🧮 Forward Calculator | 📈 Bond Spread Analytics | 🇺🇸 USD/PLN Analytics<br>
    ⏰ Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
    🔗 <a href="https://fred.stlouisfed.org/docs/api/" target="_blank">FRED API Docs</a><br>
    ⚠️ <em>For educational and analytical purposes - not financial advice</em>
    </div>
    """, 
    unsafe_allow_html=True
)
