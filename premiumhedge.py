import streamlit as st
import pandas as pd
import statsmodels.api as sm
import plotly.graph_objects as go

# -------------------- Load and Clean Uploaded Data --------------------

def load_data(uploaded_file, label):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)

        # Rename columns from Polish or English headers
        col_map = {
            "Data": "Date",
            "Ostatnio": "Price",
            "Date": "Date",
            "Last": "Price"
        }
        df.rename(columns={col: col_map.get(col, col) for col in df.columns}, inplace=True)

        # Validate
        if "Date" not in df.columns or "Price" not in df.columns:
            st.error(f"❌ '{label}' must include 'Date' and 'Price'. Found: {list(df.columns)}")
            return None

        # Clean up: fix commas, remove %, convert types
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Price"] = df["Price"].astype(str).str.replace(",", ".").str.replace("%", "").str.strip()
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        df.dropna(subset=["Date", "Price"], inplace=True)

        return df
    return None

# -------------------- FX Style Plotly Chart Styling --------------------

def style_fx_chart(fig, title):
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Exchange Rate",
        plot_bgcolor="white",
        hovermode="x unified",
        font=dict(size=13),
        xaxis=dict(
            showgrid=True,
            gridwidth=0.5,
            gridcolor="lightgray",
            showline=True,
            linewidth=1,
            linecolor="black",
            ticks="outside"
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=0.5,
            gridcolor="lightgray",
            showline=True,
            linewidth=1,
            linecolor="black",
            ticks="outside"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    return fig

# -------------------- Streamlit App UI --------------------

st.title("📈 FX Bond Spread Dashboard")

st.sidebar.header("Upload CSV Files")
germany_bond_file = st.sidebar.file_uploader("🇩🇪 Germany Bond Yield CSV")
poland_bond_file = st.sidebar.file_uploader("🇵🇱 Poland Bond Yield CSV")
us_bond_file = st.sidebar.file_uploader("🇺🇸 US Bond Yield CSV")
eur_pln_file = st.sidebar.file_uploader("💶 EUR/PLN FX CSV")
usd_pln_file = st.sidebar.file_uploader("💵 USD/PLN FX CSV")

# -------------------- Load Data --------------------

germany_bond = load_data(germany_bond_file, "Germany Bond Yield")
poland_bond = load_data(poland_bond_file, "Poland Bond Yield")
us_bond = load_data(us_bond_file, "US Bond Yield")
eur_pln = load_data(eur_pln_file, "EUR/PLN FX")
usd_pln = load_data(usd_pln_file, "USD/PLN FX")

# -------------------- Proceed if All Files Loaded --------------------

if all(df is not None for df in [germany_bond, poland_bond, us_bond, eur_pln, usd_pln]):

    # Merge bond data
    bond_data = poland_bond.merge(germany_bond, on="Date", suffixes=("_PL", "_DE"))
    bond_data = bond_data.merge(us_bond, on="Date", suffixes=("", "_US"))
    bond_data.rename(columns={
        "Price_PL": "Poland_Yield",
        "Price_DE": "Germany_Yield",
        "Price": "US_Yield"
    }, inplace=True)

    # Calculate bond spreads
    bond_data["EURPLN_Spread"] = bond_data["Germany_Yield"] - bond_data["Poland_Yield"]
    bond_data["USDPLN_Spread"] = bond_data["US_Yield"] - bond_data["Poland_Yield"]

    # Merge FX data with spreads
    fx_data = eur_pln.merge(usd_pln, on="Date", suffixes=("_EURPLN", "_USDPLN")).merge(bond_data, on="Date")
    fx_data = fx_data[["Date", "Price_EURPLN", "Price_USDPLN", "EURPLN_Spread", "USDPLN_Spread"]]
    fx_data.sort_values("Date", inplace=True)

    # -------------------- Regressions --------------------

    # EUR/PLN model
    X_eur = sm.add_constant(fx_data["EURPLN_Spread"])
    y_eur = fx_data["Price_EURPLN"]
    model_eur = sm.OLS(y_eur, X_eur).fit()
    fx_data["Predicted_EURPLN"] = model_eur.predict(X_eur)

    # USD/PLN model
    X_usd = sm.add_constant(fx_data["USDPLN_Spread"])
    y_usd = fx_data["Price_USDPLN"]
    model_usd = sm.OLS(y_usd, X_usd).fit()
    fx_data["Predicted_USDPLN"] = model_usd.predict(X_usd)

    # -------------------- Charts --------------------

    # EUR/PLN chart
    fig_eur = go.Figure()
    fig_eur.add_trace(go.Scatter(
        x=fx_data["Date"], y=fx_data["Price_EURPLN"],
        name='EUR/PLN (Actual)',
        line=dict(color="black", width=1.5, dash='dash')
    ))
    fig_eur.add_trace(go.Scatter(
        x=fx_data["Date"], y=fx_data["Predicted_EURPLN"],
        name='EUR/PLN (Predicted)',
        line=dict(color="green", width=2)
    ))
    fig_eur = style_fx_chart(fig_eur, "EUR/PLN: Historical vs Predicted")
    st.plotly_chart(fig_eur, use_container_width=True)

    # USD/PLN chart
    fig_usd = go.Figure()
    fig_usd.add_trace(go.Scatter(
        x=fx_data["Date"], y=fx_data["Price_USDPLN"],
        name='USD/PLN (Actual)',
        line=dict(color="black", width=1.5, dash='dash')
    ))
    fig_usd.add_trace(go.Scatter(
        x=fx_data["Date"], y=fx_data["Predicted_USDPLN"],
        name='USD/PLN (Predicted)',
        line=dict(color="blue", width=2)
    ))
    fig_usd = style_fx_chart(fig_usd, "USD/PLN: Historical vs Predicted")
    st.plotly_chart(fig_usd, use_container_width=True)

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
