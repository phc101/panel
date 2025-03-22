import streamlit as st
import hashlib
import time
import json

# --- MUST BE FIRST STREAMLIT COMMAND ---
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
        block_content = f"{self.index}{self.previous_hash}{self.timestamp}{json.dumps(self.transactions, sort_keys=True)}{self.nonce}"
        return hashlib.sha256(block_content.encode()).hexdigest()

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
            prev = self.chain[i - 1]
            if current.hash != current.calculate_hash():
                return False
            if current.previous_hash != prev.hash:
                return False
        return True

# --- STREAMLIT APP STARTS HERE ---
if 'blockchain' not in st.session_state:
    st.session_state.blockchain = Blockchain()

bchain = st.session_state.blockchain
wallets = ["Alice", "Bob", "Charlie"]

st.title("💼 Blockchain with Wallets, Balances & Mining")

# --- BALANCE OVERVIEW ---
st.subheader("💰 Wallet Balances")
cols = st.columns(len(wallets))
for i, wallet in enumerate(wallets):
    cols[i].metric(label=wallet, value=f"{bchain.get_balance(wallet):.1f} coins")

# --- TRANSACTION FORM ---
st.subheader("🧾 Create a Transaction")

with st.form("tx_form"):
    sender = st.selectbox("Sender", ["SYSTEM"] + wallets)
    recipient = st.selectbox("Recipient", wallets)
    amount = st.number_input("Amount", min_value=0.1, step=0.1)
    submitted = st.form_submit_button("Add Transaction")

    if submitted:
        if sender == recipient:
            st.error("Sender and recipient must be different.")
        else:
            success = bchain.add_transaction(sender, recipient, amount)
            if success:
                st.success("✅ Transaction added to pending pool.")
            else:
                st.error("❌ Insufficient balance.")

# --- MINE BLOCK ---
st.subheader("⛏️ Mine Pending Transactions")
miner = st.selectbox("Select Miner", wallets)
if st.button("Mine Block"):
    with st.spinner("Mining in progress..."):
        mined = bchain.mine_pending_transactions(miner)
        if mined:
            st.success("✅ Block successfully mined and added.")
        else:
            st.info("No transactions to mine.")

# --- BLOCKCHAIN EXPLORER ---
st.subheader("📦 Blockchain Explorer")
for block in bchain.chain:
    with st.expander(f"Block #{block.index}"):
        st.write(f"Timestamp: {block.timestamp}")
        st.write(f"Nonce: {block.nonce}")
        st.write(f"Previous Hash: `{block.previous_hash}`")
        st.write(f"Hash: `{block.hash}`")
        st.write("Transactions:")
        for tx in block.transactions:
            if isinstance(tx, str):
                st.write(f"- {tx}")
            else:
                st.write(f"- {tx['sender']} → {tx['recipient']} : {tx['amount']} coins")

# --- VALIDATE CHAIN ---
st.subheader("🔐 Blockchain Integrity")
if bchain.is_chain_valid():
    st.success("✅ Chain is valid.")
else:
    st.error("❌ Chain has been tampered with!")
