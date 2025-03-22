import streamlit as st
import hashlib
import time
import json

st.set_page_config(page_title="Blockchain with Wallets", layout="wide")

# --- BLOCK CLASS WITH TRANSACTIONS ---
class Block:
    def __init__(self, index, previous_hash, timestamp, transactions, nonce=0):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.transactions = transactions  # now a list of transactions
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.index}{self.previous_hash}{self.timestamp}{json.dumps(self.transactions)}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty):
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()

# --- BLOCKCHAIN CLASS WITH TRANSACTION VALIDATION ---
class Blockchain:
    def __init__(self, difficulty=3):
        self.difficulty = difficulty
        self.chain = [self.create_genesis_block()]
        self.pending_transactions = []
        self.mining_reward = 50  # reward for mining a block

    def create_genesis_block(self):
        genesis_block = Block(0, "0", time.time(), ["Genesis Block"])
        genesis_block.mine_block(self.difficulty)
        return genesis_block

    def get_latest_block(self):
        return self.chain[-1]

    def add_transaction(self, sender, recipient, amount):
        if sender != "SYSTEM" and self.get_balance(sender) < amount:
            return False
        transaction = {"sender": sender, "recipient": recipient, "amount": amount}
        self.pending_transactions.append(transaction)
        return True

    def mine_pending_transactions(self, miner_address):
        if not self.pending_transactions:
            return None
        self.add_transaction("SYSTEM", miner_address, self.mining_reward)  # reward
        new_block = Block(
            len(self.chain),
            self.get_latest_block().hash,
            time.time(),
            self.pending_transactions
        )
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        self.pending_transactions = []  # clear mempool
        return new_block

    def get_balance(self, address):
        balance = 0
        for block in self.chain:
            if isinstance(block.transactions, list):
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
