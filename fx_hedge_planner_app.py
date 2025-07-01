import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta

# FRED API Configuration
FRED_API_KEY = "f65897ba8bbc5c387dc26081d5b66edf"  # Replace with your API key

# Page config
st.set_page_config(
    page_title="Window Forward Calculator - Prawdziwa Metodologia",
    page_icon="💱",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .calculation-step {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.5rem;
        border-radius: 0.8rem;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .result-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 1.5rem;
        border-radius: 0.8rem;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
        text-align: center;
    }
    .final-rate {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1976d2;
        margin: 0.5rem 0;
    }
    .profit-box {
        background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%);
        padding: 1.5rem;
        border-radius: 0.8rem;
        border-left: 4px solid #4caf50;
        margin: 1rem 0;
        text-align: center;
    }
    .formula-box {
        background-color: #2d3748;
        color: #e2e8f0;
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Courier New', monospace;
        margin: 1rem 0;
    }
    .metric-large {
        font-size: 1.8rem;
        font-weight: bold;
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# API CLIENTS
# ============================================================================

class FREDAPIClient:
    """FRED API client for fetching economic data"""
    
    def __init__(self, api_key=FRED_API_KEY):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"
    
    def get_series_data(self, series_id, limit=1, sort_order='desc'):
        """Get latest data for a specific FRED series"""
        url = f"https://api.stlouisfed.org/fred/series/observations"
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json',
            'limit': limit,
            'sort_order': sort_order
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'observations' in data and data['observations']:
                latest = data['observations'][0]
                if latest['value'] != '.':
                    return {
                        'value': float(latest['value']),
                        'date': latest['date'],
                        'series_id': series_id,
                        'source': 'FRED',
                        'status': 'success'
                    }
            return {'status': 'no_data', 'series_id': series_id}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'series_id': series_id}
    
    def get_multiple_series(self, series_dict):
        """Get data for multiple FRED series"""
        results = {}
        errors = []
        for name, series_id in series_dict.items():
            data = self.get_series_data(series_id)
            if data.get('status') == 'success':
                results[name] = data
            else:
                errors.append(f"{name}: {data.get('error', 'No data available')}")
        
        if errors:
            st.warning(f"FRED API issues: {'; '.join(errors)}")
        
        return results

# ============================================================================
# WINDOW FORWARD CALCULATOR
# ============================================================================

class WindowForwardCalculator:
    """Professional Window Forward Calculator with correct methodology"""
    
    def __init__(self):
        self.fred_client = FREDAPIClient()
    
    def calculate_forward_points(self, spot_rate, polish_yield, german_yield, days):
        """Calculate forward points using bond yield differential"""
        T = days / 365.0
        if T == 0:
            return 0
        
        forward_rate = spot_rate * (1 + polish_yield/100 * T) / (1 + german_yield/100 * T)
        forward_points = forward_rate - spot_rate
        return forward_points
    
    def calculate_window_forward_pricing(self, spot_rate, forward_points, points_to_client_pct=0.70, risk_compensation_pct=0.40):
        """
        Calculate Window Forward pricing using CORRECT methodology:
        FWD_Client = Spot + (Forward_Points × 0.70) - (Forward_Points × 0.40)
        FWD_Client = Spot + (Forward_Points × 0.30)
        """
        
        # Points given to client (70% of forward points)
        points_to_client = forward_points * points_to_client_pct
        
        # Risk compensation (40% of forward points) - DEDUCTED from client rate
        risk_compensation = forward_points * risk_compensation_pct
        
        # Final client rate
        client_rate = spot_rate + points_to_client - risk_compensation
        
        # Net points for client (30% of forward points)
        net_points_client = forward_points * (points_to_client_pct - risk_compensation_pct)
        
        # Dealer profit (70% of forward points)
        dealer_profit = forward_points * (1 - (points_to_client_pct - risk_compensation_pct))
        
        # Theoretical forward rate (100% of points)
        theoretical_rate = spot_rate + forward_points
        
        return {
            "client_rate": client_rate,
            "theoretical_rate": theoretical_rate,
            "forward_points": forward_points,
            "points_to_client": points_to_client,
            "risk_compensation": risk_compensation,
            "net_points_client": net_points_client,
            "dealer_profit": dealer_profit,
            "dealer_profit_pct": (dealer_profit / spot_rate) * 100
        }
    
    def analyze_multiple_windows(self, spot_rate, polish_yield, german_yield):
        """Analyze different window lengths"""
        windows = [30, 60, 90, 120, 180, 270, 365]
        results = []
        
        for days in windows:
            forward_points = self.calculate_forward_points(spot_rate, polish_yield, german_yield, days)
            pricing = self.calculate_window_forward_pricing(spot_rate, forward_points)
            
            results.append({
                "window_days": days,
                "window_months": days / 30,
                "forward_points": forward_points,
                "forward_points_pips": forward_points * 10000,
                "client_rate": pricing["client_rate"],
                "dealer_profit": pricing["dealer_profit"],
                "dealer_profit_pips": pricing["dealer_profit"] * 10000,
                "dealer_profit_pct": pricing["dealer_profit_pct"]
            })
        
        return results

# ============================================================================
# DATA FUNCTIONS
# ============================================================================

@st.cache_data(ttl=3600)
def get_bond_data():
    """Get government bond yields from FRED"""
    fred_client = FREDAPIClient()
    bond_series = {
        'Poland_10Y': 'IRLTLT01PLM156N',
        'Germany_10Y': 'IRLTLT01DEM156N'
    }
    
    data = fred_client.get_multiple_series(bond_series)
    return data

@st.cache_data(ttl=300)
def get_eur_pln_rate():
    """Get current EUR/PLN from NBP API"""
    try:
        url = "https://api.nbp.pl/api/exchangerates/rates/a/eur/"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            'rate': data['rates'][0]['mid'],
            'date': data['rates'][0]['effectiveDate'],
            'source': 'NBP',
            'status': 'success'
        }
    except Exception as e:
        return {
            'rate': 4.25, 
            'date': datetime.now().strftime('%Y-%m-%d'), 
            'source': 'Fallback',
            'status': 'fallback'
        }

# ============================================================================
# MAIN APPLICATION
# ============================================================================

# Header
st.markdown("""
<div style="display: flex; align-items: center; margin-bottom: 2rem;">
    <div style="background: linear-gradient(45deg, #667eea, #764ba2); width: 60px; height: 60px; border-radius: 10px; margin-right: 1rem; display: flex; align-items: center; justify-content: center;">
        <span style="font-size: 2rem;">💱</span>
    </div>
    <div>
        <h1 style="margin: 0; color: #2c3e50;">Window Forward Calculator</h1>
        <p style="margin: 0; color: #7f8c8d;">Prawdziwa Metodologia Dealerska</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Load market data
with st.spinner("📡 Ładowanie danych rynkowych..."):
    bond_data = get_bond_data()
    forex_data = get_eur_pln_rate()

# Initialize calculator
calc = WindowForwardCalculator()

# ============================================================================
# MARKET DATA DISPLAY
# ============================================================================

st.subheader("📊 Aktualne Dane Rynkowe")

col1, col2, col3, col4 = st.columns(4)

with col1:
    status_emoji = "🟢" if forex_data.get('status') == 'success' else "🟡"
    st.metric(
        f"{status_emoji} EUR/PLN Spot", 
        f"{forex_data['rate']:.4f}",
        help=f"Źródło: {forex_data['source']} | Data: {forex_data['date']}"
    )

with col2:
    if 'Poland_10Y' in bond_data:
        pl_yield = bond_data['Poland_10Y']['value']
        status_emoji = "🟢" if bond_data['Poland_10Y'].get('status') == 'success' else "🟡"
        st.metric(
            f"{status_emoji} Polska 10Y", 
            f"{pl_yield:.2f}%",
            help=f"Data: {bond_data['Poland_10Y']['date']}"
        )
    else:
        pl_yield = 5.70
        st.metric("🟡 Polska 10Y", f"{pl_yield:.2f}%", help="Dane zastępcze")

with col3:
    if 'Germany_10Y' in bond_data:
        de_yield = bond_data['Germany_10Y']['value']
        status_emoji = "🟢" if bond_data['Germany_10Y'].get('status') == 'success' else "🟡"
        st.metric(
            f"{status_emoji} Niemcy 10Y", 
            f"{de_yield:.2f}%",
            help=f"Data: {bond_data['Germany_10Y']['date']}"
        )
    else:
        de_yield = 2.35
        st.metric("🟡 Niemcy 10Y", f"{de_yield:.2f}%", help="Dane zastępcze")

with col4:
    spread = pl_yield - de_yield
    st.metric(
        "Spread PL-DE", 
        f"{spread:.2f}pp",
        help="Różnica zysków obligacji"
    )

# ============================================================================
# CALCULATOR INTERFACE
# ============================================================================

st.markdown("---")
st.subheader("🧮 Kalkulator Window Forward")

# Input parameters
input_col1, input_col2 = st.columns(2)

with input_col1:
    st.markdown("**Parametry Transakcji:**")
    
    spot_rate = st.number_input(
        "Kurs Spot EUR/PLN:",
        value=forex_data['rate'],
        min_value=3.0,
        max_value=6.0,
        step=0.0001,
        format="%.4f"
    )
    
    window_days = st.selectbox(
        "Długość Okna:",
        [30, 60, 90, 120, 180, 270, 365],
        index=2,  # Default 90 days
        help="Długość okna transakcyjnego w dniach"
    )
    
    nominal_amount = st.number_input(
        "Kwota Nominalna (EUR):",
        value=1_000_000,
        min_value=100_000,
        max_value=100_000_000,
        step=100_000,
        format="%d"
    )

with input_col2:
    st.markdown("**Parametry Rynkowe:**")
    
    pl_yield_input = st.number_input(
        "Zysk Obligacji Polski (%):",
        value=pl_yield,
        min_value=0.0,
        max_value=20.0,
        step=0.01,
        format="%.2f"
    )
    
    de_yield_input = st.number_input(
        "Zysk Obligacji Niemiec (%):",
        value=de_yield,
        min_value=-2.0,
        max_value=10.0,
        step=0.01,
        format="%.2f"
    )
    
    st.info(f"**Spread:** {pl_yield_input - de_yield_input:.2f} punktów proc.")

# ============================================================================
# CALCULATION AND RESULTS
# ============================================================================

st.markdown("---")
st.subheader("📋 Kalkulacja Krok po Kroku")

# Step 1: Calculate forward points
forward_points = calc.calculate_forward_points(spot_rate, pl_yield_input, de_yield_input, window_days)

st.markdown(f"""
<div class="calculation-step">
<h4>Krok 1: Punkty Forward ({window_days} dni)</h4>
<div class="formula-box">
T = {window_days}/365 = {window_days/365:.3f} lat

Forward_Rate = {spot_rate:.4f} × (1 + {pl_yield_input:.2f}% × {window_days/365:.3f}) / (1 + {de_yield_input:.2f}% × {window_days/365:.3f})
Forward_Rate = {spot_rate:.4f} × {1 + pl_yield_input/100 * window_days/365:.5f} / {1 + de_yield_input/100 * window_days/365:.5f}
Forward_Rate = {spot_rate + forward_points:.4f}

Forward_Points = {spot_rate + forward_points:.4f} - {spot_rate:.4f} = {forward_points:.4f}
</div>
<p><strong>Punkty Forward: {forward_points:.4f} ({forward_points*10000:.1f} pips)</strong></p>
</div>
""", unsafe_allow_html=True)

# Step 2: Window Forward calculation
pricing = calc.calculate_window_forward_pricing(spot_rate, forward_points)

st.markdown(f"""
<div class="calculation-step">
<h4>Krok 2: Kalkulacja Window Forward</h4>
<div class="formula-box">
Points_dla_klienta = {forward_points:.4f} × 0.70 = {pricing['points_to_client']:.4f}
Risk_compensation = {forward_points:.4f} × 0.40 = {pricing['risk_compensation']:.4f}

FWD_Client = Spot + Points_dla_klienta - Risk_compensation
FWD_Client = {spot_rate:.4f} + {pricing['points_to_client']:.4f} - {pricing['risk_compensation']:.4f}
FWD_Client = {pricing['client_rate']:.4f}
</div>
<p><strong>Uproszczenie: FWD_Client = Spot + (Forward_Points × 0.30)</strong></p>
<p><strong>FWD_Client = {spot_rate:.4f} + ({forward_points:.4f} × 0.30) = {pricing['client_rate']:.4f}</strong></p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# RESULTS DISPLAY
# ============================================================================

st.markdown("---")
st.subheader("🎯 Wyniki Końcowe")

result_col1, result_col2, result_col3 = st.columns(3)

with result_col1:
    st.markdown(f"""
    <div class="result-box">
        <h4>🎯 Kurs dla Klienta</h4>
        <div class="final-rate">{pricing['client_rate']:.4f}</div>
        <p>EUR/PLN Window Forward</p>
    </div>
    """, unsafe_allow_html=True)

with result_col2:
    st.markdown(f"""
    <div class="result-box">
        <h4>📈 Kurs Teoretyczny</h4>
        <div class="final-rate">{pricing['theoretical_rate']:.4f}</div>
        <p>Pełny Forward (100% punktów)</p>
    </div>
    """, unsafe_allow_html=True)

with result_col3:
    profit_nominal = pricing['dealer_profit'] * nominal_amount
    st.markdown(f"""
    <div class="profit-box">
        <h4>💰 Zysk Dealera</h4>
        <div class="final-rate">{pricing['dealer_profit_pct']:.3f}%</div>
        <p>{pricing['dealer_profit']*10000:.1f} pips | {profit_nominal:,.0f} EUR</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# DETAILED BREAKDOWN
# ============================================================================

st.markdown("---")
st.subheader("🔍 Szczegółowy Rozkład")

breakdown_col1, breakdown_col2 = st.columns(2)

with breakdown_col1:
    st.markdown("**Komponenty Ceny:**")
    st.write(f"• Kurs Spot: **{spot_rate:.4f}**")
    st.write(f"• Punkty Forward: **{forward_points:.4f}** ({forward_points*10000:.1f} pips)")
    st.write(f"• Points dla klienta (70%): **+{pricing['points_to_client']:.4f}**")
    st.write(f"• Risk compensation (40%): **-{pricing['risk_compensation']:.4f}**")
    st.write(f"• **Kurs końcowy: {pricing['client_rate']:.4f}**")
    st.write(f"• **Netto dla klienta: +{pricing['net_points_client']:.4f}** (30% punktów)")

with breakdown_col2:
    st.markdown("**Analiza Zysku:**")
    st.write(f"• Punkty zatrzymane: **{pricing['dealer_profit']:.4f}** (70%)")
    st.write(f"• Zysk w pipsach: **{pricing['dealer_profit']*10000:.1f} pips**")
    st.write(f"• Zysk procentowy: **{pricing['dealer_profit_pct']:.3f}%**")
    st.write(f"• Kwota nominalna: **{nominal_amount:,} EUR**")
    st.write(f"• **Zysk nominalny: {profit_nominal:,.0f} EUR**")
    
    # ROI calculation
    required_capital = nominal_amount * 0.05  # Assume 5% margin requirement
    roi = (profit_nominal / required_capital) * 100
    st.write(f"• **ROI (przy 5% marży): {roi:.1f}%**")

# ============================================================================
# WINDOW LENGTH ANALYSIS
# ============================================================================

st.markdown("---")
st.subheader("📊 Analiza Różnych Długości Okien")

analysis_results = calc.analyze_multiple_windows(spot_rate, pl_yield_input, de_yield_input)

# Create table
analysis_data = []
for result in analysis_results:
    analysis_data.append({
        "Okno": f"{result['window_days']} dni ({result['window_months']:.1f}M)",
        "Forward Points": f"{result['forward_points']:.4f}",
        "Pips Forward": f"{result['forward_points_pips']:.1f}",
        "Kurs Klienta": f"{result['client_rate']:.4f}",
        "Zysk Dealera": f"{result['dealer_profit']:.4f}",
        "Zysk (pips)": f"{result['dealer_profit_pips']:.1f}",
        "Zysk (%)": f"{result['dealer_profit_pct']:.3f}%"
    })

df_analysis = pd.DataFrame(analysis_data)
st.dataframe(df_analysis, use_container_width=True)

# ============================================================================
# VISUALIZATION
# ============================================================================

st.subheader("📈 Wizualizacja Zysków vs Długość Okna")

# Create profit chart
fig = go.Figure()

windows = [r['window_days'] for r in analysis_results]
profits_pips = [r['dealer_profit_pips'] for r in analysis_results]
profits_pct = [r['dealer_profit_pct'] for r in analysis_results]

fig.add_trace(go.Scatter(
    x=windows,
    y=profits_pips,
    mode='lines+markers',
    name='Zysk (pips)',
    line=dict(color='#1f77b4', width=3),
    marker=dict(size=8),
    yaxis='y'
))

fig.add_trace(go.Scatter(
    x=windows,
    y=profits_pct,
    mode='lines+markers',
    name='Zysk (%)',
    line=dict(color='#ff7f0e', width=3),
    marker=dict(size=8),
    yaxis='y2'
))

fig.update_layout(
    title="Zysk Dealera vs Długość Okna",
    xaxis_title="Długość Okna (dni)",
    yaxis=dict(title="Zysk (pips)", side="left"),
    yaxis2=dict(title="Zysk (%)", side="right", overlaying="y"),
    height=400,
    legend=dict(x=0.02, y=0.98)
)

st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# SUMMARY AND INSIGHTS
# ============================================================================

st.markdown("---")
st.subheader("💡 Wnioski i Rekomendacje")

insights_col1, insights_col2 = st.columns(2)

with insights_col1:
    st.markdown("**Kluczowe Obserwacje:**")
    
    # Find optimal window
    optimal_result = max(analysis_results, key=lambda x: x['dealer_profit_pct'])
    
    st.success(f"🎯 **Optymalne okno:** {optimal_result['window_days']} dni ({optimal_result['dealer_profit_pct']:.3f}% zysku)")
    
    if spread > 3:
        st.warning("⚠️ **Wysoki spread** - zwiększone ryzyko, ale wyższe zyski")
    else:
        st.info("ℹ️ **Normalny spread** - stabilne warunki rynkowe")
    
    if pricing['dealer_profit_pct'] > 0.3:
        st.success("✅ **Atrakcyjna marża** - dobra rentowność transakcji")
    else:
        st.warning("⚠️ **Niska marża** - rozważ zmianę parametrów")

with insights_col2:
    st.markdown("**Strategiczne Rekomendacje:**")
    
    st.markdown(f"""
    • **Obecna transakcja**: {pricing['dealer_profit']*10000:.1f} pips zysku
    • **Nominalny zysk**: {profit_nominal:,.0f} EUR
    • **ROI**: {roi:.1f}% (przy 5% marży)
    
    **Działania:**
    """)
    
    if window_days < 90:
        st.info("📈 Rozważ dłuższe okna dla wyższych zysków")
    elif window_days > 180:
        st.warning("📉 Krótsze okna mogą być bardziej konkurencyjne")
    else:
        st.success("✅ Optymalna długość okna")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p><strong>Window Forward Calculator</strong> - Prawdziwa Metodologia Dealerska</p>
    <p>Formuła: FWD_Client = Spot + (Forward_Points × 0.30)</p>
    <p>Dealer zatrzymuje 70% punktów forward jako zysk</p>
</div>
""", unsafe_allow_html=True)
