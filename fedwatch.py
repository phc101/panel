# -*- coding: utf-8 -*-
"""
FX ECM Forecaster — EUR/PLN, EUR/USD, USD/PLN (spójny trójkąt walutowy)
=======================================================================
Przebudowa modelu wg priorytetów 1-4:
  1. ECM (Engle-Granger): prognozowany jest powrót ODCHYLENIA kursu od
     wartości równowagi (fair value), a nie poziom kursu ze stałym slope.
  2. Wszystkie parametry (alpha, beta, gamma, sigma) estymowane w aplikacji
     z załadowanych danych; sigma z reszt regresji, realne R2 i t-staty.
  3. Przedziały prognozy rosną z horyzontem: Var(h) = sigma^2*(1-rho^2h)/(1-rho^2)
     (~ sigma*sqrt(h) dla krótkich horyzontów, plateau przy długich).
  4. Spójność trójkątna: estymowane są EUR/PLN i EUR/USD, a USD/PLN jest
     WYPROWADZANY jako iloraz (z poprawną wariancją i korelacją reszt).

Uruchomienie:
    pip install streamlit pandas numpy plotly
    streamlit run fx_ecm_forecaster.py
"""

import io
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------------
# Konfiguracja
# ------------------------------------------------------------------
st.set_page_config(
    page_title="FX ECM Forecaster",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded",
)

PHC = "#2E68A5"   # EUR/PLN
BLU = "#2563EB"   # EUR/USD
GRN = "#059669"   # USD/PLN

Z50 = 0.6745      # kwantyl 25/75
Z80 = 1.2816      # kwantyl 10/90

# Wartości krytyczne Engle-Grangera (2 zmienne, ze stałą w relacji długookresowej)
EG_CV = {"1%": -3.90, "5%": -3.34, "10%": -3.04}

# ------------------------------------------------------------------
# Dane PL (wbudowany CSV użytkownika)
# ------------------------------------------------------------------
PL_CSV = """date,inflation_rate,nbp_reference_rate,eur_pln,usd_pln
2014-01,0.5,2.50,4.1776,3.0650
2014-02,0.7,2.50,4.1786,3.0613
2014-03,0.7,2.50,4.1972,3.0378
2014-04,0.3,2.50,4.1841,3.0293
2014-05,0.2,2.50,4.1594,3.0234
2014-06,0.3,2.50,4.1659,3.0381
2014-07,-0.2,2.50,4.1773,3.0456
2014-08,-0.3,2.50,4.1856,3.0723
2014-09,-0.3,2.50,4.1953,3.1249
2014-10,-0.6,2.50,4.2071,3.1657
2014-11,-0.6,2.50,4.2389,3.2847
2014-12,-1.0,2.50,4.2623,3.5072
2015-01,-1.4,2.00,4.2538,3.6403
2015-02,-1.6,2.00,4.0934,3.6587
2015-03,-1.5,1.50,4.0678,3.7188
2015-04,-1.1,1.50,4.0853,3.7540
2015-05,-0.9,1.50,4.1078,3.6738
2015-06,-0.8,1.50,4.1856,3.8268
2015-07,-0.7,1.50,4.1302,3.7635
2015-08,-0.6,1.50,4.2247,3.9513
2015-09,-0.8,1.50,4.2655,4.0371
2015-10,-0.7,1.50,4.2839,3.9276
2015-11,-0.6,1.50,4.3211,3.9060
2015-12,-0.5,1.50,4.2639,3.9011
2016-01,-0.8,1.50,4.3616,4.0044
2016-02,-0.8,1.50,4.3438,3.7584
2016-03,-0.9,1.50,4.3732,3.7643
2016-04,-1.1,1.50,4.3947,3.7899
2016-05,-0.8,1.50,4.4259,3.9671
2016-06,-0.8,1.50,4.4240,3.9780
2016-07,-0.8,1.50,4.3284,3.9533
2016-08,-0.8,1.50,4.3567,3.9311
2016-09,-0.5,1.50,4.3123,3.8501
2016-10,-0.2,1.50,4.2969,3.8332
2016-11,-0.4,1.50,4.4588,3.7584
2016-12,-0.5,1.50,4.4240,4.1793
2017-01,-0.2,1.50,4.3135,3.8581
2017-02,0.1,1.50,4.3011,3.7840
2017-03,1.4,1.50,4.2247,3.8090
2017-04,1.7,1.50,4.2291,3.7963
2017-05,1.6,1.50,4.1953,3.7635
2017-06,1.8,1.50,4.2291,3.7963
2017-07,1.6,1.50,4.2655,3.8268
2017-08,1.4,1.50,4.2839,3.9276
2017-09,1.2,1.50,4.3211,3.9060
2017-10,1.1,1.50,4.2969,3.8332
2017-11,1.2,1.50,4.2389,3.7584
2017-12,1.0,1.50,4.1709,3.4813
2018-01,1.2,1.50,4.1497,3.4138
2018-02,1.4,1.50,4.1856,3.4427
2018-03,1.3,1.50,4.2071,3.4250
2018-04,1.7,1.50,4.2247,3.4427
2018-05,1.7,1.50,4.3618,3.7348
2018-06,1.7,1.50,4.3618,3.7348
2018-07,1.9,1.50,4.2655,3.8268
2018-08,2.0,1.50,4.2839,3.9276
2018-09,1.4,1.50,4.3211,3.9060
2018-10,1.2,1.50,4.2969,3.8332
2018-11,1.3,1.50,4.2389,3.7584
2018-12,1.1,1.50,4.2669,3.7597
2019-01,0.7,1.50,4.2615,3.7643
2019-02,1.2,1.50,4.3011,3.7840
2019-03,1.7,1.50,4.2247,3.8090
2019-04,2.2,1.50,4.2291,3.7963
2019-05,2.3,1.50,4.2655,3.7635
2019-06,1.0,1.50,4.2687,3.9311
2019-07,0.5,1.50,4.2839,3.9276
2019-08,0.4,1.50,4.3211,3.9060
2019-09,0.5,1.50,4.3732,3.8501
2019-10,0.4,1.50,4.2969,3.8332
2019-11,0.6,1.50,4.2389,3.7584
2019-12,1.3,1.50,4.2568,3.7977
2020-01,3.2,1.50,4.2597,3.7282
2020-02,3.7,1.50,4.3011,3.7840
2020-03,3.2,1.00,4.5523,4.1044
2020-04,3.4,0.50,4.5268,4.0776
2020-05,3.4,0.10,4.4584,4.0408
2020-06,3.3,0.10,4.4588,3.9680
2020-07,3.6,0.10,4.4240,3.9533
2020-08,3.8,0.10,4.4259,3.9671
2020-09,3.2,0.10,4.5268,3.9780
2020-10,3.1,0.10,4.4584,4.0408
2020-11,3.0,0.10,4.4588,3.9680
2020-12,3.7,0.10,4.6148,3.7584
2021-01,2.6,0.10,4.5826,3.8332
2021-02,2.4,0.10,4.1856,3.8090
2021-03,3.2,0.10,4.6525,4.2030
2021-04,4.6,0.10,4.1953,3.7635
2021-05,4.4,0.10,4.4259,3.9671
2021-06,4.1,0.10,4.5208,3.7840
2021-07,4.8,0.10,4.5826,3.8332
2021-08,5.2,0.10,4.6856,4.0671
2021-09,5.8,0.10,4.6184,4.0086
2021-10,5.9,0.50,4.6184,4.0086
2021-11,6.8,1.25,4.6856,4.0671
2021-12,8.6,1.75,4.5994,4.0600
2022-01,9.4,2.25,4.5969,4.0683
2022-02,8.5,2.75,4.6939,4.0687
2022-03,10.9,3.50,4.6525,4.2030
2022-04,12.4,4.50,4.6560,4.5267
2022-05,13.5,5.25,4.5691,4.2608
2022-06,11.8,6.00,4.4615,4.2631
2022-07,10.8,6.00,4.7011,4.7169
2022-08,10.1,6.00,4.6939,4.5267
2022-09,10.7,6.75,4.8694,4.8574
2022-10,8.2,6.75,4.7392,4.9894
2022-11,7.8,6.75,4.6939,4.7169
2022-12,7.5,6.75,4.6808,4.4018
2023-01,6.6,6.75,4.7047,4.4541
2023-02,6.0,6.75,4.6939,4.4018
2023-03,6.1,6.75,4.6808,4.4541
2023-04,11.0,6.75,4.5691,4.2608
2023-05,12.9,6.75,4.4615,4.2631
2023-06,11.5,6.75,4.4617,4.0718
2023-07,10.1,6.75,4.5208,4.0086
2023-08,9.6,6.75,4.5826,4.0671
2023-09,8.2,6.75,4.6353,4.3490
2023-10,7.8,6.75,4.3395,3.9780
2023-11,6.5,6.75,4.3652,4.0011
2023-12,6.2,5.75,4.3395,3.9780
2024-01,5.5,5.75,4.3652,4.0011
2024-02,4.9,5.75,4.3274,4.0083
2024-03,3.6,5.75,4.3074,3.9658
2024-04,3.9,5.75,4.3026,4.0106
2024-05,2.8,5.75,4.2848,3.9675
2024-06,2.6,5.75,4.3177,4.0127
2024-07,3.4,5.75,4.2811,3.9462
2024-08,3.8,5.75,4.2918,3.9020
2024-09,3.8,5.75,4.2782,3.8501
2024-10,4.2,5.75,4.3164,3.9573
2024-11,4.6,5.75,4.3339,4.0763
2024-12,4.7,5.75,4.2714,4.0787
2025-01,4.9,5.75,4.2800,4.0500
2025-02,4.9,5.75,4.2750,4.0400
2025-03,4.9,5.75,4.2700,4.0350
2025-04,4.3,5.75,4.2650,4.0320
2025-05,4.0,5.25,4.2600,4.0300"""

# ------------------------------------------------------------------
# Serie US / EA — PRZYBLIŻONE (stopy: kroki decyzji; inflacja: interpolacja
# punktów kotwicznych). Do zastąpienia własnym CSV (FRED / ECB SDW).
# ------------------------------------------------------------------
US_RATE_STEPS = [
    ("2014-01", 0.125), ("2015-12", 0.375), ("2016-12", 0.625),
    ("2017-03", 0.875), ("2017-06", 1.125), ("2017-12", 1.375),
    ("2018-03", 1.625), ("2018-06", 1.875), ("2018-09", 2.125),
    ("2018-12", 2.375), ("2019-08", 2.125), ("2019-09", 1.875),
    ("2019-10", 1.625), ("2020-03", 0.125), ("2022-03", 0.375),
    ("2022-05", 0.875), ("2022-06", 1.625), ("2022-07", 2.375),
    ("2022-09", 3.125), ("2022-11", 3.875), ("2022-12", 4.375),
    ("2023-02", 4.625), ("2023-03", 4.875), ("2023-05", 5.125),
    ("2023-07", 5.375), ("2024-09", 4.875), ("2024-11", 4.625),
    ("2024-12", 4.375),
]
ECB_RATE_STEPS = [
    ("2014-01", 0.00), ("2014-06", -0.10), ("2014-09", -0.20),
    ("2015-12", -0.30), ("2016-03", -0.40), ("2019-09", -0.50),
    ("2022-07", 0.00), ("2022-09", 0.75), ("2022-11", 1.50),
    ("2022-12", 2.00), ("2023-02", 2.50), ("2023-03", 3.00),
    ("2023-05", 3.25), ("2023-06", 3.50), ("2023-08", 3.75),
    ("2023-09", 4.00), ("2024-06", 3.75), ("2024-09", 3.50),
    ("2024-10", 3.25), ("2024-12", 3.00), ("2025-02", 2.75),
    ("2025-03", 2.50), ("2025-04", 2.25),
]
US_BKEVEN_ANCHORS = [
    ("2014-01", 2.25), ("2014-12", 1.70), ("2015-09", 1.45),
    ("2016-02", 1.20), ("2016-12", 1.95), ("2018-05", 2.15),
    ("2019-01", 1.75), ("2019-12", 1.75), ("2020-03", 0.95),
    ("2020-12", 1.95), ("2021-05", 2.50), ("2021-12", 2.55),
    ("2022-04", 2.90), ("2022-12", 2.30), ("2023-12", 2.20),
    ("2024-12", 2.30), ("2025-05", 2.30),
]
EA_HICP_ANCHORS = [
    ("2014-01", 0.8), ("2014-12", -0.2), ("2015-06", 0.2),
    ("2016-04", -0.2), ("2016-12", 1.1), ("2017-02", 2.0),
    ("2017-12", 1.4), ("2018-10", 2.2), ("2019-10", 0.7),
    ("2020-01", 1.4), ("2020-12", -0.3), ("2021-07", 2.2),
    ("2021-12", 5.0), ("2022-10", 10.6), ("2023-06", 5.5),
    ("2023-12", 2.9), ("2024-12", 2.4), ("2025-05", 1.9),
]


def _steps_to_series(dates: pd.Series, steps) -> np.ndarray:
    """Stopy procentowe: forward-fill od dat decyzji."""
    per = dates.dt.to_period("M")
    s = pd.Series({pd.Period(d, "M"): v for d, v in steps})
    full = pd.period_range(min(s.index.min(), per.min()), per.max(), freq="M")
    return s.reindex(full).ffill().reindex(per).to_numpy(dtype=float)


def _anchors_to_series(dates: pd.Series, anchors) -> np.ndarray:
    """Inflacja/breakeven: liniowa interpolacja między punktami kotwicznymi."""
    per = dates.dt.to_period("M")
    full = pd.period_range(min(pd.Period(anchors[0][0], "M"), per.min()),
                           per.max(), freq="M")
    s = pd.Series(np.nan, index=full)
    for d, v in anchors:
        s[pd.Period(d, "M")] = v
    s = s.astype(float).interpolate(method="linear", limit_direction="both")
    return s.reindex(per).to_numpy(dtype=float)


def fisher(nominal: np.ndarray, inflation: np.ndarray) -> np.ndarray:
    """Realna stopa (dokładny Fisher), w %. Jedna definicja dla wszystkich krajów."""
    return ((1 + np.asarray(nominal) / 100) / (1 + np.asarray(inflation) / 100) - 1) * 100


REQUIRED_COLS = ["date", "inflation_rate", "nbp_reference_rate", "eur_pln", "usd_pln"]
OPTIONAL_COLS = ["us_rate", "us_breakeven", "ecb_rate", "ea_hicp"]


@st.cache_data(show_spinner=False)
def build_dataset(csv_bytes: bytes | None) -> pd.DataFrame:
    if csv_bytes is not None:
        df = pd.read_csv(io.BytesIO(csv_bytes))
    else:
        df = pd.read_csv(io.StringIO(PL_CSV))

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Brak wymaganych kolumn: {', '.join(missing)}")

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # US / EA: z pliku jeśli dostarczone, inaczej serie przybliżone
    df["us_rate"] = df["us_rate"] if "us_rate" in df else _steps_to_series(df["date"], US_RATE_STEPS)
    df["ecb_rate"] = df["ecb_rate"] if "ecb_rate" in df else _steps_to_series(df["date"], ECB_RATE_STEPS)
    df["us_breakeven"] = df["us_breakeven"] if "us_breakeven" in df else _anchors_to_series(df["date"], US_BKEVEN_ANCHORS)
    df["ea_hicp"] = df["ea_hicp"] if "ea_hicp" in df else _anchors_to_series(df["date"], EA_HICP_ANCHORS)

    # Realne stopy — jedna definicja (Fisher) dla wszystkich
    df["pl_real"] = fisher(df["nbp_reference_rate"], df["inflation_rate"])
    df["ea_real"] = fisher(df["ecb_rate"], df["ea_hicp"])
    df["us_real"] = fisher(df["us_rate"], df["us_breakeven"])

    # Fundamenty: DYFERENCJAŁY (nie sama stopa PL)
    df["x_pln"] = df["pl_real"] - df["ea_real"]     # dla EUR/PLN
    df["x_eur"] = df["us_real"] - df["ea_real"]     # dla EUR/USD

    # EUR/USD wyprowadzony z krzyża (spójność trójkątna także w danych)
    df["eur_usd"] = df["eur_pln"] / df["usd_pln"]
    df["log_eurpln"] = np.log(df["eur_pln"])
    df["log_eurusd"] = np.log(df["eur_usd"])
    return df


# ------------------------------------------------------------------
# Ekonometria: OLS, test DF na resztach, ECM Engle-Grangera
# ------------------------------------------------------------------
def ols(y: np.ndarray, X: np.ndarray):
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    dof = max(n - k, 1)
    s2 = float(resid @ resid) / dof
    cov = s2 * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.maximum(np.diag(cov), 0))
    tvals = np.divide(beta, se, out=np.zeros_like(beta), where=se > 0)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - float(resid @ resid) / ss_tot if ss_tot > 0 else np.nan
    return beta, se, tvals, resid, float(np.sqrt(s2)), r2


def df_test_stat(e: np.ndarray) -> float:
    """ADF(1) na resztach kointegracyjnych, bez stałej (reszty są ~0-średnie).
    Statystykę porównujemy z wartościami krytycznymi Engle-Grangera (EG_CV)."""
    de = np.diff(e)
    if len(de) < 10:
        return np.nan
    y = de[1:]
    X = np.column_stack([e[1:-1], de[:-1]])
    _, _, t, _, _, _ = ols(y, X)
    return float(t[0])


def estimate_ecm(log_s: np.ndarray, x: np.ndarray) -> dict:
    """Dwustopniowy Engle-Granger:
    (1) log(S_t) = alpha + beta*x_t + ect_t      — relacja długookresowa
    (2) dlog(S_t) = gamma*ect_{t-1} + u_t        — korekta błędem
    """
    log_s = np.asarray(log_s, float)
    x = np.asarray(x, float)
    n = len(log_s)

    Xlr = np.column_stack([np.ones(n), x])
    b, se, t, ect, _, r2 = ols(log_s, Xlr)

    adf = df_test_stat(ect)

    ds = np.diff(log_s)
    Xe = ect[:-1].reshape(-1, 1)
    g, gse, gt, u, sigma_u, _ = ols(ds, Xe)
    gamma = float(g[0])
    rho = 1.0 + gamma
    mean_rev = -1.0 < gamma < 0.0
    halflife = float(np.log(0.5) / np.log(rho)) if mean_rev else np.inf

    if adf < EG_CV["5%"]:
        coint = "TAK (5%)"
    elif adf < EG_CV["10%"]:
        coint = "słaba (10%)"
    else:
        coint = "BRAK"

    return dict(
        alpha=float(b[0]), beta=float(b[1]), t_beta=float(t[1]), r2_level=r2,
        adf=adf, coint=coint, gamma=gamma, t_gamma=float(gt[0]),
        sigma_u=sigma_u, halflife=halflife, mean_rev=mean_rev,
        ect=ect, u=u, n=n,
    )


def fair_value(m: dict, x_scen: float) -> float:
    return float(np.exp(m["alpha"] + m["beta"] * x_scen))


def forecast_path(spot: float, fair: float, m: dict, H: int):
    """E[log S_h] i SD[log S_h] dla h = 0..H.
    Mean reversion: odchylenie d0 wygasa jak rho^h, wariancja AR(1).
    Brak korekty (gamma>=0): random walk — kurs plaski, wariancja sigma^2*h."""
    h = np.arange(H + 1, dtype=float)
    if m["mean_rev"]:
        rho = 1.0 + m["gamma"]
        d0 = np.log(spot) - np.log(fair)
        mu = np.log(fair) + d0 * rho ** h
        var = m["sigma_u"] ** 2 * (1 - rho ** (2 * h)) / (1 - rho ** 2)
    else:
        mu = np.full(H + 1, np.log(spot))
        var = m["sigma_u"] ** 2 * h
    return mu, np.sqrt(var)


def quantiles(mu: np.ndarray, sig: np.ndarray) -> dict:
    """Kwantyle log-normalne (asymetryczne w poziomach kursu)."""
    return {
        "p10": np.exp(mu - Z80 * sig), "p25": np.exp(mu - Z50 * sig),
        "central": np.exp(mu),
        "p75": np.exp(mu + Z50 * sig), "p90": np.exp(mu + Z80 * sig),
    }


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
st.sidebar.header("⚙️ Dane i estymacja")

src = st.sidebar.radio("Źródło danych", ["Wbudowane (2014–2025)", "Upload CSV"])
csv_bytes = None
if src == "Upload CSV":
    up = st.sidebar.file_uploader("Plik CSV (miesięczny)", type="csv")
    if up is not None:
        csv_bytes = up.getvalue()
    with st.sidebar.expander("Format pliku"):
        st.markdown(
            "**Wymagane:** `date, inflation_rate, nbp_reference_rate, eur_pln, usd_pln`\n\n"
            "**Opcjonalne:** `us_rate, us_breakeven, ecb_rate, ea_hicp` "
            "(brakujące zostaną uzupełnione seriami przybliżonymi)"
        )

try:
    df_all = build_dataset(csv_bytes)
except ValueError as exc:
    st.error(f"❌ {exc}")
    st.stop()

years = sorted(df_all["date"].dt.year.unique())
start_year = st.sidebar.select_slider(
    "Początek okna estymacji", options=years[:-2], value=years[0]
)
df = df_all[df_all["date"].dt.year >= start_year].reset_index(drop=True)

if len(df) < 36:
    st.error("❌ Za mało obserwacji do estymacji (minimum 36 miesięcy).")
    st.stop()

H = st.sidebar.slider("Horyzont prognozy (mies.)", 3, 36, 12)

last = df.iloc[-1]
st.sidebar.header("💱 Kursy bieżące")
spot_pln = st.sidebar.number_input("EUR/PLN spot", 3.0, 6.5, float(round(last["eur_pln"], 4)), 0.01, format="%.4f")
spot_eur = st.sidebar.number_input("EUR/USD spot", 0.8, 1.6, float(round(last["eur_usd"], 4)), 0.001, format="%.4f")
spot_usd = spot_pln / spot_eur
st.sidebar.caption(f"USD/PLN implikowany (trójkąt): **{spot_usd:.4f}**")

st.sidebar.header("🎛️ Scenariusz fundamentów")
st.sidebar.markdown("**🇵🇱 Polska**")
nbp = st.sidebar.slider("Stopa NBP (%)", 0.0, 12.0, float(round(last["nbp_reference_rate"], 2)), 0.25)
cpi = st.sidebar.slider("Inflacja CPI (%)", -2.0, 15.0, float(round(last["inflation_rate"], 1)), 0.1)
st.sidebar.markdown("**🇪🇺 Strefa euro**")
ecb = st.sidebar.slider("Stopa EBC (depo, %)", -1.0, 6.0, float(round(last["ecb_rate"], 2)), 0.25)
hicp = st.sidebar.slider("Inflacja HICP (%)", -1.0, 12.0, float(round(last["ea_hicp"], 1)), 0.1)
st.sidebar.markdown("**🇺🇸 USA**")
fed = st.sidebar.slider("Fed funds (%)", 0.0, 8.0, float(round(last["us_rate"], 2)), 0.25)
bkeven = st.sidebar.slider("Breakeven 10Y (%)", 0.0, 5.0, float(round(last["us_breakeven"], 1)), 0.1)

pl_real_s = float(fisher(nbp, cpi))
ea_real_s = float(fisher(ecb, hicp))
us_real_s = float(fisher(fed, bkeven))
x_pln_s = pl_real_s - ea_real_s
x_eur_s = us_real_s - ea_real_s

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"**Realne stopy (scenariusz):**\n\n"
    f"PL: {pl_real_s:+.2f}% | EA: {ea_real_s:+.2f}% | US: {us_real_s:+.2f}%\n\n"
    f"Dyferencjał PL−EA: **{x_pln_s:+.2f} pp**\n\n"
    f"Dyferencjał US−EA: **{x_eur_s:+.2f} pp**"
)

# ------------------------------------------------------------------
# Estymacja i prognoza
# ------------------------------------------------------------------
m_pln = estimate_ecm(df["log_eurpln"].to_numpy(), df["x_pln"].to_numpy())
m_eur = estimate_ecm(df["log_eurusd"].to_numpy(), df["x_eur"].to_numpy())

# korelacja reszt ECM (wspólne szoki) — do wariancji USD/PLN
res_corr = float(np.corrcoef(m_pln["u"], m_eur["u"])[0, 1])

fair_pln = fair_value(m_pln, x_pln_s)
fair_eur = fair_value(m_eur, x_eur_s)
fair_usd = fair_pln / fair_eur

mu_p, sig_p = forecast_path(spot_pln, fair_pln, m_pln, H)
mu_e, sig_e = forecast_path(spot_eur, fair_eur, m_eur, H)

# USD/PLN = EUR/PLN / EUR/USD  →  log-różnica; wariancja z korelacją reszt
mu_u = mu_p - mu_e
sig_u = np.sqrt(np.maximum(sig_p ** 2 + sig_e ** 2 - 2 * res_corr * sig_p * sig_e, 0))

q_p, q_e, q_u = quantiles(mu_p, sig_p), quantiles(mu_e, sig_e), quantiles(mu_u, sig_u)

t0 = pd.Timestamp.today().normalize()
fdates = pd.date_range(t0, periods=H + 1, freq=pd.DateOffset(months=1))

# ------------------------------------------------------------------
# Nagłówek + karty
# ------------------------------------------------------------------
st.title("📉 FX ECM Forecaster")
st.markdown(
    "**Model korekty błędem (Engle–Granger)** — parametry estymowane z danych, "
    "przedziały rosnące z horyzontem, USD/PLN wyprowadzany z trójkąta walutowego."
)
st.info(
    "ℹ️ Serie stóp i inflacji US/EA są **przybliżone** (kroki decyzji + interpolacja). "
    "Do użytku produkcyjnego podmień je własnym CSV (FRED: DFF, T10YIE; ECB SDW: DFR, HICP).",
    icon="ℹ️",
)


def card(col, name, color, spot, fair, q, m_or_none, dec_places=4):
    dev = (spot / fair - 1) * 100
    c, lo, hi = q["central"][H], q["p25"][H], q["p75"][H]
    chg = (c / spot - 1) * 100
    extra = ""
    if m_or_none is not None:
        hl = m_or_none["halflife"]
        hl_txt = f"{hl:.1f} mies." if np.isfinite(hl) else "∞ (random walk)"
        extra = (f"<p style='font-size:0.8em;color:#666;margin:4px 0;'>"
                 f"kointegracja: {m_or_none['coint']} | half-life: {hl_txt}</p>")
    else:
        extra = ("<p style='font-size:0.8em;color:#666;margin:4px 0;'>"
                 "wyprowadzony: EUR/PLN ÷ EUR/USD</p>")
    with col:
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,{color}18,{color}08);padding:18px;
                        border-radius:14px;border:2px solid {color}40;text-align:center;">
              <h3 style="color:{color};margin:0;">{name}</h3>
              <p style="margin:6px 0;color:#666;">spot: {spot:.{dec_places}f} |
                 fair value: <b>{fair:.{dec_places}f}</b></p>
              <p style="margin:4px 0;font-size:0.95em;">odchylenie od równowagi:
                 <b style="color:{'#dc2626' if dev>0 else '#059669'}">{dev:+.2f}%</b></p>
              <h1 style="color:{color};margin:8px 0;font-size:2.1em;">{c:.{dec_places}f}</h1>
              <p style="margin:2px 0;color:#666;">prognoza {H}M ({chg:+.2f}%)</p>
              <p style="margin:4px 0;">zakres 50%: <b>{lo:.{dec_places}f} – {hi:.{dec_places}f}</b></p>
              {extra}
            </div>
            """,
            unsafe_allow_html=True,
        )


c1, c2, c3 = st.columns(3)
card(c1, "EUR/PLN", PHC, spot_pln, fair_pln, q_p, m_pln)
card(c2, "EUR/USD", BLU, spot_eur, fair_eur, q_e, m_eur)
card(c3, "USD/PLN", GRN, spot_usd, fair_usd, q_u, None)

for name, m in (("EUR/PLN", m_pln), ("EUR/USD", m_eur)):
    if m["coint"] == "BRAK":
        st.warning(
            f"⚠️ **{name}:** test DF nie odrzuca braku kointegracji "
            f"(ADF = {m['adf']:.2f} > {EG_CV['10%']:.2f}). Fair value i prognozę "
            f"powrotu traktuj ostrożnie.", icon="⚠️")
    if not m["mean_rev"]:
        st.warning(
            f"⚠️ **{name}:** γ = {m['gamma']:+.3f} — brak korekty błędem w próbie; "
            f"prognoza centralna = random walk (kurs bieżący).", icon="⚠️")

# ------------------------------------------------------------------
# Wykresy i tabele
# ------------------------------------------------------------------
def fan_fig(hist_dates, hist_vals, q, color, title, fair, hist_months=36):
    hd = hist_dates[-hist_months:]
    hv = hist_vals[-hist_months:]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(fdates) + list(fdates[::-1]),
        y=list(q["p10"]) + list(q["p90"][::-1]),
        fill="toself", fillcolor=f"rgba{tuple(int(color[i:i+2],16) for i in (1,3,5)) + (0.10,)}",
        line=dict(width=0), name="zakres 80% (P10–P90)", hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=list(fdates) + list(fdates[::-1]),
        y=list(q["p25"]) + list(q["p75"][::-1]),
        fill="toself", fillcolor=f"rgba{tuple(int(color[i:i+2],16) for i in (1,3,5)) + (0.22,)}",
        line=dict(width=0), name="zakres 50% (P25–P75)", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=hd, y=hv, name="historia",
                             line=dict(color="#94a3b8", width=2)))
    fig.add_trace(go.Scatter(x=fdates, y=q["central"], name="prognoza centralna",
                             line=dict(color=color, width=4), mode="lines"))
    fig.add_hline(y=fair, line_dash="dash", line_color="#64748b",
                  annotation_text=f"fair value {fair:.4f}",
                  annotation_position="bottom right")
    fig.update_layout(title=title, height=480, hovermode="x unified",
                      legend=dict(orientation="h", y=1.08))
    return fig


def horizon_table(q, dec=4):
    hs = sorted({h for h in (1, 3, 6, 12, 24, H) if 0 < h <= H})
    rows = []
    for h in hs:
        rows.append({
            "Horyzont": f"{h}M",
            "P10": round(q["p10"][h], dec), "P25": round(q["p25"][h], dec),
            "Centralna": round(q["central"][h], dec),
            "P75": round(q["p75"][h], dec), "P90": round(q["p90"][h], dec),
            "Szer. 50% (%)": round((q["p75"][h] / q["p25"][h] - 1) * 100, 2),
        })
    return pd.DataFrame(rows)


tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📈 EUR/PLN", "📈 EUR/USD", "📈 USD/PLN (trójkąt)", "🔬 Diagnostyka", "📄 Dane"])

with tab1:
    st.plotly_chart(fan_fig(df["date"], df["eur_pln"], q_p, PHC,
                            f"EUR/PLN — ECM | dyferencjał PL−EA: {x_pln_s:+.2f} pp",
                            fair_pln), width="stretch")
    st.dataframe(horizon_table(q_p), width="stretch", hide_index=True)
    st.caption("Szerokość pasma rośnie z horyzontem: Var(h) = σ²·(1−ρ²ʰ)/(1−ρ²) "
               "≈ σ²·h dla małych h, z plateau na wariancji bezwarunkowej.")

with tab2:
    st.plotly_chart(fan_fig(df["date"], df["eur_usd"], q_e, BLU,
                            f"EUR/USD — ECM | dyferencjał US−EA: {x_eur_s:+.2f} pp",
                            fair_eur), width="stretch")
    st.dataframe(horizon_table(q_e), width="stretch", hide_index=True)
    st.caption("Seria historyczna EUR/USD wyprowadzona z krzyża EUR/PLN ÷ USD/PLN — "
               "dziedziczy jakość danych PLN.")

with tab3:
    st.plotly_chart(fan_fig(df["date"], df["eur_pln"] / df["eur_usd"], q_u, GRN,
                            "USD/PLN — wyprowadzony z trójkąta (EUR/PLN ÷ EUR/USD)",
                            fair_usd), width="stretch")
    st.dataframe(horizon_table(q_u), width="stretch", hide_index=True)
    st.caption(f"Wariancja: σ²ᵤ = σ²ₚ + σ²ₑ − 2·ρ·σₚ·σₑ, "
               f"korelacja reszt ECM ρ = {res_corr:+.2f}. "
               f"Prognozy trzech par są z konstrukcji spójne: USD/PLN = EUR/PLN ÷ EUR/USD "
               f"na każdym horyzoncie.")

with tab4:
    st.markdown("### Parametry estymowane z danych "
                f"(okno: {start_year}–{df['date'].dt.year.max()}, n = {len(df)})")

    def fmt_hl(m):
        return f"{m['halflife']:.1f}" if np.isfinite(m["halflife"]) else "∞"

    diag = pd.DataFrame({
        "Parametr": [
            "α (stała, log)", "β (wrażliwość na dyferencjał)", "t-stat β",
            "R² (poziomy — tylko opisowo)", "ADF na resztach", "Kointegracja",
            "γ (szybkość korekty)", "t-stat γ", "Half-life (mies.)",
            "σ miesięczna (reszty ECM, %)", "σ roczna (%)",
        ],
        "EUR/PLN": [
            f"{m_pln['alpha']:.4f}", f"{m_pln['beta']:+.4f}", f"{m_pln['t_beta']:.2f}",
            f"{m_pln['r2_level']*100:.1f}%", f"{m_pln['adf']:.2f}", m_pln["coint"],
            f"{m_pln['gamma']:+.4f}", f"{m_pln['t_gamma']:.2f}", fmt_hl(m_pln),
            f"{m_pln['sigma_u']*100:.2f}", f"{m_pln['sigma_u']*np.sqrt(12)*100:.2f}",
        ],
        "EUR/USD": [
            f"{m_eur['alpha']:.4f}", f"{m_eur['beta']:+.4f}", f"{m_eur['t_beta']:.2f}",
            f"{m_eur['r2_level']*100:.1f}%", f"{m_eur['adf']:.2f}", m_eur["coint"],
            f"{m_eur['gamma']:+.4f}", f"{m_eur['t_gamma']:.2f}", fmt_hl(m_eur),
            f"{m_eur['sigma_u']*100:.2f}", f"{m_eur['sigma_u']*np.sqrt(12)*100:.2f}",
        ],
    })
    st.dataframe(diag, width="stretch", hide_index=True)
    st.caption(
        f"Wartości krytyczne Engle–Grangera (2 zmienne, stała): "
        f"1%: {EG_CV['1%']} | 5%: {EG_CV['5%']} | 10%: {EG_CV['10%']}. "
        f"Korelacja reszt ECM (EUR/PLN vs EUR/USD): {res_corr:+.2f}. "
        f"t-stat β na poziomach jest zawyżony (autokorelacja reszt) — o wiarygodności "
        f"relacji decyduje test kointegracji i t-stat γ, nie t-stat β."
    )

    st.markdown("### Fair value vs kurs rzeczywisty (w oknie estymacji)")
    colA, colB = st.columns(2)
    for col, name, m, xcol, scol, color in (
        (colA, "EUR/PLN", m_pln, "x_pln", "eur_pln", PHC),
        (colB, "EUR/USD", m_eur, "x_eur", "eur_usd", BLU),
    ):
        fitted = np.exp(m["alpha"] + m["beta"] * df[xcol].to_numpy())
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["date"], y=df[scol], name="kurs",
                                 line=dict(color="#94a3b8", width=2)))
        fig.add_trace(go.Scatter(x=df["date"], y=fitted, name="fair value (model)",
                                 line=dict(color=color, width=2, dash="dash")))
        fig.update_layout(title=name, height=360,
                          legend=dict(orientation="h", y=1.12))
        col.plotly_chart(fig, width="stretch")

    st.markdown("### Odchylenie od równowagi (ECT) w czasie")
    fig_ect = go.Figure()
    fig_ect.add_trace(go.Scatter(x=df["date"], y=m_pln["ect"] * 100,
                                 name="EUR/PLN", line=dict(color=PHC, width=2)))
    fig_ect.add_trace(go.Scatter(x=df["date"], y=m_eur["ect"] * 100,
                                 name="EUR/USD", line=dict(color=BLU, width=2)))
    fig_ect.add_hline(y=0, line_dash="dash", line_color="gray")
    fig_ect.update_layout(height=360, yaxis_title="odchylenie (%)",
                          legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig_ect, width="stretch")

with tab5:
    st.markdown("### Zbiór danych użyty do estymacji")
    show_cols = ["date", "eur_pln", "usd_pln", "eur_usd", "inflation_rate",
                 "nbp_reference_rate", "pl_real", "ecb_rate", "ea_hicp", "ea_real",
                 "us_rate", "us_breakeven", "us_real", "x_pln", "x_eur"]
    st.dataframe(df[show_cols].round(4), width="stretch", hide_index=True)
    st.download_button(
        "⬇️ Pobierz dane (CSV)",
        df[show_cols].to_csv(index=False).encode(),
        file_name="fx_ecm_dataset.csv", mime="text/csv",
    )
    fig_x = go.Figure()
    fig_x.add_trace(go.Scatter(x=df["date"], y=df["x_pln"], name="dyferencjał PL−EA",
                               line=dict(color=PHC, width=2)))
    fig_x.add_trace(go.Scatter(x=df["date"], y=df["x_eur"], name="dyferencjał US−EA",
                               line=dict(color=BLU, width=2)))
    fig_x.add_hline(y=0, line_dash="dash", line_color="gray")
    fig_x.update_layout(title="Fundamenty (realne dyferencjały stóp)", height=380,
                        yaxis_title="pp", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_x, width="stretch")

# ------------------------------------------------------------------
# Założenia i ograniczenia
# ------------------------------------------------------------------
st.markdown("---")
with st.expander("📋 Założenia, ograniczenia i następne kroki"):
    st.markdown(f"""
**Mechanika modelu**
1. Relacja długookresowa: `log(kurs) = α + β · dyferencjał realnych stóp` (Engle–Granger, krok 1).
2. Test DF na resztach vs wartości krytyczne E-G → czy fair value ma sens statystyczny.
3. ECM: `Δlog(kurs) = γ · odchylenie(t−1) + u` — kurs reaguje **tylko** gdy odjechał od równowagi
   (naprawia podwójne liczenie dyferencjału ze starego modelu).
4. Prognoza: odchylenie bieżącego spotu od fair value wygasa w tempie `ρ = 1+γ` (half-life z danych).
5. Przedziały: log-normalne, `σ(h)² = σ²·(1−ρ²ʰ)/(1−ρ²)` — rosną ~√h, plateau na wariancji bezwarunkowej.
6. USD/PLN nie jest osobno modelowany: `USD/PLN = EUR/PLN ÷ EUR/USD` na każdym horyzoncie,
   z wariancją uwzględniającą korelację reszt ({res_corr:+.2f}).

**Ograniczenia (świadome)**
- Serie US/EA są przybliżone (kroki decyzji + interpolacja) — podmień przez upload CSV.
- Wbudowane dane PLN zawierają powtórzone wartości w różnych okresach (jakość źródła) —
  estymacja je dziedziczy; zalecany upload czystych danych NBP.
- Inflacja PL/EA to CPI/HICP wstecz, US to breakeven (oczekiwania) — do ujednolicenia
  po podpięciu żywych danych (swapy inflacyjne / projekcje).
- Scenariusz zakłada stały dyferencjał w horyzoncie prognozy (brak ścieżki stóp).

**Następne kroki (priorytety 5-8 z analizy)**
- Benchmark out-of-sample vs forward (CIP) i random walk (RMSE) — kluczowe biznesowo.
- Żywe dane: NBP API (Tabela A), FRED (DFF, T10YIE), ECB SDW (DFR, HICP).
- Backtest pokrycia przedziałów (czy pasmo 50% łapie ~50% realizacji).
""")

st.markdown(
    f"""<div style="text-align:center;color:#666;font-size:0.85em;">
    FX ECM Forecaster | Engle–Granger ECM, estymacja w aplikacji, spójny trójkąt walutowy<br>
    ⚠️ Prognozy mają charakter informacyjny i nie stanowią rekomendacji inwestycyjnej
    </div>""",
    unsafe_allow_html=True,
)
