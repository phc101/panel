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
    reg_df["ValuationGap"] = reg_df["FX"] - reg_df["Predicted"]

    # Ensure only trades initiated on Mondays
    reg_df = reg_df[reg_df["Date"].dt.weekday == 0].copy()

    trade_amount = 250000
    results_all = []
    colors = {30: "blue", 60: "orange", 90: "green"}
    yearly_summary = {}

    st.subheader("🔍 FX vs Predicted Price")
    st.line_chart(reg_df.set_index("Date")[['FX', 'Predicted']])

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
    plt.figure(figsize=(14, 5))
    plt.plot(reg_df['Date'], reg_df['FX'], label='FX Market Price')
    plt.plot(reg_df['Date'], reg_df['Predicted'], label='Predicted Price', linestyle='--')
    plt.title('Historical FX vs Predicted Valuation')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True)
    st.pyplot(plt)

    st.subheader("📈 Cumulative PnL (% of Base Currency)")
    fig, ax = plt.subplots(figsize=(14, 6))

    for days in [30, 60, 90]:
        temp = reg_df.copy()

        # Ensure exit happens exactly after X calendar days
        temp["ExitDate"] = temp["Date"] + pd.to_timedelta(days, unit="D")
        temp = temp.merge(fx[["Date", "FX"]].rename(columns={"Date": "ExitDate", "FX": "Future"}), on="ExitDate", how="left")
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

        yearly_trades = temp.groupby(temp["Date"].dt.year).size()
        yearly_hedged = yearly_trades * trade_amount
        yearly_returns = temp.groupby(temp["Date"].dt.year)["PnL"].sum() / yearly_hedged * 100
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

    st.subheader("📊 Yearly Revenue Summary (%) and Notional Hedged")
    st.write("Total notional hedged each year based on number of trades × trade size:")
    yearly_df = pd.DataFrame(yearly_summary).fillna(0)
    notional_df = pd.DataFrame({
        'Total Hedged (EUR)': yearly_hedged,
        'Revenue (%)': yearly_returns
    }).fillna(0)
    st.dataframe(notional_df.style.format({"Total Hedged (EUR)": "€{:.0f}", "Revenue (%)": "{:.2f}%"}))

    st.subheader("📊 Yearly Revenue Summary (%)")
    yearly_df = pd.DataFrame(yearly_summary).fillna(0)
    st.dataframe(yearly_df.style.format("{:.2f}%"))

    st.subheader("📊 Detailed Trade Results")
    final_results_df = pd.concat(results_all).reset_index(drop=True)
    st.dataframe(final_results_df)
else:
    st.info("📂 Please upload all three CSV files to begin.")
