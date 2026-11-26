import re
from pathlib import Path
import pytest
from app import app
from database.db import create_user, add_user_expense, get_user_expenses, get_user_stats


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_delete_expense_unauthenticated_redirects(client):
    """Deleting without being logged in redirects to /login."""
    response = client.post("/expenses/1/delete", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_delete_own_expense_success(client):
    """An authenticated user can successfully delete their own expense."""
    import time
    email = f"user_del_{int(time.time())}@example.com"
    user_id = create_user("Delete Tester", email, "pass123")

    # Add two expenses
    exp1_id = add_user_expense(user_id, 200.0, "Food", "2026-11-26", "Lunch")
    exp2_id = add_user_expense(user_id, 500.0, "Bills", "2026-11-26", "Phone bill")

    assert len(get_user_expenses(user_id)) == 2
    assert get_user_stats(user_id)["total_spent"] == 700.0

    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = "Delete Tester"
        sess["user_email"] = email

    # Delete exp1
    response = client.post(f"/expenses/{exp1_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Check flash message and updated expenses
    assert "Expense deleted successfully" in html
    remaining = get_user_expenses(user_id)
    assert len(remaining) == 1
    assert remaining[0]["id"] == exp2_id
    assert get_user_stats(user_id)["total_spent"] == 500.0


def test_cannot_delete_other_user_expense(client):
    """A user cannot delete another user's expense."""
    import time
    email_a = f"user_a_{int(time.time())}@example.com"
    email_b = f"user_b_{int(time.time())}@example.com"
    user_a = create_user("User A", email_a, "pass123")
    user_b = create_user("User B", email_b, "pass123")

    # User A creates an expense
    exp_a_id = add_user_expense(user_a, 300.0, "Health", "2026-11-26", "Medicine")

    # User B logs in and attempts to delete User A's expense
    with client.session_transaction() as sess:
        sess["user_id"] = user_b
        sess["user_name"] = "User B"
        sess["user_email"] = email_b

    response = client.post(f"/expenses/{exp_a_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Expense not found or unauthorized" in html
    # Verify User A's expense is still intact
    expenses_a = get_user_expenses(user_a)
    assert len(expenses_a) == 1
    assert expenses_a[0]["id"] == exp_a_id


def test_delete_nonexistent_expense(client):
    """Attempting to delete a nonexistent expense id handles gracefully."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    response = client.post("/expenses/999999/delete", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Expense not found or unauthorized" in html


def test_no_inline_styles_and_hex_in_profile_html():
    """Verify profile.html continues to have zero inline styles and zero hex colors."""
    profile_html = Path("templates/profile.html").read_text(encoding="utf-8")
    assert "style=" not in profile_html.lower()
    hex_colors = re.findall(r"#[0-9a-fA-F]{3,8}\b", profile_html)
    assert len(hex_colors) == 0
