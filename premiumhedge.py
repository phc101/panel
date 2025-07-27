import streamlit as st
import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import numpy as np

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

    # ---------- Regressions using sklearn ----------
    # EUR/PLN regression
    model_eur = LinearRegression()
    X_eur = fx_data["EURPLN_Spread"].values.reshape(-1, 1)
    y_eur = fx_data["Price_EURPLN"].values
    model_eur.fit(X_eur, y_eur)
    fx_data["Predicted_EURPLN"] = model_eur.predict(X_eur)
    
    # USD/PLN regression
    model_usd = LinearRegression()
    X_usd = fx_data["USDPLN_Spread"].values.reshape(-1, 1)
    y_usd = fx_data["Price_USDPLN"].values
    model_usd.fit(X_usd, y_usd)
    fx_data["Predicted_USDPLN"] = model_usd.predict(X_usd)

    # ---------- Display Model Statistics ----------
    r2_eur = model_eur.score(X_eur, y_eur)
    r2_usd = model_usd.score(X_usd, y_usd)
    
    st.write("### 📊 Model Performance")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("EUR/PLN R²", f"{r2_eur:.3f}")
        st.write(f"**Coefficient:** {model_eur.coef_[0]:.4f}")
        st.write(f"**Intercept:** {model_eur.intercept_:.4f}")
    with col2:
        st.metric("USD/PLN R²", f"{r2_usd:.3f}")
        st.write(f"**Coefficient:** {model_usd.coef_[0]:.4f}")
        st.write(f"**Intercept:** {model_usd.intercept_:.4f}")

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

    fig.tight_layout()
    st.pyplot(fig)

    # ---------- Latest Price Display ----------
    latest = fx_data.sort_values("Date").iloc[-1]
    price_actual_usd = latest["Price_USDPLN"]
    price_pred_usd = latest["Predicted_USDPLN"]
    price_actual_eur = latest["Price_EURPLN"]
    price_pred_eur = latest["Predicted_EURPLN"]

    percent_diff_usd = ((price_pred_usd - price_actual_usd) / price_actual_usd) * 100
    percent_diff_eur = ((price_pred_eur - price_actual_eur) / price_actual_eur) * 100

    st.write("### 📊 Latest FX vs Predicted")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Actual EUR/PLN", f"{price_actual_eur:.4f}")
        st.metric("Predicted EUR/PLN", f"{price_pred_eur:.4f}")
        st.write(f"**% Difference EUR/PLN:** {percent_diff_eur:.2f}%")
    with col2:
        st.metric("Actual USD/PLN", f"{price_actual_usd:.4f}")
        st.metric("Predicted USD/PLN", f"{price_pred_usd:.4f}")
        st.write(f"**% Difference USD/PLN:** {percent_diff_usd:.2f}%")

else:
    st.write("### ⬆️ Please upload all 5 CSV files to begin analysis")
    st.write("Required files:")
    st.write("- Germany Bond Yield CSV")
    st.write("- Poland Bond Yield CSV")
    st.write("- US Bond Yield CSV")  
    st.write("- EUR/PLN FX CSV")
    st.write("- USD/PLN FX CSV")
