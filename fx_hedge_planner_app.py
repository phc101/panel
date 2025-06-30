st.plotly_chart(fig3, use_container_width=True)

# ============================================================================
# TAB 3: USD/PLN ANALYTICS
# ============================================================================

with tab3:
    st.header("🇺🇸 USD/PLN Bond Spread Analytics")
    
    # Current market data for USD
    st.subheader("📊 Current USD/PLN Market Data")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "USD/PLN Spot", 
            f"{usd_forex_data['rate']:.4f}",
            help=f"Source: {usd_forex_data['source']} | Date: {usd_forex_data['date']}"
        )
    
    with col2:
        if 'Poland_10Y' in bond_data:
            pl_yield = bond_data['Poland_10Y']['value']
            st.metric(
                "Poland 10Y Bond", 
                f"{pl_yield:.2f}%",
                help="Polish government bond yield from FRED"
            )
        else:
            st.metric("Poland 10Y Bond", "N/A")
    
    with col3:
        if 'US_10Y' in bond_data:
            us_yield = bond_data['US_10Y']['value']
            st.metric(
                "US 10Y Treasury", 
                f"{us_yield:.2f}%",
                help="US Treasury yield from FRED"
            )
        else:
            st.metric("US 10Y Treasury", "N/A")
    
    with col4:
        if 'Poland_10Y' in bond_data and 'US_10Y' in bond_data:
            usd_spread = bond_data['Poland_10Y']['value'] - bond_data['US_10Y']['value']
            st.metric(
                "PL-US Spread", 
                f"{usd_spread:.2f} pp",
                help="Poland 10Y minus US 10Y"
            )
    
    # USD/PLN Forward Calculator
    st.markdown("---")
    st.subheader("🧮 USD/PLN Forward Calculator")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.write("**USD/PLN Parameters:**")
        
        # USD spot rate
        usd_spot_rate = st.number_input(
            "USD/PLN Spot Rate:",
            value=usd_forex_data['rate'],
            min_value=2.0,
            max_value=6.0,
            step=0.01,
            format="%.4f"
        )
        
        # Bond yields for USD
        col_pl_usd, col_us = st.columns(2)
        
        with col_pl_usd:
            default_pl_usd = bond_data['Poland_10Y']['value'] if 'Poland_10Y' in bond_data else 5.70
            pl_yield_usd = st.number_input(
                "Poland Yield (%):",
                value=default_pl_usd,
                min_value=0.0,
                max_value=20.0,
                step=0.01,
                format="%.2f",
                key="pl_yield_usd"
            )
        
        with col_us:
            default_us = bond_data['US_10Y']['value'] if 'US_10Y' in bond_data else 4.50
            us_yield = st.number_input(
                "US Yield (%):",
                value=default_us,
                min_value=0.0,
                max_value=15.0,
                step=0.01,
                format="%.2f"
            )
        
        # Time period for USD
        usd_period_choice = st.selectbox(
            "Select Period:",
            ["1M", "3M", "6M", "9M", "1Y", "2Y", "Custom Days"],
            key="usd_period"
        )
        
        if usd_period_choice == "Custom Days":
            usd_days = st.number_input("Days:", value=365, min_value=1, max_value=730, key="usd_days")
        else:
            period_days = {"1M": 30, "3M": 90, "6M": 180, "9M": 270, "1Y": 365, "2Y": 730}
            usd_days = period_days[usd_period_choice]
    
    with col2:
        st.write("**USD/PLN Results:**")
        
        # Calculate USD forward rate
        usd_forward_rate = calculate_forward_rate(usd_spot_rate, pl_yield_usd, us_yield, usd_days)
        usd_forward_points = calculate_forward_points(usd_spot_rate, usd_forward_rate)
        
        # Display USD results
        result_col1, result_col2 = st.columns(2)
        
        with result_col1:
            st.metric(
                "USD Forward Rate",
                f"{usd_forward_rate:.4f}",
                delta=f"{usd_forward_rate - usd_spot_rate:.4f}"
            )
        
        with result_col2:
            st.metric(
                "USD Forward Points",
                f"{usd_forward_points:.2f} pips"
            )
        
        # USD Analysis
        usd_annualized_premium = ((usd_forward_rate / usd_spot_rate) - 1) * (365 / usd_days) * 100
        
        if usd_forward_rate > usd_spot_rate:
            st.success(f"🔺 USD trades at **{usd_annualized_premium:.2f}% premium** annually")
        else:
            st.error(f"🔻 USD trades at **{abs(usd_annualized_premium):.2f}% discount** annually")
        
        # USD detailed metrics
        with st.expander("📈 USD Detailed Analysis"):
            st.write(f"**USD Calculation Details:**")
            st.write(f"- USD Spot Rate: {usd_spot_rate:.4f}")
            st.write(f"- USD Forward Rate: {usd_forward_rate:.4f}")
            st.write(f"- Time to Maturity: {usd_days} days ({usd_days/365:.2f} years)")
            st.write(f"- Poland Yield: {pl_yield_usd:.2f}%")
            st.write(f"- US Yield: {us_yield:.2f}%")
            st.write(f"- Yield Spread: {pl_yield_usd - us_yield:.2f} pp")
    
    # USD/PLN Forward Table
    st.markdown("---")
    st.header("📅 USD/PLN Forward Rate Table")
    
    usd_periods = [30, 90, 180, 270, 365, 730]
    usd_period_names = ["1M", "3M", "6M", "9M", "1Y", "2Y"]
    
    usd_forward_table_data = []
    for i, period_days in enumerate(usd_periods):
        usd_fw_rate = calculate_forward_rate(usd_spot_rate, pl_yield_usd, us_yield, period_days)
        usd_fw_points = calculate_forward_points(usd_spot_rate, usd_fw_rate)
        usd_annual_premium = ((usd_fw_rate / usd_spot_rate - 1) * (365 / period_days) * 100)
        
        usd_forward_table_data.append({
            "Period": usd_period_names[i],
            "Days": period_days,
            "Forward Rate": f"{usd_fw_rate:.4f}",
            "Forward Points": f"{usd_fw_points:.2f}",
            "Annual Premium": f"{usd_annual_premium:.2f}%",
            "Spread vs Spot": f"{(usd_fw_rate - usd_spot_rate):.4f}"
        })
    
    df_usd_forward = pd.DataFrame(usd_forward_table_data)
    st.dataframe(df_usd_forward, use_container_width=True)
    
    # USD Historical Analysis
    st.markdown("---")
    st.subheader("📈 USD/PLN Historical vs Predicted (6 Months)")
    
    # Generate USD historical data
    dashboard_usd = FXBondSpreadDashboard()
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)
    
    with st.spinner("📊 Loading USD historical data..."):
        try:
            # Get historical USD/PLN
            usd_pln_data = dashboard_usd.get_nbp_historical_data(start_date, end_date, 'usd')
            
            # Get bond yields (reuse from previous calls)
            pl_bonds_usd = dashboard_usd.fred_client.get_historical_data('IRLTLT01PLM156N', 
                                                                       start_date.strftime('%Y-%m-%d'), 
                                                                       end_date.strftime('%Y-%m-%d'))
            us_bonds = dashboard_usd.fred_client.get_historical_data('DGS10', 
                                                                   start_date.strftime('%Y-%m-%d'), 
                                                                   end_date.strftime('%Y-%m-%d'))
            
            if not usd_pln_data.empty and not pl_bonds_usd.empty and not us_bonds.empty:
                # Combine real data
                df_usd = usd_pln_data.copy()
                df_usd.columns = ['actual_usd_pln']
                df_usd = df_usd.join(pl_bonds_usd.rename(columns={'value': 'pl_yield'}), how='left')
                df_usd = df_usd.join(us_bonds.rename(columns={'value': 'us_yield'}), how='left')
                df_usd = df_usd.fillna(method='ffill').fillna(method='bfill')
                
                # Calculate predicted USD rates
                df_usd['predicted_usd_pln'] = df_usd.apply(
                    lambda row: dashboard_usd.calculate_predicted_fx_rate(
                        row['pl_yield'], row['us_yield'], df_usd['actual_usd_pln'].iloc[0], 'USD'
                    ), axis=1
                )
                df_usd['yield_spread'] = df_usd['pl_yield'] - df_usd['us_yield']
                st.success("✅ Using real USD market data")
            else:
                raise Exception("Insufficient USD data")
                
        except Exception as e:
            st.info("📊 Using sample USD data for demonstration")
            # Generate sample USD data
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            np.random.seed(43)  # Different seed for USD
            
            # Sample USD/PLN
            base_rate = 3.85
            trend = np.linspace(0, 0.015, len(dates))
            noise = np.cumsum(np.random.randn(len(dates)) * 0.004)
            actual_usd_pln = base_rate + trend + noise
            
            # Sample yields
            pl_yields_usd = 5.7 + np.cumsum(np.random.randn(len(dates)) * 0.01)
            us_yields = 4.5 + np.cumsum(np.random.randn(len(dates)) * 0.012)
            
            predicted_usd_pln = []
            for i in range(len(dates)):
                pred_rate = dashboard_usd.calculate_predicted_fx_rate(pl_yields_usd[i], us_yields[i], base_rate, 'USD')
                predicted_usd_pln.append(pred_rate)
            
            df_usd = pd.DataFrame({
                'actual_usd_pln': actual_usd_pln,
                'predicted_usd_pln': predicted_usd_pln,
                'pl_yield': pl_yields_usd,
                'us_yield': us_yields,
                'yield_spread': pl_yields_usd - us_yields
            }, index=dates)
    
    # USD Current values
    current_actual_usd = df_usd['actual_usd_pln'].iloc[-1]
    current_predicted_usd = df_usd['predicted_usd_pln'].iloc[-1]
    difference_pct_usd = ((current_predicted_usd - current_actual_usd) / current_actual_usd) * 100
    current_spread_usd = df_usd['yield_spread'].iloc[-1]
    
    # USD metrics display
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="rate-label">Actual USD/PLN</div>
            <div class="actual-rate">{current_actual_usd:.4f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="rate-label">Predicted USD/PLN</div>
            <div class="predicted-rate">{current_predicted_usd:.4f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        difference_color_usd = "#28a745" if abs(difference_pct_usd) < 1 else "#dc3545"
        st.markdown(f"""
        <div class="metric-card">
            <div class="rate-label">% Difference USD</div>
            <div class="difference" style="color: {difference_color_usd}">{difference_pct_usd:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="rate-label">PL-US Spread</div>
            <div class="difference">{current_spread_usd:.2f}pp</div>
        </div>
        """, unsafe_allow_html=True)
    
    # USD Charts
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**USD/PLN: Historical vs Predicted**")
        
        fig_usd1 = go.Figure()
        
        # Actual USD/PLN
        fig_usd1.add_trace(go.Scatter(
            x=df_usd.index,
            y=df_usd['actual_usd_pln'],
            mode='lines',
            name='USD/PLN (Actual)',
            line=dict(color='#2E86AB', width=3),
            hovertemplate='Actual: %{y:.4f}<br>%{x}<extra></extra>'
        ))
        
        # Predicted USD/PLN
        fig_usd1.add_trace(go.Scatter(
            x=df_usd.index,
            y=df_usd['predicted_usd_pln'],
            mode='lines',
            name='USD/PLN (Predicted)',
            line=dict(color='#F24236', width=3, dash='dash'),
            hovertemplate='Predicted: %{y:.4f}<br>%{x}<extra></extra>'
        ))
        
        fig_usd1.update_layout(
            height=450,
            showlegend=True,
            legend=dict(x=0.02, y=0.98, bgcolor='rgba(255,255,255,0.8)'),
            xaxis_title="Date",
            yaxis_title="USD/PLN Rate",
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        fig_usd1.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig_usd1.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        st.plotly_chart(fig_usd1, use_container_width=True)
    
    with col2:
        st.markdown("**Bond Yield Spread (PL 10Y - US 10Y)**")
        
        fig_usd2 = go.Figure()
        
        fig_usd2.add_trace(go.Scatter(
            x=df_usd.index,
            y=df_usd['yield_spread'],
            mode='lines',
            name='PL-US Spread',
            line=dict(color='#FFB6C1', width=4),
            fill='tozeroy',
            fillcolor='rgba(255, 182, 193, 0.3)',
            hovertemplate='Spread: %{y:.2f}pp<br>%{x}<extra></extra>'
        ))
        
        # Current spread line
        fig_usd2.add_hline(y=current_spread_usd, line_dash="dot", line_color="red", line_width=2,
                           annotation_text=f"Current: {current_spread_usd:.2f}pp",
                           annotation_position="top right")
        
        fig_usd2.update_layout(
            height=450,
            xaxis_title="Date",
            yaxis_title="Yield Spread (pp)",
            hovermode='x',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        fig_usd2.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig_usd2.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        st.plotly_chart(fig_usd2, use_container_width=True)
    
    # USD Model Performance
    st.markdown("---")
    st.subheader("📊 USD Model Performance")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # USD Calculate metrics
        usd_correlation = df_usd['actual_usd_pln'].corr(df_usd['predicted_usd_pln'])
        usd_rmse = np.sqrt(np.mean((df_usd['actual_usd_pln'] - df_usd['predicted_usd_pln'])**2))
        usd_mae = np.mean(np.abs(df_usd['actual_usd_pln'] - df_usd['predicted_usd_pln']))
        
        st.markdown(f"""
        **USD Model Accuracy:**
        - **Correlation**: {usd_correlation:.3f}
        - **RMSE**: {usd_rmse:.4f}
        - **MAE**: {usd_mae:.4f}
        - **Current Error**: {abs(current_actual_usd - current_predicted_usd):.4f}
        """)
    
    with col2:
        # USD Recent trends
        recent_df_usd = df_usd.tail(30)
        recent_actual_change_usd = recent_df_usd['actual_usd_pln'].iloc[-1] - recent_df_usd['actual_usd_pln'].iloc[0]
        recent_spread_change_usd = recent_df_usd['yield_spread'].iloc[-1] - recent_df_usd['yield_spread'].iloc[0]
        
        st.markdown(f"""
        **USD 30-Day Trends:**
        - **USD/PLN Change**: {recent_actual_change_usd:.4f}
        - **Spread Change**: {recent_spread_change_usd:.2f}pp
        - **Avg Error**: {np.mean(np.abs(recent_df_usd['actual_usd_pln'] - recent_df_usd['predicted_usd_pln'])):.4f}
        """)
    
    with col3:
        # USD Error distribution chart
        errors_usd = df_usd['actual_usd_pln'] - df_usd['predicted_usd_pln']
        
        fig_usd3 = go.Figure()
        fig_usd3.add_trace(go.Histogram(
            x=errors_usd,
            nbinsx=15,
            name='USD Prediction Errors',
            marker_color='lightcoral',
            opacity=0.7
        ))
        
        fig_usd3.update_layout(
            title="USD Error Distribution",
            xaxis_title="Error (Actual - Predicted)",
            yaxis_title="Frequency",
            height=250,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig_usd3, use_container_width=True)
    
    # EUR vs USD Comparison
    st.markdown("---")
    st.subheader("⚖️ EUR/PLN vs USD/PLN Comparison")
    
    # Load EUR data for comparison
    try:
        # Get EUR data from Tab 2 or generate it
        dashboard_eur = FXBondSpreadDashboard()
        eur_pln_data = dashboard_eur.get_nbp_historical_data(start_date, end_date, 'eur')
        
        if not eur_pln_data.empty:
            # Simple comparison chart
            fig_comparison = go.Figure()
            
            # EUR/PLN actual
            fig_comparison.add_trace(go.Scatter(
                x=eur_pln_data.index,
                y=eur_pln_data['value'],
                mode='lines',
                name='EUR/PLN (Actual)',
                line=dict(color='#1f77b4', width=2),
                yaxis='y1'
            ))
            
            # USD/PLN actual
            fig_comparison.add_trace(go.Scatter(
                x=df_usd.index,
                y=df_usd['actual_usd_pln'],
                mode='lines',
                name='USD/PLN (Actual)',
                line=dict(color='#ff7f0e', width=2),
                yaxis='y2'
            ))
            
            # Create subplot with dual y-axes
            fig_comparison.update_layout(
                title="EUR/PLN vs USD/PLN - 6 Month Comparison",
                xaxis_title="Date",
                yaxis=dict(
                    title="EUR/PLN Rate",
                    side="left",
                    color='#1f77b4'
                ),
                yaxis2=dict(
                    title="USD/PLN Rate",
                    side="right",
                    overlaying="y",
                    color='#ff7f0e'
                ),
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_comparison, use_container_width=True)
            
            # Correlation analysis
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Calculate correlation between EUR and USD vs PLN
                common_dates = eur_pln_data.index.intersection(df_usd.index)
                if len(common_dates) > 10:
                    eur_common = eur_pln_data.loc[common_dates, 'value']
                    usd_common = df_usd.loc[common_dates, 'actual_usd_pln']
                    cross_correlation = eur_common.corr(usd_common)
                    
                    st.metric(
                        "EUR vs USD Correlation",
                        f"{cross_correlation:.3f}",
                        help="Correlation between EUR/PLN and USD/PLN movements"
                    )
            
            with col2:
                # EUR recent performance
                eur_recent_change = (eur_pln_data['value'].iloc[-1] - eur_pln_data['value'].iloc[-30]) / eur_pln_data['value'].iloc[-30] * 100
                st.metric(
                    "EUR/PLN (30d %)",
                    f"{eur_recent_change:.2f}%"
                )
            
            with col3:
                # USD recent performance
                usd_recent_change = (df_usd['actual_usd_pln'].iloc[-1] - df_usd['actual_usd_pln'].iloc[-30]) / df_usd['actual_usd_pln'].iloc[-30] * 100
                st.metric(
                    "USD/PLN (30d %)",
                    f"{usd_recent_change:.2f}%"
                )
                
    except Exception as e:
        st.info("📊 EUR comparison data not available")
    
    # Currency strength analysis
    with st.expander("💪 Currency Strength Analysis"):
        st.markdown("""
        **Key Insights:**
        
        **EUR/PLN vs USD/PLN Dynamics:**
        - **Interest Rate Sensitivity**: USD/PLN typically more sensitive to rate differentials
        - **Economic Cycles**: EUR/PLN influenced by ECB policy, USD/PLN by Fed policy
        - **Risk Sentiment**: USD often strengthens during risk-off periods
        - **Trade Relations**: EUR/PLN affected by EU-Poland trade, USD/PLN by global trade
        
        **Bond Spread Interpretation:**
        - **Higher PL-DE spread**: Favors EUR strength (lower EUR/PLN)
        - **Higher PL-US spread**: Favors USD strength (lower USD/PLN)
        - **Convergence**: Spreads narrowing suggests PLN strengthening
        - **Divergence**: Spreads widening suggests PLN weakening
        
        **Trading Considerations:**
        - **Carry Trade**: Higher Polish yields attract foreign investment
        - **Central Bank Policy**: NBP vs ECB/Fed policy divergence
        - **Economic Data**: Polish GDP, inflation vs foreign counterparts
        - **Political Risk**: Polish domestic policies vs EU/US relations
        """)

# ============================================================================
# SHARED CONTROLS (Updated)
# ============================================================================import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta

# FRED API Configuration
FRED_API_KEY = "demo"  # Replace with your API key

# Page config
st.set_page_config(
    page_title="FX Trading Dashboard",
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
    .actual-rate {
        font-size: 2.2rem;
        font-weight: bold;
        color: #2E86AB;
        margin: 0;
    }
    .predicted-rate {
        font-size: 2.2rem;
        font-weight: bold;
        color: #F24236;
        margin: 0;
    }
    .rate-label {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 0.5rem;
        font-weight: 500;
    }
    .difference {
        font-size: 1.1rem;
        font-weight: bold;
        color: #28a745;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
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
    
    def get_historical_data(self, series_id, start_date, end_date):
        """Get historical data from FRED API"""
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
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
            st.warning(f"FRED historical data error for {series_id}: {e}")
            return pd.DataFrame()

# ============================================================================
# FX BOND SPREAD DASHBOARD CLASS
# ============================================================================

class FXBondSpreadDashboard:
    def __init__(self):
        self.fred_client = FREDAPIClient()
    
    def get_nbp_historical_data(self, start_date, end_date, currency='eur'):
        """Get historical currency/PLN from NBP API"""
        try:
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            url = f"https://api.nbp.pl/api/exchangerates/rates/a/{currency.lower()}/{start_str}/{end_str}/"
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
            st.warning(f"NBP historical data error for {currency.upper()}: {e}")
            return self.generate_sample_fx_data(start_date, end_date, currency)
    
    def calculate_predicted_fx_rate(self, pl_yield, foreign_yield, base_rate, currency='EUR'):
        """Calculate predicted FX rate based on bond yield spread"""
        yield_spread = pl_yield - foreign_yield
        # Different sensitivity for EUR vs USD
        spread_sensitivity = 0.15 if currency == 'EUR' else 0.18  # USD is slightly more sensitive
        predicted_rate = base_rate * (1 + yield_spread * spread_sensitivity / 100)
        return predicted_rate
    
    def generate_sample_fx_data(self, start_date, end_date, currency='eur'):
        """Generate sample currency/PLN data"""
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        np.random.seed(42)
        
        if currency.lower() == 'eur':
            base_rate = 4.24
            volatility = 0.003
        else:  # USD
            base_rate = 3.85
            volatility = 0.004  # USD typically more volatile vs PLN
        
        trend = np.linspace(0, 0.02, len(dates))
        noise = np.cumsum(np.random.randn(len(dates)) * volatility)
        values = base_rate + trend + noise
        return pd.DataFrame({'value': values}, index=dates)

# ============================================================================
# CACHED DATA FUNCTIONS
# ============================================================================

@st.cache_data(ttl=3600)
def get_fred_bond_data():
    """Get government bond yields from FRED"""
    fred_client = FREDAPIClient()
    bond_series = {
        'Poland_10Y': 'IRLTLT01PLM156N',
        'Germany_10Y': 'IRLTLT01DEM156N',
        'US_10Y': 'DGS10',
        'US_2Y': 'DGS2',
        'Euro_Area_10Y': 'IRLTLT01EZM156N'
    }
    
    data = fred_client.get_multiple_series(bond_series)
    
    # Interpolate German short-term rates
    if 'Germany_10Y' in data:
        de_10y = data['Germany_10Y']['value']
        data['Germany_9M'] = {
            'value': max(de_10y - 0.25, 0.1),
            'date': data['Germany_10Y']['date'],
            'series_id': 'Interpolated',
            'source': 'FRED + Interpolation'
        }
    
    return data

@st.cache_data(ttl=3600)
def get_fred_rates_data():
    """Get interest rate benchmarks from FRED"""
    fred_client = FREDAPIClient()
    rates_series = {
        'EURIBOR_3M': 'EUR3MTD156N',
        'Fed_Funds': 'FEDFUNDS',
        'ECB_Rate': 'IRSTCB01EZM156N'
    }
    return fred_client.get_multiple_series(rates_series)

@st.cache_data(ttl=300)
def get_eur_pln_rate():
    """Get current EUR/PLN from NBP API"""
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
        st.warning(f"NBP API error: {e}")
        return {'rate': 4.25, 'date': 'Fallback', 'source': 'Estimated'}

@st.cache_data(ttl=300)
def get_usd_pln_rate():
    """Get current USD/PLN from NBP API"""
    try:
        url = "https://api.nbp.pl/api/exchangerates/rates/a/usd/"
        response = requests.get(url, timeout=10)
        data = response.json()
        return {
            'rate': data['rates'][0]['mid'],
            'date': data['rates'][0]['effectiveDate'],
            'source': 'NBP'
        }
    except Exception as e:
        st.warning(f"NBP API error for USD: {e}")
        return {'rate': 3.85, 'date': 'Fallback', 'source': 'Estimated'}

# ============================================================================
# CALCULATION FUNCTIONS
# ============================================================================

def calculate_forward_rate(spot_rate, domestic_yield, foreign_yield, days):
    """Calculate forward rate using bond yields"""
    T = days / 365.0
    forward_rate = spot_rate * (1 + domestic_yield/100 * T) / (1 + foreign_yield/100 * T)
    return forward_rate

def calculate_forward_points(spot_rate, forward_rate):
    """Calculate forward points in pips"""
    return (forward_rate - spot_rate) * 10000

# ============================================================================
# MAIN APPLICATION
# ============================================================================

# Header
st.markdown("""
<div style="display: flex; align-items: center; margin-bottom: 2rem;">
    <div style="background: linear-gradient(45deg, #667eea, #764ba2); width: 60px; height: 60px; border-radius: 10px; margin-right: 1rem; display: flex; align-items: center; justify-content: center;">
        <span style="font-size: 2rem;">💱</span>
    </div>
    <h1 style="margin: 0; color: #2c3e50;">Professional FX Trading Dashboard</h1>
</div>
""", unsafe_allow_html=True)

st.markdown("*Advanced Forward Rate Calculator & Bond Spread Analytics*")

# Load shared data
with st.spinner("📡 Loading market data..."):
    bond_data = get_fred_bond_data()
    rates_data = get_fred_rates_data()
    forex_data = get_eur_pln_rate()
    usd_forex_data = get_usd_pln_rate()

# Main tabs
tab1, tab2 = st.tabs(["🧮 Forward Rate Calculator", "📊 Bond Spread Dashboard (EUR/PLN + USD/PLN)"])

# ============================================================================
# TAB 1: FORWARD RATE CALCULATOR
# ============================================================================

with tab1:
    st.header("🧮 Forward Rate Calculator with FRED API")
    
    # Current market data display
    st.subheader("📊 Current Market Data")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "EUR/PLN Spot", 
            f"{forex_data['rate']:.4f}",
            help=f"Source: {forex_data['source']} | Date: {forex_data['date']}"
        )
    
    with col2:
        if 'Poland_10Y' in bond_data:
            pl_yield = bond_data['Poland_10Y']['value']
            pl_date = bond_data['Poland_10Y']['date']
            st.metric(
                "Poland 10Y Bond", 
                f"{pl_yield:.2f}%",
                help=f"FRED Series: IRLTLT01PLM156N | Date: {pl_date}"
            )
        else:
            st.metric("Poland 10Y Bond", "N/A", help="Data not available")
    
    with col3:
        if 'Germany_9M' in bond_data:
            de_yield = bond_data['Germany_9M']['value']
            st.metric(
                "Germany 9M Bond", 
                f"{de_yield:.2f}%",
                help="Interpolated from 10Y German bond"
            )
        else:
            st.metric("Germany Bond", "N/A", help="Data not available")
    
    with col4:
        if 'Poland_10Y' in bond_data and 'Germany_9M' in bond_data:
            spread = bond_data['Poland_10Y']['value'] - bond_data['Germany_9M']['value']
            st.metric(
                "PL-DE Spread", 
                f"{spread:.2f} pp",
                help="Poland 10Y minus Germany 9M"
            )
    
    # Calculator interface
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("⚙️ Input Parameters")
        
        # Spot rate
        spot_rate = st.number_input(
            "EUR/PLN Spot Rate:",
            value=forex_data['rate'],
            min_value=3.0,
            max_value=6.0,
            step=0.01,
            format="%.4f"
        )
        
        # Bond yields
        st.write("**Government Bond Yields:**")
        col_pl, col_de = st.columns(2)
        
        with col_pl:
            default_pl = bond_data['Poland_10Y']['value'] if 'Poland_10Y' in bond_data else 5.70
            pl_yield = st.number_input(
                "Poland Yield (%):",
                value=default_pl,
                min_value=0.0,
                max_value=20.0,
                step=0.01,
                format="%.2f"
            )
        
        with col_de:
            default_de = bond_data['Germany_9M']['value'] if 'Germany_9M' in bond_data else 2.35
            de_yield = st.number_input(
                "Germany Yield (%):",
                value=default_de,
                min_value=-2.0,
                max_value=10.0,
                step=0.01,
                format="%.2f"
            )
        
        # Time period
        st.write("**Forward Period:**")
        period_choice = st.selectbox(
            "Select Period:",
            ["1M", "3M", "6M", "9M", "1Y", "2Y", "Custom Days"]
        )
        
        if period_choice == "Custom Days":
            days = st.number_input("Days:", value=365, min_value=1, max_value=730, help="Maximum 2 years")
        else:
            period_days = {"1M": 30, "3M": 90, "6M": 180, "9M": 270, "1Y": 365, "2Y": 730}
            days = period_days[period_choice]
    
    with col2:
        st.subheader("💰 Calculation Results")
        
        # Calculate forward rate
        forward_rate = calculate_forward_rate(spot_rate, pl_yield, de_yield, days)
        forward_points = calculate_forward_points(spot_rate, forward_rate)
        
        # Display results
        result_col1, result_col2 = st.columns(2)
        
        with result_col1:
            st.metric(
                "Forward Rate",
                f"{forward_rate:.4f}",
                delta=f"{forward_rate - spot_rate:.4f}"
            )
        
        with result_col2:
            st.metric(
                "Forward Points",
                f"{forward_points:.2f} pips"
            )
        
        # Analysis
        annualized_premium = ((forward_rate / spot_rate) - 1) * (365 / days) * 100
        
        if forward_rate > spot_rate:
            st.success(f"🔺 EUR trades at **{annualized_premium:.2f}% premium** annually")
        else:
            st.error(f"🔻 EUR trades at **{abs(annualized_premium):.2f}% discount** annually")
        
        # Detailed metrics
        with st.expander("📈 Detailed Analysis"):
            st.write(f"**Calculation Details:**")
            st.write(f"- Spot Rate: {spot_rate:.4f}")
            st.write(f"- Forward Rate: {forward_rate:.4f}")
            st.write(f"- Time to Maturity: {days} days ({days/365:.2f} years)")
            st.write(f"- Poland Yield: {pl_yield:.2f}%")
            st.write(f"- Germany Yield: {de_yield:.2f}%")
            st.write(f"- Yield Spread: {pl_yield - de_yield:.2f} pp")
    
    # Forward curve table
    st.markdown("---")
    st.header("📅 Forward Rate Table (Max 2 Years)")
    
    periods = [30, 90, 180, 270, 365, 730]
    period_names = ["1M", "3M", "6M", "9M", "1Y", "2Y"]
    
    forward_table_data = []
    for i, period_days in enumerate(periods):
        fw_rate = calculate_forward_rate(spot_rate, pl_yield, de_yield, period_days)
        fw_points = calculate_forward_points(spot_rate, fw_rate)
        annual_premium = ((fw_rate / spot_rate - 1) * (365 / period_days) * 100)
        
        forward_table_data.append({
            "Period": period_names[i],
            "Days": period_days,
            "Forward Rate": f"{fw_rate:.4f}",
            "Forward Points": f"{fw_points:.2f}",
            "Annual Premium": f"{annual_premium:.2f}%",
            "Spread vs Spot": f"{(fw_rate - spot_rate):.4f}"
        })
    
    df_forward = pd.DataFrame(forward_table_data)
    st.dataframe(df_forward, use_container_width=True)
    
    # Forward curve chart
    st.markdown("---")
    st.header("📊 Forward Curve Visualization")
    
    # Generate curve data
    curve_days = np.linspace(30, 730, 100)
    curve_forwards = [calculate_forward_rate(spot_rate, pl_yield, de_yield, d) for d in curve_days]
    curve_points = [calculate_forward_points(spot_rate, fw) for fw in curve_forwards]
    
    # Create chart
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("EUR/PLN Forward Curve", "Forward Points"),
        vertical_spacing=0.15,
        row_heights=[0.65, 0.35]
    )
    
    # Forward curve
    fig.add_trace(go.Scatter(
        x=curve_days,
        y=curve_forwards,
        mode='lines',
        name='Forward Curve',
        line=dict(color='#1f77b4', width=3),
        hovertemplate='%{x} days<br>Rate: %{y:.4f}<extra></extra>'
    ), row=1, col=1)
    
    # Spot rate line
    fig.add_hline(y=spot_rate, line_dash="dash", line_color="red", 
                  annotation_text=f"Spot: {spot_rate:.4f}", row=1)
    
    # Standard period points
    fig.add_trace(go.Scatter(
        x=periods,
        y=[calculate_forward_rate(spot_rate, pl_yield, de_yield, d) for d in periods],
        mode='markers+text',
        name='Standard Periods',
        marker=dict(color='orange', size=12),
        text=period_names,
        textposition="top center"
    ), row=1, col=1)
    
    # Forward points
    fig.add_trace(go.Scatter(
        x=curve_days,
        y=curve_points,
        mode='lines',
        name='Forward Points',
        line=dict(color='green', width=3),
        showlegend=False
    ), row=2, col=1)
    
    fig.add_hline(y=0, line_dash="dot", line_color="gray", row=2)
    
    fig.update_layout(
        title="EUR/PLN Forward Analysis - Based on FRED Bond Data",
        height=600,
        hovermode='closest'
    )
    
    fig.update_xaxes(title_text="Days to Maturity", row=2, col=1)
    fig.update_yaxes(title_text="EUR/PLN Rate", row=1, col=1)
    fig.update_yaxes(title_text="Forward Points (pips)", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# TAB 2: BOND SPREAD DASHBOARD
# ============================================================================

with tab2:
    st.header("📊 FX Bond Spread Dashboard")
    
    # Initialize dashboard
    dashboard = FXBondSpreadDashboard()
    
    # Generate historical data (6 months)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)
    
    with st.spinner("📊 Loading historical data..."):
        try:
            # Get historical EUR/PLN
            eur_pln_data = dashboard.get_nbp_historical_data(start_date, end_date)
            
            # Get bond yields
            pl_bonds = dashboard.fred_client.get_historical_data('IRLTLT01PLM156N', 
                                                               start_date.strftime('%Y-%m-%d'), 
                                                               end_date.strftime('%Y-%m-%d'))
            de_bonds = dashboard.fred_client.get_historical_data('IRLTLT01DEM156N', 
                                                               start_date.strftime('%Y-%m-%d'), 
                                                               end_date.strftime('%Y-%m-%d'))
            
            if not eur_pln_data.empty and not pl_bonds.empty and not de_bonds.empty:
                # Combine real data
                df = eur_pln_data.copy()
                df.columns = ['actual_eur_pln']
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
                st.success("✅ Using real market data")
            else:
                raise Exception("Insufficient data")
                
        except Exception as e:
            st.info("📊 Using sample data for demonstration")
            # Generate sample data
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            np.random.seed(42)
            
            # Sample EUR/PLN
            base_rate = 4.24
            trend = np.linspace(0, 0.02, len(dates))
            noise = np.cumsum(np.random.randn(len(dates)) * 0.003)
            actual_eur_pln = base_rate + trend + noise
            
            # Sample yields
            pl_yields = 5.7 + np.cumsum(np.random.randn(len(dates)) * 0.01)
            de_yields = 2.2 + np.cumsum(np.random.randn(len(dates)) * 0.008)
            
            predicted_eur_pln = []
            for i in range(len(dates)):
                pred_rate = dashboard.calculate_predicted_fx_rate(pl_yields[i], de_yields[i], base_rate)
                predicted_eur_pln.append(pred_rate)
            
            df = pd.DataFrame({
                'actual_eur_pln': actual_eur_pln,
                'predicted_eur_pln': predicted_eur_pln,
                'pl_yield': pl_yields,
                'de_yield': de_yields,
                'yield_spread': pl_yields - de_yields
            }, index=dates)
    
    # Current values
    current_actual = df['actual_eur_pln'].iloc[-1]
    current_predicted = df['predicted_eur_pln'].iloc[-1]
    difference_pct = ((current_predicted - current_actual) / current_actual) * 100
    current_spread = df['yield_spread'].iloc[-1]
    
    # Latest FX vs Predicted metrics
    st.subheader("💰 Latest FX vs Predicted")
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
            <div class="rate-label">% Difference</div>
            <div class="difference" style="color: {difference_color}">{difference_pct:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="rate-label">Current Spread</div>
            <div class="difference">{current_spread:.2f}pp</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Charts side by side with better visibility
    st.markdown("---")
    st.subheader("📈 Historical Analysis (Last 6 Months)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**EUR/PLN: Historical vs Predicted**")
        
        fig1 = go.Figure()
        
        # Actual EUR/PLN
        fig1.add_trace(go.Scatter(
            x=df.index,
            y=df['actual_eur_pln'],
            mode='lines',
            name='EUR/PLN (Actual)',
            line=dict(color='#2E86AB', width=3),
            hovertemplate='Actual: %{y:.4f}<br>%{x}<extra></extra>'
        ))
        
        # Predicted EUR/PLN
        fig1.add_trace(go.Scatter(
            x=df.index,
            y=df['predicted_eur_pln'],
            mode='lines',
            name='EUR/PLN (Predicted)',
            line=dict(color='#F24236', width=3, dash='dash'),
            hovertemplate='Predicted: %{y:.4f}<br>%{x}<extra></extra>'
        ))
        
        fig1.update_layout(
            height=450,
            showlegend=True,
            legend=dict(x=0.02, y=0.98, bgcolor='rgba(255,255,255,0.8)'),
            xaxis_title="Date",
            yaxis_title="Exchange Rate",
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        # Add grid
        fig1.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig1.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.markdown("**Bond Yield Spread (PL 1Y - DE 1Y)**")
        
        fig2 = go.Figure()
        
        fig2.add_trace(go.Scatter(
            x=df.index,
            y=df['yield_spread'],
            mode='lines',
            name='PL-DE Spread',
            line=dict(color='#A8E6CF', width=4),
            fill='tozeroy',
            fillcolor='rgba(168, 230, 207, 0.3)',
            hovertemplate='Spread: %{y:.2f}pp<br>%{x}<extra></extra>'
        ))
        
        # Current spread line
        fig2.add_hline(y=current_spread, line_dash="dot", line_color="red", line_width=2,
                       annotation_text=f"Current: {current_spread:.2f}pp",
                       annotation_position="top right")
        
        fig2.update_layout(
            height=450,
            xaxis_title="Date",
            yaxis_title="Yield Spread (pp)",
            hovermode='x',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        # Add grid
        fig2.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig2.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        st.plotly_chart(fig2, use_container_width=True)
    
    # Statistical Analysis
    st.markdown("---")
    st.subheader("📊 Model Performance Analytics")
    
    
    with col1:
        # Calculate metrics
        correlation = df['actual_eur_pln'].corr(df['predicted_eur_pln'])
        rmse = np.sqrt(np.mean((df['actual_eur_pln'] - df['predicted_eur_pln'])**2))
        mae = np.mean(np.abs(df['actual_eur_pln'] - df['predicted_eur_pln']))
        
        st.markdown(f"""
        **Model Accuracy:**
        - **Correlation**: {correlation:.3f}
        - **RMSE**: {rmse:.4f}
        - **MAE**: {mae:.4f}
        - **Current Error**: {abs(current_actual - current_predicted):.4f}
        """)
    
    with col2:
        # Recent trends
        recent_df = df.tail(30)
        recent_actual_change = recent_df['actual_eur_pln'].iloc[-1] - recent_df['actual_eur_pln'].iloc[0]
        recent_spread_change = recent_df['yield_spread'].iloc[-1] - recent_df['yield_spread'].iloc[0]
        
        st.markdown(f"""
        **30-Day Trends:**
        - **EUR/PLN Change**: {recent_actual_change:.4f}
        - **Spread Change**: {recent_spread_change:.2f}pp
        - **Avg Error**: {np.mean(np.abs(recent_df['actual_eur_pln'] - recent_df['predicted_eur_pln'])):.4f}
        """)
    
    with col3:
        # Error distribution chart
        errors = df['actual_eur_pln'] - df['predicted_eur_pln']
        
        fig3 = go.Figure()
        fig3.add_trace(go.Histogram(
            x=errors,
            nbinsx=15,
            name='Prediction Errors',
            marker_color='lightblue',
            opacity=0.7
        ))
        
        fig3.update_layout(
            title="Error Distribution",
            xaxis_title="Error (Actual - Predicted)",
            yaxis_title="Frequency",
            height=250,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig3, use_container_width=True)

# ============================================================================
# SHARED CONTROLS
# ============================================================================

st.markdown("---")

# Refresh and info controls
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("🔄 Refresh All Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with col2:
    if st.button("📊 FRED Series Info", use_container_width=True):
        with st.expander("📋 FRED Series Used", expanded=True):
            st.markdown("""
            **Bond Yields:**
            - Poland 10Y: `IRLTLT01PLM156N`
            - Germany 10Y: `IRLTLT01DEM156N`
            - US 10Y: `DGS10`
            - US 2Y: `DGS2`
            
            **Interest Rates:**
            - EURIBOR 3M: `EUR3MTD156N`
            - Fed Funds: `FEDFUNDS`
            - ECB Rate: `IRSTCB01EZM156N`
            
            **FX Rates:**
            - EUR/PLN: NBP API
            - USD/PLN: NBP API
            """)

with col3:
    if st.button("ℹ️ Methodology", use_container_width=True):
        with st.expander("🔬 Calculation Methods", expanded=True):
            st.markdown("""
            **Forward Rate Formula (Both Currencies):**
            ```
            Forward = Spot × (1 + r_PL × T) / (1 + r_Foreign × T)
            ```
            
            **Bond Spread Models:**
            ```
            EUR: Predicted_FX = Base_Rate × (1 + Spread × 0.15)
            USD: Predicted_FX = Base_Rate × (1 + Spread × 0.18)
            ```
            
            **Data Sources:**
            - **EUR/PLN & USD/PLN**: NBP API (Polish Central Bank)
            - **Bond Yields**: FRED API (Federal Reserve Economic Data)
            - **Interpolation**: German 9M = German 10Y - 25bp
            
            **Model Differences:**
            - **EUR Model**: 15% sensitivity (more stable)
            - **USD Model**: 18% sensitivity (more volatile)
            - **Base Rates**: EUR ~4.24, USD ~3.85
            
            **Update Frequency:**
            - Bond data: 1 hour cache
            - FX data: 5 minute cache
            - Historical: Daily
            """)

# Performance note
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: gray; font-size: 0.8em; padding: 1rem; border-top: 1px solid #eee;'>
    💱 <strong>Professional FX Trading Dashboard</strong><br>
    📊 Real-time data: NBP API, FRED API | 🧮 Forward Calculator | 📈 Bond Spread Analytics | 🇺🇸 USD/PLN Analytics<br>
    ⏰ Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
    🔗 <a href="https://fred.stlouisfed.org/docs/api/" target="_blank">FRED API Docs</a><br>
    ⚠️ <em>For educational and analytical purposes - not financial advice</em>
    </div>
    """, 
    unsafe_allow_html=True
)
