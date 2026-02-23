"""
Fibonacci Signal Bot – Live Dashboard
Streamlit auto-refresh co N minut, szuka setupów Fib na żywo.

Usage:
    pip install yfinance pandas numpy streamlit plotly streamlit-autorefresh
    streamlit run signal_bot.py
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import time

# Auto-refresh
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Fib Signal Bot",
    page_icon="🔔",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; }
    .signal-box-buy {
        background: #0d3b2e;
        border: 2px solid #26a69a;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .signal-box-watch {
        background: #2a2a10;
        border: 2px solid #ff9800;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .signal-box-none {
        background: #1a1a2e;
        border: 1px solid #444;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    div[data-testid="metric-container"] {
        background: #1a1a2e;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
PAIRS = {
    "USD/PLN": ("PLN=X",    False),
    "EUR/PLN": ("EURPLN=X", False),
    "GBP/PLN": ("GBPPLN=X", False),
    "CHF/PLN": ("CHFPLN=X", False),
    "EUR/USD": ("EURUSD=X", False),
    "GBP/USD": ("GBPUSD=X", False),
    "USD/CHF": ("CHF=X",    True),   # odwrócone
    "GBP/EUR": ("GBPEUR=X", False),
    "CHF/EUR": ("CHFEUR=X", False),
}

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
st.sidebar.title("⚙️ Ustawienia bota")

selected_pairs = st.sidebar.multiselect(
    "Monitorowane pary",
    list(PAIRS.keys()),
    default=["EUR/PLN", "USD/PLN", "EUR/USD"]
)

interval = st.sidebar.selectbox(
    "Interwał świec",
    ["1h", "4h", "1d"],
    index=0,
    help="1h = najbardziej aktualne sygnały (dane do ~2y)"
)

refresh_min = st.sidebar.slider(
    "Odświeżanie co (min)", 1, 60, 15,
    help="Co ile minut bot sprawdza nowe sygnały"
)

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Parametry Fibonacciego")

swing_window = st.sidebar.slider("Okno swingów (bary)", 5, 30, 10)
entry_fib    = st.sidebar.slider("Wejście (retracement)",   0.500, 0.786, 0.618, 0.001, format="%.3f")
stop_fib     = st.sidebar.slider("Stop Loss (retracement)", 0.618, 0.900, 0.786, 0.001, format="%.3f")
target_fib   = st.sidebar.slider("Take Profit (extension)", 1.272, 2.618, 1.618, 0.001, format="%.3f")
fib_zone     = st.sidebar.slider("Tolerancja strefy (%)", 0.1, 3.0, 1.0, 0.1) / 100
min_impulse  = st.sidebar.slider("Minimalny impuls (%)",   0.1, 2.0, 0.5, 0.1) / 100

# Jak blisko strefy wejścia żeby pokazać "WATCHING" (cena zbliża się)
watch_pct = st.sidebar.slider(
    "Alert 'zbliża się' (%)", 0.5, 5.0, 2.0, 0.5,
    help="Pomarańczowy alert gdy cena jest w tej odległości od strefy wejścia"
) / 100

st.sidebar.markdown("---")
# Ręczne odświeżenie
if st.sidebar.button("🔄 Odśwież teraz"):
    st.cache_data.clear()
    st.rerun()

# ─────────────────────────────────────────────
# AUTO-REFRESH
# ─────────────────────────────────────────────
if HAS_AUTOREFRESH:
    refresh_ms = refresh_min * 60 * 1000
    count = st_autorefresh(interval=refresh_ms, key="bot_refresh")
else:
    st.sidebar.warning(
        "⚠️ Brak streamlit-autorefresh.\n"
        "Zainstaluj: pip install streamlit-autorefresh\n"
        "Lub odświeżaj ręcznie przyciskiem powyżej."
    )

# ─────────────────────────────────────────────
# FUNCTIONS
# ─────────────────────────────────────────────
@st.cache_data(ttl=refresh_min * 60)
def load_live(ticker, interval, invert=False):
    """Pobiera ostatnie dane live z Yahoo Finance."""
    period_map = {"1h": "60d", "4h": "60d", "1d": "1y"}
    dl_interval = "1h" if interval == "4h" else interval
    period = period_map.get(interval, "60d")

    df = yf.download(ticker, period=period, interval=dl_interval, auto_adjust=True, progress=False)
    if df.empty:
        return pd.DataFrame()

    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df[['Open', 'High', 'Low', 'Close']].dropna()

    if interval == "4h":
        df = df.resample("4h").agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'
        }).dropna()

    if invert:
        df['Open']  = 1.0 / df['Open']
        df['Close'] = 1.0 / df['Close']
        h = 1.0 / df['Low']
        l = 1.0 / df['High']
        df['High'] = h
        df['Low']  = l

    return df


def find_swings(df, window):
    highs, lows = [], []
    for i in range(window, len(df) - window):
        if df['High'].iloc[i] == df['High'].iloc[i - window:i + window + 1].max():
            highs.append((i, float(df['High'].iloc[i])))
        if df['Low'].iloc[i] == df['Low'].iloc[i - window:i + window + 1].min():
            lows.append((i, float(df['Low'].iloc[i])))
    return highs, lows


def find_active_setups(df, highs, lows, entry_fib, stop_fib, target_fib,
                       fib_zone, min_impulse, watch_pct):
    """
    Szuka aktywnych setupów Fibonacci na końcu danych (ostatnie N świec).
    Zwraca listę setupów z ich statusem:
      - ENTRY_NOW  : cena jest w strefie wejścia
      - WATCHING   : cena zbliża się do strefy wejścia
      - PENDING    : setup istnieje, cena daleko
    """
    setups = []
    current_price = float(df['Close'].iloc[-1])
    current_bar   = len(df) - 1

    # Bierzemy tylko ostatnie swingi (z ostatnich 100 barów)
    recent_lows  = [(i, p) for i, p in lows  if i > current_bar - 100]
    recent_highs = [(i, p) for i, p in highs if i > current_bar - 100]

    for low_idx, low_price in recent_lows:
        next_highs = [(i, p) for i, p in recent_highs if i > low_idx]
        if not next_highs:
            continue
        high_idx, high_price = next_highs[0]

        impulse = high_price - low_price
        if impulse / low_price < min_impulse:
            continue

        entry_level  = high_price - impulse * entry_fib
        stop_level   = high_price - impulse * stop_fib
        target_level = high_price + impulse * (target_fib - 1.0)

        # Pomiń jeśli cena już wybiła powyżej higha (setup nieważny)
        if current_price > high_price * 1.005:
            continue

        # Pomiń jeśli cena poniżej stop (setup nieważny)
        if current_price < stop_level:
            continue

        risk   = entry_level - stop_level
        reward = target_level - entry_level
        rr     = reward / risk if risk > 0 else 0

        # Odległość ceny od strefy wejścia
        dist_to_entry = abs(current_price - entry_level) / entry_level

        # Czy cena jest w strefie wejścia?
        in_zone = (
            current_price <= entry_level * (1 + fib_zone) and
            current_price >= entry_level * (1 - fib_zone)
        )

        if in_zone:
            status = "ENTRY_NOW"
        elif dist_to_entry <= watch_pct:
            status = "WATCHING"
        else:
            status = "PENDING"

        setups.append({
            'status':        status,
            'high_price':    high_price,
            'low_price':     low_price,
            'high_idx':      high_idx,
            'low_idx':       low_idx,
            'entry_level':   entry_level,
            'stop_level':    stop_level,
            'target_level':  target_level,
            'current_price': current_price,
            'dist_pct':      dist_to_entry * 100,
            'rr_ratio':      rr,
            'impulse_size':  impulse,
        })

    # Sortuj: najpierw ENTRY_NOW, potem WATCHING, potem PENDING
    order = {'ENTRY_NOW': 0, 'WATCHING': 1, 'PENDING': 2}
    setups.sort(key=lambda x: (order[x['status']], x['dist_pct']))
    return setups


def make_chart(df, setup, pair_name):
    """Generuje wykres świecowy z poziomami Fib dla danego setupu."""
    # Pokaż okno wokół setupu + trochę kontekstu
    start_bar = max(0, setup['low_idx'] - 10)
    end_bar   = min(len(df), setup['high_idx'] + 60)
    sample    = df.iloc[start_bar:end_bar]

    fig = go.Figure()

    # Świece
    fig.add_trace(go.Candlestick(
        x=sample.index,
        open=sample['Open'], high=sample['High'],
        low=sample['Low'],   close=sample['Close'],
        name='Price',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350',
        increasing_fillcolor='#26a69a',
        decreasing_fillcolor='#ef5350',
    ))

    x_range = [sample.index[0], sample.index[-1]]

    # Poziomy Fib
    levels = [
        (setup['target_level'], '#26a69a',  'solid',  f"TP  {setup['target_level']:.4f}"),
        (setup['entry_level'],  '#2196F3',  'solid',  f"ENT {setup['entry_level']:.4f}"),
        (setup['stop_level'],   '#ef5350',  'solid',  f"SL  {setup['stop_level']:.4f}"),
        (setup['high_price'],   '#ffffff',  'dash',   f"High {setup['high_price']:.4f}"),
        (setup['low_price'],    '#ffffff',  'dash',   f"Low  {setup['low_price']:.4f}"),
    ]
    for price, color, dash, label in levels:
        fig.add_shape(
            type='line', x0=x_range[0], x1=x_range[1],
            y0=price, y1=price,
            line=dict(color=color, width=1.5, dash=dash)
        )
        fig.add_annotation(
            x=x_range[-1], y=price,
            text=label, showarrow=False,
            xanchor='left', font=dict(size=11, color=color),
            bgcolor='rgba(0,0,0,0.5)'
        )

    # Strefa wejścia (fill)
    zone_hi = setup['entry_level'] * (1 + fib_zone)
    zone_lo = setup['entry_level'] * (1 - fib_zone)
    fig.add_hrect(
        y0=zone_lo, y1=zone_hi,
        fillcolor='rgba(33,150,243,0.15)',
        line_width=0,
        annotation_text="Entry zone",
        annotation_position="right",
        annotation_font_color='#2196F3'
    )

    # Aktualna cena
    fig.add_hline(
        y=setup['current_price'],
        line_dash='dot', line_color='yellow', opacity=0.8,
        annotation_text=f"Now {setup['current_price']:.4f}",
        annotation_position='right'
    )

    fig.update_layout(
        paper_bgcolor='#1a1a2e', plot_bgcolor='#1a1a2e',
        font=dict(color='white'),
        height=420,
        xaxis=dict(gridcolor='#2a2a4a', rangeslider=dict(visible=False)),
        yaxis=dict(gridcolor='#2a2a4a'),
        showlegend=False,
        margin=dict(t=10, b=30, r=120),
        title=dict(text=f"{pair_name} | R:R {setup['rr_ratio']:.2f}", font=dict(size=14))
    )
    return fig


def status_badge(status):
    if status == "ENTRY_NOW":
        return "🟢 **ENTRY NOW**"
    elif status == "WATCHING":
        return "🟡 **WATCHING**"
    else:
        return "⚪ PENDING"


def status_css_class(status):
    if status == "ENTRY_NOW":
        return "signal-box-buy"
    elif status == "WATCHING":
        return "signal-box-watch"
    else:
        return "signal-box-none"


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
col_title, col_time = st.columns([3, 1])
with col_title:
    st.title("🔔 Fibonacci Signal Bot")
    st.caption(
        f"Entry: **{entry_fib:.3f}** | SL: **{stop_fib:.3f}** | TP: **{target_fib:.3f}** | "
        f"Interwał: **{interval}** | Okno swingów: **{swing_window}** barów"
    )
with col_time:
    st.metric("Ostatnie sprawdzenie", datetime.now().strftime("%H:%M:%S"))
    st.caption(f"Następne za ~{refresh_min} min")

st.markdown("---")

# ─────────────────────────────────────────────
# MAIN SCAN LOOP
# ─────────────────────────────────────────────
if not selected_pairs:
    st.warning("Wybierz co najmniej jedną parę w sidebarze.")
    st.stop()

# Zbieramy wszystkie aktywne sygnały do górnego summary
all_signals = []

pair_tabs = st.tabs(selected_pairs + ["📋 Wszystkie sygnały"])

for tab, pair_name in zip(pair_tabs[:-1], selected_pairs):
    ticker, invert = PAIRS[pair_name]

    with tab:
        with st.spinner(f"Skanowanie {pair_name}..."):
            try:
                df = load_live(ticker, interval, invert=invert)
            except Exception as e:
                st.error(f"Błąd pobierania: {e}")
                continue

        if df.empty:
            st.warning("Brak danych.")
            continue

        highs, lows = find_swings(df, swing_window)
        setups = find_active_setups(
            df, highs, lows,
            entry_fib, stop_fib, target_fib,
            fib_zone, min_impulse, watch_pct
        )

        current_price = float(df['Close'].iloc[-1])

        # Status pary
        active = [s for s in setups if s['status'] in ('ENTRY_NOW', 'WATCHING')]
        if any(s['status'] == 'ENTRY_NOW' for s in setups):
            pair_status = "🟢 ENTRY NOW"
        elif any(s['status'] == 'WATCHING' for s in setups):
            pair_status = "🟡 WATCHING"
        else:
            pair_status = "⚪ Brak sygnału"

        st.subheader(f"{pair_name}  |  Cena: **{current_price:.4f}**  |  {pair_status}")
        st.caption(f"{len(df)} świec | {df.index[0].date()} → {df.index[-1].date()} | {len(setups)} aktywnych setupów")

        if not setups:
            st.info("Brak setupów Fibonacci w ostatnich 100 barach.")
            continue

        # Pokaż max 3 najlepsze setupy
        for setup in setups[:3]:
            css = status_css_class(setup['status'])
            badge = status_badge(setup['status'])

            # Odległość ceny od wejścia
            arrow = "⬆️" if current_price < setup['entry_level'] else "⬇️"

            st.markdown(f"""
<div class="{css}">
{badge} &nbsp;&nbsp; Para: <b>{pair_name}</b> &nbsp;|&nbsp; R:R: <b>{setup['rr_ratio']:.2f}</b>
<br><br>
<table style="width:100%; color:white; border-collapse:collapse;">
  <tr>
    <td style="padding:4px 12px;">💹 Cena teraz</td>
    <td style="padding:4px 12px;"><b>{setup['current_price']:.4f}</b></td>
    <td style="padding:4px 12px;">📏 Odległość od ENT</td>
    <td style="padding:4px 12px;">{arrow} <b>{setup['dist_pct']:.2f}%</b></td>
  </tr>
  <tr>
    <td style="padding:4px 12px;">🎯 Entry</td>
    <td style="padding:4px 12px;"><b>{setup['entry_level']:.4f}</b></td>
    <td style="padding:4px 12px;">🔴 Stop Loss</td>
    <td style="padding:4px 12px;"><b>{setup['stop_level']:.4f}</b></td>
  </tr>
  <tr>
    <td style="padding:4px 12px;">✅ Take Profit</td>
    <td style="padding:4px 12px;"><b>{setup['target_level']:.4f}</b></td>
    <td style="padding:4px 12px;">📊 Impuls</td>
    <td style="padding:4px 12px;"><b>{setup['impulse_size']:.4f}</b></td>
  </tr>
</table>
</div>
""", unsafe_allow_html=True)

            # Wykres
            fig = make_chart(df, setup, pair_name)
            st.plotly_chart(fig, use_container_width=True)

            # Dodaj do globalnej listy sygnałów
            all_signals.append({**setup, 'pair': pair_name})

        if len(setups) > 3:
            with st.expander(f"Pokaż pozostałe {len(setups) - 3} setupy..."):
                for setup in setups[3:]:
                    st.write(
                        f"{status_badge(setup['status'])} | "
                        f"ENT: **{setup['entry_level']:.4f}** | "
                        f"SL: **{setup['stop_level']:.4f}** | "
                        f"TP: **{setup['target_level']:.4f}** | "
                        f"R:R: **{setup['rr_ratio']:.2f}** | "
                        f"Odl: **{setup['dist_pct']:.2f}%**"
                    )

# ─────────────────────────────────────────────
# SUMMARY TAB
# ─────────────────────────────────────────────
with pair_tabs[-1]:
    st.subheader("📋 Podsumowanie wszystkich aktywnych sygnałów")

    entry_now = [s for s in all_signals if s['status'] == 'ENTRY_NOW']
    watching  = [s for s in all_signals if s['status'] == 'WATCHING']

    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 ENTRY NOW",  len(entry_now))
    c2.metric("🟡 WATCHING",   len(watching))
    c3.metric("📊 Par skanych", len(selected_pairs))

    if not all_signals:
        st.info("Brak aktywnych sygnałów na wybranych parach.")
    else:
        rows = []
        for s in all_signals:
            arrow = "⬆️" if s['current_price'] < s['entry_level'] else "⬇️"
            rows.append({
                'Para':          s['pair'],
                'Status':        s['status'],
                'Cena':          round(s['current_price'], 4),
                'Entry':         round(s['entry_level'], 4),
                'Stop':          round(s['stop_level'], 4),
                'TP':            round(s['target_level'], 4),
                'R:R':           round(s['rr_ratio'], 2),
                'Odl. od ENT':   f"{arrow} {s['dist_pct']:.2f}%",
            })

        df_sum = pd.DataFrame(rows)

        def color_status(val):
            if val == 'ENTRY_NOW':
                return 'color: #26a69a; font-weight: bold'
            elif val == 'WATCHING':
                return 'color: #ff9800; font-weight: bold'
            return 'color: #aaa'

        st.dataframe(
            df_sum.style.applymap(color_status, subset=['Status']),
            use_container_width=True,
            hide_index=True
        )

st.markdown("---")
st.caption(
    f"Fibonacci Signal Bot | PHC Trading Tools | Dane: Yahoo Finance | "
    f"Odświeżanie co {refresh_min} min | Nie stanowi doradztwa inwestycyjnego"
)
