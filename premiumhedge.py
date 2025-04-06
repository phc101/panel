import streamlit as st
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt

# -------------------- Load and Clean Uploaded Data --------------------

def load_data(uploaded_file, label):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)

        # Rename common Polish/English headers
        col_map = {
            "Data": "Date",
            "Ostatnio": "Price",
            "Date": "Date",
            "Last": "Price"
        }
        df.rename(columns={col: col_map.get(col, col) for col in df.columns}, inplace=True)

        if "Date" not in df.columns or "Price" not in df.columns:
            st.error(f"❌ '{label}' must include 'Date' and 'Price'. Found: {list(df.columns)}")
            return None

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Price"] = df["Price"].astype(str).str.replace(",", ".").str.replace("%", "").str.strip()
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        df.dropna(subset=["Date", "Price"], inplace=True)

        return df
    return None

# -------------------- Streamlit App --------------------

st.title("📈 FX Bond Spread Dashboard (Smoothed Matplotlib Version)")

# Uploads
st.sidebar.header("Upload CSV Files")
germany_bond_file = st.sidebar.file_uploader("🇩🇪 Germany Bond Yield CSV")
poland_bond_file = st.sidebar.file_uploader("🇵🇱 Poland Bond Yield CSV")
us_bond_file = st.sidebar.file_uploader("🇺🇸 US Bond Yield CSV")
eur_pln_file = st.sidebar.file_uploader("💶 EUR/PLN FX CSV")
usd_pln_file = st.sidebar.file_uploader("💵 USD/PLN FX CSV")

# Load CSVs
germany_bond = load_data(germany_bond_file, "Germany Bond Yield")
poland_bond = load_data(poland_bond_file, "Poland Bond Yield")
us_bond = load_data(us_bond_file, "US Bond Yield")
eur_pln = load_data(eur_pln_file, "EUR/PLN FX")
usd_pln = load_data(usd_pln_file, "USD/PLN FX")

# -------------------- If all files loaded --------------------

if all(df is not None for df in [germany_bond, poland_bond, us_bond, eur_pln, usd_pln]):

    # Merge bond data
    bond_data = poland_bond.merge(germany_bond, on="Date", suffixes=("_PL", "_DE"))
    bond_data = bond_data.merge(us_bond, on="Date", suffixes=("", "_US"))
    bond_data.rename(columns={
        "Price_PL": "Poland_Yield",
        "Price_DE": "Germany_Yield",
        "Price": "US_Yield"
    }, inplace=True)

    bond_data["EURPLN_Spread"] = bond_data["Germany_Yield"] - bond_data["Poland_Yield"]
    bond_data["USDPLN_Spread"] = bond_data["US_Yield"] - bond_data["Poland_Yield"]

    # -------------------- Smoothing with full date range --------------------

    start = max(eur_pln["Date"].min(), usd_pln["Date"].min(), bond_data["Date"].min())
    end = min(eur_pln["Date"].max(), usd_pln["Date"].max(), bond_data["Date"].max())
    full_dates = pd.DataFrame({"Date": pd.date_range(start=start, end=end)})

    eur_pln_full = full_dates.merge(eur_pln, on="Date", how="left").fillna(method="ffill")
    usd_pln_full = full_dates.merge(usd_pln, on="Date", how="left").fillna(method="ffill")
    bond_full = full_dates.merge(bond_data, on="Date", how="left").fillna(method="ffill")

    fx_data = eur_pln_full.merge(usd_pln_full, on="Date", suffixes=("_EURPLN", "_USDPLN"))
    fx_data = fx_data.merge(bond_full, on="Date")
    fx_data = fx_data[["Date", "Price_EURPLN", "Price_USDPLN", "EURPLN_Spread", "USDPLN_Spread"]]
    fx_data.sort_values("Date", inplace=True)

    # -------------------- Regressions --------------------

    X_eur = sm.add_constant(fx_data["EURPLN_Spread"])
    y_eur = fx_data["Price_EURPLN"]
    model_eur = sm.OLS(y_eur, X_eur).fit()
    fx_data["Predicted_EURPLN"] = model_eur.predict(X_eur)

    X_usd = sm.add_constant(fx_data["USDPLN_Spread"])
    y_usd = fx_data["Price_USDPLN"]
    model_usd = sm.OLS(y_usd, X_usd).fit()
    fx_data["Predicted_USDPLN"] = model_usd.predict(X_usd)

    # -------------------- Matplotlib Chart --------------------

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

    # EUR/PLN
    axes[0].plot(fx_data["Date"], fx_data["Price_EURPLN"], label="EUR/PLN (Actual)",
                 linestyle="--", color="steelblue")
    axes[0].plot(fx_data["Date"], fx_data["Predicted_EURPLN"], label="EUR/PLN (Predicted)",
                 color="darkorange", linewidth=2)
    axes[0].set_title("EUR/PLN: Historical vs Predicted")
    axes[0].set_xlabel("Date")
    axes[0].set_ylabel("Exchange Rate")
    axes[0].legend()
    axes[0].tick_params(axis='x', rotation=45)

    # USD/PLN
    axes[1].plot(fx_data["Date"], fx_data["Price_USDPLN"], label="USD/PLN (Actual)",
                 linestyle="--", color="steelblue")
    axes[1].plot(fx_data["Date"], fx_data["Predicted_USDPLN"], label="USD/PLN (Predicted)",
                 color="darkorange", linewidth=2)
    axes[1].set_title("USD/PLN: Historical vs Predicted")
    axes[1].set_xlabel("Date")
    axes[1].legend()
    axes[1].tick_params(axis='x', rotation=45)

    fig.tight_layout()
    st.pyplot(fig)

    # -------------------- Latest Price Metrics --------------------

    latest = fx_data.sort_values("Date").iloc[-1]
    st.write("### 📊 Latest FX vs Predicted")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Actual EUR/PLN", f"{latest['Price_EURPLN']:.4f}")
        st.metric("Predicted EUR/PLN", f"{latest['Predicted_EURPLN']:.4f}")
    with col2:
        st.metric("Actual USD/PLN", f"{latest['Price_USDPLN']:.4f}")
        st.metric("Predicted USD/PLN", f"{latest['Predicted_USDPLN']:.4f}")
