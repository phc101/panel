import streamlit as st
import datetime
import pandas as pd
from database import get_connection

st.title("💸 Payments")

conn = get_connection()
cursor = conn.cursor()

# --- Load client list ---
cursor.execute("SELECT name FROM clients ORDER BY name")
client_names = [row[0] for row in cursor.fetchall()]

# --- Add New Payment ---
with st.form("add_payment"):
    st.subheader("➕ Add Payment")

    client_name = st.selectbox("Client", client_names if client_names else ["<no clients>"])
    amount = st.number_input("Amount", step=0.01)
    currency = st.selectbox("Currency", ["EUR", "USD", "PLN", "GBP"])
    direction = st.radio("Direction", ["Incoming", "Outgoing"])
    status = st.selectbox("Status", ["Paid", "Unpaid"])
    payment_date = st.date_input("Payment Date", value=datetime.date.today())
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Add Payment")

    if submitted and client_name != "<no clients>":
        cursor.execute("""
            INSERT INTO payments (
                client_name, amount, currency, direction,
                payment_date, notes, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (client_name, amount, currency, direction,
              payment_date.isoformat(), notes, status))
        conn.commit()
        st.success(f"{direction} payment of {amount} {currency} added for {client_name}.")

# --- Filter Section ---
st.subheader("🔍 Filter Payments")

selected_client = st.selectbox("Filter by Client", ["All"] + client_names)
selected_currency = st.selectbox("Filter by Currency", ["All", "EUR", "USD", "PLN", "GBP"])
selected_status = st.selectbox("Filter by Status", ["All", "Paid", "Unpaid"])

query = "SELECT client_name, amount, currency, direction, payment_date, status, notes FROM payments WHERE 1=1"
params = []

if selected_client != "All":
    query += " AND client_name = ?"
    params.append(selected_client)

if selected_currency != "All":
    query += " AND currency = ?"
    params.append(selected_currency)

if selected_status != "All":
    query += " AND status = ?"
    params.append(selected_status)

query += " ORDER BY payment_date DESC"
df = pd.read_sql_query(query, conn, params=params)

# --- Display Table ---
st.subheader("📋 Payments Table")

if not df.empty:
    st.dataframe(df)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Filtered CSV", csv, "filtered_payments.csv", "text/csv")
else:
    st.info("No payments found with current filters.")
