import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

st.set_page_config(page_title="FX Hedge Backtester", layout="wide")
st.title("📈 FX Hedge Strategy Backtester")

# --- File Upload ---
fx_file = st.file_uploader("Upload FX Price CSV (Date, Price)", type=["csv"])
domestic_file = st.file_uploader("Upload Domestic Bond Yield CSV (Date, Yield %)", type=["csv"])
foreign_file = st.file_uploader("Upload Foreign Bond Yield CSV (Date, Yield %)", type=["csv"])

strategy = st.selectbox("Choose Strategy", ["Seller", "Buyer", "Both"])

if fx_file and domestic_file and foreign_file:
    fx = pd.read_csv(fx_file).iloc[:, :2]
    fx.columns = ["Date", "FX"]
    fx["Date"] = pd.to_datetime(fx["Date"], errors='coerce', dayfirst=True)
    fx.dropna(subset=["Date"], inplace=True)

    dom = pd.read_csv(domestic_file).iloc[:, :2]
    dom.columns = ["Date", "Domestic"]
    dom["Date"] = pd.to_datetime(dom["Date"], errors='coerce', dayfirst=True)
    dom.dropna(subset=["Date"], inplace=True)
    dom["Domestic"] = dom["Domestic"].astype(str).str.replace('%', '', regex=False).astype(float) / 100

    for_ = pd.read_csv(foreign_file).iloc[:, :2]
    for_.columns = ["Date", "Foreign"]
    for_["Date"] = pd.to_datetime(for_["Date"], errors='coerce', dayfirst=True)
    for_.dropna(subset=["Date"], inplace=True)
    for_["Foreign"] = for_["Foreign"].astype(str).str.replace('%', '', regex=False).astype(float) / 100

    df = fx.merge(dom, on="Date").merge(for_, on="Date").dropna().sort_values("Date")
    df["Spread"] = df["Domestic"] - df["Foreign"]

    predicted = []
    window = 90
    for i in range(window, len(df)):
        X = df.iloc[i - window:i][["Spread"]]
        y = df.iloc[i - window:i]["FX"]
        model = LinearRegression().fit(X, y)
        pred = model.predict([[df.iloc[i]["Spread"]]])[0]
        predicted.append([df.iloc[i]["Date"], df.iloc[i]["FX"], pred])

    reg_df = pd.DataFrame(predicted, columns=["Date", "FX", "Predicted"])
    # Ensure Date is datetime before filtering
    reg_df["Date"] = pd.to_datetime(reg_df["Date"], errors='coerce')
    reg_df.dropna(subset=["Date"], inplace=True)

    # Filter only Monday signals
    reg_df = reg_df[reg_df["Date"].dt.weekday == 0].copy()

    reg_df["ValuationGap"] = reg_df["FX"] - reg_df["Predicted"]

    trade_amount = 250000
    results_all = []
    colors = {30: "blue", 60: "orange", 90: "green", 120: "purple", 180: "red"}
    yearly_summary = {}

    st.subheader("🔍 FX vs Predicted Price")
    plt.figure(figsize=(14, 5))
    plt.plot(reg_df['Date'], reg_df['FX'], label='FX Market Price', color='green')
    plt.plot(reg_df['Date'], reg_df['Predicted'], label='Predicted Price', linestyle='--', color='red')
    plt.title('Historical FX vs Predicted Valuation')
    plt.xlabel('Date')
    plt.ylabel('Price')
    fx_min = reg_df[['FX', 'Predicted']].min().min()
    fx_max = reg_df[['FX', 'Predicted']].max().max()
    if pd.notna(fx_min) and pd.notna(fx_max):
        plt.ylim(fx_min * 0.995, fx_max * 1.005)
    plt.legend()
    plt.grid(True)
    st.pyplot(plt)

    st.subheader("📉 Valuation Gap (FX - Predicted)")
    plt.figure(figsize=(14, 4))
    plt.plot(reg_df['Date'], reg_df['ValuationGap'], label='Valuation Gap', color='purple')
    plt.axhline(0, color='gray', linestyle='--')
    plt.title('Valuation Gap Over Time')
    plt.xlabel('Date')
    plt.ylabel('FX - Predicted')
    plt.grid(True)
    plt.legend()
    st.pyplot(plt)

    st.subheader("📈 Cumulative PnL (% of Base Currency)")
    fig, ax = plt.subplots(figsize=(14, 6))
    for days in [30, 60, 90, 120, 180]:
        temp = reg_df.copy()
        temp["ExitDate"] = temp["Date"] + pd.to_timedelta(days, unit="D")
        fx_renamed = fx.rename(columns={"Date": "ExitDate", "FX": "Future"})
        temp = pd.merge_asof(temp.sort_values("ExitDate"), fx_renamed.sort_values("ExitDate"), on="ExitDate")
        temp.dropna(subset=["Future"], inplace=True)

        def calc_pnl(row):
            if strategy in ["Seller", "Both"] and row["FX"] > row["Predicted"]:
                return (row["FX"] - row["Future"]) * trade_amount
            elif strategy in ["Buyer", "Both"] and row["FX"] < row["Predicted"]:
                return (row["Future"] - row["FX"]) * trade_amount
            return 0

        temp["PnL"] = temp.apply(calc_pnl, axis=1)
        temp = temp[temp["PnL"] != 0]
        temp["CumPnL_pct"] = temp["PnL"].cumsum() / (trade_amount * len(temp)) * 100

        yearly_returns = temp.groupby(temp["Date"].dt.year)["PnL"].sum() / (len(temp) * trade_amount) * 100
        yearly_summary[f"{days}-Day Hold"] = yearly_returns

        ax.plot(temp["Date"], temp["CumPnL_pct"], label=f"{days}-Day Hold", color=colors[days])
        results_all.append(temp.assign(Holding_Period=days))

    ax.axhline(0, color='gray', linestyle='--')
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative PnL (%)")
    ax.set_title("Cumulative PnL by Holding Period")
    ax.grid(True)
    ax.legend()
    st.pyplot(fig)

    st.subheader("📉 Strategy Drawdown Chart")
    plt.figure(figsize=(14, 4))
    for days, temp in zip([30, 60, 90, 120, 180], results_all):
        temp_sorted = temp.sort_values("Date").copy()
        temp_sorted["Drawdown"] = temp_sorted["CumPnL_pct"] - temp_sorted["CumPnL_pct"].cummax()
        plt.plot(temp_sorted["Date"], temp_sorted["Drawdown"], label=f"{days}-Day Hold", linestyle="--")
    plt.axhline(0, color='gray', linestyle='--')
    plt.title("Drawdown Over Time by Strategy")
    plt.xlabel("Date")
    plt.ylabel("Drawdown (%)")
    plt.grid(True)
    plt.legend()
    st.pyplot(plt)

    st.subheader("📊 Yearly Revenue Summary (%) and Notional Hedged")
    yearly_df = pd.DataFrame(yearly_summary).fillna(0)
    notional_data = {f"{days}-Day Hold": df.groupby(df["Date"].dt.year).size() * trade_amount for days, df in zip([30, 60, 90, 120, 180], results_all)}
    notional_df = pd.DataFrame(notional_data).fillna(0)
    notional_df["Total Hedged (EUR)"] = notional_df.sum(axis=1)
    notional_df["Revenue (%)"] = yearly_df.mean(axis=1)
    st.dataframe(notional_df.style.format({"Total Hedged (EUR)": "€{:.0f}", "Revenue (%)": "{:.2f}%"}))

    st.subheader("📊 Yearly Revenue Summary (%)")
    st.dataframe(yearly_df.style.format("{:.2f}%"))

    final_results_df = pd.concat(results_all).reset_index(drop=True)

    st.subheader("📋 Trade Summary Info")
    st.write(f"Total signal dates (Mondays): **{len(reg_df)}**")
    st.write(f"Executed trades with valid exit FX data: **{len(final_results_df)}**")
    st.subheader("📊 Detailed Trade Results")
    st.dataframe(final_results_df)
else:
    st.info("📂 Please upload all three CSV files to begin.")
