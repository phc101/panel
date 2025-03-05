import streamlit as st
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
import numpy as np

st.title("EUR/PLN Real Value Analysis Based on Yield Spread")

# File uploaders
eurpln_file = st.file_uploader("Upload EUR/PLN Historical Data CSV", type=["csv"])
germany_yield_file = st.file_uploader("Upload Germany 2Y Yield CSV", type=["csv"])
poland_yield_file = st.file_uploader("Upload Poland 2Y Yield CSV", type=["csv"])

if eurpln_file and germany_yield_file and poland_yield_file:
    # Load the data
    eur_pln_data = pd.read_csv(eurpln_file)
    german_yield_data = pd.read_csv(germany_yield_file)
    polish_yield_data = pd.read_csv(poland_yield_file)
    
    # Standardize column names
eur_pln_data.columns = ["Date", "Close", "Open", "High", "Low", "Volume", "Change"]
    german_yield_data.columns = ["Date", "Yield_Germany", "Open_Germany", "High_Germany", "Low_Germany", "Change_Germany"]
    polish_yield_data.columns = ["Date", "Yield_Poland", "Open_Poland", "High_Poland", "Low_Poland", "Change_Poland"]

    # Convert Date to datetime format
    eur_pln_data["Date"] = pd.to_datetime(eur_pln_data["Date"], format="%d.%m.%Y")
    german_yield_data["Date"] = pd.to_datetime(german_yield_data["Date"], format="%d.%m.%Y")
    polish_yield_data["Date"] = pd.to_datetime(polish_yield_data["Date"], format="%d.%m.%Y")

    # Convert numerical values
    eur_pln_data["Close"] = eur_pln_data["Close"].str.replace(",", ".").astype(float)
    german_yield_data["Yield_Germany"] = german_yield_data["Yield_Germany"].str.replace(",", ".").astype(float)
    polish_yield_data["Yield_Poland"] = polish_yield_data["Yield_Poland"].str.replace(",", ".").astype(float)
    
    # Merge datasets
    merged_data = eur_pln_data.merge(german_yield_data, on="Date", how="inner").merge(polish_yield_data, on="Date", how="inner")
    
    # Calculate yield spread
    merged_data["Yield_Spread"] = merged_data["Yield_Poland"] - merged_data["Yield_Germany"]
    
    # Regression model to estimate real EUR/PLN
    X = sm.add_constant(merged_data["Yield_Spread"])
    y = merged_data["Close"]
    model = sm.OLS(y, X).fit()
    
    # Predict real EUR/PLN
    merged_data["Real_EURPLN"] = model.predict(X)
    
    # Plot actual vs real EUR/PLN
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(merged_data["Date"], merged_data["Close"], label="Actual EUR/PLN", color="blue")
    ax.plot(merged_data["Date"], merged_data["Real_EURPLN"], label="Real EUR/PLN (Based on Spread)", color="red", linestyle="dashed")
    ax.set_xlabel("Date")
    ax.set_ylabel("Exchange Rate")
    ax.set_title("Actual vs. Real EUR/PLN Based on Yield Spread")
    ax.legend()
    ax.grid()
    st.pyplot(fig)
    
    # Interpretation of the current state
    current_eurpln = merged_data.iloc[-1]["Close"]
    current_real_eurpln = merged_data.iloc[-1]["Real_EURPLN"]
    difference = current_eurpln - current_real_eurpln
    
    if difference > 0:
        direction = "above"
    else:
        direction = "below"
    
    # Estimating the time to reach the real value
    recent_differences = abs(merged_data["Close"] - merged_data["Real_EURPLN"]).rolling(window=5).mean()
    avg_adjustment_speed = recent_differences.mean()
    estimated_days = abs(difference) / avg_adjustment_speed if avg_adjustment_speed > 0 else "unknown"
    
    st.write(f"EUR/PLN is currently at {current_eurpln:.4f}, which is {direction} its real value at {current_real_eurpln:.4f}.")
    st.write(f"It will probably take approximately {estimated_days:.0f} days to reach its real value.")
