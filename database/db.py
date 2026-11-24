import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

# Path to the SQLite database file in the project root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATABASE_NAME = os.environ.get("DATABASE_NAME", "expense_tracker.db")
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, DATABASE_NAME))

CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


def get_db():
    """
    Opens a connection to the SQLite database in the project root.
    Configures row_factory to sqlite3.Row for dictionary-like access
    and enables foreign key constraint enforcement.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """
    Creates 'users' and 'expenses' tables using CREATE TABLE IF NOT EXISTS.
    Safe to call multiple times.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    """)

    conn.commit()
    conn.close()


def seed_db():
    """
    Seeds the database with initial demo data.
    If the users table already contains data, returns early to prevent duplicates.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM users")
    row = cursor.fetchone()
    if row and row["count"] > 0:
        conn.close()
        return

    # 1. Insert Demo User
    demo_password_hash = generate_password_hash("demo123")
    cursor.execute(
        """
        INSERT INTO users (name, email, password_hash)
        VALUES (?, ?, ?)
        """,
        ("Demo User", "demo@spendly.com", demo_password_hash),
    )
    user_id = cursor.lastrowid

    # 2. Insert 8 Sample Expenses covering all categories across current month
    current_year_month = datetime.now().strftime("%Y-%m")
    sample_expenses = [
        (user_id, 450.00, "Food", f"{current_year_month}-02", "Grocery shopping at supermarket"),
        (user_id, 120.00, "Transport", f"{current_year_month}-05", "Metro card recharge"),
        (user_id, 1450.00, "Bills", f"{current_year_month}-08", "Electricity & Wi-Fi bills"),
        (user_id, 320.00, "Health", f"{current_year_month}-12", "Pharmacy medicines"),
        (user_id, 650.00, "Entertainment", f"{current_year_month}-15", "Weekend movie tickets"),
        (user_id, 1800.00, "Shopping", f"{current_year_month}-19", "Running shoes"),
        (user_id, 250.00, "Other", f"{current_year_month}-22", "Notebooks & stationery"),
        (user_id, 380.00, "Food", f"{current_year_month}-25", "Dinner with friends"),
    ]

    cursor.executemany(
        """
        INSERT INTO expenses (user_id, amount, category, date, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        sample_expenses,
    )

    conn.commit()
    conn.close()
