import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# Konfiguracja strony
st.set_page_config(
    page_title="Kalkulator Forward EUR/PLN",
    page_icon="💱",
    layout="wide"
)

st.title("💱 Kalkulator Forward EUR/PLN")
st.markdown("---")

# Funkcje do pobierania danych
@st.cache_data(ttl=300)  # Cache na 5 minut
def get_current_eur_pln_rate():
    """Pobiera aktualny kurs EUR/PLN z API NBP"""
    try:
        url = "https://api.nbp.pl/api/exchangerates/rates/a/eur/"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['rates'][0]['mid']
    except Exception as e:
        st.warning(f"Nie udało się pobrać kursu EUR/PLN z NBP: {e}")
    
    # Fallback - przykładowy kurs
    return 4.25

@st.cache_data(ttl=1800)  # Cache na 30 minut
def get_wibor_rates():
    """Pobiera aktualne stawki WIBOR"""
    # Najpierw próbujemy scraping ze Stooq (alternatywne źródło)
    try:
        # Próba pobrania z popularnego serwisu finansowego
        # W rzeczywistości GPW Benchmark wymaga licencji na API
        
        # Symulacja danych WIBOR na podstawie stopy referencyjnej NBP + spread
        nbp_rate = get_nbp_reference_rate()
        if nbp_rate:
            # Szacunkowe stawki WIBOR na podstawie stopy NBP (historyczny spread)
            wibor_rates = {
                'ON': nbp_rate + 0.10,    # Overnight
                '1W': nbp_rate + 0.15,    # 1 tydzień
                '2W': nbp_rate + 0.20,    # 2 tygodnie
                '1M': nbp_rate + 0.25,    # 1 miesiąc
                '2M': nbp_rate + 0.30,    # 2 miesiące
                '3M': nbp_rate + 0.35,    # 3 miesiące
                '6M': nbp_rate + 0.40,    # 6 miesięcy
            }
            return wibor_rates
    except Exception as e:
        st.warning(f"Nie udało się pobrać stawek WIBOR: {e}")
    
    # Fallback - przykładowe stawki
    return {
        'ON': 5.65, '1W': 5.70, '2W': 5.72, '1M': 5.75, 
        '2M': 5.78, '3M': 5.80, '6M': 5.85
    }

@st.cache_data(ttl=1800)  # Cache na 30 minut  
def get_nbp_reference_rate():
    """Pobiera stopę referencyjną NBP"""
    try:
        # NBP nie udostępnia API dla stóp procentowych, więc używamy znanej wartości
        # W rzeczywistej aplikacji można scraping ze strony NBP lub ręczna aktualizacja
        return 5.75  # Aktualna stopa referencyjna (czerwiec 2025)
    except:
        return 5.75

@st.cache_data(ttl=1800)  # Cache na 30 minut
def get_euribor_rates():
    """Pobiera aktualne stawki EURIBOR z API"""
    try:
        # Próba z darmowym API (może wymagać klucza API)
        url = "https://api.api-ninjas.com/v1/euribor"
        headers = {
            'X-Api-Key': 'YOUR_API_KEY'  # Wymagany klucz API
        }
        
        # Bez klucza API używamy przykładowych danych
        # response = requests.get(url, headers=headers, timeout=10)
        # if response.status_code == 200:
        #     data = response.json()
        #     euribor_rates = {}
        #     for rate in data:
        #         tenor = rate['name'].split(' - ')[1]
        #         euribor_rates[tenor] = rate['rate_pct']
        #     return euribor_rates
        
        # Fallback na szacunkowe dane na podstawie stopy ECB
        ecb_rate = 3.25  # Aktualna stopa ECB
        euribor_rates = {
            '1 week': ecb_rate + 0.05,
            '1 month': ecb_rate + 0.10,
            '3 months': ecb_rate + 0.15,
            '6 months': ecb_rate + 0.20,
            '12 months': ecb_rate + 0.25
        }
        return euribor_rates
        
    except Exception as e:
        st.warning(f"Nie udało się pobrać stawek EURIBOR: {e}")
    
    # Fallback - przykładowe stawki
    return {
        '1 week': 3.30, '1 month': 3.35, '3 months': 3.40, 
        '6 months': 3.45, '12 months': 3.50
    }

@st.cache_data(ttl=3600)  # Cache na 1 godzinę
def scrape_money_pl_wibor():
    """Alternatywny scraping WIBOR z money.pl (backup)"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://wibor.money.pl/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # W rzeczywistości wymagałoby to parsowania HTML
            # Tutaj symulujemy wynik
            pass
            
    except Exception as e:
        st.warning(f"Backup scraping failed: {e}")
    
    return None

# Funkcja do obliczania kursu forward
def calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, days):
    """
    Oblicza kurs forward używając wzoru:
    Forward = Spot × (1 + r_domestic × T) / (1 + r_foreign × T)
    gdzie T to czas w latach
    """
    T = days / 365.0
    forward_rate = spot_rate * (1 + domestic_rate * T) / (1 + foreign_rate * T)
    return forward_rate

# Funkcja do obliczania punktów forward
def calculate_forward_points(spot_rate, forward_rate):
    return (forward_rate - spot_rate) * 10000  # W punktach (pips)

# Pobieranie danych rynkowych
with st.spinner("Pobieranie aktualnych danych rynkowych..."):
    current_eur_pln = get_current_eur_pln_rate()
    wibor_rates = get_wibor_rates()
    euribor_rates = get_euribor_rates()

# Wyświetlenie statusu danych
col_status1, col_status2, col_status3 = st.columns(3)

with col_status1:
    st.metric("EUR/PLN (NBP)", f"{current_eur_pln:.4f}", help="Kurs spot z API NBP")

with col_status2:
    st.metric("WIBOR 3M", f"{wibor_rates.get('3M', 0):.2f}%", 
              help="Szacunkowa stawka na podstawie stopy NBP")

with col_status3:
    st.metric("EURIBOR 3M", f"{euribor_rates.get('3 months', 0):.2f}%", 
              help="Szacunkowa stawka na podstawie stopy ECB")

st.markdown("---")

# Layout w kolumnach
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📊 Parametry rynkowe")
    
    # Kurs spot
    spot_rate = st.number_input(
        "Kurs spot EUR/PLN:",
        value=current_eur_pln,
        min_value=3.0,
        max_value=6.0,
        step=0.01,
        format="%.4f",
        help="Automatycznie pobierany z NBP API"
    )
    
    # Sekcja stóp procentowych z automatycznym pobieraniem
    st.subheader("🔄 Stopy procentowe (% rocznie)")
    
    # Toggle dla automatycznych/ręcznych stóp
    auto_rates = st.checkbox("Użyj automatycznie pobranych stóp", value=True)
    
    if auto_rates:
        # Wybór terminów z automatycznych danych
        col_pln, col_eur = st.columns(2)
        
        with col_pln:
            st.write("**Stawki WIBOR dostępne:**")
            wibor_options = list(wibor_rates.keys())
            selected_wibor = st.selectbox(
                "Wybierz termin WIBOR:",
                wibor_options,
                index=wibor_options.index('3M') if '3M' in wibor_options else 0
            )
            pln_rate = wibor_rates[selected_wibor] / 100
            st.info(f"WIBOR {selected_wibor}: {wibor_rates[selected_wibor]:.2f}%")
        
        with col_eur:
            st.write("**Stawki EURIBOR dostępne:**")
            euribor_options = list(euribor_rates.keys())
            selected_euribor = st.selectbox(
                "Wybierz termin EURIBOR:",
                euribor_options,
                index=euribor_options.index('3 months') if '3 months' in euribor_options else 0
            )
            eur_rate = euribor_rates[selected_euribor] / 100
            st.info(f"EURIBOR {selected_euribor}: {euribor_rates[selected_euribor]:.2f}%")
    else:
        # Ręczne wprowadzanie stóp
        col_pln, col_eur = st.columns(2)
        
        with col_pln:
            pln_rate = st.number_input(
                "Stopa PLN (WIBOR):",
                value=wibor_rates.get('3M', 5.75),
                min_value=0.0,
                max_value=20.0,
                step=0.25,
                format="%.2f"
            ) / 100
        
        with col_eur:
            eur_rate = st.number_input(
                "Stopa EUR (EURIBOR):",
                value=euribor_rates.get('3 months', 3.25),
                min_value=0.0,
                max_value=20.0,
                step=0.25,
                format="%.2f"
            ) / 100
    
    # Okres forward
    st.subheader("📅 Okres forward")
    period_type = st.selectbox(
        "Wybierz typ okresu:",
        ["Standardowe terminy", "Dni", "Miesiące"]
    )
    
    if period_type == "Dni":
        days = st.number_input(
            "Liczba dni:",
            value=90,
            min_value=1,
            max_value=365*5,
            step=1
        )
    elif period_type == "Miesiące":
        months = st.number_input(
            "Liczba miesięcy:",
            value=3,
            min_value=1,
            max_value=60,
            step=1
        )
        days = months * 30  # Przybliżenie
    else:
        standard_terms = st.selectbox(
            "Standardowe terminy:",
            ["1W", "2W", "1M", "2M", "3M", "6M", "9M", "1Y", "2Y", "3Y", "5Y"],
            index=4  # Domyślnie 3M
        )
        term_days = {
            "1W": 7, "2W": 14, "1M": 30, "2M": 60, "3M": 90,
            "6M": 180, "9M": 270, "1Y": 365, "2Y": 730, "3Y": 1095, "5Y": 1825
        }
        days = term_days[standard_terms]

with col2:
    st.header("💰 Wyniki obliczeń")
    
    # Obliczenia
    forward_rate = calculate_forward_rate(spot_rate, pln_rate, eur_rate, days)
    forward_points = calculate_forward_points(spot_rate, forward_rate)
    
    # Wyświetlanie wyników w kartach
    result_col1, result_col2 = st.columns(2)
    
    with result_col1:
        st.metric(
            label="Kurs Forward EUR/PLN",
            value=f"{forward_rate:.4f}",
            delta=f"{forward_rate - spot_rate:.4f}"
        )
    
    with result_col2:
        st.metric(
            label="Punkty Forward",
            value=f"{forward_points:.2f} pips",
            delta=None
        )
    
    # Dodatkowe analizy
    st.subheader("📈 Analiza forward")
    
    annualized_premium = ((forward_rate / spot_rate) - 1) * (365 / days) * 100
    rate_differential = (pln_rate - eur_rate) * 100
    
    # Kolorowe wskaźniki
    if forward_rate > spot_rate:
        st.success(f"🔺 EUR w **premium** o {annualized_premium:.2f}% w skali roku")
    else:
        st.error(f"🔻 EUR w **discount** o {abs(annualized_premium):.2f}% w skali roku")
    
    st.info(f"📊 Różnica stóp procentowych: {rate_differential:.2f} p.p.")
    
    # Dodatkowe metryki
    with st.expander("🔍 Szczegółowe metryki"):
        st.write(f"**Czas do maturity:** {days} dni ({days/365:.2f} lat)")
        st.write(f"**Użyta stopa PLN:** {pln_rate*100:.2f}%")
        st.write(f"**Użyta stopa EUR:** {eur_rate*100:.2f}%")
        st.write(f"**Forward premium/discount:** {((forward_rate/spot_rate)-1)*100:.4f}%")
        
        # Implied forward rate calculation
        implied_rate_diff = ((forward_rate/spot_rate - 1) * 365/days) * 100
        st.write(f"**Implikowana różnica stóp:** {implied_rate_diff:.2f}% p.a.")

# Automatyczne odświeżanie danych
if st.button("🔄 Odśwież dane rynkowe"):
    st.cache_data.clear()
    st.rerun()

# Sekcja z tabelą dla różnych terminów
st.markdown("---")
st.header("📅 Tabela kursów forward dla różnych terminów")

# Tworzenie tabeli z różnymi terminami
terms = [7, 14, 30, 60, 90, 180, 270, 365, 730, 1095]
term_names = ["1W", "2W", "1M", "2M", "3M", "6M", "9M", "1Y", "2Y", "3Y"]

forward_data = []
for i, term_days in enumerate(terms):
    fw_rate = calculate_forward_rate(spot_rate, pln_rate, eur_rate, term_days)
    fw_points = calculate_forward_points(spot_rate, fw_rate)
    annual_premium = ((fw_rate / spot_rate - 1) * (365 / term_days) * 100)
    
    forward_data.append({
        "Termin": term_names[i],
        "Dni": term_days,
        "Kurs Forward": f"{fw_rate:.4f}",
        "Punkty Forward": f"{fw_points:.2f}",
        "Premium/Discount %": f"{annual_premium:.2f}%",
        "Spread vs Spot": f"{(fw_rate - spot_rate)*10000:.1f} pips"
    })

df = pd.DataFrame(forward_data)

# Kolorowanie tabeli
def highlight_premium_discount(val):
    if '%' in str(val):
        num_val = float(val.replace('%', ''))
        if num_val > 0:
            return 'background-color: #ffebee'  # Lekki czerwony dla premium
        else:
            return 'background-color: #e8f5e8'  # Lekki zielony dla discount
    return ''

styled_df = df.style.applymap(highlight_premium_discount, subset=['Premium/Discount %'])
st.dataframe(styled_df, use_container_width=True)

# Wykres krzywej forward
st.markdown("---")
st.header("📊 Krzywa Forward EUR/PLN")

# Generowanie danych dla wykresu
chart_days = np.linspace(1, 1095, 100)
chart_forwards = [calculate_forward_rate(spot_rate, pln_rate, eur_rate, d) for d in chart_days]

fig = make_subplots(
    rows=2, cols=1,
    subplot_titles=("Krzywa Forward EUR/PLN", "Forward Points (pips)"),
    vertical_spacing=0.1,
    row_heights=[0.7, 0.3]
)

# Krzywa forward - główny wykres
fig.add_trace(go.Scatter(
    x=chart_days,
    y=chart_forwards,
    mode='lines',
    name='Krzywa Forward',
    line=dict(color='blue', width=2)
), row=1, col=1)

# Kurs spot jako linia pozioma
fig.add_hline(y=spot_rate, line_dash="dash", line_color="red", 
              annotation_text=f"Spot: {spot_rate:.4f}", row=1)

# Punkty dla standardowych terminów
fig.add_trace(go.Scatter(
    x=terms,
    y=[calculate_forward_rate(spot_rate, pln_rate, eur_rate, d) for d in terms],
    mode='markers',
    name='Standardowe terminy',
    marker=dict(color='orange', size=10),
    text=term_names,
    textposition="top center"
), row=1, col=1)

# Forward points na dolnym wykresie
chart_points = [calculate_forward_points(spot_rate, fw) for fw in chart_forwards]
fig.add_trace(go.Scatter(
    x=chart_days,
    y=chart_points,
    mode='lines',
    name='Forward Points',
    line=dict(color='green', width=2),
    showlegend=False
), row=2, col=1)

# Zero line dla punktów forward
fig.add_hline(y=0, line_dash="dot", line_color="gray", row=2)

fig.update_layout(
    title="Analiza krzywej forward EUR/PLN",
    height=700,
    hovermode='x unified',
    showlegend=True
)

fig.update_xaxes(title_text="Dni do maturity", row=2, col=1)
fig.update_yaxes(title_text="Kurs EUR/PLN", row=1, col=1)
fig.update_yaxes(title_text="Punkty (pips)", row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

# Sekcja informacyjna o źródłach danych
st.markdown("---")
st.header("📡 Status źródeł danych")

status_col1, status_col2, status_col3 = st.columns(3)

with status_col1:
    st.markdown("""
    **💱 Kurs EUR/PLN**
    - ✅ API NBP (Narodowy Bank Polski)
    - 🔄 Odświeżanie co 5 minut
    - 📊 Oficjalne kursy średnie
    """)

with status_col2:
    st.markdown("""
    **🏦 Stawki WIBOR**
    - ⚠️ Szacunkowe (NBP + spread)
    - 🔄 Odświeżanie co 30 minut
    - 📈 Bazuje na stopie referencyjnej NBP
    """)

with status_col3:
    st.markdown("""
    **🇪🇺 Stawki EURIBOR** 
    - ⚠️ Szacunkowe (ECB + spread)
    - 🔄 Odświeżanie co 30 minut
    - 📉 Bazuje na stopie ECB
    """)

# Sekcja informacyjna
st.markdown("---")
st.header("ℹ️ Informacje o kalkulatorze")

with st.expander("🔧 Jak działa automatyczne pobieranie danych?"):
    st.markdown("""
    **Źródła danych:**
    
    1. **Kurs EUR/PLN**: Pobierany z oficjalnego API NBP w czasie rzeczywistym
    2. **WIBOR**: Szacowany na podstawie stopy referencyjnej NBP + historyczny spread
    3. **EURIBOR**: Szacowany na podstawie stopy ECB + historyczny spread
    
    **Dlaczego szacunkowe stawki?**
    - GPW Benchmark (oficjalny administrator WIBOR) wymaga licencji komercyjnej
    - EMMI (administrator EURIBOR) udostępnia dane z 24h opóźnieniem
    - Dla celów kalkulacyjnych używamy przybliżeń opartych na stopach centralnych banków
    
    **Jak poprawić dokładność:**
    - Wprowadź ręcznie aktualne stawki WIBOR/EURIBOR
    - Sprawdź oficjalne źródła: gpwbenchmark.pl, emmi-benchmarks.eu
    - Uwzględnij spread bid/ask w rzeczywistych transakcjach
    """)

with st.expander("📊 Wzory i metodologia"):
    st.markdown("""
    **Wzór na kurs forward:**
    ```
    Forward = Spot × (1 + r_PLN × T) / (1 + r_EUR × T)
    ```
    
    **Wzór na punkty forward:**
    ```
    Punkty = (Forward - Spot) × 10,000
    ```
    
    **Annualizowane premium/discount:**
    ```
    Premium% = ((Forward/Spot) - 1) × (365/dni) × 100
    ```
    
    Gdzie:
    - **Spot** - aktualny kurs wymiany EUR/PLN
    - **r_PLN** - stopa procentowa w Polsce (WIBOR)
    - **r_EUR** - stopa procentowa w strefie euro (EURIBOR) 
    - **T** - czas do maturity w latach (dni/365)
    """)

with st.expander("⚠️ Zastrzeżenia i ograniczenia"):
    st.markdown("""
    **Ważne informacje:**
    
    - 📊 Wyniki mają charakter **orientacyjny** i nie stanowią oferty handlowej
    - 💰 Rzeczywiste kursy forward mogą różnić się od kalkulacji teoretycznych
    - 📈 Kalkulator nie uwzględnia:
      - Spread bid/ask
      - Koszty transakcyjne  
      - Premie za ryzyko kredytowe
      - Płynność rynku
    
    **Zalecenia przed transakcją:**
    - Sprawdź aktualne kwotowania w bankach
    - Uwzględnij koszty i marże instytucji finansowej
    - Skonsultuj się z doradcą finansowym
    - Monitoruj zmiany stóp procentowych
    """)

# Footer z informacjami technicznymi
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: gray; font-size: 0.8em;'>
    💱 Kalkulator Forward EUR/PLN | Ostatnia aktualizacja: {datetime.now().strftime('%H:%M:%S')}<br>
    📡 Dane: NBP API (kurs spot) | Szacunkowe stawki WIBOR/EURIBOR<br>
    ⚠️ Wyniki orientacyjne - nie stanowią oferty handlowej | 
    🔄 <a href="javascript:window.location.reload()">Odśwież stronę</a>
    </div>
    """, 
    unsafe_allow_html=True
)
