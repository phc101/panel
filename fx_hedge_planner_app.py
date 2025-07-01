import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta

# ============================================================================
# PROFESSIONAL WINDOW FORWARD CALCULATOR - API INTEGRATED
# ============================================================================

class APIIntegratedForwardCalculator:
    """Professional window forward calculator using real API data"""
    
    def __init__(self, fred_client):
        self.fred_client = fred_client
        self.tenors = [
            "One Month", "Two Month", "Three Month", "Four Month", 
            "Five Month", "Six Month", "Seven Month", "Eight Month",
            "Nine Month", "Ten Month", "Eleven Month", "One Year"
        ]
        
        # Tenor mapping to months
        self.tenor_months = {
            "One Month": 1, "Two Month": 2, "Three Month": 3, "Four Month": 4,
            "Five Month": 5, "Six Month": 6, "Seven Month": 7, "Eight Month": 8,
            "Nine Month": 9, "Ten Month": 10, "Eleven Month": 11, "One Year": 12
        }
        
        # Professional pricing parameters (based on your CSV analysis)
        self.points_factor = 0.70  # Client gets 70% of forward points
        self.risk_factor = 0.40    # Bank charges 40% of swap risk
    
    def calculate_theoretical_forward_points(self, spot_rate, pl_yield, de_yield, days):
        """Calculate theoretical forward points using bond yield spreads"""
        T = days / 365.0
        
        # Interest rate parity formula
        forward_rate = spot_rate * (1 + pl_yield/100 * T) / (1 + de_yield/100 * T)
        forward_points = forward_rate - spot_rate
        
        return {
            'forward_rate': forward_rate,
            'forward_points': forward_points,
            'days': days,
            'yield_spread': pl_yield - de_yield,
            'time_factor': T
        }
    
    def generate_api_forward_points_curve(self, spot_rate, pl_yield, de_yield, bid_ask_spread=0.002):
        """Generate complete forward points curve from API bond data"""
        curve_data = {}
        
        for tenor in self.tenors:
            months = self.tenor_months[tenor]
            days = months * 30  # Approximate days
            
            # Calculate theoretical forward points
            theoretical = self.calculate_theoretical_forward_points(spot_rate, pl_yield, de_yield, days)
            forward_points = theoretical['forward_points']
            
            # Add market spread
            bid_points = forward_points - (bid_ask_spread / 2)
            ask_points = forward_points + (bid_ask_spread / 2)
            mid_points = forward_points
            
            curve_data[tenor] = {
                "days": days,
                "months": months,
                "bid": bid_points,
                "ask": ask_points,
                "mid": mid_points,
                "theoretical_forward": theoretical['forward_rate'],
                "yield_spread": theoretical['yield_spread']
            }
        
        return curve_data
    
    def interpolate_points_to_window(self, window_days, forward_curve):
        """Interpolate forward points to the exact window start date"""
        # Convert window days to months
        window_months = window_days / 30.0
        
        # Get available tenors sorted by months
        available_data = [(data["months"], tenor, data) for tenor, data in forward_curve.items()]
        available_data.sort(key=lambda x: x[0])
        
        # Find interpolation bounds
        if window_months <= available_data[0][0]:
            # Extrapolate from shortest tenor
            months = available_data[0][0]
            data = available_data[0][2]
            ratio = window_months / months
            return {
                "bid": data["bid"] * ratio,
                "ask": data["ask"] * ratio,
                "mid": data["mid"] * ratio,
                "interpolation_method": f"Extrapolated from {available_data[0][1]}"
            }
        
        elif window_months >= available_data[-1][0]:
            # Use longest tenor
            data = available_data[-1][2]
            return {
                "bid": data["bid"],
                "ask": data["ask"], 
                "mid": data["mid"],
                "interpolation_method": f"Used {available_data[-1][1]}"
            }
        
        else:
            # Linear interpolation between two tenors
            for i in range(len(available_data) - 1):
                lower_months, lower_tenor, lower_data = available_data[i]
                upper_months, upper_tenor, upper_data = available_data[i + 1]
                
                if lower_months <= window_months <= upper_months:
                    # Interpolation ratio
                    ratio = (window_months - lower_months) / (upper_months - lower_months)
                    
                    return {
                        "bid": lower_data["bid"] + ratio * (upper_data["bid"] - lower_data["bid"]),
                        "ask": lower_data["ask"] + ratio * (upper_data["ask"] - lower_data["ask"]),
                        "mid": lower_data["mid"] + ratio * (upper_data["mid"] - lower_data["mid"]),
                        "interpolation_method": f"Interpolated between {lower_tenor} and {upper_tenor}"
                    }
    
    def calculate_swap_risk(self, window_days, points_to_window, volatility_factor=0.25):
        """Calculate swap risk based on window length and market volatility
        
        Based on your CSV analysis:
        - Swap risk increases with tenor
        - Typical range: 0.02-0.03 points for standard windows
        """
        base_risk = abs(points_to_window) * volatility_factor
        time_adjustment = np.sqrt(window_days / 90)  # Scale with sqrt of time
        
        # Add minimum risk floor
        min_risk = 0.015
        calculated_risk = max(base_risk * time_adjustment, min_risk)
        
        return calculated_risk
    
    def calculate_professional_rates(self, spot_rate, points_to_window, swap_risk):
        """Calculate rates using professional window forward logic
        
        Based on your CSV analysis:
        - FWD Client = Spot + (Points to Window × 0.70) - (Swap Risk × 0.40) 
        - FWD to Open = Spot + Points to Window
        - Profit = FWD to Open - FWD Client
        """
        
        # Client rate: Give 70% of points, charge 40% of swap risk
        fwd_client = spot_rate + (points_to_window * self.points_factor) - (swap_risk * self.risk_factor)
        
        # Theoretical rate to window start (full points)
        fwd_to_open = spot_rate + points_to_window
        
        # Profit analysis
        profit_per_eur = fwd_to_open - fwd_client
        
        return {
            'fwd_client': fwd_client,
            'fwd_to_open': fwd_to_open,
            'profit_per_eur': profit_per_eur,
            'points_given_to_client': points_to_window * self.points_factor,
            'swap_risk_charged': swap_risk * self.risk_factor,
            'effective_spread': profit_per_eur
        }
    
    def calculate_pnl_analysis(self, profit_per_eur, nominal_amount_eur, leverage=1.0):
        """Calculate comprehensive P&L analysis"""
        
        # Basic calculations
        gross_profit_eur = profit_per_eur * nominal_amount_eur
        leveraged_profit = gross_profit_eur * leverage
        
        # Risk metrics
        profit_percentage = (profit_per_eur / 4.25) * 100  # Approximate spot base
        profit_bps = profit_per_eur * 10000
        
        return {
            'gross_profit_eur': gross_profit_eur,
            'leveraged_profit': leveraged_profit,
            'profit_percentage': profit_percentage,
            'profit_bps': profit_bps,
            'nominal_amount': nominal_amount_eur,
            'leverage_factor': leverage
        }

# ============================================================================
# ENHANCED STREAMLIT INTERFACE
# ============================================================================

def create_professional_window_forward_tab():
    """Create the professional window forward calculator interface"""
    
    st.header("💼 Professional Window Forward Calculator")
    st.markdown("*Real-time API data with professional pricing logic*")
    
    # Load real market data
    with st.spinner("📡 Loading real-time market data..."):
        bond_data = get_fred_bond_data()
        forex_data = get_eur_pln_rate()
    
    # Initialize calculator
    calculator = APIIntegratedForwardCalculator(FREDAPIClient())
    
    # ============================================================================
    # MARKET DATA DISPLAY
    # ============================================================================
    
    st.subheader("📊 Live Market Data")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        spot_rate = forex_data['rate']
        st.metric(
            "EUR/PLN Spot",
            f"{spot_rate:.4f}",
            help=f"Source: {forex_data['source']} | Updated: {forex_data['date']}"
        )
    
    with col2:
        pl_yield = bond_data['Poland_10Y']['value'] if 'Poland_10Y' in bond_data else 5.70
        st.metric(
            "Poland 10Y Yield",
            f"{pl_yield:.2f}%",
            help="FRED API - Polish government bonds"
        )
    
    with col3:
        de_yield = bond_data['Germany_9M']['value'] if 'Germany_9M' in bond_data else 2.35
        st.metric(
            "Germany Yield",
            f"{de_yield:.2f}%", 
            help="Interpolated from German bonds"
        )
    
    with col4:
        spread = pl_yield - de_yield
        st.metric(
            "PL-DE Spread",
            f"{spread:.2f}pp",
            help="Yield differential driving forward points"
        )
    
    # ============================================================================
    # CONFIGURATION PARAMETERS
    # ============================================================================
    
    st.markdown("---")
    st.subheader("⚙️ Deal Configuration")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        window_days = st.number_input(
            "Window Length (days):",
            value=90,
            min_value=30,
            max_value=365,
            step=5,
            help="Length of the window forward period"
        )
    
    with col2:
        nominal_amount = st.number_input(
            "Nominal Amount (EUR):",
            value=2_500_000,
            min_value=100_000,
            max_value=100_000_000,
            step=100_000,
            format="%d",
            help="Deal notional amount"
        )
    
    with col3:
        leverage = st.number_input(
            "Leverage Factor:",
            value=1.0,
            min_value=1.0,
            max_value=3.0,
            step=0.1,
            help="Risk leverage for P&L calculation"
        )
    
    # Advanced parameters
    with st.expander("🔧 Advanced Pricing Parameters"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            points_factor = st.slider(
                "Points Factor (% to client):",
                min_value=0.60,
                max_value=0.85,
                value=0.70,
                step=0.01,
                help="Percentage of forward points given to client"
            )
        
        with col2:
            risk_factor = st.slider(
                "Risk Factor (% charged):",
                min_value=0.30,
                max_value=0.60,
                value=0.40,
                step=0.01,
                help="Percentage of swap risk charged to client"
            )
        
        with col3:
            bid_ask_spread = st.number_input(
                "Bid-Ask Spread:",
                value=0.002,
                min_value=0.001,
                max_value=0.005,
                step=0.0005,
                format="%.4f",
                help="Market bid-ask spread in forward points"
            )
    
    # Update calculator parameters
    calculator.points_factor = points_factor
    calculator.risk_factor = risk_factor
    
    # ============================================================================
    # REAL-TIME CALCULATIONS
    # ============================================================================
    
    st.markdown("---")
    st.subheader("🔢 Live Forward Points Generation")
    
    # Generate forward curve from API data
    forward_curve = calculator.generate_api_forward_points_curve(
        spot_rate, pl_yield, de_yield, bid_ask_spread
    )
    
    # Display forward points table
    with st.expander("📋 Complete Forward Points Curve"):
        curve_display_data = []
        for tenor, data in forward_curve.items():
            curve_display_data.append({
                "Tenor": tenor,
                "Days": data["days"],
                "Bid": f"{data['bid']:.4f}",
                "Ask": f"{data['ask']:.4f}",
                "Mid": f"{data['mid']:.4f}",
                "Yield Spread": f"{data['yield_spread']:.2f}pp"
            })
        
        df_curve = pd.DataFrame(curve_display_data)
        st.dataframe(df_curve, use_container_width=True)
    
    # Calculate points to window
    points_to_window_data = calculator.interpolate_points_to_window(window_days, forward_curve)
    points_to_window = points_to_window_data['mid']
    
    # Calculate swap risk
    swap_risk = calculator.calculate_swap_risk(window_days, points_to_window)
    
    # Calculate professional rates
    rates = calculator.calculate_professional_rates(spot_rate, points_to_window, swap_risk)
    
    # Calculate P&L
    pnl = calculator.calculate_pnl_analysis(rates['profit_per_eur'], nominal_amount, leverage)
    
    # ============================================================================
    # RESULTS DISPLAY
    # ============================================================================
    
    st.subheader("💰 Professional Pricing Results")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Points to Window",
            f"{points_to_window:.4f}",
            help=f"Forward points to window start ({points_to_window_data['interpolation_method']})"
        )
    
    with col2:
        st.metric(
            "Swap Risk",
            f"{swap_risk:.4f}",
            help="Estimated swap risk for window period"
        )
    
    with col3:
        st.metric(
            "Client Forward Rate",
            f"{rates['fwd_client']:.4f}",
            delta=f"{rates['fwd_client'] - spot_rate:.4f}",
            help="Rate quoted to client"
        )
    
    with col4:
        st.metric(
            "Profit per EUR",
            f"{rates['profit_per_eur']:.4f} PLN",
            help="Bank profit per EUR notional"
        )
    
    # Detailed breakdown
    st.markdown("---")
    st.subheader("📈 Detailed Pricing Breakdown")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("**🔍 Rate Calculation:**")
        st.code(f"""
Forward Points to Window:     {points_to_window:.4f}
Points Given to Client (70%): {rates['points_given_to_client']:.4f}
Swap Risk:                    {swap_risk:.4f}
Risk Charged to Client (40%): {rates['swap_risk_charged']:.4f}

CLIENT RATE FORMULA:
{spot_rate:.4f} + {rates['points_given_to_client']:.4f} - {rates['swap_risk_charged']:.4f} = {rates['fwd_client']:.4f}

THEORETICAL RATE TO WINDOW:
{spot_rate:.4f} + {points_to_window:.4f} = {rates['fwd_to_open']:.4f}

BANK PROFIT PER EUR:
{rates['fwd_to_open']:.4f} - {rates['fwd_client']:.4f} = {rates['profit_per_eur']:.4f} PLN
        """)
    
    with col2:
        st.markdown("**💼 P&L Analysis:**")
        
        # P&L metrics
        st.metric("Gross Profit", f"€{pnl['gross_profit_eur']:,.0f}", help="Total profit in EUR")
        st.metric("Leveraged Profit", f"€{pnl['leveraged_profit']:,.0f}", help=f"With {leverage}x leverage")
        st.metric("Profit Margin", f"{pnl['profit_percentage']:.2f}%", help="As % of spot rate")
        st.metric("Profit (Basis Points)", f"{pnl['profit_bps']:.1f} bps", help="Profit in basis points")
        
        # Risk warning
        if pnl['profit_percentage'] < 0.1:
            st.warning("⚠️ Low profit margin - consider adjusting parameters")
        elif pnl['profit_percentage'] > 1.0:
            st.success("✅ Healthy profit margin")
    
    # ============================================================================
    # SCENARIO ANALYSIS
    # ============================================================================
    
    st.markdown("---")
    st.subheader("📊 Scenario Analysis")
    
    # Create scenarios for different market conditions
    scenarios = {
        "Current Market": {"pl_shift": 0, "de_shift": 0, "vol_mult": 1.0},
        "PL Yields +50bp": {"pl_shift": 0.50, "de_shift": 0, "vol_mult": 1.2},
        "PL Yields -50bp": {"pl_shift": -0.50, "de_shift": 0, "vol_mult": 1.2}, 
        "DE Yields +25bp": {"pl_shift": 0, "de_shift": 0.25, "vol_mult": 1.1},
        "Spread Tightening": {"pl_shift": -0.25, "de_shift": 0.25, "vol_mult": 1.3}
    }
    
    scenario_results = []
    
    for scenario_name, shifts in scenarios.items():
        # Adjust yields
        adj_pl_yield = pl_yield + shifts['pl_shift']
        adj_de_yield = de_yield + shifts['de_shift']
        
        # Generate new curve
        scenario_curve = calculator.generate_api_forward_points_curve(
            spot_rate, adj_pl_yield, adj_de_yield, bid_ask_spread
        )
        
        # Calculate scenario metrics
        scenario_points = calculator.interpolate_points_to_window(window_days, scenario_curve)['mid']
        scenario_swap_risk = calculator.calculate_swap_risk(window_days, scenario_points) * shifts['vol_mult']
        scenario_rates = calculator.calculate_professional_rates(spot_rate, scenario_points, scenario_swap_risk)
        scenario_pnl = calculator.calculate_pnl_analysis(scenario_rates['profit_per_eur'], nominal_amount, leverage)
        
        scenario_results.append({
            "Scenario": scenario_name,
            "PL Yield": f"{adj_pl_yield:.2f}%",
            "DE Yield": f"{adj_de_yield:.2f}%",
            "Spread": f"{adj_pl_yield - adj_de_yield:.2f}pp",
            "Points to Window": f"{scenario_points:.4f}",
            "Client Rate": f"{scenario_rates['fwd_client']:.4f}",
            "Profit per EUR": f"{scenario_rates['profit_per_eur']:.4f}",
            "Total Profit": f"€{scenario_pnl['gross_profit_eur']:,.0f}",
            "Profit %": f"{scenario_pnl['profit_percentage']:.2f}%"
        })
    
    df_scenarios = pd.DataFrame(scenario_results)
    
    # Style the dataframe
    def highlight_scenarios(row):
        if row.name == 0:  # Current market
            return ['background-color: #e8f5e8'] * len(row)
        elif "€-" in str(row['Total Profit']):  # Loss scenarios
            return ['background-color: #ffe8e8'] * len(row)
        else:
            return [''] * len(row)
    
    st.dataframe(
        df_scenarios.style.apply(highlight_scenarios, axis=1),
        use_container_width=True
    )
    
    # ============================================================================
    # VISUALIZATION
    # ============================================================================
    
    st.markdown("---")
    st.subheader("📈 Forward Curve Visualization")
    
    # Create forward curve chart
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Forward Points Curve', 'Profit by Scenario', 'Yield Spread Impact', 'Risk Analysis'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": True}, {"secondary_y": False}]]
    )
    
    # 1. Forward Points Curve
    curve_days = [data["days"] for data in forward_curve.values()]
    curve_points = [data["mid"] for data in forward_curve.values()]
    curve_tenors = list(forward_curve.keys())
    
    fig.add_trace(
        go.Scatter(
            x=curve_days,
            y=curve_points,
            mode='lines+markers',
            name='Forward Points',
            line=dict(color='blue', width=2),
            marker=dict(size=6)
        ),
        row=1, col=1
    )
    
    # Highlight window point
    fig.add_trace(
        go.Scatter(
            x=[window_days],
            y=[points_to_window],
            mode='markers',
            name=f'{window_days}D Window',
            marker=dict(size=12, color='red', symbol='diamond')
        ),
        row=1, col=1
    )
    
    # 2. Profit by Scenario
    scenario_names = [result["Scenario"] for result in scenario_results]
    scenario_profits = [float(result["Profit per EUR"]) for result in scenario_results]
    
    colors = ['green' if p > 0 else 'red' for p in scenario_profits]
    
    fig.add_trace(
        go.Bar(
            x=scenario_names,
            y=scenario_profits,
            name='Profit per EUR',
            marker_color=colors
        ),
        row=1, col=2
    )
    
    # 3. Yield Spread Impact
    spreads = [float(result["Spread"].replace('pp', '')) for result in scenario_results]
    profits_pct = [float(result["Profit %"].replace('%', '')) for result in scenario_results]
    
    fig.add_trace(
        go.Scatter(
            x=spreads,
            y=profits_pct,
            mode='markers+lines',
            name='Spread vs Profit',
            marker=dict(size=10, color='purple')
        ),
        row=2, col=1
    )
    
    # 4. Risk Analysis - Window Days vs Profit
    risk_analysis_days = list(range(30, 366, 30))
    risk_analysis_profits = []
    
    for days in risk_analysis_days:
        temp_points = calculator.interpolate_points_to_window(days, forward_curve)['mid']
        temp_risk = calculator.calculate_swap_risk(days, temp_points)
        temp_rates = calculator.calculate_professional_rates(spot_rate, temp_points, temp_risk)
        risk_analysis_profits.append(temp_rates['profit_per_eur'])
    
    fig.add_trace(
        go.Scatter(
            x=risk_analysis_days,
            y=risk_analysis_profits,
            mode='lines+markers',
            name='Window Length vs Profit',
            line=dict(color='orange', width=2)
        ),
        row=2, col=2
    )
    
    # Update layout
    fig.update_layout(
        height=600,
        showlegend=True,
        title_text="Window Forward Analytics Dashboard"
    )
    
    fig.update_xaxes(title_text="Days", row=1, col=1)
    fig.update_yaxes(title_text="Forward Points", row=1, col=1)
    fig.update_xaxes(title_text="Scenario", row=1, col=2)
    fig.update_yaxes(title_text="Profit per EUR", row=1, col=2)
    fig.update_xaxes(title_text="Yield Spread (pp)", row=2, col=1)
    fig.update_yaxes(title_text="Profit %", row=2, col=1)
    fig.update_xaxes(title_text="Window Days", row=2, col=2)
    fig.update_yaxes(title_text="Profit per EUR", row=2, col=2)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ============================================================================
    # DEAL SUMMARY
    # ============================================================================
    
    st.markdown("---")
    st.subheader("📋 Deal Summary")
    
    with st.container():
        summary_col1, summary_col2 = st.columns([1, 1])
        
        with summary_col1:
            st.markdown(f"""
            <div class="metric-card">
                <h4>💼 Window Forward Deal Structure</h4>
                <p><strong>Product:</strong> {window_days}-Day EUR/PLN Window Forward</p>
                <p><strong>Notional:</strong> €{nominal_amount:,}</p>
                <p><strong>Spot Rate:</strong> {spot_rate:.4f}</p>
                <p><strong>Client Forward Rate:</strong> {rates['fwd_client']:.4f}</p>
                <p><strong>Points Factor:</strong> {points_factor:.1%} (Industry: 70%)</p>
                <p><strong>Risk Factor:</strong> {risk_factor:.1%} (Industry: 40%)</p>
            </div>
            """, unsafe_allow_html=True)
        
        with summary_col2:
            st.markdown(f"""
            <div class="metric-card">
                <h4>💰 Financial Summary</h4>
                <p><strong>Bank Profit per EUR:</strong> {rates['profit_per_eur']:.4f} PLN</p>
                <p><strong>Total Gross Profit:</strong> €{pnl['gross_profit_eur']:,.0f}</p>
                <p><strong>Profit Margin:</strong> {pnl['profit_percentage']:.2f}%</p>
                <p><strong>Profit (Basis Points):</strong> {pnl['profit_bps']:.1f} bps</p>
                <p><strong>Points Given to Client:</strong> {rates['points_given_to_client']:.4f}</p>
                <p><strong>Risk Premium Charged:</strong> {rates['swap_risk_charged']:.4f}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Export functionality
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("📊 Generate Deal Report", use_container_width=True):
            # Create comprehensive deal report
            deal_report = f"""
# WINDOW FORWARD DEAL REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## DEAL PARAMETERS
- Product: {window_days}-Day EUR/PLN Window Forward
- Notional Amount: €{nominal_amount:,}
- Current Spot Rate: {spot_rate:.4f}
- Client Forward Rate: {rates['fwd_client']:.4f}

## MARKET DATA (Live API)
- Poland 10Y Yield: {pl_yield:.2f}%
- Germany Yield: {de_yield:.2f}%
- Yield Spread: {spread:.2f}pp
- Points to Window: {points_to_window:.4f}
- Estimated Swap Risk: {swap_risk:.4f}

## PRICING BREAKDOWN
- Points Factor: {points_factor:.1%}
- Risk Factor: {risk_factor:.1%}
- Points Given to Client: {rates['points_given_to_client']:.4f}
- Risk Premium Charged: {rates['swap_risk_charged']:.4f}

## FINANCIAL ANALYSIS
- Bank Profit per EUR: {rates['profit_per_eur']:.4f} PLN
- Total Gross Profit: €{pnl['gross_profit_eur']:,.0f}
- Profit Margin: {pnl['profit_percentage']:.2f}%
- Profit in Basis Points: {pnl['profit_bps']:.1f} bps

## RISK SCENARIOS
{df_scenarios.to_string(index=False)}

---
*Report generated using real-time FRED API and NBP exchange rate data*
            """
            
            st.download_button(
                label="📥 Download Deal Report",
                data=deal_report,
                file_name=f"window_forward_deal_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                use_container_width=True
            )

# ============================================================================
# INTEGRATION FUNCTIONS (to be added to main app)
# ============================================================================

def add_api_forward_calculator_to_main_app():
    """Integration function to add this calculator to the main Streamlit app"""
    
    # This would be added as Tab 4 in your main application
    with st.tabs(["🧮 Forward Rate Calculator", "📊 Bond Spread Dashboard", "💼 Window Forward Calculator", "🚀 API Professional Calculator"])[3]:
        create_professional_window_forward_tab()

# ============================================================================
# STANDALONE DEMO (if running this file directly)
# ============================================================================

if __name__ == "__main__":
    st.set_page_config(
        page_title="API Professional Forward Calculator",
        page_icon="🚀",
        layout="wide"
    )
    
    # Add custom CSS
    st.markdown("""
    <style>
        .metric-card {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
            margin: 0.5rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    create_professional_window_forward_tab()
