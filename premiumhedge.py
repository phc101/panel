import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

def initialize_session():
    if 'data' not in st.session_state:
        st.session_state['data'] = pd.DataFrame(columns=['Month', 'Currency', 'Inflow', 'Outflow', 'Budget Rate'])

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

def calculate_var(returns, confidence_level=0.95):
    """
    Calculate the Value at Risk (VaR) using the historical method.
    """
    if len(returns) == 0:
        return np.nan
    sorted_returns = np.sort(returns)
    index = int((1 - confidence_level) * len(sorted_returns))
    return abs(sorted_returns[index])

def input_expected_flows():
    st.sidebar.header("Expected Cash Flows")
    currency = st.sidebar.selectbox("Select Currency", ["EUR", "USD"])
    
    # Data Input Table
    num_months = 12
    months = pd.date_range(start=pd.Timestamp.today(), periods=num_months, freq='M').strftime('%Y-%m')
    data = pd.DataFrame({'Month': months, 'Currency': currency, 'Inflow': [0]*num_months, 'Outflow': [0]*num_months, 'Budget Rate': [0.00]*num_months})
    
    data = st.sidebar.data_editor(data, use_container_width=True)
    
    # Auto-fill Budget Rate
    if 'Budget Rate' in data.columns:
        first_value = data.loc[0, 'Budget Rate']
        if first_value != 0.00:
            data['Budget Rate'] = first_value
    
    if st.sidebar.button("Save Data"):
        st.session_state['data'] = data
        st.success("Data saved successfully!")
    
    # CSV Upload Description
    st.sidebar.markdown("**Upload CSV Format:**")
    st.sidebar.text("Month (YYYY-MM), Currency (EUR/USD), Inflow, Outflow, Budget Rate")
    st.sidebar.text("Example:")
    st.sidebar.text("2025-01, EUR, 10000, 5000, 4.30")
    
    # Upload CSV Option
    uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=['csv'])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.session_state['data'] = df
        st.success("CSV uploaded successfully!")

def main():
    st.title("FX Risk Management Tool")
    initialize_session()
    input_expected_flows()
    
    # Fetch historical data
    end_date = datetime.today()
    start_date = end_date - timedelta(days=365)
    currency = "EUR" if "EUR" in st.session_state['data']['Currency'].unique() else "USD"
    rates = fetch_exchange_rates(currency, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    
    if not rates.empty:
        rates['returns'] = np.log(rates[f'{currency}_PLN'] / rates[f'{currency}_PLN'].shift(1))
        rates.dropna(inplace=True)
        var_95 = calculate_var(rates['returns'], confidence_level=0.95)
        
        st.subheader(f"Value at Risk (VaR) for {currency}/PLN")
        st.write(f"With a 95% confidence level, the maximum expected daily loss is {var_95*100:.2f}%.")
        
        st.line_chart(rates[[f'{currency}_PLN']])
        st.line_chart(rates[['returns']])
    else:
        st.error("No exchange rate data available for the selected currency and date range.")

if __name__ == "__main__":
    main()
