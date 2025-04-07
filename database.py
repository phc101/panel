import os

os.makedirs("data", exist_ok=True)  # ensures the folder exists

import sqlite3


DB_NAME = "data/treasury.db"

def get_connection():
    os.makedirs("data", exist_ok=True)  # make sure 'data/' exists
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    return conn
