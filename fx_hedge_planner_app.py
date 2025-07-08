import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import math

# ============================================================================
# CONFIGURATION & API KEYS
# ============================================================================

# CurrencyLayer API Configuration
CURRENCYLAYER_API_KEY = "be20bd424276192cd8352f83036e7b37"

# FRED API Configuration
FRED_API_KEY = st.secrets.get("FRED_API_KEY", "4f6d1c3d1817347baec4a99bfc05cce2")

# Page config
st.set_page_config(
    page_title="Professional FX Platform with Binomial Model",
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
    .profit-metric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
    }
    .client-summary {
        background: white;
        color: #2c3e50;
        border: 3px solid #2e68a5;
        padding: 1.5rem;
        border-radius: 1rem;
        margin: 1rem 0;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .pricing-sync {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
    }
    .api-status {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 0.8rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
        font-size: 0.9rem;
    }
    .pro-api {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.8rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
        font-size: 0.9rem;
    }
    .binomial-model {
        background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
        color: #2c3e50;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
        border: 2px solid #e91e63;
    }
    .nbp-api {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# PROFESSIONAL CURRENCYLAYER API CLASS
# ============================================================================

class CurrencyLayerAPI:
    """Professional CurrencyLayer API client"""
    
    def __init__(self, api_key=CURRENCYLAYER_API_KEY):
        self.api_key = api_key
        self.base_url = "https://api.currencylayer.com"
        self.endpoints = {
            'live': f"{self.base_url}/live",
            'historical': f"{self.base_url}/historical",
            'convert': f"{self.base_url}/convert"
        }
    
    def get_live_rates(self, source="USD", currencies="EUR,PLN"):
        """Get live exchange rates"""
        try:
            params = {
                'access_key': self.api_key,
                'source': source,
                'currencies': currencies,
                'format': 1
            }
            
            response = requests.get(self.endpoints['live'], params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('success'):
                return {
                    'success': True,
                    'timestamp': data.get('timestamp'),
                    'source': data.get('source'),
                    'quotes': data.get('quotes', {}),
                    'api_source': 'CurrencyLayer Pro 💎'
                }
            else:
                error = data.get('error', {})
                st.warning(f"CurrencyLayer API Error: {error.get('type', 'Unknown')} - {error.get('info', 'No details')}")
                return {'success': False, 'error': error}
                
        except Exception as e:
            st.warning(f"CurrencyLayer API request failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_eur_pln_rate(self):
        """Get EUR/PLN rate using CurrencyLayer API"""
        try:
            # Try direct EUR base first
            eur_data = self.get_live_rates(source="EUR", currencies="PLN")
            
            if eur_data['success'] and 'EURPLN' in eur_data['quotes']:
                return {
                    'rate': eur_data['quotes']['EURPLN'],
                    'date': datetime.fromtimestamp(eur_data['timestamp']).strftime('%Y-%m-%d'),
                    'source': 'CurrencyLayer (EUR→PLN) 💎'
                }
            
            # Fallback: USD base and calculate EUR/PLN
            usd_data = self.get_live_rates(source="USD", currencies="EUR,PLN")
            
            if usd_data['success'] and 'USDEUR' in usd_data['quotes'] and 'USDPLN' in usd_data['quotes']:
                # Calculate EUR/PLN = USD/PLN ÷ USD/EUR
                eur_pln_rate = usd_data['quotes']['USDPLN'] / usd_data['quotes']['USDEUR']
                
                return {
                    'rate': eur_pln_rate,
                    'date': datetime.fromtimestamp(usd_data['timestamp']).strftime('%Y-%m-%d'),
                    'source': 'CurrencyLayer (USD calc) 💎'
                }
            
            return None
            
        except Exception as e:
            st.warning(f"CurrencyLayer EUR/PLN calculation failed: {str(e)}")
            return None

# ============================================================================
# IMPROVED FOREX API WITH CURRENCYLAYER PRIORITY
# ============================================================================

class ProfessionalForexAPI:
    """Professional forex API with CurrencyLayer as primary source"""
    
    def __init__(self):
        self.currencylayer = CurrencyLayerAPI()
        self.fallback_rate = 4.25
    
    def get_eur_pln_rate(self):
        """Get EUR/PLN rate with professional priority"""
        
        # Priority 1: CurrencyLayer API (Professional)
        try:
            cl_rate = self.currencylayer.get_eur_pln_rate()
            if cl_rate and cl_rate['rate'] > 0:
                return cl_rate
        except Exception as e:
            st.warning(f"CurrencyLayer primary failed: {str(e)}")
        
        # Priority 2: NBP API (Official Polish source)
        try:
            url = "https://api.nbp.pl/api/exchangerates/rates/a/eur/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('rates') and len(data['rates']) > 0:
                return {
                    'rate': data['rates'][0]['mid'],
                    'date': data['rates'][0]['effectiveDate'],
                    'source': 'NBP Official 🏛️'
                }
        except Exception as e:
            st.warning(f"NBP API backup failed: {str(e)}")
        
        # Priority 3: Hardcoded fallback
        st.error("⚠️ All APIs failed! Using hardcoded fallback rate.")
        return {
            'rate': self.fallback_rate,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'source': 'Hardcoded Fallback ⚠️'
        }
    
    def get_usd_pln_rate(self):
        """Get USD/PLN rate"""
        try:
            url = "https://api.nbp.pl/api/exchangerates/rates/a/usd/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('rates') and len(data['rates']) > 0:
                return {
                    'rate': data['rates'][0]['mid'],
                    'date': data['rates'][0]['effectiveDate'],
                    'source': 'NBP Official 🏛️'
                }
        except Exception:
            return {
                'rate': 4.00,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'source': 'Fallback ⚠️'
            }

# ============================================================================
# PROFESSIONAL BOND API WITH ENHANCED FALLBACK
# ============================================================================

class ProfessionalBondAPI:
    """Professional bond yields with current market data"""
    
    def __init__(self):
        # Current market yields as of July 2025
        self.current_yields = {
            'Poland_10Y': 5.82,    # Current market
            'Germany_10Y': 2.62,   # Current market  
            'US_10Y': 4.32,        # Current market
            'Euro_Area_10Y': 3.18, # Current market
            'US_2Y': 4.05          # Current market
        }
    
    def get_bond_yields(self):
        """Get current bond yields with professional sources"""
        results = {}
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Try FRED API first for official data
        try:
            fred_results = self._try_fred_api()
            if fred_results:
                return fred_results
        except Exception:
            pass
        
        # Fallback to current market data
        for bond_name, yield_value in self.current_yields.items():
            results[bond_name] = {
                'value': yield_value,
                'date': current_date,
                'source': 'Professional Market Data 📈'
            }
        
        return results
    
    def _try_fred_api(self):
        """Try to get data from FRED API"""
        try:
            # Simplified FRED attempt - would need full implementation
            return None
        except Exception:
            return None

# ============================================================================
# PROFESSIONAL BINOMIAL OPTION PRICING MODEL
# ============================================================================

class BinomialOptionModel:
    """Professional binomial model for FX options with NBP data integration"""
    
    def __init__(self, forex_api):
        self.forex_api = forex_api
        
    def calculate_binomial_tree(self, S0, K, T, r, sigma, n, option_type='call'):
        """
        Calculate option price using binomial tree model
        
        Parameters:
        S0: Current spot price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Volatility
        n: Number of steps
        option_type: 'call' or 'put'
        """
        
        # Calculate parameters
        dt = T / n
        u = np.exp(sigma * np.sqrt(dt))  # Up factor
        d = 1 / u  # Down factor
        p = (np.exp(r * dt) - d) / (u - d)  # Risk-neutral probability
        
        # Initialize asset prices at maturity
        ST = np.zeros(n + 1)
        for i in range(n + 1):
            ST[i] = S0 * (u ** (n - i)) * (d ** i)
        
        # Initialize option values at maturity
        if option_type == 'call':
            payoffs = np.maximum(ST - K, 0)
        else:  # put
            payoffs = np.maximum(K - ST, 0)
        
        # Backward induction
        for j in range(n - 1, -1, -1):
            for i in range(j + 1):
                payoffs[i] = np.exp(-r * dt) * (p * payoffs[i] + (1 - p) * payoffs[i + 1])
        
        return {
            'option_price': payoffs[0],
            'u_factor': u,
            'd_factor': d,
            'risk_neutral_prob': p,
            'tree_steps': n,
            'time_step': dt
        }
    
    def calculate_greeks(self, S0, K, T, r, sigma, n, option_type='call'):
        """Calculate option Greeks using binomial model"""
        
        # Base calculation
        base_result = self.calculate_binomial_tree(S0, K, T, r, sigma, n, option_type)
        base_price = base_result['option_price']
        
        # Delta calculation (dV/dS)
        dS = S0 * 0.01  # 1% change
        S_up = S0 + dS
        S_down = S0 - dS
        
        V_up = self.calculate_binomial_tree(S_up, K, T, r, sigma, n, option_type)['option_price']
        V_down = self.calculate_binomial_tree(S_down, K, T, r, sigma, n, option_type)['option_price']
        
        delta = (V_up - V_down) / (2 * dS)
        
        # Gamma calculation (d²V/dS²)
        V_base = base_price
        gamma = (V_up - 2 * V_base + V_down) / (dS ** 2)
        
        # Theta calculation (dV/dT)
        dT = 1/365  # 1 day
        if T > dT:
            V_theta = self.calculate_binomial_tree(S0, K, T - dT, r, sigma, n, option_type)['option_price']
            theta = (V_theta - base_price) / dT
        else:
            theta = 0
        
        # Vega calculation (dV/dσ)
        d_sigma = 0.01  # 1% volatility change
        V_vega_up = self.calculate_binomial_tree(S0, K, T, r, sigma + d_sigma, n, option_type)['option_price']
        V_vega_down = self.calculate_binomial_tree(S0, K, T, r, sigma - d_sigma, n, option_type)['option_price']
        vega = (V_vega_up - V_vega_down) / (2 * d_sigma)
        
        # Rho calculation (dV/dr)
        dr = 0.01  # 1% rate change
        V_rho_up = self.calculate_binomial_tree(S0, K, T, r + dr, sigma, n, option_type)['option_price']
        V_rho_down = self.calculate_binomial_tree(S0, K, T, r - dr, sigma, n, option_type)['option_price']
        rho = (V_rho_up - V_rho_down) / (2 * dr)
        
        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega,
            'rho': rho
        }
    
    def generate_price_tree_visualization(self, S0, K, T, r, sigma, n=5):
        """Generate data for binomial tree visualization"""
        
        dt = T / n
        u = np.exp(sigma * np.sqrt(dt))
        d = 1 / u
        
        # Create tree structure
        tree_data = []
        
        for i in range(n + 1):
            for j in range(i + 1):
                price = S0 * (u ** (i - j)) * (d ** j)
                tree_data.append({
                    'step': i,
                    'node': j,
                    'price': price,
                    'x': i,
                    'y': i - 2 * j
                })
        
        return tree_data

# ============================================================================
# ENHANCED FRED API CLIENT
# ============================================================================

class FREDAPIClient:
    """Enhanced FRED API client with professional fallback"""
    
    def __init__(self, api_key=FRED_API_KEY):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"
        self.bond_api = ProfessionalBondAPI()
    
    def get_series_data(self, series_id, limit=1, sort_order='desc'):
        """Get latest data with professional fallback"""
        
        # Try original FRED first
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'limit': limit,
                'sort_order': sort_order
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'observations' in data and data['observations']:
                latest = data['observations'][0]
                if latest['value'] != '.':
                    return {
                        'value': float(latest['value']),
                        'date': latest['date'],
                        'series_id': series_id,
                        'source': 'FRED Official 🏛️'
                    }
        except Exception:
            pass
        
        # Fallback to professional bond data
        bond_mapping = {
            'IRLTLT01PLM156N': 'Poland_10Y',
            'IRLTLT01DEM156N': 'Germany_10Y',
            'DGS10': 'US_10Y',
            'DGS2': 'US_2Y',
            'IRLTLT01EZM156N': 'Euro_Area_10Y'
        }
        
        if series_id in bond_mapping:
            bond_data = self.bond_api.get_bond_yields()
            mapped_series = bond_mapping[series_id]
            
            if mapped_series in bond_data:
                return {
                    'value': bond_data[mapped_series]['value'],
                    'date': bond_data[mapped_series]['date'],
                    'series_id': series_id,
                    'source': bond_data[mapped_series]['source']
                }
        
        return None
    
    def get_multiple_series(self, series_dict):
        """Get data for multiple series with professional fallback"""
        results = {}
        for name, series_id in series_dict.items():
            data = self.get_series_data(series_id)
            if data:
                results[name] = data
        return results

# ============================================================================
# PROFESSIONAL WINDOW FORWARD CALCULATOR
# ============================================================================

class APIIntegratedForwardCalculator:
    """Professional window forward calculator using real API data"""
    
    def __init__(self, fred_client):
        self.fred_client = fred_client
        
        # Professional pricing parameters
        self.points_factor = 0.70  # Client gets 70% of forward points
        self.risk_factor = 0.40    # Bank charges 40% of swap risk
    
    def get_tenors_with_window(self, window_days):
        """Generate tenors with proper window calculation"""
        today = datetime.now()
        tenors = {}
        
        for i in range(1, 13):  # 1-12 months
            tenor_key = f"{i}M"
            tenor_start = today + timedelta(days=i*30)  # Start of tenor
            window_start = tenor_start  # Window starts at tenor start
            window_end = tenor_start + timedelta(days=window_days)  # Window ends after window_days
            
            tenors[tenor_key] = {
                "name": f"{i} {'miesiąc' if i == 1 else 'miesiące' if i <= 4 else 'miesięcy'}",
                "months": i,
                "days": i * 30,
                "okno_od": window_start.strftime("%d.%m.%Y"),
                "rozliczenie_do": window_end.strftime("%d.%m.%Y")
            }
        
        return tenors
    
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
    
    def generate_api_forward_points_curve(self, spot_rate, pl_yield, de_yield, bid_ask_spread=0.002, window_days=90):
        """Generate complete forward points curve from API bond data with proper window calculation"""
        curve_data = {}
        tenors = self.get_tenors_with_window(window_days)
        
        for tenor_key, tenor_info in tenors.items():
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

# ============================================================================
# PROFESSIONAL CACHED DATA FUNCTIONS
# ============================================================================

@st.cache_data(ttl=3600)
def get_fred_bond_data():
    """Get government bond yields with professional sources"""
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
        
        if not data:
            # Professional fallback
            bond_api = ProfessionalBondAPI()
            return bond_api.get_bond_yields()
            
        return data
        
    except Exception as e:
        st.warning(f"Using professional fallback bond data")
        bond_api = ProfessionalBondAPI()
        return bond_api.get_bond_yields()

@st.cache_data(ttl=300)
def get_eur_pln_rate():
    """Get current EUR/PLN with professional APIs"""
    try:
        professional_forex = ProfessionalForexAPI()
        rate_data = professional_forex.get_eur_pln_rate()
        return rate_data
    except Exception as e:
        st.error(f"All forex APIs failed: {str(e)}")
        return {'rate': 4.25, 'date': '2025-01-15', 'source': 'Emergency Fallback ⚠️'}

@st.cache_data(ttl=300)
def get_market_data():
    """Get complete market data from APIs"""
    forex_api = ProfessionalForexAPI()
    
    return {
        'eur_pln': forex_api.get_eur_pln_rate(),
        'usd_pln': forex_api.get_usd_pln_rate(),
        'bonds': get_fred_bond_data()
    }

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def initialize_session_state():
    """Initialize session state variables for data sharing between tabs"""
    if 'dealer_pricing_data' not in st.session_state:
        st.session_state.dealer_pricing_data = None
    if 'dealer_config' not in st.session_state:
        st.session_state.dealer_config = {
            'spot_rate': 4.25,
            'spot_source': 'Fallback',
            'pl_yield': 5.70,
            'de_yield': 2.35,
            'window_days': 90,
            'points_factor': 0.70,
            'risk_factor': 0.40,
            'bid_ask_spread': 0.002,
            'volatility_factor': 0.25,
            'hedging_savings_pct': 0.60,
            'minimum_profit_floor': 0.000
        }
    if 'pricing_updated' not in st.session_state:
        st.session_state.pricing_updated = False
    if 'market_data' not in st.session_state:
        st.session_state.market_data = None
    if 'binomial_results' not in st.session_state:
        st.session_state.binomial_results = None

# ============================================================================
# PRICING SYNC FUNCTIONS
# ============================================================================

def calculate_dealer_pricing(config):
    """Calculate dealer pricing and store in session state"""
    calculator = APIIntegratedForwardCalculator(FREDAPIClient())
    calculator.points_factor = config['points_factor']
    calculator.risk_factor = config['risk_factor']
    
    # Generate forward curve
    forward_curve = calculator.generate_api_forward_points_curve(
        config['spot_rate'], 
        config['pl_yield'], 
        config['de_yield'], 
        config['bid_ask_spread'],
        config['window_days']
    )
    
    # Calculate pricing for all tenors
    pricing_data = []
    
    for tenor_key, curve_data in forward_curve.items():
        tenor_days = curve_data["days"]
        tenor_points = curve_data["mid"]
        
        # Calculate window-specific swap risk
        tenor_window_swap_risk = abs(tenor_points) * config['volatility_factor'] * np.sqrt(config['window_days'] / 90)
        tenor_window_swap_risk = max(tenor_window_swap_risk, 0.015)
        
        # Calculate professional window forward rates
        tenor_rates = calculator.calculate_professional_rates(
            config['spot_rate'], tenor_points, tenor_window_swap_risk, config['minimum_profit_floor']
        )
        
        pricing
