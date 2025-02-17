import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import os

# ---------------------- Load or Save Data ---------------------- #
DATA_FILE = "hedging_data.csv"
USER_FILE_PREFIX = "hedging_data_"

def get_user_file(user_id):
    return f"{USER_FILE_PREFIX}{user_id}.csv"

def load_data(user_id):
    user_file = get_user_file(user_id)
    if os.path.exists(user_file):
        return pd.read_csv(user_file)
    else:
        return None

def save_data(df, user_id):
    user_file = get_user_file(user_id)
    df.to_csv(user_file, index=False)

# ---------------------- User Authentication ---------------------- #
st.title("Automatic FX Hedging System")
user_id = st.text_input("Enter Your User ID:", value="default_user")
data_loaded = load_data(user_id)

# ---------------------- User Inputs ---------------------- #
# User selects if they are an Exporter or Importer
user_type = st.radio("Select Business Type:", ["Exporter", "Importer"], horizontal=True)

# Input expected FX flows using a 4x3 grid layout
st.write("### Expected FX Flows (12-Month View)")
cols = st.columns(4)
data = []
num_months = 12  # Default to 12-month hedging horizon

for i in range(num_months):
    with cols[i % 4]:
        amount = st.number_input(f"Month {i+1}", value=100000 if data_loaded is None else int(data_loaded.iloc[i]["Expected FX Flow"]), step=10000, key=f"flow_{i+1}")
        data.append(amount)

df = pd.DataFrame({"Month": range(1, num_months + 1), "Expected FX Flow": data})

# User-defined budget rate and hedging limits
budget_rate = st.number_input("Enter Budget Rate (EUR/PLN):", value=4.40 if data_loaded is None else float(data_loaded.iloc[0]["Budget Rate"]), step=0.01)
if user_type == "Importer":
    max_hedge_price = st.number_input("Set Max Hedge Price (No Forward Hedge Above):", value=4.35 if data_loaded is None else float(data_loaded.iloc[0]["Max Hedge Price"]), step=0.01)
if user_type == "Exporter":
    min_hedge_price = st.number_input("Set Min Hedge Price (No Forward Hedge Below):", value=4.25 if data_loaded is None else float(data_loaded.iloc[0]["Min Hedge Price"]), step=0.01)

# Hedge ratio selection per month using a 4x3 grid layout
st.write("### Hedge Ratios (12-Month View)")
cols = st.columns(4)
hedge_ratios = []

for i in range(num_months):
    with cols[i % 4]:
        ratio = st.slider(f"Month {i+1}", min_value=0, max_value=100, value=75 if data_loaded is None else int(data_loaded.iloc[i]["Hedge Ratio"]), key=f"hedge_{i+1}")
        hedge_ratios.append(ratio / 100)

df["Hedge Ratio"] = hedge_ratios

# ---------------------- Market Data & Forward Pricing ---------------------- #
spot_rate = st.number_input("Current Spot Rate (EUR/PLN):", value=4.38, step=0.01)
forward_points = st.number_input("Forward Points (Annualized %):", value=0.91, step=0.01) / 100

forward_rates = [spot_rate * (1 + forward_points * (i / 12)) for i in range(1, num_months + 1)]
df["Forward Rate"] = forward_rates

# ---------------------- Hedge Execution Logic ---------------------- #
def calculate_hedge(df, user_type, max_hedge_price=None, min_hedge_price=None):
    hedged_amounts = []
    final_hedge_ratios = []
    
    for index, row in df.iterrows():
        forward_rate = row["Forward Rate"]
        hedge_ratio = row["Hedge Ratio"]
        
        if user_type == "Importer" and forward_rate > max_hedge_price:
            hedge_ratio = 0
        elif user_type == "Exporter" and forward_rate < min_hedge_price:
            hedge_ratio = 0
        
        hedged_amount = row["Expected FX Flow"] * hedge_ratio
        hedged_amounts.append(hedged_amount)
        final_hedge_ratios.append(hedge_ratio)
    
    df["Final Hedge Ratio"] = final_hedge_ratios
    df["Hedged Amount"] = hedged_amounts
    return df

df = calculate_hedge(df, user_type, max_hedge_price if user_type == "Importer" else None, min_hedge_price if user_type == "Exporter" else None)

# Save Data
df["Budget Rate"] = budget_rate
df["Max Hedge Price"] = max_hedge_price if user_type == "Importer" else "N/A"
df["Min Hedge Price"] = min_hedge_price if user_type == "Exporter" else "N/A"
save_data(df, user_id)

# Display results
st.write("### Hedging Plan")
st.dataframe(df[["Month", "Expected FX Flow", "Forward Rate", "Final Hedge Ratio", "Hedged Amount"]])

# ---------------------- Hedging Structure Chart ---------------------- #
st.write("### Hedging Structure Visualization")
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(df["Month"], df["Hedged Amount"], label="Hedged Amount", color="blue", alpha=0.6)
ax.plot(df["Month"], df["Expected FX Flow"], marker="o", linestyle="--", color="red", label="Expected FX Flow")
ax.set_xlabel("Month")
ax.set_ylabel("Amount (EUR)")
ax.set_title("Hedging Structure Over 12 Months")
ax.legend()
st.pyplot(fig)
