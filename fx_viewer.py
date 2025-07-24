import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
from typing import Dict, List, Tuple
import math
import requests
import json

# Konfiguracja strony
st.set_page_config(
    page_title="Kalendarz FX",
    page_icon="💱",
    layout="wide"
)

# Inicjalizacja session state
if 'selected_window' not in st.session_state:
    st.session_state.selected_window = {}
if 'volumes' not in st.session_state:
    st.session_state.volumes = {}
if 'current_month' not in st.session_state:
    st.session_state.current_month = datetime(2025, 7, 1)
if 'quoted_transactions' not in st.session_state:
    st.session_state.quoted_transactions = []

# Stałe
SPOT_RATE = 4.2500
FRED_API_KEY = "693819ccc32ac43704fbbc15cfb4a6d7"

@st.cache_data(ttl=3600)  # Cache na 1 godzinę
def get_bond_yields():
    """Pobiera aktualne rentowności obligacji 10-letnich z FRED API"""
    try:
        # Kody serii FRED
        poland_series = "IRLTLT01PLM156N"  # Polska 10Y
        germany_series = "IRLTLT01DEM156N"  # Niemcy 10Y
        
        base_url = "https://api.stlouisfed.org/fred/series/observations"
        
        # Pobierz dane dla Polski
        pl_response = requests.get(base_url, params={
            'series_id': poland_series,
            'api_key': FRED_API_KEY,
            'file_type': 'json',
            'limit': 1,
            'sort_order': 'desc'
        })
        
        # Pobierz dane dla Niemiec
        de_response = requests.get(base_url, params={
            'series_id': germany_series,
            'api_key': FRED_API_KEY,
            'file_type': 'json',
            'limit': 1,
            'sort_order': 'desc'
        })
        
        if pl_response.status_code == 200 and de_response.status_code == 200:
            pl_data = pl_response.json()
            de_data = de_response.json()
            
            # Wyciągnij najnowsze wartości
            pl_yield = float(pl_data['observations'][0]['value'])
            de_yield = float(de_data['observations'][0]['value'])
            
            # Daty ostatniej aktualizacji
            pl_date = pl_data['observations'][0]['date']
            de_date = de_data['observations'][0]['date']
            
            return {
                'pl_yield': pl_yield,
                'de_yield': de_yield,
                'pl_date': pl_date,
                'de_date': de_date,
                'success': True
            }
        else:
            return {
                'pl_yield': 5.42,  # fallback
                'de_yield': 2.63,  # fallback
                'success': False,
                'error': f"API Error: PL={pl_response.status_code}, DE={de_response.status_code}"
            }
            
    except Exception as e:
        return {
            'pl_yield': 5.42,  # fallback
            'de_yield': 2.63,  # fallback
            'success': False,
            'error': str(e)
        }

def get_polish_month_name(date: datetime) -> str:
    months = [
        'Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec',
        'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień'
    ]
    return f"{months[date.month - 1]} {date.year}"

def is_weekday(date: datetime) -> bool:
    return date.weekday() < 5  # 0-4 to poniedziałek-piątek

def calculate_settlement_date(start_date: datetime, window_days: int) -> datetime:
    settlement_date = start_date
    days_added = 0
    
    while days_added < window_days:
        settlement_date += timedelta(days=1)
        if is_weekday(settlement_date):
            days_added += 1
    
    return settlement_date

def format_polish_date(date: datetime) -> str:
    return date.strftime("%d.%m.%Y")

def generate_working_days(year: int, month: int) -> List[Dict]:
    working_days = []
    _, days_in_month = calendar.monthrange(year, month)
    
    for day in range(1, days_in_month + 1):
        date = datetime(year, month, day)
        if is_weekday(date):
            working_days.append({
                'date': date,
                'day_of_month': day,
                'date_str': date.strftime("%Y-%m-%d")
            })
    
    return working_days

def calculate_forward_rate(start_date: datetime, window_days: int, pl_yield: float, de_yield: float) -> Dict:
    configs = {
        30: {'points_factor': 0.80, 'risk_factor': 0.35},
        60: {'points_factor': 0.75, 'risk_factor': 0.40},
        90: {'points_factor': 0.70, 'risk_factor': 0.45}
    }
    
    config = configs.get(window_days, configs[60])
    
    today = datetime.now()
    days_to_maturity = max((start_date - today).days, 1)
    
    # Używamy aktualnych rentowności z FRED
    T = days_to_maturity / 365.0
    theoretical_forward_rate = SPOT_RATE * (1 + pl_yield/100 * T) / (1 + de_yield/100 * T)
    theoretical_forward_points = theoretical_forward_rate - SPOT_RATE
    
    swap_risk = max(abs(theoretical_forward_points) * 0.25 * math.sqrt(window_days / 90), 0.015)
    
    points_given_to_client = theoretical_forward_points * config['points_factor']
    swap_risk_charged = swap_risk * config['risk_factor']
    
    net_client_points = points_given_to_client - swap_risk_charged
    client_rate = SPOT_RATE + net_client_points
    
    return {
        'client_rate': client_rate,
        'net_client_points': net_client_points,
        'theoretical_forward_points': theoretical_forward_points,
        'swap_risk': swap_risk,
        'days_to_maturity': days_to_maturity
    }

def add_to_quote(day_data: Dict, window_days: int, forward_calc: Dict, settlement_date: datetime, volume: float, pl_yield: float, de_yield: float):
    new_transaction = {
        'id': len(st.session_state.quoted_transactions) + 1,
        'open_date': format_polish_date(day_data['date']),
        'settlement_date': format_polish_date(settlement_date),
        'window_days': window_days,
        'forward_rate': forward_calc['client_rate'],
        'net_points': forward_calc['net_client_points'],
        'days_to_maturity': forward_calc['days_to_maturity'],
        'added_at': datetime.now().strftime("%H:%M:%S"),
        'month': get_polish_month_name(day_data['date']),
        'volume': volume or 0,
        'pl_yield_used': pl_yield,
        'de_yield_used': de_yield
    }
    
    st.session_state.quoted_transactions.append(new_transaction)

def calculate_weighted_summary() -> Dict:
    if not st.session_state.quoted_transactions:
        return {
            'total_volume': 0,
            'weighted_average_rate': 0,
            'weighted_average_points': 0,
            'total_transactions': 0,
            'total_value_pln': 0,
            'total_benefit_vs_spot': 0
        }
    
    transactions = st.session_state.quoted_transactions
    total_volume = sum(t['volume'] for t in transactions)
    total_value_pln = sum(t['volume'] * t['forward_rate'] for t in transactions)
    total_spot_value_pln = sum(t['volume'] * SPOT_RATE for t in transactions)
    total_benefit_vs_spot = total_value_pln - total_spot_value_pln
    
    if total_volume == 0:
        return {
            'total_volume': 0,
            'weighted_average_rate': sum(t['forward_rate'] for t in transactions) / len(transactions),
            'weighted_average_points': sum(t['net_points'] for t in transactions) / len(transactions),
            'total_transactions': len(transactions),
            'total_value_pln': 0,
            'total_benefit_vs_spot': 0
        }
    
    weighted_rate_sum = sum(t['forward_rate'] * t['volume'] for t in transactions)
    weighted_points_sum = sum(t['net_points'] * t['volume'] for t in transactions)
    
    return {
        'total_volume': total_volume,
        'weighted_average_rate': weighted_rate_sum / total_volume,
        'weighted_average_points': weighted_points_sum / total_volume,
        'total_transactions': len(transactions),
        'total_value_pln': total_value_pln,
        'total_benefit_vs_spot': total_benefit_vs_spot
    }

def clear_quote():
    st.session_state.quoted_transactions = []

def remove_from_quote(transaction_id: int):
    st.session_state.quoted_transactions = [
        t for t in st.session_state.quoted_transactions 
        if t['id'] != transaction_id
    ]

def generate_email_body() -> str:
    if not st.session_state.quoted_transactions:
        return ""
    
    summary = calculate_weighted_summary()
    
    email_body = f"""WYCENA FORWARD EUR/PLN
==============================

Data wyceny: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
Kurs spot referencyjny: {SPOT_RATE:.4f}
Rentowności używane: PL 10Y = {bond_data['pl_yield']:.2f}%, DE 10Y = {bond_data['de_yield']:.2f}%
Źródło: FRED API St. Louis Fed

LISTA TRANSAKCJI:
================

"""
    
    for i, transaction in enumerate(st.session_state.quoted_transactions, 1):
        benefit_vs_spot = ((transaction['forward_rate'] - SPOT_RATE) / SPOT_RATE) * 100
        value_pln = transaction['volume'] * transaction['forward_rate']
        
        email_body += f"""{i}. {transaction['open_date']} ({transaction['month']})
   Rozliczenie: {transaction['settlement_date']}
   Okno: {transaction['window_days']} dni
   Wolumen: €{transaction['volume']:,.0f}
   Kurs Forward: {transaction['forward_rate']:.4f}
   vs Spot: {'+' if benefit_vs_spot >= 0 else ''}{benefit_vs_spot:.2f}%
   Wartość PLN: {value_pln:,.0f} PLN

"""
    
    email_body += f"""PODSUMOWANIE:
=============
Liczba transakcji: {summary['total_transactions']}
Łączny wolumen: €{summary['total_volume']:,.0f}
Średni ważony kurs: {summary['weighted_average_rate']:.4f}
"""
    
    if summary['total_volume'] > 0:
        avg_benefit_vs_spot = ((summary['weighted_average_rate'] - SPOT_RATE) / SPOT_RATE) * 100
        email_body += f"""Łączna wartość PLN: {summary['total_value_pln']:,.0f} PLN
Korzyść vs Spot: {'+' if avg_benefit_vs_spot >= 0 else ''}{avg_benefit_vs_spot:.3f}%
Korzyść PLN: {'+' if summary['total_benefit_vs_spot'] >= 0 else ''}{summary['total_benefit_vs_spot']:,.0f} PLN
"""
    
    email_body += """
---
POTWIERDZENIE:
Zgadzam się i potwierdzam zawarcie transakcji terminowych forward zgodnie z powyższą wyceną. Transakcje zawarte są w celu zabezpieczenia ryzyka kursowego wynikającego z oczekiwanych należności we wskazanym okresie. Transakcje wynikają z działalności operacyjnej i nie mają charakteru spekulacyjnego.

---
Wygenerowane przez Kalendarz FX"""
    
    return email_body

# GŁÓWNA APLIKACJA
st.title("💱 Kalendarz FX")

# Pobierz aktualne rentowności obligacji
bond_data = get_bond_yields()

col_info, col_refresh = st.columns([4, 1])
with col_info:
    if bond_data['success']:
        st.success(f"✅ Dane FRED załadowane: PL={bond_data['pl_yield']:.2f}% ({bond_data['pl_date']}), DE={bond_data['de_yield']:.2f}% ({bond_data['de_date']})")
    else:
        st.warning(f"⚠️ Błąd API FRED: {bond_data.get('error', 'Nieznany błąd')}. Używam wartości domyślnych.")

with col_refresh:
    if st.button("🔄 Odśwież FRED", help="Odśwież dane rentowności obligacji"):
        st.cache_data.clear()
        st.rerun()

pl_yield = bond_data['pl_yield']
de_yield = bond_data['de_yield']

# Karty informacyjne
spread = pl_yield - de_yield
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.info(f"**Kurs Spot EUR/PLN**: {SPOT_RATE:.4f}")
with col2:
    st.info(f"**PL 10Y**: {pl_yield:.2f}%")
with col3:
    st.info(f"**DE 10Y**: {de_yield:.2f}%")
with col4:
    st.metric("**Spread PL-DE**", f"{spread:.2f} pkt", help="Różnica między rentownościami Polski i Niemiec")

# Tabs
tab1, tab2 = st.tabs([
    f"📅 Kalendarz ({len(generate_working_days(st.session_state.current_month.year, st.session_state.current_month.month))} dni)",
    f"📋 Wycena ({len(st.session_state.quoted_transactions)})"
])

with tab1:
    # Nawigacja miesięcy
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("← Poprzedni miesiąc"):
            current = st.session_state.current_month
            if current.month == 1:
                st.session_state.current_month = datetime(current.year - 1, 12, 1)
            else:
                st.session_state.current_month = datetime(current.year, current.month - 1, 1)
            st.rerun()
    
    with col2:
        st.markdown(f"<h2 style='text-align: center'>{get_polish_month_name(st.session_state.current_month)}</h2>", 
                   unsafe_allow_html=True)
    
    with col3:
        max_date = datetime.now() + timedelta(days=365)
        if st.session_state.current_month < max_date:
            if st.button("Następny miesiąc →"):
                current = st.session_state.current_month
                if current.month == 12:
                    st.session_state.current_month = datetime(current.year + 1, 1, 1)
                else:
                    st.session_state.current_month = datetime(current.year, current.month + 1, 1)
                st.rerun()
    
    st.divider()
    
    # Generowanie dni roboczych
    working_days = generate_working_days(
        st.session_state.current_month.year, 
        st.session_state.current_month.month
    )
    
    # Wyświetlanie kalendarza w kolumnach
    cols_per_row = 5
    for i in range(0, len(working_days), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j, col in enumerate(cols):
            if i + j < len(working_days):
                day_data = working_days[i + j]
                date_str = day_data['date_str']
                
                with col:
                    with st.container(border=True):
                        # Nagłówek dnia
                        st.markdown(f"**{day_data['day_of_month']}** ({day_data['date'].strftime('%a')})")
                        
                        # Wybór okna czasowego
                        window_key = f"window_{date_str}"
                        window_days = st.selectbox(
                            "Okno:",
                            [30, 60, 90],
                            index=1,  # domyślnie 60
                            key=window_key
                        )
                        
                        # Input wolumenu
                        volume_key = f"volume_{date_str}"
                        volume = st.number_input(
                            "Wolumen EUR:",
                            min_value=0,
                            value=0,
                            step=10000,
                            key=volume_key
                        )
                        
                        # Obliczenia
                        forward_calc = calculate_forward_rate(day_data['date'], window_days, pl_yield, de_yield)
                        settlement_date = calculate_settlement_date(day_data['date'], window_days)
                        rate_advantage = ((forward_calc['client_rate'] - SPOT_RATE) / SPOT_RATE) * 100
                        
                        # Wyświetlanie wyników
                        st.metric(
                            "Forward Rate",
                            f"{forward_calc['client_rate']:.4f}",
                            f"{rate_advantage:+.2f}%"
                        )
                        
                        st.caption(f"Rozliczenie: {format_polish_date(settlement_date)}")
                        st.caption(f"Dni: {forward_calc['days_to_maturity']} | Pkt: {forward_calc['net_client_points']:+.4f}")
                        
                        # Przycisk dodawania
                        if st.button("➕ Dodaj", key=f"add_{date_str}", use_container_width=True):
                            add_to_quote(day_data, window_days, forward_calc, settlement_date, volume, pl_yield, de_yield)
                            st.success("Dodano do wyceny!")
                            st.rerun()

with tab2:
    st.header("Lista Transakcji Forward")
    
    if not st.session_state.quoted_transactions:
        st.info("Brak transakcji w wycenie. Przejdź do kalendarza i dodaj transakcje.")
    else:
        # Przyciski akcji
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🗑️ Wyczyść wszystko", type="secondary"):
                clear_quote()
                st.rerun()
        
        with col2:
            if st.button("📧 Przygotuj email", type="primary"):
                email_body = generate_email_body()
                st.text_area("Treść emaila do skopiowania:", email_body, height=300)
        
        st.divider()
        
        # Tabela transakcji
        df_transactions = []
        for i, t in enumerate(st.session_state.quoted_transactions, 1):
            benefit_vs_spot = ((t['forward_rate'] - SPOT_RATE) / SPOT_RATE) * 100
            value_pln = t['volume'] * t['forward_rate']
            
            df_transactions.append({
                'Lp.': i,
                'Otwarcie': t['open_date'],
                'Rozliczenie': t['settlement_date'],
                'Okno': f"{t['window_days']} dni",
                'Wolumen (EUR)': f"{t['volume']:,.0f}" if t['volume'] > 0 else '-',
                'Kurs Forward': f"{t['forward_rate']:.4f}",
                'vs Spot %': f"{benefit_vs_spot:+.2f}%",
                'Wartość PLN': f"{value_pln:,.0f}" if t['volume'] > 0 else '-',
                'Miesiąc': t['month'],
                'PL Yield': f"{t.get('pl_yield_used', 'N/A'):.2f}%",
                'DE Yield': f"{t.get('de_yield_used', 'N/A'):.2f}%"
            })
        
        df = pd.DataFrame(df_transactions)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Możliwość usuwania pojedynczych transakcji
        st.subheader("Usuń transakcję")
        if st.session_state.quoted_transactions:
            transaction_options = [
                f"{i+1}. {t['open_date']} - {t['forward_rate']:.4f}"
                for i, t in enumerate(st.session_state.quoted_transactions)
            ]
            
            selected_to_remove = st.selectbox(
                "Wybierz transakcję do usunięcia:",
                options=range(len(transaction_options)),
                format_func=lambda x: transaction_options[x]
            )
            
            if st.button("🗑️ Usuń wybraną transakcję", type="secondary"):
                transaction_id = st.session_state.quoted_transactions[selected_to_remove]['id']
                remove_from_quote(transaction_id)
                st.rerun()
        
        st.divider()
        
        # Podsumowanie
        st.subheader("📊 Podsumowanie Wyceny")
        summary = calculate_weighted_summary()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Liczba transakcji", summary['total_transactions'])
        
        with col2:
            if summary['total_volume'] > 0:
                st.metric("Łączny wolumen", f"€{summary['total_volume']:,.0f}")
            else:
                st.metric("Łączny wolumen", "Brak wolumenów")
        
        with col3:
            label = "Średni ważony kurs" if summary['total_volume'] > 0 else "Średni kurs"
            st.metric(label, f"{summary['weighted_average_rate']:.4f}")
        
        with col4:
            if summary['total_volume'] > 0:
                avg_benefit = ((summary['weighted_average_rate'] - SPOT_RATE) / SPOT_RATE) * 100
                st.metric("Korzyść vs Spot", f"{avg_benefit:+.3f}%")
                st.metric("Łączna wartość PLN", f"{summary['total_value_pln']:,.0f}")
                st.metric("Korzyść PLN", f"{summary['total_benefit_vs_spot']:+,.0f}")

# Footer
st.divider()
st.caption("Kalendarz FX - System wyceny transakcji forward EUR/PLN")
