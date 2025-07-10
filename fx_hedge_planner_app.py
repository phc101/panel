import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import math

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
    
    # Client config
    st.subheader("⚙️ Parametry Zabezpieczenia")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        exposure_amount = st.number_input(
            "Kwota EUR:",
            value=1_000_000,
            min_value=10_000,
            max_value=50_000_000,
            step=10_000,
            format="%d"
        )
    
    with col2:
        show_details = st.checkbox("Pokaż szczegóły", value=False)
    
    with col3:
        st.info(f"💼 Okno: **{config['window_days']} dni**")
    
    st.markdown("---")
    st.subheader("💱 Dostępne Kursy Terminowe")
    
    # Process rates
    client_rates_data = []
    
    for pricing in st.session_state.dealer_pricing_data:
        client_rate = pricing['client_rate']
        spot_rate = config['spot_rate']
        rate_advantage = ((client_rate - spot_rate) / spot_rate) * 100
        
        pln_amount_forward = client_rate * exposure_amount
        pln_amount_spot = spot_rate * exposure_amount
        additional_pln = pln_amount_forward - pln_amount_spot
        
        if rate_advantage > 0.5:
            recommendation = "🟢 Doskonały"
            rec_color = "#d4edda"
        elif rate_advantage > 0.2:
            recommendation = "🟡 Dobry"
            rec_color = "#fff3cd"
        elif rate_advantage > 0:
            recommendation = "🟠 Akceptowalny"
            rec_color = "#ffeaa7"
        else:
            recommendation = "🔴 Rozważ spot"
            rec_color = "#f8d7da"
        
        row_data = {
            "Tenor": pricing['tenor_name'],
            "Kurs terminowy": f"{client_rate:.4f}",
            "vs Spot": f"{rate_advantage:+.2f}%",
            "Kwota PLN": f"{pln_amount_forward:,.0f}",
            "Dodatkowy PLN": f"{additional_pln:+,.0f}" if additional_pln != 0 else "0",
            "Rekomendacja": recommendation,
            "rec_color": rec_color
        }
        
        if show_details:
            row_data.update({
                "Okno od": pricing['okno_od'],
                "Rozliczenie do": pricing['rozliczenie_do']
            })
        
        client_rates_data.append(row_data)
    
    # Display table
    if client_rates_data:
        df_client_rates = pd.DataFrame(client_rates_data)
        
        def highlight_recommendations(row):
            color = row.get('rec_color', '#ffffff')
            return [f'background-color: {color}'] * len(row)
        
        display_df = df_client_rates.drop('rec_color', axis=1, errors='ignore')
        styled_df = display_df.style.apply(highlight_recommendations, axis=1)
        
        st.dataframe(styled_df, use_container_width=True, height=350, hide_index=True)
        
        # Summary
        st.markdown("---")
        st.subheader("📊 Podsumowanie Strategii")
        
        num_forwards = len(client_rates_data)
        avg_client_rate = sum(float(data["Kurs terminowy"]) for data in client_rates_data) / num_forwards
        avg_benefit_pct = sum(float(data["vs Spot"].rstrip('%')) for data in client_rates_data) / num_forwards
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="client-summary">
                <h4 style="margin: 0; color: #2e68a5;">Średni Kurs</h4>
                <h2 style="margin: 0; color: #2c3e50;">{avg_client_rate:.4f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="client-summary">
                <h4 style="margin: 0; color: #2e68a5;">Średnia Korzyść</h4>
                <h2 style="margin: 0; color: #2c3e50;">{avg_benefit_pct:+.2f}%</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            total_additional_pln = sum(float(data["Dodatkowy PLN"].replace(',', '').replace('+', '')) for data in client_rates_data if data["Dodatkowy PLN"] != "0")
            st.markdown(f"""
            <div class="client-summary">
                <h4 style="margin: 0; color: #2e68a5;">Łączna Korzyść</h4>
                <h2 style="margin: 0; color: #2c3e50;">{total_additional_pln:+,.0f} PLN</h2>
            </div>
            """, unsafe_allow_html=True)
        
        # PIĘKNY NIEBIESKI WYKRES
        st.markdown("---")
        st.subheader("📈 Porównanie Wizualne")
        
        tenors_list = [data["Tenor"] for data in client_rates_data]
        forward_rates = [float(data["Kurs terminowy"]) for data in client_rates_data]
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
        
        # Forward rates - PIĘKNY NIEBIESKI
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
        
        # Benefits bars
        benefits = [(float(data["Kurs terminowy"]) - config['spot_rate']) * exposure_amount for data in client_rates_data]
        
        fig.add_trace(
            go.Bar(
                x=tenors_list,
                y=benefits,
                name='Korzyść PLN vs Spot',
                yaxis='y2',
                marker_color='lightblue',
                opacity=0.7,
                hovertemplate='%{x}: %{y:,.0f} PLN<extra></extra>'
            )
        )
        
        fig.update_layout(
            title="Kursy terminowe vs kurs spot + korzyść w PLN",
            xaxis_title="Tenor",
            yaxis_title="Kurs EUR/PLN",
            yaxis2=dict(
                title="Korzyść (PLN)",
                overlaying='y',
                side='right',
                showgrid=False
            ),
            height=500,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Wyjaśnienie metody najczęstszej ścieżki
    st.subheader("🧮 Metodologia Najczęstszej Ścieżki")
    
    st.markdown("""
    **Jak znajduję najczęstszą ścieżkę:**
    
    1. **Dla każdego dnia** obliczam prawdopodobieństwo osiągnięcia każdego możliwego węzła
    2. **Formuła:** `P(j ruchów w górę w n dniach) = C(n,j) × p^j × (1-p)^(n-j)`
    3. **Wybieram węzeł** o najwyższym prawdopodobieństwie w danym dniu
    4. **Ścieżka łączy** kolejne najczęstsze węzły dzień po dniu
    
    ⚠️ **Uwaga:** To nie jest ścieżka o najwyższym prawdopodobieństwie end-to-end, 
    ale ścieżka przechodząca przez najczęstsze węzły w każdym dniu.
    """)
    
    # Tabela prawdopodobieństw dla pierwszych 3 dni
    if st.checkbox("Pokaż szczegóły prawdopodobieństw", value=False):
        prob_data = []
        
        for day in range(1, 4):  # Dni 1, 2, 3
            for j in range(day + 1):
                from math import comb
                if use_empirical:
                    node_prob = comb(day, j) * (p_up_empirical ** j) * (p_down_empirical ** (day - j))
                else:
                    node_prob = comb(day, j) * (p ** j) * ((1 - p) ** (day - j))
                
                is_selected = (j == most_probable_path[day])
                
                prob_data.append({
                    "Dzień": day,
                    "Ruchy w górę (j)": j,
                    "Ruchy w dół": day - j,
                    "C(n,j)": comb(day, j),
                    "Prawdopodobieństwo": f"{node_prob:.4f}",
                    "Najczęstszy?": "🎯 TAK" if is_selected else "❌ Nie"
                })
        
        df_prob = pd.DataFrame(prob_data)
        st.dataframe(df_prob, use_container_width=True, hide_index=True)
        
        # Top recommendations
        st.markdown("---")
        st.subheader("🎯 Rekomendacje Zabezpieczeń")
        
        best_rates = [rate for rate in client_rates_data if '🟢' in rate['Rekomendacja'] or '🟡' in rate['Rekomendacja']]
        best_rates = sorted(best_rates, key=lambda x: float(x['vs Spot'].rstrip('%')), reverse=True)[:3]
        
        if best_rates:
            st.markdown("**📋 Top 3 rekomendacje:**")
            
            for i, rate in enumerate(best_rates, 1):
                col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
                
                with col1:
                    st.write(f"**#{i}** {rate['Rekomendacja']}")
                
                with col2:
                    st.write(f"**{rate['Tenor']}** - kurs {rate['Kurs terminowy']}")
                
                with col3:
                    st.write(f"Korzyść: **{rate['vs Spot']}**")
                
                with col4:
                    st.write(f"**{rate['Dodatkowy PLN']} PLN**")
        else:
            st.info("💡 Rozważ pozostanie na kursie spot.")
    
    # ============================================================================
    # PLANOWANIE HEDGINGU
    # ============================================================================
    
    st.markdown("---")
    st.subheader("📅 Planowanie Strategii Hedgingu")
    
    # Hedge planner configuration
    col1, col2, col3 = st.columns(3)
    
    with col1:
        hedge_horizon = st.selectbox(
            "Horyzont planowania:",
            options=[3, 6, 12, 18, 24],
            index=2,
            help="Okres w miesiącach dla planowania hedgingu"
        )
    
    with col2:
        hedge_coverage = st.slider(
            "Docelowe pokrycie ekspozycji:",
            min_value=25,
            max_value=100,
            value=75,
            step=5,
            help="Procent ekspozycji do zabezpieczenia"
        ) / 100
    
    with col3:
        risk_tolerance = st.selectbox(
            "Tolerancja ryzyka:",
            options=["Konserwatywna", "Umiarkowana", "Agresywna"],
            index=1,
            help="Profil ryzyka dla strategii hedgingu"
        )
    
    # Calculate hedge plan
    target_hedge_amount = exposure_amount * hedge_coverage
    
    # Risk parameters based on tolerance
    risk_params = {
        "Konserwatywna": {"max_single_trade": 0.15, "prefer_short_tenors": True, "volatility_buffer": 1.5},
        "Umiarkowana": {"max_single_trade": 0.25, "prefer_short_tenors": False, "volatility_buffer": 1.2},
        "Agresywna": {"max_single_trade": 0.40, "prefer_short_tenors": False, "volatility_buffer": 1.0}
    }
    
    current_risk = risk_params[risk_tolerance]
    max_single_trade = target_hedge_amount * current_risk["max_single_trade"]
    
    # Generate hedge plan
    hedge_plan = []
    remaining_amount = target_hedge_amount
    
    # Filter tenors based on horizon and risk tolerance
    available_tenors = [p for p in st.session_state.dealer_pricing_data if p['tenor_months'] <= hedge_horizon]
    
    if current_risk["prefer_short_tenors"]:
        available_tenors = sorted(available_tenors, key=lambda x: x['tenor_months'])
    else:
        # Mix of short and medium tenors
        available_tenors = sorted(available_tenors, key=lambda x: abs(x['tenor_months'] - hedge_horizon/2))
    
    month_counter = 0
    while remaining_amount > 100_000 and available_tenors and month_counter < hedge_horizon:
        
        # Select tenor based on strategy
        if month_counter < len(available_tenors):
            selected_tenor = available_tenors[month_counter % len(available_tenors)]
        else:
            selected_tenor = available_tenors[0]
        
        # Calculate trade size
        trade_size = min(remaining_amount, max_single_trade)
        trade_size = max(trade_size, 100_000)  # Minimum trade size
        
        # Calculate dates
        start_date = datetime.now() + timedelta(days=30 * month_counter)
        execution_window_start = start_date + timedelta(days=selected_tenor['tenor_months'] * 30)
        execution_window_end = execution_window_start + timedelta(days=config['window_days'])
        
        hedge_plan.append({
            "Miesiąc": month_counter + 1,
            "Data rozpoczęcia": start_date.strftime("%d.%m.%Y"),
            "Tenor": selected_tenor['tenor_name'],
            "Kwota EUR": f"{trade_size:,.0f}",
            "Kurs": f"{selected_tenor['client_rate']:.4f}",
            "Okno wykonania": f"{execution_window_start.strftime('%d.%m')} - {execution_window_end.strftime('%d.%m.%Y')}",
            "Korzyść vs Spot": f"{((selected_tenor['client_rate'] - config['spot_rate']) / config['spot_rate'] * 100):+.2f}%",
            "Profit PLN": f"{(selected_tenor['client_rate'] - config['spot_rate']) * trade_size:+,.0f}"
        })
        
        remaining_amount -= trade_size
        month_counter += 1
        
        if month_counter >= 8:  # Safety break
            break
    
    # Display hedge plan
    if hedge_plan:
        st.markdown("### 📋 Proponowany Plan Hedgingu")
        
        df_hedge_plan = pd.DataFrame(hedge_plan)
        
        # Color coding for hedge plan
        def highlight_hedge_plan(row):
            profit_str = row['Profit PLN'].replace(',', '').replace('+', '').replace(' PLN', '')
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
            df_hedge_plan.style.apply(highlight_hedge_plan, axis=1),
            use_container_width=True,
            hide_index=True
        )
        
        # Plan summary
        st.markdown("### 📊 Podsumowanie Planu Hedgingu")
        
        total_planned = sum(float(row['Kwota EUR'].replace(',', '')) for row in hedge_plan)
        total_profit = sum(float(row['Profit PLN'].replace(',', '').replace('+', '').replace(' PLN', '')) for row in hedge_plan)
        coverage_achieved = total_planned / exposure_amount * 100
        avg_rate = sum(float(row['Kurs']) * float(row['Kwota EUR'].replace(',', '')) for row in hedge_plan) / total_planned
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Pokrycie Ekspozycji",
                f"{coverage_achieved:.1f}%",
                delta=f"{coverage_achieved - hedge_coverage*100:+.1f}pp vs docelowe",
                help="Procent ekspozycji zabezpieczony przez plan"
            )
        
        with col2:
            st.metric(
                "Łączna Kwota",
                f"€{total_planned:,.0f}",
                help="Suma wszystkich transakcji w planie"
            )
        
        with col3:
            st.metric(
                "Średni Kurs Hedgingu",
                f"{avg_rate:.4f}",
                delta=f"{((avg_rate - config['spot_rate']) / config['spot_rate'] * 100):+.2f}% vs spot",
                help="Średnia ważona kursów w planie"
            )
        
        with col4:
            st.metric(
                "Łączny Profit",
                f"{total_profit:+,.0f} PLN",
                help="Suma korzyści vs pozostanie na spot"
            )
        
        # Risk analysis
        st.markdown("### ⚖️ Analiza Ryzyka Planu")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h4>🎯 Charakterystyka Strategii</h4>
                <p><strong>Profil ryzyka:</strong> {risk_tolerance}</p>
                <p><strong>Max transakcja:</strong> €{max_single_trade:,.0f} ({current_risk['max_single_trade']:.0%} ekspozycji)</p>
                <p><strong>Liczba transakcji:</strong> {len(hedge_plan)}</p>
                <p><strong>Horyzont:</strong> {hedge_horizon} miesięcy</p>
                <p><strong>Średni tenor:</strong> {sum(p['tenor_months'] for p in available_tenors[:len(hedge_plan)]) / len(hedge_plan):.1f} miesięcy</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Calculate risk metrics
            plan_rates = [float(row['Kurs']) for row in hedge_plan]
            rate_volatility = np.std(plan_rates) if len(plan_rates) > 1 else 0
            
            # Exposure timeline
            months_covered = len(hedge_plan)
            timeline_risk = "Niskie" if months_covered >= 6 else "Średnie" if months_covered >= 3 else "Wysokie"
            
            st.markdown(f"""
            <div class="metric-card">
                <h4>📈 Metryki Ryzyka</h4>
                <p><strong>Zmienność kursów:</strong> {rate_volatility:.4f}</p>
                <p><strong>Ryzyko timeline:</strong> {timeline_risk}</p>
                <p><strong>Koncentracja:</strong> {'Rozproszona' if len(hedge_plan) >= 4 else 'Skoncentrowana'}</p>
                <p><strong>Bufor zmienności:</strong> {current_risk['volatility_buffer']}x</p>
                <p><strong>Elastyczność:</strong> {config['window_days']} dni na transakcję</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Execution calendar
        st.markdown("### 📅 Kalendarz Wykonania")
        
        # Create execution timeline
        execution_data = []
        for i, trade in enumerate(hedge_plan):
            execution_data.append({
                "Okres": f"M{trade['Miesiąc']}",
                "Data": trade['Data rozpoczęcia'],
                "Akcja": f"Hedge €{trade['Kwota EUR']} na {trade['Tenor']}",
                "Okno": trade['Okno wykonania'],
                "Status": "🟡 Planowana" if i < 3 else "🔵 Przyszła",
                "Priorytet": "🔴 Wysoki" if i < 2 else "🟡 Średni" if i < 4 else "🟢 Niski"
            })
        
        df_execution = pd.DataFrame(execution_data)
        st.dataframe(df_execution, use_container_width=True, hide_index=True)
        
        # Action items
        st.markdown("### ✅ Następne Kroki")
        
        next_actions = [
            "📞 **Natychmiastowe:** Skontaktuj się z dealerem FX w celu potwierdzenia dostępności kursów",
            "📋 **Do końca tygodnia:** Przygotuj dokumentację do pierwszych 2-3 transakcji",
            "📊 **Monitoring:** Ustaw alerty na kursy EUR/PLN dla timing wykonania",
            "🔄 **Miesięczny przegląd:** Ocena skuteczności i ewentualne korekty planu",
            f"⏰ **Pierwsza transakcja:** {hedge_plan[0]['Data rozpoczęcia']} - {hedge_plan[0]['Kwota EUR']} na tenor {hedge_plan[0]['Tenor']}"
        ]
        
        for action in next_actions:
            st.markdown(f"- {action}")
    
    else:
        st.warning("⚠️ Nie można wygenerować planu hedgingu z obecnymi parametrami.")

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
            
            from scipy.stats import norm
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
    
    # Most probable path - PRAWDZIWA NAJCZĘSTSZA ŚCIEŻKA
    most_probable_path = []
    for day in range(6):
        if day == 0:
            most_probable_path.append(0)
        else:
            # Znajdź węzeł o najwyższym prawdopodobieństwie w tym dniu
            best_j = 0
            best_prob = 0
            
            for j in range(day + 1):  # j może być od 0 do day
                # Prawdopodobieństwo osiągnięcia węzła (j, day)
                from math import comb
                if use_empirical:
                    node_prob = comb(day, j) * (p_up_empirical ** j) * (p_down_empirical ** (day - j))
                else:
                    node_prob = comb(day, j) * (p ** j) * ((1 - p) ** (day - j))
                
                if node_prob > best_prob:
                    best_prob = node_prob
                    best_j = j
            
            most_probable_path.append(best_j)
            
            # Debug info dla pierwszych 3 dni
            if day <= 3:
                st.write(f"Dzień {day}: najwyższe P = {best_prob:.4f} dla j={best_j} ({best_j} ruchów w górę, {day-best_j} w dół)")
    
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
        from math import comb
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
    
    # DRZEWO DWUMIANOWE WIZUALIZACJA
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
