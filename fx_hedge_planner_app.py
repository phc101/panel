# ============================================================================
        # RISK ANALYSIS SECTION
        # ============================================================================
        
        st.markdown("---")
        st.subheader("⚠️ Risk Analysis Dashboard")
        
        # Key metrics for window forward
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Window Exposure",
                f"€{nominal_amount:,.0f}",
                help=f"Nominal exposure for {window_days}-day window"
            )
        
        with col2:
            st.metric(
                "Profit Margin",
                f"{profit_percentage:.3f}%",
                help="Dealer profit margin on window forward"
            )
        
        with col3:
            st.metric(
                "Points Efficiency",
                f"{points_factor:.0%}",
                help="Percentage of forward points given to client"
            )
        
        with col4:
            st.metric(
                "Risk Coverage",
                f"{risk_factor:.0%}",
                help="Percentage of swap risk charged to client"
            )
        
        # Window forward insights
        st.markdown("### 💡 Window Forward Insights")
        
        insights = []
        
        # Points analysis
        points_kept_pct = (1 - points_factor) * 100
        risk_coverage_pct = risk_factor * 100
        
        insights.append(f"📊 **Points Strategy**: Giving {points_factor:.0%} of forward points to client, keeping {points_kept_pct:.0f}% as premium")
        insights.append(f"⚠️ **Risk Management**: Charging client {risk_coverage_pct:.0f}% of swap risk, dealer covers {100-risk_coverage_pct:.0f}%")
        insights.append(f"💰 **Profit Source**: {points_kept_pct:.0f}% from points retention + {risk_coverage_pct:.0f}% from risk premium")
        
        # Window length analysis
        if window_days <= 60:
            insights.append(f"⏰ **Window Length**: {window_days}-day window is relatively short - lower risk, lower premium")
        elif window_days <= 120:
            insights.append(f"⏰ **Window Length**: {window_days}-day window is moderate - balanced risk/reward")
        else:
            insights.append(f"⏰ **Window Length**: {window_days}-day window is long - higher risk, higher premium required")
        
        # Profitability analysis
        if profit_percentage > 0.1:
            insights.append(f"✅ **Profitability**: Strong profit margin of {profit_percentage:.3f}% - competitive pricing")
        elif profit_percentage > 0.05:
            insights.append(f"⚡ **Profitability**: Moderate profit margin of {profit_percentage:.3f}% - acceptable but could optimize")
        else:
            insights.append(f"🚨 **Profitability**: Low profit margin of {profit_percentage:.3f}% - consider increasing risk factor")
        
        # Display insights
        for insight in insights:
            st.markdown(insight)
        
        # Trading recommendations
        st.markdown("### 📋 Window Forward Recommendations")
        
        recommendations = []
        
        # Risk factor recommendations
        if risk_factor < 0.4:
            recommendations.append("🔴 **Risk Factor Too Low**: Consider increasing to 40-45% for better risk coverage")
        elif risk_factor > 0.6:
            recommendations.append("🟡 **Risk Factor High**: Consider if client will accept 60%+ risk charge")
        else:
            recommendations.append("🟢 **Risk Factor Optimal**: 40-60% range provides good balance")
        
        # Points factor recommendations
        if points_factor > 0.8:
            recommendations.append("🟡 **Points Factor High**: Giving 80%+ points - ensure adequate profit margin")
        elif points_factor < 0.6:
            recommendations.append("🔴 **Points Factor Low**: <60% may not be attractive to clients")
        else:
            recommendations.append("🟢 **Points Factor Good**: 60-80% range is client-friendly yet profitable")
        
        # Window length recommendations
        optimal_window = 90  # days
        if abs(window_days - optimal_window) > 30:
            recommendations.append(f"💡 **Window Optimization**: Consider {optimal_window}-day window for optimal risk/reward balance")
        
        # Display recommendations
        for rec in recommendations:
            if "🟢" in rec:
                st.success(rec)
            elif "🟡" in rec:
                st.warning(rec)
            elif "🔴" in rec:
                st.error(rec)
            else:
                st.info(rec)

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
            
            **Window Forward Formula (Final Correct Version):**
            ```
            FWD_Client = Spot + (Points_to_Window × Points_Factor) - (Swap_Risk × Risk_Factor)
            
            Where:
            - Points_to_Window = Forward points to window START (not maturity)
            - Points_Factor = 0.70 (70% of points given to client)
            - Risk_Factor = 0.40 (40% of swap risk charged to client)
            - Swap_Risk = Ask_Points - Mid_Points (bid-ask spread)
            ```
            
            **Key Logic:**
            - Client gets 70% benefit of forward points TO WINDOW
            - Client pays 40% of swap risk for window flexibility
            - Dealer keeps 30% of points + 60% risk coverage as profit
            - Window length determines points calculation period
            
            **Data Sources:**
            - **FX Rates**: NBP API (Polish Central Bank)
            - **Bond Yields**: FRED API (Federal Reserve Economic Data)
            - **Forward Points**: Live generation from spreads with interpolation
            
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
)import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta

# FRED API Configuration
FRED_API_KEY = "demo"  # Replace with your API key

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
                "mid": mid_points,
                "days": days,
                "months": months
            }
        
        return points_data
    
    def calculate_points_to_window(self, window_days, points_data):
        """Calculate forward points to the start of the window"""
        # Interpolate points for the window start date
        window_months = window_days / 30.0
        
        # Find the closest tenors for interpolation
        available_months = sorted([data["months"] for data in points_data.values()])
        
        if window_months <= available_months[0]:
            # Use shortest tenor
            shortest_tenor = next(tenor for tenor, data in points_data.items() if data["months"] == available_months[0])
            ratio = window_months / available_months[0]
            return {
                "bid": points_data[shortest_tenor]["bid"] * ratio,
                "ask": points_data[shortest_tenor]["ask"] * ratio,
                "mid": points_data[shortest_tenor]["mid"] * ratio
            }
        elif window_months >= available_months[-1]:
            # Use longest tenor
            longest_tenor = next(tenor for tenor, data in points_data.items() if data["months"] == available_months[-1])
            return {
                "bid": points_data[longest_tenor]["bid"],
                "ask": points_data[longest_tenor]["ask"],
                "mid": points_data[longest_tenor]["mid"]
            }
        else:
            # Interpolate between two tenors
            lower_months = max([m for m in available_months if m <= window_months])
            upper_months = min([m for m in available_months if m >= window_months])
            
            lower_tenor = next(tenor for tenor, data in points_data.items() if data["months"] == lower_months)
            upper_tenor = next(tenor for tenor, data in points_data.items() if data["months"] == upper_months)
            
            # Linear interpolation
            ratio = (window_months - lower_months) / (upper_months - lower_months)
            
            return {
                "bid": points_data[lower_tenor]["bid"] + ratio * (points_data[upper_tenor]["bid"] - points_data[lower_tenor]["bid"]),
                "ask": points_data[lower_tenor]["ask"] + ratio * (points_data[upper_tenor]["ask"] - points_data[lower_tenor]["ask"]),
                "mid": points_data[lower_tenor]["mid"] + ratio * (points_data[upper_tenor]["mid"] - points_data[lower_tenor]["mid"])
            }
    
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
    
    def calculate_forward_client(self, spot_rate, points_to_window, swap_risk, points_factor=0.70, risk_factor=0.4):
        """Calculate forward rate for client using correct window forward logic"""
        # Correct Formula: Spot + (Points_to_Window × 0.70) - (Swap_Risk × 0.40)
        # We give client 70% of points TO WINDOW start, but charge for swap risk
        points_for_client = points_to_window * points_factor
        swap_risk_compensation = swap_risk * risk_factor
        return spot_rate + points_for_client - swap_risk_compensation
    
    def calculate_forward_theoretical(self, spot_rate, points_to_window):
        """Calculate theoretical forward rate to window start (full points)"""
        return spot_rate + points_to_window
    
    def calculate_closing_cost_for_window(self, ask_points_to_window, window_length_months):
        """Calculate closing cost based on window length"""
        # Closing cost is the cost to hedge during the window period
        return ask_points_to_window * (window_length_months / self.get_months_for_points(ask_points_to_window))
    
    def get_months_for_points(self, points_value):
        """Estimate months corresponding to points value (simple approximation)"""
        # This is a simplified approach - in practice you'd use proper interpolation
        return max(1.0, abs(points_value) * 100)  # Rough approximation
    
    def calculate_swap_risk_for_window(self, closing_cost, points_to_window):
        """Calculate swap risk for window period"""
        return closing_cost - points_to_window
    
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
    
    # Advanced configuration
    st.subheader("🔧 Advanced Dealer Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        points_factor = st.slider(
            "Points Factor (% given to client):",
            min_value=0.50,
            max_value=0.90,
            value=0.70,
            step=0.05,
            key="points_factor",
            help="Percentage of forward points given to client (typical: 70%)"
        )
    
    with col2:
        risk_factor = st.slider(
            "Risk Factor (swap risk compensation):",
            min_value=0.30,
            max_value=0.70,
            value=0.40,
            step=0.05,
            key="risk_factor",
            help="Percentage of swap risk charged to client (typical: 40-65%)"
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
    
    # Calculate points to window start
    points_to_window = wf_calc.calculate_points_to_window(window_days, forward_points_data)
    
    # Display current spread info
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.info(f"🇵🇱 Poland 10Y: **{default_pl_yield:.2f}%**")
    with col2:
        st.info(f"🇩🇪 Germany 10Y: **{default_de_yield:.2f}%**")
    with col3:
        st.info(f"📊 Current Spread: **{(default_pl_yield - default_de_yield):.2f}pp**")
    with col4:
        st.info(f"📅 Window: **{window_days} days** ({window_days/30:.1f}M)")
    
    # Show points to window
    st.markdown("### 📈 Forward Points to Window Start")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Bid Points to Window", f"{points_to_window['bid']:.5f}")
    with col2:
        st.metric("Ask Points to Window", f"{points_to_window['ask']:.5f}")
    with col3:
        st.metric("Mid Points to Window", f"{points_to_window['mid']:.5f}")
    
    # ============================================================================
    # CALCULATIONS SECTION
    # ============================================================================
    
    st.subheader("💰 Window Forward Pricing Table")
    
    # Calculate window length in months
    window_months = window_days / 30.0
    
    # Prepare single calculation for window forward
    window_forward_result = {
        "Window Period": f"{window_days} days ({window_months:.1f}M)",
        "Points to Window (Mid)": points_to_window['mid'],
        "Points to Window (Bid)": points_to_window['bid'],
        "Points to Window (Ask)": points_to_window['ask'],
        "Points Given to Client": points_to_window['mid'] * points_factor,
        "Closing Cost": points_to_window['ask'],  # Simplified: ask points represent closing cost
        "Swap Risk": points_to_window['ask'] - points_to_window['mid'],
        "Risk Compensation": (points_to_window['ask'] - points_to_window['mid']) * risk_factor,
        "FWD Theoretical": spot_rate_wf + points_to_window['mid'],
        "FWD Client": wf_calc.calculate_forward_client(spot_rate_wf, points_to_window['mid'], 
                                                      points_to_window['ask'] - points_to_window['mid'], 
                                                      points_factor, risk_factor),
        "Dealer Profit (Absolute)": None,  # Will calculate after
        "Dealer Profit %": None,  # Will calculate after
        "Net Worst (EUR)": None,  # Will calculate after
    }
    
    # Calculate profits
    fwd_theoretical = window_forward_result["FWD Theoretical"]
    fwd_client = window_forward_result["FWD Client"]
    profit_absolute = fwd_theoretical - fwd_client
    profit_percentage = (profit_absolute / fwd_client) * 100
    net_worst_nominal = profit_absolute * nominal_amount
    
    # Update results
    window_forward_result.update({
        "Dealer Profit (Absolute)": profit_absolute,
        "Dealer Profit %": profit_percentage,
        "Net Worst (EUR)": net_worst_nominal,
        "Potential Profit (EUR)": net_worst_nominal * 1.5
    })
    
    # Display results in a nice format
    st.markdown("### 📊 Window Forward Calculation Results")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("FWD Theoretical", f"{fwd_theoretical:.4f}")
        st.metric("Points to Window", f"{points_to_window['mid']:.5f}")
    
    with col2:
        st.metric("FWD Client", f"{fwd_client:.4f}")
        st.metric("Points Given (70%)", f"{window_forward_result['Points Given to Client']:.5f}")
    
    with col3:
        st.metric("Dealer Profit", f"{profit_absolute:.5f}")
        st.metric("Risk Compensation", f"{window_forward_result['Risk Compensation']:.5f}")
    
    with col4:
        st.metric("Profit %", f"{profit_percentage:.3f}%")
        st.metric("Net Worst (EUR)", f"€{net_worst_nominal:,.0f}")
    
    # Detailed breakdown table
    st.markdown("### 📋 Detailed Calculation Breakdown")
    
    breakdown_data = [
        ["Spot Rate", f"{spot_rate_wf:.4f}"],
        ["Window Length", f"{window_days} days ({window_months:.1f} months)"],
        ["Points to Window (Mid)", f"{points_to_window['mid']:.5f}"],
        ["Points Factor", f"{points_factor:.0%}"],
        ["Points Given to Client", f"{window_forward_result['Points Given to Client']:.5f}"],
        ["Swap Risk", f"{window_forward_result['Swap Risk']:.5f}"],
        ["Risk Factor", f"{risk_factor:.0%}"],
        ["Risk Compensation", f"{window_forward_result['Risk Compensation']:.5f}"],
        ["FWD Theoretical", f"{fwd_theoretical:.4f}"],
        ["FWD Client", f"{fwd_client:.4f}"],
        ["Dealer Profit", f"{profit_absolute:.5f}"],
        ["Profit Percentage", f"{profit_percentage:.3f}%"]
    ]
    
    df_breakdown = pd.DataFrame(breakdown_data, columns=["Component", "Value"])
    st.dataframe(df_breakdown, use_container_width=True)
        
        # ============================================================================
        # VISUALIZATIONS
        # ============================================================================
        
        st.markdown("---")
        st.subheader("📈 Window Forward Analysis Charts")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Window forward breakdown chart
            categories = ['Spot Rate', 'Points Given', 'Risk Compensation', 'Final Client Rate']
            values = [spot_rate_wf, 
                     window_forward_result['Points Given to Client'], 
                     -window_forward_result['Risk Compensation'],
                     fwd_client]
            colors = ['blue', 'green', 'red', 'purple']
            
            fig_breakdown = go.Figure()
            
            # Add bars for breakdown
            cumulative = spot_rate_wf
            fig_breakdown.add_trace(go.Bar(
                x=['Components'],
                y=[spot_rate_wf],
                name='Spot Rate',
                marker_color='blue',
                text=f'{spot_rate_wf:.4f}',
                textposition='middle'
            ))
            
            fig_breakdown.add_trace(go.Bar(
                x=['Components'],
                y=[window_forward_result['Points Given to Client']],
                name='Points Given (+)',
                marker_color='green',
                text=f"+{window_forward_result['Points Given to Client']:.5f}",
                textposition='middle'
            ))
            
            fig_breakdown.add_trace(go.Bar(
                x=['Components'],
                y=[-window_forward_result['Risk Compensation']],
                name='Risk Compensation (-)',
                marker_color='red',
                text=f"-{window_forward_result['Risk Compensation']:.5f}",
                textposition='middle'
            ))
            
            fig_breakdown.update_layout(
                title="Window Forward Rate Breakdown",
                yaxis_title="Rate Components",
                height=400,
                barmode='relative'
            )
            
            st.plotly_chart(fig_breakdown, use_container_width=True)
        
        with col2:
            # Profit analysis chart
            profit_components = ['Points Kept', 'Risk Coverage', 'Total Profit']
            profit_values = [
                points_to_window['mid'] * (1 - points_factor),  # 30% of points kept
                window_forward_result['Risk Compensation'],  # Risk coverage
                profit_absolute  # Total profit
            ]
            
            fig_profit = go.Figure()
            fig_profit.add_trace(go.Bar(
                x=profit_components,
                y=profit_values,
                marker_color=['lightblue', 'lightcoral', 'gold'],
                text=[f"{val:.5f}" for val in profit_values],
                textposition='auto'
            ))
            
            fig_profit.update_layout(
                title="Dealer Profit Components",
                yaxis_title="Profit (Rate Points)",
                height=400
            )
            
            st.plotly_chart(fig_profit, use_container_width=True)
        
        # Forward rate comparison over different window lengths
        st.subheader("📊 Window Length Impact Analysis")
        
        # Calculate for different window lengths
        window_lengths = [30, 60, 90, 120, 150, 180]
        window_analysis = []
        
        for window_length in window_lengths:
            temp_points = wf_calc.calculate_points_to_window(window_length, forward_points_data)
            temp_fwd_client = wf_calc.calculate_forward_client(
                spot_rate_wf, 
                temp_points['mid'], 
                temp_points['ask'] - temp_points['mid'], 
                points_factor, 
                risk_factor
            )
            temp_profit = (spot_rate_wf + temp_points['mid']) - temp_fwd_client
            
            window_analysis.append({
                'Window Days': window_length,
                'Points to Window': temp_points['mid'],
                'FWD Client': temp_fwd_client,
                'Dealer Profit': temp_profit
            })
        
        df_window_analysis = pd.DataFrame(window_analysis)
        
        fig_window = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Client Forward Rate by Window Length", "Dealer Profit by Window Length"),
            vertical_spacing=0.12
        )
        
        # Client forward rates
        fig_window.add_trace(go.Scatter(
            x=df_window_analysis['Window Days'],
            y=df_window_analysis['FWD Client'],
            mode='lines+markers',
            name='FWD Client',
            line=dict(color='blue', width=3),
            marker=dict(size=8)
        ), row=1, col=1)
        
        # Dealer profit
        fig_window.add_trace(go.Scatter(
            x=df_window_analysis['Window Days'],
            y=df_window_analysis['Dealer Profit'],
            mode='lines+markers',
            name='Dealer Profit',
            line=dict(color='green', width=3),
            marker=dict(size=8)
        ), row=2, col=1)
        
        # Add current window marker
        current_window_data = df_window_analysis[df_window_analysis['Window Days'] == window_days]
        if not current_window_data.empty:
            fig_window.add_vline(x=window_days, line_dash="dash", line_color="red", 
                                annotation_text=f"Current: {window_days}d")
        
        fig_window.update_layout(
            title=f"Window Forward Analysis (Points Factor: {points_factor:.0%}, Risk Factor: {risk_factor:.0%})",
            height=600,
            showlegend=False
        )
        
        fig_window.update_xaxes(title_text="Window Length (Days)", row=2, col=1)
        fig_window.update_yaxes(title_text="EUR/PLN Rate", row=1, col=1)
        fig_window.update_yaxes(title_text="Profit (Rate Points)", row=2, col=1)
        
        st.plotly_chart(fig_window, use_container_width=True)
        
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
                    forward_points_to_maturity = scenario_data["mid"]
                    closing_cost = wf_calc.calculate_closing_cost(scenario_data["ask"], tenor_months)
                    swap_risk = wf_calc.calculate_swap_risk(closing_cost, forward_points_to_maturity)
                    fwd_theoretical = wf_calc.calculate_forward_to_window(scenario_spot, forward_points_to_maturity)
                    fwd_client = wf_calc.calculate_forward_client(scenario_spot, forward_points_to_maturity, swap_risk, points_factor, risk_factor)
                    profit_absolute = wf_calc.calculate_profit_to_window(fwd_theoretical, fwd_client)
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
            
            **Window Forward Dealer Formula (Final Correct Version):**
            ```
            FWD_Client = Spot + (Forward_Points × Points_Factor) - (Swap_Risk × Risk_Factor)
            
            Where:
            - Points_Factor = 0.70 (70% of points given to client)
            - Risk_Factor = 0.40 (40% of swap risk charged to client)
            - Swap_Risk = Closing_Cost - Forward_Points
            ```
            
            **Economic Logic:**
            - Client gets 70% benefit of forward points
            - Client pays 40% of swap risk for window flexibility
            - Dealer keeps 30% of points + 60% risk coverage as profit
            
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
