import streamlit as st
from datetime import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Function to calculate forward rate
def calculate_forward_rate(spot_rate, domestic_rate, foreign_rate, days):
    if days <= 0:
        return 0
    years = days / 365
    return spot_rate * ((1 + domestic_rate) / (1 + foreign_rate)) ** years

# Function to calculate margin
def calculate_margin(days):
    months = days // 30
    base_margin = 0.002  # 0.20%
    additional_margin = 0.001 * months  # +0.10% per month
    return base_margin + additional_margin

# Function to send email
def send_email(subject, body, recipient):
    sender_email = "your_email@example.com"  # Replace with your email
    sender_password = "your_password"  # Replace with your email password or app-specific password
    smtp_server = "smtp.example.com"  # Replace with your SMTP server (e.g., smtp.gmail.com for Gmail)
    smtp_port = 587  # Usually 587 for TLS

    # Create the email
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Secure connection
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient, msg.as_string())
            return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

# Initialize session state for monthly cashflows
if "monthly_cashflows" not in st.session_state:
    st.session_state.monthly_cashflows = {month: [] for month in range(1, 13)}

if "selected_month" not in st.session_state:
    st.session_state.selected_month = 1  # Default to January

# Define months for navigation
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June", 
    "July", "August", "September", "October", "November", "December"
]

# Global interest rates
with st.sidebar:
    st.header("Global Settings")
    global_domestic_rate = st.slider("Global Domestic Interest Rate (%)", 0.0, 10.0, 5.0, step=0.25) / 100
    global_foreign_rate = st.slider("Global Foreign Interest Rate (%)", 0.0, 10.0, 3.0, step=0.25) / 100

# Horizontal bookmarks for month navigation
st.write("### Select Month to Plan Cashflows")
selected_month = st.radio(
    "Months", MONTH_NAMES, index=st.session_state.selected_month - 1, horizontal=True
)
st.session_state.selected_month = MONTH_NAMES.index(selected_month) + 1

# Sidebar for managing cashflows
with st.sidebar:
    st.header(f"Add Cashflow for {selected_month}")
    currency = st.selectbox("Currency", ["EUR", "USD"], key="currency")
    amount = st.number_input("Cashflow Amount", min_value=0.0, value=1000.0, step=100.0, key="amount")
    future_date = st.date_input("Future Date", min_value=datetime.today(), key="future_date")
    spot_rate = st.number_input("Spot Rate", min_value=0.0, value=4.5, step=0.01, key="spot_rate")

    # Automatically update the selected month based on future date
    future_month = future_date.month
    if st.session_state.selected_month != future_month:
        st.session_state.selected_month = future_month

    if st.button("Add Cashflow"):
        st.session_state.monthly_cashflows[future_month].append({
            "Currency": currency,
            "Amount": amount,
            "Future Date": future_date,
            "Spot Rate": spot_rate,
        })

# Aggregated view of all positions
st.header("Aggregated Cashflow Summary")
all_results = []
for month, cashflows in st.session_state.monthly_cashflows.items():
    for cashflow in cashflows:
        days = (cashflow["Future Date"] - datetime.today().date()).days
        forward_rate = calculate_forward_rate(
            cashflow["Spot Rate"], global_domestic_rate, global_foreign_rate, days
        )
        margin = calculate_margin(days)
        forward_rate_with_margin = forward_rate * (1 + margin)
        pln_value = forward_rate_with_margin * cashflow["Amount"]
        profit = (forward_rate_with_margin - forward_rate) * cashflow["Amount"]
        all_results.append({
            "Month": MONTH_NAMES[month - 1],
            "Currency": cashflow["Currency"],
            "Amount": cashflow["Amount"],
            "Future Date": cashflow["Future Date"],
            "Spot Rate": cashflow["Spot Rate"],
            "Forward Rate": round(forward_rate, 4),
            "Forward Rate (with Margin)": round(forward_rate_with_margin, 4),
            "PLN Value": round(pln_value, 2),
            "Profit from Margin": round(profit, 2),
        })

# Display aggregated table
if all_results:
    aggregated_df = pd.DataFrame(all_results)
    st.table(aggregated_df)

    # Button to send order to dealer
    if st.button("Send it to Dealer"):
        # Format the email content
        email_body = aggregated_df.to_csv(index=False)
        subject = "Forward Order"
        recipient = "tomek@phc.com.pl"

        # Send email
        if send_email(subject, email_body, recipient):
            st.success("Order sent successfully!")
else:
    st.info("No cashflows added yet.")

# Footer
st.markdown("---")
st.caption("Developed using Streamlit")
