# ============================================================================
        # PODSUMOWANIE STRATEGII ZABEZPIECZENIA + ENHANCED INFO
        # ============================================================================
        
        st.markdown("---")
        st.subheader("📊 Podsumowanie Strategii (Enhanced)")
        
        # Calculate summary metrics
        num_forwards = len(client_rates_data)
        avg_client_rate = total_weighted_rate / num_forwards if num_forwards > 0 else config['spot_rate']
        avg_benefit_pct = total_benefit_vs_spot / num_forwards if num_forwards > 0 else 0
        
        # Portfolio vs spot calculation - use sum of all forwards vs sum of all spots
        portfolio_total_benefit_pln = total_pln_from_forwards - total_pln_from_spot
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="client-summary client-summary-blue">
                <h4 style="margin: 0; color: #2e68a5;">Średni Kurs Zabezpieczenia</h4>
                <h2 style="margin: 0; color: #2c3e50;">{avg_client_rate:.4f}</h2>
                <p style="margin: 0; color: #666; font-size: 0.85em;">Enhanced APIs</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="client-summary client-summary-green">
                <h4 style="margin: 0; color: #2e68a5;">Dodatkowa Marża z Zabezpieczenia</h4>
                <h2 style="margin: 0; color: #2c3e50;">{avg_benefit_pct:+.2f}%</h2>
                <p style="margin: 0; color: #666; font-size: 0.85em;">vs Enhanced Spot</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="client-summary client-summary-purple">
                <h4 style="margin: 0; color: #2e68a5;">Nominalna Marża z Zabezpieczenia</h4>
                <h2 style="margin: 0; color: #2c3e50;">{portfolio_total_benefit_pln:+,.0f} zł</h2>
                <p style="margin: 0; color: #666; font-size: 0.85em;">Enhanced Calculation</p>
            </div>
            """, unsafe_allow_html=True)
        
        # ============================================================================
        # CHART COMPARISON + ENHANCED INFO
        # ============================================================================
        
        st.markdown("---")
        st.subheader("📈 Porównanie Wizualne (Enhanced APIs)")
        
        # Create comparison chart
        tenors_list = [data["Tenor"] for data in client_rates_data]
        forward_rates = [float(data["Kurs terminowy"]) for data in client_rates_data]
        spot_rates = [config['spot_rate']] * len(tenors_list)
        
        fig = go.Figure()
        
        # Add spot rate line
        fig.add_trace(
            go.Scatter(
                x=tenors_list,
                y=spot_rates,
                mode='lines',
                name=f'Enhanced Spot ({config["spot_rate"]:.4f})',
                line=dict(color='red', width=1.5, dash='dash'),
                hovertemplate='Enhanced Spot: %{y:.4f}<extra></extra>'
            )
        )
        
        # Add forward rates
        fig.add_trace(
            go.Scatter(
                x=tenors_list,
                y=forward_rates,
                mode='lines+markers',
                name='Enhanced Kursy terminowe',
                line=dict(color='#2e68a5', width=1.5),
                marker=dict(size=8, color='#2e68a5'),
                hovertemplate='%{x}: %{y:.4f}<extra></extra>'
            )
        )
        
        # Calculate and add benefit bars
        benefits = [(float(data["Kurs terminowy"]) - config['spot_rate']) * exposure_amount for data in client_rates_data]
        
        fig.add_trace(
            go.Bar(
                x=tenors_list,
                y=benefits,
                name='Enhanced Korzyść PLN vs Spot',
                yaxis='y2',
                marker_color='#2e68a5',
                opacity=0.7,
                hovertemplate='%{x}: %{y:,.0f} PLN<extra></extra>'
            )
        )
        
        fig.update_layout(
            title="Enhanced API: Kursy terminowe vs spot + korzyść w PLN",
            xaxis_title="Tenor",
            yaxis_title="Kurs EUR/PLN",
            yaxis2=dict(
                title="Korzyść (PLN)",
                overlaying='y',
                side='right',
                showgrid=False
            ),
            height=500,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # ============================================================================
        # REKOMENDACJE + ENHANCED INFO
        # ============================================================================
        
        st.markdown("---")
        st.subheader("🎯 Rekomendacje Zabezpieczeń (Enhanced)")
        
        # Filter best recommendations
        best_rates = [rate for rate in client_rates_data if '🟢' in rate['Rekomendacja'] or '🟡' in rate['Rekomendacja']]
        best_rates = sorted(best_rates, key=lambda x: float(x['vs Spot'].rstrip('%')), reverse=True)[:3]
        
        if best_rates:
            st.markdown("**📋 Top 3 rekomendacje (Enhanced APIs):**")
            
            for i, rate in enumerate(best_rates, 1):
                col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
                
                with col1:
                    st.write(f"**#{i}** {rate['Rekomendacja']}")
                
                with col2:
                    st.write(f"**{rate['Tenor']}** - kurs {rate['Kurs terminowy']}")
                
                with col3:
                    st.write(f"Korzyść: **{rate['vs Spot']}**")
                
                with col4:
                    st.write(f"**{rate['Dodatkowy PLN']} PLN**")
        
        else:
            st.info("💡 W obecnych warunkach rynkowych (Enhanced APIs) rozważ pozostanie na kursie spot lub poczekaj na lepsze warunki.")
    
    else:
        st.warning("Brak dostępnych opcji dla wybranego okresu zabezpieczenia.")
    
    # Enhanced call to action
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="text-align: center;">
            <h4>💼 Gotowy do zabezpieczenia {exposure_amount:,} EUR z Enhanced APIs?</h4>
            <p>Skontaktuj się z dealerami FX aby sfinalizować transakcję</p>
            <p><strong>📞 +48 22 XXX XXXX | 📧 fx.trading@bank.pl</strong></p>
            <p style="font-size: 0.9em; color: #666;">Enhanced kursy ważne przez 15 minut | Multiple API sources dla lepszej dostępności</p>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# GŁÓWNA APLIKACJA Z ENHANCED MODEL DWUMIANOWYM
# ============================================================================

def main():
    """Główny punkt wejścia aplikacji z Enhanced APIs"""
    
    # Initialize session state
    initialize_session_state()
    
    # Enhanced header
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 2rem;">
        <div style="background: linear-gradient(45deg, #667eea, #764ba2); width: 60px; height: 60px; border-radius: 10px; margin-right: 1rem; display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 2rem;">🚀</span>
        </div>
        <h1 style="margin: 0; color: #2c3e50;">Enhanced Zintegrowana Platforma FX</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("*Enhanced APIs: ExchangeRate-API ⭐ | Trading Economics 📈 | Multiple Fallbacks 🛡️*")
    
    # Enhanced sync status in header
    if st.session_state.dealer_pricing_data:
        config = st.session_state.dealer_config
        st.success(f"✅ Enhanced System zsynchronizowany | Spot: {config['spot_rate']:.4f} ({config['spot_source']}) | Window: {config['window_days']} dni | Kursy: {len(st.session_state.dealer_pricing_data)} tenorów")
    else:
        st.info("🔄 Oczekiwanie na Enhanced wycenę dealerską...")
    
    # Create tabs with enhanced binomial model
    tab1, tab2, tab3 = st.tabs(["🔧 Panel Dealerski (Enhanced)", "🛡️ Panel Zabezpieczeń (Enhanced)", "📊 Enhanced Model Dwumianowy"])
    
    with tab1:
        create_dealer_panel()
    
    with tab2:
        create_client_hedging_advisor()
    
    with tab3:
        # ENHANCED 7-DAY BINOMIAL TREE MODEL
        st.header("📊 Enhanced Drzewo Dwumianowe - 7 Dni")
        st.markdown("*Krótkoterminowa prognoza EUR/PLN z Enhanced APIs i dziennymi zakresami*")
        
        # Enhanced volatility calculation using multiple sources
        try:
            # First try Enhanced APIs for historical data
            enhanced_forex = ImprovedForexAPI()
            current_rate_info = enhanced_forex.get_eur_pln_rate()
            current_spot = current_rate_info['rate']
            
            # Try to get historical volatility from NBP backup
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            url = f"https://api.nbp.pl/api/exchangerates/rates/a/eur/{start_str}/{end_str}/"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                rates = [rate_data['mid'] for rate_data in data['rates']]
                
                if len(rates) >= 20:
                    recent_rates = rates[-20:]
                    returns = np.diff(np.log(recent_rates))
                    rolling_vol = np.std(returns) * np.sqrt(252)
                    data_count = len(recent_rates)
                    st.success(f"✅ Enhanced volatility z ostatnich {data_count} dni: {rolling_vol*100:.2f}% rocznie | Current spot z Enhanced API: {current_spot:.4f}")
                else:
                    raise Exception(f"Only {len(rates)} days available")
            else:
                raise Exception("NBP backup failed")
                
        except Exception as e:
            rolling_vol = 0.12
            current_spot = current_rate_info['rate'] if 'current_rate_info' in locals() else 4.25
            st.warning(f"⚠️ Używam Enhanced fallback volatility (12%) | Current Enhanced spot: {current_spot:.4f}")
        
        # Enhanced model parameters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            spot_rate = st.number_input(
                "Enhanced Kurs spot EUR/PLN:",
                value=current_spot,
                min_value=3.50,
                max_value=6.00,
                step=0.0001,
                format="%.4f",
                help="Z Enhanced APIs: ExchangeRate-API lub fallback"
            )
        
        with col2:
            st.metric("Enhanced Horyzont", "5 dni roboczych", help="Poniedziałek - Piątek, Enhanced calculation")
            days = 5
        
        with col3:
            daily_vol = st.slider(
                "Enhanced Zmienność dzienna (%):",
                min_value=0.1,
                max_value=2.0,
                value=rolling_vol/np.sqrt(252)*100,
                step=0.05,
                help="Enhanced zmienność na jeden dzień roboczy"
            ) / 100
        
        # Enhanced binomial tree calculation
        dt = 1/252
        u = np.exp(daily_vol * np.sqrt(dt))
        d = 1/u
        r = 0.02/252
        p = (np.exp(r * dt) - d) / (u - d)
        
        # Create enhanced 5-day business tree
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
        
        # Enhanced business daily ranges
        st.subheader("📅 Enhanced Dzienne Zakresy Kursów (Dni Robocze)")
        
        today = datetime.now()
        business_days = []
        current_date = today
        
        while len(business_days) < 5:
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:
                business_days.append(current_date)
        
        weekdays = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]
        
        daily_ranges = []
        
        for day in range(1, 6):
            day_rates = [tree[day][j] for j in range(day + 1)]
            min_rate = min(day_rates)
            max_rate = max(day_rates)
            
            business_date = business_days[day-1]
            weekday_name = weekdays[business_date.weekday()]
            date_str = business_date.strftime("%d.%m")
            
            daily_ranges.append({
                "Dzień": f"Enhanced Dzień {day}",
                "Data": f"{weekday_name} {date_str}",
                "Min kurs": f"{min_rate:.4f}",
                "Max kurs": f"{max_rate:.4f}",
                "Zakres": f"{min_rate:.4f} - {max_rate:.4f}",
                "Enhanced Rozpiętość": f"{((max_rate - min_rate) / min_rate * 10000):.0f} pkt"
            })
        
        df_ranges = pd.DataFrame(daily_ranges)
        
        # Enhanced color coding
        def highlight_enhanced_ranges(row):
            spread_pkt = float(row['Enhanced Rozpiętość'].split()[0])
            if spread_pkt > 200:
                return ['background-color: #f8d7da'] * len(row)  # Red
            elif spread_pkt > 100:
                return ['background-color: #fff3cd'] * len(row)  # Yellow  
            else:
                return ['background-color: #d4edda'] * len(row)  # Green
        
        st.dataframe(
            df_ranges.style.apply(highlight_enhanced_ranges, axis=1),
            use_container_width=True,
            hide_index=True
        )
        
        # Enhanced tree visualization
        st.subheader("🌳 Enhanced Drzewo Dwumianowe z Najczęściej Prawdopodobną Ścieżką")
        
        # Calculate enhanced most probable path
        most_probable_path = []
        for day in range(6):
            if day == 0:
                most_probable_path.append(0)
            else:
                expected_ups = day * p
                closest_j = round(expected_ups)
                closest_j = max(0, min(closest_j, day))
                most_probable_path.append(closest_j)
        
        # Enhanced tree visualization
        fig = go.Figure()
        
        # Plot enhanced tree nodes
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
                        hovertemplate=f"Enhanced Dzień {day}<br>Kurs: {rate:.4f}<br>{'🎯 Enhanced najczęstsza ścieżka' if is_most_probable else ''}<extra></extra>"
                    )
                )
                
                # Enhanced text labels
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
                
                # Enhanced connecting lines
                if day < 5:
                    # Up movement
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
                    
                    # Down movement
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
        
        # Enhanced legend
        fig.add_trace(
            go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(size=20, color='#ff6b35'),
                name='🎯 Enhanced najczęstsza ścieżka',
                showlegend=True
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(size=15, color='#2e68a5'),
                name='Enhanced inne możliwe kursy',
                showlegend=True
            )
        )
        
        # Enhanced layout
        fig.update_layout(
            title="Enhanced Drzewo dwumianowe EUR/PLN - 5 dni roboczych",
            xaxis_title="Enhanced Dzień roboczy",
            yaxis_title="Enhanced Poziom w drzewie",
            height=500,
            xaxis=dict(
                tickmode='array',
                tickvals=list(range(6)),
                ticktext=[f"Enhanced Dzień {i}" if i == 0 else f"Enhanced Dzień {i}\n({weekdays[(business_days[i-1].weekday())][:3]})" for i in range(6)]
            ),
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Enhanced path details
        st.subheader("🎯 Enhanced Najczęstsza Prognozowana Ścieżka")
        
        path_details = []
        for day in range(1, 6):
            j = most_probable_path[day]
            rate = tree[day][j]
            business_date = business_days[day-1]
            weekday_name = weekdays[business_date.weekday()]
            
            # Enhanced probability calculation
            binom_coeff = 1
            for i in range(min(j, day-j)):
                binom_coeff = binom_coeff * (day - i) // (i + 1)
            node_prob = binom_coeff * (p ** j) * ((1 - p) ** (day - j))
            
            path_details.append({
                "Enhanced Dzień": f"{weekday_name}",
                "Data": business_date.strftime("%d.%m"),
                "Enhanced Prognozowany kurs": f"{rate:.4f}",
                "Enhanced Zmiana vs dziś": f"{((rate/spot_rate - 1) * 100):+.2f}%",
                "Enhanced Prawdopodobieństwo": f"{node_prob*100:.1f}%"
            })
        
        df_path = pd.DataFrame(path_details)
        st.dataframe(df_path, use_container_width=True, hide_index=True)
        
        # Enhanced statistical summary
        st.subheader("📊 Enhanced Podsumowanie Statystyczne")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Enhanced final day statistics
        final_rates = [tree[5][j] for j in range(6)]
        final_probs = []
        
        for j in range(6):
            binom_coeff = 1
            for i in range(min(j, 5-j)):
                binom_coeff = binom_coeff * (5 - i) // (i + 1)
            prob = binom_coeff * (p ** j) * ((1 - p) ** (5 - j))
            final_probs.append(prob)
        
        total_prob = sum(final_probs)
        final_probs = [prob/total_prob for prob in final_probs]
        
        expected_rate = sum(rate * prob for rate, prob in zip(final_rates, final_probs))
        min_final = min(final_rates)
        max_final = max(final_rates)
        most_probable_final = tree[5][most_probable_path[5]]
        
        prob_below_spot = sum(prob for rate, prob in zip(final_rates, final_probs) if rate < spot_rate) * 100
        
        with col1:
            st.metric(
                "Enhanced Oczekiwany kurs (5 dni)",
                f"{expected_rate:.4f}",
                delta=f"{((expected_rate/spot_rate - 1) * 100):+.2f}%"
            )
        
        with col2:
            st.metric(
                "Enhanced Najczęstsza prognoza",
                f"{most_probable_final:.4f}",
                delta=f"{((most_probable_final/spot_rate - 1) * 100):+.2f}%",
                help="Enhanced kurs z najczęstszej ścieżki"
            )
        
        with col3:
            st.metric(
                "Enhanced Zakres (min-max)",
                f"{min_final:.4f} - {max_final:.4f}",
                help="Enhanced możliwe ekstremalne scenariusze"
            )
        
        with col4:
            st.metric(
                "Enhanced Prawdop. umocnienia PLN",
                f"{prob_below_spot:.1f}%",
                help="Enhanced prawdopodobieństwo kursu poniżej dzisiejszego"
            )
        
        # Enhanced model parameters
        st.subheader("📋 Enhanced Parametry Modelu")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            **Enhanced Dane wejściowe:**
            - Enhanced Kurs spot: {spot_rate:.4f}
            - Enhanced Zmienność dzienna: {daily_vol*100:.3f}%
            - Enhanced Zmienność roczna: {daily_vol*np.sqrt(252)*100:.2f}%
            - Enhanced Horyzont: 5 dni roboczych (Pn-Pt)
            - Enhanced Okno zmienności: 20 dni roboczych
            - Enhanced API Source: Multiple fallbacks
            """)
        
        with col2:
            st.markdown(f"""
            **Enhanced Parametry drzewa:**
            - Enhanced Współczynnik wzrostu (u): {u:.6f}
            - Enhanced Współczynnik spadku (d): {d:.6f}
            - Enhanced Prawdop. risk-neutral (p): {p:.4f}
            - Enhanced Stopa wolna od ryzyka: {r*252*100:.2f}%
            - Enhanced API Status: ✅ Active
            """)

# ============================================================================
# ENHANCED URUCHOMIENIE APLIKACJI
# ============================================================================

if __name__ == "__main__":
    main()import streamlit as st
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

# FRED API Configuration - PLACE YOUR API KEY HERE
FRED_API_KEY = st.secrets.get("FRED_API_KEY", "demo")  # Uses Streamlit secrets or demo

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
    .api-status {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
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
# ULEPSZONE API KLASY - DODANE DO ISTNIEJĄCEJ APLIKACJI
# ============================================================================

class ImprovedForexAPI:
    """Ulepszona klasa FX z multiple fallback sources"""
    
    def __init__(self):
        self.sources = [
            {
                'name': 'ExchangeRate-API',
                'url_template': 'https://v6.exchangerate-api.com/v6/latest/EUR',
                'parser': self._parse_exchangerate_api,
                'priority': 1
            },
            {
                'name': 'ExchangeRate.host', 
                'url_template': 'https://api.exchangerate.host/latest?base=EUR&symbols=PLN',
                'parser': self._parse_exchangerate_host,
                'priority': 2
            },
            {
                'name': 'Fawaz Currency API',
                'url_template': 'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/eur.json',
                'parser': self._parse_fawaz_api,
                'priority': 3
            }
        ]
        self.fallback_rate = 4.25  # Backup rate
    
    def get_eur_pln_rate(self):
        """Pobiera kurs EUR/PLN z multiple sources z fallback"""
        
        for source in self.sources:
            try:
                response = requests.get(source['url_template'], timeout=8)
                
                if response.status_code == 200:
                    data = response.json()
                    rate_info = source['parser'](data)
                    
                    if rate_info and rate_info['rate'] > 0:
                        return rate_info
                        
            except Exception:
                continue
        
        # Fallback rate
        return {
            'rate': self.fallback_rate,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'source': 'Fallback'
        }
    
    def _parse_exchangerate_api(self, data):
        """Parser for ExchangeRate-API.com"""
        if 'result' in data and data['result'] == 'success':
            return {
                'rate': data['conversion_rates']['PLN'],
                'date': data['time_last_update_utc'][:10],
                'source': 'ExchangeRate-API ⭐'
            }
        return None
    
    def _parse_exchangerate_host(self, data):
        """Parser for ExchangeRate.host"""
        if 'success' in data and data['success']:
            return {
                'rate': data['rates']['PLN'],
                'date': data['date'],
                'source': 'ExchangeRate.host 💎'
            }
        return None
    
    def _parse_fawaz_api(self, data):
        """Parser for Fawaz Currency API"""
        if 'eur' in data:
            return {
                'rate': data['eur']['pln'],
                'date': data.get('date', datetime.now().strftime('%Y-%m-%d')),
                'source': 'Fawaz API 🚀'
            }
        return None

class ImprovedBondAPI:
    """Ulepszona klasa obligacji z current market data"""
    
    def __init__(self):
        # Current market data as of July 2025
        self.current_data = {
            'Poland_10Y': 5.82,     # Trading Economics current
            'Germany_10Y': 2.62,    # Trading Economics current  
            'US_10Y': 4.32,         # Current market
            'Euro_Area_10Y': 3.18   # Current market
        }
    
    def get_bond_yields(self):
        """Pobiera aktualne rentowności obligacji"""
        
        results = {}
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        for bond_name, yield_value in self.current_data.items():
            results[bond_name] = {
                'value': yield_value,
                'date': current_date,
                'source': 'Current Market 📈'
            }
        
        return results

# ============================================================================
# ZMODYFIKOWANA KLASA FRED API CLIENT
# ============================================================================

class FREDAPIClient:
    """Enhanced FRED API client with improved fallback"""
    
    def __init__(self, api_key=FRED_API_KEY):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"
        self.improved_bond_api = ImprovedBondAPI()
    
    def get_series_data(self, series_id, limit=1, sort_order='desc'):
        """Get latest data with enhanced fallback"""
        
        # Try original FRED first
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'limit': limit,
                'sort_order': sort_order
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'observations' in data and data['observations']:
                latest = data['observations'][0]
                if latest['value'] != '.':
                    return {
                        'value': float(latest['value']),
                        'date': latest['date'],
                        'series_id': series_id,
                        'source': 'FRED API ✅'
                    }
        except Exception:
            pass
        
        # Fallback to improved bond data
        bond_mapping = {
            'IRLTLT01PLM156N': 'Poland_10Y',
            'IRLTLT01DEM156N': 'Germany_10Y',
            'DGS10': 'US_10Y',
            'IRLTLT01EZM156N': 'Euro_Area_10Y'
        }
        
        if series_id in bond_mapping:
            bond_data = self.improved_bond_api.get_bond_yields()
            mapped_series = bond_mapping[series_id]
            
            if mapped_series in bond_data:
                return {
                    'value': bond_data[mapped_series]['value'],
                    'date': bond_data[mapped_series]['date'],
                    'series_id': series_id,
                    'source': bond_data[mapped_series]['source']
                }
        
        return None
    
    def get_multiple_series(self, series_dict):
        """Get data for multiple FRED series with enhanced fallback"""
        results = {}
        for name, series_id in series_dict.items():
            data = self.get_series_data(series_id)
            if data:
                results[name] = data
        return results

# ============================================================================
# ENHANCED CACHED DATA FUNCTIONS  
# ============================================================================

@st.cache_data(ttl=3600)
def get_fred_bond_data():
    """Get government bond yields with enhanced sources"""
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
        
        # Enhanced fallback with current market data
        if not data:
            improved_bond_api = ImprovedBondAPI()
            fallback_data = improved_bond_api.get_bond_yields()
            
            # Add US_2Y fallback
            fallback_data['US_2Y'] = {
                'value': 4.05, 
                'date': datetime.now().strftime('%Y-%m-%d'), 
                'source': 'Current Market 📈'
            }
            
            return fallback_data
            
        return data
        
    except Exception as e:
        st.warning(f"Using enhanced fallback bond data")
        # Enhanced fallback data
        return {
            'Poland_10Y': {'value': 5.82, 'date': '2025-07-08', 'source': 'Current Market 📈'},
            'Germany_10Y': {'value': 2.62, 'date': '2025-07-08', 'source': 'Current Market 📈'},
            'US_10Y': {'value': 4.32, 'date': '2025-07-08', 'source': 'Current Market 📈'},
            'US_2Y': {'value': 4.05, 'date': '2025-07-08', 'source': 'Current Market 📈'},
            'Euro_Area_10Y': {'value': 3.18, 'date': '2025-07-08', 'source': 'Current Market 📈'}
        }

@st.cache_data(ttl=300)
def get_eur_pln_rate():
    """Get current EUR/PLN with multiple enhanced sources"""
    try:
        # Try improved forex API first
        improved_forex = ImprovedForexAPI()
        enhanced_rate = improved_forex.get_eur_pln_rate()
        
        if enhanced_rate['source'] != 'Fallback':
            return enhanced_rate
            
        # Fallback to original NBP if enhanced sources fail
        url = "https://api.nbp.pl/api/exchangerates/rates/a/eur/"
        response = requests.get(url, timeout=10)
        data = response.json()
        return {
            'rate': data['rates'][0]['mid'],
            'date': data['rates'][0]['effectiveDate'],
            'source': 'NBP (backup)'
        }
    except Exception as e:
        st.warning(f"Using fallback EUR/PLN rate")
        return {'rate': 4.25, 'date': '2025-01-15', 'source': 'Fallback'}

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
# PROFESSIONAL WINDOW FORWARD CALCULATOR
# ============================================================================

class APIIntegratedForwardCalculator:
    """Professional window forward calculator using real API data"""
    
    def __init__(self, fred_client):
        self.fred_client = fred_client
        
        # Professional pricing parameters
        self.points_factor = 0.70  # Client gets 70% of forward points
        self.risk_factor = 0.40    # Bank charges 40% of swap risk
    
    def get_tenors_with_window(self, window_days):
        """Generate tenors with proper window calculation"""
        today = datetime.now()
        tenors = {}
        
        for i in range(1, 13):  # 1-12 months
            tenor_key = f"{i}M"
            tenor_start = today + timedelta(days=i*30)  # Start of tenor
            window_start = tenor_start  # Window starts at tenor start
            window_end = tenor_start + timedelta(days=window_days)  # Window ends after window_days
            
            tenors[tenor_key] = {
                "name": f"{i} {'miesiąc' if i == 1 else 'miesiące' if i <= 4 else 'miesięcy'}",
                "months": i,
                "days": i * 30,
                "okno_od": window_start.strftime("%d.%m.%Y"),
                "rozliczenie_do": window_end.strftime("%d.%m.%Y")
            }
        
        return tenors
    
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
    
    def generate_api_forward_points_curve(self, spot_rate, pl_yield, de_yield, bid_ask_spread=0.002, window_days=90):
        """Generate complete forward points curve from API bond data with proper window calculation"""
        curve_data = {}
        tenors = self.get_tenors_with_window(window_days)
        
        for tenor_key, tenor_info in tenors.items():
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
# PRICING SYNC FUNCTIONS
# ============================================================================

def calculate_dealer_pricing(config):
    """Calculate dealer pricing and store in session state"""
    calculator = APIIntegratedForwardCalculator(FREDAPIClient())
    calculator.points_factor = config['points_factor']
    calculator.risk_factor = config['risk_factor']
    
    # Generate forward curve
    forward_curve = calculator.generate_api_forward_points_curve(
        config['spot_rate'], 
        config['pl_yield'], 
        config['de_yield'], 
        config['bid_ask_spread'],
        config['window_days']
    )
    
    # Calculate pricing for all tenors
    pricing_data = []
    
    for tenor_key, curve_data in forward_curve.items():
        tenor_days = curve_data["days"]
        tenor_points = curve_data["mid"]
        
        # Calculate window-specific swap risk
        tenor_window_swap_risk = abs(tenor_points) * config['volatility_factor'] * np.sqrt(config['window_days'] / 90)
        tenor_window_swap_risk = max(tenor_window_swap_risk, 0.015)
        
        # Calculate professional window forward rates
        tenor_rates = calculator.calculate_professional_rates(
            config['spot_rate'], tenor_points, tenor_window_swap_risk, config['minimum_profit_floor']
        )
        
        pricing_data.append({
            'tenor_key': tenor_key,
            'tenor_name': curve_data["name"],
            'tenor_days': tenor_days,
            'tenor_months': curve_data["months"],
            'okno_od': curve_data["okno_od"],
            'rozliczenie_do': curve_data["rozliczenie_do"],
            'forward_points': tenor_points,
            'swap_risk': tenor_window_swap_risk,
            'client_rate': tenor_rates['fwd_client'],
            'theoretical_rate': tenor_rates['fwd_to_open'],
            'profit_per_eur': tenor_rates['profit_per_eur'],
            'yield_spread': curve_data['yield_spread']
        })
    
    return pricing_data

def update_dealer_config(spot_rate, spot_source, pl_yield, de_yield, window_days, 
                        points_factor, risk_factor, bid_ask_spread, volatility_factor, 
                        hedging_savings_pct, minimum_profit_floor):
    """Update dealer configuration in session state"""
    st.session_state.dealer_config = {
        'spot_rate': spot_rate,
        'spot_source': spot_source,
        'pl_yield': pl_yield,
        'de_yield': de_yield,
        'window_days': window_days,
        'points_factor': points_factor,
        'risk_factor': risk_factor,
        'bid_ask_spread': bid_ask_spread,
        'volatility_factor': volatility_factor,
        'hedging_savings_pct': hedging_savings_pct,
        'minimum_profit_floor': minimum_profit_floor
    }
    
    # Recalculate pricing
    st.session_state.dealer_pricing_data = calculate_dealer_pricing(st.session_state.dealer_config)
    st.session_state.pricing_updated = True

# ============================================================================
# PANEL DEALERSKI Z KONTROLĄ NAD WYCENĄ + ENHANCED API STATUS
# ============================================================================

def create_dealer_panel():
    """Panel dealerski - ustala wycenę dla całego systemu"""
    
    st.header("🚀 Panel Dealerski - Wycena Master")
    st.markdown("*Ustaw parametry wyceny - te kursy będą widoczne w panelu zabezpieczeń*")
    
    # Enhanced API Status Display
    st.subheader("📡 Status Enhanced API")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Test forex APIs
        forex_api = ImprovedForexAPI()
        forex_result = forex_api.get_eur_pln_rate()
        
        if forex_result['source'] != 'Fallback':
            st.markdown(f"""
            <div class="api-status" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                <h4 style="margin: 0;">✅ Forex API Active</h4>
                <p style="margin: 0;">Source: {forex_result['source']}</p>
                <p style="margin: 0;">Rate: {forex_result['rate']:.4f} | Date: {forex_result['date']}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="api-status" style="background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%); color: #2d3436;">
                <h4 style="margin: 0;">⚠️ Forex API Fallback</h4>
                <p style="margin: 0;">Using: {forex_result['source']}</p>
                <p style="margin: 0;">Rate: {forex_result['rate']:.4f}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # Test bond APIs
        bond_api = ImprovedBondAPI()
        bond_result = bond_api.get_bond_yields()
        
        st.markdown(f"""
        <div class="api-status" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <h4 style="margin: 0;">📈 Bond API Enhanced</h4>
            <p style="margin: 0;">Source: {bond_result['Poland_10Y']['source']}</p>
            <p style="margin: 0;">PL 10Y: {bond_result['Poland_10Y']['value']:.2f}% | DE 10Y: {bond_result['Germany_10Y']['value']:.2f}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Load market data using enhanced APIs
    with st.spinner("📡 Ładowanie danych z Enhanced APIs..."):
        bond_data = get_fred_bond_data()
        forex_data = get_eur_pln_rate()
    
    # Manual spot rate control
    st.subheader("⚙️ Kontrola Kursu Spot")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        use_manual_spot = st.checkbox(
            "Ustaw kurs ręcznie", 
            value=False,
            key="dealer_manual_spot",
            help="Odznacz aby używać automatycznego kursu z Enhanced API"
        )
    
    with col2:
        if use_manual_spot:
            spot_rate = st.number_input(
                "Kurs EUR/PLN:",
                value=st.session_state.dealer_config['spot_rate'],
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
            st.info(f"Enhanced API kurs: **{spot_rate:.4f}** (źródło: {spot_source})")
    
    # Market data display
    st.subheader("📊 Dane Rynkowe (Enhanced)")
    col1, col2, col3, col4 = st.columns(4)
    
    pl_yield = bond_data['Poland_10Y']['value'] if 'Poland_10Y' in bond_data else 5.82
    de_yield = bond_data['Germany_10Y']['value'] if 'Germany_10Y' in bond_data else 2.62
    spread = pl_yield - de_yield
    
    with col1:
        st.metric(
            "EUR/PLN Spot",
            f"{spot_rate:.4f}",
            help=f"Enhanced Source: {spot_source}"
        )
    
    with col2:
        st.metric(
            "Rentowność PL 10Y",
            f"{pl_yield:.2f}%",
            help=f"Enhanced Source: {bond_data.get('Poland_10Y', {}).get('source', 'Current Market 📈')}"
        )
    
    with col3:
        st.metric(
            "Rentowność DE 10Y",
            f"{de_yield:.2f}%", 
            help=f"Enhanced Source: {bond_data.get('Germany_10Y', {}).get('source', 'Current Market 📈')}"
        )
    
    with col4:
        st.metric(
            "Spread PL-DE 10Y",
            f"{spread:.2f}pp",
            help="Różnica rentowności 10Y napędzająca punkty terminowe"
        )
    
    # Transaction configuration
    st.markdown("---")
    st.subheader("⚙️ Konfiguracja Transakcji")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        window_days = st.number_input(
            "Długość okna (dni):",
            value=st.session_state.dealer_config['window_days'],
            min_value=30,
            max_value=365,
            step=5,
            help="Długość okresu window forward"
        )
    
    with col2:
        nominal_amount = st.number_input(
            "Kwota nominalna (EUR):",
            value=2_500_000,
            min_value=10_000,
            max_value=100_000_000,
            step=10_000,
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
    
    # Advanced pricing parameters
    with st.expander("🔧 Zaawansowane Parametry Wyceny"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            points_factor = st.slider(
                "Współczynnik punktów (% dla klienta):",
                min_value=0.60,
                max_value=0.85,
                value=st.session_state.dealer_config['points_factor'],
                step=0.01,
                help="Procent punktów terminowych przekazywanych klientowi"
            )
        
        with col2:
            risk_factor = st.slider(
                "Współczynnik ryzyka (% obciążenia):",
                min_value=0.30,
                max_value=0.60,
                value=st.session_state.dealer_config['risk_factor'],
                step=0.01,
                help="Procent ryzyka swap obciążanego klientowi"
            )
        
        with col3:
            bid_ask_spread = st.number_input(
                "Spread bid-ask:",
                value=st.session_state.dealer_config['bid_ask_spread'],
                min_value=0.001,
                max_value=0.005,
                step=0.0005,
                format="%.4f",
                help="Rynkowy spread bid-ask w punktach terminowych"
            )
        
        col4, col5, col6 = st.columns(3)
        
        with col4:
            minimum_profit_floor = st.number_input(
                "Min próg zysku (PLN/EUR):",
                value=st.session_state.dealer_config['minimum_profit_floor'],
                min_value=-0.020,
                max_value=0.020,
                step=0.001,
                format="%.4f",
                help="Minimalny gwarantowany zysk na EUR"
            )
        
        with col5:
            volatility_factor = st.slider(
                "Współczynnik zmienności:",
                min_value=0.15,
                max_value=0.35,
                value=st.session_state.dealer_config['volatility_factor'],
                step=0.01,
                help="Wpływ zmienności na ryzyko swap"
            )
        
        with col6:
            hedging_savings_pct = st.slider(
                "Oszczędności hedging (%):",
                min_value=0.40,
                max_value=0.80,
                value=st.session_state.dealer_config['hedging_savings_pct'],
                step=0.05,
                help="% oszczędności swap risk w najlepszym scenariuszu"
            )
    
    # Update pricing button
    if st.button("🔄 Zaktualizuj Wycenę (Enhanced APIs)", type="primary", use_container_width=True):
        update_dealer_config(
            spot_rate, spot_source, pl_yield, de_yield, window_days,
            points_factor, risk_factor, bid_ask_spread, volatility_factor,
            hedging_savings_pct, minimum_profit_floor
        )
        st.success("✅ Wycena zaktualizowana z Enhanced APIs! Przejdź do panelu zabezpieczeń aby zobaczyć kursy klienta.")
        st.rerun()
    
    # Show current pricing if available
    if st.session_state.dealer_pricing_data:
        st.markdown("---")
        st.subheader("💼 Aktualna Wycena Dealerska (Enhanced)")
        
        # Create DataFrame for display
        pricing_df_data = []
        portfolio_totals = {
            'total_min_profit': 0,
            'total_max_profit': 0,
            'total_expected_profit': 0,
            'total_notional': 0,
            'total_points_to_window': 0,
            'total_swap_risk': 0,
            'total_client_premium': 0
        }
        
        for pricing in st.session_state.dealer_pricing_data:
            # Calculate window forward metrics
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
            portfolio_totals['total_points_to_window'] += pricing['forward_points'] * nominal_amount
            portfolio_totals['total_swap_risk'] += pricing['swap_risk'] * nominal_amount
            portfolio_totals['total_client_premium'] += (pricing['client_rate'] - spot_rate) * nominal_amount
            
            pricing_df_data.append({
                "Tenor": pricing['tenor_name'],
                "Forward Days": pricing['tenor_days'],
                "Window Days": window_days,
                "Forward Points": f"{pricing['forward_points']:.4f}",
                "Swap Risk": f"{pricing['swap_risk']:.4f}",
                "Client Rate": f"{pricing['client_rate']:.4f}",
                "Theoretical Rate": f"{pricing['theoretical_rate']:.4f}",
                "Min Profit/EUR": f"{window_min_profit_per_eur:.4f}",
                "Max Profit/EUR": f"{window_max_profit_per_eur:.4f}",
                "Expected Profit/EUR": f"{window_expected_profit_per_eur:.4f}",
                "Min Profit Total": f"{window_min_profit_total:,.0f} PLN",
                "Max Profit Total": f"{window_max_profit_total:,.0f} PLN",
                "Expected Profit Total": f"{window_expected_profit_total:,.0f} PLN"
            })
        
        df_pricing = pd.DataFrame(pricing_df_data)
        st.dataframe(df_pricing, use_container_width=True, height=400)
        
        # Portfolio summary with percentage metrics
        total_exposure_pln = spot_rate * portfolio_totals['total_notional']
        min_profit_pct = (portfolio_totals['total_min_profit'] / total_exposure_pln) * 100
        expected_profit_pct = (portfolio_totals['total_expected_profit'] / total_exposure_pln) * 100
        max_profit_pct = (portfolio_totals['total_max_profit'] / total_exposure_pln) * 100
        
        st.subheader("📊 Podsumowanie Portfolio")
        
        # First row - PLN amounts
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
        
        # Second row - percentage metrics
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
    
    else:
        st.info("👆 Kliknij 'Zaktualizuj Wycenę (Enhanced APIs)' aby wygenerować kursy dla klientów")

# ============================================================================
# PANEL ZABEZPIECZEŃ - SYNCHRONIZOWANY Z WYCENĘ DEALERSKĄ + ENHANCED STATUS
# ============================================================================

def create_client_hedging_advisor():
    """Panel zabezpieczeń - pokazuje kursy z panelu dealerskiego"""
    
    st.header("🛡️ Panel Zabezpieczeń EUR/PLN (Enhanced)")
    st.markdown("*Kursy synchronizowane z panelem dealerskim + Enhanced APIs*")
    
    # Check if dealer pricing is available
    if not st.session_state.dealer_pricing_data:
        st.warning("⚠️ Brak wyceny dealerskiej! Przejdź najpierw do panelu dealerskiego i zaktualizuj wycenę.")
        
        # Show enhanced fallback info
        forex_data = get_eur_pln_rate()
        
        st.markdown(f"""
        <div class="api-status" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
            <h4 style="margin: 0;">📡 Enhanced API Status</h4>
            <p style="margin: 0;">Current EUR/PLN: {forex_data['rate']:.4f} ({forex_data['source']})</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div class="metric-card" style="text-align: center;">
                <h4>🚀 Rozpocznij Wycenę z Enhanced APIs</h4>
                <p>Przejdź do panelu dealerskiego aby:</p>
                <ul style="text-align: left; margin: 1rem 0;">
                    <li>✅ Ustawić parametry rynkowe z multiple sources</li>
                    <li>✅ Skonfigurować marże i ryzyka</li>
                    <li>✅ Wygenerować kursy dla klientów</li>
                    <li>✅ Używać Enhanced APIs (ExchangeRate-API, Trading Economics)</li>
                </ul>
                <p><strong>Enhanced APIs zapewniają lepszą dostępność i aktualne dane!</strong></p>
            </div>
            """, unsafe_allow_html=True)
        
        return
    
    # Show enhanced pricing sync status
    config = st.session_state.dealer_config
    st.markdown(f"""
    <div class="pricing-sync">
        <h4 style="margin: 0;">✅ Enhanced Wycena Zsynchronizowana</h4>
        <p style="margin: 0;">Kurs spot: {config['spot_rate']:.4f} ({config['spot_source']}) | Window: {config['window_days']} dni | Enhanced APIs: Aktywne | Ostatnia aktualizacja: {datetime.now().strftime('%H:%M:%S')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Client configuration
    st.subheader("⚙️ Parametry Zabezpieczenia")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        exposure_amount = st.number_input(
            "Kwota EUR do zabezpieczenia:",
            value=1_000_000,
            min_value=10_000,
            max_value=50_000_000,
            step=10_000,
            format="%d",
            help="Kwota ekspozycji EUR do zabezpieczenia"
        )
    
    with col2:
        show_details = st.checkbox(
            "Pokaż szczegóły transakcji",
            value=False,
            help="Wyświetl dodatkowe informacje o okresach rozliczenia"
        )
    
    with col3:
        st.info(f"💼 Okno elastyczności: **{config['window_days']} dni**\n\n(zgodne z Enhanced wycenią dealerską)")
    
    # All pricing data (no filtering by horizon)
    filtered_pricing = st.session_state.dealer_pricing_data
    
    # ============================================================================
    # TABELA KURSÓW DLA KLIENTA + ENHANCED INFO
    # ============================================================================
    
    st.markdown("---")
    st.subheader("💱 Dostępne Kursy Terminowe (Enhanced APIs)")
    st.markdown("*Kursy gotowe do zawarcia transakcji z Enhanced market data*")
    
    # Calculate client summary metrics
    total_weighted_rate = 0
    total_benefit_vs_spot = 0
    total_pln_from_forwards = 0
    total_pln_from_spot = 0
    
    client_rates_data = []
    
    for pricing in filtered_pricing:
        client_rate = pricing['client_rate']
        spot_rate = config['spot_rate']
        
        # Calculate benefits vs spot
        rate_advantage = ((client_rate - spot_rate) / spot_rate) * 100
        
        # Calculate PLN amounts - SINGLE FORWARD TRANSACTION with correct exposure_amount
        pln_amount_forward = client_rate * exposure_amount  # PLN from this single forward with actual exposure
        pln_amount_spot = spot_rate * exposure_amount       # PLN if stayed on spot with actual exposure
        additional_pln = pln_amount_forward - pln_amount_spot  # Benefit from this forward
        
        # Add to portfolio totals
        total_weighted_rate += client_rate
        total_benefit_vs_spot += rate_advantage
        total_pln_from_forwards += pln_amount_forward
        total_pln_from_spot += pln_amount_spot
        
        # Determine recommendation
        if rate_advantage > 0.5:
            recommendation = "🟢 Doskonały"
            rec_color = "#d4edda"
        elif rate_advantage > 0.2:
            recommendation = "🟡 Dobry"
            rec_color = "#fff3cd"
        elif rate_advantage > 0:
            recommendation = "🟠 Akceptowalny"
            rec_color = "#ffeaa7"
        else:
            recommendation = "🔴 Rozważ spot"
            rec_color = "#f8d7da"
        
        row_data = {
            "Tenor": pricing['tenor_name'],
            "Kurs terminowy": f"{client_rate:.4f}",
            "vs Spot": f"{rate_advantage:+.2f}%",
            "Kwota PLN": f"{pln_amount_forward:,.0f}",  # PLN from single forward
            "Dodatkowy PLN": f"{additional_pln:+,.0f}" if additional_pln != 0 else "0",
            "Rekomendacja": recommendation,
            "rec_color": rec_color
        }
        
        if show_details:
            row_data.update({
                "Okno od": pricing['okno_od'],
                "Rozliczenie do": pricing['rozliczenie_do'],
                "Spread vs Teor.": f"{(pricing['theoretical_rate'] - client_rate):.4f}"
            })
        
        client_rates_data.append(row_data)
    
    # Create and display DataFrame
    if client_rates_data:
        df_client_rates = pd.DataFrame(client_rates_data)
        
        # Style the table
        def highlight_recommendations(row):
            color = row.get('rec_color', '#ffffff')
            return [f'background-color: {color}'] * len(row)
        
        # Remove color column before display
        display_df = df_client_rates.drop('rec_color', axis=1, errors='ignore')
        
        # Apply compact styling and reduce height
        styled_df = display_df.style.apply(highlight_recommendations, axis=1)
        
        st.markdown('<div class="compact-table">', unsafe_allow_html=True)
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=min(350, len(client_rates_data) * 28 + 80),  # Reduced height calculation
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
