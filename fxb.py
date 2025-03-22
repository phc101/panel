import streamlit as st
from web3 import Web3
import json
import os

st.set_page_config(page_title="Blockchain FX App", layout="centered")
st.title("💱 Local FX Converter DApp")
st.markdown("Mint and convert EURx ↔ USDx using smart contracts.")

# -------------------------
# Debug: Show working directory
# -------------------------
st.write("📂 Working directory:", os.getcwd())

# -------------------------
# Load contract ABIs
# -------------------------

erc20_path = os.path.abspath("artifacts/contracts/ERC20Token.sol/ERC20Token.json")
fx_path = os.path.abspath("artifacts/contracts/FXConverter.sol/FXConverter.json")

st.write("🔍 ERC20 ABI path:", erc20_path)
st.write("🔍 FXConverter ABI path:", fx_path)

try:
    with open(erc20_path) as f:
        token_abi = json.load(f)["abi"]
    with open(fx_path) as f:
        fx_abi = json.load(f)["abi"]
except FileNotFoundError:
    st.error("❌ ABI file not found. Please check the path and run `npx hardhat compile`.")
    st.stop()

# -------------------------
# Connect to blockchain
# -------------------------

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

if not w3.is_connected():
    st.error("❌ Could not connect to Hardhat local node. Make sure it's running with `npx hardhat node`.")
    st.stop()

accounts = w3.eth.accounts
user_address = st.selectbox("Select wallet", accounts)

# -------------------------
# Set deployed contract addresses (copy from your deploy output)
# -------------------------

TOKEN_ADDRESSES = {
    "EURx": "0xYourEurxAddressHere",
    "USDx": "0xYourUsdxAddressHere"
}

FX_CONVERTER_ADDRESS = "0xYourFxConverterAddressHere"

# -------------------------
# Load contract instances
# -------------------------

eurx = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESSES["EURx"]), abi=token_abi)
usdx = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESSES["USDx"]), abi=token_abi)
converter = w3.eth.contract(address=Web3.to_checksum_address(FX_CONVERTER_ADDRESS), abi=fx_abi)

# -------------------------
# Show Balances
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
# Mint Tokens (Admin only)
# -------------------------

st.subheader("🪙 Mint EURx (admin only)")

mint_amount = st.number_input("Amount to mint", min_value=0.0, value=10.0, step=1.0)

if st.button("Mint"):
    tx_hash = eurx.functions.mint(user_address, int(mint_amount * 1e18)).transact({"from": accounts[0]})
    w3.eth.wait_for_transaction_receipt(tx_hash)
    st.success("✅ Minted successfully!")
    st.rerun()

# -------------------------
# Convert EURx to USDx
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
