import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from werkzeug.security import check_password_hash
from database.db import (
    get_db,
    init_db,
    seed_db,
    create_user,
    get_user_by_id,
    get_user_expenses,
    get_user_stats,
    get_user_category_breakdown,
)

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
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    # Live query: fetch authenticated user from database
    user_db = get_user_by_id(user_id)
    if not user_db:
        session.clear()
        return redirect(url_for("login"))

    user_name = user_db["name"]
    user_email = user_db["email"]
    name_parts = user_name.split()
    initials = "".join([part[0].upper() for part in name_parts[:2]]) if name_parts else "U"

    created_at_raw = user_db.get("created_at") or ""
    try:
        dt = datetime.strptime(created_at_raw[:10], "%Y-%m-%d")
        member_since = dt.strftime("%B %Y")
    except Exception:
        member_since = "March 2026"

    user_info = {
        "name": user_name,
        "email": user_email,
        "initials": initials,
        "member_since": member_since,
    }

    # Live queries for stats, expenses, and category breakdown
    stats = get_user_stats(user_id)
    transactions = get_user_expenses(user_id)
    categories = get_user_category_breakdown(user_id)

    return render_template(
        "profile.html",
        user=user_info,
        stats=stats,
        transactions=transactions,
        categories=categories,
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
