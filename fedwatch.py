import streamlit as st

def calculate_fx_forward_rate(spot_rate, r_domestic, r_foreign, months):
    t = months / 12
    forward_rate = spot_rate * (1 + r_domestic * t) / (1 + r_foreign * t)
    return round(forward_rate, 4)

st.set_page_config(page_title="FX Forward Rate Calculator", layout="centered")
st.title("💱 Synthetic FX Forward Rate Calculator")

st.markdown("""
Simulate a synthetic FX forward rate using spot rate and interest rate differentials.  
This tool mimics the pricing behavior of FX forwards and NDFs using stablecoins or tokenized currencies.
""")

# Currency selection
base_currency = st.selectbox("Base Currency", ["EUR", "USD", "PLN"])
quote_currency = st.selectbox("Quote Currency", ["PLN", "EUR", "USD"])

if base_currency == quote_currency:
    st.error("Base and quote currencies must differ.")
    st.stop()

# Spot rate
spot = st.number_input(f"Spot rate ({base_currency}/{quote_currency})", min_value=0.0001, value=4.30, step=0.0001, format="%.4f")

# Interest rates
r_base = st.number_input(f"{base_currency} interest rate (%)", min_value=0.0, max_value=100.0, value=4.00, step=0.25) / 100
r_quote = st.number_input(f"{quote_currency} interest rate (%)", min_value=0.0, max_value=100.0, value=5.75, step=0.25) / 100

# Tenor
tenor_months = st.slider("Tenor (months)", min_value=1, max_value=12, value=6)

# Calculate forward
forward = calculate_fx_forward_rate(spot, r_quote, r_base, tenor_months)

st.success(f"📈 Synthetic Forward Rate ({base_currency}/{quote_currency}) in {tenor_months}M: **{forward:.4f}**")

st.caption("Formula: Forward = Spot × (1 + domestic_rate × T) / (1 + foreign_rate × T)")
