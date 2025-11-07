import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import io

# Konfiguracja strony
st.set_page_config(
    page_title="Analiza Finansowa Spółki",
    page_icon="📊",
    layout="wide"
)

# Funkcje pomocnicze do parsowania XML
def parse_financial_xml(xml_content):
    """Parsuje XML ze sprawozdaniem finansowym"""
    try:
        root = ET.fromstring(xml_content)
        return root
    except Exception as e:
        st.error(f"Błąd parsowania XML: {str(e)}")
        return None

def extract_financial_data(root):
    """Wyciąga dane finansowe z XML"""
    # Ta funkcja będzie dostosowana do struktury konkretnego XML
    # Dla demonstracji tworzymy uniwersalny parser
    data = {
        'bilans': {},
        'rachunek_zyskow_strat': {},
        'cashflow': {}
    }
    
    # Rekurencyjne przeszukiwanie XML
    def extract_values(element, prefix=''):
        result = {}
        for child in element:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            key = f"{prefix}_{tag}" if prefix else tag
            
            if len(child) > 0:
                result.update(extract_values(child, key))
            else:
                if child.text and child.text.strip():
                    try:
                        result[key] = float(child.text.replace(',', '.'))
                    except:
                        result[key] = child.text
        return result
    
    all_data = extract_values(root)
    
    # Próbujemy wyciągnąć okres/datę sprawozdania
    period = None
    for key, value in all_data.items():
        if 'okres' in key.lower() or 'data' in key.lower():
            period = value
            break
    
    all_data['_period'] = period
    return all_data

def compare_periods(data_list):
    """Porównuje dane z różnych okresów"""
    if len(data_list) < 2:
        return None
    
    # Sortujemy według okresu
    sorted_data = sorted(data_list, key=lambda x: x.get('_period', ''))
    
    comparisons = []
    
    # Kluczowe pozycje do porównania
    key_metrics = [
        'przychody_netto', 'zysk_netto', 'zysk_operacyjny',
        'aktywa', 'aktywa_obrotowe', 'kapital_wlasny',
        'zobowiazania', 'zobowiazania_krotkoterminowe',
        'suma_przeplywy_operacyjne'
    ]
    
    # Porównujemy ostatni okres z poprzednim
    if len(sorted_data) >= 2:
        current = sorted_data[-1]
        previous = sorted_data[-2]
        
        for key in key_metrics:
            current_val = None
            previous_val = None
            
            # Szukamy klucza w danych (może być zagnieżdżony)
            for k, v in current.items():
                if key in k.lower() and isinstance(v, (int, float)):
                    current_val = v
                    break
            
            for k, v in previous.items():
                if key in k.lower() and isinstance(v, (int, float)):
                    previous_val = v
                    break
            
            if current_val is not None and previous_val is not None and previous_val != 0:
                change_pct = ((current_val - previous_val) / abs(previous_val)) * 100
                change_abs = current_val - previous_val
                
                comparisons.append({
                    'metric': key.replace('_', ' ').title(),
                    'previous': previous_val,
                    'current': current_val,
                    'change_abs': change_abs,
                    'change_pct': change_pct,
                    'trend': '📈' if change_pct > 0 else '📉' if change_pct < 0 else '➡️'
                })
    
    return comparisons

def calculate_financial_ratios(data):
    """Oblicza wskaźniki finansowe"""
    ratios = {}
    
    # Wskaźniki płynności
    if 'aktywa_obrotowe' in data and 'zobowiazania_krotkoterminowe' in data:
        ratios['wskaznik_plynnosciI'] = data['aktywa_obrotowe'] / data['zobowiazania_krotkoterminowe'] if data['zobowiazania_krotkoterminowe'] != 0 else 0
    
    # Wskaźnik zadłużenia
    if 'zobowiazania' in data and 'aktywa' in data:
        ratios['wskaznik_zadluzenia'] = data['zobowiazania'] / data['aktywa'] if data['aktywa'] != 0 else 0
    
    # ROE
    if 'zysk_netto' in data and 'kapital_wlasny' in data:
        ratios['roe'] = (data['zysk_netto'] / data['kapital_wlasny']) * 100 if data['kapital_wlasny'] != 0 else 0
    
    # ROA
    if 'zysk_netto' in data and 'aktywa' in data:
        ratios['roa'] = (data['zysk_netto'] / data['aktywa']) * 100 if data['aktywa'] != 0 else 0
    
    return ratios

def analyze_cashflow(data):
    """Analizuje cashflow"""
    analysis = {
        'status': 'Dobry',
        'alerts': [],
        'details': {}
    }
    
    # Szukamy danych o cashflow
    cf_operations = None
    cf_investments = None
    cf_financing = None
    
    for key, value in data.items():
        if 'operacyj' in key.lower() and 'przeply' in key.lower():
            cf_operations = value
        elif 'inwestycyj' in key.lower() and 'przeply' in key.lower():
            cf_investments = value
        elif 'finansow' in key.lower() and 'przeply' in key.lower():
            cf_financing = value
    
    analysis['details'] = {
        'Przepływy z działalności operacyjnej': cf_operations,
        'Przepływy z działalności inwestycyjnej': cf_investments,
        'Przepływy z działalności finansowej': cf_financing
    }
    
    # Analiza
    if cf_operations is not None and cf_operations < 0:
        analysis['status'] = 'Niepokojący'
        analysis['alerts'].append('⚠️ Ujemne przepływy z działalności operacyjnej')
    
    if cf_operations is not None and cf_investments is not None:
        if cf_operations > 0 and cf_investments < 0:
            analysis['alerts'].append('✅ Dobry wzorzec: dodatnie CF operacyjne, inwestycje w rozwój')
    
    return analysis

def analyze_changes(data, comparisons):
    """Analizuje przyczyny zmian w wynikach"""
    insights = []
    
    if not comparisons:
        return insights
    
    # Analiza przychodów
    revenue_change = next((c for c in comparisons if 'przychody' in c['metric'].lower()), None)
    profit_change = next((c for c in comparisons if 'zysk netto' in c['metric'].lower()), None)
    
    if revenue_change and profit_change:
        if revenue_change['change_pct'] > 0 and profit_change['change_pct'] > revenue_change['change_pct']:
            insights.append({
                'typ': 'Pozytywny',
                'opis': f"Rentowność rośnie szybciej niż przychody (+{profit_change['change_pct']:.1f}% vs +{revenue_change['change_pct']:.1f}%) - poprawa efektywności operacyjnej",
                'ikona': '✅'
            })
        elif revenue_change['change_pct'] > 0 and profit_change['change_pct'] < 0:
            insights.append({
                'typ': 'Ostrzeżenie',
                'opis': f"Przychody rosną (+{revenue_change['change_pct']:.1f}%), ale zysk spada ({profit_change['change_pct']:.1f}%) - rosnące koszty lub marże",
                'ikona': '⚠️'
            })
        elif revenue_change['change_pct'] < 0 and profit_change['change_pct'] < revenue_change['change_pct']:
            insights.append({
                'typ': 'Negatywny',
                'opis': f"Zysk spada szybciej niż przychody - problemy z kontrolą kosztów",
                'ikona': '🔴'
            })
    
    # Analiza aktywów i kapitału
    assets_change = next((c for c in comparisons if 'aktywa' in c['metric'].lower() and 'obrotowe' not in c['metric'].lower()), None)
    equity_change = next((c for c in comparisons if 'kapital' in c['metric'].lower()), None)
    
    if assets_change and equity_change:
        if assets_change['change_pct'] > equity_change['change_pct']:
            debt_growth = assets_change['change_pct'] - equity_change['change_pct']
            insights.append({
                'typ': 'Ostrzeżenie',
                'opis': f"Aktywa rosną szybciej niż kapitał własny (różnica {debt_growth:.1f}pp) - wzrost zadłużenia",
                'ikona': '⚠️'
            })
    
    # Analiza cashflow
    cashflow_change = next((c for c in comparisons if 'przeplywy operacyjne' in c['metric'].lower()), None)
    if cashflow_change and profit_change:
        if cashflow_change['current'] > 0 and profit_change['current'] > 0:
            if cashflow_change['current'] > profit_change['current']:
                insights.append({
                    'typ': 'Pozytywny',
                    'opis': "Cashflow operacyjny wyższy niż zysk netto - dobra jakość zysków",
                    'ikona': '✅'
                })
    
    return insights

def detect_warning_signals(data, ratios):
    """Wykrywa niepokojące sygnały"""
    warnings = []
    
    # Płynność
    if 'wskaznik_plynnosciI' in ratios:
        if ratios['wskaznik_plynnosciI'] < 1:
            warnings.append({
                'typ': 'Płynność',
                'poziom': 'Krytyczny',
                'opis': f"Wskaźnik płynności bieżącej: {ratios['wskaznik_plynnosciI']:.2f} (poniżej 1.0)",
                'ikona': '🔴'
            })
        elif ratios['wskaznik_plynnosciI'] < 1.5:
            warnings.append({
                'typ': 'Płynność',
                'poziom': 'Ostrzeżenie',
                'opis': f"Wskaźnik płynności bieżącej: {ratios['wskaznik_plynnosciI']:.2f} (poniżej 1.5)",
                'ikona': '🟡'
            })
    
    # Zadłużenie
    if 'wskaznik_zadluzenia' in ratios:
        if ratios['wskaznik_zadluzenia'] > 0.7:
            warnings.append({
                'typ': 'Zadłużenie',
                'poziom': 'Ostrzeżenie',
                'opis': f"Wysokie zadłużenie: {ratios['wskaznik_zadluzenia']*100:.1f}%",
                'ikona': '🟡'
            })
    
    # Rentowność
    if 'roe' in ratios and ratios['roe'] < 0:
        warnings.append({
            'typ': 'Rentowność',
            'poziom': 'Krytyczny',
            'opis': f"Ujemny ROE: {ratios['roe']:.2f}%",
            'ikona': '🔴'
        })
    
    return warnings

# Interfejs użytkownika
st.title("📊 Analityk Finansowy - Analiza Sprawozdań")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Konfiguracja")
    
    # Możliwość wgrania wielu plików
    uploaded_files = st.file_uploader(
        "Wgraj sprawozdania finansowe (XML)", 
        type=['xml'],
        accept_multiple_files=True,
        help="Możesz wgrać wiele plików z różnych okresów do porównania"
    )
    
    st.markdown("---")
    st.markdown("### 📋 O aplikacji")
    st.info("""
    Aplikacja analizuje sprawozdania finansowe i dostarcza:
    - Kluczowe wskaźniki finansowe
    - Analizę cashflow
    - **Porównania rok do roku**
    - **Analizę trendów**
    - Wykrywanie sygnałów ostrzegawczych
    - Ocenę kondycji finansowej
    
    💡 **Tip**: Wgraj kilka sprawozdań z różnych lat aby zobaczyć trendy!
    """)
    
    if uploaded_files and len(uploaded_files) > 1:
        st.success(f"✅ Wgrano {len(uploaded_files)} plików - analiza porównawcza aktywna!")

# Główna część aplikacji
if uploaded_files is not None and len(uploaded_files) > 0:
    # Wczytanie i parsowanie wszystkich XML
    all_financial_data = []
    
    for uploaded_file in uploaded_files:
        xml_content = uploaded_file.read()
        root = parse_financial_xml(xml_content)
        
        if root is not None:
            financial_data = extract_financial_data(root)
            financial_data['_filename'] = uploaded_file.name
            all_financial_data.append(financial_data)
    
    if all_financial_data:
        # Używamy najnowszych danych jako głównych
        financial_data = all_financial_data[-1]
        
        # Porównanie okresów (jeśli jest więcej niż jeden plik)
        comparisons = None
        if len(all_financial_data) > 1:
            comparisons = compare_periods(all_financial_data)
        
        # Obliczenie wskaźników
        ratios = calculate_financial_ratios(financial_data)
        
        # Analiza cashflow
        cf_analysis = analyze_cashflow(financial_data)
        
        # Wykrywanie ostrzeżeń
        warnings = detect_warning_signals(financial_data, ratios)
        
        # Analiza zmian (jeśli są porównania)
        insights = []
        if comparisons:
            insights = analyze_changes(financial_data, comparisons)
        
        # Dashboard - Podsumowanie
        st.header("🎯 Podsumowanie Wykonawcze")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status_color = "🟢" if len(warnings) == 0 else "🟡" if len(warnings) <= 2 else "🔴"
            st.metric("Status ogólny", f"{status_color} {'Dobry' if len(warnings) == 0 else 'Wymaga uwagi' if len(warnings) <= 2 else 'Niepokojący'}")
        
        with col2:
            if 'wskaznik_plynnosciI' in ratios:
                st.metric("Płynność bieżąca", f"{ratios['wskaznik_plynnosciI']:.2f}")
        
        with col3:
            if 'wskaznik_zadluzenia' in ratios:
                st.metric("Zadłużenie", f"{ratios['wskaznik_zadluzenia']*100:.1f}%")
        
        with col4:
            if 'roe' in ratios:
                st.metric("ROE", f"{ratios['roe']:.2f}%")
        
        st.markdown("---")
        
        # NOWA SEKCJA: Analiza trendów (tylko jeśli jest więcej niż 1 plik)
        if comparisons:
            st.header("📊 Analiza Trendów - Co się zmienia?")
            
            # Grupujemy zmiany według kierunku
            increases = [c for c in comparisons if c['change_pct'] > 5]
            decreases = [c for c in comparisons if c['change_pct'] < -5]
            stable = [c for c in comparisons if -5 <= c['change_pct'] <= 5]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("📈 Wzrosty")
                if increases:
                    for item in sorted(increases, key=lambda x: x['change_pct'], reverse=True)[:5]:
                        st.metric(
                            item['metric'],
                            f"{item['current']:,.0f}",
                            delta=f"{item['change_pct']:+.1f}%"
                        )
                else:
                    st.info("Brak znaczących wzrostów")
            
            with col2:
                st.subheader("📉 Spadki")
                if decreases:
                    for item in sorted(decreases, key=lambda x: x['change_pct'])[:5]:
                        st.metric(
                            item['metric'],
                            f"{item['current']:,.0f}",
                            delta=f"{item['change_pct']:+.1f}%"
                        )
                else:
                    st.info("Brak znaczących spadków")
            
            with col3:
                st.subheader("➡️ Stabilne")
                if stable:
                    for item in stable[:5]:
                        st.metric(
                            item['metric'],
                            f"{item['current']:,.0f}",
                            delta=f"{item['change_pct']:+.1f}%"
                        )
                else:
                    st.info("Brak stabilnych pozycji")
            
            # Wykres porównawczy dla kluczowych metryk
            st.subheader("📊 Porównanie kluczowych wskaźników")
            
            if comparisons:
                # Top 6 największych zmian (bezwzględnie)
                top_changes = sorted(comparisons, key=lambda x: abs(x['change_pct']), reverse=True)[:6]
                
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    name='Poprzedni okres',
                    x=[c['metric'] for c in top_changes],
                    y=[c['previous'] for c in top_changes],
                    marker_color='lightblue'
                ))
                
                fig.add_trace(go.Bar(
                    name='Bieżący okres',
                    x=[c['metric'] for c in top_changes],
                    y=[c['current'] for c in top_changes],
                    marker_color='darkblue'
                ))
                
                fig.update_layout(
                    title="Porównanie okresów - największe zmiany",
                    xaxis_title="",
                    yaxis_title="Wartość",
                    barmode='group',
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # NOWA SEKCJA: Analiza przyczyn zmian
            if insights:
                st.header("🔍 Z czego wynikają zmiany?")
                
                for insight in insights:
                    if insight['typ'] == 'Pozytywny':
                        st.success(f"{insight['ikona']} **{insight['typ']}**: {insight['opis']}")
                    elif insight['typ'] == 'Negatywny':
                        st.error(f"{insight['ikona']} **{insight['typ']}**: {insight['opis']}")
                    else:
                        st.warning(f"{insight['ikona']} **{insight['typ']}**: {insight['opis']}")
                
                st.markdown("---")
        
        # Sekcja ostrzeżeń
        if warnings:
            st.header("⚠️ Sygnały ostrzegawcze")
            
            for warning in warnings:
                if warning['poziom'] == 'Krytyczny':
                    st.error(f"{warning['ikona']} **{warning['typ']}**: {warning['opis']}")
                else:
                    st.warning(f"{warning['ikona']} **{warning['typ']}**: {warning['opis']}")
        else:
            st.success("✅ Nie wykryto niepokojących sygnałów")
        
        st.markdown("---")
        
        # Analiza Cashflow
        st.header("💰 Analiza Cashflow")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if cf_analysis['details']:
                cf_df = pd.DataFrame([
                    {'Kategoria': k, 'Wartość': v if v is not None else 0}
                    for k, v in cf_analysis['details'].items()
                    if v is not None
                ])
                
                if not cf_df.empty:
                    fig = go.Figure(data=[
                        go.Bar(
                            x=cf_df['Kategoria'],
                            y=cf_df['Wartość'],
                            marker_color=['green' if x > 0 else 'red' for x in cf_df['Wartość']]
                        )
                    ])
                    fig.update_layout(
                        title="Przepływy pieniężne",
                        xaxis_title="",
                        yaxis_title="Wartość (tys. PLN)",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Status Cashflow")
            if cf_analysis['status'] == 'Dobry':
                st.success(f"✅ {cf_analysis['status']}")
            else:
                st.error(f"⚠️ {cf_analysis['status']}")
            
            if cf_analysis['alerts']:
                st.markdown("**Uwagi:**")
                for alert in cf_analysis['alerts']:
                    st.markdown(f"- {alert}")
        
        st.markdown("---")
        
        # Wskaźniki finansowe
        st.header("📈 Wskaźniki Finansowe")
        
        if ratios:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Płynność i Zadłużenie")
                ratios_df = pd.DataFrame([
                    {'Wskaźnik': 'Płynność bieżąca', 'Wartość': ratios.get('wskaznik_plynnosciI', 0), 'Norma': '1.5-2.0'},
                    {'Wskaźnik': 'Zadłużenie', 'Wartość': ratios.get('wskaznik_zadluzenia', 0) * 100, 'Norma': '< 70%'}
                ])
                st.dataframe(ratios_df, hide_index=True, use_container_width=True)
            
            with col2:
                st.subheader("Rentowność")
                profitability_df = pd.DataFrame([
                    {'Wskaźnik': 'ROE', 'Wartość': f"{ratios.get('roe', 0):.2f}%"},
                    {'Wskaźnik': 'ROA', 'Wartość': f"{ratios.get('roa', 0):.2f}%"}
                ])
                st.dataframe(profitability_df, hide_index=True, use_container_width=True)
        
        st.markdown("---")
        
        # Szczegółowe dane
        with st.expander("🔍 Szczegółowe dane finansowe"):
            st.subheader("Wszystkie wyekstrahowane dane")
            df_details = pd.DataFrame([
                {'Pozycja': k, 'Wartość': v}
                for k, v in financial_data.items()
                if isinstance(v, (int, float))
            ])
            st.dataframe(df_details, use_container_width=True)
        
        # Rekomendacje
        st.header("💡 Rekomendacje")
        
        recommendations = []
        
        if 'wskaznik_plynnosciI' in ratios and ratios['wskaznik_plynnosciI'] < 1.5:
            recommendations.append("📍 Rozważ poprawę płynności finansowej poprzez zarządzanie należnościami i zapasami")
        
        if 'wskaznik_zadluzenia' in ratios and ratios['wskaznik_zadluzenia'] > 0.6:
            recommendations.append("📍 Wysokie zadłużenie - rozważ redukcję zobowiązań lub zwiększenie kapitału własnego")
        
        if 'roe' in ratios and ratios['roe'] < 10:
            recommendations.append("📍 Niska rentowność - analiza kosztów i możliwości zwiększenia marży")
        
        if not recommendations:
            st.success("✅ Sytuacja finansowa spółki jest stabilna. Kontynuuj obecną strategię.")
        else:
            for rec in recommendations:
                st.info(rec)
    
    else:
        st.warning("⚠️ Nie udało się wyekstrahować danych finansowych z pliku XML. Sprawdź format pliku.")

else:
    # Ekran startowy
    st.info("👆 Wgraj plik XML ze sprawozdaniem finansowym, aby rozpocząć analizę")
    
    st.markdown("### 🎯 Funkcje aplikacji:")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ✅ **Automatyczna analiza:**
        - Wskaźniki płynności
        - Wskaźniki zadłużenia
        - Wskaźniki rentowności
        """)
    
    with col2:
        st.markdown("""
        ✅ **Inteligentne alerty:**
        - Wykrywanie problemów z płynnością
        - Sygnały o wysokim zadłużeniu
        - Analiza cashflow
        """)
    
    st.markdown("---")
    st.markdown("### 📝 Przykładowa struktura XML:")
    st.code("""
    <sprawozdanie>
        <bilans>
            <aktywa>1000000</aktywa>
            <aktywa_obrotowe>500000</aktywa_obrotowe>
            <zobowiazania>400000</zobowiazania>
            <zobowiazania_krotkoterminowe>200000</zobowiazania_krotkoterminowe>
            <kapital_wlasny>600000</kapital_wlasny>
        </bilans>
        <rachunek>
            <zysk_netto>50000</zysk_netto>
        </rachunek>
    </sprawozdanie>
    """, language="xml")
