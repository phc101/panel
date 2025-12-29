import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import datetime

# Optional imports - app will work without them
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    
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
try:
    pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
except:
    pass

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f4788;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card-red {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card-green {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .danger-box {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)


class FinancialAnalyzer:
    """Klasa do analizy sprawozdań finansowych"""
    
    def __init__(self):
        self.data = {}
        self.indicators = {}
        self.rating = None
        self.recommendation = None
        
    def parse_xml(self, xml_content):
        """Parse XML financial statement"""
        try:
            root = ET.fromstring(xml_content)
            
            # Extracting data from XML - simplified version
            # You would need to adjust namespaces and paths based on actual XML structure
            self.data = {
                'company_name': self._get_xml_value(root, './/NazwaFirmy'),
                'nip': self._get_xml_value(root, './/IdentyfikatorPodatkowyNIP'),
                'krs': self._get_xml_value(root, './/NumerKRS'),
                'period_from': self._get_xml_value(root, './/DataOd'),
                'period_to': self._get_xml_value(root, './/DataDo'),
            }
            
            # Balance sheet data
            balance = self._extract_balance_sheet(root)
            pnl = self._extract_pnl(root)
            cashflow = self._extract_cashflow(root)
            
            self.data.update(balance)
            self.data.update(pnl)
            self.data.update(cashflow)
            
            return True
        except Exception as e:
            st.error(f"Błąd parsowania XML: {str(e)}")
            return False
    
    def _get_xml_value(self, root, path):
        """Helper to extract XML value"""
        elem = root.find(path)
        return elem.text if elem is not None else "N/A"
    
    def _extract_balance_sheet(self, root):
        """Extract balance sheet data"""
        return {
            'total_assets': self._parse_float(self._get_xml_value(root, './/AktywaRazem')),
            'fixed_assets': self._parse_float(self._get_xml_value(root, './/AktywaTrwale')),
            'current_assets': self._parse_float(self._get_xml_value(root, './/AktywaObrotowe')),
            'inventory': self._parse_float(self._get_xml_value(root, './/Zapasy')),
            'receivables': self._parse_float(self._get_xml_value(root, './/NaleznosciKrotkoterminowe')),
            'cash': self._parse_float(self._get_xml_value(root, './/SrodkiPieniezne')),
            'equity': self._parse_float(self._get_xml_value(root, './/KapitalWlasny')),
            'liabilities': self._parse_float(self._get_xml_value(root, './/ZobowiazaniaRazem')),
            'short_term_liabilities': self._parse_float(self._get_xml_value(root, './/ZobowiazaniaKrotkoterminowe')),
        }
    
    def _extract_pnl(self, root):
        """Extract P&L data"""
        return {
            'revenue': self._parse_float(self._get_xml_value(root, './/PrzychodyNetto')),
            'operating_profit': self._parse_float(self._get_xml_value(root, './/ZyskStrataDzialalnosciOperacyjnej')),
            'net_profit': self._parse_float(self._get_xml_value(root, './/ZyskStrataNetto')),
            'ebitda': self._parse_float(self._get_xml_value(root, './/EBITDA')),
        }
    
    def _extract_cashflow(self, root):
        """Extract cash flow data"""
        return {
            'operating_cf': self._parse_float(self._get_xml_value(root, './/PrzeplywyOperacyjne')),
            'investing_cf': self._parse_float(self._get_xml_value(root, './/PrzeplywyInwestycyjne')),
            'financing_cf': self._parse_float(self._get_xml_value(root, './/PrzeplywyFinansowe')),
        }
    
    def _parse_float(self, value):
        """Parse string to float"""
        try:
            return float(str(value).replace(',', '.').replace(' ', ''))
        except:
            return 0.0
    
    def calculate_indicators(self):
        """Calculate financial indicators"""
        d = self.data
        
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
    
    def assess_credit_risk(self):
        """Assess credit risk and provide rating"""
        ind = self.indicators
        d = self.data
        
        score = 0
        max_score = 100
        red_flags = []
        
        # 1. Liquidity assessment (25 points)
        if ind['current_ratio'] >= 1.5:
            score += 25
        elif ind['current_ratio'] >= 1.2:
            score += 15
        elif ind['current_ratio'] >= 1.0:
            score += 5
        else:
            red_flags.append("Krytycznie niski wskaźnik bieżącej płynności")
        
        # 2. Profitability assessment (25 points)
        if d.get('net_profit', 0) > 0 and ind['net_margin'] > 5:
            score += 25
        elif d.get('net_profit', 0) > 0 and ind['net_margin'] > 0:
            score += 15
        elif d.get('net_profit', 0) > 0:
            score += 10
        else:
            red_flags.append("Firma generuje stratę netto")
        
        # 3. Leverage assessment (25 points)
        if ind['debt_to_equity'] < 0.5:
            score += 25
        elif ind['debt_to_equity'] < 1.0:
            score += 15
        elif ind['debt_to_equity'] < 1.5:
            score += 5
        else:
            red_flags.append("Bardzo wysokie zadłużenie")
        
        # 4. Cash flow assessment (25 points)
        if d.get('operating_cf', 0) > 0 and d.get('cash', 0) > d.get('revenue', 1) * 0.05:
            score += 25
        elif d.get('operating_cf', 0) > 0:
            score += 15
        else:
            red_flags.append("Ujemny przepływ z działalności operacyjnej")
        
        # Determine rating
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
        """Generate credit limit recommendation for FX forwards"""
        ind = self.indicators
        d = self.data
        rating = self.rating
        
        # Calculate recommended limit based on multiple factors
        revenue_mln = d.get('revenue', 0) / 1_000_000
        equity_mln = d.get('equity', 0) / 1_000_000
        cash_mln = d.get('cash', 0) / 1_000_000
        
        # Base limit: 5-10% of annual revenue for FX forwards
        base_limit = revenue_mln * 0.075  # 7.5% of revenue
        
        # Adjust by credit rating
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
        
        # Determine if approval recommended
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
        
        # Collateral requirements
        if rating['score'] < 50:
            collateral = "120% zabezpieczenia gotówkowego"
        elif rating['score'] < 65:
            collateral = "100% zabezpieczenia gotówkowego lub gwarancja bankowa"
        else:
            collateral = "Standardowe zabezpieczenie 10-20%"
        
        # Tenor recommendation
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
        """Generate specific conditions based on risk profile"""
        conditions = []
        ind = self.indicators
        d = self.data
        
        if ind['current_ratio'] < 1.5:
            conditions.append("Monitoring płynności co miesiąc")
        
        if d.get('net_profit', 0) < 0:
            conditions.append("Zakaz wypłat dywidend do osiągnięcia zyskowności")
        
        if ind['debt_to_equity'] > 1.0:
            conditions.append("Covenant: D/E ratio nie może przekroczyć 1.5")
        
        if d.get('cash', 0) < d.get('revenue', 0) * 0.03:
            conditions.append("Utrzymanie minimalnego salda gotówkowego")
        
        return conditions


def generate_pdf_report(analyzer, output_buffer):
    """Generate comprehensive PDF report"""
    doc = SimpleDocTemplate(output_buffer, pagesize=A4, 
                           topMargin=2*cm, bottomMargin=2*cm,
                           leftMargin=2*cm, rightMargin=2*cm)
    
    story = []
    
    # Styles
    title_style = ParagraphStyle(
        'CustomTitle',
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='DejaVuSans-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='DejaVuSans-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        fontSize=9,
        leading=12,
        alignment=TA_JUSTIFY,
        fontName='DejaVuSans'
    )
    
    # Title
    story.append(Paragraph("ANALIZA KREDYTOWA - LIMIT FX FORWARD", title_style))
    story.append(Paragraph(analyzer.data.get('company_name', 'N/A'), title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Company info
    info_data = [
        ['Data analizy:', datetime.now().strftime('%d.%m.%Y')],
        ['NIP:', analyzer.data.get('nip', 'N/A')],
        ['KRS:', analyzer.data.get('krs', 'N/A')],
        ['Okres sprawozdawczy:', f"{analyzer.data.get('period_from', 'N/A')} - {analyzer.data.get('period_to', 'N/A')}"],
    ]
    info_table = Table(info_data, colWidths=[5*cm, 9*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
        ('FONTNAME', (0, 0), (0, -1), 'DejaVuSans-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'DejaVuSans'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.8*cm))
    
    # Rating box
    rating_color = colors.HexColor('#28a745') if analyzer.rating['color'] == 'green' else \
                   colors.HexColor('#ffc107') if analyzer.rating['color'] in ['blue', 'orange'] else \
                   colors.HexColor('#dc3545')
    
    rating_data = [
        ['RATING KREDYTOWY', f"{analyzer.rating['rating']} - {analyzer.rating['risk_level']}"],
        ['WYNIK PUNKTOWY', f"{analyzer.rating['score']}/100"],
    ]
    rating_table = Table(rating_data, colWidths=[7*cm, 7*cm])
    rating_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), rating_color),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(rating_table)
    story.append(Spacer(1, 0.8*cm))
    
    # Key indicators
    story.append(Paragraph("KLUCZOWE WSKAŹNIKI FINANSOWE", heading_style))
    
    ind_data = [
        ['Wskaźnik', 'Wartość', 'Ocena'],
        ['Wskaźnik bieżącej płynności', f"{analyzer.indicators['current_ratio']:.2f}", 
         'DOBRA' if analyzer.indicators['current_ratio'] >= 1.5 else 'SŁ' if analyzer.indicators['current_ratio'] >= 1.0 else 'ZŁA'],
        ['Wskaźnik szybkiej płynności', f"{analyzer.indicators['quick_ratio']:.2f}",
         'DOBRA' if analyzer.indicators['quick_ratio'] >= 1.0 else 'SŁ' if analyzer.indicators['quick_ratio'] >= 0.7 else 'ZŁA'],
        ['Dług / Kapitał własny', f"{analyzer.indicators['debt_to_equity']:.2f}",
         'DOBRA' if analyzer.indicators['debt_to_equity'] < 1.0 else 'SŁ' if analyzer.indicators['debt_to_equity'] < 1.5 else 'ZŁA'],
        ['Marża netto', f"{analyzer.indicators['net_margin']:.1f}%",
         'DOBRA' if analyzer.indicators['net_margin'] > 5 else 'SŁ' if analyzer.indicators['net_margin'] > 0 else 'ZŁA'],
        ['ROE', f"{analyzer.indicators['roe']:.1f}%",
         'DOBRA' if analyzer.indicators['roe'] > 10 else 'SŁ' if analyzer.indicators['roe'] > 0 else 'ZŁA'],
    ]
    
    ind_table = Table(ind_data, colWidths=[6*cm, 4*cm, 4*cm])
    ind_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(ind_table)
    story.append(Spacer(1, 0.8*cm))
    
    # Recommendation
    story.append(Paragraph("REKOMENDACJA LIMITU FX FORWARD", heading_style))
    
    rec_color = colors.HexColor('#28a745') if analyzer.recommendation['decision_color'] == 'success' else \
                colors.HexColor('#ffc107') if analyzer.recommendation['decision_color'] == 'warning' else \
                colors.HexColor('#dc3545')
    
    rec_data = [
        ['DECYZJA', analyzer.recommendation['decision']],
        ['Rekomendowany limit', f"{analyzer.recommendation['recommended_limit_mln']:.2f} mln PLN"],
        ['Zabezpieczenie', analyzer.recommendation['collateral']],
        ['Maksymalny tenor', analyzer.recommendation['max_tenor']],
    ]
    rec_table = Table(rec_data, colWidths=[5*cm, 9*cm])
    rec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rec_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('FONTNAME', (0, 0), (0, -1), 'DejaVuSans-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'DejaVuSans'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(rec_table)
    
    # Build PDF
    doc.build(story)


def main():
    # Header
    st.markdown('<p class="main-header">📊 Analityk Kredytowy - Limity FX Forward</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/financial-growth-analysis.png", width=80)
        st.title("⚙️ Ustawienia")
        
        st.markdown("---")
        st.subheader("📤 Wczytaj sprawozdanie")
        
        file_type = st.radio("Typ pliku:", ["XML", "PDF (tekstowy)"])
        uploaded_file = st.file_uploader(
            "Wybierz plik sprawozdania finansowego",
            type=['xml', 'pdf'],
            help="Wgraj sprawozdanie finansowe w formacie XML lub PDF"
        )
        
        st.markdown("---")
        st.subheader("💰 Parametry analizy")
        
        requested_limit = st.number_input(
            "Wnioskowany limit (mln PLN)",
            min_value=0.1,
            max_value=100.0,
            value=1.0,
            step=0.1,
            help="Limit na transakcje FX forward"
        )
        
        st.markdown("---")
        st.info("""
        **Instrukcja:**
        1. Wybierz typ pliku (XML/PDF)
        2. Wczytaj sprawozdanie finansowe
        3. Wprowadź wnioskowany limit
        4. Kliknij 'Analizuj sprawozdanie'
        5. Pobierz raport PDF
        """)
    
    # Main content
    if uploaded_file is None:
        st.info("👈 Wczytaj sprawozdanie finansowe aby rozpocząć analizę")
        
        # Example metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Przeanalizowane firmy", "47", "12 w tym miesiącu")
        with col2:
            st.metric("Zatwierdzone limity", "32", "68%")
        with col3:
            st.metric("Średni limit", "2.3 mln PLN", "+0.4")
        with col4:
            st.metric("Czas analizy", "< 2 min", "")
        
        st.markdown("---")
        
        # Features
        st.subheader("🎯 Funkcjonalności systemu")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **✅ Automatyczna analiza:**
            - Wczytywanie XML i PDF
            - Automatyczne obliczanie wskaźników
            - Ocena ryzyka kredytowego
            - Rekomendacja limitu
            
            **📊 Wskaźniki finansowe:**
            - Płynność (bieżąca, szybka)
            - Zadłużenie (D/E, D/A)
            - Rentowność (ROE, ROA, marże)
            - Cash flow operacyjny
            """)
        
        with col2:
            st.markdown("""
            **🎯 Rating kredytowy:**
            - Ocena punktowa 0-100
            - Rating od A do C-
            - Poziom ryzyka
            - Czerwone flagi
            
            **📄 Dokumentacja:**
            - Raport PDF z analizą
            - Rekomendacja limitu
            - Warunki zabezpieczenia
            - Covenant'y finansowe
            """)
        
        st.markdown("---")
        
        # Sample rating table
        st.subheader("📈 Skala ratingowa")
        
        rating_df = pd.DataFrame({
            'Rating': ['A', 'B+', 'B', 'C+', 'C-'],
            'Punkty': ['80-100', '65-79', '50-64', '35-49', '0-34'],
            'Ryzyko': ['Niskie', 'Umiarkowane', 'Podwyższone', 'Wysokie', 'Bardzo wysokie'],
            'Limit bazowy': ['10% przychodów', '7.5% przychodów', '5% przychodów', '2.5% przychodów', 'Odmowa'],
            'Zabezpieczenie': ['10-20%', '50%', '80%', '100%', '120%']
        })
        
        st.dataframe(rating_df, use_container_width=True)
        
    else:
        # Process uploaded file
        if st.sidebar.button("🔍 Analizuj sprawozdanie", type="primary", use_container_width=True):
            with st.spinner("Przetwarzam sprawozdanie..."):
                analyzer = FinancialAnalyzer()
                
                if file_type == "XML":
                    xml_content = uploaded_file.read()
                    if analyzer.parse_xml(xml_content):
                        st.success("✅ Sprawozdanie wczytane pomyślnie!")
                    else:
                        st.error("❌ Błąd wczytywania sprawozdania")
                        return
                else:
                    st.warning("⚠️ Obsługa PDF w rozwoju - użyj pliku XML")
                    return
                
                # Calculate indicators
                analyzer.calculate_indicators()
                
                # Assess risk
                analyzer.assess_credit_risk()
                
                # Generate recommendation
                analyzer.generate_recommendation(requested_limit)
                
                # Store in session state
                st.session_state['analyzer'] = analyzer
        
        # Display results if analysis done
        if 'analyzer' in st.session_state:
            analyzer = st.session_state['analyzer']
            
            # Company header
            st.markdown(f"### 🏢 {analyzer.data.get('company_name', 'N/A')}")
            st.markdown(f"**NIP:** {analyzer.data.get('nip', 'N/A')} | **KRS:** {analyzer.data.get('krs', 'N/A')}")
            
            # Rating banner
            rating_colors = {
                'green': '#28a745',
                'blue': '#007bff',
                'orange': '#fd7e14',
                'red': '#dc3545',
                'darkred': '#8b0000'
            }
            
            rating_html = f"""
            <div style='background: linear-gradient(135deg, {rating_colors.get(analyzer.rating['color'], '#666')} 0%, #333 100%); 
                        padding: 2rem; border-radius: 15px; color: white; text-align: center; margin: 2rem 0;
                        box-shadow: 0 8px 16px rgba(0,0,0,0.2);'>
                <h1 style='margin: 0; font-size: 3rem;'>{analyzer.rating['rating']}</h1>
                <h3 style='margin: 0.5rem 0 0 0;'>{analyzer.rating['risk_level']}</h3>
                <p style='margin: 0.5rem 0 0 0; font-size: 1.2rem;'>Wynik: {analyzer.rating['score']}/100 punktów</p>
            </div>
            """
            st.markdown(rating_html, unsafe_allow_html=True)
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                revenue_mln = analyzer.data.get('revenue', 0) / 1_000_000
                st.metric(
                    "Przychody",
                    f"{revenue_mln:.1f} mln PLN",
                    delta=None
                )
            
            with col2:
                net_profit_mln = analyzer.data.get('net_profit', 0) / 1_000_000
                st.metric(
                    "Wynik netto",
                    f"{net_profit_mln:.2f} mln PLN",
                    delta="Zysk" if net_profit_mln > 0 else "Strata",
                    delta_color="normal" if net_profit_mln > 0 else "inverse"
                )
            
            with col3:
                cash_mln = analyzer.data.get('cash', 0) / 1_000_000
                st.metric(
                    "Środki pieniężne",
                    f"{cash_mln:.2f} mln PLN",
                    delta=None
                )
            
            with col4:
                equity_mln = analyzer.data.get('equity', 0) / 1_000_000
                st.metric(
                    "Kapitał własny",
                    f"{equity_mln:.1f} mln PLN",
                    delta=None
                )
            
            # Tabs for detailed analysis
            tab1, tab2, tab3, tab4 = st.tabs(["📊 Wskaźniki", "⚠️ Czerwone flagi", "💰 Rekomendacja", "📄 Bilans"])
            
            with tab1:
                st.subheader("Wskaźniki finansowe")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Płynność**")
                    liquidity_df = pd.DataFrame({
                        'Wskaźnik': ['Bieżąca płynność', 'Szybka płynność', 'Gotówkowa płynność'],
                        'Wartość': [
                            f"{analyzer.indicators['current_ratio']:.2f}",
                            f"{analyzer.indicators['quick_ratio']:.2f}",
                            f"{analyzer.indicators['cash_ratio']:.2f}"
                        ],
                        'Norma': ['>1.5', '>1.0', '>0.2'],
                        'Status': [
                            '✅' if analyzer.indicators['current_ratio'] >= 1.5 else '⚠️' if analyzer.indicators['current_ratio'] >= 1.0 else '❌',
                            '✅' if analyzer.indicators['quick_ratio'] >= 1.0 else '⚠️' if analyzer.indicators['quick_ratio'] >= 0.7 else '❌',
                            '✅' if analyzer.indicators['cash_ratio'] >= 0.2 else '⚠️' if analyzer.indicators['cash_ratio'] >= 0.1 else '❌'
                        ]
                    })
                    st.dataframe(liquidity_df, use_container_width=True, hide_index=True)
                    
                    st.markdown("**Zadłużenie**")
                    leverage_df = pd.DataFrame({
                        'Wskaźnik': ['Dług / Kapitał własny', 'Dług / Aktywa'],
                        'Wartość': [
                            f"{analyzer.indicators['debt_to_equity']:.2f}",
                            f"{analyzer.indicators['debt_to_assets']:.2f}"
                        ],
                        'Norma': ['<1.0', '<0.6'],
                        'Status': [
                            '✅' if analyzer.indicators['debt_to_equity'] < 1.0 else '⚠️' if analyzer.indicators['debt_to_equity'] < 1.5 else '❌',
                            '✅' if analyzer.indicators['debt_to_assets'] < 0.6 else '⚠️' if analyzer.indicators['debt_to_assets'] < 0.7 else '❌'
                        ]
                    })
                    st.dataframe(leverage_df, use_container_width=True, hide_index=True)
                
                with col2:
                    st.markdown("**Rentowność**")
                    profitability_df = pd.DataFrame({
                        'Wskaźnik': ['ROE', 'ROA', 'Marża netto', 'Marża operacyjna'],
                        'Wartość': [
                            f"{analyzer.indicators['roe']:.1f}%",
                            f"{analyzer.indicators['roa']:.1f}%",
                            f"{analyzer.indicators['net_margin']:.1f}%",
                            f"{analyzer.indicators['operating_margin']:.1f}%"
                        ],
                        'Status': [
                            '✅' if analyzer.indicators['roe'] > 10 else '⚠️' if analyzer.indicators['roe'] > 0 else '❌',
                            '✅' if analyzer.indicators['roa'] > 5 else '⚠️' if analyzer.indicators['roa'] > 0 else '❌',
                            '✅' if analyzer.indicators['net_margin'] > 5 else '⚠️' if analyzer.indicators['net_margin'] > 0 else '❌',
                            '✅' if analyzer.indicators['operating_margin'] > 5 else '⚠️' if analyzer.indicators['operating_margin'] > 0 else '❌'
                        ]
                    })
                    st.dataframe(profitability_df, use_container_width=True, hide_index=True)
                    
                    st.markdown("**Kapitał obrotowy**")
                    wc_mln = analyzer.indicators['working_capital'] / 1_000_000
                    st.metric("Kapitał obrotowy netto", f"{wc_mln:.2f} mln PLN")
            
            with tab2:
                st.subheader("Czerwone flagi i punkty uwagi")
                
                if analyzer.rating['red_flags']:
                    for flag in analyzer.rating['red_flags']:
                        st.markdown(f"""
                        <div class='danger-box'>
                            ❌ <strong>{flag}</strong>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class='success-box'>
                        ✅ <strong>Brak krytycznych czerwonych flag</strong>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Additional warnings
                st.markdown("### Dodatkowe uwagi:")
                
                if analyzer.indicators['current_ratio'] < 1.2:
                    st.warning("⚠️ Wskaźnik płynności bieżącej poniżej rekomendowanego poziomu 1.5")
                
                if analyzer.data.get('net_profit', 0) < 0:
                    st.error("🔴 Firma generuje stratę netto - wymaga szczególnej uwagi")
                
                if analyzer.indicators['debt_to_equity'] > 1.5:
                    st.error("🔴 Bardzo wysokie zadłużenie względem kapitału własnego")
                
                cash_to_revenue = analyzer.data.get('cash', 0) / analyzer.data.get('revenue', 1) * 100 if analyzer.data.get('revenue', 0) > 0 else 0
                if cash_to_revenue < 3:
                    st.warning(f"⚠️ Niski poziom gotówki ({cash_to_revenue:.1f}% przychodów)")
            
            with tab3:
                st.subheader("Rekomendacja limitu FX Forward")
                
                # Decision box
                decision_box_class = analyzer.recommendation['decision_color'] + '-box'
                decision_icon = '✅' if analyzer.recommendation['decision'] == 'ZATWIERDZENIE' else '⚠️' if analyzer.recommendation['decision'] == 'ZATWIERDZENIE WARUNKOWE' else '❌'
                
                st.markdown(f"""
                <div class='{decision_box_class}'>
                    <h2>{decision_icon} {analyzer.recommendation['decision']}</h2>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 💰 Parametry limitu")
                    st.metric("Rekomendowany limit", f"{analyzer.recommendation['recommended_limit_mln']:.2f} mln PLN")
                    st.metric("Wnioskowany limit", f"{analyzer.recommendation['requested_limit_mln']:.2f} mln PLN")
                    st.metric("Stopień pokrycia", f"{analyzer.recommendation['approval_ratio']:.1f}%")
                
                with col2:
                    st.markdown("### 🔒 Warunki")
                    st.info(f"**Zabezpieczenie:** {analyzer.recommendation['collateral']}")
                    st.info(f"**Maksymalny tenor:** {analyzer.recommendation['max_tenor']}")
                
                # Conditions
                if analyzer.recommendation['conditions']:
                    st.markdown("### 📋 Dodatkowe warunki (Covenants)")
                    for i, condition in enumerate(analyzer.recommendation['conditions'], 1):
                        st.markdown(f"{i}. {condition}")
                
                # Explanation
                st.markdown("---")
                st.markdown("### 📝 Uzasadnienie")
                
                if analyzer.recommendation['decision'] == 'ZATWIERDZENIE':
                    st.success("""
                    Firma spełnia kryteria przyznania limitu na transakcje FX forward. 
                    Wskaźniki finansowe są na zadowalającym poziomie, a ryzyko kredytowe ocenione jako akceptowalne.
                    """)
                elif analyzer.recommendation['decision'] == 'ZATWIERDZENIE WARUNKOWE':
                    st.warning("""
                    Firma może otrzymać limit pod warunkiem spełnienia dodatkowych wymagań dotyczących 
                    zabezpieczenia i monitoringu. Wskaźniki finansowe wymagają bieżącej kontroli.
                    """)
                else:
                    st.error("""
                    Firma nie spełnia minimalnych kryteriów przyznania limitu na transakcje FX forward. 
                    Wysokie ryzyko kredytowe wymaga odmowy lub znaczącego zwiększenia zabezpieczenia.
                    """)
            
            with tab4:
                st.subheader("Bilans i rachunki wyników")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**AKTYWA**")
                    assets_df = pd.DataFrame({
                        'Pozycja': [
                            'Aktywa razem',
                            '  - Aktywa trwałe',
                            '  - Aktywa obrotowe',
                            '    - Zapasy',
                            '    - Należności',
                            '    - Środki pieniężne'
                        ],
                        'Wartość (mln PLN)': [
                            f"{analyzer.data.get('total_assets', 0)/1_000_000:.2f}",
                            f"{analyzer.data.get('fixed_assets', 0)/1_000_000:.2f}",
                            f"{analyzer.data.get('current_assets', 0)/1_000_000:.2f}",
                            f"{analyzer.data.get('inventory', 0)/1_000_000:.2f}",
                            f"{analyzer.data.get('receivables', 0)/1_000_000:.2f}",
                            f"{analyzer.data.get('cash', 0)/1_000_000:.2f}"
                        ]
                    })
                    st.dataframe(assets_df, use_container_width=True, hide_index=True)
                
                with col2:
                    st.markdown("**PASYWA**")
                    liabilities_df = pd.DataFrame({
                        'Pozycja': [
                            'Pasywa razem',
                            '  - Kapitał własny',
                            '  - Zobowiązania razem',
                            '    - Zobowiązania krótkoterm.'
                        ],
                        'Wartość (mln PLN)': [
                            f"{analyzer.data.get('total_assets', 0)/1_000_000:.2f}",
                            f"{analyzer.data.get('equity', 0)/1_000_000:.2f}",
                            f"{analyzer.data.get('liabilities', 0)/1_000_000:.2f}",
                            f"{analyzer.data.get('short_term_liabilities', 0)/1_000_000:.2f}"
                        ]
                    })
                    st.dataframe(liabilities_df, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.markdown("**RACHUNEK ZYSKÓW I STRAT**")
                
                pnl_df = pd.DataFrame({
                    'Pozycja': ['Przychody ze sprzedaży', 'Wynik operacyjny', 'Wynik netto', 'EBITDA'],
                    'Wartość (mln PLN)': [
                        f"{analyzer.data.get('revenue', 0)/1_000_000:.2f}",
                        f"{analyzer.data.get('operating_profit', 0)/1_000_000:.2f}",
                        f"{analyzer.data.get('net_profit', 0)/1_000_000:.2f}",
                        f"{analyzer.data.get('ebitda', 0)/1_000_000:.2f}"
                    ]
                })
                st.dataframe(pnl_df, use_container_width=True, hide_index=True)
            
            # Download PDF button
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if not REPORTLAB_AVAILABLE:
                    st.warning("⚠️ Eksport PDF wymaga pakietu reportlab. Zainstaluj: `pip install reportlab`")
                elif st.button("📥 Pobierz raport PDF", type="primary", use_container_width=True):
                    try:
                        pdf_buffer = BytesIO()
                        generate_pdf_report(analyzer, pdf_buffer)
                        pdf_buffer.seek(0)
                        
                        st.download_button(
                            label="💾 Zapisz raport PDF",
                            data=pdf_buffer,
                            file_name=f"Analiza_kredytowa_{analyzer.data.get('nip', 'N-A')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Błąd generowania PDF: {str(e)}")


if __name__ == "__main__":
    main()
