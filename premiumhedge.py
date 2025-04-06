import streamlit as st
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt

# ---------- Load CSVs with English headers ----------
def load_data(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        if "Date" not in df.columns or "Price" not in df.columns:
            st.error(f"❌ File must have columns: 'Date' and 'Price'. Found: {df.columns.tolist()}")
            return None
        df["Date"] = pd.to_datetime(df["Date"])
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        df.dropna(subset=["Date", "Price"], inplace=True)
        return df
    return None

# ---------- Streamlit UI ----------
st.title("📈 FX Bond Spread Dashboard")

st.sidebar.header("Upload Clean CSV Files")
germany_bond_file = st.sidebar.file_uploader("Germany Bond Yield CSV")
poland_bond_file = st.sidebar.file_uploader("Poland Bond Yield CSV")
us_bond_file = st.sidebar.file_uploader("US Bond Yield CSV")
eur_pln_file = st.sidebar.file_uploader("EUR/PLN FX CSV")
usd_pln_file = st.sidebar.file_uploader("USD/PLN FX CSV")

# ---------- Load all files ----------
germany_bond = load_data(germany_bond_file)
poland_bond = load_data(poland_bond_file)
us_bond = load_data(us_bond_file)
eur_pln = load_data(eur_pln_file)
usd_pln = load_data(usd_pln_file)

# ---------- Proceed only if all files are valid ----------
if all(df is not None for df in [germany_bond, poland_bond, us_bond, eur_pln, usd_pln]):

    # Merge bond yields
    bond_data = poland_bond.merge(germany_bond, on="Date", suffixes=("_PL", "_DE"))
    bond_data = bond_data.merge(us_bond, on="Date", suffixes=("", "_US"))
    bond_data.rename(columns={
        "Price_PL": "Poland_Yield",
        "Price_DE": "Germany_Yield",
        "Price": "US_Yield"
    }, inplace=True)

    # Calculate spreads
    bond_data["EURPLN_Spread"] = bond_data["Germany_Yield"] - bond_data["Poland_Yield"]
    bond_data["USDPLN_Spread"] = bond_data["US_Yield"] - bond_data["Poland_Yield"]

    # Merge with FX data
    fx_data = eur_pln.merge(usd_pln, on="Date", suffixes=("_EURPLN", "_USDPLN")).merge(bond_data, on="Date")
    fx_data = fx_data[["Date", "Price_EURPLN", "Price_USDPLN", "EURPLN_Spread", "USDPLN_Spread"]]
    fx_data.sort_values("Date", inplace=True)

    # ---------- Regressions ----------
    X_eur = sm.add_constant(fx_data["EURPLN_Spread"])
    y_eur = fx_data["Price_EURPLN"]
    model_eur = sm.OLS(y_eur, X_eur).fit()
    fx_data["Predicted_EURPLN"] = model_eur.predict(X_eur)

    X_usd = sm.add_constant(fx_data["USDPLN_Spread"])
    y_usd = fx_data["Price_USDPLN"]
    model_usd = sm.OLS(y_usd, X_usd).fit()
    fx_data["Predicted_USDPLN"] = model_usd.predict(X_usd)

    # ---------- Matplotlib Charts ----------
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=False)

    # Auto-scale based on USD/PLN range
    min_rate = min(fx_data["Price_USDPLN"].min(), fx_data["Predicted_USDPLN"].min())
    max_rate = max(fx_data["Price_USDPLN"].max(), fx_data["Predicted_USDPLN"].max())
    padding = 0.01
    ymin, ymax = min_rate - padding, max_rate + padding

    # EUR/PLN chart
    axes[0].plot(fx_data["Date"], fx_data["Price_EURPLN"], label="EUR/PLN (Actual)",
                 linestyle="--", color="steelblue")
    axes[0].plot(fx_data["Date"], fx_data["Predicted_EURPLN"], label="EUR/PLN (Predicted)",
                 color="darkorange", linewidth=2)
    axes[0].set_title("EUR/PLN: Historical vs Predicted")
    axes[0].set_xlabel("Date")
    axes[0].set_ylabel("Exchange Rate")
    axes[0].legend()
    axes[0].tick_params(axis='x', rotation=45)

    # USD/PLN chart
    axes[1].plot(fx_data["Date"], fx_data["Price_USDPLN"], label="USD/PLN (Actual)",
                 linestyle="--", color="steelblue")
    axes[1].plot(fx_data["Date"], fx_data["Predicted_USDPLN"], label="USD/PLN (Predicted)",
                 color="darkorange", linewidth=2)
    axes[1].set_ylim([ymin, ymax])
    axes[1].set_title("USD/PLN: Historical vs Predicted")
    axes[1].set_xlabel("Date")
    axes[1].legend()
    axes[1].tick_params(axis='x', rotation=45)

    # Show last prices as text on right
    latest = fx_data.sort_values("Date").iloc[-1]
    price_actual = latest["Price_USDPLN"]
    price_pred = latest["Predicted_USDPLN"]
    percent_diff = ((price_pred - price_actual) / price_actual) * 100

    axes[1].annotate(f"{price_actual:.4f} (Actual)", xy=(latest["Date"], price_actual),
                     xytext=(10, 0), textcoords="offset points", color="steelblue", fontsize=10)
    axes[1].annotate(f"{price_pred:.4f} (Predicted)", xy=(latest["Date"], price_pred),
                     xytext=(10, -15), textcoords="offset points", color="darkorange", fontsize=10)

    fig.tight_layout()
    st.pyplot(fig)

    # ---------- Latest Price Display ----------
    st.write("### 📊 Latest FX vs Predicted")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Actual EUR/PLN", f"{latest['Price_EURPLN']:.4f}")
        st.metric("Predicted EUR/PLN", f"{latest['Predicted_EURPLN']:.4f}")
    with col2:
        st.metric("Actual USD/PLN", f"{price_actual:.4f}")
        st.metric("Predicted USD/PLN", f"{price_pred:.4f}")
        st.write(f"**% Difference USD/PLN:** {percent_diff:.2f}%")
