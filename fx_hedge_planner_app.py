import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import datetime
import re

# Optional imports
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Page config
st.set_page_config(
    page_title="Analityk Kredytowy - Limity FX Forward",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Register fonts for PDF export
if REPORTLAB_AVAILABLE:
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    except:
        pass


class XMLParser:
    """Parser for Polish KRS/GUS XML financial statements"""
    
    @staticmethod
    def parse_xml_file(xml_content):
        """Parse XML and extract financial data - robust version"""
        try:
            # Convert to string if bytes
            if isinstance(xml_content, bytes):
                xml_str = xml_content.decode('utf-8', errors='ignore')
            else:
                xml_str = xml_content
            
            # Remove ALL namespace declarations to avoid parsing issues
            # Remove xmlns attributes
            xml_str = re.sub(r'\s+xmlns(?::\w+)?="[^"]*"', '', xml_str)
            # Remove namespace prefixes from tags
            xml_str = re.sub(r'<(\w+:)', r'<', xml_str)
            xml_str = re.sub(r'</(\w+:)', r'</', xml_str)
            
            # Parse cleaned XML
            root = ET.fromstring(xml_str)
            
            data = {}
            
            # Helper function to find value in XML tree
            def find_value(tag_names):
                """Search for tag by multiple possible names"""
                if isinstance(tag_names, str):
                    tag_names = [tag_names]
                
                for tag_name in tag_names:
                    # Search through all elements
                    for elem in root.iter():
                        # Check if tag ends with our search term (handles any prefix)
                        if elem.tag == tag_name or elem.tag.endswith(tag_name):
                            if elem.text and elem.text.strip():
                                return elem.text.strip()
                return None
            
            # Basic company info
            data['company_name'] = find_value('NazwaFirmy') or 'N/A'
            data['nip'] = find_value(['IdentyfikatorPodatkowyNIP', 'NIP']) or 'N/A'
            data['krs'] = find_value('NumerKRS') or 'N/A'
            data['period_from'] = find_value('DataOd') or 'N/A'
            data['period_to'] = find_value('DataDo') or 'N/A'
            
            # Extract year
            if data['period_to'] and data['period_to'] != 'N/A':
                match = re.search(r'(\d{4})', data['period_to'])
                data['year'] = int(match.group(1)) if match else datetime.now().year
            else:
                data['year'] = datetime.now().year
            
            # Balance Sheet - ASSETS
            data['total_assets'] = XMLParser._parse_float(find_value('AktywaRazem'))
            data['fixed_assets'] = XMLParser._parse_float(find_value('AktywaTrwale'))
            data['current_assets'] = XMLParser._parse_float(find_value('AktywaObrotowe'))
            data['inventory'] = XMLParser._parse_float(find_value('Zapasy'))
            data['receivables'] = XMLParser._parse_float(find_value('NaleznosciKrotkoterminowe'))
            
            # Cash - multiple possible names
            cash = find_value('SrodkiPieniezne')
            if not cash:
                cash = find_value('SrodkiPieniezneIInneAktywaPieniezne')
            data['cash'] = XMLParser._parse_float(cash)
            
            # Balance Sheet - LIABILITIES & EQUITY
            equity = find_value('KapitalWlasny')
            if not equity:
                equity = find_value('KapitalFunduszWlasny')
            data['equity'] = XMLParser._parse_float(equity)
            
            liabilities = find_value('ZobowiazaniaIRezerwyNaZobowiazania')
            if not liabilities:
                liabilities = find_value('ZobowiazaniaRazem')
            data['liabilities'] = XMLParser._parse_float(liabilities)
            
            data['short_term_liabilities'] = XMLParser._parse_float(find_value('ZobowiazaniaKrotkoterminowe'))
            
            # P&L Statement
            revenue = find_value('PrzychodyNettoZeSprzedazyProduktowTowarowMaterialow')
            if not revenue:
                revenue = find_value('PrzychodyNettoZeSprzedazyProduktowTowarow')
            if not revenue:
                revenue = find_value('PrzychodyNettoZeSprzedazy')
            data['revenue'] = XMLParser._parse_float(revenue)
            
            op_profit = find_value('ZyskStrataDzialalnosciOperacyjnej')
            if not op_profit:
                op_profit = find_value('ZyskStrataZeSprzedazy')
            data['operating_profit'] = XMLParser._parse_float(op_profit)
            
            data['net_profit'] = XMLParser._parse_float(find_value('ZyskStrataNetto'))
            data['ebitda'] = data['operating_profit']  # Simplified
            
            # Cash Flow Statement
            data['operating_cf'] = XMLParser._parse_float(
                find_value('PrzeplywyPieniezneNettoDzialalnosciOperacyjnej')
            )
            data['investing_cf'] = XMLParser._parse_float(
                find_value('PrzeplywyPieniezneNettoDzialalnosciInwestycyjnej')
            )
            data['financing_cf'] = XMLParser._parse_float(
                find_value('PrzeplywyPieniezneNettoDzialalnosciFinansowej')
            )
            
            # Debug info
            st.success(f"✅ Sparsowano: {data['company_name']} ({data['year']})")
            st.info(f"📊 Przychody: {data['revenue']/1_000_000:.1f} mln PLN, Aktywa: {data['total_assets']/1_000_000:.1f} mln PLN")
            
            return data
            
        except Exception as e:
            st.error(f"❌ Błąd parsowania XML: {str(e)}")
            st.error("Sprawdź czy plik jest prawidłowym sprawozdaniem finansowym w formacie XML")
            return None
    
    @staticmethod
    def _parse_float(value):
        """Parse string to float, handling Polish number format"""
        if not value or value == 'N/A':
            return 0.0
        try:
            # Clean the text
            value = str(value).strip()
            # Remove all spaces
            value = value.replace(' ', '')
            # Replace comma with dot
            value = value.replace(',', '.')
            # Keep only digits, dot, and minus
            value = re.sub(r'[^\d.-]', '', value)
            # Handle multiple dots (keep only first)
            parts = value.split('.')
            if len(parts) > 2:
                value = parts[0] + '.' + ''.join(parts[1:])
            return float(value) if value and value != '-' else 0.0
        except:
            return 0.0


class FinancialAnalyzer:
    """Multi-year financial analyzer"""
    
    def __init__(self, data_years):
        """
        data_years: list of dicts with financial data, sorted by year (newest first)
        """
        self.data_years = sorted(data_years, key=lambda x: x.get('year', 0), reverse=True)
        self.current_year = self.data_years[0] if self.data_years else {}
        self.indicators = {}
        self.trends = {}
        self.rating = None
        self.recommendation = None
    
    def calculate_indicators(self):
        """Calculate financial indicators for current year"""
        d = self.current_year
        
        # Liquidity ratios
        current_ratio = d.get('current_assets', 0) / d.get('short_term_liabilities', 1) if d.get('short_term_liabilities', 0) > 0 else 0
        quick_ratio = (d.get('current_assets', 0) - d.get('inventory', 0)) / d.get('short_term_liabilities', 1) if d.get('short_term_liabilities', 0) > 0 else 0
        cash_ratio = d.get('cash', 0) / d.get('short_term_liabilities', 1) if d.get('short_term_liabilities', 0) > 0 else 0
        
        # Leverage ratios
        debt_to_equity = d.get('liabilities', 0) / d.get('equity', 1) if d.get('equity', 0) > 0 else 0
        debt_to_assets = d.get('liabilities', 0) / d.get('total_assets', 1) if d.get('total_assets', 0) > 0 else 0
        
        # Profitability ratios
        roe = d.get('net_profit', 0) / d.get('equity', 1) * 100 if d.get('equity', 0) > 0 else 0
        roa = d.get('net_profit', 0) / d.get('total_assets', 1) * 100 if d.get('total_assets', 0) > 0 else 0
        net_margin = d.get('net_profit', 0) / d.get('revenue', 1) * 100 if d.get('revenue', 0) > 0 else 0
        operating_margin = d.get('operating_profit', 0) / d.get('revenue', 1) * 100 if d.get('revenue', 0) > 0 else 0
        
        # Working capital
        working_capital = d.get('current_assets', 0) - d.get('short_term_liabilities', 0)
        
        self.indicators = {
            'current_ratio': current_ratio,
            'quick_ratio': quick_ratio,
            'cash_ratio': cash_ratio,
            'debt_to_equity': debt_to_equity,
            'debt_to_assets': debt_to_assets,
            'roe': roe,
            'roa': roa,
            'net_margin': net_margin,
            'operating_margin': operating_margin,
            'working_capital': working_capital,
        }
        
        return self.indicators
    
    def calculate_trends(self):
        """Calculate trends if multiple years available"""
        if len(self.data_years) < 2:
            return {}
        
        current = self.data_years[0]
        previous = self.data_years[1]
        
        self.trends = {
            'revenue_growth': self._calc_growth(current.get('revenue'), previous.get('revenue')),
            'profit_growth': self._calc_growth(current.get('net_profit'), previous.get('net_profit')),
            'assets_growth': self._calc_growth(current.get('total_assets'), previous.get('total_assets')),
            'equity_growth': self._calc_growth(current.get('equity'), previous.get('equity')),
        }
        
        return self.trends
    
    def _calc_growth(self, current, previous):
        """Calculate growth rate"""
        if previous and previous != 0:
            return ((current - previous) / abs(previous)) * 100
        return 0
    
    def assess_credit_risk(self):
        """Assess credit risk with multi-year consideration"""
        ind = self.indicators
        d = self.current_year
        
        score = 0
        max_score = 100
        red_flags = []
        
        # 1. Liquidity (25 points)
        if ind['current_ratio'] >= 1.5:
            score += 25
        elif ind['current_ratio'] >= 1.2:
            score += 15
        elif ind['current_ratio'] >= 1.0:
            score += 5
        else:
            red_flags.append("Krytycznie niski wskaźnik bieżącej płynności")
        
        # 2. Profitability (25 points)
        if d.get('net_profit', 0) > 0 and ind['net_margin'] > 5:
            score += 25
        elif d.get('net_profit', 0) > 0 and ind['net_margin'] > 0:
            score += 15
        elif d.get('net_profit', 0) > 0:
            score += 10
        else:
            red_flags.append("Firma generuje stratę netto")
        
        # 3. Leverage (25 points)
        if ind['debt_to_equity'] < 0.5:
            score += 25
        elif ind['debt_to_equity'] < 1.0:
            score += 15
        elif ind['debt_to_equity'] < 1.5:
            score += 5
        else:
            red_flags.append("Bardzo wysokie zadłużenie")
        
        # 4. Cash flow (25 points)
        if d.get('operating_cf', 0) > 0 and d.get('cash', 0) > d.get('revenue', 1) * 0.05:
            score += 25
        elif d.get('operating_cf', 0) > 0:
            score += 15
        else:
            red_flags.append("Ujemny przepływ z działalności operacyjnej")
        
        # Bonus/penalty for trends (if available)
        if self.trends:
            if self.trends.get('revenue_growth', 0) < -10:
                score -= 5
                red_flags.append(f"Spadek przychodów o {abs(self.trends['revenue_growth']):.1f}%")
            elif self.trends.get('revenue_growth', 0) > 10:
                score += 5
            
            if self.trends.get('profit_growth', 0) < 0 and d.get('net_profit', 0) < 0:
                score -= 10
                red_flags.append("Pogłębiające się straty")
        
        # Determine rating
        score = max(0, min(100, score))  # Clamp between 0-100
        
        if score >= 80:
            rating = "A"
            risk_level = "NISKIE RYZYKO"
            color = "green"
        elif score >= 65:
            rating = "B+"
            risk_level = "UMIARKOWANE RYZYKO"
            color = "blue"
        elif score >= 50:
            rating = "B"
            risk_level = "PODWYŻSZONE RYZYKO"
            color = "orange"
        elif score >= 35:
            rating = "C+"
            risk_level = "WYSOKIE RYZYKO"
            color = "red"
        else:
            rating = "C-"
            risk_level = "BARDZO WYSOKIE RYZYKO"
            color = "darkred"
        
        self.rating = {
            'score': score,
            'rating': rating,
            'risk_level': risk_level,
            'color': color,
            'red_flags': red_flags
        }
        
        return self.rating
    
    def generate_recommendation(self, requested_limit_mln=1.0):
        """Generate credit limit recommendation"""
        ind = self.indicators
        d = self.current_year
        rating = self.rating
        
        # Calculate recommended limit
        revenue_mln = d.get('revenue', 0) / 1_000_000
        equity_mln = d.get('equity', 0) / 1_000_000
        
        # Base limit: 5-10% of annual revenue
        base_limit = revenue_mln * 0.075
        
        # Adjust by rating
        rating_multiplier = {
            'A': 1.2,
            'B+': 1.0,
            'B': 0.7,
            'C+': 0.4,
            'C-': 0.1
        }
        
        adjusted_limit = base_limit * rating_multiplier.get(rating['rating'], 0.5)
        
        # Cap at 20% of equity
        equity_cap = equity_mln * 0.20
        recommended_limit = min(adjusted_limit, equity_cap)
        
        # Decision
        if rating['score'] >= 65 and ind['current_ratio'] >= 1.2:
            decision = "ZATWIERDZENIE"
            decision_color = "success"
        elif rating['score'] >= 50 and ind['current_ratio'] >= 1.0:
            decision = "ZATWIERDZENIE WARUNKOWE"
            decision_color = "warning"
        else:
            decision = "ODMOWA"
            decision_color = "danger"
            recommended_limit = 0
        
        # Collateral
        if rating['score'] < 50:
            collateral = "120% zabezpieczenia gotówkowego"
        elif rating['score'] < 65:
            collateral = "100% zabezpieczenia gotówkowego lub gwarancja bankowa"
        else:
            collateral = "Standardowe zabezpieczenie 10-20%"
        
        # Tenor
        if rating['score'] >= 65:
            max_tenor = "12 miesięcy"
        elif rating['score'] >= 50:
            max_tenor = "6 miesięcy"
        else:
            max_tenor = "3 miesiące"
        
        self.recommendation = {
            'decision': decision,
            'decision_color': decision_color,
            'recommended_limit_mln': round(recommended_limit, 2),
            'requested_limit_mln': requested_limit_mln,
            'approval_ratio': round((recommended_limit / requested_limit_mln * 100) if requested_limit_mln > 0 else 0, 1),
            'collateral': collateral,
            'max_tenor': max_tenor,
            'conditions': self._generate_conditions()
        }
        
        return self.recommendation
    
    def _generate_conditions(self):
        """Generate specific conditions"""
        conditions = []
        ind = self.indicators
        d = self.current_year
        
        if ind['current_ratio'] < 1.5:
            conditions.append("Monitoring płynności co miesiąc")
        
        if d.get('net_profit', 0) < 0:
            conditions.append("Zakaz wypłat dywidend do osiągnięcia zyskowności")
        
        if ind['debt_to_equity'] > 1.0:
            conditions.append("Covenant: D/E ratio nie może przekroczyć 1.5")
        
        if d.get('cash', 0) < d.get('revenue', 0) * 0.03:
            conditions.append("Utrzymanie minimalnego salda gotówkowego")
        
        if self.trends and self.trends.get('revenue_growth', 0) < -5:
            conditions.append("Monitoring przychodów - raportowanie kwartalne")
        
        return conditions


def main():
    # Header
    st.markdown("# 📊 Analityk Kredytowy - Limity FX Forward")
    st.markdown("### Analiza wieloletnia sprawozdań finansowych")
    
    # Sidebar
    with st.sidebar:
        st.title("⚙️ Ustawienia")
        
        st.markdown("---")
        st.subheader("📤 Wczytaj sprawozdania XML")
        
        st.info("**Wgraj do 5 plików XML** (kolejne lata)\nNajnowszy rok powinien być pierwszy")
        
        uploaded_files = st.file_uploader(
            "Wybierz pliki XML",
            type=['xml'],
            accept_multiple_files=True,
            help="Możesz wgrać 1-5 plików XML z różnych lat"
        )
        
        st.markdown("---")
        st.subheader("💰 Parametry limitu")
        
        requested_limit = st.number_input(
            "Wnioskowany limit (mln PLN)",
            min_value=0.1,
            max_value=100.0,
            value=1.0,
            step=0.1
        )
        
        analyze_button = st.button("🔍 Analizuj sprawozdania", type="primary", use_container_width=True)
    
    # Main content
    if not uploaded_files:
        st.info("👈 Wczytaj pliki XML aby rozpocząć analizę")
        
        # Info cards
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Wspierane formaty", "XML (KRS/GUS)")
        with col2:
            st.metric("Maksymalna liczba lat", "5")
        with col3:
            st.metric("Czas analizy", "< 30 sek")
        
        st.markdown("---")
        
        # Instructions
        st.subheader("📖 Instrukcja")
        st.markdown("""
        1. **Pobierz sprawozdania XML** z systemu KRS/GUS
        2. **Wczytaj pliki** (1-5 lat, najnowszy jako pierwszy)
        3. **Wprowadź wnioskowany limit** w mln PLN
        4. **Kliknij "Analizuj"** i poczekaj na wyniki
        5. **Przejrzyj analizę** w zakładkach poniżej
        """)
        
    elif analyze_button and uploaded_files:
        with st.spinner("Przetwarzam sprawozdania..."):
            # Parse all XML files
            all_data = []
            for uploaded_file in uploaded_files:
                xml_content = uploaded_file.read()
                data = XMLParser.parse_xml_file(xml_content)
                if data:
                    all_data.append(data)
            
            if not all_data:
                st.error("❌ Nie udało się sparsować żadnego pliku XML")
                return
            
            # Sort by year
            all_data = sorted(all_data, key=lambda x: x.get('year', 0), reverse=True)
            
            # Create analyzer
            analyzer = FinancialAnalyzer(all_data)
            analyzer.calculate_indicators()
            analyzer.calculate_trends()
            analyzer.assess_credit_risk()
            analyzer.generate_recommendation(requested_limit)
            
            st.session_state['analyzer'] = analyzer
            st.success(f"✅ Przeanalizowano {len(all_data)} rok(ów/i) sprawozdań!")
    
    # Display results
    if 'analyzer' in st.session_state:
        analyzer = st.session_state['analyzer']
        d = analyzer.current_year
        
        # Company info
        st.markdown(f"## 🏢 {d.get('company_name', 'N/A')}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**NIP:** {d.get('nip', 'N/A')}")
        with col2:
            st.markdown(f"**KRS:** {d.get('krs', 'N/A')}")
        with col3:
            st.markdown(f"**Okres:** {d.get('period_from', 'N/A')} - {d.get('period_to', 'N/A')}")
        
        st.markdown("---")
        
        # Rating banner
        rating_colors = {
            'green': '#28a745',
            'blue': '#007bff',
            'orange': '#fd7e14',
            'red': '#dc3545',
            'darkred': '#8b0000'
        }
        
        rating_color = rating_colors.get(analyzer.rating['color'], '#666')
        
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, {rating_color} 0%, #333 100%); 
                    padding: 2rem; border-radius: 15px; color: white; text-align: center; margin: 1rem 0;
                    box-shadow: 0 8px 16px rgba(0,0,0,0.2);'>
            <h1 style='margin: 0; font-size: 3rem;'>{analyzer.rating['rating']}</h1>
            <h3 style='margin: 0.5rem 0 0 0;'>{analyzer.rating['risk_level']}</h3>
            <p style='margin: 0.5rem 0 0 0; font-size: 1.2rem;'>Wynik: {analyzer.rating['score']}/100 punktów</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        revenue_mln = d.get('revenue', 0) / 1_000_000
        with col1:
            delta_rev = f"{analyzer.trends.get('revenue_growth', 0):+.1f}%" if analyzer.trends else None
            st.metric("Przychody", f"{revenue_mln:.1f} mln", delta=delta_rev)
        
        net_profit_mln = d.get('net_profit', 0) / 1_000_000
        with col2:
            delta_profit = f"{analyzer.trends.get('profit_growth', 0):+.1f}%" if analyzer.trends else None
            st.metric("Wynik netto", f"{net_profit_mln:.2f} mln", delta=delta_profit)
        
        cash_mln = d.get('cash', 0) / 1_000_000
        with col3:
            st.metric("Gotówka", f"{cash_mln:.2f} mln")
        
        equity_mln = d.get('equity', 0) / 1_000_000
        with col4:
            delta_equity = f"{analyzer.trends.get('equity_growth', 0):+.1f}%" if analyzer.trends else None
            st.metric("Kapitał własny", f"{equity_mln:.1f} mln", delta=delta_equity)
        
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Wskaźniki", "📈 Trendy", "⚠️ Ryzyka", "💰 Rekomendacja"])
        
        with tab1:
            st.subheader("Wskaźniki finansowe")
            
            # Create indicators dataframe
            ind_data = {
                'Wskaźnik': [
                    'Bieżąca płynność', 'Szybka płynność', 'Gotówkowa płynność',
                    'Dług / Kapitał własny', 'Dług / Aktywa',
                    'ROE', 'ROA', 'Marża netto', 'Marża operacyjna'
                ],
                'Wartość': [
                    f"{analyzer.indicators['current_ratio']:.2f}",
                    f"{analyzer.indicators['quick_ratio']:.2f}",
                    f"{analyzer.indicators['cash_ratio']:.2f}",
                    f"{analyzer.indicators['debt_to_equity']:.2f}",
                    f"{analyzer.indicators['debt_to_assets']:.2f}",
                    f"{analyzer.indicators['roe']:.1f}%",
                    f"{analyzer.indicators['roa']:.1f}%",
                    f"{analyzer.indicators['net_margin']:.1f}%",
                    f"{analyzer.indicators['operating_margin']:.1f}%"
                ],
                'Status': [
                    '✅' if analyzer.indicators['current_ratio'] >= 1.5 else '⚠️' if analyzer.indicators['current_ratio'] >= 1.0 else '❌',
                    '✅' if analyzer.indicators['quick_ratio'] >= 1.0 else '⚠️' if analyzer.indicators['quick_ratio'] >= 0.7 else '❌',
                    '✅' if analyzer.indicators['cash_ratio'] >= 0.2 else '⚠️' if analyzer.indicators['cash_ratio'] >= 0.1 else '❌',
                    '✅' if analyzer.indicators['debt_to_equity'] < 1.0 else '⚠️' if analyzer.indicators['debt_to_equity'] < 1.5 else '❌',
                    '✅' if analyzer.indicators['debt_to_assets'] < 0.6 else '⚠️' if analyzer.indicators['debt_to_assets'] < 0.7 else '❌',
                    '✅' if analyzer.indicators['roe'] > 10 else '⚠️' if analyzer.indicators['roe'] > 0 else '❌',
                    '✅' if analyzer.indicators['roa'] > 5 else '⚠️' if analyzer.indicators['roa'] > 0 else '❌',
                    '✅' if analyzer.indicators['net_margin'] > 5 else '⚠️' if analyzer.indicators['net_margin'] > 0 else '❌',
                    '✅' if analyzer.indicators['operating_margin'] > 5 else '⚠️' if analyzer.indicators['operating_margin'] > 0 else '❌'
                ]
            }
            
            df_indicators = pd.DataFrame(ind_data)
            st.dataframe(df_indicators, use_container_width=True, hide_index=True)
        
        with tab2:
            st.subheader("Analiza trendów")
            
            if len(analyzer.data_years) > 1:
                # Multi-year comparison
                years_data = []
                for year_data in analyzer.data_years:
                    years_data.append({
                        'Rok': year_data.get('year', 'N/A'),
                        'Przychody (mln)': f"{year_data.get('revenue', 0)/1_000_000:.1f}",
                        'Zysk netto (mln)': f"{year_data.get('net_profit', 0)/1_000_000:.2f}",
                        'Aktywa (mln)': f"{year_data.get('total_assets', 0)/1_000_000:.1f}",
                        'Kapitał własny (mln)': f"{year_data.get('equity', 0)/1_000_000:.1f}"
                    })
                
                df_years = pd.DataFrame(years_data)
                st.dataframe(df_years, use_container_width=True, hide_index=True)
                
                st.markdown("### Dynamika zmian (r/r)")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Przychody", f"{analyzer.trends.get('revenue_growth', 0):+.1f}%")
                    st.metric("Aktywa", f"{analyzer.trends.get('assets_growth', 0):+.1f}%")
                with col2:
                    st.metric("Zysk netto", f"{analyzer.trends.get('profit_growth', 0):+.1f}%")
                    st.metric("Kapitał własny", f"{analyzer.trends.get('equity_growth', 0):+.1f}%")
            else:
                st.info("Wczytaj więcej lat aby zobaczyć trendy")
        
        with tab3:
            st.subheader("Czerwone flagi i ryzyka")
            
            if analyzer.rating['red_flags']:
                for flag in analyzer.rating['red_flags']:
                    st.error(f"🔴 {flag}")
            else:
                st.success("✅ Brak krytycznych czerwonych flag")
        
        with tab4:
            st.subheader("Rekomendacja limitu FX Forward")
            
            # Decision box
            if analyzer.recommendation['decision'] == 'ZATWIERDZENIE':
                st.success(f"✅ **{analyzer.recommendation['decision']}**")
            elif analyzer.recommendation['decision'] == 'ZATWIERDZENIE WARUNKOWE':
                st.warning(f"⚠️ **{analyzer.recommendation['decision']}**")
            else:
                st.error(f"❌ **{analyzer.recommendation['decision']}**")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Rekomendowany limit", f"{analyzer.recommendation['recommended_limit_mln']:.2f} mln PLN")
                st.metric("Wnioskowany limit", f"{analyzer.recommendation['requested_limit_mln']:.2f} mln PLN")
            with col2:
                st.info(f"**Zabezpieczenie:** {analyzer.recommendation['collateral']}")
                st.info(f"**Maksymalny tenor:** {analyzer.recommendation['max_tenor']}")
            
            if analyzer.recommendation['conditions']:
                st.markdown("### Warunki (Covenants)")
                for i, cond in enumerate(analyzer.recommendation['conditions'], 1):
                    st.markdown(f"{i}. {cond}")
        
        st.markdown("---")
        
        # Export options
        st.subheader("📥 Eksport")
        if not REPORTLAB_AVAILABLE:
            st.warning("⚠️ Zainstaluj pakiet `reportlab` aby włączyć eksport PDF: `pip install reportlab`")
        
        # Export to Excel
        if st.button("📊 Eksportuj do Excel", use_container_width=True):
            # Create Excel file
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Indicators sheet
                df_indicators.to_excel(writer, sheet_name='Wskaźniki', index=False)
                
                # Years comparison if available
                if len(analyzer.data_years) > 1:
                    df_years.to_excel(writer, sheet_name='Trendy', index=False)
            
            output.seek(0)
            st.download_button(
                label="💾 Pobierz Excel",
                data=output,
                file_name=f"Analiza_{d.get('nip', 'N-A')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


if __name__ == "__main__":
    main()
