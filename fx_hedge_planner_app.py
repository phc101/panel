import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

# Optional reportlab
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    except:
        pass
except ImportError:
    REPORTLAB_AVAILABLE = False

# Page config
st.set_page_config(
    page_title="Analityk Kredytowy - FX Forward",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
    .main-title {font-size: 2.5rem; font-weight: bold; color: #1f4788; text-align: center; padding: 1rem 0;}
    .metric-good {background: #d4edda; padding: 1rem; border-radius: 5px; border-left: 5px solid #28a745;}
    .metric-warn {background: #fff3cd; padding: 1rem; border-radius: 5px; border-left: 5px solid #ffc107;}
    .metric-bad {background: #f8d7da; padding: 1rem; border-radius: 5px; border-left: 5px solid #dc3545;}
</style>
""", unsafe_allow_html=True)


class FinancialAnalyzer:
    def __init__(self, data):
        self.data = data
        self.indicators = {}
        self.rating = None
        self.recommendation = None
    
    def calculate_indicators(self):
        d = self.data
        
        self.indicators = {
            'current_ratio': d['current_assets'] / d['short_term_liabilities'] if d['short_term_liabilities'] > 0 else 0,
            'quick_ratio': (d['current_assets'] - d['inventory']) / d['short_term_liabilities'] if d['short_term_liabilities'] > 0 else 0,
            'cash_ratio': d['cash'] / d['short_term_liabilities'] if d['short_term_liabilities'] > 0 else 0,
            'debt_to_equity': d['liabilities'] / d['equity'] if d['equity'] > 0 else 999,
            'debt_to_assets': d['liabilities'] / d['total_assets'] if d['total_assets'] > 0 else 0,
            'roe': d['net_profit'] / d['equity'] * 100 if d['equity'] > 0 else 0,
            'roa': d['net_profit'] / d['total_assets'] * 100 if d['total_assets'] > 0 else 0,
            'net_margin': d['net_profit'] / d['revenue'] * 100 if d['revenue'] > 0 else 0,
            'operating_margin': d['operating_profit'] / d['revenue'] * 100 if d['revenue'] > 0 else 0,
            'working_capital': d['current_assets'] - d['short_term_liabilities']
        }
        return self.indicators
    
    def assess_credit_risk(self):
        ind = self.indicators
        d = self.data
        score = 0
        red_flags = []
        
        # Liquidity (25 pts)
        if ind['current_ratio'] >= 1.5:
            score += 25
        elif ind['current_ratio'] >= 1.2:
            score += 15
        elif ind['current_ratio'] >= 1.0:
            score += 5
        else:
            red_flags.append("Krytycznie niski wskaźnik płynności bieżącej")
        
        # Profitability (25 pts)
        if d['net_profit'] > 0 and ind['net_margin'] > 5:
            score += 25
        elif d['net_profit'] > 0:
            score += 15
        else:
            red_flags.append("Firma generuje stratę netto")
        
        # Leverage (25 pts)
        if ind['debt_to_equity'] < 0.5:
            score += 25
        elif ind['debt_to_equity'] < 1.0:
            score += 15
        elif ind['debt_to_equity'] < 1.5:
            score += 5
        else:
            red_flags.append("Bardzo wysokie zadłużenie (D/E > 1.5)")
        
        # Cash flow (25 pts)
        if d.get('operating_cf', 0) > 0 and d['cash'] > d['revenue'] * 0.05:
            score += 25
        elif d.get('operating_cf', 0) > 0:
            score += 15
        else:
            red_flags.append("Ujemny CF operacyjny lub niska gotówka")
        
        # Rating
        if score >= 80:
            rating, risk, color = "A", "NISKIE RYZYKO", "green"
        elif score >= 65:
            rating, risk, color = "B+", "UMIARKOWANE RYZYKO", "blue"
        elif score >= 50:
            rating, risk, color = "B", "PODWYŻSZONE RYZYKO", "orange"
        elif score >= 35:
            rating, risk, color = "C+", "WYSOKIE RYZYKO", "red"
        else:
            rating, risk, color = "C-", "BARDZO WYSOKIE RYZYKO", "darkred"
        
        self.rating = {
            'score': score,
            'rating': rating,
            'risk_level': risk,
            'color': color,
            'red_flags': red_flags
        }
        return self.rating
    
    def generate_recommendation(self, requested_limit_mln):
        d = self.data
        rating = self.rating
        
        revenue_mln = d['revenue'] / 1_000_000
        equity_mln = d['equity'] / 1_000_000
        
        base_limit = revenue_mln * 0.075
        rating_mult = {'A': 1.2, 'B+': 1.0, 'B': 0.7, 'C+': 0.4, 'C-': 0.1}
        recommended_limit = min(base_limit * rating_mult.get(rating['rating'], 0.5), equity_mln * 0.20)
        
        if rating['score'] >= 65 and self.indicators['current_ratio'] >= 1.2:
            decision, color = "ZATWIERDZENIE", "success"
        elif rating['score'] >= 50:
            decision, color = "ZATWIERDZENIE WARUNKOWE", "warning"
        else:
            decision, color, recommended_limit = "ODMOWA", "danger", 0
        
        collateral = "120% cash" if rating['score'] < 50 else "100% cash/gwarancja" if rating['score'] < 65 else "10-20%"
        tenor = "12 mies" if rating['score'] >= 65 else "6 mies" if rating['score'] >= 50 else "3 mies"
        
        self.recommendation = {
            'decision': decision,
            'color': color,
            'recommended_limit_mln': round(recommended_limit, 2),
            'requested_limit_mln': requested_limit_mln,
            'collateral': collateral,
            'tenor': tenor
        }
        return self.recommendation


def main():
    st.markdown('<p class="main-title">📊 Analityk Kredytowy - Limity FX Forward</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.title("⚙️ Dane firmy")
        
        company_name = st.text_input("Nazwa firmy", "")
        nip = st.text_input("NIP", "")
        year = st.number_input("Rok sprawozdania", 2020, 2025, 2024)
        
        st.markdown("---")
        st.subheader("💰 Bilans (w PLN)")
        
        total_assets = st.number_input("Aktywa razem", 0, None, 0, 1000000, format="%d")
        current_assets = st.number_input("Aktywa obrotowe", 0, None, 0, 1000000, format="%d")
        inventory = st.number_input("Zapasy", 0, None, 0, 1000000, format="%d")
        cash = st.number_input("Środki pieniężne", 0, None, 0, 1000000, format="%d")
        
        equity = st.number_input("Kapitał własny", -100000000, None, 0, 1000000, format="%d")
        liabilities = st.number_input("Zobowiązania razem", 0, None, 0, 1000000, format="%d")
        short_term_liabilities = st.number_input("Zobowiązania krótkoterm.", 0, None, 0, 1000000, format="%d")
        
        st.markdown("---")
        st.subheader("📈 Rachunek zysków i strat")
        
        revenue = st.number_input("Przychody ze sprzedaży", 0, None, 0, 1000000, format="%d")
        operating_profit = st.number_input("Zysk operacyjny", -100000000, None, 0, 1000000, format="%d")
        net_profit = st.number_input("Zysk netto", -100000000, None, 0, 1000000, format="%d")
        
        st.markdown("---")
        st.subheader("💵 Cash Flow (opcjonalnie)")
        operating_cf = st.number_input("CF operacyjny", -100000000, None, 0, 1000000, format="%d")
        
        st.markdown("---")
        st.subheader("🎯 Limit")
        requested_limit = st.number_input("Wnioskowany limit (mln PLN)", 0.1, 100.0, 1.0, 0.1)
        
        analyze_btn = st.button("🔍 Analizuj", type="primary", use_container_width=True)
    
    # Main
    if not analyze_btn:
        st.info("👈 Wprowadź dane finansowe i kliknij 'Analizuj'")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Wspierane formaty", "Ręczne wprowadzanie")
        col2.metric("Czas analizy", "< 1 sek")
        col3.metric("Dokładność", "100%")
        col4.metric("Błędy parsowania", "0")
        
        st.markdown("---")
        st.subheader("📖 Instrukcja")
        st.markdown("""
        1. **Otwórz PDF** ze sprawozdaniem finansowym (z e-sprawozdania.biz.pl)
        2. **Przepisz dane** do formularza po lewej stronie:
           - Bilans: Aktywa, Pasywa
           - RZiS: Przychody, Zysk operacyjny, Zysk netto
           - CF: Przepływy operacyjne (opcjonalnie)
        3. **Wprowadź wnioskowany limit** w mln PLN
        4. **Kliknij "Analizuj"** i otrzymaj rekomendację
        
        💡 **Wskazówka:** Wartości wprowadzaj bez spacji i przecinków (np. 5000000 zamiast 5 000 000)
        """)
        
    else:
        if not company_name or total_assets == 0 or revenue == 0:
            st.error("❌ Wypełnij przynajmniej: Nazwę firmy, Aktywa razem i Przychody")
            return
        
        # Create analyzer
        data = {
            'company_name': company_name,
            'nip': nip,
            'year': year,
            'total_assets': total_assets,
            'current_assets': current_assets,
            'inventory': inventory,
            'cash': cash,
            'equity': equity,
            'liabilities': liabilities,
            'short_term_liabilities': short_term_liabilities,
            'revenue': revenue,
            'operating_profit': operating_profit,
            'net_profit': net_profit,
            'operating_cf': operating_cf
        }
        
        analyzer = FinancialAnalyzer(data)
        analyzer.calculate_indicators()
        analyzer.assess_credit_risk()
        analyzer.generate_recommendation(requested_limit)
        
        # Display results
        st.markdown(f"## 🏢 {company_name}")
        st.markdown(f"**NIP:** {nip} | **Rok:** {year}")
        
        # Rating banner
        colors_map = {'green': '#28a745', 'blue': '#007bff', 'orange': '#fd7e14', 'red': '#dc3545', 'darkred': '#8b0000'}
        rating_color = colors_map.get(analyzer.rating['color'], '#666')
        
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, {rating_color} 0%, #333 100%); 
                    padding: 2rem; border-radius: 15px; color: white; text-align: center; margin: 1rem 0;'>
            <h1 style='margin: 0; font-size: 3rem;'>{analyzer.rating['rating']}</h1>
            <h3 style='margin: 0.5rem 0;'>{analyzer.rating['risk_level']}</h3>
            <p style='margin: 0.5rem 0; font-size: 1.2rem;'>Wynik: {analyzer.rating['score']}/100 pkt</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Przychody", f"{revenue/1_000_000:.1f} mln")
        col2.metric("Wynik netto", f"{net_profit/1_000_000:.2f} mln", 
                   delta="Zysk" if net_profit > 0 else "Strata")
        col3.metric("Gotówka", f"{cash/1_000_000:.2f} mln")
        col4.metric("Kapitał własny", f"{equity/1_000_000:.1f} mln")
        
        # Tabs
        tab1, tab2, tab3 = st.tabs(["📊 Wskaźniki", "⚠️ Ryzyka", "💰 Rekomendacja"])
        
        with tab1:
            ind = analyzer.indicators
            df = pd.DataFrame({
                'Wskaźnik': [
                    'Płynność bieżąca', 'Płynność szybka', 'Płynność gotówkowa',
                    'Dług / Kapitał własny', 'Dług / Aktywa',
                    'ROE', 'ROA', 'Marża netto', 'Marża operacyjna'
                ],
                'Wartość': [
                    f"{ind['current_ratio']:.2f}",
                    f"{ind['quick_ratio']:.2f}",
                    f"{ind['cash_ratio']:.3f}",
                    f"{ind['debt_to_equity']:.2f}",
                    f"{ind['debt_to_assets']:.2f}",
                    f"{ind['roe']:.1f}%",
                    f"{ind['roa']:.1f}%",
                    f"{ind['net_margin']:.1f}%",
                    f"{ind['operating_margin']:.1f}%"
                ],
                'Status': [
                    '✅' if ind['current_ratio'] >= 1.5 else '⚠️' if ind['current_ratio'] >= 1.0 else '❌',
                    '✅' if ind['quick_ratio'] >= 1.0 else '⚠️' if ind['quick_ratio'] >= 0.7 else '❌',
                    '✅' if ind['cash_ratio'] >= 0.2 else '⚠️' if ind['cash_ratio'] >= 0.1 else '❌',
                    '✅' if ind['debt_to_equity'] < 1.0 else '⚠️' if ind['debt_to_equity'] < 1.5 else '❌',
                    '✅' if ind['debt_to_assets'] < 0.6 else '⚠️' if ind['debt_to_assets'] < 0.7 else '❌',
                    '✅' if ind['roe'] > 10 else '⚠️' if ind['roe'] > 0 else '❌',
                    '✅' if ind['roa'] > 5 else '⚠️' if ind['roa'] > 0 else '❌',
                    '✅' if ind['net_margin'] > 5 else '⚠️' if ind['net_margin'] > 0 else '❌',
                    '✅' if ind['operating_margin'] > 5 else '⚠️' if ind['operating_margin'] > 0 else '❌'
                ]
            })
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        with tab2:
            if analyzer.rating['red_flags']:
                for flag in analyzer.rating['red_flags']:
                    st.error(f"🔴 {flag}")
            else:
                st.success("✅ Brak krytycznych czerwonych flag")
        
        with tab3:
            rec = analyzer.recommendation
            if rec['decision'] == 'ZATWIERDZENIE':
                st.success(f"✅ **{rec['decision']}**")
            elif rec['decision'] == 'ZATWIERDZENIE WARUNKOWE':
                st.warning(f"⚠️ **{rec['decision']}**")
            else:
                st.error(f"❌ **{rec['decision']}**")
            
            col1, col2 = st.columns(2)
            col1.metric("Rekomendowany limit", f"{rec['recommended_limit_mln']:.2f} mln PLN")
            col1.metric("Wnioskowany limit", f"{rec['requested_limit_mln']:.2f} mln PLN")
            col2.info(f"**Zabezpieczenie:** {rec['collateral']}")
            col2.info(f"**Maksymalny tenor:** {rec['tenor']}")
        
        # Export
        st.markdown("---")
        if st.button("📊 Eksportuj do Excel", use_container_width=True):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Wskaźniki', index=False)
            output.seek(0)
            st.download_button(
                "💾 Pobierz Excel",
                output,
                f"Analiza_{nip}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


if __name__ == "__main__":
    main()
