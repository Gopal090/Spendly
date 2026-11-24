import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, create_user

app = Flask(__name__)
app.secret_key = "spendly-dev-secret-key"

# Initialize and seed database on startup
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # 1. Server-side validation: All fields are non-empty
        if not name or not email or not password or not confirm_password:
            flash("All fields are required", "error")
            return render_template("register.html", name=name, email=email)

        # 2. Server-side validation: password == confirm_password
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("register.html", name=name, email=email)

        # 3. Create user, catching unique email violation
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            flash("Email already registered", "error")
            return render_template("register.html", name=name, email=email)

        # On success, flash message and redirect to login
        flash("Account created successfully! Please sign in.", "success")
        return redirect(url_for("login"))

    abort(405)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("All fields are required", "error")
            return render_template("login.html", email=email)

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]
            flash("Welcome back!", "success")
            return redirect(url_for("profile"))

        flash("Invalid email or password", "error")
        return render_template("login.html", email=email)

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    # Authentication guard: check session.get("user_id")
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Hardcoded profile data as per spec
    user_name = session.get("user_name", "Nitish Kumar")
    user_email = session.get("user_email", "nitish@example.com")
    name_parts = user_name.split()
    initials = "".join([part[0].upper() for part in name_parts[:2]]) if name_parts else "NK"

    user_info = {
        "name": user_name,
        "email": user_email,
        "initials": initials,
        "member_since": "March 2026",
    }

    stats = {
        "total_spent": 12450.00,
        "transaction_count": 28,
        "top_category": "Food",
    }

    transactions = [
        {
            "date": "2026-03-24",
            "description": "Weekly grocery run at Whole Foods",
            "category": "Food",
            "amount": 2450.00,
        },
        {
            "date": "2026-03-22",
            "description": "Monthly fiber broadband internet",
            "category": "Bills",
            "amount": 1200.00,
        },
        {
            "date": "2026-03-20",
            "description": "Metro & public transit card recharge",
            "category": "Transport",
            "amount": 800.00,
        },
        {
            "date": "2026-03-18",
            "description": "Annual health checkup and medicine",
            "category": "Health",
            "amount": 3100.00,
        },
        {
            "date": "2026-03-15",
            "description": "Weekend movie tickets and popcorn",
            "category": "Entertainment",
            "amount": 950.00,
        },
    ]

    category_breakdown = [
        {"category": "Food", "amount": 4200.00, "percentage": 34},
        {"category": "Bills", "amount": 3200.00, "percentage": 26},
        {"category": "Health", "amount": 3100.00, "percentage": 25},
        {"category": "Transport", "amount": 1000.00, "percentage": 8},
        {"category": "Entertainment", "amount": 950.00, "percentage": 7},
    ]

    return render_template(
        "profile.html",
        user=user_info,
        stats=stats,
        transactions=transactions,
        categories=category_breakdown,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
