import streamlit as st
from web3 import Web3
import json
import os

st.set_page_config(page_title="Blockchain FX App", layout="centered")
st.title("💱 Local FX Converter DApp")
st.markdown("Mint and convert EURx ↔ USDx using smart contracts.")

# -------------------------
# Load contract ABIs
# -------------------------

erc20_path = os.path.abspath("artifacts/contracts/ERC20Token.sol/ERC20Token.json")
fx_path = os.path.abspath("artifacts/contracts/FXConverter.sol/FXConverter.json")

try:
    with open(erc20_path) as f:
        token_abi = json.load(f)["abi"]
    with open(fx_path) as f:
        fx_abi = json.load(f)["abi"]
except FileNotFoundError:
    st.error("❌ ABI file not found. Run `npx hardhat compile` first.")
    st.stop()

# -------------------------
# Connect to local Hardhat network
# -------------------------

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

if not w3.is_connected():
    st.error("❌ Could not connect to Hardhat local node. Run `npx hardhat node`.")
    st.stop()

accounts = w3.eth.accounts
user_address = st.selectbox("Select your wallet", accounts)

# -------------------------
# ✅ Paste your deployed contract addresses here
# -------------------------

TOKEN_ADDRESSES = {
    "EURx": "0x5FbDB2315678afecb367f032d93F642f64180aa3",
    "USDx": "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"
}

FX_CONVERTER_ADDRESS = "0x9FE46736679d2D9a65F0992F2272de9f3c7fa6e0"

# -------------------------
# Create contract instances
# -------------------------

eurx = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESSES["EURx"]), abi=token_abi)
usdx = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESSES["USDx"]), abi=token_abi)
converter = w3.eth.contract(address=Web3.to_checksum_address(FX_CONVERTER_ADDRESS), abi=fx_abi)

# -------------------------
# Show balances
# -------------------------

def get_balances():
    b_eur = eurx.functions.balanceOf(user_address).call()
    b_usd = usdx.functions.balanceOf(user_address).call()
    return b_eur / 1e18, b_usd / 1e18

eur_balance, usd_balance = get_balances()
st.subheader("💰 Balances")
st.write(f"**EURx:** {eur_balance:.4f}")
st.write(f"**USDx:** {usd_balance:.4f}")

# -------------------------
# Mint EURx (admin only)
# -------------------------

st.subheader("🪙 Mint EURx")

mint_amount = st.number_input("Amount to mint", min_value=0.0, value=10.0, step=1.0)

if st.button("Mint"):
    tx = eurx.functions.mint(user_address, int(mint_amount * 1e18)).transact({"from": accounts[0]})
    w3.eth.wait_for_transaction_receipt(tx)
    st.success("✅ Minted successfully!")
    st.rerun()

# -------------------------
# Convert EURx → USDx
# -------------------------

st.subheader("🔁 Convert EURx → USDx")

convert_amount = st.number_input("Amount to convert", min_value=0.0, value=5.0, step=1.0)

if st.button("Convert"):
    amt = int(convert_amount * 1e18)
    eurx.functions.approve(FX_CONVERTER_ADDRESS, amt).transact({"from": user_address})
    tx = converter.functions.convert(eurx.address, usdx.address, amt).transact({"from": user_address})
    w3.eth.wait_for_transaction_receipt(tx)
    st.success("✅ Conversion complete!")
    st.rerun()
