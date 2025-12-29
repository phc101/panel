import streamlit as st
import pandas as pd
import pdfplumber
from io import BytesIO
from datetime import datetime
import re

# Optional reportlab
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
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

st.set_page_config(page_title="Analityk Kredytowy - FX Forward", page_icon="📊", layout="wide")


class PDFParser:
    """Parser dla PDF z e-sprawozdania.biz.pl - wersja z tabelami"""
    
    @staticmethod
    def parse_pdf(pdf_file):
        """Parse PDF financial statement using table extraction"""
        try:
            data = {}
            
            with pdfplumber.open(pdf_file) as pdf:
                # Extract all text for basic info
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
                
                # Extract tables from all pages
                all_tables = []
                for page in pdf.pages:
                    tables = page.extract_tables()
                    if tables:
                        all_tables.extend(tables)
            
            st.write("🔍 **Debug - Parser działa...**")
            
            # Basic info from text
            data['company_name'] = PDFParser._extract_value(full_text, r'NazwaFirmy:\s*(.+?)(?:\n|Siedziba)')
            data['nip'] = PDFParser._extract_value(full_text, r'Identyfikator podatkowy NIP:\s*(\d+)')
            data['krs'] = PDFParser._extract_value(full_text, r'Numer KRS[^:]*:\s*(\d+)')
            data['period_from'] = PDFParser._extract_value(full_text, r'DataOd:\s*([\d-]+)')
            data['period_to'] = PDFParser._extract_value(full_text, r'DataDo:\s*([\d-]+)')
            
            if data['period_to']:
                match = re.search(r'(\d{4})', data['period_to'])
                data['year'] = int(match.group(1)) if match else 2024
            else:
                data['year'] = 2024
            
            st.write(f"✅ Firma: **{data['company_name']}**")
            st.write(f"✅ NIP: {data['nip']} | KRS: {data['krs']}")
            
            # Now extract from tables
            bilans_data = PDFParser._find_in_tables(all_tables, 'Bilans')
            
            # Extract key values
            data['total_assets'] = PDFParser._get_table_value(bilans_data, 'Aktywa razem')
            data['current_assets'] = PDFParser._get_table_value(bilans_data, 'B. Aktywa obrotowe')
            data['fixed_assets'] = PDFParser._get_table_value(bilans_data, 'A. Aktywa trwałe')
            data['inventory'] = PDFParser._get_table_value(bilans_data, 'I. Zapasy')
            data['cash'] = PDFParser._get_table_value(bilans_data, 'środki pieniężne w kasie i na rachunkach')
            if data['cash'] == 0:
                data['cash'] = PDFParser._get_table_value(bilans_data, 'Środki pieniężne i inne aktywa pieniężne')
            
            data['receivables'] = PDFParser._get_table_value(bilans_data, 'II. Należności krótkoterminowe')
            data['equity'] = PDFParser._get_table_value(bilans_data, 'A. Kapitał (fundusz) własny')
            data['liabilities'] = PDFParser._get_table_value(bilans_data, 'B. Zobowiązania i rezerwy na zobowiązania')
            data['short_term_liabilities'] = PDFParser._get_table_value(bilans_data, 'III. Zobowiązania krótkoterminowe')
            
            # P&L
            rzis_data = PDFParser._find_in_tables(all_tables, 'Rachunek zysków')
            data['revenue'] = PDFParser._get_table_value(rzis_data, 'A. Przychody netto ze sprzedaży')
            data['operating_profit'] = PDFParser._get_table_value(rzis_data, 'F. Zysk (strata) z działalności operacyjnej')
            
            net_profit_raw = PDFParser._get_table_value(rzis_data, 'L. Zysk (strata) netto', allow_negative=True)
            data['net_profit'] = net_profit_raw
            
            # Cash flow
            cf_data = PDFParser._find_in_tables(all_tables, 'Rachunek przepływów')
            data['operating_cf'] = PDFParser._get_table_value(cf_data, 'III. Przepływy pieniężne netto z działalności operacyjnej', allow_negative=True)
            data['investing_cf'] = PDFParser._get_table_value(cf_data, 'III. Przepływy pieniężne netto z działalności inwestycyjnej', allow_negative=True)
            data['financing_cf'] = PDFParser._get_table_value(cf_data, 'III. Przepływy pieniężne netto z działalności finansowej', allow_negative=True)
            
            data['ebitda'] = data.get('operating_profit', 0)
            
            # Show results
            st.write("---")
            st.write("📊 **Wyciągnięte dane:**")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Aktywa razem", f"{data['total_assets']:,.0f} PLN")
                st.metric("Kapitał własny", f"{data['equity']:,.0f} PLN")
                st.metric("Zobowiązania", f"{data['liabilities']:,.0f} PLN")
            with col2:
                st.metric("Przychody", f"{data['revenue']:,.0f} PLN")
                st.metric("Zysk netto", f"{data['net_profit']:,.0f} PLN")
                st.metric("Gotówka", f"{data['cash']:,.0f} PLN")
            
            return data
            
        except Exception as e:
            st.error(f"❌ Błąd parsowania PDF: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return None
    
    @staticmethod
    def _find_in_tables(tables, keyword):
        """Find table section containing keyword"""
        result = []
        for table in tables:
            table_text = ' '.join([' '.join([str(cell) if cell else '' for cell in row]) for row in table])
            if keyword.lower() in table_text.lower():
                result.extend(table)
        return result
    
    @staticmethod
    def _get_table_value(table_data, label, allow_negative=False):
        """Extract numeric value from table row matching label"""
        if not table_data:
            return 0.0
        
        for row in table_data:
            if not row:
                continue
            
            # Check if label is in first column
            first_cell = str(row[0]) if row[0] else ''
            if label.lower() in first_cell.lower():
                # Get the second column (current year value)
                if len(row) >= 2 and row[1]:
                    value = PDFParser._parse_amount(str(row[1]))
                    # Check if negative (strata)
                    if allow_negative and 'strata' in first_cell.lower():
                        return -abs(value)
                    return value
        
        return 0.0
    
    @staticmethod
    def _extract_value(text, pattern):
        """Extract text value using regex"""
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return "N/A"
    
    @staticmethod
    def _parse_amount(amount_str):
        """Parse amount string to float"""
        if not amount_str or amount_str == 'None':
            return 0.0
        try:
            # Clean: "18 506 056,70" -> 18506056.70
            amount_str = str(amount_str).strip()
            # Remove all spaces
            amount_str = amount_str.replace(' ', '')
            # Replace comma with dot
            amount_str = amount_str.replace(',', '.')
            # Keep only digits, dot, and minus
            amount_str = re.sub(r'[^\d.-]', '', amount_str)
            return float(amount_str) if amount_str and amount_str != '-' else 0.0
        except:
            return 0.0


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
        
        conditions = []
        if self.indicators['current_ratio'] < 1.5:
            conditions.append("Monitoring płynności co miesiąc")
        if d['net_profit'] < 0:
            conditions.append("Zakaz wypłat dywidend do osiągnięcia zyskowności")
        if self.indicators['debt_to_equity'] > 1.0:
            conditions.append("Covenant: D/E nie może przekroczyć 1.5")
        
        self.recommendation = {
            'decision': decision,
            'color': color,
            'recommended_limit_mln': round(recommended_limit, 2),
            'requested_limit_mln': requested_limit_mln,
            'collateral': collateral,
            'tenor': tenor,
            'conditions': conditions
        }
        return self.recommendation


def main():
    st.markdown("# 📊 Analityk Kredytowy - Limity FX Forward")
    st.markdown("### Automatyczna analiza PDF z e-sprawozdania.biz.pl")
    
    with st.sidebar:
        st.title("⚙️ Ustawienia")
        
        st.markdown("---")
        st.subheader("📤 Wczytaj PDF")
        st.info("**Format:** PDF z e-sprawozdania.biz.pl\n(wygenerowany z XML)")
        
        uploaded_files = st.file_uploader(
            "Wybierz pliki PDF",
            type=['pdf'],
            accept_multiple_files=True,
            help="Możesz wgrać 1-5 plików z różnych lat"
        )
        
        st.markdown("---")
        st.subheader("💰 Parametry")
        requested_limit = st.number_input("Wnioskowany limit (mln PLN)", 0.1, 100.0, 1.0, 0.1)
        
        analyze_btn = st.button("🔍 Analizuj PDF", type="primary", use_container_width=True)
    
    if not uploaded_files:
        st.info("👈 Wczytaj PDF aby rozpocząć analizę")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Format", "PDF z e-sprawozdania.biz.pl")
        col2.metric("Maksymalna liczba plików", "5")
        col3.metric("Czas analizy", "< 10 sek")
        
        st.markdown("---")
        st.subheader("📖 Instrukcja")
        st.markdown("""
        1. Wejdź na **e-sprawozdania.biz.pl**
        2. Wczytaj XML ze sprawozdaniem finansowym
        3. **Wydrukuj jako PDF** (Ctrl+P → Zapisz jako PDF)
        4. Wczytaj ten PDF tutaj
        5. Kliknij "Analizuj PDF"
        """)
        
    elif analyze_btn and uploaded_files:
        with st.spinner("Przetwarzam PDF..."):
            all_data = []
            for uploaded_file in uploaded_files:
                data = PDFParser.parse_pdf(uploaded_file)
                if data:
                    all_data.append(data)
                    st.success(f"✅ {data.get('company_name', 'N/A')} ({data.get('year', 'N/A')})")
            
            if not all_data:
                st.error("❌ Nie udało się sparsować żadnego PDF")
                return
            
            # Use most recent
            all_data = sorted(all_data, key=lambda x: x.get('year', 0), reverse=True)
            current_data = all_data[0]
            
            # Analyze
            analyzer = FinancialAnalyzer(current_data)
            analyzer.calculate_indicators()
            analyzer.assess_credit_risk()
            analyzer.generate_recommendation(requested_limit)
            
            st.session_state['analyzer'] = analyzer
            st.session_state['all_data'] = all_data
    
    if 'analyzer' in st.session_state:
        analyzer = st.session_state['analyzer']
        d = analyzer.data
        
        st.markdown(f"## 🏢 {d.get('company_name', 'N/A')}")
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**NIP:** {d.get('nip', 'N/A')}")
        col2.markdown(f"**KRS:** {d.get('krs', 'N/A')}")
        col3.markdown(f"**Okres:** {d.get('period_from', 'N/A')} - {d.get('period_to', 'N/A')}")
        
        # Rating
        colors_map = {'green': '#28a745', 'blue': '#007bff', 'orange': '#fd7e14', 'red': '#dc3545', 'darkred': '#8b0000'}
        rating_color = colors_map.get(analyzer.rating['color'], '#666')
        
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, {rating_color} 0%, #333 100%); 
                    padding: 2rem; border-radius: 15px; color: white; text-align: center; margin: 1rem 0;'>
            <h1 style='margin: 0; font-size: 3rem;'>{analyzer.rating['rating']}</h1>
            <h3 style='margin: 0.5rem 0;'>{analyzer.rating['risk_level']}</h3>
            <p style='margin: 0.5rem 0; font-size: 1.2rem;'>Wynik: {analyzer.rating['score']}/100</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Przychody", f"{d['revenue']/1_000_000:.1f} mln")
        col2.metric("Wynik netto", f"{d['net_profit']/1_000_000:.2f} mln")
        col3.metric("Gotówka", f"{d['cash']/1_000_000:.2f} mln")
        col4.metric("Kapitał własny", f"{d['equity']/1_000_000:.1f} mln")
        
        # Tabs
        tab1, tab2, tab3 = st.tabs(["📊 Wskaźniki", "⚠️ Ryzyka", "💰 Rekomendacja"])
        
        with tab1:
            ind = analyzer.indicators
            df = pd.DataFrame({
                'Wskaźnik': [
                    'Płynność bieżąca', 'Płynność szybka', 'Płynność gotówkowa',
                    'Dług / Kapitał', 'Dług / Aktywa',
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
                    '✅' if ind['debt_to_assets'] < 0.6 else '⚠️',
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
                st.success("✅ Brak krytycznych flag")
        
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
            col2.info(f"**Tenor:** {rec['tenor']}")
            
            if rec['conditions']:
                st.markdown("### Warunki:")
                for i, cond in enumerate(rec['conditions'], 1):
                    st.markdown(f"{i}. {cond}")
        
        st.markdown("---")
        if st.button("📊 Eksportuj do Excel", use_container_width=True):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Wskaźniki', index=False)
            output.seek(0)
            st.download_button(
                "💾 Pobierz Excel",
                output,
                f"Analiza_{d.get('nip', 'NA')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


if __name__ == "__main__":
    main()
