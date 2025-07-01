import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta

# ============================================================================
# CONFIGURATION & API KEYS
# ============================================================================

# FRED API Configuration - PLACE YOUR API KEY HERE
FRED_API_KEY = st.secrets.get("FRED_API_KEY", "f65897ba8bbc5c387dc26081d5b66edf")  # Uses Streamlit secrets or demo

# You can also set it directly:
# FRED_API_KEY = "your_fred_api_key_here"

# Page config
st.set_page_config(
    page_title="Professional FX Calculator",
    page_icon="🚀",
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
# FRED API CLIENT CLASS
# ============================================================================

class FREDAPIClient:
    """FRED API client for fetching economic data"""
    
    def __init__(self, api_key=FRED_API_KEY):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"
    
    def get_series_data(self, series_id, limit=1, sort_order='desc'):
        """Get latest data for a specific FRED series"""
        url = "https://api.stlouisfed.org/fred/series/observations"
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

# ============================================================================
# CACHED DATA FUNCTIONS
# ============================================================================

@st.cache_data(ttl=3600)
def get_fred_bond_data():
    """Get government bond yields from FRED with fallback data"""
    fred_client = FREDAPIClient()
    bond_series = {
        'Poland_10Y': 'IRLTLT01PLM156N',
        'Germany_10Y': 'IRLTLT01DEM156N',
        'US_10Y': 'DGS10',
        'US_2Y': 'DGS2',
        'Euro_Area_10Y': 'IRLTLT01EZM156N'
    }
    
    try:
        data = fred_client.get_multiple_series(bond_series)
        
        # Add interpolated German short-term rates
        if 'Germany_10Y' in data:
            de_10y = data['Germany_10Y']['value']
            data['Germany_9M'] = {
                'value': max(de_10y - 0.25, 0.1),
                'date': data['Germany_10Y']['date'],
                'series_id': 'Interpolated',
                'source': 'FRED + Interpolation'
            }
        
        # If no data from API, use fallback
        if not data:
            raise Exception("No data from FRED API")
            
        return data
        
    except Exception as e:
        st.warning(f"Using fallback bond data: {e}")
        # Fallback data
        return {
            'Poland_10Y': {'value': 5.70, 'date': '2025-01-15', 'source': 'Fallback'},
            'Germany_10Y': {'value': 2.60, 'date': '2025-01-15', 'source': 'Fallback'},
            'Germany_9M': {'value': 2.35, 'date': '2025-01-15', 'source': 'Fallback'},
            'US_10Y': {'value': 4.25, 'date': '2025-01-15', 'source': 'Fallback'}
        }

@st.cache_data(ttl=300)
def get_eur_pln_rate():
    """Get current EUR/PLN from NBP API with fallback"""
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
        st.warning(f"Using fallback EUR/PLN rate: {e}")
        return {'rate': 4.25, 'date': '2025-01-15', 'source': 'Fallback'}

@st.cache_data(ttl=300)
def get_usd_pln_rate():
    """Get current USD/PLN from NBP API with fallback"""
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
        st.warning(f"Using fallback USD/PLN rate: {e}")
        return {'rate': 3.85, 'date': '2025-01-15', 'source': 'Fallback'}

# ============================================================================
# PROFESSIONAL WINDOW FORWARD CALCULATOR
# ============================================================================

class APIIntegratedForwardCalculator:
    """Professional window forward calculator using real API data"""
    
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
        
        # Professional pricing parameters (based on CSV analysis)
        self.points_factor = 0.70  # Client gets 70% of forward points
        self.risk_factor = 0.40    # Bank charges 40% of swap risk
    
    def calculate_theoretical_forward_points(self, spot_rate, pl_yield, de_yield, days):
        """Calculate theoretical forward points using bond yield spreads"""
        T = days / 365.0
        
        # Interest rate parity formula
        forward_rate = spot_rate * (1 + pl_yield/100 * T) / (1 + de_yield/100 * T)
        forward_points = forward_rate - spot_rate
        
        return {
            'forward_rate': forward_rate,
            'forward_points': forward_points,
            'days': days,
            'yield_spread': pl_yield - de_yield,
            'time_factor': T
        }
    
    def generate_api_forward_points_curve(self, spot_rate, pl_yield, de_yield, bid_ask_spread=0.002):
        """Generate complete forward points curve from API bond data"""
        curve_data = {}
        
        for tenor in self.tenors:
            months = self.tenor_months[tenor]
            days = months * 30  # Approximate days
            
            # Calculate theoretical forward points
            theoretical = self.calculate_theoretical_forward_points(spot_rate, pl_yield, de_yield, days)
            forward_points = theoretical['forward_points']
            
            # Add market spread
            bid_points = forward_points - (bid_ask_spread / 2)
            ask_points = forward_points + (bid_ask_spread / 2)
            mid_points = forward_points
            
            curve_data[tenor] = {
                "days": days,
                "months": months,
                "bid": bid_points,
                "ask": ask_points,
                "mid": mid_points,
                "theoretical_forward": theoretical['forward_rate'],
                "yield_spread": theoretical['yield_spread']
            }
        
        return curve_data
    
    def interpolate_points_to_window(self, window_days, forward_curve):
        """Interpolate forward points to the exact window start date"""
        # Convert window days to months
        window_months = window_days / 30.0
        
        # Get available tenors sorted by months
        available_data = [(data["months"], tenor, data) for tenor, data in forward_curve.items()]
        available_data.sort(key=lambda x: x[0])
        
        # Find interpolation bounds
        if window_months <= available_data[0][0]:
            # Extrapolate from shortest tenor
            months = available_data[0][0]
            data = available_data[0][2]
            ratio = window_months / months
            return {
                "bid": data["bid"] * ratio,
                "ask": data["ask"] * ratio,
                "mid": data["mid"] * ratio,
                "interpolation_method": f"Extrapolated from {available_data[0][1]}"
            }
        
        elif window_months >= available_data[-1][0]:
            # Use longest tenor
            data = available_data[-1][2]
            return {
                "bid": data["bid"],
                "ask": data["ask"], 
                "mid": data["mid"],
                "interpolation_method": f"Used {available_data[-1][1]}"
            }
        
        else:
            # Linear interpolation between two tenors
            for i in range(len(available_data) - 1):
                lower_months, lower_tenor, lower_data = available_data[i]
                upper_months, upper_tenor, upper_data = available_data[i + 1]
                
                if lower_months <= window_months <= upper_months:
                    # Interpolation ratio
                    ratio = (window_months - lower_months) / (upper_months - lower_months)
                    
                    return {
                        "bid": lower_data["bid"] + ratio * (upper_data["bid"] - lower_data["bid"]),
                        "ask": lower_data["ask"] + ratio * (upper_data["ask"] - lower_data["ask"]),
                        "mid": lower_data["mid"] + ratio * (upper_data["mid"] - lower_data["mid"]),
                        "interpolation_method": f"Interpolated between {lower_tenor} and {upper_tenor}"
                    }
    
    def calculate_swap_risk(self, window_days, points_to_window, volatility_factor=0.25):
        """Calculate swap risk based on window length and market volatility"""
        base_risk = abs(points_to_window) * volatility_factor
        time_adjustment = np.sqrt(window_days / 90)  # Scale with sqrt of time
        
        # Add minimum risk floor
        min_risk = 0.015
        calculated_risk = max(base_risk * time_adjustment, min_risk)
        
        return calculated_risk
    
    def calculate_professional_rates(self, spot_rate, points_to_window, swap_risk, min_profit_floor=0.0):
        """Calculate rates using professional window forward logic
        
        Based on CSV analysis:
        - FWD Client = Spot + (Points to Window × 0.70) - (Swap Risk × 0.40) 
        - FWD to Open = Spot + Points to Window
        - Profit = FWD to Open - FWD Client
        
        Args:
            min_profit_floor: Minimum guaranteed profit per EUR (adjusts pricing if needed)
        """
        
        # Standard calculation
        points_given_to_client = points_to_window * self.points_factor
        swap_risk_charged = swap_risk * self.risk_factor
        
        # Initial client rate
        fwd_client_initial = spot_rate + points_given_to_client - swap_risk_charged
        
        # Theoretical rate to window start (full points)
        fwd_to_open = spot_rate + points_to_window
        
        # Check minimum profit floor
        initial_profit = fwd_to_open - fwd_client_initial
        
        if initial_profit < min_profit_floor:
            # Adjust client rate to meet minimum profit requirement
            fwd_client = fwd_to_open - min_profit_floor
            profit_per_eur = min_profit_floor
            adjustment_made = True
            adjustment_amount = fwd_client_initial - fwd_client
        else:
            # Use standard calculation
            fwd_client = fwd_client_initial
            profit_per_eur = initial_profit
            adjustment_made = False
            adjustment_amount = 0.0
        
        return {
            'fwd_client': fwd_client,
            'fwd_to_open': fwd_to_open,
            'profit_per_eur': profit_per_eur,
            'points_given_to_client': points_given_to_client,
            'swap_risk_charged': swap_risk_charged,
            'effective_spread': profit_per_eur,
            'min_profit_adjustment': {
                'applied': adjustment_made,
                'amount': adjustment_amount,
                'original_profit': initial_profit,
                'floor_profit': min_profit_floor
            }
        }
    
    def calculate_pnl_analysis(self, profit_per_eur, nominal_amount_eur, leverage=1.0):
        """Calculate basic P&L analysis (kept for compatibility)"""
        
        # Basic calculations
        gross_profit_eur = profit_per_eur * nominal_amount_eur
        leveraged_profit = gross_profit_eur * leverage
        
        # Risk metrics
        profit_percentage = (profit_per_eur / 4.25) * 100  # Approximate spot base
        profit_bps = profit_per_eur * 10000
        
        return {
            'gross_profit_eur': gross_profit_eur,
            'leveraged_profit': leveraged_profit,
            'profit_percentage': profit_percentage,
            'profit_bps': profit_bps,
            'nominal_amount': nominal_amount_eur,
            'leverage_factor': leverage
        }
    
    def calculate_window_pnl_analysis(self, spot_rate, points_to_window, swap_risk, window_days, nominal_amount_eur, leverage=1.0):
        """Calculate comprehensive P&L analysis including window settlement scenarios
        
        CORRECT LOGIC:
        - Client always gets the same quoted rate
        - Bank profit varies based on hedging costs and timing
        
        Minimum Profit: Points to Window - Swap Risk (bank pays full hedging cost)
        Maximum Profit: Points to Window (optimal conditions, minimal hedging cost)
        """
        
        # Calculate professional rates (client rate stays constant)
        rates = self.calculate_professional_rates(spot_rate, points_to_window, swap_risk)
        
        # Basic P&L (current calculation) - this is the expected/average case
        basic_pnl = self.calculate_pnl_analysis(rates['profit_per_eur'], nominal_amount_eur, leverage)
        
        # Window settlement scenarios - CORRECT LOGIC
        
        # MINIMUM PROFIT: Bank faces maximum hedging costs
        # Profit = Points to Window - Full Swap Risk
        min_profit_per_eur = points_to_window - swap_risk
        min_gross_profit = min_profit_per_eur * nominal_amount_eur
        min_leveraged_profit = min_gross_profit * leverage
        min_profit_percentage = (min_profit_per_eur / spot_rate) * 100
        min_profit_bps = min_profit_per_eur * 10000
        
        # MAXIMUM PROFIT: Bank faces minimal hedging costs
        # Profit = Full Points to Window (optimal market conditions)
        max_profit_per_eur = points_to_window
        max_gross_profit = max_profit_per_eur * nominal_amount_eur
        max_leveraged_profit = max_gross_profit * leverage
        max_profit_percentage = (max_profit_per_eur / spot_rate) * 100
        max_profit_bps = max_profit_per_eur * 10000
        
        return {
            # Basic metrics (expected case)
            'basic_gross_profit_eur': basic_pnl['gross_profit_eur'],
            'basic_leveraged_profit': basic_pnl['leveraged_profit'],
            'basic_profit_percentage': basic_pnl['profit_percentage'],
            'basic_profit_bps': basic_pnl['profit_bps'],
            
            # Window settlement scenarios (CORRECTED)
            'min_profit_per_eur': min_profit_per_eur,
            'min_gross_profit': min_gross_profit,
            'min_leveraged_profit': min_leveraged_profit,
            'min_profit_percentage': min_profit_percentage,
            'min_profit_bps': min_profit_bps,
            
            'max_profit_per_eur': max_profit_per_eur,
            'max_gross_profit': max_gross_profit,
            'max_leveraged_profit': max_leveraged_profit,
            'max_profit_percentage': max_profit_percentage,
            'max_profit_bps': max_profit_bps,
            
            # Additional metrics
            'profit_range_eur': max_gross_profit - min_gross_profit,
            'profit_range_percentage': max_profit_percentage - min_profit_percentage,
            'expected_profit': (min_gross_profit + max_gross_profit) / 2,
            'risk_reward_ratio': (max_gross_profit / min_gross_profit) if min_gross_profit > 0 else float('inf'),
            
            # Settlement scenarios (CORRECTED DESCRIPTIONS)
            'window_open_settlement': {
                'scenario': 'High hedging costs',
                'bank_position': 'Pays full swap risk for hedging',
                'profit_eur': min_gross_profit,
                'profit_description': f'Minimum - Points({points_to_window:.4f}) - SwapRisk({swap_risk:.4f}) = {min_profit_per_eur:.4f}'
            },
            'window_end_settlement': {
                'scenario': 'Optimal market conditions',
                'bank_position': 'Minimal hedging costs',
                'profit_eur': max_gross_profit,
                'profit_description': f'Maximum - Full Points({points_to_window:.4f}) = {max_profit_per_eur:.4f}'
            },
            
            # Meta
            'nominal_amount': nominal_amount_eur,
            'leverage_factor': leverage,
            'window_days': window_days
        }

# ============================================================================
# MAIN APPLICATION INTERFACE
# ============================================================================

def create_professional_window_forward_tab():
    """Create the professional window forward calculator interface"""
    
    st.header("🚀 Professional Window Forward Calculator")
    st.markdown("*Real-time API data with professional pricing logic*")
    
    # API Key Configuration Section
    with st.expander("🔧 API Configuration", expanded=False):
        st.markdown("""
        **FRED API Key Setup:**
        1. Get free API key from: https://fred.stlouisfed.org/docs/api/api_key.html
        2. Add to Streamlit secrets.toml: `FRED_API_KEY = "your_key_here"`
        3. Or modify the code directly to include your key
        
        **Current Status:**
        """)
        
        if FRED_API_KEY == "demo":
            st.warning("⚠️ Using demo mode - limited API access")
        else:
            st.success("✅ FRED API key configured")
    
    # Load real market data
    with st.spinner("📡 Loading real-time market data..."):
        bond_data = get_fred_bond_data()
        forex_data = get_eur_pln_rate()
    
    # Initialize calculator
    calculator = APIIntegratedForwardCalculator(FREDAPIClient())
    
    # ============================================================================
    # MARKET DATA DISPLAY
    # ============================================================================
    
    st.subheader("📊 Live Market Data")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        spot_rate = forex_data['rate']
        st.metric(
            "EUR/PLN Spot",
            f"{spot_rate:.4f}",
            help=f"Source: {forex_data['source']} | Updated: {forex_data['date']}"
        )
    
    with col2:
        pl_yield = bond_data['Poland_10Y']['value'] if 'Poland_10Y' in bond_data else 5.70
        st.metric(
            "Poland 10Y Yield",
            f"{pl_yield:.2f}%",
            help=f"Source: {bond_data.get('Poland_10Y', {}).get('source', 'Fallback')}"
        )
    
    with col3:
        de_yield = bond_data['Germany_9M']['value'] if 'Germany_9M' in bond_data else 2.35
        st.metric(
            "Germany Yield",
            f"{de_yield:.2f}%", 
            help=f"Source: {bond_data.get('Germany_9M', {}).get('source', 'Fallback')}"
        )
    
    with col4:
        spread = pl_yield - de_yield
        st.metric(
            "PL-DE Spread",
            f"{spread:.2f}pp",
            help="Yield differential driving forward points"
        )
    
    # ============================================================================
    # CONFIGURATION PARAMETERS
    # ============================================================================
    
    st.markdown("---")
    st.subheader("⚙️ Deal Configuration")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        window_days = st.number_input(
            "Window Length (days):",
            value=90,
            min_value=30,
            max_value=365,
            step=5,
            help="Length of the window forward period"
        )
    
    with col2:
        nominal_amount = st.number_input(
            "Nominal Amount (EUR):",
            value=2_500_000,
            min_value=100_000,
            max_value=100_000_000,
            step=100_000,
            format="%d",
            help="Deal notional amount"
        )
    
    with col3:
        leverage = st.number_input(
            "Leverage Factor:",
            value=1.0,
            min_value=1.0,
            max_value=3.0,
            step=0.1,
            help="Risk leverage for P&L calculation"
        )
    
    # Advanced parameters
    with st.expander("🔧 Advanced Pricing Parameters"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            points_factor = st.slider(
                "Points Factor (% to client):",
                min_value=0.60,
                max_value=0.85,
                value=0.70,
                step=0.01,
                help="Percentage of forward points given to client"
            )
        
        with col2:
            risk_factor = st.slider(
                "Risk Factor (% charged):",
                min_value=0.30,
                max_value=0.60,
                value=0.40,
                step=0.01,
                help="Percentage of swap risk charged to client"
            )
        
        with col3:
            bid_ask_spread = st.number_input(
                "Bid-Ask Spread:",
                value=0.002,
                min_value=0.001,
                max_value=0.005,
                step=0.0005,
                format="%.4f",
                help="Market bid-ask spread in forward points"
            )
        
        # Additional parameters row
        col4, col5, col6 = st.columns(3)
        
        with col4:
            minimum_profit_floor = st.number_input(
                "Min Profit Floor (PLN/EUR):",
                value=0.000,
                min_value=-0.020,
                max_value=0.020,
                step=0.001,
                format="%.4f",
                help="Minimum guaranteed profit per EUR (0 = allow natural range)"
            )
    
    # Update calculator parameters
    calculator.points_factor = points_factor
    calculator.risk_factor = risk_factor
    
    # ============================================================================
    # REAL-TIME CALCULATIONS
    # ============================================================================
    
    st.markdown("---")
    st.subheader("🔢 Live Forward Points Generation")
    
    # Generate forward curve from API data
    forward_curve = calculator.generate_api_forward_points_curve(
        spot_rate, pl_yield, de_yield, bid_ask_spread
    )
    
    # ============================================================================
    # CLIENT PRICE CURVE VISUALIZATION
    # ============================================================================
    
    st.markdown("---")
    st.subheader("📈 Client Price Curve Analysis")
    
    # Generate complete client price curve data
    client_curve_data = []
    for tenor, curve_data in forward_curve.items():
        tenor_points = curve_data["mid"]
        tenor_swap_risk = calculator.calculate_swap_risk(curve_data["days"], tenor_points)
        tenor_rates = calculator.calculate_professional_rates(spot_rate, tenor_points, tenor_swap_risk)
        
        client_curve_data.append({
            'tenor': tenor,
            'days': curve_data["days"],
            'months': curve_data["months"],
            'client_rate': tenor_rates['fwd_client'],
            'theoretical_rate': tenor_rates['fwd_to_open'],
            'spot_rate': spot_rate,
            'profit_per_eur': tenor_rates['profit_per_eur'],
            'forward_points': tenor_points,
            'swap_risk': tenor_swap_risk
        })
    
    # Create client price curve chart
    fig_client = go.Figure()
    
    # Extract data for plotting
    days_list = [item['days'] for item in client_curve_data]
    client_rates = [item['client_rate'] for item in client_curve_data]
    theoretical_rates = [item['theoretical_rate'] for item in client_curve_data]
    tenor_names = [item['tenor'] for item in client_curve_data]
    
    # Add spot rate line
    fig_client.add_trace(
        go.Scatter(
            x=days_list,
            y=[spot_rate] * len(days_list),
            mode='lines',
            name='Spot Rate',
            line=dict(color='black', width=2, dash='solid'),
            hovertemplate='Spot Rate: %{y:.4f}<extra></extra>'
        )
    )
    
    # Add theoretical forward curve
    fig_client.add_trace(
        go.Scatter(
            x=days_list,
            y=theoretical_rates,
            mode='lines+markers',
            name='Theoretical Forward Curve',
            line=dict(color='blue', width=2, dash='dash'),
            marker=dict(size=6, color='blue'),
            hovertemplate='<b>%{text}</b><br>Days: %{x}<br>Theoretical Rate: %{y:.4f}<extra></extra>',
            text=tenor_names
        )
    )
    
    # Add client rate curve (main curve)
    fig_client.add_trace(
        go.Scatter(
            x=days_list,
            y=client_rates,
            mode='lines+markers',
            name='Client Rate Curve',
            line=dict(color='red', width=3),
            marker=dict(size=8, color='red'),
            hovertemplate='<b>%{text}</b><br>Days: %{x}<br>Client Rate: %{y:.4f}<br>vs Spot: %{customdata:.4f}<extra></extra>',
            text=tenor_names,
            customdata=[rate - spot_rate for rate in client_rates]
        )
    )
    
    # Highlight selected window length
    selected_client_rate = None
    selected_theoretical_rate = None
    for item in client_curve_data:
        if abs(item['days'] - window_days) <= 15:
            selected_client_rate = item['client_rate']
            selected_theoretical_rate = item['theoretical_rate']
            break
    
    if selected_client_rate:
        fig_client.add_trace(
            go.Scatter(
                x=[window_days],
                y=[selected_client_rate],
                mode='markers',
                name=f'Selected Window ({window_days}D)',
                marker=dict(size=15, color='orange', symbol='diamond', line=dict(width=2, color='black')),
                hovertemplate=f'<b>Selected: {window_days} Days</b><br>Client Rate: %{{y:.4f}}<extra></extra>'
            )
        )
    
    # Add profit area (difference between theoretical and client rates)
    fig_client.add_trace(
        go.Scatter(
            x=days_list,
            y=theoretical_rates,
            fill='tonexty',
            mode='none',
            name='Bank Profit Area',
            fillcolor='rgba(0, 255, 0, 0.2)',
            hoverinfo='skip'
        )
    )
    
    # Update layout
    fig_client.update_layout(
        title="Client Rate Curve vs Theoretical Forward Curve",
        xaxis_title="Days",
        yaxis_title="EUR/PLN Rate",
        height=500,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Add grid and formatting
    fig_client.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    fig_client.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    
    st.plotly_chart(fig_client, use_container_width=True)
    
    # Client curve analysis table
    st.subheader("📊 Client Rate Curve Analysis")
    
    client_analysis_data = []
    for item in client_curve_data:
        spread_vs_spot = (item['client_rate'] - spot_rate) * 10000  # in pips
        annualized_premium = ((item['client_rate'] / spot_rate - 1) * (365 / item['days']) * 100)
        
        client_analysis_data.append({
            "Tenor": item['tenor'],
            "Days": item['days'],
            "Client Rate": f"{item['client_rate']:.4f}",
            "vs Spot (pips)": f"{spread_vs_spot:.1f}",
            "Annualized Premium": f"{annualized_premium:.2f}%",
            "Theoretical Rate": f"{item['theoretical_rate']:.4f}",
            "Bank Spread": f"{item['profit_per_eur']:.4f}",
            "Forward Points": f"{item['forward_points']:.4f}",
            "Swap Risk": f"{item['swap_risk']:.4f}"
        })
    
    df_client_analysis = pd.DataFrame(client_analysis_data)
    
    # Highlight selected window
    def highlight_selected_window_client(row):
        if abs(row['Days'] - window_days) <= 15:
            return ['background-color: #fff3cd; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    st.dataframe(
        df_client_analysis.style.apply(highlight_selected_window_client, axis=1),
        use_container_width=True,
        height=300
    )
    
    st.subheader("📋 Complete 12-Month Window Forward Pricing Curve")
    
    # Generate pricing for all 12 tenors
    complete_pricing_data = []
    
    for tenor, curve_data in forward_curve.items():
        tenor_days = curve_data["days"]
        tenor_points = curve_data["mid"]
        
        # Calculate swap risk for this tenor
        tenor_swap_risk = calculator.calculate_swap_risk(tenor_days, tenor_points)
        
        # Calculate professional rates for this tenor
        tenor_rates = calculator.calculate_professional_rates(spot_rate, tenor_points, tenor_swap_risk)
        
        # Calculate enhanced P&L for this tenor
        tenor_enhanced_pnl = calculator.calculate_window_pnl_analysis(
            spot_rate, tenor_points, tenor_swap_risk, tenor_days, nominal_amount, leverage
        )
        
        complete_pricing_data.append({
            "Tenor": tenor,
            "Window Days": tenor_days,
            "Window Months": f"{curve_data['months']:.1f}M",
            "Forward Points": f"{tenor_points:.4f}",
            "Swap Risk": f"{tenor_swap_risk:.4f}",
            "Client Rate": f"{tenor_rates['fwd_client']:.4f}",
            "Theoretical Rate": f"{tenor_rates['fwd_to_open']:.4f}",
            "Profit/EUR": f"{tenor_rates['profit_per_eur']:.4f}",
            "Min Profit": f"€{tenor_enhanced_pnl['min_gross_profit']:,.0f}",
            "Max Profit": f"€{tenor_enhanced_pnl['max_gross_profit']:,.0f}",
            "Expected Profit": f"€{tenor_enhanced_pnl['expected_profit']:,.0f}",
            "Profit Range": f"€{tenor_enhanced_pnl['profit_range_eur']:,.0f}",
            "Profit %": f"{tenor_enhanced_pnl['basic_profit_percentage']:.2f}%",
            "Profit BPS": f"{tenor_enhanced_pnl['basic_profit_bps']:.1f}",
            "Yield Spread": f"{curve_data['yield_spread']:.2f}pp"
        })
    
    df_complete_pricing = pd.DataFrame(complete_pricing_data)
    
    # Highlight the selected window length
    def highlight_selected_window(row):
        if abs(row['Window Days'] - window_days) <= 15:  # Within 15 days tolerance
            return ['background-color: #e8f5e8; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    # Display the complete pricing table
    st.dataframe(
        df_complete_pricing.style.apply(highlight_selected_window, axis=1),
        use_container_width=True,
        height=400
    )
    
    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_profit_per_eur = df_complete_pricing['Profit/EUR'].str.replace('', '').astype(float).mean()
        st.metric(
            "Avg Profit/EUR", 
            f"{avg_profit_per_eur:.4f}",
            help="Average profit per EUR across all tenors"
        )
    
    with col2:
        max_profit_tenor = df_complete_pricing.loc[df_complete_pricing['Profit/EUR'].str.replace('', '').astype(float).idxmax(), 'Tenor']
        max_profit_value = df_complete_pricing['Profit/EUR'].str.replace('', '').astype(float).max()
        st.metric(
            "Best Tenor", 
            f"{max_profit_tenor}",
            delta=f"{max_profit_value:.4f}",
            help="Most profitable tenor"
        )
    
    with col3:
        total_expected_profit = df_complete_pricing['Expected Profit'].str.replace('€', '').str.replace(',', '').astype(float).sum()
        st.metric(
            "Total Expected Value", 
            f"€{total_expected_profit:,.0f}",
            help="Sum of all tenor expected profits"
        )
    
    with col4:
        profit_range = df_complete_pricing['Profit/EUR'].str.replace('', '').astype(float).max() - df_complete_pricing['Profit/EUR'].str.replace('', '').astype(float).min()
        st.metric(
            "Profit Range", 
            f"{profit_range:.4f}",
            help="Difference between best and worst tenor"
        )
    
    # Advanced curve analysis
    with st.expander("📊 Detailed Forward Points Curve Analysis"):
        curve_analysis_data = []
        for tenor, data in forward_curve.items():
            curve_analysis_data.append({
                "Tenor": tenor,
                "Days": data["days"],
                "Bid Points": f"{data['bid']:.4f}",
                "Ask Points": f"{data['ask']:.4f}",
                "Mid Points": f"{data['mid']:.4f}",
                "Theoretical Forward": f"{data['theoretical_forward']:.4f}",
                "Yield Spread": f"{data['yield_spread']:.2f}pp",
                "Annualized Premium": f"{((data['theoretical_forward']/spot_rate - 1) * (365/data['days']) * 100):.2f}%"
            })
        
        df_curve_analysis = pd.DataFrame(curve_analysis_data)
        st.dataframe(df_curve_analysis, use_container_width=True)
    
    # ============================================================================
    # PORTFOLIO WINDOW FORWARD CALCULATIONS (ALL 12 TENORS)
    # ============================================================================
    
    st.markdown("---")
    st.subheader("🔢 Portfolio Window Forward Generation")
    st.markdown(f"*All 12 tenors converted to window forwards with {window_days}-day flexibility*")
    
    # Generate window forward pricing for ALL 12 tenors with same window length
    portfolio_window_data = {}
    portfolio_totals = {
        'total_points_to_window': 0,
        'total_swap_risk': 0,
        'total_min_profit': 0,
        'total_max_profit': 0,
        'total_expected_profit': 0,
        'total_client_premium': 0,
        'total_notional': 0
    }
    
    for tenor, curve_data in forward_curve.items():
        tenor_points = curve_data["mid"]
        
        # Key change: Use the SAME window_days for ALL tenors
        # This makes all of them window forwards with the same flexibility
        tenor_window_swap_risk = calculator.calculate_swap_risk(window_days, tenor_points)
        
        # Calculate rates for this tenor as window forward
        tenor_rates = calculator.calculate_professional_rates(
            spot_rate, tenor_points, tenor_window_swap_risk, minimum_profit_floor
        )
        
        # Window forward profit calculations (same logic for all tenors)
        window_min_profit_per_eur = tenor_points - tenor_window_swap_risk
        window_max_profit_per_eur = tenor_points
        window_expected_profit_per_eur = (window_min_profit_per_eur + window_max_profit_per_eur) / 2
        
        # Convert to totals
        window_min_profit_total = window_min_profit_per_eur * nominal_amount
        window_max_profit_total = window_max_profit_per_eur * nominal_amount
        window_expected_profit_total = window_expected_profit_per_eur * nominal_amount
        
        # Store individual tenor data
        portfolio_window_data[tenor] = {
            'original_days': curve_data["days"],
            'window_days': window_days,
            'points': tenor_points,
            'swap_risk': tenor_window_swap_risk,
            'client_rate': tenor_rates['fwd_client'],
            'theoretical_rate': tenor_rates['fwd_to_open'],
            'min_profit_per_eur': window_min_profit_per_eur,
            'max_profit_per_eur': window_max_profit_per_eur,
            'expected_profit_per_eur': window_expected_profit_per_eur,
            'min_profit_total': window_min_profit_total,
            'max_profit_total': window_max_profit_total,
            'expected_profit_total': window_expected_profit_total
        }
        
        # Add to portfolio totals
        portfolio_totals['total_points_to_window'] += tenor_points * nominal_amount
        portfolio_totals['total_swap_risk'] += tenor_window_swap_risk * nominal_amount
        portfolio_totals['total_min_profit'] += window_min_profit_total
        portfolio_totals['total_max_profit'] += window_max_profit_total
        portfolio_totals['total_expected_profit'] += window_expected_profit_total
        portfolio_totals['total_client_premium'] += (tenor_rates['fwd_client'] - spot_rate) * nominal_amount
        portfolio_totals['total_notional'] += nominal_amount
    
    # Calculate portfolio averages
    portfolio_avg_points = portfolio_totals['total_points_to_window'] / portfolio_totals['total_notional']
    portfolio_avg_swap_risk = portfolio_totals['total_swap_risk'] / portfolio_totals['total_notional']
    portfolio_avg_min_profit = portfolio_totals['total_min_profit'] / portfolio_totals['total_notional']
    portfolio_avg_max_profit = portfolio_totals['total_max_profit'] / portfolio_totals['total_notional']
    
    # ============================================================================
    # PORTFOLIO RESULTS DISPLAY
    # ============================================================================
    
    st.subheader("💰 Portfolio Window Forward Results")
    st.markdown(f"*All 12 tenors with {window_days}-day window flexibility*")
    
    # Portfolio-level key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Portfolio Avg Points",
            f"{portfolio_avg_points:.4f}",
            help=f"Weighted average forward points across all 12 tenors"
        )
    
    with col2:
        st.metric(
            "Portfolio Avg Swap Risk",
            f"{portfolio_avg_swap_risk:.4f}",
            help=f"Average swap risk for {window_days}-day windows"
        )
    
    with col3:
        portfolio_avg_client_rate = spot_rate + portfolio_avg_points * points_factor - portfolio_avg_swap_risk * risk_factor
        st.metric(
            "Portfolio Avg Client Rate",
            f"{portfolio_avg_client_rate:.4f}",
            delta=f"{portfolio_avg_client_rate - spot_rate:.4f}",
            help="Average client rate across all window forwards"
        )
    
    with col4:
        portfolio_avg_profit = (portfolio_avg_min_profit + portfolio_avg_max_profit) / 2
        st.metric(
            "Portfolio Avg Profit/EUR",
            f"{portfolio_avg_profit:.4f} PLN",
            help="Average profit per EUR across all tenors"
        )
    
    # Detailed breakdown for portfolio
    st.markdown("---")
    st.subheader("📈 Portfolio Pricing Breakdown")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("**🔍 Portfolio Rate Calculation:**")
        st.code(f"""
PORTFOLIO WINDOW FORWARD SUMMARY:
Window Length for All Tenors:    {window_days} days
Total Tenors:                     12
Total Notional:                   €{portfolio_totals['total_notional']:,}

AVERAGE CALCULATIONS:
Avg Forward Points:               {portfolio_avg_points:.4f}
Avg Points Given to Client (70%): {portfolio_avg_points * points_factor:.4f}
Avg Swap Risk:                    {portfolio_avg_swap_risk:.4f}
Avg Risk Charged to Client (40%): {portfolio_avg_swap_risk * risk_factor:.4f}

PORTFOLIO CLIENT RATE FORMULA:
{spot_rate:.4f} + {portfolio_avg_points * points_factor:.4f} - {portfolio_avg_swap_risk * risk_factor:.4f} = {portfolio_avg_client_rate:.4f}

PORTFOLIO PROFIT RANGE:
Min: {portfolio_avg_min_profit:.4f} PLN/EUR
Max: {portfolio_avg_max_profit:.4f} PLN/EUR
Avg: {portfolio_avg_profit:.4f} PLN/EUR
        """)
    
    with col2:
        st.markdown("**💼 Portfolio P&L Analysis:**")
        
        # Portfolio P&L metrics with min/max scenarios
        col_min, col_max = st.columns(2)
        
        with col_min:
            st.markdown("**📉 Portfolio Minimum**")
            st.caption("*High hedging costs scenario*")
            st.metric(
                "Min Profit", 
                f"€{portfolio_totals['total_min_profit']:,.0f}",
                delta=f"{(portfolio_avg_min_profit/spot_rate)*100:.2f}%",
                help="Sum of all minimum profits"
            )
            st.write(f"**{(portfolio_avg_min_profit * 10000):.1f} bps avg**")
        
        with col_max:
            st.markdown("**📈 Portfolio Maximum**")
            st.caption("*Optimal market conditions*")
            st.metric(
                "Max Profit", 
                f"€{portfolio_totals['total_max_profit']:,.0f}",
                delta=f"{(portfolio_avg_max_profit/spot_rate)*100:.2f}%",
                help="Sum of all maximum profits"
            )
            st.write(f"**{(portfolio_avg_max_profit * 10000):.1f} bps avg**")
        
        # Portfolio summary metrics
        st.markdown("**📊 Portfolio Summary:**")
        st.metric("Expected Profit", f"€{portfolio_totals['total_expected_profit']:,.0f}", help="Average scenario")
        profit_range_eur = portfolio_totals['total_max_profit'] - portfolio_totals['total_min_profit']
        st.metric("Profit Range", f"€{profit_range_eur:,.0f}", help="Max - Min profit")
        
        risk_reward_ratio = portfolio_totals['total_max_profit'] / portfolio_totals['total_min_profit'] if portfolio_totals['total_min_profit'] > 0 else float('inf')
        st.metric("Risk/Reward", f"{risk_reward_ratio:.1f}x", help="Max/Min profit ratio")
        
        # Risk assessment for portfolio
        profit_volatility = (profit_range_eur / portfolio_totals['total_expected_profit']) * 100 if portfolio_totals['total_expected_profit'] > 0 else 0
        if profit_volatility < 20:
            st.success("✅ Low portfolio volatility - stable profit range")
        elif profit_volatility < 40:
            st.info("ℹ️ Moderate portfolio volatility - standard risk")
        else:
            st.warning("⚠️ High portfolio volatility - significant profit variability")
    
    # ============================================================================
    # DEAL SUMMARY
    # ============================================================================
    
    st.markdown("---")
    st.subheader("📋 Deal Summary")
    
    with st.container():
        summary_col1, summary_col2 = st.columns([1, 1])
        
        with summary_col1:
            st.markdown(f"""
            <div class="metric-card">
                <h4>💼 Window Forward Deal Structure</h4>
                <p><strong>Product:</strong> {window_days}-Day EUR/PLN Window Forward</p>
                <p><strong>Notional:</strong> €{nominal_amount:,}</p>
                <p><strong>Spot Rate:</strong> {spot_rate:.4f}</p>
                <p><strong>Client Forward Rate:</strong> {rates['fwd_client']:.4f}</p>
                <p><strong>Points Factor:</strong> {points_factor:.1%} (Industry: 70%)</p>
                <p><strong>Risk Factor:</strong> {risk_factor:.1%} (Industry: 40%)</p>
            </div>
            """, unsafe_allow_html=True)
        
        with summary_col2:
            st.markdown(f"""
            <div class="metric-card">
                <h4>💰 Portfolio Financial Summary</h4>
                <p><strong>Total Expected Profit:</strong> €{portfolio_totals['total_expected_profit']:,.0f}</p>
                <p><strong>Portfolio Minimum:</strong> €{portfolio_totals['total_min_profit']:,.0f}</p>
                <p><strong>Portfolio Maximum:</strong> €{portfolio_totals['total_max_profit']:,.0f}</p>
                <p><strong>Average Profit/EUR:</strong> {portfolio_avg_profit:.4f} PLN</p>
                <p><strong>Total Notional:</strong> €{portfolio_totals['total_notional']:,}</p>
                <p><strong>Average Client Rate:</strong> {portfolio_avg_client_rate:.4f}</p>
            </div>
            """, unsafe_allow_html=True)

# ============================================================================
# MAIN APPLICATION ENTRY POINT
# ============================================================================

def main():
    """Main application entry point"""
    
    # Header
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 2rem;">
        <div style="background: linear-gradient(45deg, #667eea, #764ba2); width: 60px; height: 60px; border-radius: 10px; margin-right: 1rem; display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 2rem;">🚀</span>
        </div>
        <h1 style="margin: 0; color: #2c3e50;">Professional FX Trading Calculator</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("*Advanced Window Forward Pricing with Real-Time API Integration*")
    
    # Run the main calculator
    create_professional_window_forward_tab()

# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == "__main__":
    main()
