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
            y=[spot_rate] * len(tenors_list),
            mode='lines',
            name='Kurs dzisiejszy',
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
        title="Kursy terminowe vs kurs dzisiejszy",
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
        """, unsafe_allow_html=True)

# ============================================================================
# PANEL DEALERSKI (UPROSZCZONY)
# ============================================================================

def create_dealer_panel():
    """Panel dealerski z podstawowymi funkcjami"""
    
    st.header("🚀 Panel Dealerski Window Forward")
    st.markdown("*Profesjonalne wyceny kontraktów terminowych*")
    
    # Load market data
    with st.spinner("📡 Ładowanie danych rynkowych..."):
        bond_data = get_fred_bond_data()
        forex_data = get_eur_pln_rate()
    
    # Initialize calculator
    calculator = APIIntegratedForwardCalculator(FREDAPIClient())
    
    # Market data display
    st.subheader("📊 Dane Rynkowe")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        spot_rate = forex_data['rate']
        st.metric("EUR/PLN Spot", f"{spot_rate:.4f}")
    
    with col2:
        pl_yield = bond_data['Poland_10Y']['value'] if 'Poland_10Y' in bond_data else 5.70
        st.metric("Rentowność PL 10Y", f"{pl_yield:.2f}%")
    
    with col3:
        de_yield = bond_data['Germany_9M']['value'] if 'Germany_9M' in bond_data else 2.35
        st.metric("Rentowność DE", f"{de_yield:.2f}%")
    
    with col4:
        spread = pl_yield - de_yield
        st.metric("Spread PL-DE", f"{spread:.2f}pp")
    
    # Configuration
    st.markdown("---")
    st.subheader("⚙️ Parametry")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        window_days = st.number_input("Długość okna (dni):", value=90, min_value=30, max_value=365, step=5)
    
    with col2:
        nominal_amount = st.number_input("Kwota (EUR):", value=2_500_000, min_value=100_000, step=100_000, format="%d")
    
    with col3:
        points_factor = st.slider("Points Factor:", 0.60, 0.85, 0.70, 0.01)
    
    # Generate forward curve
    forward_curve = calculator.generate_api_forward_points_curve(spot_rate, pl_yield, de_yield, 0.002)
    
    # Portfolio table
    st.markdown("---")
    st.subheader("📋 Portfolio Window Forward")
    
    portfolio_data = []
    for tenor_key, curve_data in forward_curve.items():
        tenor_points = curve_data["mid"]
        tenor_window_swap_risk = calculator.calculate_swap_risk(window_days, tenor_points)
        tenor_rates = calculator.calculate_professional_rates(spot_rate, tenor_points, tenor_window_swap_risk, 0.0)
        
        # Calculate min/max profits using bank spread logic
        window_min_profit_per_eur = tenor_rates['fwd_to_open'] - tenor_rates['fwd_client']
        window_max_profit_per_eur = window_min_profit_per_eur + (tenor_window_swap_risk * 0.6)
        
        portfolio_data.append({
            "Tenor": curve_data["name"],
            "Okno od": curve_data["okno_od"],
            "Rozliczenie do": curve_data["rozliczenie_do"],
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
