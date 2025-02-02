import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

def initialize_session():
    if 'data' not in st.session_state:
        st.session_state['data'] = pd.DataFrame(columns=['Month', 'Currency', 'Inflow', 'Outflow', 'Budget Rate', 'VaR 95% (%)', 'VaR 95% Nominal', 'VaR 99% (%)', 'VaR 99% Nominal', 'Forward Rate'])

def fetch_interest_rates():
    """
    Fetches domestic (PLN) and foreign (EUR/USD) interest rates.
    This function can be modified to pull data from an API or accept user input.
    """
    return {'PLN': 0.05, 'EUR': 0.03, 'USD': 0.04}  # Example static rates

def calculate_forward_rates():
    """
    Calculate forward rates based on interest rate parity formula.
    """
    if 'data' in st.session_state and not st.session_state['data'].empty:
        spot_rate = st.session_state['spot_rate']
        interest_rates = fetch_interest_rates()
        
        for month in range(1, 13):
            T = month / 12  # Convert months to years
            currency = st.session_state['data'].at[month-1, 'Currency']
            r_domestic = interest_rates['PLN']
            r_foreign = interest_rates[currency]
            
            forward_rate = spot_rate * ((1 + r_foreign * T) / (1 + r_domestic * T))
            st.session_state['data'].at[month-1, 'Forward Rate'] = round(forward_rate, 4)

def input_interest_rates():
    st.sidebar.header("Interest Rates")
    pln_rate = st.sidebar.number_input("Domestic (PLN) Interest Rate", min_value=0.0, max_value=1.0, value=0.05, step=0.001)
    eur_rate = st.sidebar.number_input("Foreign (EUR) Interest Rate", min_value=0.0, max_value=1.0, value=0.03, step=0.001)
    usd_rate = st.sidebar.number_input("Foreign (USD) Interest Rate", min_value=0.0, max_value=1.0, value=0.04, step=0.001)
    
    st.session_state['interest_rates'] = {'PLN': pln_rate, 'EUR': eur_rate, 'USD': usd_rate}

def main():
    st.title("FX Risk Management Tool")
    initialize_session()
    input_interest_rates()
    input_expected_flows()
    
    if not st.session_state['data'].empty:
        st.subheader("Saved Expected Flows")
        st.dataframe(st.session_state['data'])
    
    # Fetch historical spot rate (latest exchange rate)
    end_date = datetime.today()
    start_date = end_date - timedelta(days=365)
    currency = "EUR" if "EUR" in st.session_state['data']['Currency'].unique() else "USD"
    rates = fetch_exchange_rates(currency, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    
    if not rates.empty:
        spot_rate = rates[f'{currency}_PLN'].iloc[-1]  # Latest exchange rate
        st.session_state['spot_rate'] = spot_rate
        
        calculate_forward_rates()
        
        st.subheader(f"Calculated Forward Rates (Based on Spot {spot_rate:.4f})")
        st.dataframe(st.session_state['data'][['Month', 'Forward Rate']])
        
        # Fixing chart scaling
        min_price = 4.15
        max_price = 4.40
        scaled_rates = rates[[f'{currency}_PLN']].clip(lower=min_price, upper=max_price)
        
        st.line_chart(scaled_rates.rename(columns={f'{currency}_PLN': 'Exchange Rate'}), use_container_width=True, height=400)
        st.line_chart(rates[['returns']].rename(columns={'returns': 'Daily Returns'}), use_container_width=True, height=400)
    else:
        st.error("No exchange rate data available for the selected currency and date range.")
    
    # Display updated data with Forward Rates
    if not st.session_state['data'].empty:
        st.subheader("Updated Expected Flows with Forward Rates")
        st.dataframe(st.session_state['data'])

if __name__ == "__main__":
    main()
