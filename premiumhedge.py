import streamlit as st
import pandas as pd
import statsmodels.api as sm
import plotly.graph_objects as go

def load_data(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        # Try to find the date column
        for col in df.columns:
            if col.strip().lower() == "date":
                df["Date"] = pd.to_datetime(df[col])
                break
        else:
            st.error("Date column not found in uploaded file.")
            return None
        return df
    return None

st.title("📈 FX Bond Spread Dashboard")

st.sidebar.header("Upload CSV Files")
germany_bond_file = st.sidebar.file_uploader("Germany Bond Yield CSV")
poland_bond_file = st.sidebar.file_uploader("Poland Bond Yield CSV")
us_bond_file = st.sidebar.file_uploader("US Bond Yield CSV")
eur_pln_file = st.sidebar.file_uploader("EUR/PLN FX CSV")
usd_pln_file = st.sidebar.file_uploader("USD/PLN FX CSV")

if all([germany_bond_file, poland_bond_file, us_bond_file, eur_pln_file, usd_pln_file]):
    germany_bond = load_data(germany_bond_file)
    poland_bond = load_data(poland_bond_file)
    us_bond = load_data(us_bond_file)
    eur_pln = load_data(eur_pln_file)
    usd_pln = load_data(usd_pln_file)

    if None not in [germany_bond, poland_bond, us_bond, eur_pln, usd_pln]:
        bond_data = poland_bond.merge(germany_bond, on="Date", suffixes=("_PL", "_DE"))
        bond_data = bond_data.merge(us_bond, on="Date", suffixes=("", "_US"))
        bond_data.rename(columns={
            "Price_PL": "Poland_Yield",
            "Price_DE": "Germany_Yield",
            "Price": "US_Yield"
        }, inplace=True)

        bond_data["EURPLN_Spread"] = bond_data["Germany_Yield"] - bond_data["Poland_Yield"]
        bond_data["USDPLN_Spread"] = bond_data["US_Yield"] - bond_data["Poland_Yield"]

        fx_data = eur_pln.merge(usd_pln, on="Date", suffixes=("_EURPLN", "_USDPLN")).merge(bond_data, on="Date")
        fx_data = fx_data[["Date", "Price_EURPLN", "Price_USDPLN", "EURPLN_Spread", "USDPLN_Spread"]]
        fx_data.sort_values("Date", inplace=True)

        # Linear regression
        X_eurpln = sm.add_constant(fx_data["EURPLN_Spread"])
        y_eurpln = fx_data["Price_EURPLN"]
        model_eurpln = sm.OLS(y_eurpln, X_eurpln).fit()
        fx_data["Predicted_EURPLN"] = model_eurpln.predict(X_eurpln)

        X_usdpln = sm.add_constant(fx_data["USDPLN_Spread"])
        y_usdpln = fx_data["Price_USDPLN"]
        model_usdpln = sm.OLS(y_usdpln, X_usdpln).fit()
        fx_data["Predicted_USDPLN"] = model_usdpln.predict(X_usdpln)

        # Interactive plotly charts
        fig_eur = go.Figure()
        fig_eur.add_trace(go.Scatter(x=fx_data["Date"], y=fx_data["Price_EURPLN"],
                                     mode='lines', name='Historical EUR/PLN', line=dict(dash='dash')))
        fig_eur.add_trace(go.Scatter(x=fx_data["Date"], y=fx_data["Predicted_EURPLN"],
                                     mode='lines', name='Predicted EUR/PLN'))
        fig_eur.update_layout(title="EUR/PLN: Historical vs Predicted", xaxis_title="Date", yaxis_title="Rate")

        fig_usd = go.Figure()
        fig_usd.add_trace(go.Scatter(x=fx_data["Date"], y=fx_data["Price_USDPLN"],
                                     mode='lines', name='Historical USD/PLN', line=dict(dash='dash')))
        fig_usd.add_trace(go.Scatter(x=fx_data["Date"], y=fx_data["Predicted_USDPLN"],
                                     mode='lines', name='Predicted USD/PLN'))
        fig_usd.update_layout(title="USD/PLN: Historical vs Predicted", xaxis_title="Date", yaxis_title="Rate")

        st.plotly_chart(fig_eur, use_container_width=True)
        st.plotly_chart(fig_usd, use_container_width=True)

        st.write("### 📊 Latest Values")

        latest = fx_data.sort_values("Date").iloc[-1]
        st.metric("Actual EUR/PLN", f"{latest['Price_EURPLN']:.4f}")
        st.metric("Predicted EUR/PLN", f"{latest['Predicted_EURPLN']:.4f}")
        st.metric("Actual USD/PLN", f"{latest['Price_USDPLN']:.4f}")
        st.metric("Predicted USD/PLN", f"{latest['Predicted_USDPLN']:.4f}")

        # Convergence days
        fx_data["Diff_EURPLN"] = abs(fx_data["Price_EURPLN"] - fx_data["Predicted_EURPLN"])
        fx_data["Diff_USDPLN"] = abs(fx_data["Price_USDPLN"] - fx_data["Predicted_USDPLN"])
        fx_data["Converged_EURPLN"] = fx_data["Diff_EURPLN"] / fx_data["Price_EURPLN"] < 0.005
        fx_data["Converged_USDPLN"] = fx_data["Diff_USDPLN"] / fx_data["Price_USDPLN"] < 0.005

        eur_days = fx_data["Converged_EURPLN"].astype(int).rolling(365, min_periods=1).sum().mean()
        usd_days = fx_data["Converged_USDPLN"].astype(int).rolling(365, min_periods=1).sum().mean()

        st.write(f"📈 Average Days for EUR/PLN Convergence (0.5% Threshold): **{eur_days:.0f} days**")
        st.write(f"📈 Average Days for USD/PLN Convergence (0.5% Threshold): **{usd_days:.0f} days**")
