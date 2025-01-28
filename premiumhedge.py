import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Helper Functions
def simulate_fx_rates(current_rate, volatility, days=252, simulations=10000):
    dt = 1 / days  # Daily time step
    paths = np.zeros((days, simulations))
    paths[0] = current_rate

    for t in range(1, days):
        rand = np.random.standard_normal(simulations)
        paths[t] = paths[t - 1] * np.exp((0 - 0.5 * volatility ** 2) * dt + volatility * np.sqrt(dt) * rand)
    
    return paths

def calculate_cfar(expected_flow, current_rate, fx_volatility, confidence_level=0.95):
    simulations = simulate_fx_rates(current_rate, fx_volatility)
    fx_changes = simulations[-1] - current_rate  # Final FX changes
    fx_changes_percent = fx_changes / current_rate

    adverse_change = np.percentile(fx_changes_percent, (1 - confidence_level) * 100)
    cfar = expected_flow * current_rate * abs(adverse_change)
    return round(cfar, 2)

def calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, time_to_maturity):
    forward_rate = spot_rate * np.exp((domestic_rate - foreign_rate) * time_to_maturity)
    return round(forward_rate, 4)

def calculate_multi_maturity_forward_rates(spot_rate, domestic_rate, foreign_rate, max_months=12):
    forward_rates = {}
    for month in range(1, max_months + 1):
        time_to_maturity = month / 12  # Convert months to years
        forward_rate = calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, time_to_maturity)
        forward_rates[f"{month}M"] = forward_rate
    return forward_rates

def visualize_hedging_outcomes(spot_rate, forward_rate, cfar, expected_flow):
    fig, ax = plt.subplots()

    ax.axhline(y=spot_rate, color="blue", linestyle="--", label="Spot Rate")
    ax.axhline(y=forward_rate, color="green", linestyle="--", label="Forward Rate")

    ax.bar(["Expected Flow"], [expected_flow], color="gray", label="Expected Flow")
    ax.bar(["CFaR"], [-cfar], color="red", label="CFaR Impact")

    ax.set_ylabel("PLN")
    ax.set_title("Hedging Outcomes")
    ax.legend()
    st.pyplot(fig)

# Streamlit Components
def operational_questionnaire():
    st.title("Automatic Hedging Strategy")
    st.subheader("Step 1: Operational Insights")
    
    with st.form("currency_flow_form"):
        st.write("Please fill in the details about your currency flows:")
        
        currency_pair = st.selectbox("Select currency pair", ["EUR/PLN", "USD/PLN", "GBP/PLN"])
        annual_flow = st.number_input("Expected annual flow volume (in millions):", min_value=0.0, step=0.1)
        payment_frequency = st.selectbox("Payment/Collection Frequency", ["Monthly", "Quarterly", "Yearly"])
        risk_tolerance = st.slider("Risk tolerance level (1 = low, 10 = high):", 1, 10, 5)
        existing_hedge = st.radio("Do you have existing hedging practices?", ["Yes", "No"])
        
        submitted = st.form_submit_button("Submit")
        if submitted:
            st.session_state["inputs"] = {
                "currency_pair": currency_pair,
                "annual_flow": annual_flow,
                "payment_frequency": payment_frequency,
                "risk_tolerance": risk_tolerance,
                "existing_hedge": existing_hedge,
            }
            st.success("Inputs saved! Proceed to the next step.")

def interactive_hedging_visualization(forward_rates, spot_rate, expected_flow):
    st.subheader("Interactive Hedging Scenarios")

    selected_maturity = st.selectbox("Select Maturity", list(forward_rates.keys()))
    hedge_amount = st.slider("Hedge Amount (in millions):", 0.0, expected_flow / 1e6, step=0.1)

    forward_rate = forward_rates[selected_maturity]
    hedge_value = hedge_amount * 1e6 * forward_rate
    st.write(f"**Hedged Value ({selected_maturity}):** {hedge_value:.2f} PLN")

    fig, ax = plt.subplots()
    ax.axhline(y=spot_rate, color="blue", linestyle="--", label="Spot Rate")
    ax.axhline(y=forward_rate, color="green", linestyle="--", label=f"Forward Rate ({selected_maturity})")
    ax.bar(["Expected Flow"], [expected_flow], color="gray", label="Expected Flow")
    ax.bar(["Hedge Value"], [hedge_value], color="green", label="Hedge Value")

    ax.set_ylabel("PLN")
    ax.set_title("Hedging Scenario")
    ax.legend()
    st.pyplot(fig)

def hedging_plan_with_visuals():
    st.subheader("Step 2: Hedging Plan with Visuals")
    
    if "inputs" in st.session_state:
        inputs = st.session_state["inputs"]
        expected_flow = inputs["annual_flow"] * 1e6
        current_rate = 4.21
        fx_volatility = 0.05
        domestic_rate = 0.05
        foreign_rate = 0.02

        cfar = calculate_cfar(expected_flow, current_rate, fx_volatility)
        forward_rates = calculate_multi_maturity_forward_rates(current_rate, domestic_rate, foreign_rate)

        st.write(f"**CFaR (95% Confidence):** {cfar} PLN")
        st.write(f"**Forward Rates by Maturity:**")
        st.table(forward_rates)

        st.subheader("Simulated FX Rates")
        simulated_paths = simulate_fx_rates(current_rate, fx_volatility)
        simulated_df = pd.DataFrame(simulated_paths)
        st.line_chart(simulated_df.iloc[:, :10])

        st.subheader("Hedging Outcomes")
        interactive_hedging_visualization(forward_rates, current_rate, expected_flow)
    else:
        st.warning("Please complete Step 1 first.")

def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Questionnaire", "Hedging Plan"])

    if page == "Questionnaire":
        operational_questionnaire()
    elif page == "Hedging Plan":
        hedging_plan_with_visuals()

if __name__ == "__main__":
    main()
