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
    Fetch live forward rates for EUR/PLN and USD/PLN from Twelve Data API.
    """
    twelve_api_key = "25dd798d5907450bb70a17ed8c6c4f89"
    url = f"https://api.twelvedata.com/forex_forwards"
    
    params = {
        "symbol": f"{currency}/PLN",
        "apikey": twelve_api_key
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        st.write("API Response:", data)  # Debugging output
        
        try:
            forward_rates = {str(i+1): round(float(data["values"][i]["close"], 4)) for i in range(12)}
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
        for i in range(12):
            st.session_state['data'].at[i, 'Forward Rate'] = forward_rates[str(i+1)]
        
        st.subheader("Live Forward Rates from Twelve Data API")
        st.dataframe(st.session_state['data'][['Month', 'Forward Rate']])
    else:
        st.error("Failed to fetch live forward rates.")
    
    if not st.session_state['data'].empty:
        st.subheader("Updated Expected Flows with Forward Rates")
        st.dataframe(st.session_state['data'])

if __name__ == "__main__":
    main()
