import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

def initialize_session():
    if 'data' not in st.session_state:
        st.session_state['data'] = pd.DataFrame(columns=['Month', 'Currency', 'Inflow', 'Outflow', 'Net Exposure', 'Budget Rate', 'VaR 95% (%)', 'VaR 95% Nominal', 'VaR 99% (%)', 'VaR 99% Nominal', 'Forward Rate'])

def input_interest_rates():
    st.sidebar.header("Interest Rates")
    pln_rate = st.sidebar.number_input("Domestic (PLN) Interest Rate", min_value=0.0, max_value=1.0, value=0.05, step=0.001)
    eur_rate = st.sidebar.number_input("Foreign (EUR) Interest Rate", min_value=0.0, max_value=1.0, value=0.03, step=0.001)
    usd_rate = st.sidebar.number_input("Foreign (USD) Interest Rate", min_value=0.0, max_value=1.0, value=0.04, step=0.001)
    
    st.session_state['interest_rates'] = {'PLN': pln_rate, 'EUR': eur_rate, 'USD': usd_rate}

def calculate_var(returns, horizon, confidence_level):
    if len(returns) == 0:
        return np.nan
    sorted_returns = np.sort(returns)
    index = int((1 - confidence_level) * len(sorted_returns))
    daily_var = abs(sorted_returns[index])
    return daily_var * np.sqrt(horizon)

def calculate_risk():
    if 'data' in st.session_state and not st.session_state['data'].empty and 'returns' in st.session_state:
        total_var_95_nominal = 0
        total_var_99_nominal = 0
        
        for month in range(1, 13):
            var_95 = calculate_var(st.session_state['returns'], horizon=month, confidence_level=0.95)
            var_99 = calculate_var(st.session_state['returns'], horizon=month, confidence_level=0.99)
            nominal_95 = abs(st.session_state['data'].at[month-1, 'Net Exposure'] * var_95)
            nominal_99 = abs(st.session_state['data'].at[month-1, 'Net Exposure'] * var_99)
            
            st.session_state['data'].at[month-1, 'VaR 95% (%)'] = var_95 * 100
            st.session_state['data'].at[month-1, 'VaR 95% Nominal'] = nominal_95
            st.session_state['data'].at[month-1, 'VaR 99% (%)'] = var_99 * 100
            st.session_state['data'].at[month-1, 'VaR 99% Nominal'] = nominal_99
            
            total_var_95_nominal += nominal_95
            total_var_99_nominal += nominal_99
        
        st.subheader("Total Nominal VaR")
        st.write(f"Total 95% Confidence Level VaR: {total_var_95_nominal:.2f}")
        st.write(f"Total 99% Confidence Level VaR: {total_var_99_nominal:.2f}")
        st.write(f"Your maximum amount to lose in the next 12 months is {total_var_99_nominal:.2f} at 99% confidence.")

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
