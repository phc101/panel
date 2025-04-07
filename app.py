import streamlit as st

st.set_page_config(
    page_title="Internal Treasury System",
    page_icon="💰",
    layout="wide"
)

st.title("💼 Internal Treasury System")

st.markdown("""
Welcome to your custom treasury dashboard.  
Use the menu on the left to navigate between:
- Clients
- Payments
- FX Exposure
- Hedging
- Reports
""")
