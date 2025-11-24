import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

# Page config
st.set_page_config(
    page_title="Strategia R2 - EUR/PLN Forward",
    page_icon="🎯",
    layout="wide"
)

# Title
st.title("🎯 Strategia R2 - Pivot Points SELL")
st.markdown("Automatyczne generowanie sygnałów SELL na podstawie pivot points (14-day lookback)")

# Sidebar - Strategy selection
st.sidebar.header("⚙️ Konfiguracja Strategii")

strategy_mode = st.sidebar.radio(
    "Wybierz strategię:",
    options=[3, 6],
    format_func=lambda x: f"{x} Forwardy" + (" ✅ REKOMENDOWANE" if x == 3 else ""),
    index=0
)

# Strategy comparison in sidebar
if strategy_mode == 3:
    st.sidebar.success("""
    **3 Forwardy (REKOMENDOWANE)**
    - Start: 0, 30, 60 dni
    - Expected: +479k PLN/rok
    - Win rate: 74.8%
    - Exposure: EUR 3M per sygnał
    """)
else:
    st.sidebar.warning("""
    **6 Forwardów**
    - Start: 0, 30, 60, 90, 120, 150 dni
    - Expected: +471k PLN/rok
    - Win rate: 70.8%
    - Exposure: EUR 6M per sygnał
    - ⚠️ Forwardy 4-6 słabe
    """)

# Upload CSV
st.sidebar.header("📁 Wgraj Dane Historyczne")
uploaded_file = st.sidebar.file_uploader(
    "CSV z EUR/PLN (Date,Price,Open,High,Low)",
    type=['csv'],
    help="Format: Date,Price,Open,High,Low,Vol.,Change%"
)

spot_rate = st.sidebar.number_input("Kurs Spot EUR/PLN", value=4.2500, step=0.0001, format="%.4f")

# Functions
@st.cache_data
def parse_csv(file):
    """Parse uploaded CSV file"""
    df = pd.read_csv(file)
    
    # Try to parse Date column
    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y', errors='coerce')
    
    # Convert numeric columns
    for col in ['Price', 'Open', 'High', 'Low']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Drop rows with NaN
    df = df.dropna(subset=['Date', 'Open', 'High', 'Low', 'Price'])
    
    # Sort by date
    df = df.sort_values('Date').reset_index(drop=True)
    
    return df

def calculate_pivot_points(df, index, lookback=14):
    """Calculate pivot points (MT5 style)"""
    if index < lookback:
        return None
    
    window = df.iloc[index-lookback:index]
    
    avg_high = window['High'].mean()
    avg_low = window['Low'].mean()
    avg_close = window['Price'].mean()
    range_hl = avg_high - avg_low
    pivot = (avg_high + avg_low + avg_close) / 3
    
    return {
        'pivot': pivot,
        'r1': pivot + (pivot - avg_low),
        'r2': pivot + range_hl,
        's1': pivot - (avg_high - pivot),
        's2': pivot - range_hl
    }

def generate_r2_signals(df, mode=3):
    """Generate R2 SELL signals"""
    signals = []
    
    today = pd.Timestamp.now()
    one_year_ago = today - pd.DateOffset(years=1)
    
    for idx, row in df.iterrows():
        # Only Mondays
        if row['Date'].dayofweek != 0:
            continue
        
        # Only last 12 months
        if row['Date'] < one_year_ago:
            continue
        
        pivots = calculate_pivot_points(df, idx, 14)
        if pivots is None:
            continue
        
        # R2 SELL signal: Open >= R2
        if row['Open'] >= pivots['r2']:
            forwards = []
            
            if mode == 3:
                offsets = [0, 30, 60]
            else:
                offsets = [0, 30, 60, 90, 120, 150]
            
            for i, offset in enumerate(offsets):
                forwards.append({
                    'num': i + 1,
                    'start_offset': offset,
                    'start_date': row['Date'] + pd.DateOffset(days=offset),
                    'end_date': row['Date'] + pd.DateOffset(days=offset+60)
                })
            
            signals.append({
                'date': row['Date'],
                'open': row['Open'],
                'r2': pivots['r2'],
                'pivot': pivots['pivot'],
                'forwards': forwards
            })
    
    return signals

def calculate_active_forwards(signals):
    """Calculate currently active forwards"""
    today = pd.Timestamp.now()
    active_count = 0
    total_exposure = 0
    
    for signal in signals:
        for fwd in signal['forwards']:
            if fwd['start_date'] <= today <= fwd['end_date']:
                active_count += 1
                total_exposure += 1  # EUR 1M per forward
    
    return active_count, total_exposure

# Main app logic
if uploaded_file is not None:
    # Parse CSV
    try:
        df = parse_csv(uploaded_file)
        st.success(f"✅ Wczytano {len(df)} wierszy danych")
        
        # Generate signals
        signals = generate_r2_signals(df, strategy_mode)
        
        if len(signals) == 0:
            st.warning("⚠️ Brak sygnałów R2 w ostatnich 12 miesiącach")
        else:
            # Calculate metrics
            active_count, total_exposure = calculate_active_forwards(signals)
            
            # Backtest results
            backtest_results = {
                3: {'total': 5.00, 'per_year': 479, 'win_rate': 74.8, 'per_signal': 61},
                6: {'total': 4.95, 'per_year': 471, 'win_rate': 70.8, 'per_signal': 60}
            }
            
            results = backtest_results[strategy_mode]
            
            # Dashboard metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Sygnały R2", len(signals), help="W ostatnich 12 miesiącach")
            
            with col2:
                st.metric("Aktywne Forwardy", active_count, help="Obecnie otwarte")
            
            with col3:
                st.metric("Exposure", f"EUR {total_exposure}M", help="Łączna ekspozycja")
            
            with col4:
                st.metric("Expected P/L", f"+{results['per_year']}k PLN/rok", 
                         help="Z backtestów 2015-2025")
            
            # Tabs
            tab1, tab2, tab3, tab4 = st.tabs([
                "📈 Timeline Sygnałów", 
                "📊 Tabela Sygnałów", 
                "📉 Performance per Forward",
                "💰 Backtest Results"
            ])
            
            # TAB 1: Timeline
            with tab1:
                st.subheader("Timeline Sygnałów R2")
                
                # Expected P/L per forward
                expected_pnl = {
                    3: [0.79, 0.58, 0.26],
                    6: [0.79, 0.58, 0.26, -0.05, 0.13, -0.16]
                }
                
                # Create timeline visualization
                fig = go.Figure()
                
                colors = ['#3B82F6', '#10B981', '#8B5CF6', '#F97316', '#EC4899', '#6366F1']
                
                for sig_idx, signal in enumerate(signals):
                    y_pos = len(signals) - sig_idx
                    
                    for fwd_idx, fwd in enumerate(signal['forwards']):
                        pnl = expected_pnl[strategy_mode][fwd_idx]
                        
                        fig.add_trace(go.Scatter(
                            x=[fwd['start_date'], fwd['end_date']],
                            y=[y_pos, y_pos],
                            mode='lines',
                            line=dict(color=colors[fwd_idx], width=20),
                            name=f"FWD {fwd['num']}" if sig_idx == 0 else "",
                            legendgroup=f"fwd{fwd['num']}",
                            showlegend=sig_idx == 0,
                            hovertemplate=f"<b>FWD {fwd['num']}</b><br>" +
                                         f"Start: {fwd['start_date'].strftime('%Y-%m-%d')}<br>" +
                                         f"End: {fwd['end_date'].strftime('%Y-%m-%d')}<br>" +
                                         f"Expected P/L: {pnl:+.2f}%<br>" +
                                         f"<extra></extra>"
                        ))
                    
                    # Add signal marker
                    fig.add_trace(go.Scatter(
                        x=[signal['date']],
                        y=[y_pos],
                        mode='markers',
                        marker=dict(size=15, color='red', symbol='star'),
                        name=f"Sygnał" if sig_idx == 0 else "",
                        legendgroup="signal",
                        showlegend=sig_idx == 0,
                        hovertemplate=f"<b>Sygnał R2</b><br>" +
                                     f"Data: {signal['date'].strftime('%Y-%m-%d')}<br>" +
                                     f"Open: {signal['open']:.4f}<br>" +
                                     f"R2: {signal['r2']:.4f}<br>" +
                                     f"<extra></extra>"
                    ))
                
                fig.update_layout(
                    title=f"Timeline {strategy_mode} Forwardów (60-day windows)",
                    xaxis_title="Data",
                    yaxis_title="Sygnał",
                    height=max(400, len(signals) * 40),
                    hovermode='closest',
                    yaxis=dict(showticklabels=False)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Show signal details
                st.subheader("Szczegóły Sygnałów")
                for idx, signal in enumerate(signals):
                    with st.expander(f"Sygnał {idx+1}: {signal['date'].strftime('%Y-%m-%d')} (Open: {signal['open']:.4f}, R2: {signal['r2']:.4f})"):
                        cols = st.columns(strategy_mode)
                        for i, fwd in enumerate(signal['forwards']):
                            with cols[i]:
                                pnl = expected_pnl[strategy_mode][i]
                                pnl_pln = pnl / 100 * 1_000_000 * spot_rate
                                st.metric(
                                    f"FWD {fwd['num']} (+{fwd['start_offset']}d)",
                                    f"{pnl:+.2f}%",
                                    f"{pnl_pln:+,.0f} PLN"
                                )
            
            # TAB 2: Table
            with tab2:
                st.subheader("Szczegółowa Lista Sygnałów")
                
                table_data = []
                for idx, signal in enumerate(signals):
                    total_pnl = sum(expected_pnl[strategy_mode])
                    total_pln = total_pnl / 100 * strategy_mode * 1_000_000 * spot_rate
                    
                    table_data.append({
                        'Lp.': idx + 1,
                        'Data Sygnału': signal['date'].strftime('%Y-%m-%d'),
                        'Open': f"{signal['open']:.4f}",
                        'R2': f"{signal['r2']:.4f}",
                        'Pivot': f"{signal['pivot']:.4f}",
                        'Forwardy': strategy_mode,
                        'Exposure': f"EUR {strategy_mode}M",
                        'Expected P/L': f"{total_pln:+,.0f} PLN"
                    })
                
                df_table = pd.DataFrame(table_data)
                st.dataframe(df_table, use_container_width=True)
            
            # TAB 3: Performance per Forward
            with tab3:
                st.subheader("Performance per Forward (Backtest 2015-2025)")
                
                fwd_names = [f"FWD {i+1} ({offset}d)" for i, offset in enumerate([0, 30, 60, 90, 120, 150][:strategy_mode])]
                fwd_pnl = expected_pnl[strategy_mode]
                
                fig_perf = go.Figure()
                
                fig_perf.add_trace(go.Bar(
                    x=fwd_names,
                    y=fwd_pnl,
                    marker_color=[colors[i] for i in range(strategy_mode)],
                    text=[f"{pnl:+.2f}%" for pnl in fwd_pnl],
                    textposition='outside'
                ))
                
                fig_perf.update_layout(
                    title="Expected P/L per Forward Type",
                    xaxis_title="Forward",
                    yaxis_title="Expected P/L (%)",
                    height=400,
                    showlegend=False
                )
                
                fig_perf.add_hline(y=0, line_dash="dash", line_color="gray")
                
                st.plotly_chart(fig_perf, use_container_width=True)
                
                # Interpretation
                if strategy_mode == 6:
                    st.warning("""
                    ⚠️ **Uwaga:** Forwardy 4-6 są słabe lub ujemne:
                    - FWD 4 (90d): -0.05%
                    - FWD 5 (120d): +0.13%
                    - FWD 6 (150d): -0.16%
                    
                    **Dlatego rekomendujemy strategię 3 Forwardy!**
                    """)
            
            # TAB 4: Backtest Results
            with tab4:
                st.subheader("💰 Podsumowanie Backtestów (2015-2025)")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 3 Forwardy ✅")
                    st.metric("Total P/L (10 lat)", "+5.00M PLN")
                    st.metric("Per Rok", "+479k PLN")
                    st.metric("Win Rate", "74.8%")
                    st.metric("Per Sygnał", "+61k PLN")
                    st.success("**REKOMENDOWANE** - Lepszy wynik przy mniejszej pracy")
                
                with col2:
                    st.markdown("### 6 Forwardów")
                    st.metric("Total P/L (10 lat)", "+4.95M PLN")
                    st.metric("Per Rok", "+471k PLN")
                    st.metric("Win Rate", "70.8%")
                    st.metric("Per Sygnał", "+60k PLN")
                    st.warning("Praktycznie identyczny wynik przy 2× więcej pracy")
                
                st.divider()
                
                st.markdown("### Porównanie Strategii")
                comparison_df = pd.DataFrame({
                    'Metryka': ['Total (10 lat)', 'Per Rok', 'Win Rate', 'Per Sygnał', 'Exposure', 'Pracy'],
                    '3 Forwardy': ['+5.00M PLN', '+479k PLN', '74.8%', '+61k PLN', 'EUR 3M', '3 pozycje'],
                    '6 Forwardów': ['+4.95M PLN', '+471k PLN', '70.8%', '+60k PLN', 'EUR 6M', '6 pozycji']
                })
                st.dataframe(comparison_df, use_container_width=True)
                
                st.info("""
                **Kluczowe Wnioski:**
                - 3 forwardy dają **lepszy wynik** (+50k PLN więcej)
                - **Wyższy win rate** (74.8% vs 70.8%)
                - **Prostsze zarządzanie** (3 vs 6 pozycji)
                - **Mniejsze exposure** (EUR 3M vs EUR 6M)
                - Forwardy 4-6 prawie nie dodają wartości
                """)
                
                # Strategy Rules
                st.divider()
                st.markdown("### 📋 Zasady Strategii ROLL")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("#### 🔴 ENTRY (Day 0)")
                    st.markdown("""
                    - Poniedziałek: Open ≥ R2
                    - Otwórz 3 lub 6 forwardów
                    - EUR 1M każdy (window 60d)
                    - Start: 0, 30, 60d (+90, +120, +150d)
                    """)
                
                with col2:
                    st.markdown("#### 🟡 DAY 30 CHECK")
                    st.markdown("""
                    - Sprawdź: Close vs Entry
                    - **ITM** (Close < Entry)?
                      → ZAMKNIJ forward
                    - **OTM** (Close ≥ Entry)?
                      → ROLUJ +60 dni
                    """)
                
                with col3:
                    st.markdown("#### 🟢 DAY 60/90 EXIT")
                    st.markdown("""
                    - Zamknij wszystkie forwardy
                    - Zapisz wyniki
                    
                    **3 FWD Expected:**
                    - +61k PLN per sygnał
                    - Win rate: 74.8%
                    """)
    
    except Exception as e:
        st.error(f"❌ Błąd wczytywania danych: {str(e)}")
        st.info("Sprawdź format CSV. Powinien zawierać kolumny: Date,Price,Open,High,Low")

else:
    # No file uploaded
    st.info("👈 Wgraj plik CSV z danymi historycznymi EUR/PLN w lewym panelu")
    
    st.markdown("### 📁 Format CSV")
    st.code("""Date,Price,Open,High,Low,Vol.,Change%
11/22/2024,4.3350,4.3385,4.3433,4.3316,0,0.01%
11/21/2024,4.3363,4.3415,4.3441,4.3346,0,-0.14%
11/20/2024,4.3424,4.3381,4.3454,4.3369,0,0.09%
""", language="csv")
    
    st.markdown("### 🎯 Jak Działa Strategia")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **3 Forwardy (REKOMENDOWANE):**
        - Start: 0, 30, 60 dni
        - Window: 60 dni każdy
        - Expected: +479k PLN/rok
        - Win rate: 74.8%
        - Prostsze zarządzanie
        """)
    
    with col2:
        st.markdown("""
        **6 Forwardów:**
        - Start: 0, 30, 60, 90, 120, 150 dni
        - Window: 60 dni każdy
        - Expected: +471k PLN/rok
        - Win rate: 70.8%
        - ⚠️ Forwardy 4-6 słabe
        """)
    
    st.markdown("""
    ### 📋 Zasady ROLL
    
    1. **ENTRY:** Poniedziałek z sygnałem R2 (Open ≥ R2) → Otwórz forwardy
    2. **DAY 30:** Sprawdź ITM/OTM → Zamknij ITM lub Roluj OTM +60d
    3. **DAY 60/90:** Zamknij wszystkie forwardy
    
    **Expected Results:** +61k PLN per sygnał (3 forwardy × EUR 1M)
    """)

# Footer
st.divider()
st.caption("Strategia R2 - Backtest 2015-2025 | Pivot Points MT5 (14-day lookback)")
