import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, maturity_months):
    maturity_years = maturity_months / 12  # Convert months to years
    forward_rate = spot_rate * np.exp((domestic_rate - foreign_rate) * maturity_years)
    return round(forward_rate, 4)

# Streamlit App
st.title("EUR/PLN Forward Calculator")

# File Upload
uploaded_file = st.file_uploader("Upload CSV or Excel file with dates and closing spot prices", type=["csv", "xlsx"])
if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        spot_data = pd.read_csv(uploaded_file)
    else:
        spot_data = pd.read_excel(uploaded_file)
    st.write("Uploaded Data:")
    st.dataframe(spot_data)
    spot_rate = spot_data.iloc[-1, 1]  # Assume last closing price as spot rate
else:
    spot_rate = st.number_input("Spot Rate (EUR/PLN)", value=4.21, format="%.4f")

domestic_rate = st.number_input("Domestic Risk-Free Rate (%)", value=5.0, format="%.2f") / 100
foreign_rate = st.number_input("Foreign Risk-Free Rate (%)", value=2.5, format="%.2f") / 100
notional = st.number_input("Notional Amount (EUR)", value=1000000, format="%.0f")
maturities = list(range(1, 13))

# Calculate forward rates
data = []
for m in maturities:
    forward_rate = calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, m)
    forward_points = round((forward_rate - spot_rate), 4)  # Forward points in pips
    data.append([m, forward_rate, forward_points])

df = pd.DataFrame(data, columns=["Maturity (Months)", "Forward Rate", "Forward Points (pips)"])

# Display table
st.write("### Forward Rates Table")
st.dataframe(df, hide_index=True)

# Plot forward rates
fig, ax = plt.subplots()
ax.plot(df["Maturity (Months)"], df["Forward Rate"], marker='o', linestyle='-')
ax.set_xlabel("Maturity (Months)")
ax.set_ylabel("Forward Rate (EUR/PLN)")
ax.set_title("EUR/PLN Forward Curve")
ax.grid(True)
st.pyplot(fig)
