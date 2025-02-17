import pandas as pd
import numpy as np
import streamlit as st

# ---------------------- User Inputs ---------------------- #
st.title("Automatic FX Hedging System")

# User selects if they are an Exporter or Importer
user_type = st.radio("Select Business Type:", ["Exporter", "Importer"], horizontal=True)

# Input expected FX flows using a 4x3 grid layout
st.write("### Expected FX Flows (12-Month View)")
cols = st.columns(4)
data = []
num_months = 12  # Default to 12-month hedging horizon

for i in range(num_months):
    with cols[i % 4]:
        amount = st.number_input(f"Month {i+1}", value=100000, step=10000, key=f"flow_{i+1}")
        data.append(amount)

df = pd.DataFrame({"Month": range(1, num_months + 1), "Expected FX Flow": data})

# User-defined budget rate and hedging limits
budget_rate = st.number_input("Enter Budget Rate (EUR/PLN):", value=4.40, step=0.01)
if user_type == "Importer":
    max_hedge_price = st.number_input("Set Max Hedge Price (No Forward Hedge Above):", value=4.35, step=0.01)
if user_type == "Exporter":
    min_hedge_price = st.number_input("Set Min Hedge Price (No Forward Hedge Below):", value=4.25, step=0.01)

# Hedge ratio selection per month using a 4x3 grid layout
st.write("### Hedge Ratios (12-Month View)")
cols = st.columns(4)
hedge_ratios = []

for i in range(num_months):
    with cols[i % 4]:
        ratio = st.slider(f"Month {i+1}", min_value=0, max_value=100, value=75, key=f"hedge_{i+1}")
        hedge_ratios.append(ratio / 100)

df["Hedge Ratio"] = hedge_ratios

# ---------------------- Market Data & Forward Pricing ---------------------- #
# Mock spot rate and forward rate (to be integrated with real API later)
spot_rate = st.number_input("Current Spot Rate (EUR/PLN):", value=4.38, step=0.01)
forward_points = st.number_input("Forward Points (Annualized %):", value=0.91, step=0.01) / 100

# Compute forward rates for different tenors
forward_rates = [spot_rate * (1 + forward_points * (i / 12)) for i in range(1, num_months + 1)]
df["Forward Rate"] = forward_rates

# ---------------------- Hedge Execution Logic ---------------------- #
def calculate_hedge(df, user_type, max_hedge_price=None, min_hedge_price=None):
    hedged_amounts = []
    final_hedge_ratios = []
    
    for index, row in df.iterrows():
        forward_rate = row["Forward Rate"]
        hedge_ratio = row["Hedge Ratio"]
        
        # Apply max/min hedge price logic
        if user_type == "Importer" and forward_rate > max_hedge_price:
            hedge_ratio = 0  # No hedge above max price
        elif user_type == "Exporter" and forward_rate < min_hedge_price:
            hedge_ratio = 0  # No hedge below min price
        
        hedged_amount = row["Expected FX Flow"] * hedge_ratio
        hedged_amounts.append(hedged_amount)
        final_hedge_ratios.append(hedge_ratio)
    
    df["Final Hedge Ratio"] = final_hedge_ratios
    df["Hedged Amount"] = hedged_amounts
    return df

df = calculate_hedge(df, user_type, max_hedge_price if user_type == "Importer" else None, min_hedge_price if user_type == "Exporter" else None)

# Display results
table = df[["Month", "Expected FX Flow", "Forward Rate", "Final Hedge Ratio", "Hedged Amount"]]
st.write("### Hedging Plan")
st.dataframe(table)

# ---------------------- Alternative Hedge Suggestions ---------------------- #
st.write("### Alternative Hedge Suggestions")
def suggest_alternative_hedge(df, user_type, max_hedge_price=None, min_hedge_price=None):
    alternative_suggestions = []
    
    for index, row in df.iterrows():
        forward_rate = row["Forward Rate"]
        suggestion = "Keep Current Hedge"
        
        if user_type == "Importer" and forward_rate > max_hedge_price:
            suggestion = "Consider Shorter Tenor Forward"
        elif user_type == "Exporter" and forward_rate < min_hedge_price:
            suggestion = "Consider Longer Tenor Forward"
        
        alternative_suggestions.append(suggestion)
    
    df["Alternative Hedge Suggestion"] = alternative_suggestions
    return df

df = suggest_alternative_hedge(df, user_type, max_hedge_price if user_type == "Importer" else None, min_hedge_price if user_type == "Exporter" else None)

st.write("### Adjusted Hedge Strategy with Alternative Recommendations")
st.dataframe(df[["Month", "Expected FX Flow", "Forward Rate", "Final Hedge Ratio", "Hedged Amount", "Alternative Hedge Suggestion"]])
