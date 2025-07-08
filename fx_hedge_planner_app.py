import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import math

# ============================================================================
# CONFIGURATION & PAGE SETUP
# ============================================================================

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
    .profit-metric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
    }
    .nbp-api {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
    }
    .binomial-model {
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
# NBP API CLIENT
# ============================================================================

class NBPAPIClient:
    """Professional NBP API client for Polish central bank data"""
    
    def __init__(self):
        self.base_url = "https://api.nbp.pl/api"
        
    def get_eur_pln_rate(self):
        """Get current EUR/PLN exchange rate from NBP"""
        try:
            url = f"{self.base_url}/exchangerates/rates/a/eur/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('rates') and len(data['rates']) > 0:
                return {
                    'rate': data['rates'][0]['mid'],
                    'date': data['rates'][0]['effectiveDate'],
                    'source': 'NBP Official 🏛️',
                    'success': True
                }
        except Exception as e:
            st.warning(f"NBP API error: {str(e)}")
            return {
                'rate': 4.25,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'source': 'Fallback ⚠️',
                'success': False
            }
    
    def get_usd_pln_rate(self):
        """Get current USD/PLN exchange rate from NBP"""
        try:
            url = f"{self.base_url}/exchangerates/rates/a/usd/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('rates') and len(data['rates']) > 0:
                return {
                    'rate': data['rates'][0]['mid'],
                    'date': data['rates'][0]['effectiveDate'],
                    'source': 'NBP Official 🏛️',
                    'success': True
                }
        except Exception as e:
            return {
                'rate': 4.00,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'source': 'Fallback ⚠️',
                'success': False
            }
    
    def get_gold_price(self):
        """Get current gold price in PLN from NBP"""
        try:
            url = f"{self.base_url}/cenyzlota/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                return {
                    'price': data[0]['cena'],
                    'date': data[0]['data'],
                    'source': 'NBP Official 🏛️',
                    'success': True
                }
        except Exception as e:
            return {
                'price': 250.0,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'source': 'Fallback ⚠️',
                'success': False
            }

# ============================================================================
# PROFESSIONAL BINOMIAL OPTION PRICING MODEL
# ============================================================================

class BinomialOptionModel:
    """Professional binomial model for FX options with NBP data integration"""
    
    def __init__(self, nbp_client):
        self.nbp_client = nbp_client
        
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
# SESSION STATE INITIALIZATION
# ============================================================================

def initialize_session_state():
    """Initialize session state for data sharing"""
    if 'nbp_data' not in st.session_state:
        st.session_state.nbp_data = None
    if 'binomial_results' not in st.session_state:
        st.session_state.binomial_results = None

# ============================================================================
# CACHED DATA FUNCTIONS
# ============================================================================

@st.cache_data(ttl=3600)
def get_nbp_market_data():
    """Get market data from NBP API with caching"""
    nbp_client = NBPAPIClient()
    
    return {
        'eur_pln': nbp_client.get_eur_pln_rate(),
        'usd_pln': nbp_client.get_usd_pln_rate(),
        'gold': nbp_client.get_gold_price()
    }

# ============================================================================
# NBP DATA PANEL
# ============================================================================

def create_nbp_data_panel():
    """Panel with NBP market data"""
    
    st.header("📊 NBP Market Data")
    st.markdown("*Real-time data from Polish National Bank*")
    
    # Load NBP data
    with st.spinner("📡 Loading NBP data..."):
        nbp_data = get_nbp_market_data()
        st.session_state.nbp_data = nbp_data
    
    # Display API status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        eur_data = nbp_data['eur_pln']
        if eur_data['success']:
            st.markdown(f"""
            <div class="nbp-api">
                <h4 style="margin: 0;">💶 EUR/PLN Rate</h4>
                <p style="margin: 0; font-size: 1.5rem; font-weight: bold;">{eur_data['rate']:.4f}</p>
                <p style="margin: 0;">Date: {eur_data['date']}</p>
                <p style="margin: 0;">Source: {eur_data['source']}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error(f"EUR/PLN: {eur_data['rate']:.4f} (Fallback)")
    
    with col2:
        usd_data = nbp_data['usd_pln']
        if usd_data['success']:
            st.markdown(f"""
            <div class="nbp-api">
                <h4 style="margin: 0;">💵 USD/PLN Rate</h4>
                <p style="margin: 0; font-size: 1.5rem; font-weight: bold;">{usd_data['rate']:.4f}</p>
                <p style="margin: 0;">Date: {usd_data['date']}</p>
                <p style="margin: 0;">Source: {usd_data['source']}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error(f"USD/PLN: {usd_data['rate']:.4f} (Fallback)")
    
    with col3:
        gold_data = nbp_data['gold']
        if gold_data['success']:
            st.markdown(f"""
            <div class="nbp-api">
                <h4 style="margin: 0;">🥇 Gold Price</h4>
                <p style="margin: 0; font-size: 1.5rem; font-weight: bold;">{gold_data['price']:.2f} PLN/g</p>
                <p style="margin: 0;">Date: {gold_data['date']}</p>
                <p style="margin: 0;">Source: {gold_data['source']}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error(f"Gold: {gold_data['price']:.2f} PLN/g (Fallback)")
    
    return nbp_data

# ============================================================================
# BINOMIAL OPTIONS PANEL
# ============================================================================

def create_binomial_options_panel():
    """Panel for binomial option pricing with NBP integration"""
    
    st.header("🌳 Binomial Option Pricing Model")
    st.markdown("*Professional FX options valuation using NBP data*")
    
    # Check if NBP data is available
    if not st.session_state.nbp_data:
        st.warning("⚠️ Load NBP data first from the Market Data tab!")
        return
    
    nbp_data = st.session_state.nbp_data
    
    # Show current market data
    st.markdown(f"""
    <div class="binomial-model">
        <h4 style="margin: 0;">🎯 Current Market Data (NBP)</h4>
        <p style="margin: 0;">EUR/PLN: {nbp_data['eur_pln']['rate']:.4f} | USD/PLN: {nbp_data['usd_pln']['rate']:.4f}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Option parameters
    st.subheader("⚙️ Option Parameters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Currency pair selection
        currency_pair = st.selectbox(
            "Currency Pair:",
            ["EUR/PLN", "USD/PLN"],
            help="Select currency pair for option pricing"
        )
        
        # Get current spot rate from NBP
        if currency_pair == "EUR/PLN":
            current_spot = nbp_data['eur_pln']['rate']
        else:
            current_spot = nbp_data['usd_pln']['rate']
        
        spot_price = st.number_input(
            f"Spot Price ({currency_pair}):",
            value=current_spot,
            min_value=0.1,
            max_value=10.0,
            step=0.0001,
            format="%.4f",
            help="Current spot exchange rate"
        )
    
    with col2:
        strike_price = st.number_input(
            "Strike Price:",
            value=current_spot * 1.05,
            min_value=0.1,
            max_value=10.0,
            step=0.0001,
            format="%.4f",
            help="Option strike price"
        )
        
        option_type = st.selectbox(
            "Option Type:",
            ["call", "put"],
            help="Call or Put option"
        )
    
    with col3:
        time_to_expiry = st.number_input(
            "Time to Expiry (days):",
            value=30,
            min_value=1,
            max_value=365,
            step=1,
            help="Days until option expiration"
        ) / 365  # Convert to years
        
        notional_amount = st.number_input(
            "Notional Amount:",
            value=1_000_000,
            min_value=10_000,
            max_value=100_000_000,
            step=10_000,
            format="%d",
            help="Option notional amount"
        )
    
    # Advanced parameters
    with st.expander("🔧 Advanced Model Parameters"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            risk_free_rate = st.slider(
                "Risk-Free Rate (%):",
                min_value=0.0,
                max_value=10.0,
                value=5.5,
                step=0.1,
                help="Polish risk-free interest rate"
            ) / 100
        
        with col2:
            volatility = st.slider(
                "Volatility (%):",
                min_value=5.0,
                max_value=50.0,
                value=15.0,
                step=0.5,
                help="Implied volatility"
            ) / 100
        
        with col3:
            tree_steps = st.slider(
                "Tree Steps:",
                min_value=10,
                max_value=200,
                value=100,
                step=10,
                help="Number of binomial tree steps"
            )
    
    # Calculate button
    if st.button("🧮 Calculate Option Price", type="primary", use_container_width=True):
        
        # Initialize binomial model
        nbp_client = NBPAPIClient()
        binomial_model = BinomialOptionModel(nbp_client)
        
        with st.spinner("🌳 Building binomial tree..."):
            
            # Calculate option price
            option_result = binomial_model.calculate_binomial_tree(
                spot_price, strike_price, time_to_expiry, risk_free_rate, 
                volatility, tree_steps, option_type
            )
            
            # Calculate Greeks
            greeks = binomial_model.calculate_greeks(
                spot_price, strike_price, time_to_expiry, risk_free_rate,
                volatility, tree_steps, option_type
            )
            
            # Store results
            st.session_state.binomial_results = {
                'option_result': option_result,
                'greeks': greeks,
                'parameters': {
                    'spot_price': spot_price,
                    'strike_price': strike_price,
                    'time_to_expiry': time_to_expiry,
                    'risk_free_rate': risk_free_rate,
                    'volatility': volatility,
                    'tree_steps': tree_steps,
                    'option_type': option_type,
                    'currency_pair': currency_pair,
                    'notional_amount': notional_amount
                }
            }
        
        st.success("✅ Option pricing completed!")
        st.rerun()
    
    # Display results if available
    if st.session_state.binomial_results:
        display_binomial_results()

def display_binomial_results():
    """Display binomial model results"""
    
    results = st.session_state.binomial_results
    option_result = results['option_result']
    greeks = results['greeks']
    params = results['parameters']
    
    st.markdown("---")
    st.subheader("📈 Option Pricing Results")
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        option_price = option_result['option_price']
        premium_pct = (option_price / params['spot_price']) * 100
        st.metric(
            "Option Price",
            f"{option_price:.6f}",
            help=f"{premium_pct:.3f}% of spot price"
        )
    
    with col2:
        total_premium = option_price * params['notional_amount']
        st.metric(
            "Total Premium",
            f"{total_premium:,.0f} PLN",
            help="Premium × Notional Amount"
        )
    
    with col3:
        moneyness = params['spot_price'] / params['strike_price']
        if params['option_type'] == 'call':
            itm_status = "ITM" if moneyness > 1 else "OTM"
        else:
            itm_status = "ITM" if moneyness < 1 else "OTM"
        
        st.metric(
            "Moneyness",
            f"{moneyness:.4f}",
            help=f"Spot/Strike - {itm_status}"
        )
    
    with col4:
        time_value = option_price
        if params['option_type'] == 'call':
            intrinsic = max(params['spot_price'] - params['strike_price'], 0)
        else:
            intrinsic = max(params['strike_price'] - params['spot_price'], 0)
        
        time_value = max(option_price - intrinsic, 0)
        
        st.metric(
            "Time Value",
            f"{time_value:.6f}",
            help="Option price minus intrinsic value"
        )
    
    # Greeks display
    st.subheader("🔢 Option Greeks")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Delta (Δ)",
            f"{greeks['delta']:.4f}",
            help="Price sensitivity to spot rate"
        )
    
    with col2:
        st.metric(
            "Gamma (Γ)",
            f"{greeks['gamma']:.6f}",
            help="Delta sensitivity to spot rate"
        )
    
    with col3:
        st.metric(
            "Theta (Θ)",
            f"{greeks['theta']:.6f}",
            help="Time decay (per day)"
        )
    
    with col4:
        st.metric(
            "Vega (ν)",
            f"{greeks['vega']:.6f}",
            help="Volatility sensitivity"
        )
    
    with col5:
        st.metric(
            "Rho (ρ)",
            f"{greeks['rho']:.6f}",
            help="Interest rate sensitivity"
        )
    
    # Model parameters summary
    st.subheader("📋 Model Parameters")
    
    params_df = pd.DataFrame([
        ["Currency Pair", params['currency_pair']],
        ["Spot Price", f"{params['spot_price']:.4f}"],
        ["Strike Price", f"{params['strike_price']:.4f}"],
        ["Time to Expiry", f"{params['time_to_expiry']*365:.0f} days"],
        ["Risk-Free Rate", f"{params['risk_free_rate']*100:.1f}%"],
        ["Volatility", f"{params['volatility']*100:.1f}%"],
        ["Tree Steps", f"{params['tree_steps']:,}"],
        ["Option Type", params['option_type'].upper()],
        ["Notional Amount", f"{params['notional_amount']:,}"]
    ], columns=["Parameter", "Value"])
    
    st.dataframe(params_df, use_container_width=True, hide_index=True)
    
    # Binomial tree visualization for small trees
    if params['tree_steps'] <= 10:
        st.subheader("🌳 Binomial Tree Visualization")
        
        nbp_client = NBPAPIClient()
        binomial_model = BinomialOptionModel(nbp_client)
        
        tree_data = binomial_model.generate_price_tree_visualization(
            params['spot_price'], params['strike_price'], params['time_to_expiry'],
            params['risk_free_rate'], params['volatility'], params['tree_steps']
        )
        
        # Create tree plot
        fig = go.Figure()
        
        for point in tree_data:
            fig.add_trace(go.Scatter(
                x=[point['x']],
                y=[point['y']],
                mode='markers+text',
                text=[f"{point['price']:.3f}"],
                textposition="middle center",
                marker=dict(size=20, color='lightblue'),
                showlegend=False
            ))
        
        # Add connections
        for i in range(params['tree_steps']):
            for j in range(i + 1):
                # Connect to up node
                if i < params['tree_steps']:
                    fig.add_shape(
                        type="line",
                        x0=i, y0=i-2*j,
                        x1=i+1, y1=(i+1)-2*j,
                        line=dict(color="gray", width=1)
                    )
                    # Connect to down node
                    fig.add_shape(
                        type="line",
                        x0=i, y0=i-2*j,
                        x1=i+1, y1=(i+1)-2*(j+1),
                        line=dict(color="gray", width=1)
                    )
        
        fig.update_layout(
            title="Binomial Price Tree",
            xaxis_title="Time Steps",
            yaxis_title="Price Nodes",
            showlegend=False,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application with NBP integration and binomial model"""
    
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 2rem;">
        <div style="background: linear-gradient(45deg, #667eea, #764ba2); width: 60px; height: 60px; border-radius: 10px; margin-right: 1rem; display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 2rem;">🚀</span>
        </div>
        <h1 style="margin: 0; color: #2c3e50;">Professional FX Platform with Binomial Model</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("*Powered by NBP Official API 🏛️ + Advanced Binomial Option Pricing 🌳*")
    
    # Create tabs
    tab1, tab2 = st.tabs(["📊 NBP Market Data", "🌳 Binomial Options"])
    
    with tab1:
        create_nbp_data_panel()
    
    with tab2:
        create_binomial_options_panel()

if __name__ == "__main__":
    main()
