"""
Fibonacci 0.618 → 1.618 Backtester - Streamlit App

Usage:
    pip install yfinance pandas numpy matplotlib streamlit plotly
    streamlit run fib_streamlit.py
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Fibonacci Backtester",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #0d0d1a; }
    .metric-card {
        background: #1a1a2e;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        border: 1px solid #333;
    }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR SETTINGS
# ─────────────────────────────────────────────
st.sidebar.title("⚙️ Ustawienia")

ticker = st.sidebar.selectbox(
    "Para walutowa",
    ["PLN=X", "EURUSD=X", "GBPUSD=X", "EURPLN=X", "USDJPY=X"],
    index=0
)

period = st.sidebar.selectbox(
    "Okres historyczny",
    ["6mo", "1y", "2y", "5y"],
    index=1
)

interval = st.sidebar.selectbox(
    "Interwał",
    ["1h", "1d"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.subheader("Parametry Fibonacciego")

swing_window = st.sidebar.slider("Okno swingów (bary)", 5, 30, 10)
entry_fib = st.sidebar.slider("Poziom wejścia (retracement)", 0.50, 0.786, 0.618, 0.001, format="%.3f")
stop_fib = st.sidebar.slider("Stop Loss (retracement)", 0.618, 0.90, 0.786, 0.001, format="%.3f")
target_fib = st.sidebar.slider("Take Profit (extension)", 1.272, 2.618, 1.618, 0.001, format="%.3f")
fib_zone = st.sidebar.slider("Tolerancja strefy wejścia (%)", 0.1, 3.0, 1.0, 0.1) / 100
min_impulse = st.sidebar.slider("Minimalny impuls (%)", 0.1, 2.0, 0.5, 0.1) / 100

# ─────────────────────────────────────────────
# FUNCTIONS
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data(ticker, period, interval):
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df[['Open', 'High', 'Low', 'Close']].dropna()

def find_swings(df, window):
    highs, lows = [], []
    for i in range(window, len(df) - window):
        if df['High'].iloc[i] == df['High'].iloc[i-window:i+window+1].max():
            highs.append((i, float(df['High'].iloc[i])))
        if df['Low'].iloc[i] == df['Low'].iloc[i-window:i+window+1].min():
            lows.append((i, float(df['Low'].iloc[i])))
    return highs, lows

def run_backtest(df, highs, lows, entry_fib, stop_fib, target_fib, fib_zone, min_impulse):
    trades = []
    for low_idx, low_price in lows:
        next_highs = [(i, p) for i, p in highs if i > low_idx]
        if not next_highs:
            continue
        high_idx, high_price = next_highs[0]
        impulse = high_price - low_price
        if impulse / low_price < min_impulse:
            continue

        entry_level  = high_price - impulse * entry_fib
        stop_level   = high_price - impulse * stop_fib
        target_level = high_price + impulse * (target_fib - 1.0)
        risk   = entry_level - stop_level
        reward = target_level - entry_level
        rr = reward / risk if risk > 0 else 0

        entry_bar = None
        for j, (idx, row) in enumerate(df.iloc[high_idx:].iterrows()):
            if row['Low'] <= entry_level * (1 + fib_zone) and row['High'] >= entry_level * (1 - fib_zone):
                entry_bar = (j + high_idx, idx, entry_level)
                break

        if entry_bar is None:
            continue

        entry_bar_num, entry_date, entry_price = entry_bar
        outcome = exit_price = exit_date = None

        for idx, row in df.iloc[entry_bar_num:].iterrows():
            if row['Low'] <= stop_level:
                outcome, exit_price, exit_date = 'LOSS', stop_level, idx
                break
            if row['High'] >= target_level:
                outcome, exit_price, exit_date = 'WIN', target_level, idx
                break

        if outcome is None:
            continue

        pnl_pips = (exit_price - entry_price) * 10000

        trades.append({
            'low_price': low_price, 'high_price': high_price,
            'impulse_size': impulse,
            'entry_level': entry_level, 'stop_level': stop_level,
            'target_level': target_level,
            'entry_date': entry_date, 'exit_date': exit_date,
            'outcome': outcome, 'pnl_pips': pnl_pips, 'rr_ratio': rr,
        })
    return pd.DataFrame(trades)

# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────
st.title("📊 Fibonacci Backtester")
st.caption(f"Setup: retracement {entry_fib:.3f} → extension {target_fib:.3f} | SL @ {stop_fib:.3f}")

with st.spinner("Pobieranie danych..."):
    try:
        df = load_data(ticker, period, interval)
        st.success(f"✅ {len(df)} świec | {df.index[0].date()} → {df.index[-1].date()}")
    except Exception as e:
        st.error(f"Błąd pobierania danych: {e}")
        st.stop()

with st.spinner("Szukam swingów i liczę transakcje..."):
    highs, lows = find_swings(df, swing_window)
    results = run_backtest(df, highs, lows, entry_fib, stop_fib, target_fib, fib_zone, min_impulse)

if results.empty:
    st.warning("Nie znaleziono transakcji. Spróbuj zmniejszyć minimalny impuls lub zwiększyć tolerancję strefy.")
    st.stop()

# ─────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────
total  = len(results)
wins   = (results['outcome'] == 'WIN').sum()
losses = (results['outcome'] == 'LOSS').sum()
win_rate   = wins / total * 100
avg_rr     = results['rr_ratio'].mean()
total_pips = results['pnl_pips'].sum()
expected_value = (win_rate/100 * avg_rr) - (1 - win_rate/100)
max_dd = (results['pnl_pips'].cumsum() - results['pnl_pips'].cumsum().cummax()).min()

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Transakcje", total)
col2.metric("Win Rate", f"{win_rate:.1f}%", f"{wins}W / {losses}L")
col3.metric("Avg R:R", f"{avg_rr:.2f}")
col4.metric("Expected Value", f"{expected_value:.2f}R",
            "✅ Pozytywne" if expected_value > 0 else "❌ Negatywne")
col5.metric("Total P&L", f"{total_pips:.0f} pips")
col6.metric("Max Drawdown", f"{max_dd:.0f} pips")

st.markdown("---")

# ─────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────
col_left, col_right = st.columns(2)

# Cumulative PnL
with col_left:
    st.subheader("Cumulative P&L")
    results['cum_pips'] = results['pnl_pips'].cumsum()
    fig_pnl = go.Figure()
    fig_pnl.add_trace(go.Scatter(
        x=list(range(len(results))), y=results['cum_pips'],
        fill='tozeroy',
        line=dict(color='#2196F3', width=2),
        fillcolor='rgba(33,150,243,0.15)',
        name='Cumulative pips'
    ))
    fig_pnl.update_layout(
        paper_bgcolor='#1a1a2e', plot_bgcolor='#1a1a2e',
        font=dict(color='white'), height=300,
        xaxis=dict(title='Trade #', gridcolor='#333'),
        yaxis=dict(title='Pips', gridcolor='#333'),
        showlegend=False
    )
    st.plotly_chart(fig_pnl, use_container_width=True)

# Win/Loss by month
with col_right:
    st.subheader("Win Rate miesięczny")
    results['month'] = pd.to_datetime(results['entry_date']).dt.to_period('M').astype(str)
    monthly = results.groupby('month').apply(
        lambda x: (x['outcome'] == 'WIN').mean() * 100
    ).reset_index()
    monthly.columns = ['month', 'win_rate']

    fig_monthly = go.Figure(go.Bar(
        x=monthly['month'], y=monthly['win_rate'],
        marker_color=['#26a69a' if w >= 50 else '#ef5350' for w in monthly['win_rate']],
    ))
    fig_monthly.add_hline(y=50, line_dash="dash", line_color="yellow", opacity=0.7)
    fig_monthly.update_layout(
        paper_bgcolor='#1a1a2e', plot_bgcolor='#1a1a2e',
        font=dict(color='white'), height=300,
        xaxis=dict(gridcolor='#333'),
        yaxis=dict(title='Win Rate %', gridcolor='#333', range=[0, 100]),
        showlegend=False
    )
    st.plotly_chart(fig_monthly, use_container_width=True)

# R:R distribution + PnL per trade
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("Rozkład R:R")
    fig_rr = go.Figure(go.Histogram(
        x=results['rr_ratio'], nbinsx=20,
        marker_color='#9c27b0', opacity=0.8
    ))
    fig_rr.add_vline(x=avg_rr, line_dash="dash", line_color="yellow",
                     annotation_text=f"Avg: {avg_rr:.2f}")
    fig_rr.update_layout(
        paper_bgcolor='#1a1a2e', plot_bgcolor='#1a1a2e',
        font=dict(color='white'), height=300,
        xaxis=dict(title='R:R Ratio', gridcolor='#333'),
        yaxis=dict(title='Count', gridcolor='#333'),
        showlegend=False
    )
    st.plotly_chart(fig_rr, use_container_width=True)

with col_right2:
    st.subheader("P&L per transakcja")
    colors = ['#26a69a' if p > 0 else '#ef5350' for p in results['pnl_pips']]
    fig_bar = go.Figure(go.Bar(
        x=list(range(len(results))), y=results['pnl_pips'],
        marker_color=colors
    ))
    fig_bar.update_layout(
        paper_bgcolor='#1a1a2e', plot_bgcolor='#1a1a2e',
        font=dict(color='white'), height=300,
        xaxis=dict(title='Trade #', gridcolor='#333'),
        yaxis=dict(title='Pips', gridcolor='#333'),
        showlegend=False
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ─────────────────────────────────────────────
# PRICE CHART WITH TRADE MARKERS
# ─────────────────────────────────────────────
st.subheader("📈 Wykres ceny z transakcjami")

sample_df = df.tail(500)
fig_price = go.Figure()

fig_price.add_trace(go.Candlestick(
    x=sample_df.index,
    open=sample_df['Open'], high=sample_df['High'],
    low=sample_df['Low'], close=sample_df['Close'],
    name='Price',
    increasing_line_color='#26a69a',
    decreasing_line_color='#ef5350',
))

# Plot trade entries
recent_trades = results[pd.to_datetime(results['entry_date']) >= sample_df.index[0]]

wins_df  = recent_trades[recent_trades['outcome'] == 'WIN']
losses_df = recent_trades[recent_trades['outcome'] == 'LOSS']

if not wins_df.empty:
    fig_price.add_trace(go.Scatter(
        x=wins_df['entry_date'], y=wins_df['entry_level'],
        mode='markers', marker=dict(symbol='triangle-up', size=12, color='#26a69a'),
        name='WIN entry'
    ))

if not losses_df.empty:
    fig_price.add_trace(go.Scatter(
        x=losses_df['entry_date'], y=losses_df['entry_level'],
        mode='markers', marker=dict(symbol='triangle-up', size=12, color='#ef5350'),
        name='LOSS entry'
    ))

fig_price.update_layout(
    paper_bgcolor='#1a1a2e', plot_bgcolor='#1a1a2e',
    font=dict(color='white'), height=500,
    xaxis=dict(gridcolor='#333', rangeslider=dict(visible=False)),
    yaxis=dict(gridcolor='#333'),
    legend=dict(bgcolor='#1a1a2e')
)
st.plotly_chart(fig_price, use_container_width=True)

# ─────────────────────────────────────────────
# TRADE TABLE
# ─────────────────────────────────────────────
with st.expander("📋 Lista wszystkich transakcji"):
    display = results[['entry_date', 'exit_date', 'outcome', 'entry_level',
                        'stop_level', 'target_level', 'pnl_pips', 'rr_ratio']].copy()
    display['entry_level'] = display['entry_level'].round(4)
    display['stop_level']  = display['stop_level'].round(4)
    display['target_level'] = display['target_level'].round(4)
    display['pnl_pips'] = display['pnl_pips'].round(1)
    display['rr_ratio'] = display['rr_ratio'].round(2)

    def color_outcome(val):
        return 'color: #26a69a' if val == 'WIN' else 'color: #ef5350'

    st.dataframe(
        display.style.applymap(color_outcome, subset=['outcome']),
        use_container_width=True
    )

    csv = display.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Pobierz CSV", csv, "fib_trades.csv", "text/csv")

st.markdown("---")
st.caption("Fibonacci Backtester | PHC Trading Tools | Dane: Yahoo Finance")
