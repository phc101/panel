import streamlit as st
from web3 import Web3
import os
import json



# Absolute path to ERC20Token ABI

erc20_path = os.path.abspath("artifacts/contracts/ERC20Token.sol/ERC20Token.json")
fx_path = os.path.abspath("artifacts/contracts/FXConverter.sol/FXConverter.json")

with open(erc20_path) as f:
    token_abi = json.load(f)["abi"]

with open(fx_path) as f:
    fx_abi = json.load(f)["abi"]


# Absolute path to FXConverter ABI
fx_path = os.path.join(os.getcwd(), "artifacts/contracts/FXConverter.sol/FXConverter.json")
with open(fx_path) as f:
    fx_abi = json.load(f)["abi"]
st.set_page_config(page_title="Blockchain FX App", layout="centered")
st.title("💱 FX Converter DApp (Localhost)")
st.markdown("Interact with EURx, USDx, and convert using smart contracts.")

# -------------------------
# Config
# -------------------------

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

with open("artifacts/contracts/ERC20Token.sol/ERC20Token.json") as f:
    token_abi = json.load(f)["abi"]

with open("artifacts/contracts/FXConverter.sol/FXConverter.json") as f:
    fx_abi = json.load(f)["abi"]

# Paste your actual deployed contract addresses here
TOKEN_ADDRESSES = {
    "EURx": "0xYourEurxAddressHere",
    "USDx": "0xYourUsdxAddressHere",
}

FX_CONVERTER_ADDRESS = "0xYourFXConverterAddressHere"

# -------------------------
# Account Setup
# -------------------------

accounts = w3.eth.accounts
user_address = st.selectbox("Select wallet", accounts)

# -------------------------
# Contract Setup
# -------------------------

eurx = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESSES["EURx"]), abi=token_abi)
usdx = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESSES["USDx"]), abi=token_abi)
converter = w3.eth.contract(address=Web3.to_checksum_address(FX_CONVERTER_ADDRESS), abi=fx_abi)

# -------------------------
# Balances
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
# Mint Tokens
# -------------------------

st.subheader("🪙 Mint EURx (admin only)")

mint_amount = st.number_input("Amount to mint", min_value=0.0, value=10.0, step=1.0)

if st.button("Mint"):
    tx_hash = eurx.functions.mint(user_address, int(mint_amount * 1e18)).transact({"from": accounts[0]})
    w3.eth.wait_for_transaction_receipt(tx_hash)
    st.success("Minted!")
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
    st.success("Converted!")
    st.rerun()
