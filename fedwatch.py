import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Konfiguracja strony
st.set_page_config(
    page_title="Symulator Kursów Walut",
    page_icon="💱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tytuł
st.title("💱 Symulator Kursów Walut - Wpływ Stóp Procentowych")

# Sidebar z kontrolami
st.sidebar.header("🎛️ Panel Sterowania")

# Suwaki
inflation_rate = st.sidebar.slider(
    "Inflacja bazowa (%)", 
    min_value=-3.0, 
    max_value=15.0, 
    value=4.0, 
    step=0.1
)

nominal_rate = st.sidebar.slider(
    "Stopa referencyjna NBP (%)", 
    min_value=0.0, 
    max_value=12.0, 
    value=5.75, 
    step=0.25
)

time_horizon = st.sidebar.slider(
    "Horyzont prognozy (miesiące)", 
    min_value=3, 
    max_value=24, 
    value=12
)

# Automatyczne obliczanie realnej stopy
real_rate = ((1 + nominal_rate/100) / (1 + inflation_rate/100) - 1) * 100

# Wyświetlanie realnej stopy
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Obliczona Realna Stopa")
color = "🟢" if real_rate >= 0 else "🔴"
st.sidebar.markdown(f"## {color} {real_rate:.2f}%")
st.sidebar.caption(f"(1 + {nominal_rate}%) / (1 + {inflation_rate}%) - 1")

# Główna sekcja
col1, col2, col3 = st.columns(3)

# Model predykcyjny
def predict_exchange_rates(real_rate, nominal_rate, inflation_rate):
    base_rates = {"EUR": 4.27, "USD": 4.08, "GBP": 5.15}
    sensitivity = {
        "EUR": {"real": -0.12, "volatility": 0.08},
        "USD": {"real": -0.18, "volatility": 0.12},
        "GBP": {"real": -0.15, "volatility": 0.10}
    }
    
    results = {}
    for currency in base_rates:
        real_impact = (real_rate - 0.98) * sensitivity[currency]["real"]
        central = base_rates[currency] + real_impact
        vol = sensitivity[currency]["volatility"] * central
        
        results[currency] = {
            "central": central,
            "p10": central - 1.28 * vol,
            "p90": central + 1.28 * vol,
            "change": ((central - base_rates[currency]) / base_rates[currency]) * 100
        }
    
    return results

predictions = predict_exchange_rates(real_rate, nominal_rate, inflation_rate)

# Kafelki prognoz
currencies = ["EUR", "USD", "GBP"]
colors = ["#4f46e5", "#059669", "#dc2626"]

for i, (currency, color) in enumerate(zip(currencies, colors)):
    with [col1, col2, col3][i]:
        pred = predictions[currency]
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {color}20, {color}10);
            padding: 20px;
            border-radius: 15px;
            border: 2px solid {color}40;
            text-align: center;
        ">
            <h3 style="color: {color}; margin: 0;">{currency}/PLN</h3>
            <h1 style="color: {color}; margin: 10px 0; font-size: 2.5em;">
                {pred['central']:.4f}
            </h1>
            <p style="margin: 5px 0;">
                Zmiana: <strong>{'🔴' if pred['change'] >= 0 else '🟢'} {pred['change']:+.1f}%</strong>
            </p>
            <div style="background: white; padding: 10px; border-radius: 8px; margin-top: 10px;">
                <small>10%: {pred['p10']:.4f} | 90%: {pred['p90']:.4f}</small>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# Wykresy
tab1, tab2, tab3 = st.tabs(["📈 Prognoza czasowa", "📊 Analiza wrażliwości", "🔍 Dane historyczne"])

with tab1:
    # Generowanie projekcji czasowej
    dates = [datetime.now() + timedelta(days=30*i) for i in range(time_horizon + 1)]
    projection_data = []
    
    for i, date in enumerate(dates):
        adjustment = min(i / 6, 1)  # Pełne dostosowanie po 6 miesiącach
        projection_data.append({
            "Miesiąc": i,
            "Data": date.strftime("%Y-%m"),
            "EUR": 4.27 + (predictions["EUR"]["central"] - 4.27) * adjustment,
            "USD": 4.08 + (predictions["USD"]["central"] - 4.08) * adjustment,
            "GBP": 5.15 + (predictions["GBP"]["central"] - 5.15) * adjustment,
        })
    
    df_projection = pd.DataFrame(projection_data)
    
    st.subheader(f"Prognoza kursów na {time_horizon} miesięcy")
    
    # Używamy native Streamlit line chart
    chart_data = df_projection.set_index('Miesiąc')[['EUR', 'USD', 'GBP']]
    st.line_chart(chart_data, height=400)
    
    # Tabela z danymi
    st.subheader("Dane szczegółowe")
    st.dataframe(df_projection[['Data', 'EUR', 'USD', 'GBP']].round(4))

with tab2:
    currency_choice = st.selectbox("Wybierz parę walutową:", ["EUR", "USD", "GBP"])
    
    # Analiza wrażliwości
    steps = np.arange(-2, 2.1, 0.5)
    sensitivity_data = []
    
    for step in steps:
        test_real = real_rate + step
        test_predictions = predict_exchange_rates(test_real, nominal_rate, inflation_rate)
        sensitivity_data.append({
            "Zmiana realnej stopy": step,
            currency_choice: test_predictions[currency_choice]["central"]
        })
    
    df_sensitivity = pd.DataFrame(sensitivity_data)
    
    st.subheader(f"Wrażliwość kursu {currency_choice}/PLN na zmiany realnej stopy")
    
    # Line chart
    chart_data = df_sensitivity.set_index('Zmiana realnej stopy')
    st.line_chart(chart_data)
    
    # Tabela
    st.dataframe(df_sensitivity.round(4))

with tab3:
    # Dane historyczne
    historical_data = {
        "Data": ["2014-01", "2015-01", "2020-05", "2021-12", "2022-06", "2024-06"],
        "Realna stopa": [1.99, 3.45, -3.19, -6.31, -5.19, 3.07],
        "EUR": [4.18, 4.25, 4.46, 4.60, 4.46, 4.32],
        "USD": [3.07, 3.64, 4.04, 4.06, 4.26, 4.01],
        "GBP": [5.05, 5.45, 4.95, 5.45, 5.28, 5.10]
    }
    
    df_historical = pd.DataFrame(historical_data)
    currency_hist = st.selectbox("Wybierz parę walutową:", ["EUR", "USD", "GBP"], key="hist")
    
    st.subheader(f"Korelacja historyczna: Realna stopa vs {currency_hist}/PLN")
    
    # Scatter plot using native Streamlit
    scatter_data = df_historical[['Realna stopa', currency_hist]]
    st.scatter_chart(scatter_data.set_index('Realna stopa'))
    
    # Tabela historyczna
    st.subheader("Dane historyczne")
    st.dataframe(df_historical)

# Footer
st.markdown("---")
st.markdown("### 📋 Metodologia")
st.info("""
**Model predykcyjny:** Realna stopa = (1 + nominalna) / (1 + inflacja) - 1  
**Wrażliwość:** USD (-0.18) > GBP (-0.15) > EUR (-0.12)  
**Zastrzeżenie:** Model ma charakter edukacyjny. Rzeczywiste kursy zależą od wielu czynników.
""")
