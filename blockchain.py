import streamlit as st
import hashlib
import time
import json
import pandas as pd  # For the balance-over-time chart

# --- PAGE CONFIG ---
st.set_page_config(page_title="Blockchain with Charts", layout="wide")

# --- BLOCK CLASS ---
class Block:
    def __init__(self, index, previous_hash, timestamp, transactions, nonce=0):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.transactions = transactions
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.index}{self.previous_hash}{self.timestamp}{json.dumps(self.transactions, sort_keys=True)}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty):
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()

# --- BLOCKCHAIN CLASS ---
class Blockchain:
    def __init__(self, difficulty=3):
        self.difficulty = difficulty
        self.chain = [self.create_genesis_block()]
        self.pending_transactions = []
        self.mining_reward = 50

    def create_genesis_block(self):
        genesis_block = Block(0, "0", time.time(), ["Genesis Block"])
        genesis_block.mine_block(self.difficulty)
        return genesis_block

    def get_latest_block(self):
        return self.chain[-1]

    def add_transaction(self, sender, recipient, amount):
        if sender != "SYSTEM" and self.get_balance(sender) < amount:
            return False
        self.pending_transactions.append({
            "sender": sender,
            "recipient": recipient,
            "amount": amount
        })
        return True

    def mine_pending_transactions(self, miner_address):
        if not self.pending_transactions:
            return None
        self.add_transaction("SYSTEM", miner_address, self.mining_reward)
        new_block = Block(
            len(self.chain),
            self.get_latest_block().hash,
            time.time(),
            self.pending_transactions
        )
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block

    def get_balance(self, address):
        balance = 0
        for block in self.chain:
            for tx in block.transactions:
                if isinstance(tx, dict):
                    if tx["sender"] == address:
                        balance -= tx["amount"]
                    if tx["recipient"] == address:
                        balance += tx["amount"]
        return balance

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.hash != current.calculate_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
        return True

# --- INIT STATE ---
if 'blockchain' not in st.session_state:
    st.session_state.blockchain = Blockchain()

b = st.session_state.blockchain
wallets = ["Alice", "Bob", "Charlie"]

st.title("💼 Blockchain App with Wallets, Mining, Mempool & Charts")

# --- BALANCES ---
st.subheader("💰 Wallet Balances")
cols = st.columns(len(wallets))
for i, wallet in enumerate(wallets):
    cols[i].metric(label=wallet, value=f"{b.get_balance(wallet):.1f} coins")

st.caption(f"🕒 Pending transactions: {len(b.pending_transactions)} — mine them to finalize.")

# --- TOP-UP ---
st.subheader("💸 Top-Up Wallet from SYSTEM")
with st.form("topup_form"):
    target = st.selectbox("Top-Up Wallet", wallets, key="topup_wallet")
    topup_amount = st.number_input("Amount", min_value=0.1, step=0.1)
    topup_submit = st.form_submit_button("Top Up")
    if topup_submit:
        b.add_transaction("SYSTEM", target, topup_amount)
        st.success(f"Added {topup_amount:.1f} coins to {target}. Now mine it!")

# --- SEND TRANSACTION ---
st.subheader("🧾 Send Transaction")
with st.form("tx_form"):
    sender = st.selectbox("Sender", wallets, key="tx_sender")
    recipient = st.selectbox("Recipient", [w for w in wallets if w != sender])
    amount = st.number_input("Amount", min_value=0.1, step=0.1)
    tx_submit = st.form_submit_button("Send")
    if tx_submit:
        success = b.add_transaction(sender, recipient, amount)
        if success:
            st.success("✅ Transaction added. Now mine it!")
        else:
            st.error("❌ Insufficient balance.")

# --- MINE BLOCK ---
st.subheader("⛏️ Mine Pending Transactions")
miner = st.selectbox("Miner", wallets, key="miner_select")
if st.button("Mine Now"):
    with st.spinner("Mining..."):
        result = b.mine_pending_transactions(miner)
        if result:
            st.success(f"✅ Block mined! {miner} earned 50 coins.")
        else:
            st.info("No transactions to mine.")

# --- BLOCKCHAIN EXPLORER ---
st.subheader("📦 Blockchain Explorer")
for block in b.chain:
    with st.expander(f"Block #{block.index}"):
        st.write(f"⏱ Timestamp: {block.timestamp}")
        st.write(f"🔢 Nonce: {block.nonce}")
        st.code(f"Hash: {block.hash}\nPrev: {block.previous_hash}")
        st.markdown("🧾 Transactions:")
        for tx in block.transactions:
            if isinstance(tx, str):
                st.markdown(f"- *{tx}*")
            else:
                st.markdown(f"- `{tx['sender']}` → `{tx['recipient']}`: `{tx['amount']}` coins")

# --- WALLET HISTORY ---
st.subheader("📜 View Wallet Transaction History")
selected_wallet = st.selectbox("Wallet for History", wallets, key="wallet_history")
history = []
balance = 0
for block in b.chain:
    for tx in block.transactions:
        if isinstance(tx, dict):
            if tx["sender"] == selected_wallet or tx["recipient"] == selected_wallet:
                direction = "Sent" if tx["sender"] == selected_wallet else "Received"
                other_party = tx["recipient"] if direction == "Sent" else tx["sender"]
                amount = -tx["amount"] if direction == "Sent" else tx["amount"]
                balance += amount
                history.append({
                    "Block": block.index,
                    "Timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(block.timestamp)),
                    "Direction": direction,
                    "Counterparty": other_party,
                    "Amount": f"{abs(tx['amount']):.1f}",
                    "Balance": f"{balance:.1f}"
                })
if history:
    st.dataframe(history)
else:
    st.info("This wallet has no transactions.")

# --- BALANCE OVER TIME CHART ---
st.subheader("📊 Balance Over Time")
wallet_for_chart = st.selectbox("Wallet for Chart", wallets, key="chart_wallet")
balance_timeline = []
running_balance = 0
for block in b.chain:
    for tx in block.transactions:
        if isinstance(tx, dict):
            if tx["sender"] == wallet_for_chart:
                running_balance -= tx["amount"]
            if tx["recipient"] == wallet_for_chart:
                running_balance += tx["amount"]
    balance_timeline.append({"Block": block.index, "Balance": running_balance})
chart_df = pd.DataFrame(balance_timeline)
st.line_chart(chart_df.set_index("Block"))

# --- MEMPOOL VIEWER ---
st.subheader("⏳ Pending Transactions (Mempool)")
if b.pending_transactions:
    tx_rows = []
    for tx in b.pending_transactions:
        if isinstance(tx, dict):
            tx_type = "Top-Up" if tx["sender"] == "SYSTEM" else "Transfer"
            tx_rows.append({
                "Sender": tx["sender"],
                "Recipient": tx["recipient"],
                "Amount": f"{tx['amount']:.1f}",
                "Type": tx_type
            })
    st.table(tx_rows)
else:
    st.success("✅ Mempool is empty.")

# --- VALIDATION ---
st.subheader("🔐 Blockchain Integrity")
if b.is_chain_valid():
    st.success("✅ Blockchain is valid.")
else:
    st.error("❌ Blockchain has been tampered with!")
    # --- ESCROW CONTRACT SIMULATOR ---
st.subheader("🧠 Escrow Smart Contract Simulation")

# Store in session state
if 'escrow' not in st.session_state:
    st.session_state.escrow = None

escrow = st.session_state.escrow

# Create Escrow Form
with st.form("escrow_form"):
    st.markdown("🔐 Create a new escrow contract")
    escrow_sender = st.selectbox("Escrow Sender", wallets, key="escrow_sender")
    escrow_recipient = st.selectbox("Escrow Recipient", [w for w in wallets if w != escrow_sender], key="escrow_recipient")
    escrow_amount = st.number_input("Amount to Escrow", min_value=0.1, step=0.1, key="escrow_amt")
    create_escrow = st.form_submit_button("Create Escrow")

    if create_escrow:
        if b.get_balance(escrow_sender) >= escrow_amount:
            st.session_state.escrow = {
                "sender": escrow_sender,
                "recipient": escrow_recipient,
                "amount": escrow_amount,
                "status": "Pending"
            }
            st.success(f"✅ {escrow_amount} coins placed into escrow from {escrow_sender}.")
        else:
            st.error("❌ Insufficient balance to fund escrow.")

# Display and manage escrow
if escrow := st.session_state.escrow:
    st.markdown(f"**Sender:** {escrow['sender']}  \n"
                f"**Recipient:** {escrow['recipient']}  \n"
                f"**Amount:** {escrow['amount']} coins  \n"
                f"**Status:** `{escrow['status']}`")

    if escrow['status'] == "Pending":
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Release to Recipient"):
                b.add_transaction(escrow['sender'], escrow['recipient'], escrow['amount'])
                escrow['status'] = "Released"
                st.success("✅ Funds released to recipient. Please mine to confirm.")

        with col2:
            if st.button("🔄 Refund to Sender"):
                escrow['status'] = "Refunded"
                st.success("🔁 Escrow canceled. Funds returned to sender.")

