import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

st.set_page_config(page_title="FX Hedge Backtester", layout="wide")
st.title("📈 FX Hedge Strategy Backtester")

# --- File Upload ---
fx_file = st.file_uploader("Upload FX Price CSV (Date, Price)", type=["csv"])
domestic_file = st.file_uploader("Upload Domestic Bond Yield CSV (Date, Price %)", type=["csv"])
foreign_file = st.file_uploader("Upload Foreign Bond Yield CSV (Date, Price %)", type=["csv"])

strategy = st.selectbox("Choose Strategy", ["Seller", "Buyer", "Both"])
holding_days = st.number_input("Holding Period (days)", min_value=1, max_value=365, value=90)

if fx_file and domestic_file and foreign_file:
    # --- Load Data ---
    fx = pd.read_csv(fx_file)
    if fx.shape[1] != 2:
        st.error("❌ FX file must have exactly 2 columns: Date and Price.")
        st.stop()
    fx.columns = ["Date", "FX"]
    fx["Date"] = pd.to_datetime(fx["Date"])

    dom = pd.read_csv(domestic_file)
    if dom.shape[1] != 2:
        st.error("❌ Domestic bond file must have exactly 2 columns: Date and Yield %.")
        st.stop()
    dom.columns = ["Date", "Domestic"]
    dom["Date"] = pd.to_datetime(dom["Date"])
    dom["Domestic"] = dom["Domestic"].astype(str).str.replace('%', '').astype(float) / 100

    for_ = pd.read_csv(foreign_file)
    if for_.shape[1] != 2:
        st.error("❌ Foreign bond file must have exactly 2 columns: Date and Yield %.")
        st.stop()
    for_.columns = ["Date", "Foreign"]
    for_["Date"] = pd.to_datetime(for_["Date"])
    for_["Foreign"] = for_["Foreign"].astype(str).str.replace('%', '').astype(float) / 100

    # --- Merge ---
    df = fx.merge(dom, on="Date").merge(for_, on="Date")
    df = df.sort_values("Date")
    df["Spread"] = df["Domestic"] - df["Foreign"]

    # --- Rolling Regression ---
    window = 90
    predicted = []
    for i in range(window, len(df)):
        X = df.iloc[i - window:i][["Spread"]].values
        y = df.iloc[i - window:i]["FX"].values
        model = LinearRegression().fit(X, y)
        pred = model.predict([[df.iloc[i]["Spread"]]])[0]
        predicted.append([df.iloc[i]["Date"], df.iloc[i]["FX"], pred])

    reg_df = pd.DataFrame(predicted, columns=["Date", "FX", "Predicted"])
    reg_df["Future"] = reg_df["FX"].shift(-holding_days)

    results = []
    trade_amount = 250000

    for _, row in reg_df.iterrows():
        action = "Hold"
        pnl = 0
        if strategy in ["Seller", "Both"] and row["FX"] > row["Predicted"]:
            action = "Sell"
            pnl = (row["FX"] - row["Future"]) * trade_amount
        elif strategy in ["Buyer", "Both"] and row["FX"] < row["Predicted"]:
            action = "Buy"
            pnl = (row["Future"] - row["FX"]) * trade_amount
        results.append({"Date": row["Date"], "FX": row["FX"], "Predicted": row["Predicted"],
                        "Future": row["Future"], "Action": action, "PnL": pnl})

    res_df = pd.DataFrame(results)
    res_df["Cumulative_PnL"] = res_df["PnL"].cumsum()

    st.subheader("📊 Strategy Results")
    st.dataframe(res_df[res_df["Action"] != "Hold"].reset_index(drop=True))

    st.subheader("📈 Cumulative PnL")
    plt.figure(figsize=(12, 5))
    plt.plot(res_df["Date"], res_df["Cumulative_PnL"], label="Cumulative PnL")
    plt.axhline(0, color='gray', linestyle='--')
    plt.xlabel("Date")
    plt.ylabel("PnL (PLN)")
    plt.title("Cumulative PnL Over Time")
    plt.grid(True)
    plt.legend()
    st.pyplot(plt)
else:
    st.info("📂 Please upload all three CSV files to begin.")
