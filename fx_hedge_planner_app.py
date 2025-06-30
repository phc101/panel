import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="FX Bond Spread Dashboard",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for dashboard styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .actual-rate {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E86AB;
        margin: 0;
    }
    .predicted-rate {
        font-size: 2.5rem;
        font-weight: bold;
        color: #F24236;
        margin: 0;
    }
    .rate-label {
        font-size: 1rem;
        color: #666;
        margin-bottom: 0.5rem;
    }
    .difference {
        font-size: 1.2rem;
        font-weight: bold;
        color: #28a745;
    }
</style>
""", unsafe_allow_html=True)

class FXBondSpreadDashboard:
    def __init__(self):
        self.fred_api_key = "demo"
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"
    
    def get_fred_data(self, series_id, start_date, end_date):
        """Get historical data from FRED API"""
        params = {
            'series_id': series_id,
            'api_key': self.fred_api_key,
            'file_type': 'json',
            'start_date': start_date,
            'end_date': end_date,
            'frequency': 'd',
            'aggregation_method': 'avg'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=15)
            data = response.json()
            
            if 'observations' in data:
                df_data = []
                for obs in data['observations']:
                    if obs['value'] != '.':
                        df_data.append({
                            'date': pd.to_datetime(obs['date']),
                            'value': float(obs['value'])
                        })
                return pd.DataFrame(df_data).set_index('date')
            return pd.DataFrame()
        except Exception as e:
            st.warning(f"FRED API error for {series_id}: {e}")
            return pd.DataFrame()
    
    def get_nbp_historical_data(self, start_date, end_date):
        """Get historical EUR/PLN from NBP API"""
        try:
            # NBP API dla danych historycznych
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            url = f"https://api.nbp.pl/api/exchangerates/rates/a/eur/{start_str}/{end_str}/"
            response = requests.get(url, timeout=15)
            data = response.json()
            
            df_data = []
            for rate in data['rates']:
                df_data.append({
                    'date': pd.to_datetime(rate['effectiveDate']),
                    'value': rate['mid']
                })
            
            return pd.DataFrame(df_data).set_index('date')
        except Exception as e:
            st.warning(f"NBP API error: {e}")
            # Fallback to simulated data
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            # Simulate EUR/PLN around 4.24 with some volatility
            np.random.seed(42)
            values = 4.24 + np.cumsum(np.random.randn(len(dates)) * 0.01)
            return pd.DataFrame({'value': values}, index=dates)
    
    def calculate_predicted_fx_rate(self, pl_yield, de_yield, base_rate=4.24):
        """
        Calculate predicted FX rate based on bond yield spread
        
        Model: FX_predicted = base_rate * (1 + yield_spread_adjustment)
        """
        yield_spread = pl_yield - de_yield
        # Empirical adjustment factor (can be calibrated with historical data)
        spread_sensitivity = 0.15  # 1% yield spread moves FX by ~15%
        
        predicted_rate = base_rate * (1 + yield_spread * spread_sensitivity / 100)
        return predicted_rate
    
    def generate_sample_data(self, end_date):
        """Generate sample data for demonstration"""
        start_date = end_date - timedelta(days=180)  # 6 months
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Simulate realistic EUR/PLN movement
        np.random.seed(42)
        base_rate = 4.24
        
        # Actual EUR/PLN with some trend and volatility
        trend = np.linspace(0, 0.02, len(dates))  # Slight upward trend
        noise = np.cumsum(np.random.randn(len(dates)) * 0.003)
        actual_eur_pln = base_rate + trend + noise
        
        # Bond yields simulation
        pl_yields = 5.7 + np.cumsum(np.random.randn(len(dates)) * 0.01)  # Poland 1Y
        de_yields = 2.2 + np.cumsum(np.random.randn(len(dates)) * 0.008)  # Germany 1Y
        
        # Predicted rates based on yield spreads
        predicted_eur_pln = []
        for i in range(len(dates)):
            pred_rate = self.calculate_predicted_fx_rate(pl_yields[i], de_yields[i], base_rate)
            predicted_eur_pln.append(pred_rate)
        
        return pd.DataFrame({
            'actual_eur_pln': actual_eur_pln,
            'predicted_eur_pln': predicted_eur_pln,
            'pl_yield': pl_yields,
            'de_yield': de_yields,
            'yield_spread': pl_yields - de_yields
        }, index=dates)

# Initialize dashboard
dashboard = FXBondSpreadDashboard()

# Header
st.markdown("""
<div style="display: flex; align-items: center; margin-bottom: 2rem;">
    <div style="background: linear-gradient(45deg, #ff6b6b, #4ecdc4); width: 60px; height: 60px; border-radius: 10px; margin-right: 1rem; display: flex; align-items: center; justify-content: center;">
        <span style="font-size: 2rem;">📊</span>
    </div>
    <h1 style="margin: 0; color: #2c3e50;">FX Bond Spread Dashboard</h1>
</div>
""", unsafe_allow_html=True)

st.markdown("*Predicting EUR/PLN using 1-Year Government Bond Spreads*")

# Generate sample data (6 months historical)
end_date = datetime.now().date()
start_date = end_date - timedelta(days=180)

with st.spinner("📊 Loading market data and calculating predictions..."):
    # Try to get real data, fallback to sample data
    try:
        # Get real EUR/PLN data
        eur_pln_data = dashboard.get_nbp_historical_data(start_date, end_date)
        
        # Get bond yield data from FRED
        pl_bonds = dashboard.get_fred_data('IRLTLT01PLM156N', 
                                         start_date.strftime('%Y-%m-%d'), 
                                         end_date.strftime('%Y-%m-%d'))
        de_bonds = dashboard.get_fred_data('IRLTLT01DEM156N', 
                                         start_date.strftime('%Y-%m-%d'), 
                                         end_date.strftime('%Y-%m-%d'))
        
        # If we have partial real data, combine with simulated
        if not eur_pln_data.empty and not pl_bonds.empty and not de_bonds.empty:
            # Use real data where available
            st.success("✅ Using real market data from NBP and FRED APIs")
            
            # Create predicted rates based on bond spreads
            df = eur_pln_data.copy()
            df.columns = ['actual_eur_pln']
            
            # Add bond yields (forward fill missing data)
            df = df.join(pl_bonds.rename(columns={'value': 'pl_yield'}), how='left')
            df = df.join(de_bonds.rename(columns={'value': 'de_yield'}), how='left')
            df = df.fillna(method='ffill').fillna(method='bfill')
            
            # Calculate predicted rates
            df['predicted_eur_pln'] = df.apply(
                lambda row: dashboard.calculate_predicted_fx_rate(
                    row['pl_yield'], row['de_yield'], df['actual_eur_pln'].iloc[0]
                ), axis=1
            )
            df['yield_spread'] = df['pl_yield'] - df['de_yield']
            
        else:
            st.info("📊 Using sample data for demonstration (register for FRED API for real data)")
            df = dashboard.generate_sample_data(end_date)
    
    except Exception as e:
        st.info("📊 Using sample data for demonstration")
        df = dashboard.generate_sample_data(end_date)

# Current values
current_actual = df['actual_eur_pln'].iloc[-1]
current_predicted = df['predicted_eur_pln'].iloc[-1]
difference_pct = ((current_predicted - current_actual) / current_actual) * 100

# Main dashboard layout
col1, col2 = st.columns(2)

with col1:
    st.markdown("### EUR/PLN: Historical vs Predicted")
    
    fig1 = go.Figure()
    
    # Add actual EUR/PLN
    fig1.add_trace(go.Scatter(
        x=df.index,
        y=df['actual_eur_pln'],
        mode='lines',
        name='EUR/PLN (Actual)',
        line=dict(color='#2E86AB', width=2),
        hovertemplate='Actual: %{y:.4f}<br>Date: %{x}<extra></extra>'
    ))
    
    # Add predicted EUR/PLN
    fig1.add_trace(go.Scatter(
        x=df.index,
        y=df['predicted_eur_pln'],
        mode='lines',
        name='EUR/PLN (Predicted)',
        line=dict(color='#F24236', width=2, dash='dash'),
        hovertemplate='Predicted: %{y:.4f}<br>Date: %{x}<extra></extra>'
    ))
    
    fig1.update_layout(
        height=400,
        showlegend=True,
        legend=dict(x=0.02, y=0.98),
        xaxis_title="Date",
        yaxis_title="Exchange Rate",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    # Bond yield spread chart
    st.markdown("### Bond Yield Spread (PL 1Y - DE 1Y)")
    
    fig2 = go.Figure()
    
    fig2.add_trace(go.Scatter(
        x=df.index,
        y=df['yield_spread'],
        mode='lines',
        name='PL-DE Spread',
        line=dict(color='#A8E6CF', width=3),
        fill='tonexty',
        hovertemplate='Spread: %{y:.2f}pp<br>Date: %{x}<extra></extra>'
    ))
    
    # Add horizontal line for current spread
    current_spread = df['yield_spread'].iloc[-1]
    fig2.add_hline(y=current_spread, line_dash="dot", line_color="red",
                   annotation_text=f"Current: {current_spread:.2f}pp")
    
    fig2.update_layout(
        height=400,
        xaxis_title="Date",
        yaxis_title="Yield Spread (pp)",
        hovermode='x'
    )
    
    st.plotly_chart(fig2, use_container_width=True)

# Latest FX vs Predicted section
st.markdown("---")
st.markdown("### 📊 Latest FX vs Predicted")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="rate-label">Actual EUR/PLN</div>
        <div class="actual-rate">{current_actual:.4f}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="rate-label">Predicted EUR/PLN</div>
        <div class="predicted-rate">{current_predicted:.4f}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    difference_color = "#28a745" if abs(difference_pct) < 1 else "#dc3545"
    st.markdown(f"""
    <div class="metric-card">
        <div class="rate-label">% Difference EUR/PLN</div>
        <div class="difference" style="color: {difference_color}">{difference_pct:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    current_spread = df['yield_spread'].iloc[-1]
    st.markdown(f"""
    <div class="metric-card">
        <div class="rate-label">Current Spread</div>
        <div class="difference">{current_spread:.2f}pp</div>
    </div>
    """, unsafe_allow_html=True)

# Statistical Analysis
st.markdown("---")
st.markdown("### 📈 Model Performance Analytics")

col1, col2 = st.columns(2)

with col1:
    # Calculate correlation and error metrics
    correlation = df['actual_eur_pln'].corr(df['predicted_eur_pln'])
    rmse = np.sqrt(np.mean((df['actual_eur_pln'] - df['predicted_eur_pln'])**2))
    mae = np.mean(np.abs(df['actual_eur_pln'] - df['predicted_eur_pln']))
    
    st.markdown(f"""
    **Model Accuracy Metrics:**
    - **Correlation**: {correlation:.3f}
    - **RMSE**: {rmse:.4f}
    - **MAE**: {mae:.4f}
    - **Current Error**: {abs(current_actual - current_predicted):.4f}
    """)

with col2:
    # Error distribution
    errors = df['actual_eur_pln'] - df['predicted_eur_pln']
    
    fig3 = go.Figure()
    fig3.add_trace(go.Histogram(
        x=errors,
        nbinsx=20,
        name='Prediction Errors',
        marker_color='lightblue',
        opacity=0.7
    ))
    
    fig3.update_layout(
        title="Prediction Error Distribution",
        xaxis_title="Error (Actual - Predicted)",
        yaxis_title="Frequency",
        height=300
    )
    
    st.plotly_chart(fig3, use_container_width=True)

# Recent trend analysis
st.markdown("---")
st.markdown("### 📊 Recent Trends (Last 30 Days)")

recent_df = df.tail(30)

col1, col2, col3 = st.columns(3)

with col1:
    recent_actual_change = recent_df['actual_eur_pln'].iloc[-1] - recent_df['actual_eur_pln'].iloc[0]
    st.metric("EUR/PLN Change (30d)", f"{recent_actual_change:.4f}", 
              f"{(recent_actual_change/recent_df['actual_eur_pln'].iloc[0]*100):.2f}%")

with col2:
    recent_spread_change = recent_df['yield_spread'].iloc[-1] - recent_df['yield_spread'].iloc[0]
    st.metric("Spread Change (30d)", f"{recent_spread_change:.2f}pp",
              f"{recent_spread_change:.2f}pp")

with col3:
    recent_error = np.mean(np.abs(recent_df['actual_eur_pln'] - recent_df['predicted_eur_pln']))
    st.metric("Avg Error (30d)", f"{recent_error:.4f}",
              f"{(recent_error/recent_df['actual_eur_pln'].mean()*100):.2f}%")

# Methodology explanation
with st.expander("🔍 Methodology & Data Sources"):
    st.markdown("""
    **Bond Spread Model:**
    - **Formula**: `Predicted_FX = Base_Rate × (1 + Yield_Spread × Sensitivity)`
    - **Sensitivity Factor**: 0.15 (1% yield spread ≈ 15% FX impact)
    - **Base Rate**: Initial EUR/PLN rate for calibration
    
    **Data Sources:**
    - **EUR/PLN Actual**: NBP (Polish Central Bank) API
    - **Bond Yields**: FRED API (Federal Reserve Economic Data)
      - Poland 1Y: IRLTLT01PLM156N
      - Germany 1Y: IRLTLT01DEM156N
    - **Update Frequency**: Daily
    
    **Model Assumptions:**
    - Interest rate parity drives long-term FX movements
    - Bond yield spreads reflect relative economic conditions
    - 1-year maturity captures medium-term expectations
    - Linear relationship between spreads and FX (can be enhanced)
    
    **Limitations:**
    - Model doesn't account for risk premium changes
    - Central bank interventions not captured
    - Short-term market sentiment ignored
    - Requires calibration with longer historical data
    """)

# Refresh button
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.8em;'>
    📊 <strong>FX Bond Spread Dashboard</strong> | 
    Data: NBP API, FRED API | 
    Model: 1Y Government Bond Spread | 
    Updated: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
    </div>
    """, 
    unsafe_allow_html=True
)
