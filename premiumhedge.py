import streamlit as st

# Step 1: Questionnaire
def operational_questionnaire():
    st.title("Automatic Hedging Strategy")
    st.subheader("Step 1: Operational Insights")
    
    with st.form("currency_flow_form"):
        st.write("Please fill in the details about your currency flows:")
        
        # Currency flow details
        currency_pair = st.selectbox("Select currency pair", ["EUR/PLN", "USD/PLN", "GBP/PLN"])
        annual_volume = st.number_input("Expected annual volume in base currency (e.g., EUR):", min_value=0.0, step=0.1)

        # Inflows and Outflows
        st.write("Provide inflow and outflow details:")
        inflows = st.number_input("Total yearly inflows in base currency:", min_value=0.0, step=0.1)
        outflows = st.number_input("Total yearly outflows in base currency:", min_value=0.0, step=0.1)
        
        # Calculate net exposure
        net_exposure = inflows - outflows
        exposure_type = "Neutral (No Net Exposure)"
        if net_exposure > 0:
            exposure_type = "Net Exporter"
        elif net_exposure < 0:
            exposure_type = "Net Importer"
        
        # Display net exposure and classification
        st.write(f"**Net Exposure:** {net_exposure:.2f} base currency ({exposure_type})")

        # Seasonality
        has_seasonality = st.radio("Is there quarterly seasonality in your flows?", ["No", "Yes"])
        quarterly_distribution = None

        if has_seasonality == "Yes":
            st.write("Specify the percentage of yearly volume for each quarter (total must equal 100%).")
            q1 = st.number_input("Q1 (%):", min_value=0.0, max_value=100.0, step=0.1)
            q2 = st.number_input("Q2 (%):", min_value=0.0, max_value=100.0, step=0.1)
            q3 = st.number_input("Q3 (%):", min_value=0.0, max_value=100.0, step=0.1)
            q4 = st.number_input("Q4 (%):", min_value=0.0, max_value=100.0, step=0.1)
            
            if q1 + q2 + q3 + q4 != 100.0:
                st.warning("The total percentage must equal 100%.")
            else:
                quarterly_distribution = [q1, q2, q3, q4]

        # Risk Tolerance
        risk_tolerance = st.slider("Risk tolerance level (1 = low, 10 = high):", 1, 10, 5)

        # Existing hedging practices
        existing_hedge = st.radio("Do you have existing hedging practices?", ["No", "Yes"])
        
        # Submit form
        submitted = st.form_submit_button("Submit")
        if submitted:
            # Save inputs to session state
            st.session_state["inputs"] = {
                "currency_pair": currency_pair,
                "annual_volume": annual_volume,
                "inflows": inflows,
                "outflows": outflows,
                "net_exposure": net_exposure,
                "exposure_type": exposure_type,
                "has_seasonality": has_seasonality,
                "quarterly_distribution": quarterly_distribution,
                "risk_tolerance": risk_tolerance,
                "existing_hedge": existing_hedge,
            }
            st.success("Inputs saved! Proceed to the next step.")

if __name__ == "__main__":
    operational_questionnaire()
