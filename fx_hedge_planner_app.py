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
FRED_API_KEY = st.secrets.get("FRED_API_KEY", "f04a11751a8bb9fed2e9e321aa76e783")  # Uses Streamlit secrets or demo

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
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
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
        
        # Polskie nazwy tenorów z datami
        today = datetime.now()
        self.tenors = {
            "1M": {
                "name": "1 miesiąc",
                "months": 1,
                "days": 30,
                "okno_od": (today + timedelta(days=30)).strftime("%d.%m.%Y"),
                "rozliczenie_do": (today + timedelta(days=60)).strftime("%d.%m.%Y")
            },
            "2M": {
                "name": "2 miesiące", 
                "months": 2,
                "days": 60,
                "okno_od": (today + timedelta(days=60)).strftime("%d.%m.%Y"),
                "rozliczenie_do": (today + timedelta(days=90)).strftime("%d.%m.%Y")
            },
            "3M": {
                "name": "3 miesiące",
                "months": 3, 
                "days": 90,
                "okno_od": (today + timedelta(days=90)).strftime("%d.%m.%Y"),
                "rozliczenie_do": (today + timedelta(days=120)).strftime("%d.%m.%Y")
            },
            "4M": {
                "name": "4 miesiące",
                "months": 4,
                "days": 120,
                "okno_od": (today + timedelta(days=120)).strftime("%d.%m.%Y"),
                "rozliczenie_do": (today + timedelta(days=150)).strftime("%d.%m.%Y")
            },
            "5M": {
                "name": "5 miesięcy",
                "months": 5,
                "days": 150,
                "okno_od": (today + timedelta(days=150)).strftime("%d.%m.%Y"),
                "rozliczenie_do": (today + timedelta(days=180)).strftime("%d.%m.%Y")
            },
            "6M": {
                "name": "6 miesięcy",
                "months": 6,
                "days": 180,
                "okno_od": (today + timedelta(days=180)).strftime("%d.%m.%Y"),
                "rozliczenie_do": (today + timedelta(days=210)).strftime("%d.%m.%Y")
            },
            "7M": {
                "name": "7 miesięcy",
                "months": 7,
                "days": 210,
                "okno_od": (today + timedelta(days=210)).strftime("%d.%m.%Y"),
                "rozliczenie_do": (today + timedelta(days=240)).strftime("%d.%m.%Y")
            },
            "8M": {
                "name": "8 miesięcy",
                "months": 8,
                "days": 240,
                "okno_od": (today + timedelta(days=240)).strftime("%d.%m.%Y"),
                "rozliczenie_do": (today + timedelta(days=270)).strftime("%d.%m.%Y")
            },
            "9M": {
                "name": "9 miesięcy",
                "months": 9,
                "days": 270,
                "okno_od": (today + timedelta(days=270)).strftime("%d.%m.%Y"),
                "rozliczenie_do": (today + timedelta(days=300)).strftime("%d.%m.%Y")
            },
            "10M": {
                "name": "10 miesięcy",
                "months": 10,
                "days": 300,
                "okno_od": (today + timedelta(days=300)).strftime("%d.%m.%Y"),
                "rozliczenie_do": (today + timedelta(days=330)).strftime("%d.%m.%Y")
            },
            "11M": {
                "name": "11 miesięcy", 
                "months": 11,
                "days": 330,
                "okno_od": (today + timedelta(days=330)).strftime("%d.%m.%Y"),
                "rozliczenie_do": (today + timedelta(days=360)).strftime("%d.%m.%Y")
            },
            "12M": {
                "name": "12 miesięcy",
                "months": 12,
                "days": 360,
                "okno_od": (today + timedelta(days=360)).strftime("%d.%m.%Y"),
                "rozliczenie_do": (today + timedelta(days=390)).strftime("%d.%m.%Y")
            }
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
        
        for tenor_key, tenor_info in self.tenors.items():
            months = tenor_info["months"]
            days = tenor_info["days"]
            
            # Calculate theoretical forward points
            theoretical = self.calculate_theoretical_forward_points(spot_rate, pl_yield, de_yield, days)
            forward_points = theoretical['forward_points']
            
            # Add market spread
            bid_points = forward_points - (bid_ask_spread / 2)
            ask_points = forward_points + (bid_ask_spread / 2)
            mid_points = forward_points
            
            curve_data[tenor_key] = {
                "name": tenor_info["name"],
                "days": days,
                "months": months,
                "okno_od": tenor_info["okno_od"],
                "rozliczenie_do": tenor_info["rozliczenie_do"],
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
        """Calculate rates using professional window forward logic"""
        
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
        """Calculate basic P&L analysis - CORRECTED FOR PLN"""
        
        # CORRECTED: profit_per_eur is in PLN, so total profit should be in PLN
        gross_profit_pln = profit_per_eur * nominal_amount_eur  # PLN total profit
        leveraged_profit_pln = gross_profit_pln * leverage
        
        # Risk metrics
        profit_percentage = (profit_per_eur / 4.25) * 100  # PLN profit as % of spot rate
        profit_bps = profit_per_eur * 10000  # Basis points
        
        return {
            'gross_profit_pln': gross_profit_pln,
            'leveraged_profit_pln': leveraged_profit_pln,
            'profit_percentage': profit_percentage,
            'profit_bps': profit_bps,
            'nominal_amount': nominal_amount_eur,
            'leverage_factor': leverage
        }
    
    def calculate_window_pnl_analysis(self, spot_rate, points_to_window, swap_risk, window_days, nominal_amount_eur, leverage=1.0):
        """Calculate comprehensive P&L analysis including window settlement scenarios"""
        
        # Calculate professional rates (client rate stays constant)
        rates = self.calculate_professional_rates(spot_rate, points_to_window, swap_risk)
        
        # Basic P&L (current calculation) - this is the expected/average case
        basic_pnl = self.calculate_pnl_analysis(rates['profit_per_eur'], nominal_amount_eur, leverage)
        
        # Window settlement scenarios - CORRECTED LOGIC BASED ON BANK SPREAD
        
        # MINIMUM PROFIT: Bank's guaranteed spread from client pricing
        # This is the bank spread = theoretical_forward - client_rate
        # Bank always gets this profit regardless of settlement timing
        min_profit_per_eur = rates['fwd_to_open'] - rates['fwd_client']  # Bank spread
        min_gross_profit_pln = min_profit_per_eur * nominal_amount_eur
        min_leveraged_profit_pln = min_gross_profit_pln * leverage
        min_profit_percentage = (min_profit_per_eur / spot_rate) * 100
        min_profit_bps = min_profit_per_eur * 10000
        
        # MAXIMUM PROFIT: Bank spread + additional benefits from optimal hedging
        # In best case scenario, bank saves on hedging costs
        hedging_savings = swap_risk * 0.6  # Bank saves 60% of expected swap risk
        max_profit_per_eur = min_profit_per_eur + hedging_savings
        max_gross_profit_pln = max_profit_per_eur * nominal_amount_eur
        max_leveraged_profit_pln = max_gross_profit_pln * leverage
        max_profit_percentage = (max_profit_per_eur / spot_rate) * 100
        max_profit_bps = max_profit_per_eur * 10000
        
        return {
            # Basic metrics (expected case) - CORRECTED KEYS
            'basic_gross_profit_pln': basic_pnl['gross_profit_pln'],
            'basic_leveraged_profit_pln': basic_pnl['leveraged_profit_pln'],
            'basic_profit_percentage': basic_pnl['profit_percentage'],
            'basic_profit_bps': basic_pnl['profit_bps'],
            
            # Window settlement scenarios (CORRECTED TO BANK SPREAD LOGIC)
            'min_profit_per_eur': min_profit_per_eur,
            'min_gross_profit_pln': min_gross_profit_pln,
            'min_leveraged_profit_pln': min_leveraged_profit_pln,
            'min_profit_percentage': min_profit_percentage,
            'min_profit_bps': min_profit_bps,
            
            'max_profit_per_eur': max_profit_per_eur,
            'max_gross_profit_pln': max_gross_profit_pln,
            'max_leveraged_profit_pln': max_leveraged_profit_pln,
            'max_profit_percentage': max_profit_percentage,
            'max_profit_bps': max_profit_bps,
            
            # Additional metrics (ALL PLN)
            'profit_range_pln': max_gross_profit_pln - min_gross_profit_pln,
            'profit_range_percentage': max_profit_percentage - min_profit_percentage,
            'expected_profit_pln': (min_gross_profit_pln + max_gross_profit_pln) / 2,
            'risk_reward_ratio': (max_gross_profit_pln / min_gross_profit_pln) if min_gross_profit_pln > 0 else float('inf'),
            
            # Settlement scenarios
            'window_open_settlement': {
                'scenario': 'Guaranteed bank spread',
                'bank_position': 'Bank always earns client pricing spread',
                'profit_pln': min_gross_profit_pln,
                'profit_description': f'Minimum - Bank Spread: {rates["fwd_to_open"]:.4f} - {rates["fwd_client"]:.4f} = {min_profit_per_eur:.4f} PLN/EUR'
            },
            'window_end_settlement': {
                'scenario': 'Bank spread + hedging savings',
                'bank_position': 'Bank earns spread plus saves on hedging',
                'profit_pln': max_gross_profit_pln,
                'profit_description': f'Maximum - Bank Spread + Hedging Savings = {max_profit_per_eur:.4f} PLN/EUR'
            },
            
            # Meta
            'nominal_amount': nominal_amount_eur,
            'leverage_factor': leverage,
            'window_days': window_days,
            'hedging_savings': hedging_savings
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
    # PORTFOLIO WINDOW FORWARD CALCULATIONS (ALL 12 TENORS)
    # ============================================================================
    
    st.markdown("---")
    st.subheader("🔢 Portfolio Window Forward Generation")
    st.markdown(f"*All 12 tenors converted to window forwards with {window_days}-day flexibility*")
    
    # Generate forward curve from API data
    forward_curve = calculator.generate_api_forward_points_curve(
        spot_rate, pl_yield, de_yield, bid_ask_spread
    )
    
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
        
        # Calculate enhanced P&L for this tenor
        tenor_enhanced_pnl = calculator.calculate_window_pnl_analysis(
            spot_rate, tenor_points, tenor_window_swap_risk, window_days, nominal_amount, leverage
        )
        
        # Use the correct PLN values from enhanced P&L
        window_min_profit_total = tenor_enhanced_pnl['min_gross_profit_pln']
        window_max_profit_total = tenor_enhanced_pnl['max_gross_profit_pln'] 
        window_expected_profit_total = tenor_enhanced_pnl['expected_profit_pln']
        
        # Window forward profit calculations using CORRECTED LOGIC
        # Min = Bank Spread (guaranteed), Max = Bank Spread + Hedging Savings
        tenor_rates = calculator.calculate_professional_rates(
            spot_rate, tenor_points, tenor_window_swap_risk, minimum_profit_floor
        )
        
        window_min_profit_per_eur = tenor_rates['fwd_to_open'] - tenor_rates['fwd_client']  # Bank spread
        window_max_profit_per_eur = window_min_profit_per_eur + (tenor_window_swap_risk * 0.6)  # + hedging savings
        window_expected_profit_per_eur = (window_min_profit_per_eur + window_max_profit_per_eur) / 2
        
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
            st.caption("*Guaranteed bank spread*")
            st.metric(
                "Min Profit", 
                f"{portfolio_totals['total_min_profit']:,.0f} PLN",
                delta=f"{(portfolio_avg_min_profit/spot_rate)*100:.3f}%",
                help="Sum of all guaranteed bank spreads"
            )
            st.write(f"**{(portfolio_avg_min_profit * 10000):.1f} bps avg**")
        
        with col_max:
            st.markdown("**📈 Portfolio Maximum**")
            st.caption("*Bank spread + hedging savings*")
            st.metric(
                "Max Profit", 
                f"{portfolio_totals['total_max_profit']:,.0f} PLN",
                delta=f"{(portfolio_avg_max_profit/spot_rate)*100:.3f}%",
                help="Sum of bank spreads plus hedging savings"
            )
            st.write(f"**{(portfolio_avg_max_profit * 10000):.1f} bps avg**")
        
        # Portfolio summary metrics
        st.markdown("**📊 Portfolio Summary:**")
        st.metric("Expected Profit", f"{portfolio_totals['total_expected_profit']:,.0f} PLN", help="Average scenario")
        profit_range_pln = portfolio_totals['total_max_profit'] - portfolio_totals['total_min_profit']
        st.metric("Profit Range", f"{profit_range_pln:,.0f} PLN", help="Max - Min profit")
        
        risk_reward_ratio = portfolio_totals['total_max_profit'] / portfolio_totals['total_min_profit'] if portfolio_totals['total_min_profit'] > 0 else float('inf')
        st.metric("Risk/Reward", f"{risk_reward_ratio:.1f}x", help="Max/Min profit ratio")
        
        # Risk assessment for portfolio
        profit_volatility = (profit_range_pln / portfolio_totals['total_expected_profit']) * 100 if portfolio_totals['total_expected_profit'] > 0 else 0
        if profit_volatility < 20:
            st.success("✅ Low portfolio volatility - stable profit range")
        elif profit_volatility < 40:
            st.info("ℹ️ Moderate portfolio volatility - standard risk")
        else:
            st.warning("⚠️ High portfolio volatility - significant profit variability")
    
    # ============================================================================
    # CLIENT PRICE CURVE VISUALIZATION
    # ============================================================================
    
    st.markdown("---")
    st.subheader("📈 Client Price Curve Analysis")
    
    # Generate complete client price curve data
    client_curve_data = []
    for tenor, curve_data in forward_curve.items():
        tenor_points = curve_data["mid"]
        tenor_swap_risk = calculator.calculate_swap_risk(window_days, tenor_points)
        tenor_rates = calculator.calculate_professional_rates(spot_rate, tenor_points, tenor_swap_risk, minimum_profit_floor)
        
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
    for item in client_curve_data:
        if abs(item['days'] - window_days) <= 15:
            selected_client_rate = item['client_rate']
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
    
    # ============================================================================
    # COMPLETE 12-MONTH WINDOW FORWARD PORTFOLIO ANALYSIS
    # ============================================================================
    
    st.subheader("📋 Complete 12-Month Window Forward Portfolio")
    st.markdown(f"*All tenors with {window_days}-day window flexibility*")
    
    # Generate window forward pricing for all 12 tenors
    complete_window_pricing_data = []
    portfolio_summary = {
        'total_min_profit': 0,
        'total_max_profit': 0,
        'total_expected_profit': 0,
        'total_profit_range': 0,
        'weighted_avg_profit_pct': 0,
        'total_nominal': 0
    }
    
    for tenor, curve_data in forward_curve.items():
        tenor_days = curve_data["days"]
        tenor_points = curve_data["mid"]
        
        # Calculate window-specific swap risk for this tenor with selected window length
        tenor_window_swap_risk = calculator.calculate_swap_risk(window_days, tenor_points)
        
        # Calculate professional window forward rates
        tenor_rates = calculator.calculate_professional_rates(
            spot_rate, tenor_points, tenor_window_swap_risk, minimum_profit_floor
        )
        
        # Calculate window forward metrics using CORRECTED BANK SPREAD LOGIC:
        # Min Profit = Bank Spread (Theoretical - Client), Max Profit = Bank Spread + Hedging Savings
        window_min_profit_per_eur = tenor_rates['fwd_to_open'] - tenor_rates['fwd_client']  # Bank spread
        window_max_profit_per_eur = window_min_profit_per_eur + (tenor_window_swap_risk * 0.6)  # + hedging savings
        window_expected_profit_per_eur = (window_min_profit_per_eur + window_max_profit_per_eur) / 2
        
        window_min_profit_total = window_min_profit_per_eur * nominal_amount
        window_max_profit_total = window_max_profit_per_eur * nominal_amount
        window_expected_profit_total = window_expected_profit_per_eur * nominal_amount
        
        window_min_profit_total = window_min_profit_per_eur * nominal_amount
        window_max_profit_total = window_max_profit_per_eur * nominal_amount
        window_expected_profit_total = window_expected_profit_per_eur * nominal_amount
        
        # Add to portfolio summary
        portfolio_summary['total_min_profit'] += window_min_profit_total
        portfolio_summary['total_max_profit'] += window_max_profit_total
        portfolio_summary['total_expected_profit'] += window_expected_profit_total
        portfolio_summary['total_profit_range'] += (window_max_profit_total - window_min_profit_total)
        portfolio_summary['total_nominal'] += nominal_amount
        
        complete_window_pricing_data.append({
            "Tenor": tenor,
            "Forward Days": tenor_days,
            "Window Days": window_days,
            "Window Months": f"{window_days/30:.1f}M",
            "Forward Points": f"{tenor_points:.4f}",
            "Window Swap Risk": f"{tenor_window_swap_risk:.4f}",
            "Client Rate": f"{tenor_rates['fwd_client']:.4f}",
            "Theoretical Rate": f"{tenor_rates['fwd_to_open']:.4f}",
            "Min Profit/EUR": f"{window_min_profit_per_eur:.4f}",
            "Max Profit/EUR": f"{window_max_profit_per_eur:.4f}",
            "Expected Profit/EUR": f"{window_expected_profit_per_eur:.4f}",
            "Min Profit Total": f"{window_min_profit_total:,.0f} PLN",
            "Max Profit Total": f"{window_max_profit_total:,.0f} PLN",
            "Expected Profit Total": f"{window_expected_profit_total:,.0f} PLN",
            "Profit Range": f"{(window_max_profit_total - window_min_profit_total):,.0f} PLN",
            "Profit Min %": f"{(window_min_profit_per_eur/spot_rate)*100:.2f}%",
            "Profit Max %": f"{(window_max_profit_per_eur/spot_rate)*100:.2f}%",
            "Yield Spread": f"{curve_data['yield_spread']:.2f}pp"
        })
    
    # Calculate weighted averages for portfolio
    portfolio_summary['weighted_avg_profit_pct'] = (portfolio_summary['total_expected_profit'] / portfolio_summary['total_nominal'] / spot_rate) * 100
    
    df_complete_window_pricing = pd.DataFrame(complete_window_pricing_data)
    
    # Highlight the selected window length in the table
    def highlight_selected_window_portfolio(row):
        # Highlight rows where Forward Days is close to Window Days (same tenor approximately)
        if abs(row['Forward Days'] - window_days) <= 15:
            return ['background-color: #e8f5e8; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    # Display the complete window forward portfolio table
    st.dataframe(
        df_complete_window_pricing.style.apply(highlight_selected_window_portfolio, axis=1),
        use_container_width=True,
        height=400
    )
    
    # ============================================================================
    # PORTFOLIO WINDOW FORWARD SUMMARY
    # ============================================================================
    
    st.markdown("---")
    st.subheader("💼 Portfolio Window Forward Summary")
    st.markdown(f"*Aggregated results for all 12 tenors with {window_days}-day window*")
    
    # Portfolio summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Portfolio Min Profit", 
            f"{portfolio_summary['total_min_profit']:,.0f} PLN",
            help=f"Sum of all minimum profits (Points - Swap Risk) × €{nominal_amount:,} × 12 tenors"
        )
    
    with col2:
        st.metric(
            "Portfolio Max Profit", 
            f"{portfolio_summary['total_max_profit']:,.0f} PLN",
            help=f"Sum of all maximum profits (Full Points) × €{nominal_amount:,} × 12 tenors"
        )
    
    with col3:
        st.metric(
            "Portfolio Expected Profit", 
            f"{portfolio_summary['total_expected_profit']:,.0f} PLN",
            help="Average of min/max scenarios across all tenors"
        )
    
    with col4:
        st.metric(
            "Portfolio Profit Range", 
            f"{portfolio_summary['total_profit_range']:,.0f} PLN",
            help="Total variability across all window forwards"
        )
    
    # Deal summary
    st.markdown("---")
    st.subheader("📋 Deal Summary")
    
    with st.container():
        summary_col1, summary_col2 = st.columns([1, 1])
        
        with summary_col1:
            st.markdown(f"""
            <div class="metric-card">
                <h4>💼 Portfolio Window Forward Strategy</h4>
                <p><strong>Strategy:</strong> 12 Window Forwards with {window_days}-day flexibility</p>
                <p><strong>Total Notional:</strong> €{portfolio_totals['total_notional']:,}</p>
                <p><strong>Spot Rate:</strong> {spot_rate:.4f}</p>
                <p><strong>Portfolio Avg Client Rate:</strong> {portfolio_avg_client_rate:.4f}</p>
                <p><strong>Points Factor:</strong> {points_factor:.1%} (Industry: 70%)</p>
                <p><strong>Risk Factor:</strong> {risk_factor:.1%} (Industry: 40%)</p>
            </div>
            """, unsafe_allow_html=True)
        
        with summary_col2:
            st.markdown(f"""
            <div class="metric-card">
                <h4>💰 Portfolio Financial Summary</h4>
                <p><strong>Total Expected Profit:</strong> {portfolio_totals['total_expected_profit']:,.0f} PLN</p>
                <p><strong>Portfolio Minimum:</strong> {portfolio_totals['total_min_profit']:,.0f} PLN</p>
                <p><strong>Portfolio Maximum:</strong> {portfolio_totals['total_max_profit']:,.0f} PLN</p>
                <p><strong>Average Profit/EUR:</strong> {portfolio_avg_profit:.4f} PLN</p>
                <p><strong>Total Notional:</strong> €{portfolio_totals['total_notional']:,}</p>
                <p><strong>Average Client Rate:</strong> {portfolio_avg_client_rate:.4f}</p>
            </div>
            """, unsafe_allow_html=True)

# ============================================================================
# CLIENT-FACING HEDGING ADVISOR
# ============================================================================

def create_client_hedging_advisor():
    """Doradca zabezpieczeń walutowych dla klientów"""
    
    st.header("🛡️ Doradca Zabezpieczeń EUR/PLN")
    st.markdown("*Chroń swój biznes przed ryzykiem walutowym dzięki profesjonalnym kontraktom terminowym*")
    
    # Load market data
    with st.spinner("📡 Ładowanie aktualnych kursów rynkowych..."):
        bond_data = get_fred_bond_data()
        forex_data = get_eur_pln_rate()
    
    # Initialize calculator
    calculator = APIIntegratedForwardCalculator(FREDAPIClient())
    
    # Current market display
    st.subheader("📊 Aktualna Sytuacja Rynkowa")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        spot_rate = forex_data['rate']
        st.metric(
            "EUR/PLN Dzisiaj",
            f"{spot_rate:.4f}",
            help="Aktualny kurs wymiany"
        )
    
    with col2:
        pl_yield = bond_data['Poland_10Y']['value'] if 'Poland_10Y' in bond_data else 5.70
        de_yield = bond_data['Germany_9M']['value'] if 'Germany_9M' in bond_data else 2.35
        spread = pl_yield - de_yield
        
        if spread > 3.0:
            trend_emoji = "📈"
            trend_text = "PLN umacnia się"
        elif spread > 2.0:
            trend_emoji = "➡️"
            trend_text = "Stabilny trend"
        else:
            trend_emoji = "📉"
            trend_text = "PLN słabnie"
            
        st.metric(
            "Trend Rynkowy",
            f"{trend_emoji} {trend_text}",
            help=f"Na podstawie spreadu: {spread:.1f}pp"
        )
    
    with col3:
        # Calculate 6M forward as reference
        forward_6m = calculator.calculate_theoretical_forward_points(spot_rate, pl_yield, de_yield, 180)
        direction = "silniejszy" if forward_6m['forward_rate'] > spot_rate else "słabszy"
        
        st.metric(
            "Prognoza 6M",
            f"PLN {direction}",
            delta=f"{((forward_6m['forward_rate']/spot_rate - 1) * 100):+.2f}%",
            help="Oczekiwany kierunek PLN w 6 miesięcy"
        )
    
    # Client configuration
    st.markdown("---")
    st.subheader("⚙️ Twoje Potrzeby Zabezpieczeniowe")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        exposure_amount = st.number_input(
            "Kwota EUR do zabezpieczenia:",
            value=1_000_000,
            min_value=100_000,
            max_value=50_000_000,
            step=100_000,
            format="%d",
            help="Kwota ekspozycji EUR, którą chcesz zabezpieczyć"
        )
    
    with col2:
        hedging_horizon = st.selectbox(
            "Okres zabezpieczenia:",
            ["3 miesiące", "6 miesięcy", "9 miesięcy", "12 miesięcy", "Niestandardowy"],
            index=1,
            help="Na jak długo potrzebujesz ochrony?"
        )
        
        if hedging_horizon == "Niestandardowy":
            custom_months = st.slider("Miesiące:", 1, 24, 6)
            horizon_months = custom_months
        else:
            horizon_map = {"3 miesiące": 3, "6 miesięcy": 6, "9 miesięcy": 9, "12 miesięcy": 12}
            horizon_months = horizon_map[hedging_horizon]
    
    with col3:
        risk_appetite = st.selectbox(
            "Preferencje ryzyka:",
            ["Konserwatywne", "Zrównoważone", "Oportunistyczne"],
            index=1,
            help="Jak wysokie ryzyko jesteś gotów zaakceptować?"
        )
    
    # Generate forward curve
    forward_curve = calculator.generate_api_forward_points_curve(
        spot_rate, pl_yield, de_yield, 0.002
    )
    
    # ============================================================================
    # TABELA KURSÓW TERMINOWYCH DLA KLIENTA
    # ============================================================================
    
    st.markdown("---")
    st.subheader("💱 Dostępne Kursy Terminowe")
    st.markdown("*Zablokuj te kursy dzisiaj na przyszłe sprzedaże EUR*")
    
    # Calculate client rates
    client_rates_data = []
    recommended_tenors = []
    
    for tenor_key, curve_data in forward_curve.items():
        if curve_data["months"] <= horizon_months + 3:  # Show relevant tenors
            tenor_points = curve_data["mid"]
            tenor_days = curve_data["days"]
            
            # Calculate client rate (simplified - no swap risk complexity for client view)
            client_swap_risk = calculator.calculate_swap_risk(tenor_days, tenor_points)
            client_rates = calculator.calculate_professional_rates(
                spot_rate, tenor_points, client_swap_risk, 0.0
            )
            
            client_rate = client_rates['fwd_client']
            
            # Calculate benefit vs spot
            rate_advantage = ((client_rate - spot_rate) / spot_rate) * 100
            
            # Determine recommendation
            if rate_advantage > 0.5:
                recommendation = "🟢 Doskonały"
                recommended_tenors.append(tenor_key)
            elif rate_advantage > 0.2:
                recommendation = "🟡 Dobry"
            elif rate_advantage > 0:
                recommendation = "🟠 Akceptowalny"
            else:
                recommendation = "🔴 Rozważ spot"
            
            # Calculate PLN amount client would receive
            pln_amount = client_rate * exposure_amount
            spot_pln_amount = spot_rate * exposure_amount
            additional_pln = pln_amount - spot_pln_amount
            
            client_rates_data.append({
                "Tenor": curve_data["name"],
                "Okno od": curve_data["okno_od"],
                "Rozliczenie do": curve_data["rozliczenie_do"],
                "Kurs terminowy": f"{client_rate:.4f}",
                "vs Dzisiaj": f"{rate_advantage:+.2f}%",
                "Kwota PLN": f"{pln_amount:,.0f}",
                "Dodatkowe PLN": f"{additional_pln:+,.0f}" if additional_pln != 0 else "0",
                "Rekomendacja": recommendation,
                "Sort_Order": curve_data['months']
            })
    
    # Create DataFrame and sort by months
    df_client_rates = pd.DataFrame(client_rates_data)
    df_client_rates = df_client_rates.sort_values('Sort_Order').drop('Sort_Order', axis=1)
    
    # Style the table
    def highlight_recommendations(row):
        if "🟢" in str(row['Rekomendacja']):
            return ['background-color: #d4edda'] * len(row)
        elif "🟡" in str(row['Rekomendacja']):
            return ['background-color: #fff3cd'] * len(row)
        elif "🟠" in str(row['Rekomendacja']):
            return ['background-color: #ffeaa7'] * len(row)
        else:
            return ['background-color: #f8d7da'] * len(row)
    
    st.dataframe(
        df_client_rates.style.apply(highlight_recommendations, axis=1),
        use_container_width=True,
        height=400,
        hide_index=True
    )
    
    # Simple recommendations
    st.markdown("---")
    st.subheader("🎯 Rekomendacje")
    
    best_rates = df_client_rates[df_client_rates['Rekomendacja'].str.contains('🟢|🟡')].head(3)
    
    if len(best_rates) > 0:
        st.markdown("**📋 Najlepsze opcje:**")
        for idx, row in best_rates.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{row['Tenor']}** ({row['Okno od']} - {row['Rozliczenie do']})")
                with col2:
                    st.write(f"Kurs: **{row['Kurs terminowy']}**")
                with col3:
                    st.write(f"Korzyść: **{row['vs Dzisiaj']}**")
    
    # Call to action
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="metric-card" style="text-align: center;">
            <h4>Gotowy chronić swój biznes?</h4>
            <p>Skontaktuj się z naszymi specjalistami FX</p>
            <p><strong>📞 +48 22 XXX XXXX | 📧 zabezpieczenia.fx@bank.pl</strong></p>
        </div>
        """, unsafe_allow_html=True)ening"
            
        st.metric(
            "Market Trend",
            f"{trend_emoji} {trend_text}",
            help=f"Based on yield spread: {spread:.1f}pp"
        )
    
    with col3:
        # Calculate 6M forward as reference
        forward_6m = calculator.calculate_theoretical_forward_points(spot_rate, pl_yield, de_yield, 180)
        direction = "stronger" if forward_6m['forward_rate'] > spot_rate else "weaker"
        
        st.metric(
            "6M Outlook",
            f"PLN {direction}",
            delta=f"{((forward_6m['forward_rate']/spot_rate - 1) * 100):+.2f}%",
            help="Expected PLN direction in 6 months"
        )
    
    # Client configuration
    st.markdown("---")
    st.subheader("⚙️ Your Hedging Needs")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        exposure_amount = st.number_input(
            "EUR Amount to Hedge:",
            value=1_000_000,
            min_value=100_000,
            max_value=50_000_000,
            step=100_000,
            format="%d",
            help="Amount of EUR exposure you want to protect"
        )
    
    with col2:
        hedging_horizon = st.selectbox(
            "Hedging Period:",
            ["3 Months", "6 Months", "9 Months", "12 Months", "Custom"],
            index=1,
            help="How long do you need protection?"
        )
        
        if hedging_horizon == "Custom":
            custom_months = st.slider("Months:", 1, 24, 6)
            horizon_months = custom_months
        else:
            horizon_map = {"3 Months": 3, "6 Months": 6, "9 Months": 9, "12 Months": 12}
            horizon_months = horizon_map[hedging_horizon]
    
    with col3:
        risk_appetite = st.selectbox(
            "Risk Preference:",
            ["Conservative", "Balanced", "Opportunistic"],
            index=1,
            help="How much risk are you comfortable with?"
        )
    
    # Generate forward curve
    forward_curve = calculator.generate_api_forward_points_curve(
        spot_rate, pl_yield, de_yield, 0.002
    )
    
    # ============================================================================
    # CLIENT FORWARD RATES TABLE
    # ============================================================================
    
    st.markdown("---")
    st.subheader("💱 Available Forward Rates")
    st.markdown("*Lock in these rates today for future EUR sales*")
    
    # Calculate client rates
    client_rates_data = []
    recommended_tenors = []
    
    for tenor, curve_data in forward_curve.items():
        if curve_data["months"] <= horizon_months + 3:  # Show relevant tenors
            tenor_points = curve_data["mid"]
            tenor_days = curve_data["days"]
            
            # Calculate client rate (simplified - no swap risk complexity for client view)
            client_swap_risk = calculator.calculate_swap_risk(tenor_days, tenor_points)
            client_rates = calculator.calculate_professional_rates(
                spot_rate, tenor_points, client_swap_risk, 0.0
            )
            
            client_rate = client_rates['fwd_client']
            
            # Calculate benefit vs spot
            rate_advantage = ((client_rate - spot_rate) / spot_rate) * 100
            
            # Determine recommendation
            if rate_advantage > 0.5:
                recommendation = "🟢 Excellent"
                recommended_tenors.append(tenor)
            elif rate_advantage > 0.2:
                recommendation = "🟡 Good"
            elif rate_advantage > 0:
                recommendation = "🟠 Fair"
            else:
                recommendation = "🔴 Consider spot"
            
            # Calculate PLN amount client would receive
            pln_amount = client_rate * exposure_amount
            spot_pln_amount = spot_rate * exposure_amount
            additional_pln = pln_amount - spot_pln_amount
            
            client_rates_data.append({
                "Tenor": tenor,
                "Period": f"{curve_data['months']} months",
                "Forward Rate": f"{client_rate:.4f}",
                "vs Today": f"{rate_advantage:+.2f}%",
                "PLN Amount": f"{pln_amount:,.0f}",
                "Extra PLN": f"{additional_pln:+,.0f}" if additional_pln != 0 else "0",
                "Recommendation": recommendation,
                "Sort_Order": curve_data['months']
            })
    
    # Create DataFrame and sort by months
    df_client_rates = pd.DataFrame(client_rates_data)
    df_client_rates = df_client_rates.sort_values('Sort_Order').drop('Sort_Order', axis=1)
    
    # Style the table
    def highlight_recommendations(row):
        if "🟢" in str(row['Recommendation']):
            return ['background-color: #d4edda'] * len(row)  # Green
        elif "🟡" in str(row['Recommendation']):
            return ['background-color: #fff3cd'] * len(row)  # Yellow
        elif "🟠" in str(row['Recommendation']):
            return ['background-color: #ffeaa7'] * len(row)  # Orange
        else:
            return ['background-color: #f8d7da'] * len(row)  # Red
    
    st.dataframe(
        df_client_rates.style.apply(highlight_recommendations, axis=1),
        use_container_width=True,
        height=350,
        hide_index=True
    )
    
    # ============================================================================
    # HEDGING STRATEGY VISUALIZATION
    # ============================================================================
    
    st.markdown("---")
    st.subheader("📈 Proposed Hedging Strategy")
    
    # Create hedging visualization
    fig_hedging = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Forward Rates vs Spot Rate',
            'Your Hedging Benefit',
            'Risk Protection Over Time',
            'Recommended Portfolio Split'
        ),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"type": "pie"}]]
    )
    
    # Extract data for charts
    tenors_list = [data["Tenor"] for data in client_rates_data]
    months_list = [data["Period"].replace(" months", "M") for data in client_rates_data]
    forward_rates = [float(data["Forward Rate"]) for data in client_rates_data]
    rate_advantages = [float(data["vs Today"].replace("%", "").replace("+", "")) for data in client_rates_data]
    extra_pln = [float(data["Extra PLN"].replace(",", "").replace("+", "")) for data in client_rates_data]
    
    # 1. Forward Rates vs Spot
    fig_hedging.add_trace(
        go.Scatter(
            x=months_list,
            y=[spot_rate] * len(months_list),
            mode='lines',
            name='Today\'s Rate',
            line=dict(color='red', width=3, dash='dash'),
            hovertemplate='Today\'s Rate: %{y:.4f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    fig_hedging.add_trace(
        go.Scatter(
            x=months_list,
            y=forward_rates,
            mode='lines+markers',
            name='Forward Rates',
            line=dict(color='green', width=3),
            marker=dict(size=10, color='green'),
            hovertemplate='<b>%{x}</b><br>Forward Rate: %{y:.4f}<br>Benefit: %{customdata:.2f}%<extra></extra>',
            customdata=rate_advantages
        ),
        row=1, col=1
    )
    
    # 2. Hedging Benefit
    colors = ['green' if x > 0 else 'red' for x in extra_pln]
    fig_hedging.add_trace(
        go.Bar(
            x=months_list,
            y=extra_pln,
            name='Additional PLN',
            marker_color=colors,
            hovertemplate='<b>%{x}</b><br>Extra PLN: %{y:,.0f}<extra></extra>'
        ),
        row=1, col=2
    )
    
    # 3. Risk Protection Over Time
    protection_levels = []
    for i, advantage in enumerate(rate_advantages):
        if advantage > 0.5:
            protection_levels.append(95)
        elif advantage > 0.2:
            protection_levels.append(80)
        elif advantage > 0:
            protection_levels.append(60)
        else:
            protection_levels.append(30)
    
    fig_hedging.add_trace(
        go.Scatter(
            x=months_list,
            y=protection_levels,
            mode='lines+markers',
            name='Protection Level',
            line=dict(color='blue', width=3),
            marker=dict(size=8),
            hovertemplate='<b>%{x}</b><br>Protection: %{y}%<extra></extra>'
        ),
        row=2, col=1
    )
    
    # 4. Recommended Portfolio Split
    if risk_appetite == "Conservative":
        hedge_ratio = 80
        spot_ratio = 20
    elif risk_appetite == "Balanced":
        hedge_ratio = 60
        spot_ratio = 40
    else:  # Opportunistic
        hedge_ratio = 40
        spot_ratio = 60
    
    fig_hedging.add_trace(
        go.Pie(
            labels=['Hedge with Forwards', 'Keep at Spot'],
            values=[hedge_ratio, spot_ratio],
            name="Portfolio Split",
            marker_colors=['lightgreen', 'lightcoral'],
            hovertemplate='<b>%{label}</b><br>%{value}% of exposure<br>€%{customdata:,.0f}<extra></extra>',
            customdata=[exposure_amount * hedge_ratio / 100, exposure_amount * spot_ratio / 100]
        ),
        row=2, col=2
    )
    
    # Update layout
    fig_hedging.update_layout(
        height=700,
        showlegend=True,
        title_text=f"Hedging Strategy for €{exposure_amount:,} EUR Exposure"
    )
    
    # Update axes
    fig_hedging.update_xaxes(title_text="Maturity", row=1, col=1)
    fig_hedging.update_yaxes(title_text="EUR/PLN Rate", row=1, col=1)
    fig_hedging.update_xaxes(title_text="Maturity", row=1, col=2)
    fig_hedging.update_yaxes(title_text="Additional PLN", row=1, col=2)
    fig_hedging.update_xaxes(title_text="Maturity", row=2, col=1)
    fig_hedging.update_yaxes(title_text="Protection Level (%)", row=2, col=1)
    
    st.plotly_chart(fig_hedging, use_container_width=True)
    
    # ============================================================================
    # PERSONALIZED RECOMMENDATIONS
    # ============================================================================
    
    st.markdown("---")
    st.subheader("🎯 Your Personalized Recommendations")
    
    # Calculate best options
    best_rates = df_client_rates[df_client_rates['Recommendation'].str.contains('🟢|🟡')].head(3)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**📋 Recommended Strategy:**")
        
        if risk_appetite == "Conservative":
            strategy_text = f"""
            **Conservative Approach for €{exposure_amount:,}:**
            
            🛡️ **Hedge {hedge_ratio}% immediately** (€{exposure_amount * hedge_ratio // 100:,})
            - Use {best_rates.iloc[0]['Tenor'] if len(best_rates) > 0 else '6M'} forwards for core protection
            - Rate: {best_rates.iloc[0]['Forward Rate'] if len(best_rates) > 0 else 'N/A'}
            - Benefit: {best_rates.iloc[0]['vs Today'] if len(best_rates) > 0 else 'N/A'}
            
            ⏳ **Keep {spot_ratio}% flexible** (€{exposure_amount * spot_ratio // 100:,})
            - Monitor market for better opportunities
            - Use for short-term needs
            
            💰 **Expected Additional PLN:** {best_rates.iloc[0]['Extra PLN'] if len(best_rates) > 0 else 'N/A'}
            """
        elif risk_appetite == "Balanced":
            strategy_text = f"""
            **Balanced Approach for €{exposure_amount:,}:**
            
            🎯 **Split hedging strategy:**
            - 30% in {best_rates.iloc[0]['Tenor'] if len(best_rates) > 0 else '3M'} forwards (€{exposure_amount * 30 // 100:,})
            - 30% in {best_rates.iloc[1]['Tenor'] if len(best_rates) > 1 else '6M'} forwards (€{exposure_amount * 30 // 100:,})
            - 40% keep flexible (€{exposure_amount * 40 // 100:,})
            
            📈 **Diversified protection** across multiple maturities
            
            💰 **Blended benefit:** Mix of rates and timing
            """
        else:  # Opportunistic
            strategy_text = f"""
            **Opportunistic Approach for €{exposure_amount:,}:**
            
            🎲 **Selective hedging:**
            - Hedge only {hedge_ratio}% (€{exposure_amount * hedge_ratio // 100:,})
            - Focus on best value: {best_rates.iloc[0]['Tenor'] if len(best_rates) > 0 else '6M'}
            - Keep {spot_ratio}% for market opportunities
            
            🚀 **Higher risk, higher reward potential**
            
            ⚠️ **Monitor market closely** for optimal timing
            """
        
        st.markdown(strategy_text)
    
    with col2:
        # Risk metrics
        st.markdown("**📊 Strategy Metrics:**")
        
        # Calculate portfolio metrics
        if len(best_rates) > 0:
            avg_benefit = df_client_rates['vs Today'].str.replace('%', '').str.replace('+', '').astype(float).mean()
            total_extra_pln = df_client_rates['Extra PLN'].str.replace(',', '').str.replace('+', '').astype(float).sum()
            
            st.metric("Avg Rate Benefit", f"{avg_benefit:.2f}%")
            st.metric("Total Extra PLN", f"{total_extra_pln:,.0f}")
            st.metric("Risk Level", risk_appetite)
            
            # Risk warning
            if avg_benefit < 0:
                st.warning("⚠️ Current forwards below spot - consider waiting")
            elif avg_benefit > 0.5:
                st.success("✅ Excellent hedging opportunity")
            else:
                st.info("ℹ️ Moderate hedging benefit available")
    
    # Call to action
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="metric-card" style="text-align: center;">
            <h4>Ready to Protect Your Business?</h4>
            <p>Contact our FX specialists to implement your hedging strategy</p>
            <p><strong>📞 +48 22 XXX XXXX | 📧 fx.hedging@bank.pl</strong></p>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# GŁÓWNA APLIKACJA Z ZAKŁADKAMI
# ============================================================================

def main():
    """Główny punkt wejścia aplikacji z zakładkami"""
    
    # Header
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 2rem;">
        <div style="background: linear-gradient(45deg, #667eea, #764ba2); width: 60px; height: 60px; border-radius: 10px; margin-right: 1rem; display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 2rem;">🚀</span>
        </div>
        <h1 style="margin: 0; color: #2c3e50;">Profesjonalna Platforma FX</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("*Zaawansowane wyceny kontraktów terminowych i rozwiązania zabezpieczeniowe dla klientów*")
    
    # Create tabs
    tab1, tab2 = st.tabs(["🔧 Panel Dealerski", "🛡️ Doradca Zabezpieczeń"])
    
    with tab1:
        st.header("🚀 Profesjonalny Panel Window Forward")
        st.markdown("*Dane w czasie rzeczywistym z profesjonalną logiką wyceny*")
        
        # API Key Configuration Section
        with st.expander("🔧 Konfiguracja API", expanded=False):
            st.markdown("""
            **Konfiguracja klucza FRED API:**
            1. Pobierz darmowy klucz API z: https://fred.stlouisfed.org/docs/api/api_key.html
            2. Dodaj do Streamlit secrets.toml: `FRED_API_KEY = "twoj_klucz_tutaj"`
            3. Lub zmodyfikuj kod bezpośrednio aby zawrzeć klucz
            
            **Aktualny status:**
            """)
            
            if FRED_API_KEY == "demo":
                st.warning("⚠️ Używam trybu demo - ograniczony dostęp do API")
            else:
                st.success("✅ Klucz FRED API skonfigurowany")
        
        # Load real market data
        with st.spinner("📡 Ładowanie danych rynkowych w czasie rzeczywistym..."):
            bond_data = get_fred_bond_data()
            forex_data = get_eur_pln_rate()
        
        # Initialize calculator
        calculator = APIIntegratedForwardCalculator(FREDAPIClient())
        
        # ============================================================================
        # WYŚWIETLANIE DANYCH RYNKOWYCH
        # ============================================================================
        
        st.subheader("📊 Dane Rynkowe na Żywo")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            spot_rate = forex_data['rate']
            st.metric(
                "EUR/PLN Spot",
                f"{spot_rate:.4f}",
                help=f"Źródło: {forex_data['source']} | Aktualizacja: {forex_data['date']}"
            )
        
        with col2:
            pl_yield = bond_data['Poland_10Y']['value'] if 'Poland_10Y' in bond_data else 5.70
            st.metric(
                "Rentowność PL 10Y",
                f"{pl_yield:.2f}%",
                help=f"Źródło: {bond_data.get('Poland_10Y', {}).get('source', 'Fallback')}"
            )
        
        with col3:
            de_yield = bond_data['Germany_9M']['value'] if 'Germany_9M' in bond_data else 2.35
            st.metric(
                "Rentowność DE",
                f"{de_yield:.2f}%", 
                help=f"Źródło: {bond_data.get('Germany_9M', {}).get('source', 'Fallback')}"
            )
        
        with col4:
            spread = pl_yield - de_yield
            st.metric(
                "Spread PL-DE",
                f"{spread:.2f}pp",
                help="Różnica rentowności napędzająca punkty terminowe"
            )
        
        # ============================================================================
        # PARAMETRY KONFIGURACYJNE
        # ============================================================================
        
        st.markdown("---")
        st.subheader("⚙️ Konfiguracja Transakcji")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            window_days = st.number_input(
                "Długość okna (dni):",
                value=90,
                min_value=30,
                max_value=365,
                step=5,
                help="Długość okresu window forward"
            )
        
        with col2:
            nominal_amount = st.number_input(
                "Kwota nominalna (EUR):",
                value=2_500_000,
                min_value=100_000,
                max_value=100_000_000,
                step=100_000,
                format="%d",
                help="Kwota nominalna transakcji"
            )
        
        with col3:
            leverage = st.number_input(
                "Współczynnik dźwigni:",
                value=1.0,
                min_value=1.0,
                max_value=3.0,
                step=0.1,
                help="Dźwignia ryzyka dla kalkulacji P&L"
            )
        
        # Advanced parameters
        with st.expander("🔧 Zaawansowane Parametry Wyceny"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                points_factor = st.slider(
                    "Współczynnik punktów (% dla klienta):",
                    min_value=0.60,
                    max_value=0.85,
                    value=0.70,
                    step=0.01,
                    help="Procent punktów terminowych przekazywanych klientowi"
                )
            
            with col2:
                risk_factor = st.slider(
                    "Współczynnik ryzyka (% obciążenia):",
                    min_value=0.30,
                    max_value=0.60,
                    value=0.40,
                    step=0.01,
                    help="Procent ryzyka swap obciążanego klientowi"
                )
            
            with col3:
                bid_ask_spread = st.number_input(
                    "Spread bid-ask:",
                    value=0.002,
                    min_value=0.001,
                    max_value=0.005,
                    step=0.0005,
                    format="%.4f",
                    help="Rynkowy spread bid-ask w punktach terminowych"
                )
            
            # Additional parameters row
            col4, col5, col6 = st.columns(3)
            
            with col4:
                minimum_profit_floor = st.number_input(
                    "Min próg zysku (PLN/EUR):",
                    value=0.000,
                    min_value=-0.020,
                    max_value=0.020,
                    step=0.001,
                    format="%.4f",
                    help="Minimalny gwarantowany zysk na EUR (0 = naturalny zakres)"
                )
        
        # Update calculator parameters
        calculator.points_factor = points_factor
        calculator.risk_factor = risk_factor
        
        # Generate forward curve
        forward_curve = calculator.generate_api_forward_points_curve(
            spot_rate, pl_yield, de_yield, bid_ask_spread
        )
        
        # ============================================================================
        # UPROSZCZONA TABELA PORTFOLIO (przykład dla dealerów)
        # ============================================================================
        
        st.markdown("---")
        st.subheader("📋 Portfolio Kontraktów Window Forward")
        st.markdown(f"*Wszystkie 12 tenorów z {window_days}-dniową elastycznością okna*")
        
        # Generate portfolio data with Polish dates
        portfolio_data = []
        for tenor_key, curve_data in forward_curve.items():
            tenor_points = curve_data["mid"]
            tenor_window_swap_risk = calculator.calculate_swap_risk(window_days, tenor_points)
            tenor_rates = calculator.calculate_professional_rates(
                spot_rate, tenor_points, tenor_window_swap_risk, minimum_profit_floor
            )
            
            # Calculate min/max profits using bank spread logic
            window_min_profit_per_eur = tenor_rates['fwd_to_open'] - tenor_rates['fwd_client']  # Bank spread
            window_max_profit_per_eur = window_min_profit_per_eur + (tenor_window_swap_risk * 0.6)
            
            portfolio_data.append({
                "Tenor": curve_data["name"],
                "Okno od": curve_data["okno_od"],
                "Rozliczenie do": curve_data["rozliczenie_do"],
                "Punkty terminowe": f"{tenor_points:.4f}",
                "Ryzyko swap": f"{tenor_window_swap_risk:.4f}",
                "Kurs klienta": f"{tenor_rates['fwd_client']:.4f}",
                "Kurs teoretyczny": f"{tenor_rates['fwd_to_open']:.4f}",
                "Min zysk/EUR": f"{window_min_profit_per_eur:.4f}",
                "Max zysk/EUR": f"{window_max_profit_per_eur:.4f}",
                "Min zysk total": f"{window_min_profit_per_eur * nominal_amount:,.0f} PLN",
                "Max zysk total": f"{window_max_profit_per_eur * nominal_amount:,.0f} PLN"
            })
        
        df_portfolio = pd.DataFrame(portfolio_data)
        st.dataframe(df_portfolio, use_container_width=True, height=400)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_min = sum([float(row["Min zysk total"].replace(" PLN", "").replace(",", "")) for row in portfolio_data])
        total_max = sum([float(row["Max zysk total"].replace(" PLN", "").replace(",", "")) for row in portfolio_data])
        
        with col1:
            st.metric("Portfolio Min Zysk", f"{total_min:,.0f} PLN")
        with col2:
            st.metric("Portfolio Max Zysk", f"{total_max:,.0f} PLN")
        with col3:
            st.metric("Oczekiwany Zysk", f"{(total_min + total_max)/2:,.0f} PLN")
        with col4:
            st.metric("Zakres Zysku", f"{total_max - total_min:,.0f} PLN")
    
    with tab2:
        create_client_hedging_advisor()

# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == "__main__":
    main()
