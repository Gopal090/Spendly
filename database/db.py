import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

# Path to the SQLite database file in the project root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATABASE_NAME = os.environ.get("DATABASE_NAME", "spendly.db")
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


def create_user(name, email, password):
    """
    Hashes the password with werkzeug, inserts a new row into the 'users' table,
    and returns the new user's id.
    Raises sqlite3.IntegrityError if the email is already taken (UNIQUE constraint).
    """
    password_hash = generate_password_hash(password)
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (name, email, password_hash),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


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


def get_user_by_id(user_id):
    """
    Fetches a user record by user_id.
    Returns a dict with user fields or None if not found.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        user = cursor.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if user:
            return dict(user)
        return None
    finally:
        conn.close()


def get_user_expenses(user_id, limit=None):
    """
    Fetches all expenses for a user ordered by date DESC, id DESC.
    Optionally limits the number of results.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        query = (
            "SELECT id, user_id, amount, category, date, description, created_at "
            "FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC"
        )
        params = [user_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        rows = cursor.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_user_stats(user_id):
    """
    Computes summary statistics for a user from live database rows:
    - total_spent (float): sum of all expenses
    - transaction_count (int): total number of expenses
    - top_category (str): category with the highest total spend (or 'None' if empty)
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Total spent & transaction count
        total_row = cursor.execute(
            "SELECT COALESCE(SUM(amount), 0.0) AS total_spent, COUNT(*) AS count FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        total_spent = float(total_row["total_spent"]) if total_row else 0.0
        transaction_count = int(total_row["count"]) if total_row else 0

        # Top category by expenditure
        top_cat_row = cursor.execute(
            "SELECT category, SUM(amount) AS cat_total FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY cat_total DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        top_category = top_cat_row["category"] if top_cat_row else "None"

        return {
            "total_spent": total_spent,
            "transaction_count": transaction_count,
            "top_category": top_category,
        }
    finally:
        conn.close()


def get_user_category_breakdown(user_id):
    """
    Computes category breakdown for a user:
    Returns list of dicts: [{'category': str, 'amount': float, 'percentage': int}]
    ordered by total spend DESC.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        total_row = cursor.execute(
            "SELECT COALESCE(SUM(amount), 0.0) AS total FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        total_spent = float(total_row["total"]) if total_row else 0.0

        rows = cursor.execute(
            "SELECT category, SUM(amount) AS amount FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY amount DESC",
            (user_id,),
        ).fetchall()

        breakdown = []
        for row in rows:
            amt = float(row["amount"])
            pct = round((amt / total_spent) * 100) if total_spent > 0 else 0
            breakdown.append({
                "category": row["category"],
                "amount": amt,
                "percentage": pct,
            })
        return breakdown
    finally:
        conn.close()
