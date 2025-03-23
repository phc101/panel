import streamlit as st
from web3 import Web3
import json
import os

st.set_page_config(page_title="FX Converter", layout="wide")
st.title("💱 Local FX Converter DApp")
st.markdown("Mint and convert between 5 currencies using smart contracts.")

erc20_path = os.path.abspath("artifacts/contracts/ERC20Token.sol/ERC20Token.json")
fx_path = os.path.abspath("artifacts/contracts/FXConverter.sol/FXConverter.json")


try:
    with open(erc20_path) as f:
        token_abi = json.load(f)["abi"]
    with open(fx_path) as f:
        fx_abi = json.load(f)["abi"]
except FileNotFoundError:
    st.error("❌ ABI files not found. Please run `npx hardhat compile`.")
    st.stop()

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

if not w3.is_connected():
    st.error("❌ Could not connect to Hardhat local node. Run `npx hardhat node`.")
    st.stop()

accounts = w3.eth.accounts
user_address = st.selectbox("👛 Select wallet", accounts)

TOKEN_ADDRESSES = {
    "EURx": "0x959922bE3CAee4b8Cd9a407cc3ac1C251C2007B1",
    "USDx": "0x9A9f2CCfdE556A7E9Ff0848998Aa4a0CFD8863AE",
    "PLNx": "0x68B1D87F95878fE05B998F19b66F4baba5De1aed",
    "GBPx": "0x3Aa5ebB10DC797CAC828524e59A333d0A371443c",
    "CHFx": "0xc6e7DF5E7b4f2A278906862b61205850344D4e7d"
}

FX_CONVERTER_ADDRESS = "0x59b670e9fA9D0A427751Af201D676719a970857b"

# Instantiate token contracts
contracts = {
    sym: w3.eth.contract(address=Web3.to_checksum_address(addr), abi=token_abi)
    for sym, addr in TOKEN_ADDRESSES.items()
}
converter = w3.eth.contract(address=Web3.to_checksum_address(FX_CONVERTER_ADDRESS), abi=fx_abi)

# Show balances
st.subheader("💰 Token Balances")
cols = st.columns(len(TOKEN_ADDRESSES))
for i, (symbol, contract) in enumerate(contracts.items()):
    balance = contract.functions.balanceOf(user_address).call() / 1e18
    cols[i].metric(label=symbol, value=f"{balance:.4f}")

# Mint section
st.subheader("🪙 Mint Tokens")
mint_token = st.selectbox("Select token to mint", list(TOKEN_ADDRESSES.keys()))
mint_amount = st.number_input("Amount", min_value=0.0, value=10.0, step=1.0)
if st.button("Mint"):
    tx = contracts[mint_token].functions.mint(user_address, int(mint_amount * 1e18)).transact({"from": accounts[0]})
    w3.eth.wait_for_transaction_receipt(tx)
    st.success(f"✅ Minted {mint_amount:.2f} {mint_token} to {user_address}")
    st.rerun()

# Convert section
st.subheader("🔄 Convert Tokens")
col1, col2 = st.columns(2)
from_token = col1.selectbox("From", list(TOKEN_ADDRESSES.keys()), key="from")
to_token = col2.selectbox("To", list(TOKEN_ADDRESSES.keys()), key="to")
convert_amount = st.number_input("Amount to convert", min_value=0.0, value=5.0, step=1.0)

if st.button("Convert"):
    amt = int(convert_amount * 1e18)
    contracts[from_token].functions.approve(FX_CONVERTER_ADDRESS, amt).transact({"from": user_address})
    tx = converter.functions.convert(
        contracts[from_token].address,
        contracts[to_token].address,
        amt
    ).transact({"from": user_address})
    w3.eth.wait_for_transaction_receipt(tx)
    st.success(f"✅ Converted {convert_amount:.2f} {from_token} to {to_token}")
    st.rerun()
