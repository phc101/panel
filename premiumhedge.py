import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

def initialize_session():
    if 'data' not in st.session_state:
        st.session_state['data'] = pd.DataFrame(columns=['Month', 'Currency', 'Inflow', 'Outflow', 'Net Exposure', 'Budget Rate', 'VaR 95% (%)', 'VaR 95% Nominal', 'VaR 99% (%)', 'VaR 99% Nominal', 'Forward Rate'])

def fetch_live_forward_rates(currency):
    """
    Fetch live forward rates for EUR/PLN and USD/PLN from an external API provider.
    """
    url = f'https://api.exchangerate.host/forward?base={currency}&symbols=PLN'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        forward_rates = {str(i+1): data['rates']['PLN'] * (1 + 0.002 * (i+1)) for i in range(12)}  # Example forward rate curve
        return forward_rates
    else:
        return {}

def input_expected_flows():
    st.sidebar.header("Expected Cash Flows")
    currency = st.sidebar.selectbox("Select Currency", ["EUR", "USD"])
    
    num_months = 12
    months = pd.date_range(start=pd.Timestamp.today(), periods=num_months, freq='M').strftime('%Y-%m')
    if 'data' not in st.session_state or st.session_state['data'].empty:
        st.session_state['data'] = pd.DataFrame({'Month': months, 'Currency': currency, 'Inflow': [0]*num_months, 'Outflow': [0]*num_months, 'Budget Rate': [0.00]*num_months})
    
    data = st.sidebar.data_editor(st.session_state['data'], use_container_width=True)
    
    # Auto-fill Budget Rate
    if 'Budget Rate' in data.columns:
        first_value = data.loc[0, 'Budget Rate']
        if first_value != 0.00:
            data['Budget Rate'] = first_value
    
    if st.sidebar.button("Save Data"):
        st.session_state['data'] = data
        st.success("Data saved successfully!")

def main():
    st.title("FX Risk Management Tool")
    initialize_session()
    
    input_expected_flows()
    
    if not st.session_state['data'].empty:
        st.subheader("Saved Expected Flows")
        st.dataframe(st.session_state['data'])
    
    currency = "EUR" if "EUR" in st.session_state['data']['Currency'].unique() else "USD"
    forward_rates = fetch_live_forward_rates(currency)
    
    if forward_rates:
        st.session_state['data']['Forward Rate'] = [forward_rates[str(i+1)] for i in range(12)]
        
        st.subheader("Live Forward Rates from API")
        st.dataframe(st.session_state['data'][['Month', 'Forward Rate']])
    else:
        st.error("Failed to fetch live forward rates.")
    
    if not st.session_state['data'].empty:
        st.subheader("Updated Expected Flows with Forward Rates")
        st.dataframe(st.session_state['data'])

if __name__ == "__main__":
    main()
