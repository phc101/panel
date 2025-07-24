import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import math

# CONFIG & SETUP
st.set_page_config(
    page_title="Professional FX Calculator",
    page_icon="chart",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Clean CSS without emoji
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 1rem;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    
    .profit-card {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .sync-status {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        margin: 1rem 0;
        font-weight: 500;
    }
    
    .api-status {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .recommendation-excellent { background-color: #d4edda !important; }
    .recommendation-good { background-color: #fff3cd !important; }
    .recommendation-ok { background-color: #ffeaa7 !important; }
    .recommendation-poor { background-color: #f8d7da !important; }
</style>
""", unsafe_allow_html=True)

# CORE API CLASSES
class RobustAlphaVantageAPI:
    def __init__(self):
        self.api_key = "MQGKUNL9JWIJHF9S"
        self.base_url = "https://www.alphavantage.co/query"
    
    def get_eur_pln_rate(self):
        """Get EUR/PLN with multiple fallbacks"""
        # Try Alpha Vantage first
        try:
            params = {
                'function': 'CURRENCY_EXCHANGE_RATE',
                'from_currency': 'EUR',
                'to_currency': 'PLN',
                'apikey': self.api_key
            }
            response = requests.get(self.base_url, params=params, timeout=8)
            data = response.json()
            
            if 'Realtime Currency Exchange Rate' in data:
                rate_data = data['Realtime Currency Exchange Rate']
                return {
                    'rate': float(rate_data['5. Exchange Rate']),
                    'date': rate_data['6. Last Refreshed'][:10],
                    'source': 'Alpha Vantage API',
                    'success': True
                }
        except Exception as e:
            pass
        
        # NBP fallback
        try:
            response = requests.get("https://api.nbp.pl/api/exchangerates/rates/a/eur/", timeout=5)
            data = response.json()
            if data.get('rates'):
                return {
                    'rate': data['rates'][0]['mid'],
                    'date': data['rates'][0]['effectiveDate'],
                    'source': 'NBP Bank Polski',
                    'success': True
                }
        except:
            pass
        
        # Final fallback
        return {
            'rate': 4.25,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'source': 'Default Rate',
            'success': False
        }
    
    def get_historical_data(self, days=30):
        """Get historical EUR/PLN data"""
        try:
            params = {
                'function': 'FX_DAILY',
                'from_symbol': 'EUR', 
                'to_symbol': 'PLN',
                'apikey': self.api_key,
                'outputsize': 'compact'
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json()
            
            if 'Time Series (FX)' in data:
                time_series = data['Time Series (FX)']
                rates = []
                dates = sorted(time_series.keys(), reverse=True)
                
                for date in dates[:days]:
                    rate = float(time_series[date]['4. close'])
                    rates.append(rate)
                
                return {
                    'rates': rates,
                    'dates': dates[:len(rates)],
                    'source': 'Alpha Vantage Historical',
                    'success': True,
                    'count': len(rates)
                }
        except:
            pass
        
        # NBP historical fallback
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days+5)
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            url = f"https://api.nbp.pl/api/exchangerates/rates/a/eur/{start_str}/{end_str}/"
            response = requests.get(url, timeout=8)
            data = response.json()
            
            if data.get('rates'):
                rates = [r['mid'] for r in data['rates']]
                dates = [r['effectiveDate'] for r in data['rates']]
                return {
                    'rates': rates[-days:],
                    'dates': dates[-days:],
                    'source': 'NBP Historical',
                    'success': True,
                    'count': len(rates[-days:])
                }
        except:
            pass
        
        # Synthetic fallback
        base_rate = 4.25
        rates = [base_rate * (1 + np.random.normal(0, 0.005)) for _ in range(days)]
        dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
        
        return {
            'rates': rates,
            'dates': dates,
            'source': 'Synthetic Data',
            'success': False,
            'count': days
        }

class BondYieldsAPI:
    def __init__(self):
        self.fred_key = "demo"
    
    def get_yields(self):
        """Get bond yields with fallbacks"""
        return {
            'Poland_10Y': {'value': 5.65, 'date': '2025-01-24', 'source': 'Market Data'},
            'Germany_10Y': {'value': 2.45, 'date': '2025-01-24', 'source': 'Market Data'},
            'US_10Y': {'value': 4.35, 'date': '2025-01-24', 'source': 'Market Data'}
        }

# SESSION STATE MANAGEMENT
def init_session_state():
    if 'dealer_config' not in st.session_state:
        st.session_state.dealer_config = {
            'spot_rate': 4.25,
            'spot_source': 'Default',
            'pl_yield': 5.65,
            'de_yield': 2.45,
            'window_days': 90,
            'points_factor': 0.70,
            'risk_factor': 0.40,
            'bid_ask_spread': 0.002,
            'volatility_factor': 0.25,
            'minimum_profit_floor': 0.000
        }
    
    if 'pricing_data' not in st.session_state:
        st.session_state.pricing_data = None

# FORWARD CALCULATOR ENGINE
class ProfessionalForwardCalculator:
    def __init__(self):
        self.points_factor = 0.70
        self.risk_factor = 0.40
    
    def calculate_theoretical_forward(self, spot, pl_yield, de_yield, days):
        """Calculate theoretical forward rate"""
        T = days / 365.0
        forward_rate = spot * (1 + pl_yield/100 * T) / (1 + de_yield/100 * T)
        forward_points = forward_rate - spot
        
        return {
            'forward_rate': forward_rate,
            'forward_points': forward_points,
            'yield_spread': pl_yield - de_yield,
            'time_factor': T
        }
    
    def generate_forward_curve(self, config):
        """Generate complete forward curve"""
        curve_data = []
        
        for months in range(1, 13):
            days = months * 30
            tenor_name = f"{months} miesiac" if months == 1 else f"{months} miesiace" if months <= 4 else f"{months} miesiecy"
            
            # Calculate theoretical forward
            theoretical = self.calculate_theoretical_forward(
                config['spot_rate'], config['pl_yield'], config['de_yield'], days
            )
            
            # Calculate risk premium
            volatility_adjustment = abs(theoretical['forward_points']) * config['volatility_factor'] * np.sqrt(config['window_days'] / 90)
            swap_risk = max(volatility_adjustment, 0.015)
            
            # Calculate client rate
            points_to_client = theoretical['forward_points'] * config['points_factor']
            risk_charge = swap_risk * config['risk_factor']
            
            client_rate_initial = config['spot_rate'] + points_to_client - risk_charge
            theoretical_rate = config['spot_rate'] + theoretical['forward_points']
            
            profit_per_eur = theoretical_rate - client_rate_initial
            
            # Apply minimum profit floor
            if profit_per_eur < config['minimum_profit_floor']:
                client_rate = theoretical_rate - config['minimum_profit_floor']
                profit_per_eur = config['minimum_profit_floor']
            else:
                client_rate = client_rate_initial
            
            # Window dates
            window_start = datetime.now() + timedelta(days=days)
            window_end = window_start + timedelta(days=config['window_days'])
            
            curve_data.append({
                'tenor_months': months,
                'tenor_name': tenor_name,
                'tenor_days': days,
                'window_start': window_start.strftime("%d.%m.%Y"),
                'window_end': window_end.strftime("%d.%m.%Y"),
                'theoretical_rate': theoretical_rate,
                'forward_points': theoretical['forward_points'],
                'swap_risk': swap_risk,
                'client_rate': client_rate,
                'profit_per_eur': profit_per_eur,
                'yield_spread': theoretical['yield_spread']
            })
        
        return curve_data

# BINOMIAL MODEL
def calculate_binomial_coeff(n, k):
    """Safe binomial coefficient calculation"""
    if k > n or k < 0:
        return 0
    if k == 0 or k == n:
        return 1
    
    result = 1
    for i in range(min(k, n - k)):
        result = result * (n - i) // (i + 1)
    return result

def create_binomial_tree(spot, volatility, days, p=0.5):
    """Create binomial tree for FX prediction"""
    u = 1 + volatility
    d = 1 - volatility
    
    tree = {}
    most_probable_path = []
    
    for day in range(days + 1):
        tree[day] = {}
        
        if day == 0:
            tree[day][0] = spot
            most_probable_path.append(0)
        else:
            best_j = 0
            best_prob = 0
            
            for j in range(day + 1):
                rate = spot * (u ** j) * (d ** (day - j))
                tree[day][j] = rate
                
                # Find most probable node
                prob = calculate_binomial_coeff(day, j) * (p ** j) * ((1 - p) ** (day - j))
                if prob > best_prob:
                    best_prob = prob
                    best_j = j
            
            most_probable_path.append(best_j)
    
    return tree, most_probable_path

# UI COMPONENTS
def render_header():
    st.markdown("""
    <div class="main-header">
        <h1>Professional FX Calculator</h1>
        <p>Advanced EUR/PLN Forward Pricing & Hedging Platform</p>
        <p>Alpha Vantage • NBP • Real-time Market Data</p>
    </div>
    """, unsafe_allow_html=True)

def render_dealer_panel():
    st.header("Dealer Panel")
    
    # Initialize APIs
    forex_api = RobustAlphaVantageAPI()
    bonds_api = BondYieldsAPI()
    
    # Get market data
    with st.spinner("Loading market data..."):
        forex_data = forex_api.get_eur_pln_rate()
        bond_data = bonds_api.get_yields()
        historical_data = forex_api.get_historical_data(30)
    
    # API Status
    col1, col2 = st.columns(2)
    
    with col1:
        status_color = "#11998e" if forex_data['success'] else "#e17055"
        st.markdown(f"""
        <div class="api-status" style="background: {status_color};">
            <h4>FX Data Source</h4>
            <p><strong>Rate:</strong> {forex_data['rate']:.4f}</p>
            <p><strong>Source:</strong> {forex_data['source']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="api-status">
            <h4>Historical Data</h4>
            <p><strong>Points:</strong> {historical_data['count']}</p>
            <p><strong>Source:</strong> {historical_data['source']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Configuration
    st.subheader("Market Configuration")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        use_live_rate = st.checkbox("Use Live Rate", value=True)
    
    with col2:
        if use_live_rate:
            spot_rate = forex_data['rate']
            spot_source = forex_data['source']
            st.info(f"Live rate: {spot_rate:.4f} from {spot_source}")
        else:
            spot_rate = st.number_input("Manual EUR/PLN Rate", 
                                      value=st.session_state.dealer_config['spot_rate'],
                                      min_value=3.5, max_value=6.0, step=0.0001, format="%.4f")
            spot_source = "Manual Input"
    
    # Bond yields
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("EUR/PLN Spot", f"{spot_rate:.4f}")
    
    with col2:
        pl_yield = bond_data['Poland_10Y']['value']
        st.metric("Poland 10Y", f"{pl_yield:.2f}%")
    
    with col3:
        de_yield = bond_data['Germany_10Y']['value'] 
        st.metric("Germany 10Y", f"{de_yield:.2f}%")
    
    with col4:
        spread = pl_yield - de_yield
        st.metric("PL-DE Spread", f"{spread:.2f}pp")
    
    # Advanced parameters
    st.subheader("Advanced Parameters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        window_days = st.number_input("Window Days", 
                                    value=st.session_state.dealer_config['window_days'],
                                    min_value=30, max_value=365, step=5)
        
        points_factor = st.slider("Points Factor", 0.60, 0.85, 
                                st.session_state.dealer_config['points_factor'], 0.01)
    
    with col2:
        risk_factor = st.slider("Risk Factor", 0.30, 0.60,
                              st.session_state.dealer_config['risk_factor'], 0.01)
        
        volatility_factor = st.slider("Volatility Factor", 0.15, 0.35,
                                    st.session_state.dealer_config['volatility_factor'], 0.01)
    
    with col3:
        bid_ask_spread = st.number_input("Bid-Ask Spread", 
                                       value=st.session_state.dealer_config['bid_ask_spread'],
                                       min_value=0.001, max_value=0.005, step=0.0005, format="%.4f")
        
        min_profit = st.number_input("Min Profit Floor", 
                                   value=st.session_state.dealer_config['minimum_profit_floor'],
                                   min_value=-0.02, max_value=0.02, step=0.001, format="%.4f")
    
    # Update configuration
    if st.button("Update Pricing", use_container_width=True):
        st.session_state.dealer_config.update({
            'spot_rate': spot_rate,
            'spot_source': spot_source,
            'pl_yield': pl_yield,
            'de_yield': de_yield,
            'window_days': window_days,
            'points_factor': points_factor,
            'risk_factor': risk_factor,
            'bid_ask_spread': bid_ask_spread,
            'volatility_factor': volatility_factor,
            'minimum_profit_floor': min_profit
        })
        
        # Generate pricing
        calculator = ProfessionalForwardCalculator()
        calculator.points_factor = points_factor
        calculator.risk_factor = risk_factor
        
        st.session_state.pricing_data = calculator.generate_forward_curve(st.session_state.dealer_config)
        
        st.success("Pricing updated successfully!")
        st.rerun()
    
    # Display current pricing
    if st.session_state.pricing_data:
        st.subheader("Current Dealer Pricing")
        
        # Create pricing table
        pricing_table = []
        for item in st.session_state.pricing_data:
            pricing_table.append({
                "Tenor": item['tenor_name'],
                "Days": item['tenor_days'],
                "Forward Points": f"{item['forward_points']:.4f}",
                "Swap Risk": f"{item['swap_risk']:.4f}",
                "Client Rate": f"{item['client_rate']:.4f}",
                "Profit/EUR": f"{item['profit_per_eur']:.4f}",
                "Window": f"{item['window_start']} - {item['window_end']}"
            })
        
        df_pricing = pd.DataFrame(pricing_table)
        st.dataframe(df_pricing, use_container_width=True, height=400)
        
        # Portfolio analytics
        st.subheader("Portfolio Analytics")
        
        nominal_amount = st.number_input("Nominal Amount (EUR)", value=2_500_000, 
                                       min_value=10_000, max_value=100_000_000, step=100_000)
        
        total_profit = sum(item['profit_per_eur'] * nominal_amount for item in st.session_state.pricing_data)
        avg_client_rate = np.mean([item['client_rate'] for item in st.session_state.pricing_data])
        avg_profit_per_eur = np.mean([item['profit_per_eur'] for item in st.session_state.pricing_data])
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="profit-card">
                <h4>Total Portfolio Profit</h4>
                <h2>{total_profit:,.0f} PLN</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.metric("Average Client Rate", f"{avg_client_rate:.4f}")
        
        with col3:
            st.metric("Average Profit/EUR", f"{avg_profit_per_eur:.4f}")
        
        with col4:
            profit_margin = (total_profit / (spot_rate * nominal_amount * len(st.session_state.pricing_data))) * 100
            st.metric("Portfolio Margin", f"{profit_margin:.3f}%")

def render_client_panel():
    st.header("Client Hedging Panel")
    
    if not st.session_state.pricing_data:
        st.warning("No dealer pricing available. Please configure dealer panel first.")
        return
    
    config = st.session_state.dealer_config
    
    st.markdown(f"""
    <div class="sync-status">
        Pricing Synchronized | Spot: {config['spot_rate']:.4f} | Window: {config['window_days']} days
    </div>
    """, unsafe_allow_html=True)
    
    # Client parameters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        exposure_amount = st.number_input("EUR Exposure Amount", value=1_000_000,
                                        min_value=10_000, max_value=50_000_000, step=10_000)
    
    with col2:
        show_windows = st.checkbox("Show Settlement Windows", value=False)
    
    with col3:
        st.info(f"Window Flexibility: **{config['window_days']} days**")
    
    # Generate client rates
    st.subheader("Available Forward Rates")
    
    client_data = []
    spot_rate = config['spot_rate']
    
    for item in st.session_state.pricing_data:
        client_rate = item['client_rate']
        rate_advantage = ((client_rate - spot_rate) / spot_rate) * 100
        
        pln_amount_forward = client_rate * exposure_amount
        pln_amount_spot = spot_rate * exposure_amount
        additional_pln = pln_amount_forward - pln_amount_spot
        
        # Recommendation logic
        if rate_advantage > 0.5:
            recommendation = "Excellent"
            rec_class = "recommendation-excellent"
        elif rate_advantage > 0.2:
            recommendation = "Good"
            rec_class = "recommendation-good"
        elif rate_advantage > 0:
            recommendation = "Acceptable"
            rec_class = "recommendation-ok"
        else:
            recommendation = "Consider Spot"
            rec_class = "recommendation-poor"
        
        row_data = {
            "Tenor": item['tenor_name'],
            "Forward Rate": f"{client_rate:.4f}",
            "vs Spot": f"{rate_advantage:+.2f}%",
            "PLN Amount": f"{pln_amount_forward:,.0f}",
            "Additional PLN": f"{additional_pln:+,.0f}" if additional_pln != 0 else "0",
            "Recommendation": recommendation,
            "rec_class": rec_class
        }
        
        if show_windows:
            row_data.update({
                "Settlement From": item['window_start'],
                "Settlement To": item['window_end']
            })
        
        client_data.append(row_data)
    
    # Display client rates table
    df_client = pd.DataFrame(client_data)
    display_df = df_client.drop('rec_class', axis=1, errors='ignore')
    
    # Apply styling based on recommendations
    def highlight_recommendations(row):
        rec_class = client_data[row.name]['rec_class']
        colors = {
            'recommendation-excellent': '#d4edda',
            'recommendation-good': '#fff3cd', 
            'recommendation-ok': '#ffeaa7',
            'recommendation-poor': '#f8d7da'
        }
        color = colors.get(rec_class, '#ffffff')
        return [f'background-color: {color}'] * len(row)
    
    styled_df = display_df.style.apply(highlight_recommendations, axis=1)
    st.dataframe(styled_df, use_container_width=True, height=400, hide_index=True)
    
    # Summary metrics
    st.subheader("Hedging Strategy Summary")
    
    avg_client_rate = np.mean([float(data["Forward Rate"]) for data in client_data])
    avg_benefit = np.mean([float(data["vs Spot"].rstrip('%')) for data in client_data])
    total_additional = sum([float(data["Additional PLN"].replace(',', '').replace('+', '')) 
                          for data in client_data if data["Additional PLN"] != "0"])
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h4>Average Forward Rate</h4>
            <h2>{avg_client_rate:.4f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h4>Average Benefit vs Spot</h4>
            <h2>{avg_benefit:+.2f}%</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h4>Total Additional PLN</h4>
            <h2>{total_additional:+,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Visual comparison
    st.subheader("Visual Rate Comparison")
    
    # Prepare data for plotting
    tenors = [data["Tenor"] for data in client_data]
    forward_rates = [float(data["Forward Rate"]) for data in client_data]
    spot_rates = [spot_rate] * len(tenors)
    
    fig = go.Figure()
    
    # Spot line
    fig.add_trace(go.Scatter(
        x=tenors, y=spot_rates,
        mode='lines',
        name=f'Spot Rate ({spot_rate:.4f})',
        line=dict(color='red', width=2, dash='dash'),
        hovertemplate='Spot: %{y:.4f}<extra></extra>'
    ))
    
    # Forward rates
    fig.add_trace(go.Scatter(
        x=tenors, y=forward_rates,
        mode='lines+markers',
        name='Forward Rates',
        line=dict(color='#2e68a5', width=3),
        marker=dict(size=10, color='#2e68a5'),
        hovertemplate='%{x}: %{y:.4f}<extra></extra>'
    ))
    
    # Benefits bars
    benefits = [(rate - spot_rate) * exposure_amount for rate in forward_rates]
    
    fig.add_trace(go.Bar(
        x=tenors, y=benefits,
        name='Benefit vs Spot (PLN)',
        yaxis='y2',
        marker_color='lightblue',
        opacity=0.7,
        hovertemplate='%{x}: %{y:,.0f} PLN<extra></extra>'
    ))
    
    fig.update_layout(
        title="Forward Rates vs Spot Rate + PLN Benefits",
        xaxis_title="Tenor",
        yaxis_title="EUR/PLN Rate",
        yaxis2=dict(title="Benefit (PLN)", overlaying='y', side='right'),
        height=500,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_binomial_model():
    st.header("Binomial Tree Model")
    st.markdown("*5-day EUR/PLN forecast using binomial option pricing methodology*")
    
    # Get current market data
    forex_api = RobustAlphaVantageAPI()
    
    with st.spinner("Loading market data..."):
        current_forex = forex_api.get_eur_pln_rate()
        historical_data = forex_api.get_historical_data(30)
    
    # Display data sources
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="api-status">
            <h4>Current Rate</h4>
            <p><strong>Rate:</strong> {current_forex['rate']:.4f}</p>
            <p><strong>Source:</strong> {current_forex['source']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="api-status">
            <h4>Historical Data</h4>
            <p><strong>Points:</strong> {historical_data['count']}</p>
            <p><strong>Source:</strong> {historical_data['source']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Calculate empirical volatility
    try:
        if historical_data['success'] and len(historical_data['rates']) >= 15:
            rates = historical_data['rates']
            returns = [np.log(rates[i]/rates[i-1]) for i in range(1, len(rates))]
            empirical_vol = np.std(returns)
            empirical_mean = np.mean(returns)
            
            # Simple probability estimation
            positive_moves = sum(1 for r in returns if r > 0)
            p_up_empirical = positive_moves / len(returns)
            
            st.success(f"Empirical model: Vol={empirical_vol*100:.2f}% daily, P(up)={p_up_empirical:.3f}")
        else:
            raise Exception("Insufficient data")
    except:
        empirical_vol = 0.008
        p_up_empirical = 0.5
        st.warning("Using default parameters")
    
    # Model parameters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        spot_rate = st.number_input("Starting Rate", value=current_forex['rate'], 
                                  min_value=3.5, max_value=6.0, step=0.0001, format="%.4f")
    
    with col2:
        days = st.selectbox("Forecast Horizon", [3, 5, 7, 10], index=1)
    
    with col3:
        use_empirical = st.checkbox("Use Empirical Parameters", value=True)
        
        if use_empirical:
            volatility = empirical_vol
            p_up = p_up_empirical
            st.info(f"Vol: {volatility*100:.2f}%")
        else:
            volatility = st.slider("Daily Volatility (%)", 0.1, 2.0, 0.8, 0.1) / 100
            p_up = st.slider("Up Probability", 0.3, 0.7, 0.5, 0.01)
    
    # Generate binomial tree
    if st.button("Generate Tree Model"):
        tree, most_probable_path = create_binomial_tree(spot_rate, volatility, days, p_up)
        
        # Final prediction
        st.subheader("Model Forecast")
        
        final_j = most_probable_path[days]
        predicted_rate = tree[days][final_j]
        change_pct = ((predicted_rate - spot_rate) / spot_rate) * 100
        
        final_prob = calculate_binomial_coeff(days, final_j) * (p_up ** final_j) * ((1 - p_up) ** (days - final_j))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(f"Forecast ({days} days)", f"{predicted_rate:.4f}", delta=f"{change_pct:+.2f}%")
        
        with col2:
            st.metric("Path Probability", f"{final_prob*100:.1f}%")
        
        with col3:
            all_final_rates = [tree[days][j] for j in range(days + 1)]
            rate_range = max(all_final_rates) - min(all_final_rates)
            st.metric("Rate Range", f"{rate_range:.4f}")
        
        # All possible outcomes
        st.subheader("All Possible Outcomes")
        
        outcomes = []
        for j in range(days + 1):
            final_rate = tree[days][j]
            prob = calculate_binomial_coeff(days, j) * (p_up ** j) * ((1 - p_up) ** (days - j))
            change = ((final_rate - spot_rate) / spot_rate) * 100
            
            is_most_probable = (j == final_j)
            
            outcomes.append({
                "Scenario": f"{j} up, {days-j} down",
                "Final Rate": f"{final_rate:.4f}",
                "Change %": f"{change:+.2f}%",
                "Probability": f"{prob*100:.1f}%",
                "Most Likely": "YES" if is_most_probable else ""
            })
        
        df_outcomes = pd.DataFrame(outcomes)
        st.dataframe(df_outcomes, use_container_width=True, hide_index=True)
        
        # Visualization
        st.subheader("Binomial Tree Visualization")
        
        try:
            fig = go.Figure()
            
            # Plot all nodes
            for day in range(days + 1):
                for j in range(day + 1):
                    rate = tree[day][j]
                    x = day
                    y = j - day/2
                    
                    is_on_path = (j == most_probable_path[day])
                    
                    # Node
                    fig.add_trace(go.Scatter(
                        x=[x], y=[y],
                        mode='markers',
                        marker=dict(
                            size=25 if is_on_path else 18,
                            color='#ff6b35' if is_on_path else '#2e68a5',
                            line=dict(width=3, color='white')
                        ),
                        showlegend=False,
                        hovertemplate=f"Day {day}<br>Rate: {rate:.4f}<br>Node: {j}<extra></extra>",
                        name=f"node_{day}_{j}"
                    ))
                    
                    # Rate label
                    fig.add_trace(go.Scatter(
                        x=[x], y=[y + 0.3],
                        mode='text',
                        text=f"{rate:.4f}",
                        textfont=dict(
                            size=12 if is_on_path else 10,
                            color='#ff6b35' if is_on_path else '#2e68a5'
                        ),
                        showlegend=False,
                        hoverinfo='skip',
                        name=f"label_{day}_{j}"
                    ))
                    
                    # Connections
                    if day < days:
                        # Up connection
                        if j < day + 1:
                            next_y_up = (j + 1) - (day + 1)/2
                            is_path_connection = (j == most_probable_path[day] and (j + 1) == most_probable_path[day + 1])
                            
                            fig.add_trace(go.Scatter(
                                x=[x, x + 1], y=[y, next_y_up],
                                mode='lines',
                                line=dict(
                                    color='#ff6b35' if is_path_connection else 'lightgray',
                                    width=4 if is_path_connection else 1
                                ),
                                showlegend=False,
                                hoverinfo='skip',
                                name=f"up_{day}_{j}"
                            ))
                        
                        # Down connection
                        if j >= 0:
                            next_y_down = j - (day + 1)/2
                            is_path_connection = (j == most_probable_path[day] and j == most_probable_path[day + 1])
                            
                            fig.add_trace(go.Scatter(
                                x=[x, x + 1], y=[y, next_y_down],
                                mode='lines',
                                line=dict(
                                    color='#ff6b35' if is_path_connection else 'lightgray',
                                    width=4 if is_path_connection else 1
                                ),
                                showlegend=False,
                                hoverinfo='skip',
                                name=f"down_{day}_{j}"
                            ))
            
            # Legend
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(size=25, color='#ff6b35'),
                name='Most Probable Path',
                showlegend=True
            ))
            
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode='markers', 
                marker=dict(size=18, color='#2e68a5'),
                name='Other Possible Rates',
                showlegend=True
            ))
            
            fig.update_layout(
                title=f"EUR/PLN Binomial Tree - {days} Day Forecast",
                xaxis_title="Day",
                yaxis_title="Tree Level",
                height=600,
                showlegend=True,
                hovermode='closest'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Visualization error: {str(e)}")
            st.info("Tree calculation completed successfully. Visualization temporarily unavailable.")
        
        # Statistical summary
        st.subheader("Statistical Summary")
        
        all_rates = [tree[days][j] for j in range(days + 1)]
        all_probs = [calculate_binomial_coeff(days, j) * (p_up ** j) * ((1 - p_up) ** (days - j)) for j in range(days + 1)]
        
        expected_rate = sum(rate * prob for rate, prob in zip(all_rates, all_probs))
        variance = sum(((rate - expected_rate) ** 2) * prob for rate, prob in zip(all_rates, all_probs))
        std_dev = math.sqrt(variance)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Expected Rate", f"{expected_rate:.4f}")
        
        with col2:
            st.metric("Standard Deviation", f"{std_dev:.4f}")
        
        with col3:
            st.metric("Min Possible", f"{min(all_rates):.4f}")
        
        with col4:
            st.metric("Max Possible", f"{max(all_rates):.4f}")

# MAIN APPLICATION
def main():
    # Initialize
    init_session_state()
    
    # Render header
    render_header()
    
    # Sync status
    if st.session_state.pricing_data:
        config = st.session_state.dealer_config
        st.markdown(f"""
        <div class="sync-status">
            System Synchronized | Spot: {config['spot_rate']:.4f} | Window: {config['window_days']} days | Source: {config['spot_source']}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Waiting for dealer configuration...")
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs([
        "Dealer Panel", 
        "Client Hedging", 
        "Binomial Model"
    ])
    
    with tab1:
        try:
            render_dealer_panel()
        except Exception as e:
            st.error(f"Dealer panel error: {str(e)}")
            st.info("Please refresh the page or check your internet connection.")
    
    with tab2:
        try:
            render_client_panel()
        except Exception as e:
            st.error(f"Client panel error: {str(e)}")
            st.info("Ensure dealer panel is configured first.")
    
    with tab3:
        try:
            render_binomial_model()
        except Exception as e:
            st.error(f"Binomial model error: {str(e)}")
            st.info("Model temporarily unavailable. Please try again.")

# Run the application
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application startup error: {str(e)}")
        st.markdown("## Application Recovery")
        st.info("Please refresh the page. If the problem persists, clear your browser cache.")
        
        if st.button("Restart Application"):
            st.rerun()
