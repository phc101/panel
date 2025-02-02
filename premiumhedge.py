import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

def initialize_session():
    if 'data' not in st.session_state:
        st.session_state['data'] = pd.DataFrame(columns=['Month', 'Currency', 'Inflow', 'Outflow', 'Net Exposure', 'Budget Rate', 'VaR 95% (%)', 'VaR 95% Nominal', 'VaR 99% (%)', 'VaR 99% Nominal', 'Forward Rate'])

def fetch_exchange_rates(currency_code, start_date, end_date):
    """
    Fetch historical exchange rates for a given currency against PLN from the NBP API.
    """
    url = f'https://api.nbp.pl/api/exchangerates/rates/a/{currency_code}/{start_date}/{end_date}/?format=json'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        rates = pd.DataFrame(data['rates'])
        rates['date'] = pd.to_datetime(rates['effectiveDate'])
        rates.set_index('date', inplace=True)
        rates.rename(columns={'mid': f'{currency_code}_PLN'}, inplace=True)
        rates['returns'] = np.log(rates[f'{currency_code}_PLN'] / rates[f'{currency_code}_PLN'].shift(1))
        rates.dropna(inplace=True)
        return rates
    else:
        return pd.DataFrame()

def fetch_interest_rates():
    """
    Fetches domestic (PLN) and foreign (EUR/USD) interest rates.
    """
    return {'PLN': 0.05, 'EUR': 0.03, 'USD': 0.04}  # Example static rates

def calculate_forward_rates():
    """
    Calculate forward rates based on interest rate parity formula, accounting for net exposure.
    """
    if 'data' in st.session_state and not st.session_state['data'].empty and 'spot_rate' in st.session_state:
        spot_rate = st.session_state['spot_rate']
        interest_rates = st.session_state.get('interest_rates', fetch_interest_rates())
        
        for month in range(1, 13):
            T = month / 12  # Convert months to years
            currency = st.session_state['data'].at[month-1, 'Currency']
            net_exposure = st.session_state['data'].at[month-1, 'Inflow'] - st.session_state['data'].at[month-1, 'Outflow']
            
            if net_exposure > 0:
                # Exporter (selling foreign currency, buying PLN)
                r_domestic = interest_rates['PLN']
                r_foreign = interest_rates[currency]
            else:
                # Importer (buying foreign currency, selling PLN)
                r_domestic = interest_rates[currency]
                r_foreign = interest_rates['PLN']
            
            forward_rate = spot_rate * ((1 + r_foreign * T) / (1 + r_domestic * T))
            st.session_state['data'].at[month-1, 'Forward Rate'] = round(forward_rate, 4)
            st.session_state['data'].at[month-1, 'Net Exposure'] = net_exposure

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
        spot_rate = rates[f'{currency}_PLN'].iloc[-1]  # Latest exchange rate
        st.session_state['spot_rate'] = spot_rate
        
        calculate_forward_rates()
        
        st.subheader(f"Calculated Forward Rates (Based on Spot {spot_rate:.4f})")
        st.dataframe(st.session_state['data'][['Month', 'Net Exposure', 'Forward Rate']])
        
        min_price = 4.15
        max_price = 4.40
        scaled_rates = rates[[f'{currency}_PLN']].clip(lower=min_price, upper=max_price)
        
        st.line_chart(scaled_rates.rename(columns={f'{currency}_PLN': 'Exchange Rate'}), use_container_width=True, height=400)
        st.line_chart(rates[['returns']].rename(columns={'returns': 'Daily Returns'}), use_container_width=True, height=400)
    else:
        st.error("No exchange rate data available for the selected currency and date range.")
    
    if not st.session_state['data'].empty:
        st.subheader("Updated Expected Flows with Forward Rates")
        st.dataframe(st.session_state['data'])

if __name__ == "__main__":
    main()
