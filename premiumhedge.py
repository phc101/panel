import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, maturity_months):
    maturity_years = maturity_months / 12  # Convert months to years
    if spot_rate is None or np.isnan(spot_rate):
        return None
    forward_rate = spot_rate * np.exp((domestic_rate - foreign_rate) * maturity_years)
    return round(forward_rate, 4)

# Streamlit App
st.title("EUR/PLN Forward Calculator")

# File Upload
uploaded_file = st.file_uploader("Upload CSV or Excel file with dates and closing spot prices", type=["csv", "xlsx"])
spot_rate = None
spot_data = None

date_selected = None
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            spot_data = pd.read_csv(uploaded_file, parse_dates=[0], dayfirst=True)
        else:
            spot_data = pd.read_excel(uploaded_file, parse_dates=[0], dayfirst=True)
        
        spot_data.columns = ["Date", "Close"]  # Ensure correct column names
        st.write("Uploaded Data:")
        st.dataframe(spot_data)
        
        # Date selection
        date_selected = st.selectbox("Select Start Date for Forward Strip", spot_data["Date"])
        spot_rate = spot_data.loc[spot_data["Date"] == date_selected, "Close"].values[0]
    except Exception as e:
        st.error(f"Error reading file: {e}")

# Fallback if file not uploaded or invalid
if spot_rate is None or np.isnan(spot_rate):
    spot_rate = st.number_input("Spot Rate (EUR/PLN)", value=4.21, format="%.4f")

domestic_rate = st.number_input("Domestic Risk-Free Rate (%)", value=5.0, format="%.2f") / 100
foreign_rate = st.number_input("Foreign Risk-Free Rate (%)", value=2.5, format="%.2f") / 100
notional = st.number_input("Notional Amount (EUR)", value=1000000, format="%.0f")
maturities = list(range(1, 13))

# Calculate forward rates
data = []
for m in maturities:
    forward_rate = calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, m)
    if forward_rate is not None:
        forward_points = round((forward_rate - spot_rate), 4)  # Forward points in 0.0000 format
        data.append([m, forward_rate, forward_points])

df = pd.DataFrame(data, columns=["Maturity (Months)", "Forward Rate", "Forward Points"])

# Display table
st.write("### Forward Rates Table")
st.dataframe(df, hide_index=True)

# Settlement against each forward
if spot_data is not None:
    settlement_data = []
    for m, fwd_rate in zip(maturities, df["Forward Rate"]):
        settlement_date = date_selected + pd.DateOffset(months=m)
        actual_spot = spot_data.loc[spot_data["Date"] == settlement_date, "Close"].values[0] if settlement_date in spot_data["Date"].values else None
        settlement_result = (actual_spot - fwd_rate) * notional if actual_spot is not None else None
        settlement_data.append([settlement_date, fwd_rate, actual_spot, settlement_result])
    
    settlement_df = pd.DataFrame(settlement_data, columns=["Settlement Date", "Forward Rate", "Actual Spot", "Net Settlement Result"])
    st.write("### Settlement Results")
    st.dataframe(settlement_df, hide_index=True)

# Plot forward rates
if not df.empty:
    fig, ax = plt.subplots()
    ax.plot(df["Maturity (Months)"], df["Forward Rate"], marker='o', linestyle='-')
    ax.set_xlabel("Maturity (Months)")
    ax.set_ylabel("Forward Rate (EUR/PLN)")
    ax.set_title("EUR/PLN Forward Curve")
    ax.grid(True)
    st.pyplot(fig)
