import os
import json
import streamlit as st
from web3 import Web3

# ✅ Connect to local Hardhat node
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

# ✅ Your deployed token + converter addresses
TOKEN_ADDRESSES = {
    "EURx": "0x959922bE3CAee4b8Cd9a407cc3ac1C251C2007B1",
    "USDx": "0x9A9f2CCfdE556A7E9Ff0848998Aa4a0CFD8863AE",
    "PLNx": "0x68B1D87F95878fE05B998F19b66F4baba5De1aed",
    "GBPx": "0x3Aa5ebB10DC797CAC828524e59A333d0A371443c",
    "CHFx": "0xc6e7DF5E7b4f2A278906862b61205850344D4e7d"
}
FX_CONVERTER_ADDRESS = "0x59b670e9fA9D0A427751Af201D676719a970857b"

# ✅ Load ABIs
erc20_path = os.path.abspath("artifacts/contracts/ERC20Token.sol/ERC20Token.json")
fx_path = os.path.abspath("artifacts/contracts/FXConverter.sol/FXConverter.json")

with open(erc20_path) as f:
    token_abi = json.load(f)["abi"]

with open(fx_path) as f:
    fx_abi = json.load(f)["abi"]

# ✅ UI
st.set_page_config(page_title="💱 Local FX Converter DApp")
st.title("💱 Local FX Converter DApp")
st.markdown("Mint and convert EURx ↔ USDx using smart contracts.")

st.markdown(f"📂 Working directory: `{os.getcwd()}`")
st.markdown(f"🔍 ERC20 ABI path: `{erc20_path}`")
st.markdown(f"🔍 FXConverter ABI path: `{fx_path}`")

# ✅ Select user wallet
accounts = w3.eth.accounts
user_address = st.selectbox("Select wallet", accounts)

# ✅ Load contracts
eurx = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESSES["EURx"]), abi=token_abi)
usdx = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESSES["USDx"]), abi=token_abi)
converter = w3.eth.contract(address=Web3.to_checksum_address(FX_CONVERTER_ADDRESS), abi=fx_abi)

# ✅ Get balances
def get_balances():
    b_eur = eurx.functions.balanceOf(user_address).call()
    b_usd = usdx.functions.balanceOf(user_address).call()
    return w3.from_wei(b_eur, 'ether'), w3.from_wei(b_usd, 'ether')

eur_balance, usd_balance = get_balances()
st.write(f"💶 EURx balance: `{eur_balance}`")
st.write(f"💵 USDx balance: `{usd_balance}`")

# ✅ Mint tokens
with st.form("mint"):
    st.subheader("🪙 Mint Tokens")
    token = st.selectbox("Token to mint", ["EURx", "USDx"])
    amount = st.number_input("Amount", min_value=0.0, value=10.0)
    if st.form_submit_button("Mint"):
        contract = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESSES[token]), abi=token_abi)
        tx = contract.functions.mint(user_address, w3.to_wei(amount, 'ether')).transact({"from": user_address})
        w3.eth.wait_for_transaction_receipt(tx)
        st.success(f"Minted {amount} {token}")

# ✅ Convert tokens
with st.form("convert"):
    st.subheader("🔁 Convert EURx ↔ USDx")
    direction = st.radio("Direction", ["EURx → USDx", "USDx → EURx"])
    amount = st.number_input("Convert amount", min_value=0.0, value=1.0)
    if st.form_submit_button("Convert"):
        from_token = "EURx" if "EURx" in direction else "USDx"
        to_token = "USDx" if from_token == "EURx" else "EURx"
        from_contract = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESSES[from_token]), abi=token_abi)

        amount_wei = w3.to_wei(amount, 'ether')
        # Approve converter
        from_contract.functions.approve(FX_CONVERTER_ADDRESS, amount_wei).transact({"from": user_address})
        # Convert
        tx = converter.functions.convert(
            Web3.to_checksum_address(TOKEN_ADDRESSES[from_token]),
            Web3.to_checksum_address(TOKEN_ADDRESSES[to_token]),
            amount_wei
        ).transact({"from": user_address})
        w3.eth.wait_for_transaction_receipt(tx)
        st.success(f"Converted {amount} {from_token} to {to_token}")

# 🔄 Refresh
if st.button("🔄 Refresh Balances"):
    st.experimental_rerun()
