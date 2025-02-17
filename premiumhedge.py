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

# Streamlit Authentication
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

    # ---------------------- Load or Save Data from Firestore ---------------------- #
    def load_data(user_id):
        doc_ref = db.collection("hedging_data").document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            return pd.DataFrame(doc.to_dict()["data"])
        else:
            return None

    def save_data(df, user_id):
        doc_ref = db.collection("hedging_data").document(user_id)
        doc_ref.set({"data": df.to_dict(orient="records")})

    data_loaded = load_data(user_id)

    # ---------------------- User Inputs ---------------------- #
    user_type = st.radio("Select Business Type:", ["Exporter", "Importer"], horizontal=True)

    st.write("### Expected FX Flows (12-Month View)")
    cols = st.columns(4)
    data = []
    num_months = 12

    for i in range(num_months):
        with cols[i % 4]:
            amount = st.number_input(f"Month {i+1}", value=100000 if data_loaded is None or "Expected FX Flow" not in data_loaded.columns else int(data_loaded.iloc[i]["Expected FX Flow"]), step=10000, key=f"flow_{i+1}")
            data.append(amount)

    df = pd.DataFrame({"Month": range(1, num_months + 1), "Expected FX Flow": data})

    # User-defined budget rate and hedging limits
    budget_rate = st.number_input("Enter Budget Rate (EUR/PLN):", value=4.40 if data_loaded is None or "Budget Rate" not in data_loaded.columns else float(data_loaded.iloc[0]["Budget Rate"]), step=0.01)
    if user_type == "Importer":
        max_hedge_price = st.number_input("Set Max Hedge Price (No Forward Hedge Above):", value=4.35 if data_loaded is None or "Max Hedge Price" not in data_loaded.columns else float(data_loaded.iloc[0]["Max Hedge Price"]), step=0.01)
    if user_type == "Exporter":
        min_hedge_price = st.number_input("Set Min Hedge Price (No Forward Hedge Below):", value=4.25 if data_loaded is None or "Min Hedge Price" not in data_loaded.columns else float(data_loaded.iloc[0]["Min Hedge Price"]), step=0.01)

    # Hedge ratio selection per month
    st.write("### Hedge Ratios (12-Month View)")
    cols = st.columns(4)
    hedge_ratios = []

    for i in range(num_months):
        with cols[i % 4]:
            default_value = 75 if data_loaded is None or "Hedge Ratio" not in data_loaded.columns else int(data_loaded.iloc[i].get("Hedge Ratio", 75))
            ratio = st.slider(f"Month {i+1}", min_value=0, max_value=100, value=default_value, key=f"hedge_{i+1}")
            hedge_ratios.append(ratio / 100)

    df["Hedge Ratio"] = hedge_ratios

    # ---------------------- Display Data ---------------------- #
    st.write("### Hedging Data Table")
    st.dataframe(df)
    
    # ---------------------- Save Updated Data ---------------------- #
    save_data(df, user_id)
