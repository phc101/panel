import streamlit as st
import requests
import pandas as pd
import hashlib
import base64
import uuid
import datetime
import time
import threading

# iBanFirst API Configuration (Sandbox)
API_BASE_URL = "https://sandbox.ibanfirst.com/api"
API_USERNAME = "your_username"
API_SECRET = "your_secret"

# Global variable to control monitoring
monitoring_active = False

# Function to generate X-WSSE authentication header
def generate_wsse_header(username, secret):
    nonce = base64.b64encode(uuid.uuid4().bytes).decode("utf-8")
    created = datetime.datetime.utcnow().isoformat() + "Z"
    digest = base64.b64encode(
        hashlib.sha256((nonce + created + secret).encode()).digest()
    ).decode("utf-8")
    
    return f'UsernameToken Username="{username}", PasswordDigest="{digest}", Nonce="{nonce}", Created="{created}"'

# Function to fetch forward FX rates
def get_forward_rate(base_currency, quote_currency, tenor):
    url = f"{API_BASE_URL}/rates/{base_currency}{quote_currency}"
    headers = {"X-WSSE": generate_wsse_header(API_USERNAME, API_SECRET)}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("forward_rates", {}).get(tenor)
    except Exception as e:
        st.error(f"Error fetching forward rate: {e}")
        return None

# Function to book a forward contract
def book_forward_contract(base_currency, quote_currency, amount, forward_rate, maturity_date):
    url = f"{API_BASE_URL}/trades/"
    headers = {"X-WSSE": generate_wsse_header(API_USERNAME, API_SECRET)}

    payload = {
        "currency_pair": f"{base_currency}{quote_currency}",
        "amount": amount,
        "rate": forward_rate,
        "maturity_date": maturity_date,
        "type": "FORWARD"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error booking forward contract: {e}")
        return None

# Function to send email notification (Optional)
def send_email_alert(to_email, base_currency, quote_currency, forward_rate):
    import smtplib
    from email.message import EmailMessage

    sender_email = "your_email@example.com"
    sender_password = "your_email_password"

    msg = EmailMessage()
    msg.set_content(
        f"🚀 Hedging Opportunity Alert!\n\n"
        f"The forward rate for {base_currency}/{quote_currency} has dropped to {forward_rate}.\n"
        f"Action Required: Consider booking a hedge now!"
    )
    msg["Subject"] = "FX Hedging Alert - iBanFirst"
    msg["From"] = sender_email
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        st.success(f"📧 Email alert sent to {to_email}")
    except Exception as e:
        st.error(f"Failed to send email: {e}")

# Background function to monitor FX rates
def monitor_fx_rates(base_currency, quote_currency, tenor, hedging_threshold, auto_execute, email_alert):
    global monitoring_active
    while monitoring_active:
        forward_rate = get_forward_rate(base_currency, quote_currency, tenor)
        if forward_rate:
            st.sidebar.write(f"📈 **Live Forward Rate:** {forward_rate}")

            if forward_rate <= hedging_threshold:
                st.sidebar.success("✅ Hedging opportunity detected!")

                # Auto-execute forward contract if enabled
                if auto_execute:
                    st.sidebar.write("⚡ Booking forward contract automatically...")
                    maturity_date = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
                    trade = book_forward_contract(base_currency, quote_currency, amount, forward_rate, maturity_date)

                    if trade:
                        st.sidebar.success("🚀 Forward contract booked successfully!")
                        if "trade_history" not in st.session_state:
                            st.session_state.trade_history = []
                        st.session_state.trade_history.append(trade)

                # Send email alert if enabled
                if email_alert:
                    send_email_alert("your_email@example.com", base_currency, quote_currency, forward_rate)

        time.sleep(30)  # Check rates every 30 seconds

# Streamlit App
st.title("🔄 FX Automatic Hedging Solution with Real-time Alerts & Start/Stop Monitoring")

# User input section
st.sidebar.header("Hedging Settings")
base_currency = st.sidebar.selectbox("Base Currency", ["EUR"])
quote_currency = st.sidebar.selectbox("Quote Currency", ["PLN"])
amount = st.sidebar.number_input("Amount to Hedge", min_value=1000, value=100000, step=1000)
tenor = st.sidebar.selectbox("Forward Tenor", ["1M", "3M", "6M", "12M"])
hedging_threshold = st.sidebar.slider("Max Acceptable Forward Rate", 4.20, 4.50, 4.35, 0.01)

# Alert settings
auto_execute = st.sidebar.checkbox("Auto-Execute Hedge when Rate is Good")
email_alert = st.sidebar.checkbox("Send Email Alert when Rate is Good")

# Start/Stop monitoring controls
if st.sidebar.button("Start Monitoring FX Rates"):
    if not monitoring_active:
        monitoring_active = True
        st.sidebar.write("⏳ Monitoring FX rates...")

        # Run monitoring function in a separate thread
        threading.Thread(
            target=monitor_fx_rates,
            args=(base_currency, quote_currency, tenor, hedging_threshold, auto_execute, email_alert),
            daemon=True
        ).start()
    else:
        st.sidebar.warning("Monitoring is already running!")

if st.sidebar.button("Stop Monitoring FX Rates"):
    monitoring_active = False
    st.sidebar.warning("⏹ Monitoring stopped.")

# Display trade history
if "trade_history" in st.session_state and st.session_state.trade_history:
    st.write("### 📊 Trade History")
    trade_df = pd.DataFrame(st.session_state.trade_history)
    st.dataframe(trade_df)
