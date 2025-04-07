import sqlite3
import os

DB_NAME = "data/treasury.db"

def get_connection():
    os.makedirs("data", exist_ok=True)  # make sure 'data/' exists
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    return conn
