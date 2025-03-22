import streamlit as st
import hashlib
import time

# ✅ Set page config FIRST
st.set_page_config(page_title="Toy Blockchain", layout="wide")

# --- BLOCK CLASS ---
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

# --- BLOCKCHAIN CLASS ---
class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        return Block(0, "0", time.time(), "Genesis Block")

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, data):
        previous_block = self.get_latest_block()
        new_index = previous_block.index + 1
        new_timestamp = time.time()
        new_block = Block(new_index, previous_block.hash, new_timestamp, data)
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

# --- INIT BLOCKCHAIN ---
if 'blockchain' not in st.session_state:
    st.session_state.blockchain = Blockchain()

# --- SIDEBAR ---
st.sidebar.title("Blockchain Controls")

with st.sidebar.form("add_block"):
    tx_data = st.text_input("Transaction Data", value="Alice pays Bob 5 BTC")
    submitted = st.form_submit_button("Add Block")
    if submitted:
        st.session_state.blockchain.add_block(tx_data)
        st.success("✅ Block added!")

# --- MAIN VIEW ---
st.title("🔗 Simple Blockchain Explorer")

for block in st.session_state.blockchain.chain:
    with st.expander(f"Block #{block.index}"):
        st.write(f"**Timestamp**: {block.timestamp}")
        st.write(f"**Data**: {block.data}")
        st.write(f"**Nonce**: {block.nonce}")
        st.write(f"**Hash**: `{block.hash}`")
        st.write(f"**Previous Hash**: `{block.previous_hash}`")

# --- VALIDATION ---
st.subheader("🔐 Blockchain Integrity Check")
is_valid = st.session_state.blockchain.is_chain_valid()
if is_valid:
    st.success("✅ Blockchain is valid.")
else:
    st.error("❌ Blockchain has been tampered with!")

# --- OPTIONAL HACK BUTTON ---
if st.button("💣 Tamper with Block #1"):
    if len(st.session_state.blockchain.chain) > 1:
        st.session_state.blockchain.chain[1].data = "🔥 Someone stole 1000 BTC!"
        st.warning("⚠️ Block #1 has been tampered with!")
    else:
        st.info("Add at least 2 blocks to try tampering.")
