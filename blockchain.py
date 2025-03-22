import streamlit as st
import hashlib
import time
import json

# --- CONFIG ---
st.set_page_config(page_title="Blockchain with Wallets", layout="wide")

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

# --- INIT ---
if 'blockchain' not in st.session_state:
    st.session_state.blockchain = Blockchain()

b = st.session_state.blockchain
wallets = ["Alice", "Bob", "Charlie"]

st.title("💼 Blockchain with Wallets, Mining, and Top-Ups")

# --- BALANCES ---
st.subheader("💰 Wallet Balances (after mining only)")
cols = st.columns(len(wallets))
for i, wallet in enumerate(wallets):
    cols[i].metric(label=wallet, value=f"{b.get_balance(wallet):.1f} coins")

st.caption(f"🕒 Pending transactions: {len(b.pending_transactions)} — you must mine them for balances to update.")

# --- TOP-UP FORM ---
st.subheader("💸 Top Up Wallet (SYSTEM → User)")

with st.form("topup_form"):
    target = st.selectbox("Select Wallet", wallets, key="topup_wallet")
    topup_amount = st.number_input("Amount", min_value=0.1, step=0.1, key="topup_amt")
    topup_submit = st.form_submit_button("Top Up")

    if topup_submit:
        b.add_transaction("SYSTEM", target, topup_amount)
        st.success(f"Added {topup_amount:.1f} coins to {target} — now mine to confirm.")

# --- SEND TRANSACTION ---
st.subheader("🧾 Send a Transaction")

with st.form("tx_form"):
    sender = st.selectbox("Sender", wallets, key="tx_sender")
    recipient = st.selectbox("Recipient", [w for w in wallets if w != sender], key="tx_recipient")
    amount = st.number_input("Amount", min_value=0.1, step=0.1, key="tx_amount")
    tx_submit = st.form_submit_button("Send")

    if tx_submit:
        success = b.add_transaction(sender, recipient, amount)
        if success:
            st.success("✅ Transaction added to pending pool. Now mine it to finalize.")
        else:
            st.error("❌ Insufficient balance. You may need to mine first.")

# --- MINING ---
st.subheader("⛏️ Mine Pending Transactions")
miner = st.selectbox("Choose Miner", wallets, key="miner_select")
if st.button("Mine Now"):
    with st.spinner("Mining..."):
        result = b.mine_pending_transactions(miner)
        if result:
            st.success(f"✅ Block mined! {miner} received 50 coin reward.")
        else:
            st.info("Nothing to mine.")

# --- EXPLORER ---
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

# --- VALIDATION ---
st.subheader("🔐 Blockchain Integrity")
if b.is_chain_valid():
    st.success("✅ Chain is valid.")
else:
    st.error("❌ Chain is invalid!")
