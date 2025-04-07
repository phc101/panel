import streamlit as st
import datetime
from database import get_connection

st.title("🛡️ Hedging Simulation")

# Connect to database
conn = get_connection()
cursor = conn.cursor()

# Get clients for dropdown
cursor.execute("SELECT name FROM clients ORDER BY name")
client_names = [row[0] for row in cursor.fetchall()]

# --- Hedge Form ---
with st.form("hedge_form"):
    client_name = st.selectbox("Client", client_names if client_names else ["<no clients>"])
    hedge_type = st.selectbox("Hedge Type", ["Forward", "Call Option", "Put Option", "Synthetic Forward"])
    notional = st.number_input("Notional Amount", step=1000.0)
    currency = st.selectbox("Currency", ["EUR", "USD", "PLN", "GBP"])
    strike = st.number_input("Strike Rate", step=0.0001, format="%.4f")
    maturity = st.date_input("Maturity Date", min_value=datetime.date.today())
    premium = st.number_input("Option Premium", step=0.01)

    submitted = st.form_submit_button("Add Hedge")

    if submitted:
        if client_name == "<no clients>":
            st.error("Please add a client first.")
        else:
            cursor.execute("""
                INSERT INTO hedges (
                    client_name, hedge_type, notional, currency, strike, maturity, premium
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                client_name, hedge_type, notional, currency, strike,
                maturity.isoformat(), premium
            ))
            conn.commit()
            st.success(f"Hedge for {client_name} added!")

# --- Show Recent Hedges ---
st.subheader("📋 Recent Hedges")

cursor.execute("""
    SELECT client_name, hedge_type, notional, currency, strike, maturity
    FROM hedges
    ORDER BY maturity ASC
    LIMIT 10
""")
hedges = cursor.fetchall()

if hedges:
    for h in hedges:
        st.write(
            f"**{h[0]}** — {h[1]} of {h[2]:,.0f} {h[3]} @ {h[4]:.4f}, matures {h[5]}"
        )
else:
    st.info("No hedging positions recorded yet.")
