import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

def initialize_session():
    if 'data' not in st.session_state:
        st.session_state['data'] = pd.DataFrame(columns=['Month', 'Currency', 'Inflow', 'Outflow', 'Budget Rate', 'VaR 95% (%)', 'VaR 95% Nominal', 'VaR 99% (%)', 'VaR 99% Nominal'])

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
        return rates
    else:
        return pd.DataFrame()

def calculate_var(returns, horizon, confidence_level):
    """
    Calculate the Value at Risk (VaR) for different time horizons.
    """
    if len(returns) == 0:
        return np.nan
    sorted_returns = np.sort(returns)
    index = int((1 - confidence_level) * len(sorted_returns))
    daily_var = abs(sorted_returns[index])
    return daily_var * np.sqrt(horizon)

def input_expected_flows():
    st.sidebar.header("Expected Cash Flows")
    currency = st.sidebar.selectbox("Select Currency", ["EUR", "USD"])
    
    # Data Input Table
    num_months = 12
    months = pd.date_range(start=pd.Timestamp.today(), periods=num_months, freq='M').strftime('%Y-%m')
    if 'data' not in st.session_state or st.session_state['data'].empty:
        st.session_state['data'] = pd.DataFrame({'Month': months, 'Currency': currency, 'Inflow': [0]*num_months, 'Outflow': [0]*num_months, 'Budget Rate': [0.00]*num_months, 'VaR 95% (%)': [0.00]*num_months, 'VaR 95% Nominal': [0.00]*num_months, 'VaR 99% (%)': [0.00]*num_months, 'VaR 99% Nominal': [0.00]*num_months})
    
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
    
    # Fetch historical data
    end_date = datetime.today()
    start_date = end_date - timedelta(days=365)
    currency = "EUR" if "EUR" in st.session_state['data']['Currency'].unique() else "USD"
    rates = fetch_exchange_rates(currency, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    
    if not rates.empty:
        rates['returns'] = np.log(rates[f'{currency}_PLN'] / rates[f'{currency}_PLN'].shift(1))
        rates.dropna(inplace=True)
        
        # Calculate VaR for different horizons at 95% and 99%
        total_var_95_nominal = 0
        total_var_99_nominal = 0
        
        for month in range(1, 13):
            var_95 = calculate_var(rates['returns'], horizon=month, confidence_level=0.95)
            var_99 = calculate_var(rates['returns'], horizon=month, confidence_level=0.99)
            nominal_95 = abs((st.session_state['data'].at[month-1, 'Inflow'] - st.session_state['data'].at[month-1, 'Outflow']) * var_95)
            nominal_99 = abs((st.session_state['data'].at[month-1, 'Inflow'] - st.session_state['data'].at[month-1, 'Outflow']) * var_99)
            
            st.session_state['data'].at[month-1, 'VaR 95% (%)'] = var_95 * 100
            st.session_state['data'].at[month-1, 'VaR 95% Nominal'] = nominal_95
            st.session_state['data'].at[month-1, 'VaR 99% (%)'] = var_99 * 100
            st.session_state['data'].at[month-1, 'VaR 99% Nominal'] = nominal_99
            
            total_var_95_nominal += nominal_95
            total_var_99_nominal += nominal_99
        
        num_cashflow_months = len(st.session_state['data'])
        st.subheader("Total Nominal VaR")
        st.write(f"Total 95% Confidence Level VaR: {total_var_95_nominal:.2f} {currency}")
        st.write(f"Total 99% Confidence Level VaR: {total_var_99_nominal:.2f} {currency}")
        st.write(f"Your maximum amount to lose in the next {num_cashflow_months} months is {total_var_99_nominal:.2f} {currency} at 99% confidence.")
        
        # Fixing chart scaling
        min_price = 4.15
        max_price = 4.40
        scaled_rates = rates[[f'{currency}_PLN']].clip(lower=min_price, upper=max_price)
        
        st.line_chart(scaled_rates.rename(columns={f'{currency}_PLN': 'Exchange Rate'}), use_container_width=True, height=400)
        st.line_chart(rates[['returns']].rename(columns={'returns': 'Daily Returns'}), use_container_width=True, height=400)
    else:
        st.error("No exchange rate data available for the selected currency and date range.")
    
    # Display updated data with VaR
    if not st.session_state['data'].empty:
        st.subheader("Updated Expected Flows with VaR")
        st.dataframe(st.session_state['data'])

if __name__ == "__main__":
    main()
