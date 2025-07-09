import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import math

# ============================================================================
# CONFIGURATION & API KEYS
# ============================================================================

# Alpha Vantage API Configuration
ALPHA_VANTAGE_API_KEY = "MQGKUNL9JWIJHF9S"

# Page config
st.set_page_config(
    page_title="FX Trading Platform",
    page_icon="💱",
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
    .dealer-panel {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
    }
    .client-panel {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
    }
    .prediction-panel {
        background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
        color: #2c3e50;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
        border: 2px solid #e91e63;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# ALPHA VANTAGE API CLIENT
# ============================================================================

class AlphaVantageAPI:
    """Alpha Vantage API client for forex data"""
    
    def __init__(self, api_key=ALPHA_VANTAGE_API_KEY):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
    
    def get_eur_pln_rate(self):
        """Get current EUR/PLN exchange rate"""
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
    
    def _get_nbp_fallback(self):
        """Fallback to NBP API"""
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

# ============================================================================
# BINOMIAL MODEL FOR EUR/PLN PREDICTION
# ============================================================================

class EURPLNBinomialModel:
    """Binomial model specifically for EUR/PLN 5-day prediction"""
    
    def __init__(self, alpha_api):
        self.alpha_api = alpha_api
        
    def predict_5_day_scenarios(self, current_rate, volatility=0.12, risk_free_rate=0.055):
        """Generate 5-day EUR/PLN prediction scenarios using binomial model"""
        
        # Model parameters
        T = 5/365  # 5 days in years
        n = 5      # 5 steps (1 per day)
        dt = T / n
        
        # Binomial parameters
        u = np.exp(volatility * np.sqrt(dt))  # Up factor
        d = 1 / u  # Down factor
        p = (np.exp(risk_free_rate * dt) - d) / (u - d)  # Risk-neutral probability
        
        # Generate all possible paths
        scenarios = []
        
        for day in range(1, 6):  # Days 1-5
            # Calculate possible rates for this day
            day_scenarios = []
            
            for up_moves in range(day + 1):
                down_moves = day - up_moves
                rate = current_rate * (u ** up_moves) * (d ** down_moves)
                
                # Calculate probability of this path
                probability = math.comb(day, up_moves) * (p ** up_moves) * ((1-p) ** down_moves)
                
                day_scenarios.append({
                    'rate': rate,
                    'probability': probability,
                    'change_pct': ((rate - current_rate) / current_rate) * 100
                })
            
            # Sort by probability and take top scenarios
            day_scenarios.sort(key=lambda x: x['probability'], reverse=True)
            
            scenarios.append({
                'day': day,
                'date': (datetime.now() + timedelta(days=day)).strftime('%Y-%m-%d'),
                'scenarios': day_scenarios[:3],  # Top 3 scenarios
                'expected_rate': sum(s['rate'] * s['probability'] for s in day_scenarios),
                'volatility_range': {
                    'high': max(s['rate'] for s in day_scenarios),
                    'low': min(s['rate'] for s in day_scenarios)
                }
            })
        
        return {
            'current_rate': current_rate,
            'model_params': {
                'volatility': volatility,
                'risk_free_rate': risk_free_rate,
                'up_factor': u,
                'down_factor': d,
                'risk_neutral_prob': p
            },
            'predictions': scenarios
        }

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def initialize_session_state():
    """Initialize session state"""
    if 'current_rate_data' not in st.session_state:
        st.session_state.current_rate_data = None
    if 'dealer_rates' not in st.session_state:
        st.session_state.dealer_rates = None
    if 'prediction_results' not in st.session_state:
        st.session_state.prediction_results = None

# ============================================================================
# DEALER PANEL
# ============================================================================

def create_dealer_panel():
    """Simple dealer panel for EUR/PLN pricing"""
    
    st.header("🏦 Panel Dealerski")
    
    # Get current market rate
    alpha_api = AlphaVantageAPI()
    
    with st.spinner("📡 Pobieranie kursu EUR/PLN..."):
        rate_data = alpha_api.get_eur_pln_rate()
        st.session_state.current_rate_data = rate_data
    
    # Display current rate
    st.markdown(f"""
    <div class="dealer-panel">
        <h3>💱 Aktualny Kurs EUR/PLN</h3>
        <h2>{rate_data['rate']:.4f}</h2>
        <p>Źródło: {rate_data['source']} | Data: {rate_data['date']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Dealer configuration
    st.subheader("⚙️ Konfiguracja Dealerska")
    
    col1, col2 = st.columns(2)
    
    with col1:
        spread = st.slider(
            "Spread (pips):",
            min_value=10,
            max_value=100,
            value=30,
            step=5,
            help="Spread dealerski w pipsach"
        )
        
        margin = st.slider(
            "Marża (%):",
            min_value=0.1,
            max_value=2.0,
            value=0.5,
            step=0.1,
            help="Marża dealerska w procentach"
        )
    
    with col2:
        risk_adjustment = st.slider(
            "Korekta Ryzyka:",
            min_value=-0.02,
            max_value=0.02,
            value=0.005,
            step=0.001,
            format="%.3f",
            help="Korekta na ryzyko rynkowe"
        )
        
        min_amount = st.number_input(
            "Min. kwota (EUR):",
            value=10000,
            min_value=1000,
            max_value=1000000,
            step=1000,
            help="Minimalna kwota transakcji"
        )
    
    # Calculate dealer rates
    if st.button("🔄 Oblicz Kursy Dealerskie", type="primary"):
        spot_rate = rate_data['rate']
        spread_value = spread / 10000  # Convert pips to rate
        margin_value = spot_rate * (margin / 100)
        
        buy_rate = spot_rate - spread_value/2 - margin_value + risk_adjustment
        sell_rate = spot_rate + spread_value/2 + margin_value + risk_adjustment
        
        dealer_rates = {
            'spot': spot_rate,
            'buy': buy_rate,
            'sell': sell_rate,
            'spread_pips': spread,
            'margin_pct': margin,
            'risk_adj': risk_adjustment,
            'min_amount': min_amount
        }
        
        st.session_state.dealer_rates = dealer_rates
        st.success("✅ Kursy dealerskie obliczone!")
    
    # Display dealer rates
    if st.session_state.dealer_rates:
        rates = st.session_state.dealer_rates
        
        st.subheader("💰 Kursy Dealerskie")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Kurs Kupna EUR",
                f"{rates['buy']:.4f}",
                help="Kurs po którym dealer kupuje EUR"
            )
        
        with col2:
            st.metric(
                "Kurs Sprzedaży EUR", 
                f"{rates['sell']:.4f}",
                help="Kurs po którym dealer sprzedaje EUR"
            )
        
        with col3:
            profit_per_eur = rates['sell'] - rates['buy']
            st.metric(
                "Zysk na EUR",
                f"{profit_per_eur:.4f} PLN",
                help="Zysk dealera na 1 EUR"
            )

# ============================================================================
# CLIENT PANEL
# ============================================================================

def create_client_panel():
    """Simple client advisory panel"""
    
    st.header("🤝 Panel Kliencki")
    
    if not st.session_state.current_rate_data:
        st.warning("⚠️ Najpierw załaduj dane w Panelu Dealerskim!")
        return
    
    if not st.session_state.dealer_rates:
        st.warning("⚠️ Najpierw oblicz kursy w Panelu Dealerskim!")
        return
    
    rate_data = st.session_state.current_rate_data
    dealer_rates = st.session_state.dealer_rates
    
    st.markdown(f"""
    <div class="client-panel">
        <h3>💼 Doradztwo Klienckie EUR/PLN</h3>
        <p>Aktualne kursy i rekomendacje dla klientów</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Client transaction setup
    st.subheader("⚙️ Parametry Transakcji")
    
    col1, col2 = st.columns(2)
    
    with col1:
        transaction_type = st.selectbox(
            "Typ Transakcji:",
            ["Kupno EUR", "Sprzedaż EUR"],
            help="Wybierz typ transakcji"
        )
        
        amount_eur = st.number_input(
            "Kwota EUR:",
            value=100000,
            min_value=dealer_rates['min_amount'],
            max_value=10000000,
            step=1000,
            help="Kwota w EUR"
        )
    
    with col2:
        client_type = st.selectbox(
            "Typ Klienta:",
            ["Standard", "Premium", "VIP"],
            help="Kategoria klienta"
        )
        
        # Client discount based on type
        discount_map = {"Standard": 0.0, "Premium": 0.0001, "VIP": 0.0002}
        client_discount = discount_map[client_type]
    
    # Calculate client rates
    if transaction_type == "Kupno EUR":
        base_rate = dealer_rates['sell']
        client_rate = base_rate - client_discount
        pln_amount = client_rate * amount_eur
        direction = "Klient kupuje EUR, płaci PLN"
    else:
        base_rate = dealer_rates['buy'] 
        client_rate = base_rate + client_discount
        pln_amount = client_rate * amount_eur
        direction = "Klient sprzedaje EUR, otrzymuje PLN"
    
    # Display client offer
    st.subheader("💱 Oferta dla Klienta")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Kurs Kliencki",
            f"{client_rate:.4f}",
            help=f"Kurs dla klienta {client_type}"
        )
    
    with col2:
        st.metric(
            "Kwota PLN",
            f"{pln_amount:,.0f}",
            help="Kwota w PLN"
        )
    
    with col3:
        spot_diff = ((client_rate - rate_data['rate']) / rate_data['rate']) * 100
        st.metric(
            "vs Spot",
            f"{spot_diff:+.3f}%",
            help="Różnica względem kursu spot"
        )
    
    # Transaction summary
    st.markdown(f"""
    <div class="metric-card">
        <h4>📋 Podsumowanie Transakcji</h4>
        <p><strong>Typ:</strong> {direction}</p>
        <p><strong>Kwota:</strong> {amount_eur:,} EUR = {pln_amount:,.0f} PLN</p>
        <p><strong>Kurs:</strong> {client_rate:.4f} (rabat: {client_discount:.4f})</p>
        <p><strong>Klient:</strong> {client_type}</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# PREDICTION PANEL
# ============================================================================

def create_prediction_panel():
    """5-day EUR/PLN prediction using binomial model"""
    
    st.header("🔮 Model Predykcyjny EUR/PLN")
    
    if not st.session_state.current_rate_data:
        st.warning("⚠️ Najpierw załaduj dane w Panelu Dealerskim!")
        return
    
    rate_data = st.session_state.current_rate_data
    current_rate = rate_data['rate']
    
    st.markdown(f"""
    <div class="prediction-panel">
        <h3>🌳 Model Dwumianowy - Prognoza 5 dni</h3>
        <p>Przewidywanie kursu EUR/PLN na najbliższe 5 dni</p>
        <p>Obecny kurs: {current_rate:.4f}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Model parameters
    st.subheader("⚙️ Parametry Modelu")
    
    col1, col2 = st.columns(2)
    
    with col1:
        volatility = st.slider(
            "Zmienność (%):",
            min_value=5.0,
            max_value=25.0,
            value=12.0,
            step=0.5,
            help="Roczna zmienność kursu"
        ) / 100
        
        risk_free_rate = st.slider(
            "Stopa Wolna od Ryzyka (%):",
            min_value=2.0,
            max_value=8.0,
            value=5.5,
            step=0.1,
            help="Stopa procentowa wolna od ryzyka"
        ) / 100
    
    with col2:
        st.info(f"""
        **Model Parameters:**
        - Okres: 5 dni
        - Kroki: 5 (1 dzień = 1 krok)
        - Obecny kurs: {current_rate:.4f}
        - Zmienność: {volatility*100:.1f}%
        """)
    
    # Generate prediction
    if st.button("🧮 Generuj Prognozę", type="primary"):
        alpha_api = AlphaVantageAPI()
        model = EURPLNBinomialModel(alpha_api)
        
        with st.spinner("🌳 Obliczanie scenariuszy..."):
            prediction = model.predict_5_day_scenarios(
                current_rate, volatility, risk_free_rate
            )
            st.session_state.prediction_results = prediction
        
        st.success("✅ Prognoza wygenerowana!")
    
    # Display results
    if st.session_state.prediction_results:
        prediction = st.session_state.prediction_results
        
        st.subheader("📊 Wyniki Prognozy")
        
        # Create prediction chart
        fig = go.Figure()
        
        # Add expected rates line
        days = [0] + [p['day'] for p in prediction['predictions']]
        expected_rates = [current_rate] + [p['expected_rate'] for p in prediction['predictions']]
        
        fig.add_trace(go.Scatter(
            x=days,
            y=expected_rates,
            mode='lines+markers',
            name='Oczekiwany Kurs',
            line=dict(color='blue', width=3)
        ))
        
        # Add volatility bands
        high_rates = [current_rate] + [p['volatility_range']['high'] for p in prediction['predictions']]
        low_rates = [current_rate] + [p['volatility_range']['low'] for p in prediction['predictions']]
        
        fig.add_trace(go.Scatter(
            x=days + days[::-1],
            y=high_rates + low_rates[::-1],
            fill='toself',
            fillcolor='rgba(0,100,80,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            name='Zakres Zmienności'
        ))
        
        fig.update_layout(
            title="Prognoza EUR/PLN na 5 dni",
            xaxis_title="Dzień",
            yaxis_title="Kurs EUR/PLN",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Prediction table
        st.subheader("📋 Szczegółowe Scenariusze")
        
        prediction_data = []
        for day_pred in prediction['predictions']:
            for i, scenario in enumerate(day_pred['scenarios']):
                prediction_data.append({
                    'Dzień': day_pred['day'],
                    'Data': day_pred['date'],
                    'Scenariusz': f"#{i+1}",
                    'Kurs': f"{scenario['rate']:.4f}",
                    'Zmiana': f"{scenario['change_pct']:+.2f}%",
                    'Prawdopodobieństwo': f"{scenario['probability']*100:.1f}%"
                })
        
        df_prediction = pd.DataFrame(prediction_data)
        st.dataframe(df_prediction, use_container_width=True, hide_index=True)
        
        # Summary
        final_expected = prediction['predictions'][-1]['expected_rate']
        final_change = ((final_expected - current_rate) / current_rate) * 100
        
        st.markdown(f"""
        <div class="metric-card">
            <h4>🎯 Podsumowanie Prognozy (Dzień 5)</h4>
            <p><strong>Oczekiwany kurs:</strong> {final_expected:.4f}</p>
            <p><strong>Oczekiwana zmiana:</strong> {final_change:+.2f}%</p>
            <p><strong>Zakres:</strong> {prediction['predictions'][-1]['volatility_range']['low']:.4f} - {prediction['predictions'][-1]['volatility_range']['high']:.4f}</p>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application"""
    
    initialize_session_state()
    
    # Header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1>💱 FX Trading Platform</h1>
        <p style="color: #7f8c8d;">EUR/PLN Trading & Prediction System</p>
        <p><em>Powered by Alpha Vantage API 📈</em></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "🏦 Panel Dealerski", 
        "🤝 Panel Kliencki",
        "🔮 Model Predykcyjny"
    ])
    
    with tab1:
        create_dealer_panel()
    
    with tab2:
        create_client_panel()
    
    with tab3:
        create_prediction_panel()

if __name__ == "__main__":
    main()
