import streamlit as st
import hashlib
import time

# --- BLOCK & BLOCKCHAIN CLASSES ---
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

# --- STREAMLIT APP LOGIC ---
st.set_page_config(page_title="Toy Blockchain", layout="wide")
st.title("🔗 Simple Blockchain Demo in Python")

# Initialize session state
if 'blockchain' not in st.session_state:
    st.session_state.blockchain = Blockchain()

# Add new block
with st.form("add_block_form"):
    data = st.text_input("Enter transaction data", value="Alice pays Bob 5 BTC")
    submitted = st.form_submit_button("Add Block")
    if submitted:
        st.session_state.blockchain.add_block(data)
        st.success("✅ Block added!")

# Show blockchain
st.subheader("📜 Blockchain Explorer")

for block in st.session_state.blockchain.chain:
    st.markdown(f"**Block #{block.index}**")
    st.code(f"Hash: {block.hash}\nPrev Hash: {block.previous_hash}\nData: {block.data}\nTime: {block.timestamp}")
    st.markdown("---")

# Validate chain
is_valid = st.session_state.blockchain.is_chain_valid()
if is_valid:
    st.success("✅ Blockchain is valid.")
else:
    st.error("❌ Blockchain has been tampered with!")
