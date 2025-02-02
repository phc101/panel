import streamlit as st
import pandas as pd
import numpy as np

def initialize_session():
    if 'data' not in st.session_state:
        st.session_state['data'] = pd.DataFrame(columns=['Month', 'Currency', 'Inflow', 'Outflow', 'Budget Rate'])

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
    
    # Display saved data
    if not st.session_state['data'].empty:
        st.subheader("Saved Expected Flows")
        st.dataframe(st.session_state['data'])

if __name__ == "__main__":
    main()
