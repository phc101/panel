import os
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import firebase_admin
from firebase_admin import credentials, auth, firestore

# ---------------------- Firebase Authentication & Database ---------------------- #
FIREBASE_CREDENTIALS = "firebase_credentials.json"

if os.path.exists(FIREBASE_CREDENTIALS):
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CREDENTIALS)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    st.error("Firebase credentials file not found. Please add 'firebase_credentials.json'.")
    st.stop()

# ---------------------- Session Management ---------------------- #
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.user_id = None
    st.session_state.login_status = False
if "hedge_ratios" not in st.session_state:
    st.session_state.hedge_ratios = [75] * 12  # Ensure state persistence
if "fx_flows" not in st.session_state:
    st.session_state.fx_flows = [100000] * 12  # Single default flow per month
if "budget_rate" not in st.session_state:
    st.session_state.budget_rate = 4.40  # Default budget rate

# Streamlit Authentication
st.set_page_config(layout="wide")
st.title("Automatic FX Hedging System")

if st.session_state.login_status:
    st.success(f"Logged in as {st.session_state.user.email}")
    user_id = st.session_state.user_id
else:
    option = st.radio("Select an option:", ["Login", "Create New Account"])
    user_email = st.text_input("Enter your Email:")
    password = st.text_input("Enter your Password:", type="password")
    
    if option == "Login":
        if st.button("Login"):
            try:
                user = auth.get_user_by_email(user_email)
                st.session_state.user = user
                st.session_state.user_id = user.uid
                st.session_state.login_status = True
                st.success(f"Logged in as {user.email}")
            except:
                st.error("User not found. Please check your credentials or create a new account.")
    
    elif option == "Create New Account":
        if st.button("Register"):
            try:
                existing_user = None
                try:
                    existing_user = auth.get_user_by_email(user_email)
                except:
                    pass  # User does not exist
                
                if existing_user:
                    st.error("This email is already registered. Please log in instead.")
                else:
                    user = auth.create_user(email=user_email, password=password)
                    db.collection("users").document(user.uid).set({"email": user_email, "role": "user"})
                    st.success(f"Account created successfully for {user.email}. Please log in.")
            except Exception as e:
                st.error(f"Error creating account: {e}")

if st.session_state.login_status:
    user_id = st.session_state.user_id
    user_doc_ref = db.collection("users").document(user_id)
    user_doc = user_doc_ref.get()
    user_role = "user"
    
    if user_doc.exists:
        user_role = user_doc.to_dict().get("role", "user")
    else:
        user_doc_ref.set({"email": st.session_state.user.email, "role": "user"})
        st.warning("User data not found in Firestore. A new record has been created.")

    # ---------------------- Kanban Style Layout ---------------------- #
    st.write("### Hedging Plan (Kanban Style)")
    
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    num_months = 12
    
    # Budget Rate
    st.write("#### Budget Rate")
    st.session_state.budget_rate = float(st.number_input("Enter Budget Rate (EUR/PLN):", value=float(st.session_state.budget_rate), step=0.01))
    
    # Expected FX Flow
    st.write("#### Expected FX Flow")
    cols = st.columns(num_months)
    for i in range(num_months):
        with cols[i]:
            st.session_state.fx_flows[i] = int(st.number_input(f"{months[i]}", value=int(st.session_state.fx_flows[i]), step=10000, key=f"flow_{i}"))
    
    df = pd.DataFrame({"Month": months, "Expected FX Flow": st.session_state.fx_flows})
    
    # Hedge Ratio
    st.write("#### Hedge Ratio")
    hedge_ratios = []
    cols = st.columns(num_months)
    for i in range(num_months):
        with cols[i]:
            default_value = int(st.session_state.hedge_ratios[i])
            ratio = st.slider(f"{months[i]}", min_value=0, max_value=100, value=default_value, key=f"hedge_{i+1}")
            hedge_ratios.append(ratio / 100)
    
    # Update session state for hedge ratios to persist changes
    st.session_state.hedge_ratios = [int(r * 100) for r in hedge_ratios]
    df["Hedge Ratio"] = hedge_ratios
    df["Hedged Amount"] = df["Expected FX Flow"] * df["Hedge Ratio"]
    df["Budget Rate"] = st.session_state.budget_rate

    # ---------------------- Chart Visualization ---------------------- #
    st.write("### Hedging vs Budget Rate")
    fig, ax = plt.subplots()
    ax.plot(months, df["Hedged Amount"], marker='o', label='Hedged Amount')
    ax.axhline(y=st.session_state.budget_rate, color='r', linestyle='--', label='Budget Rate')
    ax.set_ylabel("Hedged Amount (EUR)")
    ax.set_xlabel("Months")
    ax.legend()
    st.pyplot(fig)
    
    # ---------------------- Save Updated Data ---------------------- #
    def save_data(df, user_id):
        try:
            doc_ref = db.collection("hedging_data").document(user_id)
            doc_ref.set({"data": df.to_dict(orient="records")})
            st.success("Hedging data saved successfully!")
        except Exception as e:
            st.error(f"Error saving data: {e}")
    
    save_data(df, user_id)
