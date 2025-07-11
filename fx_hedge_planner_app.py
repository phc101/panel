import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import math
from scipy.stats import norm
from math import comb

# Page config
st.set_page_config(
    page_title="Professional FX Calculator",
    page_icon="🚀",
    layout="wide"
)

# Alpha Vantage API Configuration
ALPHA_VANTAGE_API_KEY = "MQGKUNL9JWIJHF9S"
FRED_API_KEY = st.secrets.get("FRED_API_KEY", "693819ccc32ac43704fbbc15cfb4a6d7")

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
# API CLASSES
# ============================================================================

class AlphaVantageAPI:
    def __init__(self, api_key=ALPHA_VANTAGE_API_KEY):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
    
    def get_eur_pln_rate(self):
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
                    'source': 'Alpha Vantage',
                    'success': True
                }
            else:
                return self._get_nbp_fallback()
                
        except Exception as e:
            return self._get_nbp_fallback()
    
    def get_historical_eur_pln(self, days=30):
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
                rates = []
                dates = sorted(time_series.keys(), reverse=True)
                
                for date in dates[:days]:
                    rate = float(time_series[date]['4. close'])
                    rates.append(rate)
                
                if len(rates) >= 10:
                    return {
                        'rates': rates,
                        'dates': dates[:len(rates)],
                        'source': 'Alpha Vantage Historical',
                        'success': True,
                        'count': len(rates)
                    }
            
            return self._get_nbp_historical_fallback(days)
            
        except Exception as e:
            return self._get_nbp_historical_fallback(days)
    
    def _get_nbp_fallback(self):
        try:
            url = "https://api.nbp.pl/api/exchangerates/rates/a/eur/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('rates') and len(data['rates']) > 0:
                return {
                    'rate': data['rates'][0]['mid'],
                    'date': data['rates'][0]['effectiveDate'],
                    'source': 'NBP Backup',
                    'success': True
                }
        except Exception:
            pass
        
        return {
            'rate': 4.25,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'source': 'Fallback',
            'success': False
        }
    
    def _get_nbp_historical_fallback(self, days=30):
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days+10)
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            url = f"https://api.nbp.pl/api/exchangerates/rates/a/eur/{start_str}/{end_str}/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('rates') and len(data['rates']) >= 10:
                rates = [rate_data['mid'] for rate_data in data['rates']]
                dates = [rate_data['effectiveDate'] for rate_data in data['rates']]
                take_count = min(days, len(rates))
                
                return {
                    'rates': rates[-take_count:],
                    'dates': dates[-take_count:],
                    'source': 'NBP Historical Backup',
                    'success': True,
                    'count': take_count
                }
        except Exception:
            pass
        
        return {
            'rates': [4.25] * 20,
            'dates': [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(20)],
            'source': 'Synthetic Data',
            'success': False,
            'count': 20
        }

class FREDAPIClient:
    def __init__(self, api_key=FRED_API_KEY):
        self.api_key = api_key
    
    def get_series_data(self, series_id, limit=1, sort_order='desc'):
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
            return None
    
    def get_multiple_series(self, series_dict):
        results = {}
        for name, series_id in series_dict.items():
            data = self.get_series_data(series_id)
            if data:
                results[name] = data
        return results

# ============================================================================
# SESSION STATE
# ============================================================================

def initialize_session_state():
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
    if 'hedge_transactions' not in st.session_state:
        st.session_state.hedge_transactions = []

# ============================================================================
# CACHED DATA FUNCTIONS
# ============================================================================

@st.cache_data(ttl=3600)
def get_fred_bond_data():
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
            raise Exception("No data from FRED API")
        return data
    except Exception as e:
        return {
            'Poland_10Y': {'value': 5.42, 'date': '2025-07-03', 'source': 'Current Market'},
            'Germany_10Y': {'value': 2.63, 'date': '2025-07-03', 'source': 'Current Market'},
            'US_10Y': {'value': 4.28, 'date': '2025-07-03', 'source': 'Current Market'},
            'Euro_Area_10Y': {'value': 3.15, 'date': '2025-07-03', 'source': 'Current Market'}
        }

@st.cache_data(ttl=300)
def get_eur_pln_rate():
    alpha_api = AlphaVantageAPI()
    return alpha_api.get_eur_pln_rate()

@st.cache_data(ttl=1800)
def get_historical_eur_pln_data(days=30):
    alpha_api = AlphaVantageAPI()
    return alpha_api.get_historical_eur_pln(days)

# ============================================================================
# FORWARD CALCULATOR
# ============================================================================

class APIIntegratedForwardCalculator:
    def __init__(self, fred_client):
        self.fred_client = fred_client
        self.points_factor = 0.70
        self.risk_factor = 0.40
    
    def get_tenors_with_window(self, window_days):
        today = datetime.now()
        tenors = {}
        
        for i in range(1, 13):
            tenor_key = f"{i}M"
            tenor_start = today + timedelta(days=i*30)
            window_start = tenor_start
            window_end = tenor_start + timedelta(days=window_days)
            
            tenors[tenor_key] = {
                "name": f"{i} {'miesiąc' if i == 1 else 'miesiące' if i <= 4 else 'miesięcy'}",
                "months": i,
                "days": i * 30,
                "okno_od": window_start.strftime("%d.%m.%Y"),
                "rozliczenie_do": window_end.strftime("%d.%m.%Y")
            }
        
        return tenors
    
    def calculate_theoretical_forward_points(self, spot_rate, pl_yield, de_yield, days):
        T = days / 365.0
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
        curve_data = {}
        tenors = self.get_tenors_with_window(window_days)
        
        for tenor_key, tenor_info in tenors.items():
            months = tenor_info["months"]
            days = tenor_info["days"]
            
            theoretical = self.calculate_theoretical_forward_points(spot_rate, pl_yield, de_yield, days)
            forward_points = theoretical['forward_points']
            
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
        points_given_to_client = points_to_window * self.points_factor
        swap_risk_charged = swap_risk * self.risk_factor
        
        fwd_client_initial = spot_rate + points_given_to_client - swap_risk_charged
        fwd_to_open = spot_rate + points_to_window
        
        initial_profit = fwd_to_open - fwd_client_initial
        
        if initial_profit < min_profit_floor:
            fwd_client = fwd_to_open - min_profit_floor
            profit_per_eur = min_profit_floor
            adjustment_made = True
            adjustment_amount = fwd_client_initial - fwd_client
        else:
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
# SUPPORT FUNCTIONS
# ============================================================================

def calculate_dealer_pricing(config):
    calculator = APIIntegratedForwardCalculator(FREDAPIClient())
    calculator.points_factor = config['points_factor']
    calculator.risk_factor = config['risk_factor']
    
    forward_curve = calculator.generate_api_forward_points_curve(
        config['spot_rate'], 
        config['pl_yield'], 
        config['de_yield'], 
        config['bid_ask_spread'],
        config['window_days']
    )
    
    pricing_data = []
    
    for tenor_key, curve_data in forward_curve.items():
        tenor_days = curve_data["days"]
        tenor_points = curve_data["mid"]
        
        tenor_window_swap_risk = abs(tenor_points) * config['volatility_factor'] * np.sqrt(config['window_days'] / 90)
        tenor_window_swap_risk = max(tenor_window_swap_risk, 0.015)
        
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
    
    st.session_state.dealer_pricing_data = calculate_dealer_pricing(st.session_state.dealer_config)

# ============================================================================
# UI FUNCTIONS
# ============================================================================

def create_dealer_panel():
    st.header("🚀 Panel Dealerski - Wycena Master")
    st.markdown("*Ustaw parametry wyceny - te kursy będą widoczne w panelu zabezpieczeń*")
    
    # API Status
    st.subheader("📡 Status API")
    col1, col2 = st.columns(2)
    
    with col1:
        alpha_api = AlphaVantageAPI()
        forex_result = alpha_api.get_eur_pln_rate()
        
        if 'Alpha Vantage' in forex_result['source']:
            status_color = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
            status_text = "📈 Alpha Vantage API Active"
        elif 'NBP' in forex_result['source']:
            status_color = "linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%); color: #2d3436"
            status_text = "🏛️ NBP API Backup"
        else:
            status_color = "linear-gradient(135deg, #e17055 0%, #d63031 100%)"
            status_text = "⚠️ Fallback Mode"
        
        st.markdown(f"""
        <div class="alpha-api" style="background: {status_color};">
            <h4 style="margin: 0;">{status_text}</h4>
            <p style="margin: 0;">Rate: {forex_result['rate']:.4f}</p>
            <p style="margin: 0;">Source: {forex_result['source']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        historical_data = get_historical_eur_pln_data(30)
        st.markdown(f"""
        <div class="alpha-api">
            <h4 style="margin: 0;">📊 Historical Data</h4>
            <p style="margin: 0;">Source: {historical_data['source']}</p>
            <p style="margin: 0;">Data points: {historical_data['count']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Load market data
    with st.spinner("📡 Ładowanie danych rynkowych..."):
        bond_data = get_fred_bond_data()
        forex_data = get_eur_pln_rate()
    
    # Spot rate control
    st.subheader("⚙️ Kontrola Kursu Spot")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        use_manual_spot = st.checkbox(
            "Ustaw kurs ręcznie", 
            value=False,
            help="Odznacz aby używać automatycznego kursu z Alpha Vantage/NBP"
        )
    
    with col2:
        if use_manual_spot:
            spot_rate = st.number_input(
                "Kurs EUR/PLN:",
                value=st.session_state.dealer_config['spot_rate'],
                min_value=3.50,
                max_value=6.00,
                step=0.0001,
                format="%.4f"
            )
            spot_source = "Manual"
        else:
            spot_rate = forex_data['rate']
            spot_source = forex_data['source']
            st.info(f"Automatyczny kurs: {spot_rate:.4f} (źródło: {spot_source})")
    
    # Market data display
    st.subheader("📊 Dane Rynkowe")
    col1, col2, col3, col4 = st.columns(4)
    
    pl_yield = bond_data['Poland_10Y']['value'] if 'Poland_10Y' in bond_data else 5.42
    de_yield = bond_data['Germany_10Y']['value'] if 'Germany_10Y' in bond_data else 2.63
    spread = pl_yield - de_yield
    
    with col1:
        st.metric("EUR/PLN Spot", f"{spot_rate:.4f}", help=f"Źródło: {spot_source}")
    
    with col2:
        st.metric("Rentowność PL 10Y", f"{pl_yield:.2f}%")
    
    with col3:
        st.metric("Rentowność DE 10Y", f"{de_yield:.2f}%")
    
    with col4:
        st.metric("Spread PL-DE 10Y", f"{spread:.2f}pp")
    
    # Configuration
    st.markdown("---")
    st.subheader("⚙️ Konfiguracja Transakcji")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        window_days = st.number_input(
            "Długość okna (dni):",
            value=st.session_state.dealer_config['window_days'],
            min_value=30,
            max_value=365,
            step=5
        )
    
    with col2:
        nominal_amount = st.number_input(
            "Kwota nominalna (EUR):",
            value=2_500_000,
            min_value=10_000,
            max_value=100_000_000,
            step=10_000,
            format="%d"
        )
    
    with col3:
        leverage = st.number_input(
            "Współczynnik dźwigni:",
            value=1.0,
            min_value=1.0,
            max_value=3.0,
            step=0.1
        )
    
    # Advanced parameters
    with st.expander("🔧 Zaawansowane Parametry Wyceny"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            points_factor = st.slider(
                "Współczynnik punktów (% dla klienta):",
                min_value=0.60,
                max_value=0.85,
                value=st.session_state.dealer_config['points_factor'],
                step=0.01
            )
        
        with col2:
            risk_factor = st.slider(
                "Współczynnik ryzyka (% obciążenia):",
                min_value=0.30,
                max_value=0.60,
                value=st.session_state.dealer_config['risk_factor'],
                step=0.01
            )
        
        with col3:
            bid_ask_spread = st.number_input(
                "Spread bid-ask:",
                value=st.session_state.dealer_config['bid_ask_spread'],
                min_value=0.001,
                max_value=0.005,
                step=0.0005,
                format="%.4f"
            )
        
        col4, col5, col6 = st.columns(3)
        
        with col4:
            minimum_profit_floor = st.number_input(
                "Min próg zysku (PLN/EUR):",
                value=st.session_state.dealer_config['minimum_profit_floor'],
                min_value=-0.020,
                max_value=0.020,
                step=0.001,
                format="%.4f"
            )
        
        with col5:
            volatility_factor = st.slider(
                "Współczynnik zmienności:",
                min_value=0.15,
                max_value=0.35,
                value=st.session_state.dealer_config['volatility_factor'],
                step=0.01
            )
        
        with col6:
            hedging_savings_pct = st.slider(
                "Oszczędności hedging (%):",
                min_value=0.40,
                max_value=0.80,
                value=st.session_state.dealer_config['hedging_savings_pct'],
                step=0.05
            )
    
    # Update button
    if st.button("🔄 Zaktualizuj Wycenę", type="primary", use_container_width=True):
        update_dealer_config(
            spot_rate, spot_source, pl_yield, de_yield, window_days,
            points_factor, risk_factor, bid_ask_spread, volatility_factor,
            hedging_savings_pct, minimum_profit_floor
        )
        st.success("✅ Wycena zaktualizowana!")
        st.rerun()
    
    # Show pricing if available
    if st.session_state.dealer_pricing_data:
        st.markdown("---")
        st.subheader("💼 Aktualna Wycena Dealerska")
        
        pricing_df_data = []
        for pricing in st.session_state.dealer_pricing_data:
            pricing_df_data.append({
                "Tenor": pricing['tenor_name'],
                "Days": pricing['tenor_days'],
                "Points": f"{pricing['forward_points']:.4f}",
                "Risk": f"{pricing['swap_risk']:.4f}",
                "Client Rate": f"{pricing['client_rate']:.4f}",
                "Profit/EUR": f"{pricing['profit_per_eur']:.4f}",
                "Total PLN": f"{pricing['profit_per_eur'] * nominal_amount:,.0f}"
            })
        
        df_pricing = pd.DataFrame(pricing_df_data)
        st.dataframe(df_pricing, use_container_width=True, height=400)
        
        # Portfolio summary with percentage metrics
        st.subheader("📊 Podsumowanie Portfolio")
        
        # Calculate portfolio totals
        portfolio_totals = {
            'total_min_profit': 0,
            'total_max_profit': 0,
            'total_expected_profit': 0,
            'total_notional': 0,
            'total_points_to_window': 0,
            'total_swap_risk': 0,
            'total_client_premium': 0
        }
        
        for pricing in st.session_state.dealer_pricing_data:
            # Calculate window forward metrics
            window_min_profit_per_eur = pricing['profit_per_eur']
            window_max_profit_per_eur = window_min_profit_per_eur + (pricing['swap_risk'] * hedging_savings_pct)
            window_expected_profit_per_eur = (window_min_profit_per_eur + window_max_profit_per_eur) / 2
            
            window_min_profit_total = window_min_profit_per_eur * nominal_amount
            window_max_profit_total = window_max_profit_per_eur * nominal_amount
            window_expected_profit_total = window_expected_profit_per_eur * nominal_amount
            
            portfolio_totals['total_min_profit'] += window_min_profit_total
            portfolio_totals['total_max_profit'] += window_max_profit_total
            portfolio_totals['total_expected_profit'] += window_expected_profit_total
            portfolio_totals['total_notional'] += nominal_amount
            portfolio_totals['total_points_to_window'] += pricing['forward_points'] * nominal_amount
            portfolio_totals['total_swap_risk'] += pricing['swap_risk'] * nominal_amount
            portfolio_totals['total_client_premium'] += (pricing['client_rate'] - spot_rate) * nominal_amount
        
        # Calculate percentage metrics
        total_exposure_pln = spot_rate * portfolio_totals['total_notional']
        min_profit_pct = (portfolio_totals['total_min_profit'] / total_exposure_pln) * 100
        expected_profit_pct = (portfolio_totals['total_expected_profit'] / total_exposure_pln) * 100
        max_profit_pct = (portfolio_totals['total_max_profit'] / total_exposure_pln) * 100
        
        # First row - PLN amounts
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Portfolio Min Zysk", 
                f"{portfolio_totals['total_min_profit']:,.0f} PLN",
                help="Suma wszystkich gwarantowanych bank spreads"
            )
        
        with col2:
            st.metric(
                "Portfolio Oczekiwany", 
                f"{portfolio_totals['total_expected_profit']:,.0f} PLN",
                help="Średnia scenariuszy min/max"
            )
        
        with col3:
            st.metric(
                "Portfolio Max Zysk", 
                f"{portfolio_totals['total_max_profit']:,.0f} PLN",
                help="Suma bank spreads + oszczędności hedging"
            )
        
        with col4:
            st.metric(
                "Zakres Zysku", 
                f"{portfolio_totals['total_max_profit'] - portfolio_totals['total_min_profit']:,.0f} PLN",
                help="Zmienność całego portfolio"
            )
        
        # Second row - percentage metrics (KAFELKI Z MARŻAMI)
        st.markdown("### 📊 Marże Procentowe")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="profit-metric">
                <h4 style="margin: 0; color: white;">Min Marża</h4>
                <h2 style="margin: 0; color: white;">{min_profit_pct:.3f}%</h2>
                <p style="margin: 0; color: #f8f9fa;">vs całkowita ekspozycja</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="profit-metric" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
                <h4 style="margin: 0; color: white;">Oczekiwana Marża</h4>
                <h2 style="margin: 0; color: white;">{expected_profit_pct:.3f}%</h2>
                <p style="margin: 0; color: #f8f9fa;">realistyczny scenariusz</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="profit-metric" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <h4 style="margin: 0; color: white;">Max Marża</h4>
                <h2 style="margin: 0; color: white;">{max_profit_pct:.3f}%</h2>
                <p style="margin: 0; color: #f8f9fa;">optymistyczny scenariusz</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            margin_volatility = max_profit_pct - min_profit_pct
            st.markdown(f"""
            <div class="profit-metric" style="background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%); color: #2d3436;">
                <h4 style="margin: 0;">Volatility Marży</h4>
                <h2 style="margin: 0;">{margin_volatility:.3f}pp</h2>
                <p style="margin: 0;">zakres zmienności</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Additional portfolio metrics
        st.markdown("### ⚙️ Parametry Portfolio")
        col1, col2, col3, col4 = st.columns(4)
        
        portfolio_avg_points = portfolio_totals['total_points_to_window'] / portfolio_totals['total_notional']
        portfolio_avg_swap_risk = portfolio_totals['total_swap_risk'] / portfolio_totals['total_notional']
        portfolio_avg_client_rate = spot_rate + portfolio_avg_points * points_factor - portfolio_avg_swap_risk * risk_factor
        
        with col1:
            st.metric(
                "Średnie Punkty", 
                f"{portfolio_avg_points:.4f}",
                help="Średnia ważona punktów terminowych"
            )
        
        with col2:
            st.metric(
                "Średnie Ryzyko Swap", 
                f"{portfolio_avg_swap_risk:.4f}",
                help=f"Średnie ryzyko swap dla {window_days}-dniowych okien"
            )
        
        with col3:
            st.metric(
                "Średni Kurs Klienta", 
                f"{portfolio_avg_client_rate:.4f}",
                help="Średni kurs klienta w portfolio"
            )
        
        with col4:
            risk_reward_ratio = portfolio_totals['total_max_profit'] / portfolio_totals['total_min_profit'] if portfolio_totals['total_min_profit'] > 0 else float('inf')
            st.metric(
                "Risk/Reward", 
                f"{risk_reward_ratio:.1f}x",
                help="Stosunek max/min zysku"
            )
        
        # Deal summary
        st.markdown("---")
        st.subheader("📋 Podsumowanie Transakcji")
        
        with st.container():
            summary_col1, summary_col2 = st.columns([1, 1])
            
            with summary_col1:
                st.markdown(f"""
                <div class="metric-card">
                    <h4>💼 Strategia Portfolio Window Forward</h4>
                    <p><strong>Strategia:</strong> 12 Window Forwards z {window_days}-dniową elastycznością</p>
                    <p><strong>Całkowity Nominał:</strong> €{portfolio_totals['total_notional']:,}</p>
                    <p><strong>Kurs Spot:</strong> {spot_rate:.4f} ({spot_source})</p>
                    <p><strong>Średni Kurs Klienta:</strong> {portfolio_avg_client_rate:.4f}</p>
                    <p><strong>Points Factor:</strong> {points_factor:.1%}</p>
                    <p><strong>Risk Factor:</strong> {risk_factor:.1%}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with summary_col2:
                st.markdown(f"""
                <div class="metric-card">
                    <h4>💰 Podsumowanie Finansowe</h4>
                    <p><strong>Oczekiwany Zysk:</strong> {portfolio_totals['total_expected_profit']:,.0f} PLN ({expected_profit_pct:.3f}%)</p>
                    <p><strong>Portfolio Minimum:</strong> {portfolio_totals['total_min_profit']:,.0f} PLN ({min_profit_pct:.3f}%)</p>
                    <p><strong>Portfolio Maximum:</strong> {portfolio_totals['total_max_profit']:,.0f} PLN ({max_profit_pct:.3f}%)</p>
                    <p><strong>Współczynnik Zmienności:</strong> {volatility_factor:.2f}</p>
                    <p><strong>Oszczędności Hedging:</strong> {hedging_savings_pct:.0%}</p>
                    <p><strong>Dźwignia:</strong> {leverage}x</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("👆 Kliknij 'Zaktualizuj Wycenę' aby wygenerować kursy")

def create_client_hedging_advisor():
    st.header("🛡️ Panel Zabezpieczeń EUR/PLN")
    st.markdown("*Kursy synchronizowane z panelem dealerskim*")
    
    if not st.session_state.dealer_pricing_data:
        st.warning("⚠️ Brak wyceny dealerskiej! Przejdź do panelu dealerskiego.")
        forex_data = get_eur_pln_rate()
        st.info(f"Aktualny kurs EUR/PLN: {forex_data['rate']:.4f}")
        return
    
    config = st.session_state.dealer_config
    
    st.markdown(f"""
    <div class="pricing-sync">
        <h4 style="margin: 0;">✅ Wycena Zsynchronizowana</h4>
        <p style="margin: 0;">Spot: {config['spot_rate']:.4f} | Window: {config['window_days']} dni</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Professional transaction interface like the bank example
    st.markdown("---")
    st.subheader("💱 Nowa Transakcja Forward Elastyczny")
    
    # Transaction direction (like the bank interface)
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        st.markdown("**SPRZEDAJ**")
        sell_currency = st.selectbox("", ["EUR"], key="sell_curr", help="Waluta sprzedaży")
    
    with col2:
        st.markdown("**KUP**")
        buy_currency = st.selectbox("", ["PLN"], key="buy_curr", help="Waluta zakupu")
    
    with col3:
        st.markdown("**CAŁKOWITY WOLUMEN**")
        volume = st.number_input(
            "",
            value=1_000_000,
            min_value=10_000,
            max_value=50_000_000,
            step=10_000,
            format="%d",
            help="Kwota w EUR"
        )
    
    # Date selection with timeline (similar to bank interface)
    st.markdown("### 📅 Wybór Terminów Wykonania")
    
    # Professional date picker
    col1, col2, col3 = st.columns(3)
    
    with col1:
        settlement_date = st.date_input(
            "**Data pierwszego wykonania:**",
            value=(datetime.now() + timedelta(days=90)).date(),
            min_value=datetime.now().date(),
            max_value=(datetime.now() + timedelta(days=730)).date(),
            help="Data rozliczenia transakcji"
        )
    
    with col2:
        window_days = st.number_input(
            "**Długość okna (dni):**",
            value=config['window_days'],
            min_value=30,
            max_value=365,
            step=5,
            help="Okres elastyczności wykonania"
        )
    
    with col3:
        execution_type = st.selectbox(
            "**Typ wykonania:**",
            ["Forward Elastyczny", "Forward Standardowy", "Window Forward"],
            help="Rodzaj kontraktu terminowego"
        )
    
    # Calculate and display rates
    settlement_datetime = datetime.combine(settlement_date, datetime.min.time())
    today_datetime = datetime.now()
    days_to_settlement = (settlement_datetime - today_datetime).days
    
    # Calculate forward rate for this specific date
    calculator = APIIntegratedForwardCalculator(FREDAPIClient())
    theoretical = calculator.calculate_theoretical_forward_points(
        config['spot_rate'], 
        config['pl_yield'], 
        config['de_yield'], 
        days_to_settlement
    )
    
    forward_points = theoretical['forward_points']
    tenor_window_swap_risk = abs(forward_points) * config['volatility_factor'] * np.sqrt(window_days / 90)
    tenor_window_swap_risk = max(tenor_window_swap_risk, 0.015)
    
    calculator.points_factor = config['points_factor']
    calculator.risk_factor = config['risk_factor']
    
    rates_result = calculator.calculate_professional_rates(
        config['spot_rate'], 
        forward_points, 
        tenor_window_swap_risk, 
        config['minimum_profit_floor']
    )
    
    client_rate = rates_result['fwd_client']
    
    # Professional rate display
    st.markdown("### 💰 Wycena Transakcji")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="client-summary">
            <h4 style="margin: 0; color: #2e68a5;">Kurs Zabezpieczenia</h4>
            <h2 style="margin: 0; color: #2c3e50;">{client_rate:.4f}</h2>
            <p style="margin: 0; color: #666;">EUR/PLN</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="client-summary">
            <h4 style="margin: 0; color: #2e68a5;">Kurs Końcowy</h4>
            <h2 style="margin: 0; color: #2c3e50;">{client_rate:.4f}</h2>
            <p style="margin: 0; color: #666;">Gwarantowany</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        pln_amount = client_rate * volume
        st.markdown(f"""
        <div class="client-summary">
            <h4 style="margin: 0; color: #2e68a5;">Kwota PLN</h4>
            <h2 style="margin: 0; color: #2c3e50;">{pln_amount:,.0f}</h2>
            <p style="margin: 0; color: #666;">Do otrzymania</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        rate_advantage = ((client_rate - config['spot_rate']) / config['spot_rate']) * 100
        advantage_pln = (client_rate - config['spot_rate']) * volume
        color = "#28a745" if rate_advantage > 0 else "#dc3545"
        st.markdown(f"""
        <div class="client-summary">
            <h4 style="margin: 0; color: #2e68a5;">Wycena do Rynku</h4>
            <h2 style="margin: 0; color: {color};">{advantage_pln:+,.0f} PLN</h2>
            <p style="margin: 0; color: #666;">{rate_advantage:+.2f}% vs spot</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Professional add transaction button
    st.markdown("---")
    if st.button("➕ Dodaj elastyczny kontrakt forwardowy", type="primary", use_container_width=True):
        # Calculate execution window
        execution_window_end = settlement_datetime
        execution_window_start = execution_window_end - timedelta(days=window_days)
        
        # Determine tenor name
        months_approx = days_to_settlement / 30
        if months_approx < 1:
            tenor_name = f"{days_to_settlement} dni"
        else:
            tenor_name = f"{months_approx:.0f}M+"
        
        # Add to transactions list
        transaction_id = len(st.session_state.hedge_transactions) + 1
        st.session_state.hedge_transactions.append({
            "nr": transaction_id,
            "typ": "Forward elastyczny",
            "pierwsze_wykonanie": settlement_date.strftime("%d %b %Y"),
            "data_wygasniecia": execution_window_end.strftime("%d %b %Y"),
            "kwota_sprzedazy": f"(EUR) {volume:,.0f}",
            "kwota_zakupu": f"(PLN) {pln_amount:,.0f}",
            "kurs_zabezpieczenia": f"{client_rate:.4f}",
            "kurs_koncowy": f"{client_rate:.4f}",
            "wycena_do_rynku": f"{advantage_pln:+,.0f} PLN" if advantage_pln != 0 else "0,00 PLN",
            "status": "PLANOWANE",
            "tenor": tenor_name,
            "window_days": window_days,
            "days_to_settlement": days_to_settlement
        })
        st.success(f"✅ Dodano kontrakt Forward Elastyczny na {volume:,.0f} EUR")
        st.rerun()
    
    # Professional transaction list (like bank interface)
    if st.session_state.hedge_transactions:
        st.markdown("---")
        st.markdown("## Lista transakcji")
        
        # Summary header like in bank interface - with error handling
        try:
            total_volume_eur = sum(
                float(str(t['kwota_sprzedazy']).replace('(EUR) ', '').replace(',', '')) 
                for t in st.session_state.hedge_transactions
                if 'kwota_sprzedazy' in t
            )
        except (KeyError, ValueError, TypeError):
            total_volume_eur = 0
        
        st.markdown(f"""
        <div style="background: #f8f9fa; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #28a745; margin: 1rem 0;">
            <h4 style="margin: 0; color: #28a745;">100% WOLUMENU ZABEZPIECZONE W FORWARD ELASTYCZNY</h4>
            <p style="margin: 0.5rem 0 0 0; color: #666;">
                Usługa Elastycznych kontraktów terminowych umożliwia korzystanie z zalet kontraktów terminowych, 
                jednocześnie zapewniając elastyczność w terminach płatności. Dzięki Elastycznym kontraktom terminowym 
                można <strong>uzyskać korzystny kurs</strong> walutowy po kilku dni od ustalenia kursu i wykorzystywać je do jednej lub kilku przyszłych płatności z elastycznymi terminami.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Professional table header
        st.markdown("### Otwarte i zaplanowane")
        
        # Create professional table layout
        transactions_data = []
        
        for i, transaction in enumerate(st.session_state.hedge_transactions, 1):
            # Safely get values with defaults - ensure no NaN values
            status = str(transaction.get('status', 'PLANOWANE')).replace('nan', 'PLANOWANE')
            typ = str(transaction.get('typ', 'Forward elastyczny')).replace('nan', 'Forward elastyczny')
            pierwsze_wykonanie = str(transaction.get('pierwsze_wykonanie', 'Brak daty')).replace('nan', 'Brak daty')
            data_wygasniecia = str(transaction.get('data_wygasniecia', 'Brak daty')).replace('nan', 'Brak daty')
            kwota_sprzedazy = str(transaction.get('kwota_sprzedazy', '(EUR) 0')).replace('nan', '(EUR) 0')
            kwota_zakupu = str(transaction.get('kwota_zakupu', '(PLN) 0')).replace('nan', '(PLN) 0')
            kurs_zabezpieczenia = str(transaction.get('kurs_zabezpieczenia', '0.0000')).replace('nan', '0.0000')
            kurs_koncowy = str(transaction.get('kurs_koncowy', '0.0000')).replace('nan', '0.0000')
            wycena_do_rynku = str(transaction.get('wycena_do_rynku', '0 PLN')).replace('nan', '0 PLN')
            
            transactions_data.append({
                "#": i,
                "TYP": typ,
                "PIERWSZE WYKONANIE": pierwsze_wykonanie,
                "DATA WYGAŚNIĘCIA": data_wygasniecia,
                "KWOTA SPRZEDAŻY": kwota_sprzedazy,
                "KWOTA ZAKUPU": kwota_zakupu,
                "KURS ZABEZPIECZENIA": kurs_zabezpieczenia,
                "KURS KOŃCOWY": kurs_koncowy,
                "WYCENA DO RYNKU": wycena_do_rynku,
                "STATUS": status
            })
        
        # Display table if we have data
        if transactions_data:
            df_transactions = pd.DataFrame(transactions_data)
            
            # Display the professional table without complex styling to avoid errors
            st.dataframe(df_transactions, use_container_width=True, height=400, hide_index=True)
            
            # Professional summary metrics with safe calculations
            st.markdown("### 📊 Podsumowanie Portfolio")
            
            try:
                # Safe calculation of totals
                total_pln = 0
                total_volume_eur_calc = 0
                total_market_value = 0
                
                for t in st.session_state.hedge_transactions:
                    # Safely parse EUR volume
                    try:
                        kwota_eur_str = str(t.get('kwota_sprzedazy', '0')).replace('(EUR) ', '').replace(',', '')
                        if kwota_eur_str and kwota_eur_str != 'nan':
                            total_volume_eur_calc += float(kwota_eur_str)
                    except (ValueError, TypeError):
                        pass
                    
                    # Safely parse PLN amount
                    try:
                        kwota_pln_str = str(t.get('kwota_zakupu', '0')).replace('(PLN) ', '').replace(',', '')
                        if kwota_pln_str and kwota_pln_str != 'nan':
                            total_pln += float(kwota_pln_str)
                    except (ValueError, TypeError):
                        pass
                    
                    # Safely parse market value
                    try:
                        market_val_str = str(t.get('wycena_do_rynku', '0')).replace(' PLN', '').replace(',', '').replace('+', '').replace('-', '')
                        if market_val_str and market_val_str != 'nan':
                            total_market_value += float(market_val_str)
                    except (ValueError, TypeError):
                        pass
                
                # Calculate average rate safely
                avg_rate = total_pln / total_volume_eur_calc if total_volume_eur_calc > 0 else 0
                
            except Exception:
                # Fallback values if any calculation fails
                total_volume_eur_calc = 0
                total_pln = 0
                avg_rate = 0
                total_market_value = 0
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Łączny Wolumen",
                    f"€{total_volume_eur:,.0f}",
                    help="Suma wszystkich kontraktów"
                )
            
            with col2:
                st.metric(
                    "Średni Kurs",
                    f"{avg_rate:.4f}",
                    delta=f"{((avg_rate - config['spot_rate']) / config['spot_rate'] * 100):+.2f}% vs spot",
                    help="Średnia ważona kursów zabezpieczenia"
                )
            
            with col3:
                st.metric(
                    "Łączna Kwota PLN",
                    f"{total_pln:,.0f} PLN",
                    help="Suma PLN do otrzymania"
                )
            
            with col4:
                st.metric(
                    "Wycena Portfolio",
                    f"{total_market_value:+,.0f} PLN",
                    help="Łączna wycena do rynku"
                )
    # Add a simple chart showing forward curve
    st.markdown("---")
    st.subheader("📈 Krzywa Forward EUR/PLN")
    
    if st.session_state.dealer_pricing_data:
        tenors_list = [p['tenor_name'] for p in st.session_state.dealer_pricing_data]
        forward_rates = [p['client_rate'] for p in st.session_state.dealer_pricing_data]
        spot_rates = [config['spot_rate']] * len(tenors_list)
        
        fig = go.Figure()
        
        # Spot line
        fig.add_trace(
            go.Scatter(
                x=tenors_list,
                y=spot_rates,
                mode='lines',
                name=f'Kurs spot ({config["spot_rate"]:.4f})',
                line=dict(color='red', width=2, dash='dash'),
                hovertemplate='Spot: %{y:.4f}<extra></extra>'
            )
        )
        
        # Forward rates
        fig.add_trace(
            go.Scatter(
                x=tenors_list,
                y=forward_rates,
                mode='lines+markers',
                name='Kursy terminowe',
                line=dict(color='#2e68a5', width=3),
                marker=dict(size=10, color='#2e68a5'),
                hovertemplate='%{x}: %{y:.4f}<extra></extra>'
            )
        )
        
        fig.update_layout(
            title="Dostępne kursy terminowe vs kurs spot",
            xaxis_title="Tenor",
            yaxis_title="Kurs EUR/PLN",
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Color coding for transactions
        def highlight_transactions(row):
            profit_str = str(row['Profit PLN']).replace(',', '').replace('+', '').replace(' PLN', '')
            try:
                profit = float(profit_str)
                if profit > 0:
                    return ['background-color: #d4edda'] * len(row)  # Green for profit
                elif profit < 0:
                    return ['background-color: #f8d7da'] * len(row)  # Red for loss
                else:
                    return ['background-color: #fff3cd'] * len(row)  # Yellow for neutral
            except:
                return [''] * len(row)
        
        st.dataframe(
            display_df.style.apply(highlight_transactions, axis=1),
            use_container_width=True,
            hide_index=True
        )
        
        # Transactions summary
        st.markdown("### 📊 Podsumowanie Transakcji")
        
        total_planned = sum(float(str(row['Kwota EUR']).replace(',', '')) for row in st.session_state.hedge_transactions)
        total_profit = sum(float(str(row['Profit PLN']).replace(',', '').replace('+', '').replace(' PLN', '')) for row in st.session_state.hedge_transactions)
        avg_rate = sum(float(row['Kurs']) * float(str(row['Kwota EUR']).replace(',', '')) for row in st.session_state.hedge_transactions) / total_planned if total_planned > 0 else 0
        
        # Calculate window diversity metrics
        window_lengths = [row.get('Długość okna', 0) for row in st.session_state.hedge_transactions if 'Długość okna' in row]
        avg_window = np.mean(window_lengths) if window_lengths else 0
        min_window = min(window_lengths) if window_lengths else 0
        max_window = max(window_lengths) if window_lengths else 0
        
        # Calculate tenor diversity
        days_to_settlements = [row.get('Dni do rozliczenia', 0) for row in st.session_state.hedge_transactions if 'Dni do rozliczenia' in row]
        avg_tenor_days = np.mean(days_to_settlements) if days_to_settlements else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Łączna Kwota",
                f"€{total_planned:,.0f}",
                help="Suma wszystkich transakcji"
            )
        
        with col2:
            st.metric(
                "Średni Kurs",
                f"{avg_rate:.4f}",
                delta=f"{((avg_rate - config['spot_rate']) / config['spot_rate'] * 100):+.2f}% vs spot" if avg_rate > 0 else "N/A",
                help="Średnia ważona kursów"
            )
        
        with col3:
            st.metric(
                "Łączny Profit",
                f"{total_profit:+,.0f} PLN",
                help="Suma korzyści vs pozostanie na spot"
            )
        
        with col4:
            st.metric(
                "Średni Tenor",
                f"{avg_tenor_days:.0f} dni",
                help="Średnia liczba dni do rozliczenia"
            )
        
        # Window analysis
        if window_lengths:
            st.markdown("### 🪟 Analiza Okien Wykonania")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Średnie Okno",
                    f"{avg_window:.0f} dni",
                    help="Średnia długość okien wykonania"
                )
            
            with col2:
                st.metric(
                    "Zakres Okien",
                    f"{min_window}-{max_window} dni",
                    help="Minimalne i maksymalne okno"
                )
            
            with col3:
                unique_windows = len(set(window_lengths))
                st.metric(
                    "Różne Okna",
                    f"{unique_windows}",
                    help="Liczba różnych długości okien"
                )
            
            with col4:
                window_flexibility = "Wysoka" if unique_windows > 2 else "Średnia" if unique_windows > 1 else "Niska"
                flexibility_color = "🟢" if unique_windows > 2 else "🟡" if unique_windows > 1 else "🔴"
                st.metric(
                    "Elastyczność",
                    f"{flexibility_color} {window_flexibility}",
                    help="Ocena różnorodności okien"
                )
    else:
        st.info("📋 Brak dodanych transakcji. Użyj przycisku 'Dodaj Transakcję' aby rozpocząć.")

def create_binomial_model_panel():
    st.header("📊 Drzewo Dwumianowe - 5 Dni")
    st.markdown("*Krótkoterminowa prognoza EUR/PLN*")
    
    with st.spinner("📡 Pobieranie danych..."):
        historical_data = get_historical_eur_pln_data(30)
        current_forex = get_eur_pln_rate()
    
    # Data source info
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="alpha-api">
            <h4 style="margin: 0;">📈 Kurs Bieżący</h4>
            <p style="margin: 0;">Rate: {current_forex['rate']:.4f}</p>
            <p style="margin: 0;">Source: {current_forex['source']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="alpha-api">
            <h4 style="margin: 0;">📊 Dane Historyczne</h4>
            <p style="margin: 0;">Points: {historical_data['count']}</p>
            <p style="margin: 0;">Source: {historical_data['source']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Calculate volatility
    try:
        if historical_data['success'] and len(historical_data['rates']) >= 20:
            rates = historical_data['rates']
            last_20_rates = rates[-20:] if len(rates) >= 20 else rates
            current_spot = last_20_rates[-1]
            
            mean_20_days = np.mean(last_20_rates)
            std_20_days = np.std(last_20_rates)
            
            p_up_empirical = 1 - norm.cdf(current_spot, mean_20_days, std_20_days)
            p_down_empirical = 1 - p_up_empirical
            
            rolling_vol = std_20_days / current_spot
            data_count = len(last_20_rates)
            
            if rolling_vol > 0:
                st.success(f"✅ Model z ostatnich {data_count} dni")
                st.info(f"P(up): {p_up_empirical:.3f}, P(down): {p_down_empirical:.3f}")
                st.info(f"Volatility: {rolling_vol*100:.2f}% dzienna")
            else:
                raise Exception("Zero volatility")
        else:
            raise Exception("Insufficient data")
            
    except Exception as e:
        rolling_vol = 0.0034
        current_spot = current_forex['rate']
        mean_20_days = current_spot
        std_20_days = current_spot * 0.0034
        p_up_empirical = 0.5
        p_down_empirical = 0.5
        st.warning("⚠️ Używam domyślnych wartości")
    
    # Model parameters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        spot_rate = st.number_input(
            "Kurs spot:",
            value=current_spot,
            min_value=3.50,
            max_value=6.00,
            step=0.0001,
            format="%.4f"
        )
    
    with col2:
        st.metric("Horyzont", "5 dni roboczych")
        days = 5
    
    with col3:
        use_empirical = st.checkbox("Użyj empirycznych prawdopodobieństw", value=True)
        
        if use_empirical:
            p_up_display = p_up_empirical
            p_down_display = p_down_empirical
            st.success(f"P(up)={p_up_display:.3f}")
        else:
            daily_vol = st.slider("Zmienność (%):", 0.1, 2.0, rolling_vol*100, 0.05) / 100
            dt = 1/252
            u = np.exp(daily_vol * np.sqrt(dt))
            d = 1/u
            r = 0.02/252
            p_up_display = (np.exp(r * dt) - d) / (u - d)
            p_down_display = 1 - p_up_display
            st.info(f"P(up)={p_up_display:.3f}")
    
    # Build tree
    if use_empirical:
        p = p_up_empirical
        u = 1 + rolling_vol
        d = 1 - rolling_vol
    else:
        dt = 1/252
        u = np.exp(daily_vol * np.sqrt(dt))
        d = 1/u
        r = 0.02/252
        p = (np.exp(r * dt) - d) / (u - d)
    
    tree = {}
    
    for day in range(6):
        tree[day] = {}
        
        if day == 0:
            tree[day][0] = spot_rate
        else:
            for j in range(day + 1):
                ups = j
                downs = day - j
                rate = spot_rate * (u ** ups) * (d ** downs)
                tree[day][j] = rate
    
    # Most probable path
    most_probable_path = []
    for day in range(6):
        if day == 0:
            most_probable_path.append(0)
        else:
            best_j = 0
            best_prob = 0
            
            for j in range(day + 1):
                if use_empirical:
                    node_prob = comb(day, j) * (p_up_empirical ** j) * (p_down_empirical ** (day - j))
                else:
                    node_prob = comb(day, j) * (p ** j) * ((1 - p) ** (day - j))
                
                if node_prob > best_prob:
                    best_prob = node_prob
                    best_j = j
            
            most_probable_path.append(best_j)
    
    # Final prediction
    st.subheader("🎯 Prognoza Finalna")
    
    final_day = days
    final_j = most_probable_path[final_day]
    final_predicted_rate = tree[final_day][final_j]
    change_pct = ((final_predicted_rate - spot_rate) / spot_rate) * 100
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Prognoza (5 dni)", f"{final_predicted_rate:.4f}", delta=f"{change_pct:+.2f}%")
    
    with col2:
        if use_empirical:
            prob = comb(final_day, final_j) * (p_up_empirical ** final_j) * (p_down_empirical ** (final_day - final_j))
        else:
            prob = comb(final_day, final_j) * (p ** final_j) * ((1 - p) ** (final_day - final_j))
        
        st.metric("Prawdopodobieństwo", f"{prob*100:.1f}%")
    
    with col3:
        final_rates = [tree[5][j] for j in range(6)]
        min_rate = min(final_rates)
        max_rate = max(final_rates)
        st.metric("Zakres", f"{min_rate:.4f} - {max_rate:.4f}")
    
    # Binomial tree visualization
    st.subheader("🌳 Drzewo Dwumianowe")
    
    fig = go.Figure()
    
    # Business days for labels
    today = datetime.now()
    business_days = []
    current_date = today
    
    while len(business_days) < 5:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:
            business_days.append(current_date)
    
    weekdays = ["Pon", "Wt", "Śr", "Czw", "Pt"]
    
    # Plot nodes
    for day in range(6):
        for j in range(day + 1):
            rate = tree[day][j]
            x = day
            y = j - day/2
            
            is_most_probable = (j == most_probable_path[day])
            
            # Node
            fig.add_trace(
                go.Scatter(
                    x=[x],
                    y=[y],
                    mode='markers',
                    marker=dict(
                        size=20 if is_most_probable else 15,
                        color='#ff6b35' if is_most_probable else '#2e68a5',
                        line=dict(width=3 if is_most_probable else 2, color='white')
                    ),
                    showlegend=False,
                    hovertemplate=f"Dzień {day}<br>Kurs: {rate:.4f}<extra></extra>"
                )
            )
            
            # Label
            fig.add_trace(
                go.Scatter(
                    x=[x],
                    y=[y + 0.25],
                    mode='text',
                    text=f"{rate:.4f}",
                    textposition="middle center",
                    textfont=dict(
                        color='#ff6b35' if is_most_probable else '#2e68a5',
                        size=12 if is_most_probable else 10,
                        family="Arial Black" if is_most_probable else "Arial"
                    ),
                    showlegend=False,
                    hoverinfo='skip'
                )
            )
            
            # Connections
            if day < 5:
                # Up
                if j < day + 1:
                    next_y_up = (j + 1) - (day + 1)/2
                    is_prob_connection = (j == most_probable_path[day] and (j + 1) == most_probable_path[day + 1])
                    
                    fig.add_trace(
                        go.Scatter(
                            x=[x, x + 1],
                            y=[y, next_y_up],
                            mode='lines',
                            line=dict(
                                color='#ff6b35' if is_prob_connection else 'lightgray',
                                width=4 if is_prob_connection else 1
                            ),
                            showlegend=False,
                            hoverinfo='skip'
                        )
                    )
                
                # Down
                if j >= 0:
                    next_y_down = j - (day + 1)/2
                    is_prob_connection = (j == most_probable_path[day] and j == most_probable_path[day + 1])
                    
                    fig.add_trace(
                        go.Scatter(
                            x=[x, x + 1],
                            y=[y, next_y_down],
                            mode='lines',
                            line=dict(
                                color='#ff6b35' if is_prob_connection else 'lightgray',
                                width=4 if is_prob_connection else 1
                            ),
                            showlegend=False,
                            hoverinfo='skip'
                        )
                    )
    
    # Legend
    fig.add_trace(
        go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=20, color='#ff6b35'),
            name='🎯 Najczęstsza ścieżka',
            showlegend=True
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=15, color='#2e68a5'),
            name='Inne możliwe kursy',
            showlegend=True
        )
    )
    
    # Layout
    fig.update_layout(
        title="Drzewo dwumianowe EUR/PLN - 5 dni roboczych",
        xaxis_title="Dzień roboczy",
        yaxis_title="Poziom w drzewie",
        height=500,
        xaxis=dict(
            tickmode='array',
            tickvals=list(range(6)),
            ticktext=[f"Dzień {i}" if i == 0 else f"Dzień {i}\n{weekdays[i-1]}" for i in range(6)]
        ),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# MAIN APP
# ============================================================================

def main():
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
    
    st.markdown("*Alpha Vantage + NBP + FRED APIs | Synchronizacja dealerska ↔ klient*")
    
    # Sync status
    if st.session_state.dealer_pricing_data:
        config = st.session_state.dealer_config
        st.success(f"✅ System zsynchronizowany | Spot: {config['spot_rate']:.4f} | Window: {config['window_days']} dni")
    else:
        st.info("🔄 Oczekiwanie na wycenę dealerską...")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["🔧 Panel Dealerski", "🛡️ Panel Zabezpieczeń", "📊 Model Dwumianowy"])
    
    with tab1:
        create_dealer_panel()
    
    with tab2:
        create_client_hedging_advisor()
    
    with tab3:
        create_binomial_model_panel()

if __name__ == "__main__":
    main()
