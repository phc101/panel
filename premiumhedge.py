import streamlit as st
import pandas as pd
import numpy as np
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta

def initialize_session():
    if 'data' not in st.session_state:
        st.session_state['data'] = pd.DataFrame(columns=['Month', 'Currency', 'Inflow', 'Outflow', 'Net Exposure', 'Budget Rate', 'VaR 95% (%)', 'VaR 95% Nominal', 'VaR 99% (%)', 'VaR 99% Nominal', 'Forward Rate'])

def fetch_live_forward_rates(currency):
    """
    Fetch live forward rates for EUR/PLN and USD/PLN from FactSet API with correct authentication.
    """
    factset_username = "YOUR_FACTSET_USERNAME"  # Replace with your FactSet username
    factset_password = "YOUR_FACTSET_PASSWORD"  # Replace with your FactSet password
    url = "https://api.factset.com/content/fx/v1/forwards"
    
    payload = {
        "ids": [f"{currency}PLN"],
        "fields": ["mid", "1M", "2M", "3M", "6M", "12M"]
    }
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Debugging: Print request details
    st.write("Requesting forward rates from FactSet API:", payload)
    response = requests.post(url, headers=headers, json=payload, auth=HTTPBasicAuth(factset_username, factset_password))
    
    if response.status_code == 200:
        data = response.json()
        st.write("API Response:", data)  # Debugging output
        
        try:
            forward_rates = {tenor: data["data"][0][tenor] for tenor in ["1M", "2M", "3M", "6M", "12M"]}
            return forward_rates
        except (KeyError, IndexError):
            st.error("Unexpected API response format. Check API documentation.")
            st.write("Response Data:", data)
            return {}
    else:
        st.error(f"Failed to fetch live forward rates. Status Code: {response.status_code}")
        st.write("Response Text:", response.text)  # Debugging output
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
        forward_mapping = {"1M": 0, "2M": 1, "3M": 2, "6M": 5, "12M": 11}
        for tenor, idx in forward_mapping.items():
            if tenor in forward_rates:
                st.session_state['data'].at[idx, 'Forward Rate'] = forward_rates[tenor]
        
        st.subheader("Live Forward Rates from FactSet API")
        st.dataframe(st.session_state['data'][['Month', 'Forward Rate']])
    else:
        st.error("Failed to fetch live forward rates.")
    
    if not st.session_state['data'].empty:
        st.subheader("Updated Expected Flows with Forward Rates")
        st.dataframe(st.session_state['data'])

if __name__ == "__main__":
    main()
