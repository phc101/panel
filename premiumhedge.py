#!/usr/bin/env python3
"""
MT5 Pivot Strategy Backtester
Strategia: Kup przy S3, sprzedaj przy R3
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="Forex Pivot Strategy Backtester",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .metric-positive {
        background: #d4edda;
        border: 2px solid #28a745;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .metric-negative {
        background: #f8d7da;
        border: 2px solid #dc3545;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .trade-buy {
        color: #28a745;
        font-weight: bold;
    }
    .trade-sell {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Forex symbols mapping
FOREX_SYMBOLS = {
    'EURUSD': 'EURUSD=X',
    'GBPUSD': 'GBPUSD=X', 
    'AUDUSD': 'AUDUSD=X',
    'NZDUSD': 'NZDUSD=X',
    'USDCAD': 'USDCAD=X',
    'USDCHF': 'USDCHF=X',
    'USDJPY': 'USDJPY=X',
    'EURJPY': 'EURJPY=X',
    'GBPJPY': 'GBPJPY=X',
    'EURGBP': 'EURGBP=X',
    'CHFPLN': 'CHFPLN=X',
    'EURPLN': 'EURPLN=X',
    'USDPLN': 'USDPLN=X',
    'GBPPLN': 'GBPPLN=X'
}

class PivotBacktester:
    def __init__(self, lookback_days=7):
        self.lookback_days = lookback_days
        
    def get_forex_data(self, symbol, days=365):
        """Pobierz dane forex"""
        try:
            yf_symbol = FOREX_SYMBOLS.get(symbol, f"{symbol}=X")
            ticker = yf.Ticker(yf_symbol)
            
            # Pobierz dane
            data = ticker.history(period=f"{days}d", interval="1d")
            
            if data.empty:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days + 5)
                data = ticker.history(start=start_date, end=end_date, interval="1d")
            
            if data.empty:
                return None
            
            # Wyczyść dane
            data = data.dropna()
            
            # Usuń timezone
            if hasattr(data.index, 'tz_localize'):
                try:
                    if data.index.tz is not None:
                        data.index = data.index.tz_convert(None)
                except:
                    pass
            
            # Utwórz DataFrame
            df = pd.DataFrame({
                'Date': pd.to_datetime(data.index),
                'Open': data['Open'].astype(float),
                'High': data['High'].astype(float), 
                'Low': data['Low'].astype(float),
                'Close': data['Close'].astype(float),
                'Volume': data['Volume'].astype(float) if 'Volume' in data.columns else 0
            }).reset_index(drop=True)
            
            df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
            
            return df
            
        except Exception as e:
            st.error(f"Błąd pobierania danych: {str(e)}")
            return None
    
    def calculate_pivot_points(self, df):
        """Oblicz punkty pivot z poziomami S3 i R3"""
        if len(df) < self.lookback_days:
            return df
            
        pivot_data = []
        
        for i in range(self.lookback_days, len(df)):
            window = df.iloc[i-self.lookback_days:i]
            avg_high = window['High'].mean()
            avg_low = window['Low'].mean()
            avg_close = window['Close'].mean()
            
            pivot = (avg_high + avg_low + avg_close) / 3
            range_val = avg_high - avg_low
            
            # Standardowe poziomy
            r1 = 2 * pivot - avg_low
            r2 = pivot + range_val
            s1 = 2 * pivot - avg_high
            s2 = pivot - range_val
            
            # Dodatkowe poziomy S3 i R3
            r3 = r2 + range_val
            s3 = s2 - range_val
            
            pivot_data.append({
                'Date': df.loc[i, 'Date'],
                'Pivot': pivot,
                'R1': r1,
                'R2': r2,
                'R3': r3,
                'S1': s1,
                'S2': s2,
                'S3': s3
            })
        
        if pivot_data:
            pivot_df = pd.DataFrame(pivot_data)
            df = df.merge(pivot_df, on='Date', how='left')
        
        return df
    
    def run_backtest(self, df, initial_capital=10000, lot_size=1.0, spread_pips=2):
        """
        Uruchom backtest strategii
        Strategia: 
        - KUP gdy cena dotknie lub przekroczy S3
        - SPRZEDAJ (zamknij) gdy cena dotknie lub przekroczy R3
        """
        
        trades = []
        capital = initial_capital
        position = None  # None, 'long'
        
        for i in range(len(df)):
            row = df.iloc[i]
            
            # Pomiń jeśli brak poziomów pivot
            if pd.isna(row.get('S3')) or pd.isna(row.get('R3')):
                continue
            
            current_price = row['Close']
            current_high = row['High']
            current_low = row['Low']
            
            # Otwórz pozycję LONG gdy cena dotknie S3
            if position is None:
                # Sprawdź czy Low dotknęło lub przekroczyło S3
                if current_low <= row['S3']:
                    # Otwórz pozycję na cenie Close lub S3 (która jest wyższa)
                    entry_price = max(current_price, row['S3'])
                    
                    # Uwzględnij spread
                    entry_price_with_spread = entry_price + (spread_pips * 0.0001)
                    
                    position = {
                        'type': 'long',
                        'entry_date': row['Date'],
                        'entry_price': entry_price_with_spread,
                        'entry_s3': row['S3'],
                        'target_r3': row['R3'],
                        'lot_size': lot_size
                    }
            
            # Zamknij pozycję LONG gdy cena dotknie R3
            elif position is not None and position['type'] == 'long':
                # Sprawdź czy High dotknęło lub przekroczyło R3
                if current_high >= row['R3']:
                    # Zamknij pozycję na cenie Close lub R3 (która jest niższa)
                    exit_price = min(current_price, row['R3'])
                    
                    # Uwzględnij spread przy zamknięciu
                    exit_price_with_spread = exit_price - (spread_pips * 0.0001)
                    
                    # Oblicz profit
                    pip_value = 0.0001  # dla większości par
                    if 'JPY' in df.attrs.get('symbol', ''):
                        pip_value = 0.01
                    
                    pips_gained = (exit_price_with_spread - position['entry_price']) / pip_value
                    profit = pips_gained * pip_value * position['lot_size'] * 100000  # standardowy lot
                    
                    # Aktualizuj kapitał
                    capital += profit
                    
                    # Zapisz transakcję
                    trades.append({
                        'Entry Date': position['entry_date'],
                        'Exit Date': row['Date'],
                        'Entry Price': position['entry_price'],
                        'Exit Price': exit_price_with_spread,
                        'Entry S3': position['entry_s3'],
                        'Exit R3': row['R3'],
                        'Pips': pips_gained,
                        'Profit': profit,
                        'Capital': capital,
                        'Duration': (row['Date'] - position['entry_date']).days
                    })
                    
                    # Resetuj pozycję
                    position = None
        
        # Zamknij otwartą pozycję na końcu backtestingu
        if position is not None:
            last_row = df.iloc[-1]
            exit_price = last_row['Close'] - (spread_pips * 0.0001)
            
            pip_value = 0.0001
            if 'JPY' in df.attrs.get('symbol', ''):
                pip_value = 0.01
            
            pips_gained = (exit_price - position['entry_price']) / pip_value
            profit = pips_gained * pip_value * position['lot_size'] * 100000
            
            capital += profit
            
            trades.append({
                'Entry Date': position['entry_date'],
                'Exit Date': last_row['Date'],
                'Entry Price': position['entry_price'],
                'Exit Price': exit_price,
                'Entry S3': position['entry_s3'],
                'Exit R3': last_row.get('R3', 0),
                'Pips': pips_gained,
                'Profit': profit,
                'Capital': capital,
                'Duration': (last_row['Date'] - position['entry_date']).days
            })
        
        return pd.DataFrame(trades), capital

# Tytuł
st.title("📊 Forex Pivot Strategy Backtester")
st.markdown("**Strategia: Kup przy S3 → Sprzedaj przy R3**")

# Sidebar
st.sidebar.header("⚙️ Konfiguracja Backtestu")

# Wybór pary walutowej
major_pairs = ['EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY']
cross_pairs = ['EURJPY', 'GBPJPY', 'EURGBP']
pln_pairs = ['EURPLN', 'USDPLN', 'GBPPLN', 'CHFPLN']

pair_category = st.sidebar.radio(
    "Kategoria par:",
    ["🌍 Pary główne", "🔄 Pary krzyżowe", "🇵🇱 Pary PLN"],
    index=0
)

if pair_category == "🌍 Pary główne":
    selected_symbol = st.sidebar.selectbox("Wybierz parę:", major_pairs, index=0)
elif pair_category == "🔄 Pary krzyżowe":
    selected_symbol = st.sidebar.selectbox("Wybierz parę:", cross_pairs, index=0)
else:
    selected_symbol = st.sidebar.selectbox("Wybierz parę:", pln_pairs, index=0)

# Parametry backtestu
st.sidebar.markdown("### 💰 Parametry Backtestu")
initial_capital = st.sidebar.number_input("Kapitał początkowy ($)", 1000, 100000, 10000, 1000)
lot_size = st.sidebar.number_input("Wielkość lota", 0.01, 10.0, 1.0, 0.01)
spread_pips = st.sidebar.number_input("Spread (pips)", 0.0, 10.0, 2.0, 0.1)

st.sidebar.markdown("### 📅 Okres backtestowania")
backtest_days = st.sidebar.slider("Liczba dni wstecz", 30, 730, 365)
lookback_days = st.sidebar.slider("Okres pivot (dni)", 3, 14, 7)

# Uruchom backtest
if st.sidebar.button("🚀 Uruchom Backtest", type="primary"):
    
    with st.spinner(f"Pobieranie danych dla {selected_symbol}..."):
        backtester = PivotBacktester(lookback_days=lookback_days)
        df = backtester.get_forex_data(selected_symbol, backtest_days)
    
    if df is not None and len(df) > 0:
        st.success(f"✅ Pobrano {len(df)} dni danych")
        
        # Oblicz pivot points
        with st.spinner("Obliczanie poziomów pivot..."):
            df = backtester.calculate_pivot_points(df)
            df.attrs['symbol'] = selected_symbol
        
        # Uruchom backtest
        with st.spinner("Wykonywanie backtestu..."):
            trades_df, final_capital = backtester.run_backtest(
                df, 
                initial_capital=initial_capital,
                lot_size=lot_size,
                spread_pips=spread_pips
            )
        
        # Wyświetl wyniki
        st.markdown("## 📈 Wyniki Backtestu")
        
        # Metryki główne
        col1, col2, col3, col4 = st.columns(4)
        
        total_return = final_capital - initial_capital
        return_pct = (total_return / initial_capital) * 100
        
        with col1:
            st.metric("Kapitał końcowy", f"${final_capital:,.2f}", 
                     f"{total_return:+,.2f}")
        
        with col2:
            st.metric("Zwrot %", f"{return_pct:.2f}%",
                     "🟢" if return_pct > 0 else "🔴")
        
        with col3:
            st.metric("Liczba transakcji", len(trades_df))
        
        with col4:
            if len(trades_df) > 0:
                win_rate = (trades_df['Profit'] > 0).sum() / len(trades_df) * 100
                st.metric("Win Rate", f"{win_rate:.1f}%")
            else:
                st.metric("Win Rate", "0%")
        
        # Szczegółowe statystyki
        if len(trades_df) > 0:
            st.markdown("### 📊 Statystyki szczegółowe")
            
            col1, col2, col3 = st.columns(3)
            
            winning_trades = trades_df[trades_df['Profit'] > 0]
            losing_trades = trades_df[trades_df['Profit'] < 0]
            
            with col1:
                st.markdown("**Transakcje zyskowne**")
                st.write(f"Liczba: {len(winning_trades)}")
                if len(winning_trades) > 0:
                    st.write(f"Średni zysk: ${winning_trades['Profit'].mean():,.2f}")
                    st.write(f"Największy zysk: ${winning_trades['Profit'].max():,.2f}")
                    st.write(f"Średnie pipy: {winning_trades['Pips'].mean():.1f}")
            
            with col2:
                st.markdown("**Transakcje stratne**")
                st.write(f"Liczba: {len(losing_trades)}")
                if len(losing_trades) > 0:
                    st.write(f"Średnia strata: ${losing_trades['Profit'].mean():,.2f}")
                    st.write(f"Największa strata: ${losing_trades['Profit'].min():,.2f}")
                    st.write(f"Średnie pipy: {losing_trades['Pips'].mean():.1f}")
            
            with col3:
                st.markdown("**Ogólne**")
                st.write(f"Średni czas trwania: {trades_df['Duration'].mean():.1f} dni")
                st.write(f"Całkowite pipy: {trades_df['Pips'].sum():.1f}")
                st.write(f"Średnie pipy/trade: {trades_df['Pips'].mean():.1f}")
                
                if len(winning_trades) > 0 and len(losing_trades) > 0:
                    profit_factor = abs(winning_trades['Profit'].sum() / losing_trades['Profit'].sum())
                    st.write(f"Profit Factor: {profit_factor:.2f}")
        
            # Wykres krzywej kapitału
            st.markdown("### 💹 Krzywa kapitału")
            
            fig_capital = go.Figure()
            
            # Dodaj kapitał początkowy
            capital_curve = [initial_capital] + trades_df['Capital'].tolist()
            dates_curve = [df['Date'].iloc[0]] + trades_df['Exit Date'].tolist()
            
            fig_capital.add_trace(go.Scatter(
                x=dates_curve,
                y=capital_curve,
                mode='lines+markers',
                name='Kapitał',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6),
                fill='tonexty',
                fillcolor='rgba(31, 119, 180, 0.1)'
            ))
            
            # Dodaj linię kapitału początkowego
            fig_capital.add_hline(
                y=initial_capital,
                line_dash='dash',
                line_color='gray',
                annotation_text='Kapitał początkowy'
            )
            
            fig_capital.update_layout(
                title=f"Rozwój kapitału - {selected_symbol}",
                xaxis_title="Data",
                yaxis_title="Kapitał ($)",
                height=400,
                showlegend=True,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_capital, use_container_width=True)
            
            # Wykres ceny z poziomami pivot i transakcjami
            st.markdown("### 📊 Wykres ceny z sygnałami")
            
            # Przygotuj dane do wykresu
            chart_data = df[df['S3'].notna()].tail(min(len(df), 200))
            
            fig_price = make_subplots(
                rows=1, cols=1,
                subplot_titles=[f'{selected_symbol} - Cena z poziomami Pivot']
            )
            
            # Candlestick
            fig_price.add_trace(go.Candlestick(
                x=chart_data['Date'],
                open=chart_data['Open'],
                high=chart_data['High'],
                low=chart_data['Low'],
                close=chart_data['Close'],
                name='Cena',
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350'
            ))
            
            # Dodaj S3 i R3
            fig_price.add_trace(go.Scatter(
                x=chart_data['Date'],
                y=chart_data['S3'],
                mode='lines',
                name='S3 (Buy)',
                line=dict(color='green', width=2, dash='dot')
            ))
            
            fig_price.add_trace(go.Scatter(
                x=chart_data['Date'],
                y=chart_data['R3'],
                mode='lines',
                name='R3 (Sell)',
                line=dict(color='red', width=2, dash='dot')
            ))
            
            # Dodaj sygnały wejścia
            if len(trades_df) > 0:
                fig_price.add_trace(go.Scatter(
                    x=trades_df['Entry Date'],
                    y=trades_df['Entry Price'],
                    mode='markers',
                    name='Wejście (Buy)',
                    marker=dict(
                        size=12,
                        color='green',
                        symbol='triangle-up',
                        line=dict(width=2, color='white')
                    )
                ))
                
                # Dodaj sygnały wyjścia
                fig_price.add_trace(go.Scatter(
                    x=trades_df['Exit Date'],
                    y=trades_df['Exit Price'],
                    mode='markers',
                    name='Wyjście (Sell)',
                    marker=dict(
                        size=12,
                        color='red',
                        symbol='triangle-down',
                        line=dict(width=2, color='white')
                    )
                ))
            
            fig_price.update_layout(
                height=600,
                xaxis_rangeslider_visible=False,
                showlegend=True,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_price, use_container_width=True)
            
            # Tabela transakcji
            st.markdown("### 📝 Historia transakcji")
            
            # Formatuj DataFrame do wyświetlenia
            display_trades = trades_df.copy()
            display_trades['Entry Date'] = display_trades['Entry Date'].dt.strftime('%Y-%m-%d')
            display_trades['Exit Date'] = display_trades['Exit Date'].dt.strftime('%Y-%m-%d')
            
            for col in ['Entry Price', 'Exit Price', 'Entry S3', 'Exit R3']:
                display_trades[col] = display_trades[col].round(5)
            
            display_trades['Pips'] = display_trades['Pips'].round(1)
            display_trades['Profit'] = display_trades['Profit'].round(2)
            display_trades['Capital'] = display_trades['Capital'].round(2)
            
            # Koloruj wiersze
            def color_profit(val):
                if isinstance(val, (int, float)):
                    color = 'background-color: #d4edda' if val > 0 else 'background-color: #f8d7da'
                    return color
                return ''
            
            styled_trades = display_trades.style.applymap(
                color_profit, 
                subset=['Profit']
            )
            
            st.dataframe(styled_trades, use_container_width=True, hide_index=True)
            
            # Możliwość pobrania wyników
            csv = trades_df.to_csv(index=False)
            st.download_button(
                label="📥 Pobierz wyniki (CSV)",
                data=csv,
                file_name=f"backtest_{selected_symbol}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        else:
            st.warning("⚠️ Brak transakcji w wybranym okresie. Spróbuj zmienić parametry.")
    
    else:
        st.error("❌ Nie udało się pobrać danych. Spróbuj innej pary walutowej.")

else:
    # Instrukcje użycia
    st.markdown("""
    ## 📖 Jak używać backtestera?
    
    ### 1️⃣ Wybierz parametry w panelu bocznym:
    - **Parę walutową** (główne, krzyżowe lub PLN)
    - **Kapitał początkowy** - kwota na start
    - **Wielkość lota** - standardowo 1.0 = 100,000 jednostek
    - **Spread** - typowo 2-3 pipsy dla głównych par
    - **Okres** - ile dni wstecz testować
    
    ### 2️⃣ Naciśnij "🚀 Uruchom Backtest"
    
    ### 3️⃣ Strategia:
    - **KUPUJ** gdy cena dotknie lub spadnie poniżej poziomu **S3**
    - **SPRZEDAJ** (zamknij pozycję) gdy cena dotknie lub wzrośnie powyżej poziomu **R3**
    - Poziomy S3/R3 są obliczane na podstawie średnich z ostatnich **7 dni** (domyślnie)
    
    ### 4️⃣ Analizuj wyniki:
    - Krzywa kapitału
    - Win rate i profit factor
    - Szczegółowa historia transakcji
    - Wykres z sygnałami wejścia/wyjścia
    
    ### ⚠️ Uwagi:
    - To tylko backtest historyczny - przeszłe wyniki nie gwarantują przyszłych
    - Zawsze testuj strategię na koncie demo przed użyciem na prawdziwym
    - Uwzględnij spread i ewentualne slippage
    - Dane z Yahoo Finance mogą mieć opóźnienie ~15 minut
    
    ---
    **Gotowy do testowania? Ustaw parametry i kliknij "Uruchom Backtest"! 🚀**
    """)

# Footer
st.markdown("---")
st.markdown(f"""
**🕐 Aktualizacja:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**⚠️ Tylko do celów edukacyjnych** - Zawsze testuj na koncie demo!  
**📊 Źródło danych:** Yahoo Finance
""")
