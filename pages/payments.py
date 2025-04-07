import streamlit as st
import datetime
import sqlite3
from database import get_connection

st.title("💸 Payments")

conn = get_connection()
cursor = conn.cursor()

# --- Payment Form ---
with st.form("add_payment"):
    cursor.execute("SELECT name FROM clients ORDER BY name")
    client_names = [row[0] for row in cursor.fetchall()]
    
    client_name = st.selectbox("Client", client_names if client_names else ["<no clients>"])
    amount = st.number_input("Amount", step=0.01)
    currency = st.selectbox("Currency", ["EUR", "USD", "PLN", "GBP"])
    direction = st.radio("Direction", ["Incoming", "Outgoing"])
    payment_date = st.date_input("Payment Date", value=datetime.date.today())
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Add Payment")
    if submitted:
        if "<no clients>" in client_name:
            st.error("Please add a client first.")
        else:
            cursor.execute("""
                INSERT INTO payments (client_name, amount, currency, direction, payment_date, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (client_name, amount, currency, direction, payment_date.isoformat(), notes))
            conn.commit()
            st.success(f"Payment of {amount} {currency} for {client_name} recorded!")

# --- Payment Table ---
st.subheader("📋 Recent Payments")

cursor.execute("""
    SELECT client_name, amount, currency, direction, payment_date
    FROM payments
    ORDER BY payment_date DESC
    LIMIT 10
""")
payments = cursor.fetchall()

if payments:
    for p in payments:
        st.write(f"**{p[0]}** — {p[3]} {p[1]:,.2f} {p[2]} on {p[4]}")
else:
    st.info("No payments recorded yet.")
