import streamlit as st
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt

def load_data(uploaded_file):
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file)
    return None

st.title("FX Bond Spread Dashboard")

st.sidebar.header("Upload CSV Files")
germany_bond_file = st.sidebar.file_uploader("Upload Germany Bond Yield CSV")
poland_bond_file = st.sidebar.file_uploader("Upload Poland Bond Yield CSV")
us_bond_file = st.sidebar.file_uploader("Upload US Bond Yield CSV")
eur_pln_file = st.sidebar.file_uploader("Upload EUR/PLN CSV")
usd_pln_file = st.sidebar.file_uploader("Upload USD/PLN CSV")

if all([germany_bond_file, poland_bond_file, us_bond_file, eur_pln_file, usd_pln_file]):
    germany_bond = load_data(germany_bond_file)
    poland_bond = load_data(poland_bond_file)
    us_bond = load_data(us_bond_file)
    eur_pln = load_data(eur_pln_file)
    usd_pln = load_data(usd_pln_file)
    
    for df in [germany_bond, poland_bond, us_bond, eur_pln, usd_pln]:
        df["Date"] = pd.to_datetime(df["Date"])
    
    bond_data = poland_bond.merge(germany_bond, on="Date", suffixes=("_PL", "_DE"))
    bond_data = bond_data.merge(us_bond, on="Date", suffixes=("", "_US"))
    bond_data.rename(columns={"Price_PL": "Poland_Yield", "Price_DE": "Germany_Yield", "Price": "US_Yield"}, inplace=True)
    
    bond_data["EURPLN_Spread"] = bond_data["Germany_Yield"] - bond_data["Poland_Yield"]
    bond_data["USDPLN_Spread"] = bond_data["US_Yield"] - bond_data["Poland_Yield"]
    
    fx_data = eur_pln.merge(usd_pln, on="Date", suffixes=("_EURPLN", "_USDPLN")).merge(bond_data, on="Date")
    fx_data = fx_data[["Date", "Price_EURPLN", "Price_USDPLN", "EURPLN_Spread", "USDPLN_Spread"]]
    
    X_eurpln = sm.add_constant(fx_data["EURPLN_Spread"])
    y_eurpln = fx_data["Price_EURPLN"]
    model_eurpln = sm.OLS(y_eurpln, X_eurpln).fit()
    fx_data["Predicted_EURPLN"] = model_eurpln.predict(X_eurpln)
    
    X_usdpln = sm.add_constant(fx_data["USDPLN_Spread"])
    y_usdpln = fx_data["Price_USDPLN"]
    model_usdpln = sm.OLS(y_usdpln, X_usdpln).fit()
    fx_data["Predicted_USDPLN"] = model_usdpln.predict(X_usdpln)
    
    st.write("### Processed FX and Bond Spread Data")
    st.dataframe(fx_data)
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    axes[0].plot(fx_data["Date"], fx_data["Price_EURPLN"], label="Historical EUR/PLN", linestyle="dashed")
    axes[0].plot(fx_data["Date"], fx_data["Predicted_EURPLN"], label="Predicted EUR/PLN", linewidth=2)
    axes[0].set_xlabel("Date")
    axes[0].set_ylabel("Exchange Rate")
    axes[0].set_title("EUR/PLN: Historical vs Predicted")
    axes[0].legend()
    axes[0].tick_params(axis='x', rotation=45)
    
    axes[1].plot(fx_data["Date"], fx_data["Price_USDPLN"], label="Historical USD/PLN", linestyle="dashed")
    axes[1].plot(fx_data["Date"], fx_data["Predicted_USDPLN"], label="Predicted USD/PLN", linewidth=2)
    axes[1].set_xlabel("Date")
    axes[1].set_ylabel("Exchange Rate")
    axes[1].set_title("USD/PLN: Historical vs Predicted")
    axes[1].legend()
    axes[1].tick_params(axis='x', rotation=45)
    
    st.pyplot(fig)
    
    latest_predicted_prices = fx_data.iloc[-1][["Predicted_EURPLN", "Predicted_USDPLN"]]
    latest_spot_prices = fx_data.iloc[0][["Price_EURPLN", "Price_USDPLN"]]
    
    st.write("### Latest Prices")
    
    # Calculate percentage difference
    eurpln_diff = abs((latest_predicted_prices['Predicted_EURPLN'] - latest_spot_prices['Price_EURPLN']) / latest_spot_prices['Price_EURPLN']) * 100
    usdpln_diff = abs((latest_predicted_prices['Predicted_USDPLN'] - latest_spot_prices['Price_USDPLN']) / latest_spot_prices['Price_USDPLN']) * 100
    
    st.write(f"**Actual EUR/PLN:** {latest_spot_prices['Price_EURPLN']:.4f}")
    st.write(f"**Predicted EUR/PLN:** {latest_predicted_prices['Predicted_EURPLN']:.4f}")
    st.write(f"**% Difference EUR/PLN:** {eurpln_diff:.2f}%")
    
    st.write(f"**Actual USD/PLN:** {latest_spot_prices['Price_USDPLN']:.4f}")
    st.write(f"**Predicted USD/PLN:** {latest_predicted_prices['Predicted_USDPLN']:.4f}")
    st.write(f"**% Difference USD/PLN:** {usdpln_diff:.2f}%")
    
    # Calculate average days to convergence based on last year
    fx_data['Diff_EURPLN'] = abs(fx_data['Price_EURPLN'] - fx_data['Predicted_EURPLN'])
    fx_data['Diff_USDPLN'] = abs(fx_data['Price_USDPLN'] - fx_data['Predicted_USDPLN'])
    
    convergence_threshold = 0.5 / 100  # Define threshold for convergence (0.5%)
    fx_data['Converged_EURPLN'] = fx_data['Diff_EURPLN'] / fx_data['Price_EURPLN'] < convergence_threshold
    fx_data['Converged_USDPLN'] = fx_data['Diff_USDPLN'] / fx_data['Price_USDPLN'] < convergence_threshold
    
    avg_days_eurpln = fx_data['Converged_EURPLN'].astype(int).rolling(365, min_periods=1).sum().mean()
    avg_days_usdpln = fx_data['Converged_USDPLN'].astype(int).rolling(365, min_periods=1).sum().mean()
    
    st.write(f"**Average days for EUR/PLN to converge:** {avg_days_eurpln:.0f} days")
    st.write(f"**Average days for USD/PLN to converge:** {avg_days_usdpln:.0f} days")
    st.write(f"**Predicted EUR/PLN:** {latest_predicted_prices['Predicted_EURPLN']:.4f}")
    st.write(f"**Predicted USD/PLN:** {latest_predicted_prices['Predicted_USDPLN']:.4f}")
    st.write(f"**Last Spot EUR/PLN:** {latest_spot_prices['Price_EURPLN']:.4f}")
    st.write(f"**Last Spot USD/PLN:** {latest_spot_prices['Price_USDPLN']:.4f}")
