import os

if os.path.exists("data/treasury.db"):
    os.remove("data/treasury.db")

import sqlite3
import os

# Ensure the "data" folder exists
os.makedirs("data", exist_ok=True)

# Define path to the database file
DB_NAME = "data/treasury.db"

def get_connection():
    """Establish a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    return conn

def init_db():
    """Initialize all required tables."""
    conn = get_connection()
    cursor = conn.cursor()

    # --- Clients Table ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        base_currency TEXT,
        industry TEXT,
        payment_terms TEXT,
        budget_rate REAL,
        risk_profile TEXT,
        tags TEXT,
        notes TEXT
    )
    """)

    # --- Payments Table ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT,
        amount REAL,
        currency TEXT,
        direction TEXT,
        payment_date TEXT,
        notes TEXT,
        status TEXT
    )
    """)

    # --- Hedges Table ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hedges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT,
        hedge_type TEXT,
        notional REAL,
        currency TEXT,
        strike REAL,
        maturity TEXT,
        premium REAL
    )
    """)

    conn.commit()
    conn.close()
