import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Streamlit UI setup
st.title("FX Valuation & Backtesting Tool")

# Upload CSV files
st.sidebar.header("Upload Data")
currency_file = st.sidebar.file_uploader("Upload Currency Pair Data (CSV)", type=["csv"])
domestic_yield_file = st.sidebar.file_uploader("Upload Domestic Bond Yield Data (CSV)", type=["csv"])
foreign_yield_file = st.sidebar.file_uploader("Upload Foreign Bond Yield Data (CSV)", type=["csv"])

if currency_file and domestic_yield_file and foreign_yield_file:
    try:
        # Load Data
        currency_data = pd.read_csv(currency_file)
        domestic_yield = pd.read_csv(domestic_yield_file)
        foreign_yield = pd.read_csv(foreign_yield_file)
        
        # Show detected column names for debugging
        st.subheader("Column Names in Uploaded Files")
        st.write("Currency Data Columns:", currency_data.columns.tolist())
        st.write("Domestic Yield Data Columns:", domestic_yield.columns.tolist())
        st.write("Foreign Yield Data Columns:", foreign_yield.columns.tolist())
        
    except Exception as e:
        st.error(f"An error occurred: {e}")
