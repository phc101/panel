import streamlit as st
import hashlib
import time

# ✅ MUST BE FIRST STREAMLIT CALL
st.set_page_config(page_title="Toy Blockchain with Mining", layout="wide")

# --- BLOCK CLASS WITH PROOF OF WORK ---
class Block:
    def __init__(self, index, previous_hash, timestamp, data, nonce=0):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.index}{self.previous_hash}{self.timestamp}{self.data}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty):
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()

# --- BLOCKCHAIN CLASS ---
class Blockchain:
    def __init__(self, difficulty=4):
        self.difficulty = difficulty
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        genesis_block = Block(0, "0", time.time(), "Genesis Block")
        genesis_block.mine_block(self.difficulty)
        return genesis_block

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, data):
        previous_block = self.get_latest_block()
        new_index = previous_block.index + 1
        new_timestamp = time.time()
        new_block = Block(new_index, previous_block.hash, new_timestamp, data)
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.calculate_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
        return True

# --- INIT BLOCKCHAIN IN SESSION STATE ---
if 'blockchain' not in st.session_state:
    st.session_state.blockchain = Blockchain(difficulty=4)

# --- SIDEBAR: ADD BLOCK ---
st.sidebar.title("⛏️ Mine a New Block")

with st.sidebar.form("add_block"):
    tx_data = st.text_input("Transaction Data", value="Alice pays Bob 5 BTC")
    submitted = st.form_submit_button("Mine Block")
    if submitted:
        with st.spinner("⛏️ Mining in progress..."):
            st.session_state.blockchain.add_block(tx_data)
        st.success("✅ Block mined and added!")

# --- MAIN APP: DISPLAY CHAIN ---
st.title("🔗 Toy Blockchain with Proof of Work")

for block in st.session_state.blockchain.chain:
    with st.expander(f"📦 Block #{block.index}"):
        st.markdown(f"**Timestamp**: {block.timestamp}")
        st.markdown(f"**Data**: {block.data}")
        st.markdown(f"**Nonce**: `{block.nonce}`")
        st.markdown(f"**Hash**: `{block.hash}`")
        st.markdown(f"**Previous Hash**: `{block.previous_hash}`")

# --- VALIDATE CHAIN ---
st.subheader("🔐 Blockchain Integrity Check")
if st.session_state.blockchain.is_chain_valid():
    st.success("✅ Blockchain is valid.")
else:
    st.error("❌ Blockchain has been tampered with!")

# --- OPTIONAL: TAMPER TEST BUTTON ---
if st.button("💣 Tamper with Block #1"):
    if len(st.session_state.blockchain.chain) > 1:
        st.session_state.blockchain.chain[1].data = "🔥 Hacked!"
        st.warning("⚠️ Block #1 has been tampered with!")
    else:
        st.info("ℹ️ Add at least one block to test tampering.")
