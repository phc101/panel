"""
Fibonacci 0.618 → 1.618 Backtester - Streamlit App
With capital management, leverage and multiple PLN pairs

Usage:
    pip install yfinance pandas numpy streamlit plotly
    streamlit run fib_streamlit.py
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Fibonacci Backtester",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; }
    div[data-testid="metric-container"] {
        background: #1a1a2e;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAIRS
# ─────────────────────────────────────────────
PAIRS = {
    "USD/PLN": "PLN=X",
    "EUR/PLN": "EURPLN=X",
    "GBP/PLN": "GBPPLN=X",
    "CHF/PLN": "CHFPLN=X",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "CHF/USD": "CHFUSD=X",
    "GBP/EUR": "GBPEUR=X",
    "CHF/EUR": "CHFEUR=X",
}

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
st.sidebar.title("⚙️ Ustawienia")

st.sidebar.subheader("💰 Kapitał i ryzyko")
capital = st.sidebar.number_input(
    "Kapitał (USD)", min_value=1000, max_value=1_000_000, value=10_000, step=1000
)
leverage = st.sidebar.select_slider("Lewar", options=[1, 5, 10, 20], value=1)
risk_pct = st.sidebar.slider("Ryzyko na transakcję (%)", 0.5, 10.0, 2.0, 0.5)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Para i dane")

selected_pairs = st.sidebar.multiselect(
    "Pary walutowe",
    list(PAIRS.keys()),
    default=["USD/PLN", "EUR/PLN"]
)

# Yahoo Finance interval limits:
# 1h  → max 730 days (2y)
# 4h  → not native, resampled from 1h (max 2y)
# 1d  → unlimited
INTERVAL_MAX_PERIOD = {
    "1h":  ["6mo", "1y", "2y"],
    "4h":  ["6mo", "1y", "2y"],
    "1d":  ["6mo", "1y", "2y", "5y"],
}

interval = st.sidebar.selectbox("Interwał", ["1h", "4h", "1d"], index=0)
allowed_periods = INTERVAL_MAX_PERIOD[interval]
period = st.sidebar.selectbox("Okres historyczny", allowed_periods, index=min(1, len(allowed_periods)-1))

if interval in ("1h", "4h") and period not in allowed_periods:
    st.sidebar.warning(f"⚠️ Interwał {interval} obsługuje max 2y – ustawiono 2y.")

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Parametry Fibonacciego")

swing_window = st.sidebar.slider("Okno swingów (bary)", 5, 30, 10)
entry_fib    = st.sidebar.slider("Wejście (retracement)",  0.500, 0.786, 0.618, 0.001, format="%.3f")
stop_fib     = st.sidebar.slider("Stop Loss (retracement)", 0.618, 0.900, 0.786, 0.001, format="%.3f")
target_fib   = st.sidebar.slider("Take Profit (extension)", 1.272, 2.618, 1.618, 0.001, format="%.3f")
fib_zone     = st.sidebar.slider("Tolerancja strefy (%)", 0.1, 3.0, 1.0, 0.1) / 100
min_impulse  = st.sidebar.slider("Minimalny impuls (%)",  0.1, 2.0, 0.5, 0.1) / 100

# ─────────────────────────────────────────────
# FUNCTIONS
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data(ticker, period, interval):
    # 4h is not natively supported by yfinance – download 1h and resample
    dl_interval = "1h" if interval == "4h" else interval

    df = yf.download(ticker, period=period, interval=dl_interval, auto_adjust=True)

    if df.empty:
        return pd.DataFrame()

    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df[['Open', 'High', 'Low', 'Close']].dropna()

    # Resample 1h → 4h
    if interval == "4h":
        df = df.resample("4h").agg({
            'Open':  'first',
            'High':  'max',
            'Low':   'min',
            'Close': 'last',
        }).dropna()

    return df


def find_swings(df, window):
    highs, lows = [], []
    for i in range(window, len(df) - window):
        if df['High'].iloc[i] == df['High'].iloc[i - window:i + window + 1].max():
            highs.append((i, float(df['High'].iloc[i])))
        if df['Low'].iloc[i] == df['Low'].iloc[i - window:i + window + 1].min():
            lows.append((i, float(df['Low'].iloc[i])))
    return highs, lows


def calc_position_size(equity, risk_pct, leverage, entry, stop):
    risk_amount  = equity * (risk_pct / 100)
    pip_risk     = abs(entry - stop)
    if pip_risk == 0:
        return 0, 0
    position_size = (risk_amount / pip_risk) * leverage
    max_position  = equity * leverage
    position_size = min(position_size, max_position)
    return position_size, risk_amount


def run_backtest(df, highs, lows, entry_fib, stop_fib, target_fib,
                 fib_zone, min_impulse, capital, leverage, risk_pct):
    trades = []
    equity = float(capital)
    # Block new setups until this bar index – enforces one position at a time
    blocked_until_bar = -1

    for low_idx, low_price in lows:
        next_highs = [(i, p) for i, p in highs if i > low_idx]
        if not next_highs:
            continue
        high_idx, high_price = next_highs[0]

        # Skip this setup if we're still in a trade from a previous one
        if high_idx <= blocked_until_bar:
            continue

        impulse = high_price - low_price
        if impulse / low_price < min_impulse:
            continue

        entry_level  = high_price - impulse * entry_fib
        stop_level   = high_price - impulse * stop_fib
        target_level = high_price + impulse * (target_fib - 1.0)
        risk   = entry_level - stop_level
        reward = target_level - entry_level
        rr     = reward / risk if risk > 0 else 0

        # Search for entry only from the swing high onward (not before blocked_until)
        search_start = max(high_idx, blocked_until_bar + 1)
        entry_bar = None
        for j, (idx, row) in enumerate(df.iloc[search_start:].iterrows()):
            if row['Low'] <= entry_level * (1 + fib_zone) and \
               row['High'] >= entry_level * (1 - fib_zone):
                entry_bar = (j + search_start, idx, entry_level)
                break
        if entry_bar is None:
            continue

        entry_bar_num, entry_date, entry_price = entry_bar
        position_size, risk_amount = calc_position_size(
            equity, risk_pct, leverage, entry_price, stop_level
        )

        outcome = exit_price = exit_date = exit_bar_num = None
        for j, (idx, row) in enumerate(df.iloc[entry_bar_num:].iterrows()):
            if row['Low'] <= stop_level:
                outcome, exit_price, exit_date, exit_bar_num = 'LOSS', stop_level, idx, j + entry_bar_num
                break
            if row['High'] >= target_level:
                outcome, exit_price, exit_date, exit_bar_num = 'WIN', target_level, idx, j + entry_bar_num
                break
        if outcome is None:
            continue

        # Block all new setups until this trade is closed
        blocked_until_bar = exit_bar_num

        pnl_price = exit_price - entry_price
        pnl_usd   = pnl_price * position_size
        pnl_pips  = pnl_price * 10000
        equity   += pnl_usd
        equity    = max(equity, 0)

        trades.append({
            'entry_date':    entry_date,
            'exit_date':     exit_date,
            'outcome':       outcome,
            'entry_level':   entry_level,
            'stop_level':    stop_level,
            'target_level':  target_level,
            'impulse_size':  impulse,
            'position_size': position_size,
            'risk_amount':   risk_amount,
            'pnl_pips':      pnl_pips,
            'pnl_usd':       pnl_usd,
            'equity':        equity,
            'rr_ratio':      rr,
        })

    return pd.DataFrame(trades)


def calc_max_drawdown(equity_series):
    peak = equity_series.cummax()
    dd   = (equity_series - peak) / peak * 100
    return dd.min()


def dark_layout(height=300):
    return dict(
        paper_bgcolor='#1a1a2e', plot_bgcolor='#1a1a2e',
        font=dict(color='white'), height=height,
        xaxis=dict(gridcolor='#333'),
        yaxis=dict(gridcolor='#333'),
        showlegend=False, margin=dict(t=10, b=30)
    )


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
st.title("📊 Fibonacci Backtester")
st.caption(
    f"Setup: retracement **{entry_fib:.3f}** → extension **{target_fib:.3f}** | "
    f"SL @ **{stop_fib:.3f}** | Kapitał: **${capital:,}** | "
    f"Lewar: **x{leverage}** | Ryzyko/trade: **{risk_pct}%**"
)

if not selected_pairs:
    st.warning("Wybierz co najmniej jedną parę walutową.")
    st.stop()

# ─────────────────────────────────────────────
# LEVERAGE QUICK CALC
# ─────────────────────────────────────────────
with st.expander("📐 Kalkulator lewarowania"):
    risk_amt = capital * risk_pct / 100
    lev_data = []
    for lev in [1, 5, 10, 20]:
        lev_data.append({
            "Lewar":                f"x{lev}",
            "Kapitał handlowy":     f"${capital * lev:,.0f}",
            "Ryzyko/trade (USD)":   f"${risk_amt:,.0f}",
            "Ryzyko/trade (%)":     f"{risk_pct}%",
            "Margin required":      f"${capital / lev:,.0f}",
        })
    st.dataframe(pd.DataFrame(lev_data), use_container_width=True, hide_index=True)

st.markdown("---")

# ─────────────────────────────────────────────
# TABS PER PAIR + COMPARISON
# ─────────────────────────────────────────────
all_results = {}
tab_labels  = selected_pairs + ["📊 Porównanie par"]
pair_tabs   = st.tabs(tab_labels)

for tab, pair_name in zip(pair_tabs[:-1], selected_pairs):
    ticker = PAIRS[pair_name]

    with tab:
        with st.spinner(f"Pobieranie {pair_name}..."):
            try:
                df = load_data(ticker, period, interval)
            except Exception as e:
                st.error(f"Błąd pobierania danych: {e}")
                continue

        if df.empty:
            st.error(f"❌ Brak danych dla {pair_name} przy interwale {interval} / okresie {period}. Spróbuj krótszego okresu.")
            continue

        st.caption(
            f"**{len(df)}** świec | {df.index[0].date()} → {df.index[-1].date()}"
            + (f" | ⚠️ 4h zresampleowane z 1h" if interval == "4h" else "")
        )

        highs, lows = find_swings(df, swing_window)

        with st.spinner("Liczę transakcje..."):
            results = run_backtest(
                df, highs, lows,
                entry_fib, stop_fib, target_fib,
                fib_zone, min_impulse,
                capital, leverage, risk_pct
            )

        if results.empty:
            st.warning("Brak transakcji – zmniejsz minimalny impuls lub zwiększ tolerancję strefy.")
            continue

        all_results[pair_name] = results

        # ── METRICS ──────────────────────────────────────────────
        total     = len(results)
        wins      = (results['outcome'] == 'WIN').sum()
        losses    = total - wins
        win_rate  = wins / total * 100
        avg_rr    = results['rr_ratio'].mean()
        total_usd = results['pnl_usd'].sum()
        final_eq  = results['equity'].iloc[-1]
        max_dd    = calc_max_drawdown(results['equity'])
        ev        = (win_rate / 100 * avg_rr) - (1 - win_rate / 100)

        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("Transakcje",      total)
        c2.metric("Win Rate",        f"{win_rate:.1f}%",    f"{wins}W / {losses}L")
        c3.metric("Avg R:R",         f"{avg_rr:.2f}")
        c4.metric("Expected Value",  f"{ev:.2f}R",
                  "✅ pozytywne" if ev > 0 else "❌ negatywne")
        c5.metric("Total P&L",       f"${total_usd:,.0f}")
        c6.metric("Końcowy kapitał", f"${final_eq:,.0f}",
                  f"{(final_eq / capital - 1) * 100:+.1f}%")
        c7.metric("Max Drawdown",    f"{max_dd:.1f}%")

        st.markdown("---")

        # ── ROW 1: Equity + Monthly WR ───────────────────────────
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Krzywa kapitału")
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(
                x=list(range(len(results))), y=results['equity'],
                fill='tozeroy', line=dict(color='#2196F3', width=2),
                fillcolor='rgba(33,150,243,0.1)'
            ))
            fig_eq.add_hline(y=capital, line_dash="dash",
                             line_color="yellow", opacity=0.5,
                             annotation_text=f"Start ${capital:,}")
            layout = dark_layout(300)
            layout['xaxis']['title'] = 'Trade #'
            layout['yaxis']['title'] = 'USD'
            fig_eq.update_layout(**layout)
            st.plotly_chart(fig_eq, use_container_width=True)

        with col2:
            st.subheader("Win Rate miesięczny")
            results['month'] = (
                pd.to_datetime(results['entry_date'])
                .dt.to_period('M').astype(str)
            )
            monthly = (
                results.groupby('month')
                .apply(lambda x: (x['outcome'] == 'WIN').mean() * 100)
                .reset_index(name='win_rate')
            )
            fig_m = go.Figure(go.Bar(
                x=monthly['month'], y=monthly['win_rate'],
                marker_color=['#26a69a' if w >= 50 else '#ef5350'
                              for w in monthly['win_rate']],
                text=[f"{w:.0f}%" for w in monthly['win_rate']],
                textposition='outside'
            ))
            fig_m.add_hline(y=50, line_dash="dash", line_color="yellow", opacity=0.5)
            layout2 = dark_layout(300)
            layout2['yaxis']['range'] = [0, 115]
            layout2['yaxis']['title'] = 'Win Rate %'
            fig_m.update_layout(**layout2)
            st.plotly_chart(fig_m, use_container_width=True)

        # ── ROW 2: P&L bars + R:R histogram ─────────────────────
        col3, col4 = st.columns(2)

        with col3:
            st.subheader("P&L per transakcja (USD)")
            fig_bar = go.Figure(go.Bar(
                x=list(range(len(results))),
                y=results['pnl_usd'].round(2),
                marker_color=['#26a69a' if p > 0 else '#ef5350'
                              for p in results['pnl_usd']]
            ))
            layout3 = dark_layout(280)
            layout3['xaxis']['title'] = 'Trade #'
            layout3['yaxis']['title'] = 'USD'
            fig_bar.update_layout(**layout3)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col4:
            st.subheader("Rozkład R:R")
            fig_rr = go.Figure(go.Histogram(
                x=results['rr_ratio'], nbinsx=20,
                marker_color='#9c27b0', opacity=0.85
            ))
            fig_rr.add_vline(x=avg_rr, line_dash="dash", line_color="yellow",
                             annotation_text=f"Avg {avg_rr:.2f}")
            layout4 = dark_layout(280)
            layout4['xaxis']['title'] = 'R:R'
            layout4['yaxis']['title'] = 'Liczba transakcji'
            fig_rr.update_layout(**layout4)
            st.plotly_chart(fig_rr, use_container_width=True)

        # ── PRICE CHART ──────────────────────────────────────────
        st.subheader("Wykres ceny z wejściami (ostatnie 300 świec)")
        sample = df.tail(300)
        fig_p  = go.Figure()
        fig_p.add_trace(go.Candlestick(
            x=sample.index,
            open=sample['Open'], high=sample['High'],
            low=sample['Low'],   close=sample['Close'],
            name='Price',
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350',
        ))
        recent = results[
            pd.to_datetime(results['entry_date']) >= sample.index[0]
        ]
        for outcome, color, symbol in [
            ('WIN',  '#26a69a', 'triangle-up'),
            ('LOSS', '#ef5350', 'triangle-up'),
        ]:
            sub = recent[recent['outcome'] == outcome]
            if not sub.empty:
                fig_p.add_trace(go.Scatter(
                    x=sub['entry_date'], y=sub['entry_level'],
                    mode='markers', name=outcome,
                    marker=dict(symbol=symbol, size=12, color=color,
                                line=dict(width=1, color='white'))
                ))
        price_layout = dark_layout(420)
        price_layout['showlegend']            = True
        price_layout['legend']                = dict(bgcolor='#1a1a2e')
        price_layout['xaxis']['rangeslider']  = dict(visible=False)
        fig_p.update_layout(**price_layout)
        st.plotly_chart(fig_p, use_container_width=True)

        # ── LEVERAGE COMPARISON ──────────────────────────────────
        st.subheader("💡 Wpływ lewara na wyniki (bieżące parametry)")
        lev_rows = []
        for lev in [1, 5, 10, 20]:
            r = run_backtest(
                df, highs, lows,
                entry_fib, stop_fib, target_fib,
                fib_zone, min_impulse,
                capital, lev, risk_pct
            )
            if r.empty:
                continue
            eq_f = r['equity'].iloc[-1]
            dd   = calc_max_drawdown(r['equity'])
            wr   = (r['outcome'] == 'WIN').mean() * 100
            lev_rows.append({
                'Lewar':             f'x{lev}',
                'Win Rate':          f'{wr:.1f}%',
                'Total P&L (USD)':   f"${r['pnl_usd'].sum():,.0f}",
                'Końcowy kapitał':   f"${eq_f:,.0f}",
                'Zwrot (%)':         f"{(eq_f / capital - 1) * 100:+.1f}%",
                'Max Drawdown (%)':  f'{dd:.1f}%',
                'Transakcji':        len(r),
            })
        if lev_rows:
            st.dataframe(
                pd.DataFrame(lev_rows), use_container_width=True, hide_index=True
            )

        # ── TRADE TABLE ──────────────────────────────────────────
        with st.expander("📋 Lista wszystkich transakcji"):
            disp = results[[
                'entry_date', 'exit_date', 'outcome',
                'entry_level', 'stop_level', 'target_level',
                'position_size', 'risk_amount', 'pnl_pips', 'pnl_usd',
                'equity', 'rr_ratio'
            ]].copy()
            for col in ['entry_level', 'stop_level', 'target_level']:
                disp[col] = disp[col].round(4)
            disp['position_size'] = disp['position_size'].round(0)
            disp['risk_amount']   = disp['risk_amount'].round(2)
            disp['pnl_pips']      = disp['pnl_pips'].round(1)
            disp['pnl_usd']       = disp['pnl_usd'].round(2)
            disp['equity']        = disp['equity'].round(2)
            disp['rr_ratio']      = disp['rr_ratio'].round(2)

            def color_outcome(val):
                return ('color: #26a69a; font-weight: bold' if val == 'WIN'
                        else 'color: #ef5350; font-weight: bold')

            st.dataframe(
                disp.style.applymap(color_outcome, subset=['outcome']),
                use_container_width=True
            )
            csv = disp.to_csv(index=False).encode('utf-8')
            st.download_button(
                f"⬇️ Pobierz CSV – {pair_name}",
                csv,
                f"fib_{pair_name.replace('/', '')}_{period}.csv",
                "text/csv"
            )

# ─────────────────────────────────────────────
# COMPARISON TAB
# ─────────────────────────────────────────────
with pair_tabs[-1]:
    st.subheader("📊 Porównanie wszystkich par")

    if not all_results:
        st.info("Uruchom backtest na co najmniej jednej parze.")
    else:
        COLORS = ['#2196F3', '#26a69a', '#ef5350', '#ff9800',
                  '#9c27b0', '#00bcd4', '#ffeb3b', '#e91e63', '#4caf50']

        comp_rows       = []
        fig_equity_comp = go.Figure()

        for i, (pair_name, res) in enumerate(all_results.items()):
            total  = len(res)
            wins   = (res['outcome'] == 'WIN').sum()
            wr     = wins / total * 100
            avg_rr = res['rr_ratio'].mean()
            ev     = (wr / 100 * avg_rr) - (1 - wr / 100)
            pnl    = res['pnl_usd'].sum()
            eq_fin = res['equity'].iloc[-1]
            ret    = (eq_fin / capital - 1) * 100
            dd     = calc_max_drawdown(res['equity'])

            comp_rows.append({
                'Para':             pair_name,
                'Transakcji':       total,
                'Win Rate':         f'{wr:.1f}%',
                'Avg R:R':          f'{avg_rr:.2f}',
                'Expected Value':   f'{ev:.2f}R',
                'Total P&L (USD)':  f'${pnl:,.0f}',
                'Zwrot':            f'{ret:+.1f}%',
                'Max Drawdown':     f'{dd:.1f}%',
                'Końcowy kapitał':  f'${eq_fin:,.0f}',
            })

            fig_equity_comp.add_trace(go.Scatter(
                x=list(range(len(res))), y=res['equity'],
                name=pair_name,
                line=dict(color=COLORS[i % len(COLORS)], width=2)
            ))

        st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)

        # Equity curves
        st.subheader("Krzywe kapitału – wszystkie pary")
        fig_equity_comp.add_hline(
            y=capital, line_dash="dash", line_color="white", opacity=0.3,
            annotation_text=f"Start ${capital:,}"
        )
        eq_layout = dark_layout(450)
        eq_layout['showlegend']   = True
        eq_layout['legend']       = dict(bgcolor='#1a1a2e', bordercolor='#333', borderwidth=1)
        eq_layout['xaxis']['title'] = 'Trade #'
        eq_layout['yaxis']['title'] = 'Equity (USD)'
        fig_equity_comp.update_layout(**eq_layout)
        st.plotly_chart(fig_equity_comp, use_container_width=True)

        # Win rate comparison bar
        st.subheader("Win Rate – porównanie")
        wr_vals = [float(r['Win Rate'].replace('%', '')) for r in comp_rows]
        fig_wr  = go.Figure(go.Bar(
            x=[r['Para'] for r in comp_rows], y=wr_vals,
            marker_color=['#26a69a' if w >= 50 else '#ef5350' for w in wr_vals],
            text=[f"{w:.1f}%" for w in wr_vals], textposition='outside'
        ))
        fig_wr.add_hline(y=50, line_dash="dash", line_color="yellow", opacity=0.5)
        wr_layout = dark_layout(350)
        wr_layout['yaxis']['range'] = [0, 115]
        wr_layout['yaxis']['title'] = 'Win Rate %'
        fig_wr.update_layout(**wr_layout)
        st.plotly_chart(fig_wr, use_container_width=True)

st.markdown("---")
st.caption(
    "Fibonacci Backtester | PHC Trading Tools | Dane: Yahoo Finance | "
    "Nie stanowi doradztwa inwestycyjnego"
)
