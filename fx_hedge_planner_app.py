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

# Alpha Vantage API Configuration
ALPHA_VANTAGE_API_KEY = "MQGKUNL9JWIJHF9S"

# FRED API Configuration - PLACE YOUR API KEY HERE
FRED_API_KEY = st.secrets.get("FRED_API_KEY", "5b6bdfa2ea4d27f55da4d7ac845c05b3")  # Uses Streamlit secrets or demo

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
    .compact-table {
        font-size: 0.85rem;
    }
    .compact-table th {
        padding: 0.3rem 0.5rem !important;
        font-size: 0.8rem !important;
    }
    .compact-table td {
        padding: 0.3rem 0.5rem !important;
        font-size: 0.85rem !important;
    }
    .pricing-sync {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
    }
    .alpha-api {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.8rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# ALPHA VANTAGE API CLIENT
# ============================================================================

class AlphaVantageAPI:
    """Alpha Vantage API client for forex data and historical data"""
    
    def __init__(self, api_key=ALPHA_VANTAGE_API_KEY):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
    
    def get_eur_pln_rate(self):
        """Get current EUR/PLN exchange rate from Alpha Vantage"""
        try:
            params = {
                'function': 'CURRENCY_EXCHANGE_RATE',
                'from_currency': 'EUR',
                'to_currency': 'PLN',
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'Realtime Currency Exchange Rate' in data:
                rate_data = data['Realtime Currency Exchange Rate']
                return {
                    'rate': float(rate_data['5. Exchange Rate']),
                    'date': rate_data['6. Last Refreshed'][:10],
                    'source': 'Alpha Vantage 📈',
                    'success': True
                }
            else:
                return self._get_nbp_fallback()
                
        except Exception as e:
            st.warning(f"Alpha Vantage API error: {str(e)}")
            return self._get_nbp_fallback()
    
    def get_historical_eur_pln(self, days=30):
        """Get historical EUR/PLN data for volatility calculation"""
        try:
            params = {
                'function': 'FX_DAILY',
                'from_symbol': 'EUR',
                'to_symbol': 'PLN',
                'apikey': self.api_key,
                'outputsize': 'compact'
            }
            
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if 'Time Series (FX)' in data:
                time_series = data['Time Series (FX)']
                
                # Convert to list of rates
                rates = []
                dates = sorted(time_series.keys(), reverse=True)  # Most recent first
                
                for date in dates[:days]:  # Take last 'days' observations
                    rate = float(time_series[date]['4. close'])
                    rates.append(rate)
                
                if len(rates) >= 10:  # Need minimum data for volatility
                    return {
                        'rates': rates,
                        'dates': dates[:len(rates)],
                        'source': 'Alpha Vantage Historical 📊',
                        'success': True,
                        'count': len(rates)
                    }
            
            return self._get_nbp_historical_fallback(days)
            
        except Exception as e:
            st.warning(f"Alpha Vantage historical data error: {str(e)}")
            return self._get_nbp_historical_fallback(days)
    
    def _get_nbp_fallback(self):
        """Fallback to NBP API for current rate"""
        try:
            url = "https://api.nbp.pl/api/exchangerates/rates/a/eur/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('rates') and len(data['rates']) > 0:
                return {
                    'rate': data['rates'][0]['mid'],
                    'date': data['rates'][0]['effectiveDate'],
                    'source': 'NBP Backup 🏛️',
                    'success': True
                }
        except Exception:
            pass
        
        return {
            'rate': 4.25,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'source': 'Fallback ⚠️',
            'success': False
        }
    
    def _get_nbp_historical_fallback(self, days=30):
        """Fallback to NBP API for historical data"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days+10)  # Add buffer for weekends
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            url = f"https://api.nbp.pl/api/exchangerates/rates/a/eur/{start_str}/{end_str}/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('rates') and len(data['rates']) >= 10:
                rates = [rate_data['mid'] for rate_data in data['rates']]
                dates = [rate_data['effectiveDate'] for rate_data in data['rates']]
                
                # Take last 'days' observations or available data
                take_count = min(days, len(rates))
                
                return {
                    'rates': rates[-take_count:],
                    'dates': dates[-take_count:],
                    'source': 'NBP Historical Backup 🏛️',
                    'success': True,
                    'count': take_count
                }
        except Exception:
            pass
        
        # Ultimate fallback - synthetic data
        return {
            'rates': [4.25] * 20,  # Constant rates
            'dates': [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(20)],
            'source': 'Synthetic Data ⚠️',
            'success': False,
            'count': 20
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
        
        # If no data from API, use fallback
        if not data:
            raise Exception("No data from FRED API")
            
        return data
        
    except Exception as e:
        st.warning(f"Using fallback bond data: {e}")
        # Fallback data with current 10Y rates
        return {
            'Poland_10Y': {'value': 5.42, 'date': '2025-07-03', 'source': 'Current Market'},
            'Germany_10Y': {'value': 2.63, 'date': '2025-07-03', 'source': 'Current Market'},
            'US_10Y': {'value': 4.28, 'date': '2025-07-03', 'source': 'Current Market'},
            'Euro_Area_10Y': {'value': 3.15, 'date': '2025-07-03', 'source': 'Current Market'}
        }

@st.cache_data(ttl=300)
def get_eur_pln_rate():
    """Get current EUR/PLN from Alpha Vantage with NBP fallback"""
    alpha_api = AlphaVantageAPI()
    return alpha_api.get_eur_pln_rate()

@st.cache_data(ttl=1800)
def get_historical_eur_pln_data(days=30):
    """Get historical EUR/PLN data for volatility calculation"""
    alpha_api = AlphaVantageAPI()
    return alpha_api.get_historical_eur_pln(days)

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
# BINOMIAL PREDICTION INTEGRATION
# ============================================================================

def calculate_binomial_prediction(historical_data, current_spot, days=5):
    """Calculate binomial prediction for integration with dealer pricing - returns HIGHEST rate from most probable path"""
    
    try:
        if historical_data['success'] and len(historical_data['rates']) >= 20:
            rates = historical_data['rates']
            last_20_rates = rates[-20:] if len(rates) >= 20 else rates
            
            # Calculate empirical probabilities
            mean_20_days = np.mean(last_20_rates)
            std_20_days = np.std(last_20_rates)
            
            from scipy.stats import norm
            p_up_empirical = 1 - norm.cdf(current_spot, mean_20_days, std_20_days)
            p_down_empirical = 1 - p_up_empirical
            
            # Build complete tree for most probable path
            tree = {}
            most_probable_path = []
            
            rolling_vol = std_20_days / current_spot
            u = 1 + rolling_vol
            d = 1 - rolling_vol
            
            # Build full tree
            for day in range(days + 1):
                tree[day] = {}
                
                if day == 0:
                    most_probable_path.append(0)
                    tree[day][0] = current_spot
                else:
                    # Find most probable node (highest probability)
                    from math import comb
                    best_j = 0
                    best_prob = 0
                    
                    for j in range(day + 1):
                        prob = comb(day, j) * (p_up_empirical ** j) * (p_down_empirical ** (day - j))
                        if prob > best_prob:
                            best_prob = prob
                            best_j = j
                    
                    most_probable_path.append(best_j)
                    
                    # Calculate ALL prices for this day
                    for j in range(day + 1):
                        predicted_rate = current_spot * (u ** j) * (d ** (day - j))
                        tree[day][j] = predicted_rate
            
            # Get all rates from most probable path
            path_rates = []
            for day in range(days + 1):
                j = most_probable_path[day]
                path_rates.append(tree[day][j])
            
            # Find HIGHEST rate from the most probable path (excluding day 0)
            highest_rate_in_path = max(path_rates[1:])  # Skip day 0
            
            # Find which day has the highest rate
            highest_day = 0
            for day in range(1, days + 1):
                if abs(tree[day][most_probable_path[day]] - highest_rate_in_path) < 0.0001:
                    highest_day = day
                    break
            
            # Calculate final prediction probability
            final_day = days
            final_j = most_probable_path[final_day]
            final_predicted_rate = tree[final_day][final_j]
            final_prob = comb(final_day, final_j) * (p_up_empirical ** final_j) * (p_down_empirical ** (final_day - final_j))
            
            return {
                'success': True,
                'predicted_spot': highest_rate_in_path,  # Return HIGHEST rate from path
                'current_spot': current_spot,
                'probability': final_prob,
                'change_pct': ((highest_rate_in_path - current_spot) / current_spot) * 100,
                'most_probable_path': most_probable_path,
                'empirical_p_up': p_up_empirical,
                'empirical_p_down': p_down_empirical,
                'data_points': len(last_20_rates),
                'path_rates': path_rates,
                'highest_day': highest_day,
                'final_rate': final_predicted_rate,
                'tree_complete': tree
            }
        
        else:
            return {
                'success': False,
                'predicted_spot': current_spot,
                'current_spot': current_spot,
                'probability': 0.2,
                'change_pct': 0.0,
                'most_probable_path': [0, 0, 0, 0, 0, 0],
                'empirical_p_up': 0.5,
                'empirical_p_down': 0.5,
                'data_points': 0,
                'path_rates': [current_spot] * 6,
                'highest_day': 0,
                'final_rate': current_spot,
                'tree_complete': {}
            }
    
    except Exception as e:
        return {
            'success': False,
            'predicted_spot': current_spot,
            'current_spot': current_spot,
            'probability': 0.2,
            'change_pct': 0.0,
            'most_probable_path': [0, 0, 0, 0, 0, 0],
            'empirical_p_up': 0.5,
            'empirical_p_down': 0.5,
            'data_points': 0,
            'path_rates': [current_spot] * 6,
            'highest_day': 0,
            'final_rate': current_spot,
            'tree_complete': {}
        }

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
        
        pricing_data.append({
            'tenor_key': tenor_key,
            'tenor_name': curve_data["name"],
            'tenor_days': tenor_days,
            'tenor_months': curve_data["months"],
            'okno_od': curve_data["okno_od"],
            'rozliczenie_do': curve_data["rozliczenie_do"],
            'forward_points': tenor_points,
            'swap_risk': tenor_window_swap_risk,
            'client_rate': tenor_rates['fwd_client'],
            'theoretical_rate': tenor_rates['fwd_to_open'],
            'profit_per_eur': tenor_rates['profit_per_eur'],
            'yield_spread': curve_data['yield_spread']
        })
    
    return pricing_data

def update_dealer_config(spot_rate, spot_source, pl_yield, de_yield, window_days, 
                        points_factor, risk_factor, bid_ask_spread, volatility_factor, 
                        hedging_savings_pct, minimum_profit_floor):
    """Update dealer configuration in session state"""
    st.session_state.dealer_config = {
        'spot_rate': spot_rate,
        'spot_source': spot_source,
        'pl_yield': pl_yield,
        'de_yield': de_yield,
        'window_days': window_days,
        'points_factor': points_factor,
        'risk_factor': risk_factor,
        'bid_ask_spread': bid_ask_spread,
        'volatility_factor': volatility_factor,
        'hedging_savings_pct': hedging_savings_pct,
        'minimum_profit_floor': minimum_profit_floor
    }
    
    # Recalculate pricing
    st.session_state.dealer_pricing_data = calculate_dealer_pricing(st.session_state.dealer_config)
    st.session_state.pricing_updated = True

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def create_dealer_panel():
    """Panel dealerski - ustala wycenę dla całego systemu"""
    
    st.header("🚀 Panel Dealerski - Wycena Master")
    st.markdown("*Ustaw parametry wyceny - te kursy będą widoczne w panelu zabezpieczeń*")
    
    # Load market data
    with st.spinner("📡 Ładowanie danych rynkowych..."):
        bond_data = get_fred_bond_data()
        forex_data = get_eur_pln_rate()
    
    # Enhanced spot rate control with binomial model integration
    st.subheader("⚙️ Kontrola Kursu Spot - z Integracją Modelu Dwumianowego")
    
    # Get binomial prediction for integration
    with st.spinner("📊 Obliczanie prognozy dwumianowej..."):
        historical_data = get_historical_eur_pln_data(30)
        binomial_prediction = calculate_binomial_prediction(historical_data, forex_data['rate'], days=5)
    
    # Display binomial prediction status
    if binomial_prediction['success']:
        st.success(f"✅ Model dwumianowy aktywny | Prognoza 5D: {binomial_prediction['predicted_spot']:.4f} ({binomial_prediction['change_pct']:+.2f}%)")
    else:
        st.warning("⚠️ Model dwumianowy niedostępny - używam kursu spot")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        spot_rate_source = st.radio(
            "Źródło kursu do wyceny:",
            options=["api", "binomial", "manual"],
            format_func=lambda x: {
                "api": "🌐 API (Alpha Vantage/NBP)",
                "binomial": "📊 Najwyższa prognoza z modelu",
                "manual": "✋ Ręczny"
            }[x],
            key="dealer_spot_source",
            help="Wybierz źródło kursu dla kalkulacji forward"
        )
    
    with col2:
        if spot_rate_source == "api":
            spot_rate = forex_data['rate']
            spot_source = forex_data['source']
            st.info(f"Kurs API: {spot_rate:.4f} (źródło: {spot_source})")
            
        elif spot_rate_source == "binomial":
            if binomial_prediction['success']:
                spot_rate = binomial_prediction['predicted_spot']
                spot_source = f"Binomial 5D ({binomial_prediction['probability']:.1%} prob)"
                
                st.success(f"Prognoza dwumianowa: {spot_rate:.4f}")
                st.info(f"Zmiana vs obecny spot: {binomial_prediction['change_pct']:+.2f}%")
                st.info(f"Prawdopodobieństwo: {binomial_prediction['probability']:.1%}")
            else:
                spot_rate = forex_data['rate']
                spot_source = f"{forex_data['source']} (binomial fallback)"
                st.warning("Model dwumianowy niedostępny - używam kursu API")
                
        else:  # manual
            spot_rate = st.number_input(
                "Kurs EUR/PLN:",
                value=st.session_state.dealer_config['spot_rate'],
                min_value=3.50,
                max_value=6.00,
                step=0.0001,
                format="%.4f",
                key="dealer_spot_input",
                help="Wprowadź własny kurs spot do wyceny"
            )
            spot_source = "Manual"
    
    # Update pricing button
    if st.button("🔄 Zaktualizuj Wycenę", type="primary", use_container_width=True):
        bond_data = get_fred_bond_data()
        pl_yield = bond_data['Poland_10Y']['value'] if 'Poland_10Y' in bond_data else 5.42
        de_yield = bond_data['Germany_10Y']['value'] if 'Germany_10Y' in bond_data else 2.63
        
        update_dealer_config(
            spot_rate, spot_source, pl_yield, de_yield, 90,
            0.70, 0.40, 0.002, 0.25, 0.60, 0.000
        )
        
        if spot_rate_source == "binomial":
            st.success("✅ Wycena zaktualizowana z prognozą dwumianową!")
        else:
            st.success("✅ Wycena zaktualizowana!")
        
        st.rerun()

def create_client_hedging_advisor():
    """Panel zabezpieczeń - pokazuje kursy z panelu dealerskiego"""
    
    st.header("🛡️ Panel Zabezpieczeń EUR/PLN")
    st.markdown("*Kursy synchronizowane z panelem dealerskim*")
    
    # Check if dealer pricing is available
    if not st.session_state.dealer_pricing_data:
        st.warning("⚠️ Brak wyceny dealerskiej! Przejdź najpierw do panelu dealerskiego i zaktualizuj wycenę.")
        return
    
    # Show pricing sync status
    config = st.session_state.dealer_config
    source_icon = "📊" if "Binomial" in config['spot_source'] else "🌐" if "Alpha" in config['spot_source'] or "NBP" in config['spot_source'] else "✋"
    
    st.markdown(f"""
    <div class="pricing-sync">
        <h4 style="margin: 0;">✅ Wycena Zsynchronizowana {source_icon}</h4>
        <p style="margin: 0;">Kurs spot: {config['spot_rate']:.4f} ({config['spot_source']}) | Window: {config['window_days']} dni</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show binomial integration info if used
    if "Binomial" in config['spot_source']:
        st.info("🎯 Wycena używa najwyższego kursu z najczęstszej ścieżki modelu dwumianowego")
    
    # Client configuration
    st.subheader("⚙️ Parametry Zabezpieczenia")
    
    exposure_amount = st.number_input(
        "Kwota EUR do zabezpieczenia:",
        value=1_000_000,
        min_value=10_000,
        max_value=50_000_000,
        step=10_000,
        format="%d",
        help="Kwota ekspozycji EUR do zabezpieczenia"
    )
    
    st.markdown("---")
    st.subheader("💱 Dostępne Kursy Terminowe")
    
    # Show available rates
    if st.session_state.dealer_pricing_data:
        rates_data = []
        for pricing in st.session_state.dealer_pricing_data:
            client_rate = pricing['client_rate']
            spot_rate = config['spot_rate']
            rate_advantage = ((client_rate - spot_rate) / spot_rate) * 100
            
            rates_data.append({
                "Tenor": pricing['tenor_name'],
                "Kurs terminowy": f"{client_rate:.4f}",
                "vs Spot": f"{rate_advantage:+.2f}%",
                "Kwota PLN": f"{client_rate * exposure_amount:,.0f}",
                "Dodatkowy PLN": f"{(client_rate - spot_rate) * exposure_amount:+,.0f}"
            })
        
        df_rates = pd.DataFrame(rates_data)
        st.dataframe(df_rates, use_container_width=True, hide_index=True)

def create_binomial_model_panel():
    """5-DAY BINOMIAL TREE MODEL with Alpha Vantage data"""
    st.header("📊 Drzewo Dwumianowe - 5 Dni")
    st.markdown("*Krótkoterminowa prognoza EUR/PLN z Alpha Vantage + NBP data*")
    
    # Show dealer integration status
    if st.session_state.dealer_config.get('spot_source', '').startswith("Binomial"):
        st.success("🎯 Model jest aktywnie używany w wycenie dealerskiej!")
    else:
        st.info("📊 Model gotowy do użycia w panelu dealerskim")
    
    # Get current data
    current_forex = get_eur_pln_rate()
    historical_data = get_historical_eur_pln_data(30)
    
    # Calculate binomial prediction
    binomial_result = calculate_binomial_prediction(historical_data, current_forex['rate'], days=5)
    
    if binomial_result['success']:
        st.success(f"✅ Model aktywny - Najwyższy kurs z prognozy: {binomial_result['predicted_spot']:.4f}")
        st.info(f"Zmiana vs obecny: {binomial_result['change_pct']:+.2f}% | Dzień: {binomial_result['highest_day']}")
        
        # Show path rates
        st.subheader("📋 Kursy z Najczęstszej Ścieżki")
        
        path_data = []
        for day in range(6):
            if day < len(binomial_result['path_rates']):
                rate = binomial_result['path_rates'][day]
                is_highest = abs(rate - binomial_result['predicted_spot']) < 0.0001 and day > 0
                
                path_data.append({
                    "Dzień": day,
                    "Kurs": f"{rate:.4f}",
                    "Zmiana vs spot": f"{((rate/current_forex['rate'] - 1) * 100):+.2f}%",
                    "Status": "🎯 Najwyższy" if is_highest else "⚪ Normalny" if day > 0 else "📍 Start"
                })
        
        df_path = pd.DataFrame(path_data)
        st.dataframe(df_path, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Model dwumianowy niedostępny - brak wystarczających danych historycznych")

def main():
    """Main application entry point"""
    
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 2rem;">
        <div style="background: linear-gradient(45deg, #667eea, #764ba2); width: 60px; height: 60px; border-radius: 10px; margin-right: 1rem; display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 2rem;">🚀</span>
        </div>
        <h1 style="margin: 0; color: #2c3e50;">Zintegrowana Platforma FX</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("*Alpha Vantage + NBP + FRED APIs | Synchronizacja dealerska ↔ klient | Model Dwumianowy*")
    
    # Show sync status in header
    if st.session_state.dealer_pricing_data:
        config = st.session_state.dealer_config
        source_icon = "📊" if "Binomial" in config['spot_source'] else "🌐" if "Alpha" in config['spot_source'] or "NBP" in config['spot_source'] else "✋"
        st.success(f"✅ System zsynchronizowany {source_icon} | Spot: {config['spot_rate']:.4f} ({config['spot_source']}) | Window: {config['window_days']} dni | Kursy: {len(st.session_state.dealer_pricing_data)} tenorów")
    else:
        st.info("🔄 Oczekiwanie na wycenę dealerską...")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["🔧 Panel Dealerski", "🛡️ Panel Zabezpieczeń", "📊 Model Dwumianowy"])
    
    with tab1:
        create_dealer_panel()
    
    with tab2:
        create_client_hedging_advisor()
    
    with tab3:
        create_binomial_model_panel()

if __name__ == "__main__":
    main()
