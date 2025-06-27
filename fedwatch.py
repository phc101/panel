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

# Wyświetlanie parametrów modelu
st.sidebar.markdown("---")
st.sidebar.markdown("### 📈 Parametry Modelu (z 10 lat danych)")
for currency in ["EUR", "USD", "GBP"]:
    params = model_params[currency]
    st.sidebar.markdown(f"**{currency}/PLN:**")
    st.sidebar.caption(f"Wrażliwość: {params['slope']:.3f}")
    st.sidebar.caption(f"Korelacja: {params['correlation']:.3f}")
    st.sidebar.caption(f"Volatility: {params['volatility']:.1%}")

# Główna sekcja
col1, col2, col3 = st.columns(3)

# Dane historyczne - używane do kalibracji modelu
historical_data = {
    "Data": ["2014-01", "2015-01", "2020-05", "2021-12", "2022-06", "2024-06"],
    "Realna stopa": [1.99, 3.45, -3.19, -6.31, -5.19, 3.07],
    "EUR": [4.18, 4.25, 4.46, 4.60, 4.46, 4.32],
    "USD": [3.07, 3.64, 4.04, 4.06, 4.26, 4.01],
    "GBP": [5.05, 5.45, 4.95, 5.45, 5.28, 5.10]
}

# Funkcja do obliczania parametrów modelu z danych historycznych
def calibrate_model(historical_data):
    df_hist = pd.DataFrame(historical_data)
    
    # Obliczamy korelacje i wrażliwości z danych rzeczywistych
    results = {}
    currencies = ["EUR", "USD", "GBP"]
    
    for currency in currencies:
        # Obliczanie współczynnika regresji (wrażliwość na realną stopę)
        x = df_hist["Realna stopa"].values
        y = df_hist[currency].values
        
        # Prosta regresja liniowa: y = a + b*x
        n = len(x)
        sum_x = np.sum(x)
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        sum_x2 = np.sum(x * x)
        
        # Współczynnik regresji (slope)
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Intercept
        intercept = (sum_y - slope * sum_x) / n
        
        # Obliczanie volatility (standard deviation of residuals)
        y_pred = intercept + slope * x
        residuals = y - y_pred
        volatility = np.std(residuals) / np.mean(y)  # Relative volatility
        
        # Korelacja
        correlation = np.corrcoef(x, y)[0, 1]
        
        # Current base rate (ostatnia wartość historyczna)
        base_rate = df_hist[currency].iloc[-1]
        
        results[currency] = {
            "slope": slope,
            "intercept": intercept,
            "volatility": volatility,
            "correlation": correlation,
            "base_rate": base_rate
        }
    
    return results

# Kalibracja modelu na danych historycznych
model_params = calibrate_model(historical_data)

# Model predykcyjny używający rzeczywistych parametrów z 10 lat danych
def predict_exchange_rates(real_rate, nominal_rate, inflation_rate):
    results = {}
    
    # Średnia historyczna realnej stopy (punkt odniesienia)
    df_hist = pd.DataFrame(historical_data)
    mean_historical_real_rate = df_hist["Realna stopa"].mean()
    
    for currency in ["EUR", "USD", "GBP"]:
        params = model_params[currency]
        
        # Predykcja na podstawie regresji liniowej z danych historycznych
        predicted_rate = params["intercept"] + params["slope"] * real_rate
        
        # Obliczenie zmiany względem obecnej bazy
        change = ((predicted_rate - params["base_rate"]) / params["base_rate"]) * 100
        
        # Przedziały ufności na podstawie volatility historycznej
        vol = params["volatility"] * predicted_rate
        
        results[currency] = {
            "central": predicted_rate,
            "p10": predicted_rate - 1.28 * vol,
            "p90": predicted_rate + 1.28 * vol,
            "change": change,
            "correlation": params["correlation"],
            "slope": params["slope"]
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
            <p style="margin: 5px 0; font-size: 0.9em;">
                Korelacja: {pred['correlation']:+.3f} | Wrażliwość: {pred['slope']:+.3f}
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
    
    # Calculate y-axis range for better visibility
    chart_data = df_projection.set_index('Miesiąc')[['EUR', 'USD', 'GBP']]
    min_val = chart_data.min().min()
    max_val = chart_data.max().max()
    margin = (max_val - min_val) * 0.1  # 10% margin
    
    st.line_chart(chart_data, height=400, y_min=min_val - margin, y_max=max_val + margin)
    
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
    
    # Calculate y-axis range for better visibility
    chart_data = df_sensitivity.set_index('Zmiana realnej stopy')
    min_val = chart_data[currency_choice].min()
    max_val = chart_data[currency_choice].max()
    margin = (max_val - min_val) * 0.1  # 10% margin
    
    st.line_chart(chart_data, y_min=min_val - margin, y_max=max_val + margin)
    
    # Tabela
    st.dataframe(df_sensitivity.round(4))

with tab3:
    # Dane historyczne
    df_historical = pd.DataFrame(historical_data)
    currency_hist = st.selectbox("Wybierz parę walutową:", ["EUR", "USD", "GBP"], key="hist")
    
    st.subheader(f"Korelacja historyczna: Realna stopa vs {currency_hist}/PLN")
    
    # Calculate y-axis range for better visibility
    scatter_data = df_historical[['Realna stopa', currency_hist]]
    min_val = scatter_data[currency_hist].min()
    max_val = scatter_data[currency_hist].max()
    margin = (max_val - min_val) * 0.15  # 15% margin for scatter plot
    
    st.scatter_chart(scatter_data.set_index('Realna stopa'), 
                    y_min=min_val - margin, y_max=max_val + margin)
    
    # Display detailed statistics from calibrated model
    params = model_params[currency_hist]
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Korelacja", f"{params['correlation']:.3f}")
    with col2:
        st.metric("Wrażliwość", f"{params['slope']:.3f}")
    with col3:
        st.metric("Volatility", f"{params['volatility']:.1%}")
    with col4:
        st.metric("Obecny kurs", f"{params['base_rate']:.4f}")
    
    # Regresja liniowa - linia trendu
    st.subheader("Równanie regresji")
    st.latex(f"{currency_hist} = {params['intercept']:.3f} + {params['slope']:.3f} \\times \\text{{Realna stopa}}")
    
    # Tabela historyczna
    st.subheader("Dane historyczne (10 lat)")
    st.dataframe(df_historical)

# Footer
st.markdown("---")
st.markdown("### 📋 Metodologia")
st.info("""
**Model predykcyjny:** Kalibrowany na 10 latach danych historycznych (2014-2024)  
**Regresja liniowa:** Kurs = Intercept + Wrażliwość × Realna stopa  
**Realna stopa:** (1 + nominalna) / (1 + inflacja) - 1  
**Wrażliwości z danych:** """ + f"EUR: {model_params['EUR']['slope']:.3f}, USD: {model_params['USD']['slope']:.3f}, GBP: {model_params['GBP']['slope']:.3f}" + """  
**Zastrzeżenie:** Model ma charakter edukacyjny. Rzeczywiste kursy zależą od wielu czynników.
""")
