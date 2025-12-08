import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
import json
import requests

st.set_page_config(
    page_title="AI Volatility Chart Analyzer",
    layout="wide",
    page_icon="🔮"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }
    .analysis-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
    }
    .insight-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 1rem 0;
    }
    .signal-bullish {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .signal-bearish {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .signal-neutral {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .metric-extreme {
        color: #dc3545;
        font-weight: bold;
    }
    .metric-normal {
        color: #28a745;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🔮 AI Volatility Chart Analyzer</div>', unsafe_allow_html=True)
st.markdown("### Upload a volatility chart and get instant market intelligence")

# Sidebar configuration
st.sidebar.header("⚙️ Analysis Settings")

analysis_depth = st.sidebar.select_slider(
    "Analysis Depth",
    options=["Quick", "Standard", "Comprehensive", "Deep Dive"],
    value="Standard",
    help="How detailed should the analysis be?"
)

include_sections = st.sidebar.multiselect(
    "Include Analysis Sections",
    [
        "Market Sentiment",
        "Risk Metrics",
        "Trading Signals", 
        "Price Expectations",
        "Volatility Structure",
        "Positioning Analysis",
        "Historical Context",
        "Risk Scenarios"
    ],
    default=["Market Sentiment", "Risk Metrics", "Trading Signals", "Price Expectations"]
)

trading_horizon = st.sidebar.radio(
    "Trading Horizon",
    ["Intraday", "Short-term (1-5 days)", "Medium-term (1-4 weeks)", "Long-term (1-3 months)"],
    index=1
)

# Main upload area
col1, col2 = st.columns([2, 1])

with col1:
    uploaded_file = st.file_uploader(
        "📊 Upload Volatility Chart (PNG, JPG, JPEG)",
        type=['png', 'jpg', 'jpeg'],
        help="Upload a screenshot of volatility metrics (CVOL, Skew, Up/Down Var, etc.)"
    )

with col2:
    st.info("""
    **Supported Charts:**
    - CVOL Index
    - Skew / Skew Ratio
    - Up/Down Variance
    - ATM Volatility
    - Volatility Surfaces
    - Options Flow
    """)

# Analysis function using Claude API
def analyze_chart_with_ai(image_bytes, analysis_settings):
    """
    Analyze volatility chart using Claude's vision API
    """
    
    # Convert image to base64
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    
    # Determine image type
    img = Image.open(BytesIO(image_bytes))
    img_format = img.format.lower()
    if img_format == 'jpg':
        img_format = 'jpeg'
    
    media_type = f"image/{img_format}"
    
    # Build comprehensive prompt based on settings
    prompt = f"""You are an expert FX options trader and volatility analyst. Analyze this volatility chart and provide detailed market intelligence.

ANALYSIS DEPTH: {analysis_settings['depth']}
TRADING HORIZON: {analysis_settings['horizon']}

Please analyze the chart and provide insights in the following structure:

1. CHART IDENTIFICATION
   - What metrics are shown (CVOL, Skew, Up/Down Var, etc.)
   - Time period covered
   - Currency pair or asset
   - Current values vs historical levels

2. CURRENT MARKET STRUCTURE
   - Are metrics elevated, suppressed, or normal?
   - Calculate approximate z-scores from visual (high/low/normal)
   - Identify any divergences between metrics
   - Trend direction and strength

3. WHAT THE MARKET IS PRICING
   - Directional bias (bullish/bearish/neutral)
   - Tail risk expectations
   - Volatility regime (low/medium/high)
   - Time decay characteristics

4. KEY INSIGHTS
   - Most important patterns or anomalies
   - Historical context and comparisons
   - Correlation or divergence analysis
   - Hidden risks or opportunities

"""

    # Add requested sections
    if "Market Sentiment" in analysis_settings['sections']:
        prompt += """
5. MARKET SENTIMENT ANALYSIS
   - Overall positioning (long/short bias)
   - Risk appetite indicators
   - Fear vs greed signals
   - Institutional vs retail behavior
"""

    if "Risk Metrics" in analysis_settings['sections']:
        prompt += """
6. RISK METRICS ASSESSMENT
   - Downside vs upside risk asymmetry
   - Tail risk pricing
   - Volatility of volatility
   - Term structure implications
"""

    if "Trading Signals" in analysis_settings['sections']:
        prompt += """
7. TRADING SIGNALS
   - Entry/exit levels
   - Stop loss recommendations
   - Position sizing guidance
   - Options strategies to consider
"""

    if "Price Expectations" in analysis_settings['sections']:
        prompt += """
8. PRICE EXPECTATIONS
   - Expected price ranges
   - Breakout/breakdown levels
   - Probability of moves (based on IV)
   - Support/resistance from vol structure
"""

    if "Volatility Structure" in analysis_settings['sections']:
        prompt += """
9. VOLATILITY STRUCTURE ANALYSIS
   - Shape of volatility curve
   - Strike skew analysis
   - Term structure (if visible)
   - Calendar spread opportunities
"""

    if "Positioning Analysis" in analysis_settings['sections']:
        prompt += """
10. POSITIONING ANALYSIS
    - Where is the market positioned?
    - Overcrowded trades
    - Contrarian opportunities
    - Hedge fund vs commercial positioning
"""

    if "Historical Context" in analysis_settings['sections']:
        prompt += """
11. HISTORICAL CONTEXT
    - How extreme are current readings?
    - Similar historical patterns
    - What happened after similar setups?
    - Regime change indicators
"""

    if "Risk Scenarios" in analysis_settings['sections']:
        prompt += """
12. RISK SCENARIOS
    - Bull case: What would drive this?
    - Bear case: What would drive this?
    - Base case: Most likely outcome
    - Black swan risks
"""

    prompt += """

IMPORTANT INSTRUCTIONS:
- Be specific with numbers when visible on the chart
- Use clear directional language (bullish/bearish/neutral)
- Highlight any extreme or anomalous readings
- Compare current levels to visible historical ranges
- Provide actionable insights, not just descriptions
- Use trader-friendly terminology
- Flag any divergences or structural breaks
- Estimate z-scores as HIGH/EXTREME/NORMAL/LOW based on visual range

Format your response in clear sections with headers using **bold markdown**.
Use bullet points for lists.
Highlight key insights with emojis: 🔴 for bearish, 🟢 for bullish, 🟡 for neutral, 🚨 for extreme readings.
"""

    # Make API call to Claude
    try:
        api_url = "https://api.anthropic.com/v1/messages"
        
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        response = requests.post(api_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            analysis_text = result['content'][0]['text']
            return {
                'success': True,
                'analysis': analysis_text,
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'model': 'claude-sonnet-4',
                    'depth': analysis_settings['depth'],
                    'horizon': analysis_settings['horizon']
                }
            }
        else:
            return {
                'success': False,
                'error': f"API Error: {response.status_code}",
                'details': response.text
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def extract_signals_from_analysis(analysis_text):
    """
    Extract key signals and metrics from the analysis
    """
    signals = {
        'sentiment': 'Neutral',
        'confidence': 'Medium',
        'key_metrics': [],
        'action': 'Hold'
    }
    
    # Simple parsing logic
    lower_text = analysis_text.lower()
    
    # Sentiment detection
    if 'bearish' in lower_text and 'bullish' not in lower_text:
        signals['sentiment'] = 'Bearish'
        signals['action'] = 'Sell/Hedge'
    elif 'bullish' in lower_text and 'bearish' not in lower_text:
        signals['sentiment'] = 'Bullish'
        signals['action'] = 'Buy'
    elif 'extreme' in lower_text or '🚨' in analysis_text:
        signals['confidence'] = 'High'
    
    # Extract metrics mentioned
    metrics = ['cvol', 'skew', 'variance', 'volatility', 'iv']
    for metric in metrics:
        if metric in lower_text:
            signals['key_metrics'].append(metric.upper())
    
    return signals

# Main analysis area
if uploaded_file is not None:
    # Display uploaded image
    image_bytes = uploaded_file.read()
    image = Image.open(BytesIO(image_bytes))
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.image(image, caption="Uploaded Chart", use_container_width=True)
    
    with col2:
        st.markdown("### 📊 Chart Info")
        st.write(f"**Filename:** {uploaded_file.name}")
        st.write(f"**Size:** {len(image_bytes) / 1024:.1f} KB")
        st.write(f"**Dimensions:** {image.size[0]} x {image.size[1]}")
        st.write(f"**Format:** {image.format}")
    
    # Analysis button
    if st.button("🔮 Analyze Chart with AI", type="primary", use_container_width=True):
        
        with st.spinner("🤖 AI is analyzing your chart... This may take 10-30 seconds..."):
            
            analysis_settings = {
                'depth': analysis_depth,
                'horizon': trading_horizon,
                'sections': include_sections
            }
            
            result = analyze_chart_with_ai(image_bytes, analysis_settings)
            
            if result['success']:
                analysis = result['analysis']
                
                # Store in session state
                st.session_state['last_analysis'] = result
                st.session_state['analysis_text'] = analysis
                
                st.success("✅ Analysis Complete!")
                
                # Extract signals
                signals = extract_signals_from_analysis(analysis)
                
                # Display quick signals at top
                st.markdown("---")
                st.markdown("## 🎯 Quick Signals")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    sentiment_color = "🟢" if signals['sentiment'] == 'Bullish' else "🔴" if signals['sentiment'] == 'Bearish' else "🟡"
                    st.metric("Market Sentiment", f"{sentiment_color} {signals['sentiment']}")
                
                with col2:
                    st.metric("Confidence Level", signals['confidence'])
                
                with col3:
                    st.metric("Suggested Action", signals['action'])
                
                with col4:
                    st.metric("Key Metrics", len(signals['key_metrics']))
                
                # Display full analysis
                st.markdown("---")
                st.markdown("## 📊 Detailed Analysis")
                
                # Render the analysis in a nice format
                analysis_html = f"""
                <div class="analysis-box">
                    <h3 style="color: white; margin-top: 0;">🤖 AI Market Intelligence</h3>
                    <p style="color: white; opacity: 0.9; font-size: 0.9em;">
                        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
                        Model: Claude Sonnet 4 | 
                        Horizon: {trading_horizon}
                    </p>
                </div>
                """
                st.markdown(analysis_html, unsafe_allow_html=True)
                
                # Display analysis with markdown formatting
                st.markdown(analysis)
                
                # Download options
                st.markdown("---")
                st.markdown("### 💾 Export Analysis")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Text download
                    analysis_full = f"""
VOLATILITY CHART ANALYSIS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Analysis Depth: {analysis_depth}
Trading Horizon: {trading_horizon}

{'=' * 60}

{analysis}

{'=' * 60}

QUICK SIGNALS:
- Market Sentiment: {signals['sentiment']}
- Confidence Level: {signals['confidence']}
- Suggested Action: {signals['action']}
- Key Metrics: {', '.join(signals['key_metrics'])}

{'=' * 60}
Disclaimer: This analysis is for informational purposes only. 
Not financial advice. Always conduct your own research.
"""
                    st.download_button(
                        label="📄 Download as Text",
                        data=analysis_full,
                        file_name=f"volatility_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
                
                with col2:
                    # JSON download
                    json_data = {
                        'timestamp': datetime.now().isoformat(),
                        'filename': uploaded_file.name,
                        'analysis_settings': analysis_settings,
                        'signals': signals,
                        'full_analysis': analysis,
                        'metadata': result['metadata']
                    }
                    
                    st.download_button(
                        label="📊 Download as JSON",
                        data=json.dumps(json_data, indent=2),
                        file_name=f"volatility_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                
            else:
                st.error(f"❌ Analysis failed: {result['error']}")
                if 'details' in result:
                    with st.expander("Error Details"):
                        st.code(result['details'])

# Display previous analysis if available
elif 'last_analysis' in st.session_state:
    st.info("👆 Upload a new chart to analyze, or view your previous analysis below")
    
    with st.expander("📜 View Previous Analysis", expanded=True):
        st.markdown(st.session_state['analysis_text'])

# Help and examples section
else:
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 How It Works
        
        1. **Upload** a volatility chart screenshot
        2. **Configure** analysis settings in sidebar
        3. **Click** "Analyze Chart with AI"
        4. **Get** instant market intelligence
        
        ### 📊 Supported Charts
        
        - **CVOL Index** - Overall volatility level
        - **Skew/Skew Ratio** - Put/Call asymmetry
        - **Up/Down Variance** - Directional risk
        - **ATM Volatility** - At-the-money IV
        - **Volatility Surface** - Strike/time structure
        - **Multi-metric** - Combined views
        
        ### 🔍 What You'll Get
        
        - Market sentiment (bullish/bearish/neutral)
        - Risk metrics assessment
        - Trading signals and levels
        - Price expectations
        - Volatility structure analysis
        - Positioning insights
        - Historical context
        - Scenario analysis
        """)
    
    with col2:
        st.markdown("""
        ### 💡 Tips for Best Results
        
        **Chart Quality:**
        - Clear, high-resolution images
        - Visible axis labels and legends
        - Full chart view (not cropped)
        - Recent data preferred
        
        **Analysis Settings:**
        - Match horizon to your trading style
        - Select relevant sections
        - Use "Deep Dive" for complex charts
        - "Quick" for fast insights
        
        **Interpretation:**
        - Look for 🚨 extreme readings
        - Check for divergences
        - Compare to historical context
        - Consider multiple timeframes
        
        ### 🎓 Use Cases
        
        **For Traders:**
        - Pre-trade analysis
        - Position sizing
        - Risk management
        - Timing entries/exits
        
        **For Risk Managers:**
        - Portfolio risk assessment
        - Hedge effectiveness
        - Tail risk monitoring
        - Exposure management
        
        **For Analysts:**
        - Market structure analysis
        - Research and reports
        - Pattern recognition
        - Strategy development
        """)
    
    st.markdown("---")
    st.markdown("""
    ### 📝 Example Analysis Output
    
    After uploading your chart, you'll receive:
    """)
    
    example_output = """
    **CHART IDENTIFICATION**
    - EUR/USD CVOL History (6-month view)
    - Current CVOL: 0.96 🟢 (Below average)
    - Skew Ratio: 7.3 🚨 (EXTREME HIGH)
    
    **MARKET STRUCTURE**
    - Down Var & Up Var declining in tandem
    - Z-Score Divergence: Skew rising while volatility falls
    - **KEY INSIGHT**: Calm surface, hidden bearish positioning
    
    **WHAT MARKET IS PRICING**
    - 🔴 Bearish bias despite low volatility
    - Tail risk premium: Elevated
    - Expected range: Compressed near-term, wider 1-month
    
    **TRADING SIGNALS**
    - Signal: Mean reversion opportunity OR early warning
    - Strategy: Sell downside vol if confident, OR buy protection if cautious
    - Risk/Reward: Asymmetric to downside
    """
    
    st.markdown(f"""
    <div class="insight-card">
    {example_output}
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>🔮 AI Volatility Chart Analyzer | Powered by Claude Sonnet 4</p>
    <p><small>Upload chart → Get instant market intelligence → Make informed decisions</small></p>
    <p><small>⚠️ Disclaimer: For informational purposes only. Not financial advice.</small></p>
</div>
""", unsafe_allow_html=True)
