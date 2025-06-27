import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta
import io

# Konfiguracja strony
st.set_page_config(
    page_title="Symulator Kursów Walut",
    page_icon="💱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ładowanie danych
@st.cache_data
def load_data():
    data = """date,year,month,inflation_rate,nbp_reference_rate,real_interest_rate,eur_pln,usd_pln,gbp_pln
2014-01,2014,1,0.5,2.50,1.99,4.1776,3.0650,5.0507
2014-02,2014,2,0.7,2.50,1.78,4.1786,3.0613,5.0658
2014-03,2014,3,0.7,2.50,1.78,4.1972,3.0378,5.0525
2014-04,2014,4,0.3,2.50,2.19,4.1841,3.0293,5.0720
2014-05,2014,5,0.2,2.50,2.29,4.1594,3.0234,5.1447
2014-06,2014,6,0.3,2.50,2.19,4.1659,3.0381,5.1028
2014-07,2014,7,-0.2,2.50,2.72,4.1773,3.0456,5.1294
2014-08,2014,8,-0.3,2.50,2.82,4.1856,3.0723,5.1673
2014-09,2014,9,-0.3,2.50,2.82,4.1953,3.1249,5.0926
2014-10,2014,10,-0.6,2.50,3.13,4.2071,3.1657,5.0338
2014-11,2014,11,-0.6,2.50,3.13,4.2389,3.2847,5.1347
2014-12,2014,12,-1.0,2.50,3.54,4.2623,3.5072,5.4859
2015-01,2015,1,-1.4,2.00,3.45,4.2538,3.6403,5.4537
2015-02,2015,2,-1.6,2.00,3.65,4.0934,3.6587,5.6234
2015-03,2015,3,-1.5,1.50,3.05,4.0678,3.7188,5.5694
2015-04,2015,4,-1.1,1.50,2.65,4.0853,3.7540,5.4783
2015-05,2015,5,-0.9,1.50,2.44,4.1078,3.6738,5.5462
2015-06,2015,6,-0.8,1.50,2.33,4.1856,3.8268,5.8847
2015-07,2015,7,-0.7,1.50,2.22,4.1302,3.7635,5.7331
2015-08,2015,8,-0.6,1.50,2.12,4.2247,3.9513,6.0863
2015-09,2015,9,-0.8,1.50,2.33,4.2655,4.0371,6.0432
2015-10,2015,10,-0.7,1.50,2.22,4.2839,3.9276,5.9841
2015-11,2015,11,-0.6,1.50,2.12,4.3211,3.9060,5.9234
2015-12,2015,12,-0.5,1.50,2.01,4.2639,3.9011,5.7847
2016-01,2016,1,-0.8,1.50,2.33,4.3616,4.0044,5.7662
2016-02,2016,2,-0.8,1.50,2.33,4.3438,3.7584,5.4011
2016-03,2016,3,-0.9,1.50,2.44,4.3732,3.7643,5.2697
2016-04,2016,4,-1.1,1.50,2.65,4.3947,3.7899,5.4474
2016-05,2016,5,-0.8,1.50,2.33,4.4259,3.9671,5.8677
2016-06,2016,6,-0.8,1.50,2.33,4.4240,3.9780,5.8935
2016-07,2016,7,-0.8,1.50,2.33,4.3284,3.9533,5.2133
2016-08,2016,8,-0.8,1.50,2.33,4.3567,3.9311,5.1623
2016-09,2016,9,-0.5,1.50,2.01,4.3123,3.8501,4.9894
2016-10,2016,10,-0.2,1.50,1.70,4.2969,3.8332,4.7775
2016-11,2016,11,-0.4,1.50,1.91,4.4588,3.7584,4.6327
2016-12,2016,12,-0.5,1.50,2.01,4.4240,4.1793,5.1323
2017-01,2017,1,-0.2,1.50,1.70,4.3135,3.8581,4.8181
2017-02,2017,2,0.1,1.50,1.39,4.3011,3.7840,4.7319
2017-03,2017,3,1.4,1.50,0.10,4.2247,3.8090,4.7169
2017-04,2017,4,1.7,1.50,-0.17,4.2291,3.7963,4.6568
2017-05,2017,5,1.6,1.50,-0.10,4.1953,3.7635,4.6611
2017-06,2017,6,1.8,1.50,-0.29,4.2291,3.7963,4.8611
2017-07,2017,7,1.6,1.50,-0.10,4.2655,3.8268,4.9519
2017-08,2017,8,1.4,1.50,0.10,4.2839,3.9276,5.1321
2017-09,2017,9,1.2,1.50,0.30,4.3211,3.9060,5.3541
2017-10,2017,10,1.1,1.50,0.40,4.2969,3.8332,5.2133
2017-11,2017,11,1.2,1.50,0.30,4.2389,3.7584,5.1623
2017-12,2017,12,1.0,1.50,0.50,4.1709,3.4813,4.6568
2018-01,2018,1,1.2,1.50,0.30,4.1497,3.4138,4.6543
2018-02,2018,2,1.4,1.50,0.10,4.1856,3.4427,4.7775
2018-03,2018,3,1.3,1.50,0.20,4.2071,3.4250,4.8846
2018-04,2018,4,1.7,1.50,-0.17,4.2247,3.4427,4.8957
2018-05,2018,5,1.7,1.50,-0.17,4.3618,3.7348,4.8846
2018-06,2018,6,1.7,1.50,-0.17,4.3618,3.7348,4.8846
2018-07,2018,7,1.9,1.50,-0.39,4.2655,3.8268,4.9519
2018-08,2018,8,2.0,1.50,-0.49,4.2839,3.9276,5.1321
2018-09,2018,9,1.4,1.50,0.10,4.3211,3.9060,5.3541
2018-10,2018,10,1.2,1.50,0.30,4.2969,3.8332,5.2133
2018-11,2018,11,1.3,1.50,0.20,4.2389,3.7584,5.1623
2018-12,2018,12,1.1,1.50,0.40,4.2669,3.7597,4.7775
2019-01,2019,1,0.7,1.50,0.79,4.2615,3.7643,4.8025
2019-02,2019,2,1.2,1.50,0.30,4.3011,3.7840,4.7319
2019-03,2019,3,1.7,1.50,-0.17,4.2247,3.8090,4.7169
2019-04,2019,4,2.2,1.50,-0.69,4.2291,3.7963,4.6568
2019-05,2019,5,2.3,1.50,-0.78,4.2655,3.7635,4.6611
2019-06,2019,6,1.0,1.50,0.50,4.2687,3.9311,4.9975
2019-07,2019,7,0.5,1.50,0.99,4.2839,3.9276,4.9519
2019-08,2019,8,0.4,1.50,1.09,4.3211,3.9060,4.8321
2019-09,2019,9,0.5,1.50,0.99,4.3732,3.8501,4.9894
2019-10,2019,10,0.4,1.50,1.09,4.2969,3.8332,4.8133
2019-11,2019,11,0.6,1.50,0.89,4.2389,3.7584,4.6327
2019-12,2019,12,1.3,1.50,0.20,4.2568,3.7977,4.9988
2020-01,2020,1,3.2,1.50,-1.68,4.2597,3.7282,4.8957
2020-02,2020,2,3.7,1.50,-2.16,4.3011,3.7840,4.7319
2020-03,2020,3,3.2,1.00,-2.13,4.5523,4.1044,5.1321
2020-04,2020,4,3.4,0.50,-2.80,4.5268,4.0776,5.0511
2020-05,2020,5,3.4,0.10,-3.19,4.4584,4.0408,4.9519
2020-06,2020,6,3.3,0.10,-3.10,4.4588,3.9680,4.9894
2020-07,2020,7,3.6,0.10,-3.39,4.4240,3.9533,5.1327
2020-08,2020,8,3.8,0.10,-3.58,4.4259,3.9671,5.2133
2020-09,2020,9,3.2,0.10,-3.00,4.5268,3.9780,5.3541
2020-10,2020,10,3.1,0.10,-2.90,4.4584,4.0408,5.4924
2020-11,2020,11,3.0,0.10,-2.81,4.4588,3.9680,5.4407
2020-12,2020,12,3.7,0.10,-3.49,4.6148,3.7584,5.1327
2021-01,2021,1,2.6,0.10,-2.44,4.5826,3.8332,5.2288
2021-02,2021,2,2.4,0.10,-2.24,4.1856,3.8090,5.5462
2021-03,2021,3,3.2,0.10,-3.00,4.6525,4.2030,5.5389
2021-04,2021,4,4.6,0.10,-4.37,4.1953,3.7635,5.4783
2021-05,2021,5,4.4,0.10,-4.18,4.4259,3.9671,5.8677
2021-06,2021,6,4.1,0.10,-3.85,4.5208,3.7840,5.3118
2021-07,2021,7,4.8,0.10,-4.57,4.5826,3.8332,5.2288
2021-08,2021,8,5.2,0.10,-4.96,4.6856,4.0671,5.4407
2021-09,2021,9,5.8,0.10,-5.54,4.6184,4.0086,5.4924
2021-10,2021,10,5.9,0.50,-5.10,4.6184,4.0086,5.4924
2021-11,2021,11,6.8,1.25,-5.20,4.6856,4.0671,5.4407
2021-12,2021,12,8.6,1.75,-6.31,4.5994,4.0600,5.4542
2022-01,2022,1,9.4,2.25,-6.54,4.5969,4.0683,5.4781
2022-02,2022,2,8.5,2.75,-5.33,4.6939,4.0687,5.4624
2022-03,2022,3,10.9,3.50,-6.67,4.6525,4.2030,5.5389
2022-04,2022,4,12.4,4.50,-7.19,4.6560,4.5267,5.6626
2022-05,2022,5,13.5,5.25,-7.43,4.5691,4.2608,5.3329
2022-06,2022,6,11.8,6.00,-5.19,4.4615,4.2631,5.2832
2022-07,2022,7,10.8,6.00,-4.34,4.7011,4.7169,5.5786
2022-08,2022,8,10.1,6.00,-3.73,4.6939,4.5267,5.4624
2022-09,2022,9,10.7,6.75,-3.57,4.8694,4.8574,5.5331
2022-10,2022,10,8.2,6.75,-1.34,4.7392,4.9894,5.6786
2022-11,2022,11,7.8,6.75,-0.90,4.6939,4.7169,5.5786
2022-12,2022,12,7.5,6.75,-0.70,4.6808,4.4018,5.3541
2023-01,2023,1,6.6,6.75,0.14,4.7047,4.4541,5.4851
2023-02,2023,2,6.0,6.75,0.71,4.6939,4.4018,5.3541
2023-03,2023,3,6.1,6.75,0.61,4.6808,4.4541,5.4851
2023-04,2023,4,11.0,6.75,-3.89,4.5691,4.2608,5.3329
2023-05,2023,5,12.9,6.75,-5.45,4.4615,4.2631,5.2832
2023-06,2023,6,11.5,6.75,-4.26,4.4617,4.0718,5.1690
2023-07,2023,7,10.1,6.75,-3.05,4.5208,4.0086,5.2288
2023-08,2023,8,9.6,6.75,-2.60,4.5826,4.0671,5.4407
2023-09,2023,9,8.2,6.75,-1.34,4.6353,4.3490,5.3749
2023-10,2023,10,7.8,6.75,-0.90,4.3395,3.9780,5.0523
2023-11,2023,11,6.5,6.75,0.23,4.3652,4.0011,5.0827
2023-12,2023,12,6.2,5.75,-0.42,4.3395,3.9780,5.0523
2024-01,2024,1,5.5,5.75,0.24,4.3652,4.0011,5.0827
2024-02,2024,2,4.9,5.75,0.82,4.3274,4.0083,5.0645
2024-03,2024,3,3.6,5.75,2.07,4.3074,3.9658,5.0357
2024-04,2024,4,3.9,5.75,1.79,4.3026,4.0106,5.0247
2024-05,2024,5,2.8,5.75,2.87,4.2848,3.9675,5.0075
2024-06,2024,6,2.6,5.75,3.07,4.3177,4.0127,5.1000
2024-07,2024,7,3.4,5.75,2.27,4.2811,3.9462,5.0749
2024-08,2024,8,3.8,5.75,1.88,4.2918,3.9020,5.0437
2024-09,2024,9,3.8,5.75,1.88,4.2782,3.8501,5.0905
2024-10,2024,10,4.2,5.75,1.49,4.3164,3.9573,5.1676
2024-11,2024,11,4.6,5.75,1.10,4.3339,4.0763,5.1980
2024-12,2024,12,4.7,5.75,0.98,4.2714,4.0787,5.1535
2025-01,2025,1,4.9,5.75,0.82,4.2800,4.0500,5.1200
2025-02,2025,2,4.9,5.75,0.82,4.2750,4.0400,5.1100
2025-03,2025,3,4.9,5.75,0.82,4.2700,4.0350,5.1050
2025-04,2025,4,4.3,5.75,1.39,4.2650,4.0320,5.1020
2025-05,2025,5,4.0,5.25,1.20,4.2600,4.0300,5.1000"""
    return pd.read_csv(io.StringIO(data))

# Ładowanie danych
df = load_data()

# Tytuł
st.title("💱 Symulator Kursów Walut - Polska")
st.markdown("### Interaktywny panel do analizy wpływu stóp procentowych i inflacji na kursy PLN")

# Panel boczny
st.sidebar.header("🎛️ Panel Sterowania")

# Obecne kursy spot
st.sidebar.markdown("### 💱 Obecne Kursy Walut")
col1, col2 = st.sidebar.columns(2)

with col1:
    current_eur = st.number_input("EUR/PLN", min_value=3.50, max_value=6.00, value=4.27, step=0.01, format="%.4f", help="Obecny kurs EUR/PLN")
    current_usd = st.number_input("USD/PLN", min_value=3.00, max_value=6.00, value=4.08, step=0.01, format="%.4f", help="Obecny kurs USD/PLN")

with col2:
    current_gbp = st.number_input("GBP/PLN", min_value=4.00, max_value=7.00, value=5.15, step=0.01, format="%.4f", help="Obecny kurs GBP/PLN")
    if st.button("📊 Użyj Kursów NBP"):
        st.rerun()

# Warunki rynkowe
st.sidebar.markdown("### 📈 Warunki Rynkowe")
inflation_rate = st.sidebar.slider("Inflacja Bazowa (%)", -3.0, 15.0, 4.0, 0.1, help="Roczna inflacja bazowa")
nominal_rate = st.sidebar.slider("Stopa Referencyjna NBP (%)", 0.0, 12.0, 5.75, 0.25, help="Stopa referencyjna Narodowego Banku Polskiego")
time_horizon = st.sidebar.slider("Horyzont Prognozy (miesiące)", 3, 24, 12, help="Długość prognozy kursów walut")

# Obliczanie realnej stopy procentowej
real_rate = ((1 + nominal_rate/100) / (1 + inflation_rate/100) - 1) * 100

# Wyświetlanie w panelu bocznym
st.sidebar.markdown(f"**Realna Stopa: {real_rate:.2f}%**")

# Funkcja predykcyjna
def predict_exchange_rates(real_rate, current_rates):
    sensitivity = {
        "EUR": {"real": -0.12, "uncertainty": 0.03}, 
        "USD": {"real": -0.18, "uncertainty": 0.05}, 
        "GBP": {"real": -0.15, "uncertainty": 0.04}
    }
    
    results = {}
    for currency in current_rates:
        impact = (real_rate - 0.98) * sensitivity[currency]["real"]
        central = current_rates[currency] + impact
        
        model_std = sensitivity[currency]["uncertainty"] * central
        p10 = central - 1.28 * model_std
        p25 = central - 0.67 * model_std
        p75 = central + 0.67 * model_std
        p90 = central + 1.28 * model_std
        
        change = ((central - current_rates[currency]) / current_rates[currency]) * 100
        
        results[currency] = {
            "central": central,
            "p10": p10,
            "p25": p25,
            "p75": p75,
            "p90": p90,
            "change": change,
            "uncertainty": sensitivity[currency]["uncertainty"] * 100,
            "current": current_rates[currency]
        }
    
    return results

# Pobranie predykcji
current_rates = {"EUR": current_eur, "USD": current_usd, "GBP": current_gbp}
predictions = predict_exchange_rates(real_rate, current_rates)

# Piękne karty predykcji
st.markdown("---")
st.markdown("## 💱 Prognozowane Kursy Walut")

col1, col2, col3 = st.columns(3)
currencies = ["EUR", "USD", "GBP"]
color = "#2e68a5"  # Jednolity kolor dla wszystkich walut

for i, currency in enumerate(currencies):
    with [col1, col2, col3][i]:
        pred = predictions[currency]
        
        card_html = f"""
        <div style="
            background: linear-gradient(135deg, {color}20, {color}10);
            padding: 20px;
            border-radius: 15px;
            border: 2px solid {color}40;
            text-align: center;
            margin-bottom: 10px;
        ">
            <h3 style="color: {color}; margin: 0; font-size: 1.5em;">{currency}/PLN</h3>
            <h1 style="color: {color}; margin: 10px 0; font-size: 2.5em;">
                {pred['central']:.4f}
            </h1>
            <p style="margin: 5px 0; font-size: 0.9em; color: #666;">
                Obecny: {pred['current']:.4f}
            </p>
            <p style="margin: 5px 0; font-size: 1.1em;">
                <strong>Zmiana: {'🔴' if pred['change'] >= 0 else '🟢'} {pred['change']:+.1f}%</strong>
            </p>
            <p style="margin: 5px 0; font-size: 0.9em; color: #666;">
                Niepewność Modelu: ±{pred['uncertainty']:.1f}%
            </p>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
        
        # Zakresy percentyli
        st.markdown(f"""
        **📊 Zakres Ufności @ {real_rate:.1f}% realnej stopy:**
        - **25. percentyl**: {pred['p25']:.4f} (prawdopodobnie niski)
        - **75. percentyl**: {pred['p75']:.4f} (prawdopodobnie wysoki)
        - **90. percentyl**: {pred['p90']:.4f} (scenariusz wysoki)
        
        **🎯 Najbardziej Prawdopodobny**: {pred['p25']:.4f} - {pred['p75']:.4f} (50% ufności)
        """)

# Sekcja wykresów
st.markdown("---")
st.markdown("## 📊 Wykresy Analityczne")

tab1, tab2, tab3 = st.tabs(["📈 Prognoza", "📊 Analiza Wrażliwości", "🔍 Dane Historyczne"])

with tab1:
    st.markdown("### Prognoza Kursów Walut w Czasie")
    
    # Generowanie projekcji
    dates = [datetime.now() + timedelta(days=30*i) for i in range(time_horizon + 1)]
    projection_data = []
    
    for i, date in enumerate(dates):
        adjustment = min(i / 6, 1)
        projection_data.append({
            "Miesiąc": i,
            "Data": date.strftime("%Y-%m"),
            "EUR": current_eur + (predictions["EUR"]["central"] - current_eur) * adjustment,
            "USD": current_usd + (predictions["USD"]["central"] - current_usd) * adjustment,
            "GBP": current_gbp + (predictions["GBP"]["central"] - current_gbp) * adjustment
        })
    
    df_proj = pd.DataFrame(projection_data)
    
    # Tworzenie wykresu z nowym kolorem
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_proj["Miesiąc"], y=df_proj["EUR"], name="EUR/PLN", line=dict(color=color, width=3), mode='lines+markers'))
    fig.add_trace(go.Scatter(x=df_proj["Miesiąc"], y=df_proj["USD"], name="USD/PLN", line=dict(color=color, width=3, dash='dash'), mode='lines+markers'))
    fig.add_trace(go.Scatter(x=df_proj["Miesiąc"], y=df_proj["GBP"], name="GBP/PLN", line=dict(color=color, width=3, dash='dot'), mode='lines+markers'))
    
    # Skalowanie osi
    all_values = list(df_proj["EUR"]) + list(df_proj["USD"]) + list(df_proj["GBP"])
    y_min = min(all_values) * 0.99
    y_max = max(all_values) * 1.01
    
    fig.update_layout(
        title=f"Prognoza Kursów Walut - {time_horizon} Miesięcy",
        xaxis_title="Miesiące od Teraz",
        yaxis_title="Kurs Walutowy (PLN)",
        yaxis=dict(range=[y_min, y_max], tickformat='.2f'),
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Dodawanie pasm percentyli
    projection_with_bands = df_proj.copy()
    
    for i, row in projection_with_bands.iterrows():
        adjustment = min(i / 6, 1)
        for currency in ["EUR", "USD", "GBP"]:
            current_rate = current_rates[currency]
            target_rate = predictions[currency]["central"]
            adjusted_central = current_rate + (target_rate - current_rate) * adjustment
            model_uncertainty = predictions[currency]["uncertainty"] / 100 * adjusted_central
            
            projection_with_bands.loc[i, f"{currency}_P25"] = adjusted_central - 0.67 * model_uncertainty
            projection_with_bands.loc[i, f"{currency}_P75"] = adjusted_central + 0.67 * model_uncertainty
    
    st.markdown("#### Dane Prognozy z Pasmami Ufności")
    display_cols = ["Miesiąc", "Data", "EUR", "EUR_P25", "EUR_P75", "USD", "USD_P25", "USD_P75", "GBP", "GBP_P25", "GBP_P75"]
    st.dataframe(projection_with_bands[display_cols].round(4), use_container_width=True)

with tab2:
    st.markdown("### Analiza Wrażliwości - Wpływ Realnej Stopy Procentowej")
    
    # Generowanie danych wrażliwości
    sensitivity_rates = np.arange(-2.0, 8.0, 0.2)
    sensitivity_data = []
    
    for rate in sensitivity_rates:
        temp_predictions = predict_exchange_rates(rate, current_rates)
        sensitivity_data.append({
            "Realna_Stopa": rate,
            "EUR_PLN": temp_predictions["EUR"]["central"],
            "USD_PLN": temp_predictions["USD"]["central"],
            "GBP_PLN": temp_predictions["GBP"]["central"]
        })
    
    df_sensitivity = pd.DataFrame(sensitivity_data)
    
    # Wykres wrażliwości
    fig_sens = go.Figure()
    fig_sens.add_trace(go.Scatter(x=df_sensitivity["Realna_Stopa"], y=df_sensitivity["EUR_PLN"], 
                                 name="EUR/PLN", line=dict(color=color, width=3), mode='lines'))
    fig_sens.add_trace(go.Scatter(x=df_sensitivity["Realna_Stopa"], y=df_sensitivity["USD_PLN"], 
                                 name="USD/PLN", line=dict(color=color, width=3, dash='dash'), mode='lines'))
    fig_sens.add_trace(go.Scatter(x=df_sensitivity["Realna_Stopa"], y=df_sensitivity["GBP_PLN"], 
                                 name="GBP/PLN", line=dict(color=color, width=3, dash='dot'), mode='lines'))
    
    # Dodanie linii dla obecnej realnej stopy
    fig_sens.add_vline(x=real_rate, line_dash="dash", line_color="red", 
                      annotation_text=f"Obecna Realna Stopa: {real_rate:.1f}%")
    
    fig_sens.update_layout(
        title="Wrażliwość Kursów Walut na Realną Stopę Procentową",
        xaxis_title="Realna Stopa Procentowa (%)",
        yaxis_title="Prognozowany Kurs (PLN)",
        height=500
    )
    
    st.plotly_chart(fig_sens, use_container_width=True)
    
    # Tabela wrażliwości
    st.markdown("#### Kluczowe Scenariusze")
    scenarios = [
        {"Scenariusz": "Bardzo Niska Stopa", "Realna_Stopa": -1.0},
        {"Scenariusz": "Niska Stopa", "Realna_Stopa": 1.0},
        {"Scenariusz": "Obecna Stopa", "Realna_Stopa": real_rate},
        {"Scenariusz": "Wysoka Stopa", "Realna_Stopa": 4.0},
        {"Scenariusz": "Bardzo Wysoka Stopa", "Realna_Stopa": 6.0}
    ]
    
    scenario_results = []
    for scenario in scenarios:
        temp_pred = predict_exchange_rates(scenario["Realna_Stopa"], current_rates)
        scenario_results.append({
            "Scenariusz": scenario["Scenariusz"],
            "Realna Stopa (%)": f"{scenario['Realna_Stopa']:.1f}%",
            "EUR/PLN": f"{temp_pred['EUR']['central']:.4f}",
            "USD/PLN": f"{temp_pred['USD']['central']:.4f}",
            "GBP/PLN": f"{temp_pred['GBP']['central']:.4f}"
        })
    
    st.dataframe(pd.DataFrame(scenario_results), use_container_width=True, hide_index=True)

with tab3:
    st.markdown("### Dane Historyczne - Kursy Walut i Stopy Procentowe")
    
    # Filtr dat
    col1, col2 = st.columns(2)
    with col1:
        start_year = st.selectbox("Rok początkowy", options=list(range(2014, 2026)), index=8)
    with col2:
        end_year = st.selectbox("Rok końcowy", options=list(range(2014, 2026)), index=11)
    
    # Filtrowanie danych
    df_filtered = df[(df['year'] >= start_year) & (df['year'] <= end_year)].copy()
    df_filtered['date_parsed'] = pd.to_datetime(df_filtered['date'])
    
    # Wykres historyczny kursów
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(x=df_filtered['date_parsed'], y=df_filtered['eur_pln'], 
                                 name="EUR/PLN", line=dict(color=color, width=2), mode='lines'))
    fig_hist.add_trace(go.Scatter(x=df_filtered['date_parsed'], y=df_filtered['usd_pln'], 
                                 name="USD/PLN", line=dict(color=color, width=2, dash='dash'), mode='lines'))
    fig_hist.add_trace(go.Scatter(x=df_filtered['date_parsed'], y=df_filtered['gbp_pln'], 
                                 name="GBP/PLN", line=dict(color=color, width=2, dash='dot'), mode='lines'))
    
    fig_hist.update_layout(
        title=f"Historyczne Kursy Walut ({start_year}-{end_year})",
        xaxis_title="Data",
        yaxis_title="Kurs Walutowy (PLN)",
        height=500
    )
    
    st.plotly_chart(fig_hist, use_container_width=True)
    
    # Wykres stóp procentowych i inflacji
    fig_rates = go.Figure()
    fig_rates.add_trace(go.Scatter(x=df_filtered['date_parsed'], y=df_filtered['nbp_reference_rate'], 
                                  name="Stopa Referencyjna NBP", line=dict(color=color, width=2), mode='lines'))
    fig_rates.add_trace(go.Scatter(x=df_filtered['date_parsed'], y=df_filtered['inflation_rate'], 
                                  name="Inflacja", line=dict(color="red", width=2), mode='lines'))
    fig_rates.add_trace(go.Scatter(x=df_filtered['date_parsed'], y=df_filtered['real_interest_rate'], 
                                  name="Realna Stopa Procentowa", line=dict(color="green", width=2), mode='lines'))
    
    fig_rates.update_layout(
        title=f"Historyczne Stopy Procentowe i Inflacja ({start_year}-{end_year})",
        xaxis_title="Data",
        yaxis_title="Stopa (%)",
        height=500
    )
    
    st.plotly_chart(fig_rates, use_container_width=True)
    
    # Statystyki opisowe
    st.markdown("#### Statystyki Opisowe dla Wybranego Okresu")
    
    stats_data = {
        "Metryka": ["Średnia", "Odchylenie Standardowe", "Minimum", "Maksimum"],
        "EUR/PLN": [
            f"{df_filtered['eur_pln'].mean():.4f}",
            f"{df_filtered['eur_pln'].std():.4f}",
            f"{df_filtered['eur_pln'].min():.4f}",
            f"{df_filtered['eur_pln'].max():.4f}"
        ],
        "USD/PLN": [
            f"{df_filtered['usd_pln'].mean():.4f}",
            f"{df_filtered['usd_pln'].std():.4f}",
            f"{df_filtered['usd_pln'].min():.4f}",
            f"{df_filtered['usd_pln'].max():.4f}"
        ],
        "GBP/PLN": [
            f"{df_filtered['gbp_pln'].mean():.4f}",
            f"{df_filtered['gbp_pln'].std():.4f}",
            f"{df_filtered['gbp_pln'].min():.4f}",
            f"{df_filtered['gbp_pln'].max():.4f}"
        ],
        "Inflacja (%)": [
            f"{df_filtered['inflation_rate'].mean():.2f}%",
            f"{df_filtered['inflation_rate'].std():.2f}%",
            f"{df_filtered['inflation_rate'].min():.2f}%",
            f"{df_filtered['inflation_rate'].max():.2f}%"
        ],
        "Stopa NBP (%)": [
            f"{df_filtered['nbp_reference_rate'].mean():.2f}%",
            f"{df_filtered['nbp_reference_rate'].std():.2f}%",
            f"{df_filtered['nbp_reference_rate'].min():.2f}%",
            f"{df_filtered['nbp_reference_rate'].max():.2f}%"
        ]
    }
    
    st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)

# Sekcja informacyjna
st.markdown("---")
st.markdown("## ℹ️ Informacje o Modelu")

with st.expander("📋 Metodologia i Założenia"):
    st.markdown("""
    **Model Prognostyczny:**
    - Model oparty jest na związku między realną stopą procentową a kursami walut
    - Uwzględnia wrażliwość różnych walut na zmiany realnych stóp procentowych
    - Prognoza centralna z pasmami ufności opartymi na niepewności modelu
    
    **Założenia Modelu:**
    - EUR/PLN: wrażliwość -0.12 na realną stopę, niepewność ±3%
    - USD/PLN: wrażliwość -0.18 na realną stopę, niepewność ±5%
    - GBP/PLN: wrażliwość -0.15 na realną stopę, niepewność ±4%
    
    **Interpretacja:**
    - Wyższa realna stopa procentowa prowadzi do umocnienia PLN (niższe kursy)
    - Niższa realna stopa procentowa prowadzi do osłabienia PLN (wyższe kursy)
    - Pasma ufności odzwierciedlają niepewność modelu
    
    **Ograniczenia:**
    - Model nie uwzględnia czynników geopolitycznych
    - Prognozy mają charakter orientacyjny
    - Rzeczywiste kursy mogą znacząco odbiegać od prognoz
    """)

with st.expander("📈 Jak Czytać Prognozy"):
    st.markdown("""
    **Prognoza Centralna:** Najbardziej prawdopodobny scenariusz według modelu
    
    **Percentyle:**
    - **25. percentyl:** Scenariusz optymistyczny dla PLN (niższe kursy walut)
    - **75. percentyl:** Scenariusz pesymistyczny dla PLN (wyższe kursy walut)
    - **90. percentyl:** Scenariusz bardzo pesymistyczny dla PLN
    
    **Zakres 50% ufności:** Prawdopodobieństwo 50%, że rzeczywisty kurs znajdzie się między 25. a 75. percentylem
    
    **Kolory w prognozach:**
    - 🟢 Zielony: umocnienie PLN (spadek kursu walut)
    - 🔴 Czerwony: osłabienie PLN (wzrost kursu walut)
    """)

# Stopka
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em;">
    💱 Symulator Kursów Walut | Dane: NBP | Model: Analiza Realnej Stopy Procentowej<br>
    ⚠️ Prognozy mają charakter orientacyjny i nie stanowią porady inwestycyjnej
</div>
""", unsafe_allow_html=True)
