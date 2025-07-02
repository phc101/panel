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
    .profit-metric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
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
        
        # Professional pricing parameters
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
# DORADCA ZABEZPIECZEŃ DLA KLIENTÓW
# ============================================================================

def create_client_hedging_advisor():
    """Doradca zabezpieczeń walutowych dla klientów"""
    
    st.header("🛡️ Doradca Zabezpieczeń EUR/PLN")
    st.markdown("*Chroń swój biznes przed ryzykiem walutowym dzięki profesjonalnym kontraktom terminowym*")
    
    # Load market data
    with st.spinner("📡 Ładowanie aktualnych kursów rynkowych..."):
        bond_data = get_fred_bond_data()
        forex_data = get_eur_pln_rate()
    
    # ============================================================================
    # MANUAL SPOT RATE CONTROL FOR CLIENT ADVISOR
    # ============================================================================
    st.subheader("⚙️ Konfiguracja Kursu")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        use_manual_spot_client = st.checkbox(
            "Ustaw kurs ręcznie", 
            value=False,
            key="client_manual_spot",
            help="Odznacz aby używać automatycznego kursu z NBP"
        )
    
    with col2:
        if use_manual_spot_client:
            spot_rate_client = st.number_input(
                "Kurs EUR/PLN:",
                value=forex_data['rate'],
                min_value=3.50,
                max_value=6.00,
                step=0.0001,
                format="%.4f",
                key="client_spot_input",
                help="Wprowadź własny kurs spot do wyceny"
            )
            spot_source_client = "Manual"
        else:
            spot_rate_client = forex_data['rate']
            spot_source_client = forex_data['source']
            st.info(f"Automatyczny kurs: {spot_rate_client:.4f} (źródło: {spot_source_client})")
    
    # Initialize calculator
    calculator = APIIntegratedForwardCalculator(FREDAPIClient())
    
    # Current market display
    st.subheader("📊 Aktualna Sytuacja Rynkowa")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "EUR/PLN Spot",
            f"{spot_rate_client:.4f}",
            help=f"Źródło: {spot_source_client}"
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
        forward_6m = calculator.calculate_theoretical_forward_points(spot_rate_client, pl_yield, de_yield, 180)
        direction = "silniejszy" if forward_6m['forward_rate'] > spot_rate_client else "słabszy"
        
        st.metric(
            "Prognoza 6M",
            f"PLN {direction}",
            delta=f"{((forward_6m['forward_rate']/spot_rate_client - 1) * 100):+.2f}%",
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
            min_value=10_000,
            max_value=50_000_000,
            step=10_000,
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
        spot_rate_client, pl_yield, de_yield, 0.002
    )
    
    # ============================================================================
    # TABELA KURSÓW TERMINOWYCH DLA KLIENTA
    # ============================================================================
    
    st.markdown("---")
    st.subheader("💱 Dostępne Kursy Terminowe")
    st.markdown("*Zablokuj te kursy dzisiaj na przyszłe sprzedaże EUR*")
    
    # Calculate client rates - SHOW ALL 12 FORWARDS
    client_rates_data = []
    
    for tenor_key, curve_data in forward_curve.items():
        tenor_points = curve_data["mid"]
        tenor_days = curve_data["days"]
        
        # Calculate client rate (simplified - no swap risk complexity for client view)
        client_swap_risk = calculator.calculate_swap_risk(tenor_days, tenor_points)
        client_rates = calculator.calculate_professional_rates(
            spot_rate_client, tenor_points, client_swap_risk, 0.0
        )
        
        client_rate = client_rates['fwd_client']
        
        # Calculate benefit vs spot
        rate_advantage = ((client_rate - spot_rate_client) / spot_rate_client) * 100
        
        # Determine recommendation
        if rate_advantage > 0.5:
            recommendation = "🟢 Doskonały"
        elif rate_advantage > 0.2:
            recommendation = "🟡 Dobry"
        elif rate_advantage > 0:
            recommendation = "🟠 Akceptowalny"
        else:
            recommendation = "🔴 Rozważ spot"
        
        # Calculate PLN amount client would receive
        pln_amount = client_rate * exposure_amount
        spot_pln_amount = spot_rate_client * exposure_amount
        additional_pln = pln_amount - spot_pln_amount
        
        client_rates_data.append({
            "Tenor": curve_data["name"],
            "Okno od": curve_data["okno_od"],
            "Rozliczenie do": curve_data["rozliczenie_do"],
            "Kurs terminowy": f"{client_rate:.4f}",
            "vs Spot": f"{rate_advantage:+.2f}%",
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
    
    # Simple chart
    st.markdown("---")
    st.subheader("📈 Porównanie Kursów")
    
    # Create simple comparison chart
    tenors_list = [data["Tenor"] for data in client_rates_data]
    forward_rates = [float(data["Kurs terminowy"]) for data in client_rates_data]
    
    fig = go.Figure()
    
    # Add spot rate line
    fig.add_trace(
        go.Scatter(
            x=tenors_list,
            y=[spot_rate_client] * len(tenors_list),
            mode='lines',
            name='Kurs spot',
            line=dict(color='red', width=3, dash='dash')
        )
    )
    
    # Add forward rates
    fig.add_trace(
        go.Scatter(
            x=tenors_list,
            y=forward_rates,
            mode='lines+markers',
            name='Kursy terminowe',
            line=dict(color='green', width=3),
            marker=dict(size=10, color='green')
        )
    )
    
    fig.update_layout(
        title="Kursy terminowe vs kurs spot",
        xaxis_title="Tenor",
        yaxis_title="Kurs EUR/PLN",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
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
                    st.write(f"Korzyść: **{row['vs Spot']}**")
    
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
        """, unsafe_allow_html=True)

# ============================================================================
# PEŁNY PANEL DEALERSKI Z KONTROLĄ NAD WYCENĄ
# ============================================================================

def create_dealer_panel():
    """Pełny panel dealerski z zaawansowaną kontrolą nad wyceną"""
    
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
    
    # Load market data
    with st.spinner("📡 Ładowanie danych rynkowych w czasie rzeczywistym..."):
        bond_data = get_fred_bond_data()
        forex_data = get_eur_pln_rate()
    
    # ============================================================================
    # MANUAL SPOT RATE CONTROL FOR DEALER PANEL
    # ============================================================================
    st.subheader("⚙️ Kontrola Kursu Spot")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        use_manual_spot = st.checkbox(
            "Ustaw kurs ręcznie", 
            value=False,
            key="dealer_manual_spot",
            help="Odznacz aby używać automatycznego kursu z NBP"
        )
    
    with col2:
        if use_manual_spot:
            spot_rate = st.number_input(
                "Kurs EUR/PLN:",
                value=forex_data['rate'],
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
    
    # Initialize calculator
    calculator = APIIntegratedForwardCalculator(FREDAPIClient())
    
    # ============================================================================
    # WYŚWIETLANIE DANYCH RYNKOWYCH
    # ============================================================================
    
    st.subheader("📊 Dane Rynkowe na Żywo")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "EUR/PLN Spot",
            f"{spot_rate:.4f}",
            help=f"Źródło: {spot_source} | Aktualizacja: {forex_data['date']}"
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
    
    # ZAAWANSOWANE PARAMETRY WYCENY
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
        
        # Dodatkowe parametry
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
        
        with col5:
            volatility_factor = st.slider(
                "Współczynnik zmienności:",
                min_value=0.15,
                max_value=0.35,
                value=0.25,
                step=0.01,
                help="Wpływ zmienności na ryzyko swap"
            )
        
        with col6:
            hedging_savings_pct = st.slider(
                "Oszczędności hedging (%):",
                min_value=0.40,
                max_value=0.80,
                value=0.60,
                step=0.05,
                help="% oszczędności swap risk w najlepszym scenariuszu"
            )
    
    # Update calculator parameters
    calculator.points_factor = points_factor
    calculator.risk_factor = risk_factor
    
    # ============================================================================
    # PORTFOLIO WINDOW FORWARD CALCULATIONS (ALL 12 TENORS)
    # ============================================================================
    
    st.markdown("---")
    st.subheader("🔢 Portfolio Window Forward Generation")
    st.markdown(f"*Wszystkie 12 tenorów z {window_days}-dniową elastycznością okna*")
    
    # Generate forward curve from API data
    forward_curve = calculator.generate_api_forward_points_curve(
        spot_rate, pl_yield, de_yield, bid_ask_spread
    )
    
    # Generate window forward pricing for ALL 12 tenors
    portfolio_totals = {
        'total_points_to_window': 0,
        'total_swap_risk': 0,
        'total_min_profit': 0,
        'total_max_profit': 0,
        'total_expected_profit': 0,
        'total_client_premium': 0,
        'total_notional': 0
    }
    
    complete_pricing_data = []
    
    for tenor_key, curve_data in forward_curve.items():
        tenor_days = curve_data["days"]
        tenor_points = curve_data["mid"]
        
        # Calculate window-specific swap risk with custom volatility factor
        tenor_window_swap_risk = abs(tenor_points) * volatility_factor * np.sqrt(window_days / 90)
        tenor_window_swap_risk = max(tenor_window_swap_risk, 0.015)  # minimum risk floor
        
        # Calculate professional window forward rates
        tenor_rates = calculator.calculate_professional_rates(
            spot_rate, tenor_points, tenor_window_swap_risk, minimum_profit_floor
        )
        
        # Calculate window forward metrics using BANK SPREAD LOGIC:
        window_min_profit_per_eur = tenor_rates['fwd_to_open'] - tenor_rates['fwd_client']  # Bank spread
        window_max_profit_per_eur = window_min_profit_per_eur + (tenor_window_swap_risk * hedging_savings_pct)  # + hedging savings
        window_expected_profit_per_eur = (window_min_profit_per_eur + window_max_profit_per_eur) / 2
        
        window_min_profit_total = window_min_profit_per_eur * nominal_amount
        window_max_profit_total = window_max_profit_per_eur * nominal_amount
        window_expected_profit_total = window_expected_profit_per_eur * nominal_amount
        
        # Add to portfolio totals
        portfolio_totals['total_points_to_window'] += tenor_points * nominal_amount
        portfolio_totals['total_swap_risk'] += tenor_window_swap_risk * nominal_amount
        portfolio_totals['total_min_profit'] += window_min_profit_total
        portfolio_totals['total_max_profit'] += window_max_profit_total
        portfolio_totals['total_expected_profit'] += window_expected_profit_total
        portfolio_totals['total_client_premium'] += (tenor_rates['fwd_client'] - spot_rate) * nominal_amount
        portfolio_totals['total_notional'] += nominal_amount
        
        complete_pricing_data.append({
            "Tenor": curve_data["name"],
            "Forward Days": tenor_days,
            "Window Days": window_days,
            "Okno od": curve_data["okno_od"],
            "Rozliczenie do": curve_data["rozliczenie_do"],
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
            "Yield Spread": f"{curve_data['yield_spread']:.2f}pp"
        })
    
    df_complete_pricing = pd.DataFrame(complete_pricing_data)
    
    # Highlight the selected window length in the table
    def highlight_selected_window_portfolio(row):
        if abs(row['Forward Days'] - window_days) <= 15:
            return ['background-color: #e8f5e8; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    # Display the complete window forward portfolio table
    st.dataframe(
        df_complete_pricing.style.apply(highlight_selected_window_portfolio, axis=1),
        use_container_width=True,
        height=400
    )
    
    # ============================================================================
    # ENHANCED PORTFOLIO SUMMARY WITH PERCENTAGE METRICS
    # ============================================================================
    
    st.markdown("---")
    st.subheader("💼 Podsumowanie Portfolio")
    
    # Calculate percentage metrics relative to spot
    total_exposure_pln = spot_rate * portfolio_totals['total_notional']
    min_profit_pct = (portfolio_totals['total_min_profit'] / total_exposure_pln) * 100
    expected_profit_pct = (portfolio_totals['total_expected_profit'] / total_exposure_pln) * 100
    max_profit_pct = (portfolio_totals['total_max_profit'] / total_exposure_pln) * 100
    
    # Portfolio summary metrics - First row with PLN amounts
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
    
    # Second row with percentage metrics
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
    
    st.markdown("*Zaawansowane wyceny kontraktów terminowych i rozwiązania zabezpieczeniowe*")
    
    # Create tabs
    tab1, tab2 = st.tabs(["🔧 Panel Dealerski", "🛡️ Doradca Zabezpieczeń"])
    
    with tab1:
        create_dealer_panel()
    
    with tab2:
        create_client_hedging_advisor()

# ============================================================================
# URUCHOMIENIE APLIKACJI
# ============================================================================

if __name__ == "__main__":
    main()
