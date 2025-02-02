import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

def initialize_session():
    if 'data' not in st.session_state:
        st.session_state['data'] = pd.DataFrame(columns=['Month', 'Currency', 'Inflow', 'Outflow', 'Net Exposure', 'Budget Rate', 'VaR 95% (%)', 'VaR 95% Nominal', 'VaR 99% (%)', 'VaR 99% Nominal', 'Forward Rate'])

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
    
    input_interest_rates()
    input_expected_flows()
    
    if not st.session_state['data'].empty:
        st.subheader("Saved Expected Flows")
        st.dataframe(st.session_state['data'])
    
    end_date = datetime.today()
    start_date = end_date - timedelta(days=365)
    currency = "EUR" if "EUR" in st.session_state['data']['Currency'].unique() else "USD"
    rates = fetch_exchange_rates(currency, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    
    if not rates.empty:
        spot_rate = rates[f'{currency}_PLN'].iloc[-1]
        st.session_state['spot_rate'] = spot_rate
        st.session_state['returns'] = rates['returns']
        
        calculate_forward_rates()
        calculate_risk()
        
        st.subheader(f"Calculated Forward Rates (Based on Spot {spot_rate:.4f})")
        st.dataframe(st.session_state['data'][['Month', 'Net Exposure', 'Forward Rate', 'VaR 95% Nominal', 'VaR 99% Nominal']])
        
        min_price = 4.15
        max_price = 4.40
        scaled_rates = rates[[f'{currency}_PLN']].clip(lower=min_price, upper=max_price)
        
        st.line_chart(scaled_rates.rename(columns={f'{currency}_PLN': 'Exchange Rate'}), use_container_width=True, height=400)
        st.line_chart(rates[['returns']].rename(columns={'returns': 'Daily Returns'}), use_container_width=True, height=400)
    else:
        st.error("No exchange rate data available for the selected currency and date range.")
    
    if not st.session_state['data'].empty:
        st.subheader("Updated Expected Flows with Forward Rates and VaR")
        st.dataframe(st.session_state['data'])

if __name__ == "__main__":
    main()
