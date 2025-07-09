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
FRED_API_KEY = st.secrets.get("FRED_API_KEY", "c37067e3f35ff6cb1d6a0d70d1e7cfc0")  # Uses Streamlit secrets or demo

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
    .client-summary-green {
        background: white;
        color: #2c3e50;
        border: 3px solid #2e68a5;
    }
    .client-summary-blue {
        background: white;
        color: #2c3e50;
        border: 3px solid #2e68a5;
    }
    .client-summary-purple {
        background: white;
        color: #2c3e50;
        border: 3px solid #2e68a5;
    }
    .client-summary-orange {
        background: white;
        color: #2c3e50;
        border: 3px solid #2e68a5;
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
# MAIN APPLICATION
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
    
    st.markdown("*Alpha Vantage + NBP + FRED APIs | Professional FX Platform*")
    
    # Simple API status check
    with st.spinner("📡 Sprawdzanie API..."):
        forex_data = get_eur_pln_rate()
        
    if forex_data['success']:
        st.success(f"✅ API Online | EUR/PLN: {forex_data['rate']:.4f} | Źródło: {forex_data['source']}")
    else:
        st.warning(f"⚠️ API Fallback | EUR/PLN: {forex_data['rate']:.4f} | Źródło: {forex_data['source']}")
    
    # Simple demo
    st.subheader("📊 Alpha Vantage API Demo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Current EUR/PLN",
            f"{forex_data['rate']:.4f}",
            help=f"Source: {forex_data['source']}"
        )
    
    with col2:
        # Get historical data
        historical_data = get_historical_eur_pln_data(20)
        st.metric(
            "Historical Data Points",
            f"{historical_data['count']}",
            help=f"Source: {historical_data['source']}"
        )
    
    # Display some historical data if available
    if historical_data['success'] and len(historical_data['rates']) > 5:
        st.subheader("📈 Recent EUR/PLN Rates")
        
        # Create simple chart
        rates = historical_data['rates'][-10:]  # Last 10 rates
        dates = historical_data['dates'][-10:]  # Last 10 dates
        
        chart_data = pd.DataFrame({
            'Date': dates,
            'Rate': rates
        })
        
        st.line_chart(chart_data.set_index('Date'))
        
        # Calculate basic volatility
        if len(rates) >= 5:
            returns = np.diff(np.log(rates))
            volatility = np.std(returns) * np.sqrt(252) * 100  # Annualized %
            
            st.info(f"📊 Calculated volatility: {volatility:.2f}% annually")
    
    # API Info
    st.subheader("🔑 API Configuration")
    
    st.markdown(f"""
    - **Alpha Vantage Key**: `{ALPHA_VANTAGE_API_KEY}` ✅
    - **FRED Key**: `{FRED_API_KEY}` 
    - **NBP**: Public API (no key needed)
    
    **API Priority:**
    1. Alpha Vantage (primary)
    2. NBP (backup)  
    3. Static fallback (emergency)
    """)

if __name__ == "__main__":
    main()
