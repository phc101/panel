import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import firebase_admin
from firebase_admin import credentials, auth, firestore

# ---------------------- Firebase Authentication & Database ---------------------- #
cred = credentials.Certificate("firebase_credentials.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Streamlit Authentication
st.title("Automatic FX Hedging System")
login_status = False

user_email = st.text_input("Enter your Email:")
password = st.text_input("Enter your Password:", type="password")

if st.button("Login"):
    try:
        user = auth.get_user_by_email(user_email)
        st.success(f"Logged in as {user.email}")
        login_status = True
    except:
        st.error("Invalid credentials or user not found.")

if login_status:
    user_id = user.uid
    user_doc = db.collection("users").document(user_id).get()
    user_role = "user"
    
    if user_doc.exists:
        user_role = user_doc.to_dict().get("role", "user")
    else:
        db.collection("users").document(user_id).set({"email": user_email, "role": "user"})
    
    # ---------------------- Admin Dashboard ---------------------- #
    if user_role == "admin":
        st.write("### Admin Dashboard")
        users_ref = db.collection("users").stream()
        users_data = [user.to_dict() for user in users_ref]
        users_df = pd.DataFrame(users_data)
        st.dataframe(users_df)
        
        selected_user = st.selectbox("Select User to View Hedging Data:", users_df["email"] if not users_df.empty else [])
        
        if selected_user:
            selected_user_id = next((user.id for user in db.collection("users").stream() if user.to_dict().get("email") == selected_user), None)
            if selected_user_id:
                user_data_ref = db.collection("hedging_data").document(selected_user_id)
                user_data = user_data_ref.get()
                if user_data.exists:
                    user_df = pd.DataFrame(user_data.to_dict()["data"])
                    st.write(f"### Hedging Data for {selected_user}")
                    st.dataframe(user_df)
                else:
                    st.warning("No hedging data available for this user.")
    
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
            amount = st.number_input(f"Month {i+1}", value=100000 if data_loaded is None else int(data_loaded.iloc[i]["Expected FX Flow"]), step=10000, key=f"flow_{i+1}")
            data.append(amount)

    df = pd.DataFrame({"Month": range(1, num_months + 1), "Expected FX Flow": data})

    # User-defined budget rate and hedging limits
    budget_rate = st.number_input("Enter Budget Rate (EUR/PLN):", value=4.40 if data_loaded is None else float(data_loaded.iloc[0]["Budget Rate"]), step=0.01)
    if user_type == "Importer":
        max_hedge_price = st.number_input("Set Max Hedge Price (No Forward Hedge Above):", value=4.35 if data_loaded is None else float(data_loaded.iloc[0]["Max Hedge Price"]), step=0.01)
    if user_type == "Exporter":
        min_hedge_price = st.number_input("Set Min Hedge Price (No Forward Hedge Below):", value=4.25 if data_loaded is None else float(data_loaded.iloc[0]["Min Hedge Price"]), step=0.01)

    # Hedge ratio selection per month
    st.write("### Hedge Ratios (12-Month View)")
    cols = st.columns(4)
    hedge_ratios = []

    for i in range(num_months):
        with cols[i % 4]:
            ratio = st.slider(f"Month {i+1}", min_value=0, max_value=100, value=75 if data_loaded is None else int(data_loaded.iloc[i]["Hedge Ratio"]), key=f"hedge_{i+1}")
            hedge_ratios.append(ratio / 100)

    df["Hedge Ratio"] = hedge_ratios

    # ---------------------- Market Data & Forward Pricing ---------------------- #
    spot_rate = st.number_input("Current Spot Rate (EUR/PLN):", value=4.38, step=0.01)
    forward_points = st.number_input("Forward Points (Annualized %):", value=0.91, step=0.01) / 100

    forward_rates = [spot_rate * (1 + forward_points * (i / 12)) for i in range(1, num_months + 1)]
    df["Forward Rate"] = forward_rates

    # ---------------------- Hedge Execution Logic ---------------------- #
    def calculate_hedge(df, user_type, max_hedge_price=None, min_hedge_price=None):
        hedged_amounts = []
        final_hedge_ratios = []
        
        for index, row in df.iterrows():
            forward_rate = row["Forward Rate"]
            hedge_ratio = row["Hedge Ratio"]
            
            if user_type == "Importer" and forward_rate > max_hedge_price:
                hedge_ratio = 0
            elif user_type == "Exporter" and forward_rate < min_hedge_price:
                hedge_ratio = 0
            
            hedged_amount = row["Expected FX Flow"] * hedge_ratio
            hedged_amounts.append(hedged_amount)
            final_hedge_ratios.append(hedge_ratio)
        
        df["Final Hedge Ratio"] = final_hedge_ratios
        df["Hedged Amount"] = hedged_amounts
        return df

    df = calculate_hedge(df, user_type, max_hedge_price if user_type == "Importer" else None, min_hedge_price if user_type == "Exporter" else None)
    save_data(df, user_id)
