import streamlit as st
from database import get_connection

st.title("👤 Clients")

conn = get_connection()
cursor = conn.cursor()

# --- Add New Client ---
with st.form("add_client"):
    st.subheader("➕ Add New Client")

    name = st.text_input("Client Name")
    base_currency = st.selectbox("Base Currency", ["EUR", "USD", "PLN", "GBP"])
    industry = st.text_input("Industry")
    payment_terms = st.selectbox("Payment Terms", ["30 days", "45 days", "60 days", "Advance"])
    budget_rate = st.number_input("FX Budget Rate", step=0.0001, format="%.4f")
    risk_profile = st.selectbox("Risk Profile", ["Low", "Moderate", "High"])
    tags = st.text_input("Tags (comma-separated)")
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Add Client")

    if submitted and name:
        cursor.execute("""
            INSERT INTO clients (
                name, base_currency, industry,
                payment_terms, budget_rate, risk_profile, tags, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, base_currency, industry,
            payment_terms, budget_rate, risk_profile, tags, notes
        ))
        conn.commit()
        st.success(f"Client '{name}' added!")

# --- View Clients ---
st.subheader("📋 Client List")

cursor.execute("""
    SELECT name, base_currency, industry, payment_terms,
           budget_rate, risk_profile, tags, notes
    FROM clients
    ORDER BY name
""")
clients = cursor.fetchall()

if clients:
    for c in clients:
        with st.expander(f"{c[0]}"):
            st.markdown(f"""
            - **Base Currency**: {c[1]}  
            - **Industry**: {c[2]}  
            - **Payment Terms**: {c[3]}  
            - **Budget Rate**: {c[4]:.4f}  
            - **Risk Profile**: {c[5]}  
            - **Tags**: {c[6]}  
            - **Notes**: {c[7] or "—"}
            """)
else:
    st.info("No clients added yet.")
