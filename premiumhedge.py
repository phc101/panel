import streamlit as st
import pandas as pd
import statsmodels.api as sm
import plotly.graph_objects as go

# Automatically map known column names to 'Date' and 'Price'
def load_data(uploaded_file, label):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)

        # Rename common Polish or English columns to standard names
        col_map = {
            "Data": "Date",
            "Ostatnio": "Price",
            "Date": "Date",
            "Last": "Price"
        }
        df.rename(columns={col: col_map.get(col, col) for col in df.columns}, inplace=True)

        # Validate columns
        if "Date" not in df.columns or "Price" not in df.columns:
            st.error(f"❌ '{label}' must include 'Date' and 'Price'. Found columns: {list(df.columns)}")
            return None

        # Convert date and clean rows
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df.dropna(subset=["Date", "Price"], inplace=True)

        return df
    return None

st.title("📈 FX Bond Spread Dashboard")

# Sidebar uploads
st.sidebar.header("Upload CSV Files")
germany_bond_file = st.sidebar.file_uploader("🇩🇪 Germany Bond Yield CSV")
poland_bond_file = st.sidebar.file_uploader("🇵🇱 Poland Bond Yield CSV")
us_bond_file = st.sidebar.file_uploader("🇺🇸 US Bond Yield CSV")
eur_pln_file = st.sidebar.file_uploader("💶 EUR/PLN FX CSV")
usd_pln_file = st.sidebar.file_uploader("💵 USD/PLN FX CSV")

# Load data
germany_bond = load_data(germany_bond_file, "Germany Bond Yield")
poland_bond = load_data(poland_bond_file, "Poland Bond Yield")
us_bond = load_data(us_bond_file, "US Bond Yield")
eur_pln = load_data(eur_pln_file, "EUR/PLN FX")
usd_pln = load_data(usd_pln_file, "USD/PLN FX")

# Ensure all datasets loaded
if all(df is not None for df in [germany_bond, poland_bond, us_bond, eur_pln, usd_pln]):
    # Merge bond data
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

    # Merge FX + bond spreads
    fx_data = eur_pln.merge(usd_pln, on="Date", suffixes=("_EURPLN", "_USDPLN")).merge(bond_data, on="Date")
    fx_data = fx_data[["Date", "Price_EURPLN", "Price_USDPLN", "EURPLN_Spread", "USDPLN_Spread"]]
    fx_data.sort_values("Date", inplace=True)

    # Regression: EUR/PLN
    X_eurpln = sm.add_constant(fx_data["EURPLN_Spread"])
    y_eurpln = fx_data["Price_EURPLN"]
    model_eurpln = sm.OLS(y_eurpln, X_eurpln).fit()
    fx_data["Predicted_EURPLN"] = model_eurpln.predict(X_eurpln)

    # Regression: USD/PLN
    X_usdpln = sm.add_constant(fx_data["USDPLN_Spread"])
    y_usdpln = fx_data["Price_USDPLN"]
    model_usdpln = sm.OLS(y_usdpln, X_usdpln).fit()
    fx_data["Predicted_USDPLN"] = model_usdpln.predict(X_usdpln)

    # 📊 Plot EUR/PLN
    fig_eur = go.Figure()
    fig_eur.add_trace(go.Scatter(x=fx_data["Date"], y=fx_data["Price_EURPLN"],
                                 name='Historical EUR/PLN', line=dict(dash='dash')))
    fig_eur.add_trace(go.Scatter(x=fx_data["Date"], y=fx_data["Predicted_EURPLN"],
                                 name='Predicted EUR/PLN'))
    fig_eur.update_layout(title="EUR/PLN: Historical vs Predicted", xaxis_title="Date", yaxis_title="Rate")

    # 📊 Plot USD/PLN
    fig_usd = go.Figure()
    fig_usd.add_trace(go.Scatter(x=fx_data["Date"], y=fx_data["Price_USDPLN"],
                                 name='Historical USD/PLN', line=dict(dash='dash')))
    fig_usd.add_trace(go.Scatter(x=fx_data["Date"], y=fx_data["Predicted_USDPLN"],
                                 name='Predicted USD/PLN'))
    fig_usd.update_layout(title="USD/PLN: Historical vs Predicted", xaxis_title="Date", yaxis_title="Rate")

    # Show charts
    st.plotly_chart(fig_eur, use_container_width=True)
    st.plotly_chart(fig_usd, use_container_width=True)

    # 📈 Show latest values
    latest = fx_data.sort_values("Date").iloc[-1]
    st.metric("Actual EUR/PLN", f"{latest['Price_EURPLN']:.4f}")
    st.metric("Predicted EUR/PLN", f"{latest['Predicted_EURPLN']:.4f}")
    st.metric("Actual USD/PLN", f"{latest['Price_USDPLN']:.4f}")
    st.metric("Predicted USD/PLN", f"{latest['Predicted_USDPLN']:.4f}")
