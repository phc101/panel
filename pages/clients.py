import streamlit as st
import sqlite3
from database import get_connection

st.title("👤 Clients")

conn = get_connection()
cursor = conn.cursor()

# --- Add New Client Form ---
with st.form("add_client"):
    name = st.text_input("Client Name")
    base_currency = st.selectbox("Base Currency", ["EUR", "USD", "PLN", "GBP"])
    industry = st.text_input("Industry")
    submitted = st.form_submit_button("Add Client")

    if submitted:
        cursor.execute(
            "INSERT INTO clients (name, base_currency, industry) VALUES (?, ?, ?)",
            (name, base_currency, industry)
        )
        conn.commit()
        st.success(f"Client '{name}' added successfully!")

# --- Display Existing Clients ---
st.subheader("📋 Client List")

cursor.execute("SELECT name, base_currency, industry FROM clients ORDER BY name")
clients = cursor.fetchall()

if clients:
    for c in clients:
        st.write(f"**{c[0]}** — {c[1]} — {c[2]}")
else:
    st.info("No clients found.")

