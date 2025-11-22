import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import io

st.set_page_config(page_title="Window Forward Analyzer", layout="wide", page_icon="📊")

# ============================================================================
# FUNKCJE POMOCNICZE
# ============================================================================

def calculate_pivot_points_mt5(window_df):
    """Oblicza pivot points metodą MT5"""
    avg_high = window_df['High'].mean()
    avg_low = window_df['Low'].mean()
    avg_close = window_df['Price'].mean()
    range_hl = avg_high - avg_low
    pivot = (avg_high + avg_low + avg_close) / 3
    
    return {
        'pivot': pivot,
        'r2': pivot + range_hl,
    }

def backtest_window_forward(df, lookback_days, hold_days, stop_loss_pct, signal_direction='SELL'):
    """
    Backtest strategii window forward
    """
    df = df.copy()
    df['DayOfWeek'] = df['Date'].dt.dayofweek
    trades = []
    
    for idx in range(lookback_days, len(df)):
        current_row = df.iloc[idx]
        if current_row['DayOfWeek'] != 0:  # Tylko poniedziałki
            continue
        
        lookback_window = df.iloc[idx-lookback_days:idx]
        pivots = calculate_pivot_points_mt5(lookback_window)
        entry_price = current_row['Open']
        
        # Tylko SELL sygnały na R2
        if signal_direction == 'SELL':
            if entry_price < pivots['r2']:
                continue
            signal = 'SELL'
        else:  # BUY
            # Dla BUY używamy S2
            s2 = pivots['pivot'] - (lookback_window['High'].mean() - lookback_window['Low'].mean())
            if entry_price > s2:
                continue
            signal = 'BUY'
        
        entry_date = current_row['Date']
        exit_date = entry_date + timedelta(days=hold_days)
        
        future_dates = df[df['Date'] >= exit_date]
        if len(future_dates) == 0:
            continue
        
        exit_row = future_dates.iloc[0]
        exit_price = exit_row['Price']
        
        # Analiza window forward
        trade_period = df[(df['Date'] > entry_date) & (df['Date'] <= exit_row['Date'])].copy()
        
        if len(trade_period) == 0:
            continue
        
        days_below_entry = 0
        max_favorable_move = 0
        max_adverse_move = 0
        best_exit_price = entry_price
        worst_case_price = entry_price
        
        for _, day in trade_period.iterrows():
            if signal == 'SELL':
                if day['Price'] < entry_price:
                    days_below_entry += 1
                if day['Low'] < best_exit_price:
                    best_exit_price = day['Low']
                if day['High'] > worst_case_price:
                    worst_case_price = day['High']
                favorable = (entry_price - day['Low']) / entry_price * 100
                adverse = (day['High'] - entry_price) / entry_price * 100
            else:  # BUY
                if day['Price'] > entry_price:
                    days_below_entry += 1
                if day['High'] > best_exit_price:
                    best_exit_price = day['High']
                if day['Low'] < worst_case_price:
                    worst_case_price = day['Low']
                favorable = (day['High'] - entry_price) / entry_price * 100
                adverse = (entry_price - day['Low']) / entry_price * 100
            
            if favorable > max_favorable_move:
                max_favorable_move = favorable
            if adverse > max_adverse_move:
                max_adverse_move = adverse
        
        total_days = len(trade_period)
        
        # Stop loss
        stop_loss_hit = False
        if signal == 'SELL':
            max_loss_price = entry_price * (1 + stop_loss_pct)
            for _, day in trade_period.iterrows():
                if day['High'] >= max_loss_price:
                    stop_loss_hit = True
                    exit_price = max_loss_price
                    exit_row = day
                    break
        else:  # BUY
            max_loss_price = entry_price * (1 - stop_loss_pct)
            for _, day in trade_period.iterrows():
                if day['Low'] <= max_loss_price:
                    stop_loss_hit = True
                    exit_price = max_loss_price
                    exit_row = day
                    break
        
        # P/L
        if signal == 'SELL':
            actual_pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            best_possible_pnl = ((entry_price - best_exit_price) / entry_price) * 100
            worst_possible_pnl = ((entry_price - worst_case_price) / entry_price) * 100
        else:  # BUY
            actual_pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            best_possible_pnl = ((best_exit_price - entry_price) / entry_price) * 100
            worst_possible_pnl = ((worst_case_price - entry_price) / entry_price) * 100
        
        pct_days_below = (days_below_entry / total_days * 100) if total_days > 0 else 0
        
        trades.append({
            'entry_date': entry_date,
            'exit_date': exit_row['Date'],
            'signal': signal,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'actual_pnl_pct': actual_pnl_pct,
            'best_possible_pnl': best_possible_pnl,
            'worst_possible_pnl': worst_possible_pnl,
            'total_days': total_days,
            'days_below_entry': days_below_entry,
            'pct_days_below': pct_days_below,
            'max_favorable_move': max_favorable_move,
            'max_adverse_move': max_adverse_move,
            'stop_loss_hit': stop_loss_hit,
            'opportunity_missed': best_possible_pnl - actual_pnl_pct
        })
    
    return pd.DataFrame(trades) if trades else None

def optimize_parameters(df, signal_direction='SELL'):
    """Optymalizacja parametrów"""
    
    lookback_range = [3, 5, 7, 10, 14, 21, 30]
    hold_range = [7, 14, 21, 30, 45, 60, 90]
    sl_range = [0.01, 0.02, 0.03, 0.04, 0.05]
    
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_iterations = len(lookback_range) * len(hold_range) * len(sl_range)
    current = 0
    
    for lookback in lookback_range:
        for hold in hold_range:
            for sl in sl_range:
                current += 1
                progress_bar.progress(current / total_iterations)
                status_text.text(f"Testowanie: Lookback={lookback}, Hold={hold}, SL={sl*100:.0f}%")
                
                trades_df = backtest_window_forward(df, lookback, hold, sl, signal_direction)
                
                if trades_df is not None and len(trades_df) > 0:
                    total_return = trades_df['actual_pnl_pct'].sum()
                    win_rate = len(trades_df[trades_df['actual_pnl_pct'] > 0]) / len(trades_df) * 100
                    avg_pct_below = trades_df['pct_days_below'].mean()
                    max_favorable = trades_df['max_favorable_move'].mean()
                    sl_hit_rate = trades_df['stop_loss_hit'].sum() / len(trades_df) * 100
                    
                    cumulative_return = trades_df['actual_pnl_pct'].cumsum()
                    max_equity = cumulative_return.expanding().max()
                    drawdown = cumulative_return - max_equity
                    max_dd = drawdown.min()
                    
                    # Sharpe-like metric
                    sharpe = total_return / abs(max_dd) if max_dd != 0 else 0
                    
                    results.append({
                        'lookback': lookback,
                        'hold_days': hold,
                        'stop_loss': sl * 100,
                        'total_trades': len(trades_df),
                        'total_return': total_return,
                        'win_rate': win_rate,
                        'avg_pct_below': avg_pct_below,
                        'max_favorable': max_favorable,
                        'max_dd': max_dd,
                        'sl_hit_rate': sl_hit_rate,
                        'sharpe': sharpe
                    })
    
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(results)

# ============================================================================
# GŁÓWNA APLIKACJA
# ============================================================================

st.title("📊 Window Forward Analyzer")
st.markdown("### Analiza strategii pivot points z opcją window forward")

# Sidebar - konfiguracja
st.sidebar.header("⚙️ Konfiguracja")

# Upload pliku
uploaded_file = st.sidebar.file_uploader(
    "Wczytaj plik CSV z danymi", 
    type=['csv'],
    help="Format: Date, Price, Open, High, Low"
)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.sidebar.success(f"✅ Wczytano {len(df)} wierszy")
    
    # Próba automatycznej konwersji dat
    try:
        df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y')
    except:
        try:
            df['Date'] = pd.to_datetime(df['Date'])
        except:
            st.sidebar.error("❌ Nie można przekonwertować dat!")
            st.stop()
    
    # Konwersja kolumn numerycznych
    for col in ['Price', 'Open', 'High', 'Low']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Wyświetl przykładowe dane
    with st.sidebar.expander("📋 Podgląd danych"):
        st.dataframe(df.head())
        st.write(f"Okres: {df['Date'].min().strftime('%Y-%m-%d')} do {df['Date'].max().strftime('%Y-%m-%d')}")
else:
    st.info("👈 Wczytaj plik CSV z danymi historycznymi w panelu po lewej")
    st.markdown("""
    **Format pliku CSV:**
    ```
    Date,Price,Open,High,Low
    01/05/2015,4.2376,4.2369,4.2566,4.2322
    01/06/2015,4.2450,4.2400,4.2500,4.2350
    ...
    ```
    
    **Wymagane kolumny:**
    - `Date` - data w formacie MM/DD/YYYY lub DD/MM/YYYY
    - `Price` - cena zamknięcia
    - `Open` - cena otwarcia
    - `High` - najwyższa cena dnia
    - `Low` - najniższa cena dnia
    """)
    st.stop()

# Tabs
tab1, tab2, tab3 = st.tabs(["🎯 Analiza", "🔧 Optymalizacja", "📈 Szczegóły transakcji"])

with tab1:
    st.header("Analiza Window Forward")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Parametry strategii")
        
        signal_direction = st.selectbox(
            "Kierunek sygnału",
            ['SELL', 'BUY'],
            help="SELL = short na R2, BUY = long na S2"
        )
        
        lookback_days = st.slider(
            "Lookback period (dni)",
            min_value=3,
            max_value=30,
            value=14,
            step=1,
            help="Liczba dni do obliczenia pivot points"
        )
        
        hold_days = st.slider(
            "Holding period (dni)",
            min_value=7,
            max_value=120,
            value=60,
            step=1,
            help="Maksymalny czas trzymania pozycji"
        )
        
        stop_loss_pct = st.slider(
            "Stop Loss (%)",
            min_value=0.5,
            max_value=10.0,
            value=3.0,
            step=0.5,
            help="Maksymalna strata procentowa"
        ) / 100
        
        if st.button("🚀 Uruchom backtest", type="primary"):
            with st.spinner("Obliczam..."):
                trades_df = backtest_window_forward(
                    df, 
                    lookback_days, 
                    hold_days, 
                    stop_loss_pct,
                    signal_direction
                )
                
                if trades_df is None or len(trades_df) == 0:
                    st.error("❌ Brak transakcji dla wybranych parametrów!")
                else:
                    st.session_state['trades_df'] = trades_df
                    st.session_state['params'] = {
                        'lookback': lookback_days,
                        'hold': hold_days,
                        'sl': stop_loss_pct * 100,
                        'direction': signal_direction
                    }
                    st.success(f"✅ Znaleziono {len(trades_df)} transakcji!")
    
    with col2:
        if 'trades_df' in st.session_state:
            trades_df = st.session_state['trades_df']
            params = st.session_state['params']
            
            st.subheader(f"Wyniki backtestingu")
            st.caption(f"Lookback: {params['lookback']}d | Hold: {params['hold']}d | SL: {params['sl']:.1f}% | Direction: {params['direction']}")
            
            # Metryki
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            
            total_trades = len(trades_df)
            winning_trades = len(trades_df[trades_df['actual_pnl_pct'] > 0])
            win_rate = winning_trades / total_trades * 100
            total_return = trades_df['actual_pnl_pct'].sum()
            
            col_m1.metric("Transakcje", total_trades)
            col_m2.metric("Win Rate", f"{win_rate:.1f}%")
            col_m3.metric("Zwrot całkowity", f"{total_return:+.2f}%")
            
            avg_pct_below = trades_df['pct_days_below'].mean()
            col_m4.metric("% dni ITM", f"{avg_pct_below:.1f}%")
            
            # Dodatkowe metryki
            col_m5, col_m6, col_m7, col_m8 = st.columns(4)
            
            avg_best = trades_df['best_possible_pnl'].mean()
            avg_actual = trades_df['actual_pnl_pct'].mean()
            efficiency = (avg_actual / avg_best * 100) if avg_best != 0 else 0
            avg_missed = trades_df['opportunity_missed'].mean()
            
            col_m5.metric("Najlepszy P/L", f"{avg_best:+.2f}%")
            col_m6.metric("Faktyczny P/L", f"{avg_actual:+.2f}%")
            col_m7.metric("Efektywność", f"{efficiency:.1f}%")
            col_m8.metric("Stracona okazja", f"{avg_missed:.2f}%")
            
            # Max ruchy
            st.markdown("---")
            col_r1, col_r2, col_r3 = st.columns(3)
            
            avg_max_fav = trades_df['max_favorable_move'].mean()
            avg_max_adv = trades_df['max_adverse_move'].mean()
            sl_hit_rate = trades_df['stop_loss_hit'].sum() / total_trades * 100
            
            col_r1.metric("Max korzystny ruch", f"{avg_max_fav:.2f}%", help="Średni maksymalny zysk dostępny")
            col_r2.metric("Max niekorzystny ruch", f"{avg_max_adv:.2f}%", help="Średni maksymalny drawdown")
            col_r3.metric("Stop loss hit", f"{sl_hit_rate:.1f}%", help="% transakcji zamkniętych SL")
            
            # Wykres equity curve
            st.markdown("---")
            st.subheader("📈 Equity Curve")
            
            cumulative_return = trades_df['actual_pnl_pct'].cumsum()
            equity = 100000 * (1 + cumulative_return / 100)
            
            fig, ax = plt.subplots(figsize=(12, 5))
            ax.plot(trades_df['exit_date'], equity, 'b-', linewidth=2, label='Equity')
            ax.axhline(y=100000, color='gray', linestyle='--', alpha=0.5, label='Start')
            ax.fill_between(trades_df['exit_date'], 100000, equity, 
                           where=(equity >= 100000), alpha=0.3, color='green')
            ax.fill_between(trades_df['exit_date'], 100000, equity, 
                           where=(equity < 100000), alpha=0.3, color='red')
            ax.set_title(f'Equity Curve - {params["direction"]} Only', fontsize=13, fontweight='bold')
            ax.set_xlabel('Data')
            ax.set_ylabel('Equity ($)')
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
            
            # Histogram % dni poniżej entry
            st.markdown("---")
            col_h1, col_h2 = st.columns(2)
            
            with col_h1:
                st.subheader("📊 Rozkład % dni ITM")
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.hist(trades_df['pct_days_below'], bins=20, alpha=0.7, color='steelblue', edgecolor='black')
                ax.axvline(x=avg_pct_below, color='red', linestyle='--', linewidth=2, 
                          label=f'Średnia: {avg_pct_below:.1f}%')
                ax.set_title('% Dni "In The Money"')
                ax.set_xlabel('% dni ITM')
                ax.set_ylabel('Liczba transakcji')
                ax.legend()
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                st.pyplot(fig)
            
            with col_h2:
                st.subheader("💹 P/L Distribution")
                fig, ax = plt.subplots(figsize=(8, 5))
                colors = ['green' if x > 0 else 'red' for x in trades_df['actual_pnl_pct']]
                ax.scatter(trades_df['pct_days_below'], trades_df['actual_pnl_pct'], 
                          c=colors, alpha=0.6, s=50)
                ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
                ax.axvline(x=50, color='gray', linestyle='--', linewidth=1, alpha=0.5)
                
                corr = trades_df['pct_days_below'].corr(trades_df['actual_pnl_pct'])
                ax.set_title(f'% ITM vs P/L (corr: {corr:+.3f})')
                ax.set_xlabel('% dni ITM')
                ax.set_ylabel('Actual P/L (%)')
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                st.pyplot(fig)
            
            # Statystyki wygrane vs przegrane
            st.markdown("---")
            st.subheader("🆚 Wygrane vs Przegrane")
            
            winning = trades_df[trades_df['actual_pnl_pct'] > 0]
            losing = trades_df[trades_df['actual_pnl_pct'] <= 0]
            
            col_w1, col_w2 = st.columns(2)
            
            with col_w1:
                st.markdown("**✅ Wygrane transakcje**")
                st.write(f"Liczba: {len(winning)}")
                st.write(f"Średni % dni ITM: {winning['pct_days_below'].mean():.1f}%")
                st.write(f"Średni P/L: {winning['actual_pnl_pct'].mean():+.2f}%")
                st.write(f"Max korzystny: {winning['max_favorable_move'].mean():.2f}%")
                st.write(f"Max niekorzystny: {winning['max_adverse_move'].mean():.2f}%")
            
            with col_w2:
                st.markdown("**❌ Przegrane transakcje**")
                st.write(f"Liczba: {len(losing)}")
                st.write(f"Średni % dni ITM: {losing['pct_days_below'].mean():.1f}%")
                st.write(f"Średni P/L: {losing['actual_pnl_pct'].mean():+.2f}%")
                st.write(f"Max korzystny: {losing['max_favorable_move'].mean():.2f}%")
                st.write(f"Max niekorzystny: {losing['max_adverse_move'].mean():.2f}%")

with tab2:
    st.header("🔧 Optymalizacja Parametrów")
    st.markdown("Znajdź optymalne parametry dla Twojej strategii")
    
    opt_direction = st.selectbox(
        "Kierunek dla optymalizacji",
        ['SELL', 'BUY'],
        key='opt_direction'
    )
    
    if st.button("🚀 Rozpocznij optymalizację", type="primary"):
        st.info("⏳ Optymalizacja może potrwać kilka minut...")
        
        results_df = optimize_parameters(df, opt_direction)
        
        if len(results_df) > 0:
            st.session_state['optimization_results'] = results_df
            st.success(f"✅ Przetestowano {len(results_df)} kombinacji parametrów!")
    
    if 'optimization_results' in st.session_state:
        results_df = st.session_state['optimization_results']
        
        st.subheader("📊 Wyniki optymalizacji")
        
        # Wybór metryki do sortowania
        sort_metric = st.selectbox(
            "Sortuj według",
            ['total_return', 'sharpe', 'win_rate', 'avg_pct_below'],
            format_func=lambda x: {
                'total_return': 'Zwrot całkowity',
                'sharpe': 'Sharpe Ratio',
                'win_rate': 'Win Rate',
                'avg_pct_below': '% dni ITM'
            }[x]
        )
        
        # TOP 10
        top10 = results_df.nlargest(10, sort_metric)
        
        st.markdown("### 🏆 TOP 10 strategii")
        st.dataframe(
            top10[[' lookback', 'hold_days', 'stop_loss', 'total_trades', 'win_rate', 
                   'total_return', 'avg_pct_below', 'max_dd', 'sharpe']].style.format({
                'win_rate': '{:.1f}%',
                'total_return': '{:+.2f}%',
                'avg_pct_below': '{:.1f}%',
                'stop_loss': '{:.1f}%',
                'max_dd': '{:.2f}%',
                'sharpe': '{:.2f}'
            }),
            use_container_width=True
        )
        
        # Heatmapy
        st.markdown("---")
        st.subheader("🔥 Heatmapy")
        
        col_h1, col_h2 = st.columns(2)
        
        with col_h1:
            # Heatmapa lookback vs hold
            st.markdown("**Lookback vs Hold Days (Total Return)**")
            pivot_table = results_df.pivot_table(
                values='total_return',
                index='lookback',
                columns='hold_days',
                aggfunc='mean'
            )
            
            fig, ax = plt.subplots(figsize=(8, 6))
            sns.heatmap(pivot_table, annot=True, fmt='.1f', cmap='RdYlGn', 
                       center=0, ax=ax, cbar_kws={'label': 'Return (%)'})
            ax.set_title('Total Return (%)')
            plt.tight_layout()
            st.pyplot(fig)
        
        with col_h2:
            # Heatmapa lookback vs SL
            st.markdown("**Lookback vs Stop Loss (Total Return)**")
            pivot_table2 = results_df.pivot_table(
                values='total_return',
                index='lookback',
                columns='stop_loss',
                aggfunc='mean'
            )
            
            fig, ax = plt.subplots(figsize=(8, 6))
            sns.heatmap(pivot_table2, annot=True, fmt='.1f', cmap='RdYlGn', 
                       center=0, ax=ax, cbar_kws={'label': 'Return (%)'})
            ax.set_title('Total Return (%)')
            plt.tight_layout()
            st.pyplot(fig)
        
        # Download wyników
        st.markdown("---")
        csv = results_df.to_csv(index=False)
        st.download_button(
            label="📥 Pobierz wyniki optymalizacji (CSV)",
            data=csv,
            file_name=f"optimization_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

with tab3:
    st.header("📈 Szczegóły Transakcji")
    
    if 'trades_df' in st.session_state:
        trades_df = st.session_state['trades_df']
        
        # Filtry
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            show_type = st.selectbox(
                "Pokaż",
                ['Wszystkie', 'Tylko wygrane', 'Tylko przegrane', 'Tylko ze stop loss']
            )
        
        with col_f2:
            min_pct_itm = st.slider("Min % dni ITM", 0, 100, 0)
        
        with col_f3:
            sort_by = st.selectbox(
                "Sortuj według",
                ['entry_date', 'actual_pnl_pct', 'pct_days_below', 'opportunity_missed']
            )
        
        # Filtrowanie
        filtered_df = trades_df.copy()
        
        if show_type == 'Tylko wygrane':
            filtered_df = filtered_df[filtered_df['actual_pnl_pct'] > 0]
        elif show_type == 'Tylko przegrane':
            filtered_df = filtered_df[filtered_df['actual_pnl_pct'] <= 0]
        elif show_type == 'Tylko ze stop loss':
            filtered_df = filtered_df[filtered_df['stop_loss_hit'] == True]
        
        filtered_df = filtered_df[filtered_df['pct_days_below'] >= min_pct_itm]
        filtered_df = filtered_df.sort_values(sort_by, ascending=False)
        
        st.write(f"**Znaleziono {len(filtered_df)} transakcji**")
        
        # Tabela
        display_df = filtered_df[[
            'entry_date', 'exit_date', 'signal', 'entry_price', 'exit_price',
            'actual_pnl_pct', 'best_possible_pnl', 'opportunity_missed',
            'pct_days_below', 'max_favorable_move', 'max_adverse_move',
            'stop_loss_hit'
        ]].copy()
        
        display_df['entry_date'] = display_df['entry_date'].dt.strftime('%Y-%m-%d')
        display_df['exit_date'] = display_df['exit_date'].dt.strftime('%Y-%m-%d')
        
        st.dataframe(
            display_df.style.format({
                'entry_price': '{:.4f}',
                'exit_price': '{:.4f}',
                'actual_pnl_pct': '{:+.2f}%',
                'best_possible_pnl': '{:+.2f}%',
                'opportunity_missed': '{:.2f}%',
                'pct_days_below': '{:.1f}%',
                'max_favorable_move': '{:.2f}%',
                'max_adverse_move': '{:.2f}%'
            }).applymap(
                lambda x: 'background-color: #90EE90' if isinstance(x, str) and '+' in x and '%' in x else '',
                subset=['actual_pnl_pct']
            ).applymap(
                lambda x: 'background-color: #FFB6C6' if isinstance(x, str) and '-' in x and '%' in x else '',
                subset=['actual_pnl_pct']
            ),
            use_container_width=True,
            height=600
        )
        
        # Download
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Pobierz transakcje (CSV)",
            data=csv,
            file_name=f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("👈 Uruchom backtest w zakładce 'Analiza' aby zobaczyć szczegóły transakcji")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>📊 Window Forward Analyzer | Wersja 1.0</p>
    <p style='font-size: 12px; color: gray;'>
        Strategia pivot points z analizą window forward dla produktów walutowych
    </p>
</div>
""", unsafe_allow_html=True)
