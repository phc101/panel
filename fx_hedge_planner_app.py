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

class APIIntegratedForwardCalculator:
    def __init__(self, fred_client):
        self.fred_client = fred_client
        self.points_factor = 0.70
        self.risk_factor = 0.40
    
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
    
    def calculate_professional_rates(self, spot_rate, points_to_window, swap_risk, min_profit_floor=0.0):
        points_given_to_client = points_to_window * self.points_factor
        swap_risk_charged = swap_risk * self.risk_factor
        
        fwd_client_initial = spot_rate + points_given_to_client - swap_risk_charged
        fwd_to_open = spot_rate + points_to_window
        
        initial_profit = fwd_to_open - fwd_client_initial
        
        if initial_profit < min_profit_floor:
            fwd_client = fwd_to_open - min_profit_floor
            profit_per_eur = min_profit_floor
        else:
            fwd_client = fwd_client_initial
            profit_per_eur = initial_profit
        
        return {
            'fwd_client': fwd_client,
            'fwd_to_open': fwd_to_open,
            'profit_per_eur': profit_per_eur,
            'points_given_to_client': points_given_to_client,
            'swap_risk_charged': swap_risk_charged
        }

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

@st.cache_data(ttl=3600)
def get_fred_bond_data():
    fred_client = FREDAPIClient()
    try:
        bond_series = {
            'Poland_10Y': 'IRLTLT01PLM156N',
            'Germany_10Y': 'IRLTLT01DEM156N'
        }
        
        results = {}
        for name, series_id in bond_series.items():
            data = fred_client.get_series_data(series_id)
            if data:
                results[name] = data
        
        if results:
            return results
        else:
            raise Exception("No data from FRED API")
    except Exception as e:
        return {
            'Poland_10Y': {'value': 5.42, 'date': '2025-07-03', 'source': 'Current Market'},
            'Germany_10Y': {'value': 2.63, 'date': '2025-07-03', 'source': 'Current Market'}
        }

@st.cache_data(ttl=300)
def get_eur_pln_rate():
    alpha_api = AlphaVantageAPI()
    return alpha_api.get_eur_pln_rate()

def create_dealer_panel():
    st.header("🚀 Panel Dealerski - Wycena Master")
    st.markdown("*Ustaw parametry wyceny - te kursy będą widoczne w panelu zabezpieczeń*")
    
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
            minimum_profit_floor = st.number_input(
                "Min próg zysku (PLN/EUR):",
                value=st.session_state.dealer_config['minimum_profit_floor'],
                min_value=-0.020,
                max_value=0.020,
                step=0.001,
                format="%.4f"
            )
    
    # Update button
    if st.button("🔄 Zaktualizuj Wycenę", type="primary", use_container_width=True):
        # Update config
        st.session_state.dealer_config.update({
            'spot_rate': spot_rate,
            'spot_source': spot_source,
            'pl_yield': pl_yield,
            'de_yield': de_yield,
            'window_days': window_days,
            'points_factor': points_factor,
            'risk_factor': risk_factor,
            'minimum_profit_floor': minimum_profit_floor
        })
        
        # Generate pricing data
        pricing_data = []
        calculator = APIIntegratedForwardCalculator(FREDAPIClient())
        calculator.points_factor = points_factor
        calculator.risk_factor = risk_factor
        
        for i in range(1, 13):
            days = i * 30
            theoretical = calculator.calculate_theoretical_forward_points(spot_rate, pl_yield, de_yield, days)
            forward_points = theoretical['forward_points']
            
            swap_risk = abs(forward_points) * 0.25 * np.sqrt(window_days / 90)
            swap_risk = max(swap_risk, 0.015)
            
            rates = calculator.calculate_professional_rates(spot_rate, forward_points, swap_risk, minimum_profit_floor)
            
            pricing_data.append({
                'tenor_name': f"{i} {'miesiąc' if i == 1 else 'miesiące' if i <= 4 else 'miesięcy'}",
                'tenor_days': days,
                'forward_points': forward_points,
                'swap_risk': swap_risk,
                'client_rate': rates['fwd_client'],
                'profit_per_eur': rates['profit_per_eur']
            })
        
        st.session_state.dealer_pricing_data = pricing_data
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
                "Profit/EUR": f"{pricing['profit_per_eur']:.4f}"
            })
        
        df_pricing = pd.DataFrame(pricing_df_data)
        st.dataframe(df_pricing, use_container_width=True, height=400)
        
        # Portfolio summary metrics
        st.subheader("📊 Podsumowanie Portfolio")
        
        # Calculate portfolio totals
        portfolio_totals = {
            'total_min_profit': 0,
            'total_max_profit': 0,
            'total_expected_profit': 0,
            'total_notional': 0
        }
        
        hedging_savings_pct = st.session_state.dealer_config['hedging_savings_pct']
        
        for pricing in st.session_state.dealer_pricing_data:
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
        
        total_exposure_pln = spot_rate * portfolio_totals['total_notional']
        min_profit_pct = (portfolio_totals['total_min_profit'] / total_exposure_pln) * 100
        expected_profit_pct = (portfolio_totals['total_expected_profit'] / total_exposure_pln) * 100
        max_profit_pct = (portfolio_totals['total_max_profit'] / total_exposure_pln) * 100
        
        # Portfolio metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Portfolio Min Zysk", 
                f"{portfolio_totals['total_min_profit']:,.0f} PLN"
            )
        
        with col2:
            st.metric(
                "Portfolio Oczekiwany", 
                f"{portfolio_totals['total_expected_profit']:,.0f} PLN"
            )
        
        with col3:
            st.metric(
                "Portfolio Max Zysk", 
                f"{portfolio_totals['total_max_profit']:,.0f} PLN"
            )
        
        with col4:
            st.metric(
                "Zakres Zysku", 
                f"{portfolio_totals['total_max_profit'] - portfolio_totals['total_min_profit']:,.0f} PLN"
            )
        
        # Percentage metrics
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
    
    st.markdown("---")
    st.subheader("💱 Nowa Transakcja Forward Elastyczny")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        st.markdown("**SPRZEDAJ**")
        sell_currency = st.selectbox("", ["EUR"], key="sell_curr")
    
    with col2:
        st.markdown("**KUP**")
        buy_currency = st.selectbox("", ["PLN"], key="buy_curr")
    
    with col3:
        st.markdown("**CAŁKOWITY WOLUMEN**")
        volume = st.number_input(
            "",
            value=1_000_000,
            min_value=10_000,
            max_value=50_000_000,
            step=10_000,
            format="%d"
        )
    
    st.markdown("### 📅 Wybór Terminów Wykonania")
    
    col1, col2 = st.columns(2)
    
    with col1:
        settlement_date = st.date_input(
            "**Data pierwszego wykonania:**",
            value=(datetime.now() + timedelta(days=90)).date(),
            min_value=datetime.now().date(),
            max_value=(datetime.now() + timedelta(days=730)).date()
        )
    
    with col2:
        window_days = st.number_input(
            "**Długość okna (dni):**",
            value=config['window_days'],
            min_value=30,
            max_value=365,
            step=5
        )
    
    settlement_datetime = datetime.combine(settlement_date, datetime.min.time())
    today_datetime = datetime.now()
    days_to_settlement = (settlement_datetime - today_datetime).days
    
    calculator = APIIntegratedForwardCalculator(FREDAPIClient())
    theoretical = calculator.calculate_theoretical_forward_points(
        config['spot_rate'], 
        config['pl_yield'], 
        config['de_yield'], 
        days_to_settlement
    )
    
    forward_points = theoretical['forward_points']
    tenor_window_swap_risk = abs(forward_points) * 0.25 * np.sqrt(window_days / 90)
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
    
    st.markdown("---")
    if st.button("➕ Dodaj elastyczny kontrakt forwardowy", type="primary", use_container_width=True):
        execution_window_start = settlement_datetime
        execution_window_end = execution_window_start + timedelta(days=window_days)
        
        # Skip weekends for expiration date - if Saturday (5) or Sunday (6), move to Monday
        while execution_window_end.weekday() >= 5:  # 5=Saturday, 6=Sunday
            execution_window_end += timedelta(days=1)
        
        months_approx = days_to_settlement / 30
        if months_approx < 1:
            tenor_name = f"{days_to_settlement} dni"
        else:
            tenor_name = f"{months_approx:.0f}M+"
        
        # Calculate percentage result vs spot
        pct_vs_spot = ((client_rate - config['spot_rate']) / config['spot_rate']) * 100
        
        transaction_id = len(st.session_state.hedge_transactions) + 1
        st.session_state.hedge_transactions.append({
            "nr": transaction_id,
            "typ": "Forward elastyczny",
            "pierwsze_wykonanie": settlement_date.strftime("%d %b %Y"),
            "data_wygasniecia": execution_window_end.strftime("%d %b %Y"),
            "kwota_sprzedazy": f"(EUR) {volume:,.0f}",
            "kwota_zakupu": f"(PLN) {pln_amount:,.0f}",
            "kurs_zabezpieczenia": f"{client_rate:.4f}",
            "pct_vs_spot": f"{pct_vs_spot:+.2f}%",
            "wycena_do_rynku": f"{advantage_pln:+,.0f} PLN" if advantage_pln != 0 else "0,00 PLN",
            "status": "PLANOWANE"
        })
        st.success(f"✅ Dodano kontrakt Forward Elastyczny na {volume:,.0f} EUR")
        st.rerun()
    
    if st.session_state.hedge_transactions:
        st.markdown("---")
        st.markdown("## Lista transakcji")
        
        transactions_data = []
        
        for i, transaction in enumerate(st.session_state.hedge_transactions, 1):
            transactions_data.append({
                "#": i,
                "TYP": transaction.get('typ', 'Forward elastyczny'),
                "PIERWSZE WYKONANIE": transaction.get('pierwsze_wykonanie', 'Brak daty'),
                "DATA WYGAŚNIĘCIA": transaction.get('data_wygasniecia', 'Brak daty'),
                "KWOTA SPRZEDAŻY": transaction.get('kwota_sprzedazy', '(EUR) 0'),
                "KWOTA ZAKUPU": transaction.get('kwota_zakupu', '(PLN) 0'),
                "KURS ZABEZPIECZENIA": transaction.get('kurs_zabezpieczenia', '0.0000'),
                "WYCENA DO RYNKU": transaction.get('wycena_do_rynku', '0 PLN'),
                "STATUS": transaction.get('status', 'PLANOWANE')
            })
        
        if transactions_data:
            df_transactions = pd.DataFrame(transactions_data)
            st.dataframe(df_transactions, use_container_width=True, height=400, hide_index=True)
            
            # Portfolio summary for client
            st.markdown("### 📊 Podsumowanie Zabezpieczeń")
            
            # Calculate totals
            total_volume_eur = 0
            total_volume_pln = 0
            weighted_rate_sum = 0
            
            for transaction in st.session_state.hedge_transactions:
                try:
                    # Extract EUR volume
                    eur_str = str(transaction.get('kwota_sprzedazy', '0')).replace('(EUR) ', '').replace(',', '')
                    if eur_str and eur_str != 'nan':
                        eur_amount = float(eur_str)
                        total_volume_eur += eur_amount
                        
                        # Extract rate for weighted average
                        rate_str = str(transaction.get('kurs_zabezpieczenia', '0'))
                        if rate_str and rate_str != 'nan':
                            rate = float(rate_str)
                            weighted_rate_sum += rate * eur_amount
                    
                    # Extract PLN volume
                    pln_str = str(transaction.get('kwota_zakupu', '0')).replace('(PLN) ', '').replace(',', '')
                    if pln_str and pln_str != 'nan':
                        total_volume_pln += float(pln_str)
                except (ValueError, TypeError):
                    pass
            
            # Calculate weighted average rate
            avg_hedging_rate = weighted_rate_sum / total_volume_eur if total_volume_eur > 0 else 0
            
            # Display summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="client-summary">
                    <h4 style="margin: 0; color: #2e68a5;">Suma Zabezpieczenia</h4>
                    <h2 style="margin: 0; color: #2c3e50;">€{total_volume_eur:,.0f}</h2>
                    <p style="margin: 0; color: #666;">Łączny wolumen</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="client-summary">
                    <h4 style="margin: 0; color: #2e68a5;">Średni Ważony Kurs</h4>
                    <h2 style="margin: 0; color: #2c3e50;">{avg_hedging_rate:.4f}</h2>
                    <p style="margin: 0; color: #666;">Kurs zabezpieczenia</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="client-summary">
                    <h4 style="margin: 0; color: #2e68a5;">Łączna Kwota PLN</h4>
                    <h2 style="margin: 0; color: #2c3e50;">{total_volume_pln:,.0f}</h2>
                    <p style="margin: 0; color: #666;">Do otrzymania</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                # Calculate advantage vs spot
                spot_rate = config['spot_rate']
                if avg_hedging_rate > 0:
                    advantage_pct = ((avg_hedging_rate - spot_rate) / spot_rate) * 100
                    advantage_pln = (avg_hedging_rate - spot_rate) * total_volume_eur
                    color = "#28a745" if advantage_pct > 0 else "#dc3545"
                else:
                    advantage_pct = 0
                    advantage_pln = 0
                    color = "#666"
                
                st.markdown(f"""
                <div class="client-summary">
                    <h4 style="margin: 0; color: #2e68a5;">Korzyść vs Spot</h4>
                    <h2 style="margin: 0; color: {color};">{advantage_pct:+.2f}%</h2>
                    <p style="margin: 0; color: #666;">{advantage_pln:+,.0f} PLN</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("📋 Brak kontraktów. Dodaj pierwszy kontrakt Forward Elastyczny.")

def create_binomial_model_panel():
    st.header("📊 Drzewo Dwumianowe - 5 Dni")
    st.markdown("*Krótkoterminowa prognoza EUR/PLN*")
    
    with st.spinner("📡 Pobieranie danych..."):
        current_forex = get_eur_pln_rate()
    
    st.markdown(f"""
    <div class="alpha-api">
        <h4 style="margin: 0;">📈 Kurs Bieżący</h4>
        <p style="margin: 0;">Rate: {current_forex['rate']:.4f}</p>
        <p style="margin: 0;">Source: {current_forex['source']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        spot_rate = st.number_input(
            "Kurs spot:",
            value=current_forex['rate'],
            min_value=3.50,
            max_value=6.00,
            step=0.0001,
            format="%.4f"
        )
    
    with col2:
        st.metric("Horyzont", "5 dni roboczych")
        days = 5
    
    with col3:
        daily_vol = st.slider("Zmienność (%):", 0.1, 2.0, 0.34, 0.05) / 100
    
    # Build binomial tree
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
                node_prob = comb(day, j) * (p ** j) * ((1 - p) ** (day - j))
                
                if node_prob > best_prob:
                    best_prob = node_prob
                    best_j = j
            
            most_probable_path.append(best_j)
    
    st.subheader("🎯 Prognoza Finalna")
    
    final_day = days
    final_j = most_probable_path[final_day]
    final_predicted_rate = tree[final_day][final_j]
    change_pct = ((final_predicted_rate - spot_rate) / spot_rate) * 100
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Prognoza (5 dni)", f"{final_predicted_rate:.4f}", delta=f"{change_pct:+.2f}%")
    
    with col2:
        prob = comb(final_day, final_j) * (p ** final_j) * ((1 - p) ** (final_day - final_j))
        st.metric("Prawdopodobieństwo", f"{prob*100:.1f}%")
    
    with col3:
        final_rates = [tree[5][j] for j in range(6)]
        min_rate = min(final_rates)
        max_rate = max(final_rates)
        st.metric("Zakres", f"{min_rate:.4f} - {max_rate:.4f}")
    
    st.subheader("🌳 Drzewo Dwumianowe")
    
    fig = go.Figure()
    
    weekdays = ["Pon", "Wt", "Śr", "Czw", "Pt"]
    
    for day in range(6):
        for j in range(day + 1):
            rate = tree[day][j]
            x = day
            y = j - day/2
            
            is_most_probable = (j == most_probable_path[day])
            
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
            
            if day < 5:
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

def main():
    initialize_session_state()
    
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 2rem;">
        <div style="background: linear-gradient(45deg, #667eea, #764ba2); width: 60px; height: 60px; border-radius: 10px; margin-right: 1rem; display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 2rem;">🚀</span>
        </div>
        <h1 style="margin: 0; color: #2c3e50;">Zintegrowana Platforma FX</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("*Alpha Vantage + NBP + FRED APIs | Synchronizacja dealerska ↔ klient*")
    
    if st.session_state.dealer_pricing_data:
        config = st.session_state.dealer_config
        st.success(f"✅ System zsynchronizowany | Spot: {config['spot_rate']:.4f} | Window: {config['window_days']} dni")
    else:
        st.info("🔄 Oczekiwanie na wycenę dealerską...")
    
    tab1, tab2, tab3 = st.tabs(["🔧 Panel Dealerski", "🛡️ Panel Zabezpieczeń", "📊 Model Dwumianowy"])
    
    with tab1:
        create_dealer_panel()
    
    with tab2:
        create_client_hedging_advisor()
    
    with tab3:
        create_binomial_model_panel()

if __name__ == "__main__":
    main()
