# Install alpha_vantage if not already installed
import subprocess
import sys

def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except Exception as e:
        print(f"Error installing {package}: {e}")

install_package("alpha_vantage")

# Verify installation
try:
    from alpha_vantage.foreignexchange import ForeignExchange
    from alpha_vantage.timeseries import TimeSeries
    print("alpha_vantage is installed and ready to use.")
except ImportError:
    print("Failed to import alpha_vantage. Please check the installation.")

# Now include the rest of your script
import numpy as np
import streamlit as st
from scipy.stats import norm

# Alpha Vantage API Key
API_KEY = "YOUR_ALPHA_VANTAGE_API_KEY"

# Initialize Alpha Vantage Clients
fx = ForeignExchange(key=API_KEY)
ts = TimeSeries(key=API_KEY, output_format="pandas")

# Rest of the code goes here...
