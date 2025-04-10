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
domestic_file = st.file_uploader("Upload Domestic Bond Yield CSV (Date, Yield %)", type=["csv"])
foreign_file = st.file_uploader("Upload Foreign Bond Yield CSV (Date, Yield %)", type=["csv"])

strategy = st.selectbox("Choose Strategy", ["Seller", "Buyer", "Both"])
trade_day = st.selectbox("Choose Trading Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
day_mapping = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}

if fx_file and domestic_file and foreign_file:
    fx = pd.read_csv(fx_file).iloc[:, :2]
    fx.columns = ["Date", "FX"]
    fx["Date"] = pd.to_datetime(fx["Date"])
    fx = fx.sort_values("Date")

    dom = pd.read_csv(domestic_file).iloc[:, :2]
    dom.columns = ["Date", "Domestic"]
    dom["Date"] = pd.to_datetime(dom["Date"])
    dom["Domestic"] = dom["Domestic"].astype(str).str.replace('%', '', regex=False).astype(float) / 100

    for_ = pd.read_csv(foreign_file).iloc[:, :2]
    for_.columns = ["Date", "Foreign"]
    for_["Date"] = pd.to_datetime(for_["Date"])
    for_["Foreign"] = for_["Foreign"].astype(str).str.replace('%', '', regex=False).astype(float) / 100

    df = fx.merge(dom, on="Date").merge(for_, on="Date").sort_values("Date")
    df["Spread"] = df["Domestic"] - df["Foreign"]

    window = 90
    predicted = []
    for i in range(window, len(df)):
        X = df.iloc[i - window:i][["Spread"]].values
        y = df.iloc[i - window:i]["FX"].values
        model = LinearRegression().fit(X, y)
        pred = model.predict([[df.iloc[i]["Spread"]]])[0]
        predicted.append([df.iloc[i]["Date"], df.iloc[i]["FX"], pred])

    reg_df = pd.DataFrame(predicted, columns=["Date", "FX", "Predicted"])

    trade_amount = 250000
    results_all = []
    colors = {30: "blue", 60: "orange", 90: "green"}

    st.subheader("📈 Cumulative PnL (% of Base Currency)")
    plt.figure(figsize=(14, 6))

    for days in [30, 60, 90]:
        temp = reg_df.copy()
        temp["Future"] = temp["FX"].shift(-days)
        results = []
        for i, row in temp.iterrows():
            if row["Date"].weekday() != day_mapping[trade_day]:
                continue
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

        df_result = pd.DataFrame(results)
        df_result = df_result[df_result["Action"] != "Hold"].copy()
        df_result["CumPnL"] = df_result["PnL"].cumsum()
        df_result["CumPnL_pct"] = df_result["CumPnL"] / (trade_amount * df_result.shape[0]) * 100
        df_result["Year"] = df_result["Date"].dt.year
        yearly_returns = df_result.groupby("Year")["PnL"].sum() / trade_amount * 100
        df_result["Days"] = days
        results_all.append(df_result)

        plt.plot(df_result["Date"], df_result["CumPnL_pct"], label=f"{days}-Day Hold", color=colors[days])
        plt.scatter(df_result["Date"], df_result["CumPnL_pct"], color=colors[days], s=10, alpha=0.5, label=f"{days}-Day Entries")

        for year, ret in yearly_returns.items():
            mid_date = pd.Timestamp(f"{year}-07-01")
            y_level = df_result[df_result["Date"].dt.year == year]["CumPnL_pct"].max()
            if np.isnan(y_level):
                continue
            y_offset = 0.2
            plt.text(mid_date, y_level + y_offset, f"{ret:.2f}%", color=colors[days], fontsize=9, ha='center')

    plt.axhline(0, color='gray', linestyle='--')
    plt.xlabel("Date")
    plt.ylabel("Cumulative PnL (%)")
    plt.title("Cumulative PnL by Holding Period")
    plt.grid(True)
    plt.legend()
    st.pyplot(plt)

    st.subheader("📊 Strategy Summary Statistics")
    for df_summary in results_all:
        days = df_summary["Days"].iloc[0]
        total_trades = len(df_summary)
        winning_trades = (df_summary["PnL"] > 0).sum()
        losing_trades = (df_summary["PnL"] < 0).sum()
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        avg_pnl = df_summary["PnL"].mean()
        max_drawdown = (df_summary["CumPnL"].cummax() - df_summary["CumPnL"]).max()

        st.markdown(f"**{days}-Day Hold**")
        st.markdown(f"- Total Trades: `{total_trades}`")
        st.markdown(f"- Winning Trades: `{winning_trades}`")
        st.markdown(f"- Losing Trades: `{losing_trades}`")
        st.markdown(f"- Win Rate: `{win_rate:.2f}%`")
        st.markdown(f"- Avg PnL per Trade: `{avg_pnl:,.2f}`")
        st.markdown(f"- Max Drawdown: `{max_drawdown:,.2f}`")

    st.subheader("📊 Strategy Results (All Holding Periods)")
    full_result_df = pd.concat(results_all).reset_index(drop=True)
    st.dataframe(full_result_df)
else:
    st.info("📂 Please upload all three CSV files to begin.")
