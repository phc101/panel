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

def extract_mf_data(root):
    """
    Wyciąga dane z formatu Ministerstwa Finansów (eSPR)
    Format: KwotaA (bieżący rok) i KwotaB (rok poprzedni)
    """
    # Namespace handling
    namespaces = {
        'ns1': 'http://www.mf.gov.pl/schematy/SF/DefinicjeTypySprawozdaniaFinansowe/2025/01/01/JednostkaInnaWZlotych',
        'ns2': 'http://www.mf.gov.pl/schematy/SF/DefinicjeTypySprawozdaniaFinansowe/2025/01/01/JednostkaInnaStruktury',
        'ns3': 'http://www.mf.gov.pl/schematy/SF/DefinicjeTypySprawozdaniaFinansowe/2018/07/09/DefinicjeTypySprawozdaniaFinansowe/'
    }
    
    data_current = {}
    data_previous = {}
    
    # Wyciągamy informacje o firmie i okresie
    nazwa_firmy = root.find('.//ns3:NazwaFirmy', namespaces)
    okres_od = root.find('.//ns3:OkresOd', namespaces)
    okres_do = root.find('.//ns3:OkresDo', namespaces)
    
    info = {
        'nazwa': nazwa_firmy.text if nazwa_firmy is not None else 'N/A',
        'okres_od': okres_od.text if okres_od is not None else 'N/A',
        'okres_do': okres_do.text if okres_do is not None else 'N/A'
    }
    
    # Mapowanie znaczników na czytelne nazwy
    mapping = {
        # BILANS - AKTYWA
        'Aktywa': 'suma_aktywow',
        'Aktywa_A': 'aktywa_trwale',
        'Aktywa_B': 'aktywa_obrotowe',
        'Aktywa_B_I': 'zapasy',
        'Aktywa_B_II': 'naleznosci_krotkoterminowe',
        'Aktywa_B_III': 'srodki_pieniezne',
        
        # BILANS - PASYWA
        'Pasywa': 'suma_pasywow',
        'Pasywa_A': 'kapital_wlasny',
        'Pasywa_B': 'zobowiazania_i_rezerwy',
        'Pasywa_B_I': 'rezerwy',
        'Pasywa_B_II': 'zobowiazania_dlugoterminowe',
        'Pasywa_B_III': 'zobowiazania_krotkoterminowe',
        
        # RACHUNEK ZYSKÓW I STRAT
        'RZiSPor_A': 'przychody_netto_sprzedazy',
        'RZiSPor_A_I': 'przychody_netto_produktow',
        'RZiSPor_A_IV': 'przychody_netto_towarow',
        'RZiSPor_B': 'koszty_dzialalnosci_operacyjnej',
        'RZiSPor_B_I': 'amortyzacja',
        'RZiSPor_B_II': 'zuzycie_materialow',
        'RZiSPor_B_III': 'uslugi_obce',
        'RZiSPor_B_IV': 'podatki_oplaty',
        'RZiSPor_B_V': 'wynagrodzenia',
        'RZiSPor_B_VIII': 'pozostale_koszty_operacyjne',
        'RZiSPor_C': 'zysk_strata_sprzedazy',
        'RZiSPor_D': 'pozostale_przychody_operacyjne',
        'RZiSPor_E': 'pozostale_koszty_operacyjne',
        'RZiSPor_F': 'zysk_strata_dzialalnosci_operacyjnej',
        'RZiSPor_G': 'przychody_finansowe',
        'RZiSPor_H': 'koszty_finansowe',
        'RZiSPor_I': 'zysk_strata_brutto',
        'RZiSPor_J': 'podatek_dochodowy',
        'RZiSPor_K': 'zysk_strata_netto',
    }
    
    # Iterujemy przez wszystkie elementy
    for element in root.iter():
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        
        # Sprawdzamy czy to element z kwotami
        kwota_a = element.find('ns3:KwotaA', namespaces)
        kwota_b = element.find('ns3:KwotaB', namespaces)
        
        if kwota_a is not None and kwota_b is not None:
            try:
                # Szukamy mapowania
                mapped_name = None
                for key, value in mapping.items():
                    if key in tag:
                        mapped_name = value
                        break
                
                if mapped_name:
                    data_current[mapped_name] = float(kwota_a.text)
                    data_previous[mapped_name] = float(kwota_b.text)
                else:
                    # Zapisujemy z oryginalną nazwą
                    data_current[tag] = float(kwota_a.text)
                    data_previous[tag] = float(kwota_b.text)
            except (ValueError, AttributeError):
                pass
    
    return data_current, data_previous, info

def extract_financial_data(root):
    """Uniwersalny parser dla różnych formatów XML"""
    # Najpierw próbujemy format MF
    try:
        data_current, data_previous, info = extract_mf_data(root)
        if data_current:
            data_current['_period'] = info['okres_do']
            data_current['_nazwa'] = info['nazwa']
            data_current['_source'] = 'mf'
            if data_previous:
                data_previous['_period'] = info['okres_od']
                data_previous['_nazwa'] = info['nazwa']
                data_previous['_source'] = 'mf'
            return [data_current, data_previous] if data_previous else [data_current]
    except:
        pass
    
    # Jeśli nie działa format MF, próbujemy generycznego parsera
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
    all_data['_source'] = 'generic'
    return [all_data]

def calculate_financial_ratios(data):
    """Oblicza wskaźniki finansowe"""
    ratios = {}
    
    # Wskaźniki płynności
    if 'aktywa_obrotowe' in data and 'zobowiazania_krotkoterminowe' in data:
        if data['zobowiazania_krotkoterminowe'] != 0:
            ratios['wskaznik_plynnosciI'] = data['aktywa_obrotowe'] / data['zobowiazania_krotkoterminowe']
    
    # Wskaźnik płynności szybkiej
    if 'naleznosci_krotkoterminowe' in data and 'srodki_pieniezne' in data and 'zobowiazania_krotkoterminowe' in data:
        if data['zobowiazania_krotkoterminowe'] != 0:
            ratios['wskaznik_plynnosciII'] = (data['naleznosci_krotkoterminowe'] + data['srodki_pieniezne']) / data['zobowiazania_krotkoterminowe']
    
    # Wskaźnik zadłużenia
    zobowiazania = data.get('zobowiazania_i_rezerwy', data.get('zobowiazania', 0))
    if 'suma_aktywow' in data and zobowiazania:
        if data['suma_aktywow'] != 0:
            ratios['wskaznik_zadluzenia'] = zobowiazania / data['suma_aktywow']
    
    # ROE
    if 'zysk_strata_netto' in data and 'kapital_wlasny' in data:
        if data['kapital_wlasny'] != 0:
            ratios['roe'] = (data['zysk_strata_netto'] / data['kapital_wlasny']) * 100
    elif 'zysk_netto' in data and 'kapital_wlasny' in data:
        if data['kapital_wlasny'] != 0:
            ratios['roe'] = (data['zysk_netto'] / data['kapital_wlasny']) * 100
    
    # ROA
    zysk_netto = data.get('zysk_strata_netto', data.get('zysk_netto', 0))
    if 'suma_aktywow' in data and zysk_netto:
        if data['suma_aktywow'] != 0:
            ratios['roa'] = (zysk_netto / data['suma_aktywow']) * 100
    
    # Rentowność sprzedaży
    if 'zysk_strata_dzialalnosci_operacyjnej' in data and 'przychody_netto_sprzedazy' in data:
        if data['przychody_netto_sprzedazy'] != 0:
            ratios['rentownosc_sprzedazy'] = (data['zysk_strata_dzialalnosci_operacyjnej'] / data['przychody_netto_sprzedazy']) * 100
    
    # Marża zysku netto
    zysk_netto = data.get('zysk_strata_netto', data.get('zysk_netto', 0))
    przychody = data.get('przychody_netto_sprzedazy', data.get('przychody_netto', 0))
    if przychody and zysk_netto is not None:
        if przychody != 0:
            ratios['marza_netto'] = (zysk_netto / przychody) * 100
    
    return ratios

def compare_periods(data_list):
    """Porównuje dane z różnych okresów"""
    if len(data_list) < 2:
        return None
    
    # Sortujemy według okresu
    sorted_data = sorted([d for d in data_list if d.get('_period')], 
                        key=lambda x: str(x.get('_period', '')))
    
    if len(sorted_data) < 2:
        return None
    
    comparisons = []
    
    # Kluczowe pozycje do porównania
    key_metrics = [
        'przychody_netto_sprzedazy', 'zysk_strata_netto', 'zysk_strata_dzialalnosci_operacyjnej',
        'suma_aktywow', 'aktywa_obrotowe', 'kapital_wlasny',
        'zobowiazania_i_rezerwy', 'zobowiazania_krotkoterminowe',
        'koszty_dzialalnosci_operacyjnej', 'wynagrodzenia', 'zapasy'
    ]
    
    # Porównujemy ostatni okres z poprzednim
    current = sorted_data[-1]
    previous = sorted_data[-2]
    
    for metric in key_metrics:
        current_val = current.get(metric)
        previous_val = previous.get(metric)
        
        if current_val is not None and previous_val is not None and previous_val != 0:
            change_pct = ((current_val - previous_val) / abs(previous_val)) * 100
            change_abs = current_val - previous_val
            
            comparisons.append({
                'metric': metric.replace('_', ' ').title(),
                'previous': previous_val,
                'current': current_val,
                'change_abs': change_abs,
                'change_pct': change_pct,
                'trend': '📈' if change_pct > 0 else '📉' if change_pct < 0 else '➡️'
            })
    
    return comparisons

def analyze_changes(data, comparisons):
    """Analizuje przyczyny zmian w wynikach"""
    insights = []
    
    if not comparisons:
        return insights
    
    # Analiza przychodów
    revenue_change = next((c for c in comparisons if 'przychody' in c['metric'].lower()), None)
    profit_change = next((c for c in comparisons if 'zysk' in c['metric'].lower() and 'netto' in c['metric'].lower()), None)
    costs_change = next((c for c in comparisons if 'koszty' in c['metric'].lower() and 'operacyjnej' in c['metric'].lower()), None)
    
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
    
    # Analiza kosztów
    if revenue_change and costs_change:
        if costs_change['change_pct'] > revenue_change['change_pct'] and costs_change['change_pct'] > 0:
            insights.append({
                'typ': 'Ostrzeżenie',
                'opis': f"Koszty operacyjne rosną szybciej niż przychody (+{costs_change['change_pct']:.1f}% vs +{revenue_change['change_pct']:.1f}%) - spadek marży",
                'ikona': '⚠️'
            })
    
    # Analiza aktywów i kapitału
    assets_change = next((c for c in comparisons if 'suma aktywow' in c['metric'].lower()), None)
    equity_change = next((c for c in comparisons if 'kapital' in c['metric'].lower()), None)
    
    if assets_change and equity_change:
        if assets_change['change_pct'] > equity_change['change_pct'] + 5:
            debt_growth = assets_change['change_pct'] - equity_change['change_pct']
            insights.append({
                'typ': 'Ostrzeżenie',
                'opis': f"Aktywa rosną szybciej niż kapitał własny (różnica {debt_growth:.1f}pp) - wzrost zadłużenia",
                'ikona': '⚠️'
            })
    
    return insights

def analyze_cashflow(data):
    """Analizuje cashflow - podstawowa wersja oparta na danych bilansowych"""
    analysis = {
        'status': 'Brak danych',
        'alerts': [],
        'details': {}
    }
    
    # Dla formatu MF nie mamy bezpośrednio cashflow, ale możemy ocenić płynność
    srodki = data.get('srodki_pieniezne', 0)
    naleznosci = data.get('naleznosci_krotkoterminowe', 0)
    zobowiazania_kr = data.get('zobowiazania_krotkoterminowe', 0)
    
    analysis['details'] = {
        'Środki pieniężne': srodki,
        'Należności krótkoterminowe': naleznosci,
        'Zobowiązania krótkoterminowe': zobowiazania_kr
    }
    
    # Analiza
    if srodki and zobowiazania_kr:
        if srodki > zobowiazania_kr * 0.3:
            analysis['status'] = 'Dobry'
            analysis['alerts'].append('✅ Dobry poziom środków pieniężnych względem zobowiązań')
        else:
            analysis['status'] = 'Wymaga uwagi'
            analysis['alerts'].append('⚠️ Niski poziom środków pieniężnych względem zobowiązań')
    
    return analysis

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
    
    # Zysk netto
    zysk_netto = data.get('zysk_strata_netto', data.get('zysk_netto'))
    if zysk_netto is not None and zysk_netto < 0:
        warnings.append({
            'typ': 'Wynik finansowy',
            'poziom': 'Krytyczny',
            'opis': f"Ujemny zysk netto: {zysk_netto:,.2f} PLN",
            'ikona': '🔴'
        })
    
    return warnings

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
    - Analizę płynności
    - **Porównania rok do roku**
    - **Analizę trendów**
    - Wykrywanie sygnałów ostrzegawczych
    - Ocenę kondycji finansowej
    
    💡 **Tip**: Wgraj kilka sprawozdań z różnych lat aby zobaczyć trendy!
    
    ✅ **Obsługuje format eSPR (Ministerstwo Finansów)**
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
            data_list = extract_financial_data(root)
            for data in data_list:
                data['_filename'] = uploaded_file.name
                all_financial_data.append(data)
    
    if all_financial_data:
        # Używamy najnowszych danych jako głównych
        all_financial_data.sort(key=lambda x: str(x.get('_period', '')))
        financial_data = all_financial_data[-1]
        
        # Wyświetlamy informacje o firmie (jeśli dostępne)
        if '_nazwa' in financial_data:
            st.title(f"📊 {financial_data['_nazwa']}")
            st.caption(f"Okres: {financial_data.get('_period', 'N/A')}")
        else:
            st.title("📊 Analiza Finansowa Spółki")
        
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
        
        st.markdown("---")
        
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
        
        # SEKCJA: Kluczowe wartości finansowe
        st.header("💰 Kluczowe wartości finansowe")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Przychody i Wynik")
            przychody = financial_data.get('przychody_netto_sprzedazy', 0)
            zysk_netto = financial_data.get('zysk_strata_netto', 0)
            zysk_op = financial_data.get('zysk_strata_dzialalnosci_operacyjnej', 0)
            
            st.metric("Przychody netto", f"{przychody:,.0f} PLN")
            st.metric("Zysk operacyjny", f"{zysk_op:,.0f} PLN", 
                     delta_color="normal" if zysk_op >= 0 else "inverse")
            st.metric("Zysk netto", f"{zysk_netto:,.0f} PLN",
                     delta_color="normal" if zysk_netto >= 0 else "inverse")
        
        with col2:
            st.subheader("Aktywa")
            suma_akt = financial_data.get('suma_aktywow', 0)
            akt_trw = financial_data.get('aktywa_trwale', 0)
            akt_obr = financial_data.get('aktywa_obrotowe', 0)
            
            st.metric("Suma aktywów", f"{suma_akt:,.0f} PLN")
            st.metric("Aktywa trwałe", f"{akt_trw:,.0f} PLN")
            st.metric("Aktywa obrotowe", f"{akt_obr:,.0f} PLN")
        
        with col3:
            st.subheader("Pasywa")
            kap_wl = financial_data.get('kapital_wlasny', 0)
            zob = financial_data.get('zobowiazania_i_rezerwy', 0)
            zob_kr = financial_data.get('zobowiazania_krotkoterminowe', 0)
            
            st.metric("Kapitał własny", f"{kap_wl:,.0f} PLN")
            st.metric("Zobowiązania razem", f"{zob:,.0f} PLN")
            st.metric("Zobowiązania krótkot.", f"{zob_kr:,.0f} PLN")
        
        st.markdown("---")
        
        # NOWA SEKCJA: Analiza trendów (tylko jeśli jest więcej niż 1 okres)
        if comparisons:
            st.header("📊 Analiza Trendów - Co się zmienia?")
            
            # Grupujemy zmiany według kierunku
            increases = [c for c in comparisons if c['change_pct'] > 2]
            decreases = [c for c in comparisons if c['change_pct'] < -2]
            stable = [c for c in comparisons if -2 <= c['change_pct'] <= 2]
            
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
                    yaxis_title="Wartość (PLN)",
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
        
        # Wskaźniki finansowe
        st.header("📈 Wskaźniki Finansowe")
        
        if ratios:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Płynność i Zadłużenie")
                ratios_data = []
                if 'wskaznik_plynnosciI' in ratios:
                    ratios_data.append({'Wskaźnik': 'Płynność bieżąca', 'Wartość': f"{ratios['wskaznik_plynnosciI']:.2f}", 'Norma': '1.5-2.0'})
                if 'wskaznik_plynnosciII' in ratios:
                    ratios_data.append({'Wskaźnik': 'Płynność szybka', 'Wartość': f"{ratios['wskaznik_plynnosciII']:.2f}", 'Norma': '1.0-1.2'})
                if 'wskaznik_zadluzenia' in ratios:
                    ratios_data.append({'Wskaźnik': 'Zadłużenie', 'Wartość': f"{ratios['wskaznik_zadluzenia']*100:.1f}%", 'Norma': '< 70%'})
                
                if ratios_data:
                    ratios_df = pd.DataFrame(ratios_data)
                    st.dataframe(ratios_df, hide_index=True, use_container_width=True)
            
            with col2:
                st.subheader("Rentowność")
                profitability_data = []
                if 'roe' in ratios:
                    profitability_data.append({'Wskaźnik': 'ROE', 'Wartość': f"{ratios['roe']:.2f}%"})
                if 'roa' in ratios:
                    profitability_data.append({'Wskaźnik': 'ROA', 'Wartość': f"{ratios['roa']:.2f}%"})
                if 'marza_netto' in ratios:
                    profitability_data.append({'Wskaźnik': 'Marża netto', 'Wartość': f"{ratios['marza_netto']:.2f}%"})
                if 'rentownosc_sprzedazy' in ratios:
                    profitability_data.append({'Wskaźnik': 'Rentowność sprzedaży', 'Wartość': f"{ratios['rentownosc_sprzedazy']:.2f}%"})
                
                if profitability_data:
                    profitability_df = pd.DataFrame(profitability_data)
                    st.dataframe(profitability_df, hide_index=True, use_container_width=True)
        
        st.markdown("---")
        
        # Szczegółowe dane
        with st.expander("🔍 Szczegółowe dane finansowe"):
            st.subheader("Wszystkie wyekstrahowane dane")
            df_details = pd.DataFrame([
                {'Pozycja': k.replace('_', ' ').title(), 'Wartość': f"{v:,.2f}" if isinstance(v, (int, float)) else str(v)}
                for k, v in financial_data.items()
                if not k.startswith('_') and isinstance(v, (int, float, str))
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
        
        if 'marza_netto' in ratios and ratios['marza_netto'] < 5:
            recommendations.append("📍 Niska marża netto - rozważ optymalizację kosztów lub podniesienie cen")
        
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
        - Wskaźniki płynności (bieżąca, szybka)
        - Wskaźniki zadłużenia
        - Wskaźniki rentowności (ROE, ROA, marża netto)
        - Analiza trendów rok-do-roku
        """)
    
    with col2:
        st.markdown("""
        ✅ **Inteligentne alerty:**
        - Wykrywanie problemów z płynnością
        - Sygnały o wysokim zadłużeniu
        - Analiza zmian i ich przyczyn
        - Rekomendacje biznesowe
        """)
    
    st.markdown("---")
    st.success("✅ **Obsługuje oficjalny format eSPR (Ministerstwo Finansów)**")
    st.markdown("Aplikacja automatycznie rozpoznaje i parsuje sprawozdania w formacie XML z systemu eSPR")
