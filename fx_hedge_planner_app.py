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
# SUPPORT FUNCTIONS
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
# PANEL DEALERSKI Z KONTROLĄ NAD WYCENĄ
# ============================================================================

def create_dealer_panel():
    """Panel dealerski - ustala wycenę dla całego systemu"""
    
    st.header("🚀 Panel Dealerski - Wycena Master")
    st.markdown("*Ustaw parametry wyceny - te kursy będą widoczne w panelu zabezpieczeń*")
    
    # Alpha Vantage API Status Display
    st.subheader("📡 Status API")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Test Alpha Vantage API
        alpha_api = AlphaVantageAPI()
        forex_result = alpha_api.get_eur_pln_rate()
        
        if 'Alpha Vantage' in forex_result['source']:
            st.markdown(f"""
            <div class="alpha-api">
                <h4 style="margin: 0;">📈 Alpha Vantage API Active</h4>
                <p style="margin: 0;">Source: {forex_result['source']}</p>
                <p style="margin: 0;">Rate: {forex_result['rate']:.4f} | Date: {forex_result['date']}</p>
                <p style="margin: 0;">Real-time professional data</p>
            </div>
            """, unsafe_allow_html=True)
        
        # ============================================================================
        # CHART COMPARISON - PIĘKNY NIEBIESKI WYKRES
        # ============================================================================
        
        st.markdown("---")
        st.subheader("📈 Porównanie Wizualne")
        
        # Create comparison chart
        tenors_list = [data["Tenor"] for data in client_rates_data]
        forward_rates = [float(data["Kurs terminowy"]) for data in client_rates_data]
        spot_rates = [config['spot_rate']] * len(tenors_list)
        
        fig = go.Figure()
        
        # Add spot rate line
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
        
        # Add forward rates - PIĘKNY NIEBIESKI
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
        
        # Calculate and add benefit bars
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
        
        # ============================================================================
        # REKOMENDACJE
        # ============================================================================
        
        st.markdown("---")
        st.subheader("🎯 Rekomendacje Zabezpieczeń")
        
        # Filter best recommendations
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
            st.info("💡 W obecnych warunkach rynkowych rozważ pozostanie na kursie spot lub poczekaj na lepsze warunki.")
        elif 'NBP' in forex_result['source']:
            st.markdown(f"""
            <div class="alpha-api" style="background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%); color: #2d3436;">
                <h4 style="margin: 0;">🏛️ NBP API Backup</h4>
                <p style="margin: 0;">Source: {forex_result['source']}</p>
                <p style="margin: 0;">Rate: {forex_result['rate']:.4f}</p>
                <p style="margin: 0;">Official Polish central bank</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="alpha-api" style="background: linear-gradient(135deg, #e17055 0%, #d63031 100%);">
                <h4 style="margin: 0;">⚠️ Fallback Mode</h4>
                <p style="margin: 0;">Source: {forex_result['source']}</p>
                <p style="margin: 0;">Rate: {forex_result['rate']:.4f}</p>
                <p style="margin: 0;">Check API connectivity</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # Show historical data status
        historical_data = get_historical_eur_pln_data(30)
        
        st.markdown(f"""
        <div class="alpha-api">
            <h4 style="margin: 0;">📊 Historical Data</h4>
            <p style="margin: 0;">Source: {historical_data['source']}</p>
            <p style="margin: 0;">Data points: {historical_data['count']}</p>
            <p style="margin: 0;">For volatility calculation</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Load market data
    with st.spinner("📡 Ładowanie danych rynkowych..."):
        bond_data = get_fred_bond_data()
        forex_data = get_eur_pln_rate()
    
    # Manual spot rate control
    st.subheader("⚙️ Kontrola Kursu Spot")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        use_manual_spot = st.checkbox(
            "Ustaw kurs ręcznie", 
            value=False,
            key="dealer_manual_spot",
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
                format="%.4f",
                key="dealer_spot_input",
                help="Wprowadź własny kurs spot do wyceny"
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
        st.metric(
            "EUR/PLN Spot",
            f"{spot_rate:.4f}",
            help=f"Źródło: {spot_source}"
        )
    
    with col2:
        st.metric(
            "Rentowność PL 10Y",
            f"{pl_yield:.2f}%",
            help=f"Źródło: {bond_data.get('Poland_10Y', {}).get('source', 'Current Market')}"
        )
    
    with col3:
        st.metric(
            "Rentowność DE 10Y",
            f"{de_yield:.2f}%", 
            help=f"Źródło: {bond_data.get('Germany_10Y', {}).get('source', 'Current Market')}"
        )
    
    with col4:
        st.metric(
            "Spread PL-DE 10Y",
            f"{spread:.2f}pp",
            help="Różnica rentowności 10Y napędzająca punkty terminowe"
        )
    
    # Transaction configuration
    st.markdown("---")
    st.subheader("⚙️ Konfiguracja Transakcji")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        window_days = st.number_input(
            "Długość okna (dni):",
            value=st.session_state.dealer_config['window_days'],
            min_value=30,
            max_value=365,
            step=5,
            help="Długość okresu window forward"
        )
    
    with col2:
        nominal_amount = st.number_input(
            "Kwota nominalna (EUR):",
            value=2_500_000,
            min_value=10_000,
            max_value=100_000_000,
            step=10_000,
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
    
    # Advanced pricing parameters
    with st.expander("🔧 Zaawansowane Parametry Wyceny"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            points_factor = st.slider(
                "Współczynnik punktów (% dla klienta):",
                min_value=0.60,
                max_value=0.85,
                value=st.session_state.dealer_config['points_factor'],
                step=0.01,
                help="Procent punktów terminowych przekazywanych klientowi"
            )
        
        with col2:
            risk_factor = st.slider(
                "Współczynnik ryzyka (% obciążenia):",
                min_value=0.30,
                max_value=0.60,
                value=st.session_state.dealer_config['risk_factor'],
                step=0.01,
                help="Procent ryzyka swap obciążanego klientowi"
            )
        
        with col3:
            bid_ask_spread = st.number_input(
                "Spread bid-ask:",
                value=st.session_state.dealer_config['bid_ask_spread'],
                min_value=0.001,
                max_value=0.005,
                step=0.0005,
                format="%.4f",
                help="Rynkowy spread bid-ask w punktach terminowych"
            )
        
        col4, col5, col6 = st.columns(3)
        
        with col4:
            minimum_profit_floor = st.number_input(
                "Min próg zysku (PLN/EUR):",
                value=st.session_state.dealer_config['minimum_profit_floor'],
                min_value=-0.020,
                max_value=0.020,
                step=0.001,
                format="%.4f",
                help="Minimalny gwarantowany zysk na EUR"
            )
        
        with col5:
            volatility_factor = st.slider(
                "Współczynnik zmienności:",
                min_value=0.15,
                max_value=0.35,
                value=st.session_state.dealer_config['volatility_factor'],
                step=0.01,
                help="Wpływ zmienności na ryzyko swap"
            )
        
        with col6:
            hedging_savings_pct = st.slider(
                "Oszczędności hedging (%):",
                min_value=0.40,
                max_value=0.80,
                value=st.session_state.dealer_config['hedging_savings_pct'],
                step=0.05,
                help="% oszczędności swap risk w najlepszym scenariuszu"
            )
    
    # Update pricing button
    if st.button("🔄 Zaktualizuj Wycenę", type="primary", use_container_width=True):
        update_dealer_config(
            spot_rate, spot_source, pl_yield, de_yield, window_days,
            points_factor, risk_factor, bid_ask_spread, volatility_factor,
            hedging_savings_pct, minimum_profit_floor
        )
        st.success("✅ Wycena zaktualizowana! Przejdź do panelu zabezpieczeń aby zobaczyć kursy klienta.")
        st.rerun()
    
    # Show current pricing if available
    if st.session_state.dealer_pricing_data:
        st.markdown("---")
        st.subheader("💼 Aktualna Wycena Dealerska")
        
        # Create DataFrame for display
        pricing_df_data = []
        
        for pricing in st.session_state.dealer_pricing_data:
            pricing_df_data.append({
                "Tenor": pricing['tenor_name'],
                "Forward Days": pricing['tenor_days'],
                "Window Days": window_days,
                "Forward Points": f"{pricing['forward_points']:.4f}",
                "Swap Risk": f"{pricing['swap_risk']:.4f}",
                "Client Rate": f"{pricing['client_rate']:.4f}",
                "Theoretical Rate": f"{pricing['theoretical_rate']:.4f}",
                "Profit/EUR": f"{pricing['profit_per_eur']:.4f}",
                "Profit Total": f"{pricing['profit_per_eur'] * nominal_amount:,.0f} PLN"
            })
        
        df_pricing = pd.DataFrame(pricing_df_data)
        st.dataframe(df_pricing, use_container_width=True, height=400)
    
    else:
        st.info("👆 Kliknij 'Zaktualizuj Wycenę' aby wygenerować kursy dla klientów")

# ============================================================================
# PANEL ZABEZPIECZEŃ - SYNCHRONIZOWANY Z WYCENĘ DEALERSKĄ
# ============================================================================

def create_client_hedging_advisor():
    """Panel zabezpieczeń - pokazuje kursy z panelu dealerskiego"""
    
    st.header("🛡️ Panel Zabezpieczeń EUR/PLN")
    st.markdown("*Kursy synchronizowane z panelem dealerskim*")
    
    # Check if dealer pricing is available
    if not st.session_state.dealer_pricing_data:
        st.warning("⚠️ Brak wyceny dealerskiej! Przejdź najpierw do panelu dealerskiego i zaktualizuj wycenę.")
        
        # Show fallback basic info
        forex_data = get_eur_pln_rate()
        st.info(f"Aktualny kurs EUR/PLN: {forex_data['rate']:.4f} ({forex_data['source']})")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div class="metric-card" style="text-align: center;">
                <h4>🚀 Rozpocznij Wycenę</h4>
                <p>Przejdź do panelu dealerskiego aby:</p>
                <ul style="text-align: left; margin: 1rem 0;">
                    <li>Ustawić parametry rynkowe</li>
                    <li>Skonfigurować marże i ryzyka</li>
                    <li>Wygenerować kursy dla klientów</li>
                </ul>
                <p><strong>Po aktualizacji wyceny kursy pojawią się tutaj automatycznie!</strong></p>
            </div>
            """, unsafe_allow_html=True)
        
        return
    
    # Show pricing sync status
    config = st.session_state.dealer_config
    
    st.markdown(f"""
    <div class="pricing-sync">
        <h4 style="margin: 0;">✅ Wycena Zsynchronizowana</h4>
        <p style="margin: 0;">Kurs spot: {config['spot_rate']:.4f} | Window: {config['window_days']} dni | Ostatnia aktualizacja: {datetime.now().strftime('%H:%M:%S')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Client configuration
    st.subheader("⚙️ Parametry Zabezpieczenia")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        exposure_amount = st.number_input(
            "Kwota EUR do zabezpieczenia:",
            value=1_000_000,
            min_value=10_000,
            max_value=50_000_000,
            step=10_000,
            format="%d",
            help="Kwota ekspozycji EUR do zabezpieczenia"
        )
    
    with col2:
        show_details = st.checkbox(
            "Pokaż szczegóły transakcji",
            value=False,
            help="Wyświetl dodatkowe informacje o okresach rozliczenia"
        )
    
    with col3:
        st.info(f"💼 Okno elastyczności: **{config['window_days']} dni**\n\n(zgodne z wyceną dealerską)")
    
    # All pricing data
    filtered_pricing = st.session_state.dealer_pricing_data
    
    st.markdown("---")
    st.subheader("💱 Dostępne Kursy Terminowe")
    st.markdown("*Kursy gotowe do zawarcia transakcji*")
    
    # Calculate client summary metrics
    client_rates_data = []
    
    for pricing in filtered_pricing:
        client_rate = pricing['client_rate']
        spot_rate = config['spot_rate']
        
        # Calculate benefits vs spot
        rate_advantage = ((client_rate - spot_rate) / spot_rate) * 100
        
        # Calculate PLN amounts
        pln_amount_forward = client_rate * exposure_amount
        pln_amount_spot = spot_rate * exposure_amount
        additional_pln = pln_amount_forward - pln_amount_spot
        
        # Determine recommendation
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
                "Rozliczenie do": pricing['rozliczenie_do'],
                "Spread vs Teor.": f"{(pricing['theoretical_rate'] - client_rate):.4f}"
            })
        
        client_rates_data.append(row_data)
    
    # Create and display DataFrame
    if client_rates_data:
        df_client_rates = pd.DataFrame(client_rates_data)
        
        # Style the table
        def highlight_recommendations(row):
            color = row.get('rec_color', '#ffffff')
            return [f'background-color: {color}'] * len(row)
        
        # Remove color column before display
        display_df = df_client_rates.drop('rec_color', axis=1, errors='ignore')
        
        # Apply styling
        styled_df = display_df.style.apply(highlight_recommendations, axis=1)
        
        st.markdown('<div class="compact-table">', unsafe_allow_html=True)
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=min(350, len(client_rates_data) * 28 + 80),
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Summary metrics
        st.markdown("---")
        st.subheader("📊 Podsumowanie Strategii")
        
        num_forwards = len(client_rates_data)
        avg_client_rate = sum(float(data["Kurs terminowy"]) for data in client_rates_data) / num_forwards
        avg_benefit_pct = sum(float(data["vs Spot"].rstrip('%')) for data in client_rates_data) / num_forwards
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="client-summary">
                <h4 style="margin: 0; color: #2e68a5;">Średni Kurs Zabezpieczenia</h4>
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
    
    else:
        st.warning("Brak dostępnych opcji dla wybranego okresu zabezpieczenia.")
    
    # Call to action
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="text-align: center;">
            <h4>💼 Gotowy do zabezpieczenia {exposure_amount:,} EUR?</h4>
            <p>Skontaktuj się z dealerami FX aby sfinalizować transakcję</p>
            <p><strong>📞 +48 22 XXX XXXX | 📧 fx.trading@bank.pl</strong></p>
            <p style="font-size: 0.9em; color: #666;">Kursy ważne przez 15 minut od wygenerowania wyceny</p>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# MODEL DWUMIANOWY Z ALPHA VANTAGE
# ============================================================================

def create_binomial_model_panel():
    """5-DAY BINOMIAL TREE MODEL with Alpha Vantage data"""
    st.header("📊 Drzewo Dwumianowe - 5 Dni")
    st.markdown("*Krótkoterminowa prognoza EUR/PLN z Alpha Vantage + NBP data*")
    
    # Get historical data for volatility calculation using Alpha Vantage
    with st.spinner("📡 Pobieranie danych historycznych z Alpha Vantage..."):
        historical_data = get_historical_eur_pln_data(30)
        current_forex = get_eur_pln_rate()
    
    # Display data source info
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="alpha-api">
            <h4 style="margin: 0;">📈 Kurs Bieżący</h4>
            <p style="margin: 0;">Source: {current_forex['source']}</p>
            <p style="margin: 0;">Rate: {current_forex['rate']:.4f}</p>
            <p style="margin: 0;">Date: {current_forex['date']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="alpha-api">
            <h4 style="margin: 0;">📊 Dane Historyczne</h4>
            <p style="margin: 0;">Source: {historical_data['source']}</p>
            <p style="margin: 0;">Points: {historical_data['count']}</p>
            <p style="margin: 0;">For volatility calculation</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Calculate volatility and mean from historical data
    try:
        if historical_data['success'] and len(historical_data['rates']) >= 20:
            rates = historical_data['rates']
            
            # Take exactly last 20 rates for calculation
            last_20_rates = rates[-20:] if len(rates) >= 20 else rates
            current_spot = last_20_rates[-1]  # Most recent rate
            
            # Calculate mean and std dev from last 20 days
            mean_20_days = np.mean(last_20_rates)
            std_20_days = np.std(last_20_rates)
            
            # Calculate empirical probabilities using normal distribution
            from scipy.stats import norm
            
            # P(up) = probability of being above current level based on historical distribution
            p_up_empirical = 1 - norm.cdf(current_spot, mean_20_days, std_20_days)
            p_down_empirical = 1 - p_up_empirical
            
            # For display, also calculate simple volatility
            rolling_vol = std_20_days / current_spot
            
            data_count = len(last_20_rates)
            
            if rolling_vol > 0:
                st.success(f"✅ Empirical Model z ostatnich {data_count} dni:")
                st.info(f"Mean: {mean_20_days:.4f}, Std: {std_20_days:.4f}, Current: {current_spot:.4f}")
                st.info(f"Empirical P(up): {p_up_empirical:.3f}, P(down): {p_down_empirical:.3f}")
                st.info(f"Implied volatility: {rolling_vol*100:.2f}% dzienna")
            else:
                raise Exception("Zero volatility calculated")
        else:
            raise Exception("Insufficient historical data (need 20 days)")
            
    except Exception as e:
        # Default values
        rolling_vol = 0.0034  # 0.34% daily
        current_spot = current_forex['rate']
        mean_20_days = current_spot  # Assume mean = current
        std_20_days = current_spot * 0.0034  # Default std
        p_up_empirical = 0.5  # Default 50/50
        p_down_empirical = 0.5
        st.warning(f"⚠️ Używam domyślnych wartości. Błąd: {str(e)[:50]}...")
    
    # Model parameters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        spot_rate = st.number_input(
            "Kurs spot EUR/PLN:",
            value=current_spot,
            min_value=3.50,
            max_value=6.00,
            step=0.0001,
            format="%.4f"
        )
    
    with col2:
        st.metric("Horyzont", "5 dni roboczych", help="Poniedziałek - Piątek, pomijający weekendy")
        days = 5  # Only business days
    
    with col3:
        # Allow user to override empirical probabilities
        use_empirical = st.checkbox(
            "Użyj empirycznych prawdopodobieństw",
            value=True,
            help="Użyj prawdopodobieństw z rozkładu normalnego ostatnich 20 dni"
        )
        
        if use_empirical:
            p_up_display = p_up_empirical
            p_down_display = p_down_empirical
            st.success(f"Empirical: P(up)={p_up_display:.3f}")
        else:
            # Traditional binomial approach
            daily_vol = st.slider(
                "Zmienność dzienna (%):",
                min_value=0.1,
                max_value=2.0,
                value=rolling_vol*100,
                step=0.05,
                help="Tradycyjna zmienność binomialna"
            ) / 100
            
            # Traditional binomial parameters
            dt = 1/252
            u = np.exp(daily_vol * np.sqrt(dt))
            d = 1/u
            r = 0.02/252
            p_up_display = (np.exp(r * dt) - d) / (u - d)
            p_down_display = 1 - p_up_display
            
            st.info(f"Traditional: P(up)={p_up_display:.3f}")
    
    # Use empirical probabilities for tree calculation
    if use_empirical:
        p = p_up_empirical
        u = 1 + rolling_vol  # Simple approximation
        d = 1 - rolling_vol
    else:
        # Traditional approach
        dt = 1/252
        u = np.exp(daily_vol * np.sqrt(dt))
        d = 1/u
        r = 0.02/252
        p = (np.exp(r * dt) - d) / (u - d)
    
    # Create 5-day business tree
    tree = {}
    
    # Generate all possible paths for 5 business days
    for day in range(6):  # Day 0 to 5
        tree[day] = {}
        
        if day == 0:
            tree[day][0] = spot_rate
        else:
            for j in range(day + 1):
                ups = j
                downs = day - j
                rate = spot_rate * (u ** ups) * (d ** downs)
                tree[day][j] = rate
    
    # Calculate most probable path
    most_probable_path = []
    for day in range(6):
        if day == 0:
            most_probable_path.append(0)
        else:
            # Find the node closest to expected value
            expected_ups = day * p  # Expected number of up moves
            closest_j = round(expected_ups)
            closest_j = max(0, min(closest_j, day))  # Ensure valid range
            most_probable_path.append(closest_j)
    
    # Show final prediction
    st.subheader("🎯 Prognoza Finalna")
    
    final_day = days
    final_j = most_probable_path[final_day]
    final_predicted_rate = tree[final_day][final_j]
    change_pct = ((final_predicted_rate - spot_rate) / spot_rate) * 100
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Prognoza (5 dni)",
            f"{final_predicted_rate:.4f}",
            delta=f"{change_pct:+.2f}%"
        )
    
    with col2:
        from math import comb
        if use_empirical:
            prob = comb(final_day, final_j) * (p_up_empirical ** final_j) * (p_down_empirical ** (final_day - final_j))
        else:
            prob = comb(final_day, final_j) * (p ** final_j) * ((1 - p) ** (final_day - final_j))
        
        st.metric(
            "Prawdopodobieństwo",
            f"{prob*100:.1f}%",
            help="Prawdopodobieństwo tej konkretnej ścieżki"
        )
    
    with col3:
        final_rates = [tree[5][j] for j in range(6)]
        min_rate = min(final_rates)
        max_rate = max(final_rates)
        st.metric(
            "Zakres (min-max)",
            f"{min_rate:.4f} - {max_rate:.4f}",
            help="Możliwe ekstremalne scenariusze"
        )

# ============================================================================
# GŁÓWNA APLIKACJA
# ============================================================================

def main():
    """Główny punkt wejścia aplikacji"""
    
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
    
    st.markdown("*Alpha Vantage + NBP + FRED APIs | Synchronizacja dealerska ↔ klient*")
    
    # Show sync status in header
    if st.session_state.dealer_pricing_data:
        config = st.session_state.dealer_config
        st.success(f"✅ System zsynchronizowany | Spot: {config['spot_rate']:.4f} | Window: {config['window_days']} dni | Kursy: {len(st.session_state.dealer_pricing_data)} tenorów")
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

# ============================================================================
# URUCHOMIENIE APLIKACJI
# ============================================================================

if __name__ == "__main__":
    main()
