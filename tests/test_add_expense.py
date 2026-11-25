import pytest
from app import app
from database.db import create_user, get_user_expenses, get_user_stats, CATEGORIES


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_add_expense_unauthenticated_redirects(client):
    """Accessing /expenses/add while not logged in redirects to /login."""
    response = client.get("/expenses/add", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_add_expense_get_form(client):
    """Logged in user can load the add expense form."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    response = client.get("/expenses/add")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Add an expense" in html
    assert 'name="amount"' in html
    assert 'name="category"' in html
    assert 'name="date"' in html
    assert 'name="description"' in html
    for cat in CATEGORIES:
        assert f'<option value="{cat}"' in html


def test_add_expense_invalid_amount(client):
    """Submitting negative or zero amount re-renders form with error."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    response = client.post("/expenses/add", data={
        "amount": "-50.00",
        "category": "Food",
        "date": "2026-11-25",
        "description": "Invalid expense"
    })
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Please enter a valid positive amount" in html


def test_add_expense_valid_submission(client):
    """Submitting valid expense inserts into database and redirects to profile."""
    import time
    email = f"user_add_exp_{int(time.time())}@example.com"
    user_id = create_user("Expense Tester", email, "pass123")

    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = "Expense Tester"
        sess["user_email"] = email

    response = client.post("/expenses/add", data={
        "amount": "850.50",
        "category": "Entertainment",
        "date": "2026-11-25",
        "description": "Concert ticket"
    }, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    # Check database
    expenses = get_user_expenses(user_id)
    assert len(expenses) == 1
    assert expenses[0]["amount"] == 850.50
    assert expenses[0]["category"] == "Entertainment"
    assert expenses[0]["description"] == "Concert ticket"

    # Verify profile page displays newly added expense
    prof_response = client.get("/profile")
    prof_html = prof_response.get_data(as_text=True)
    assert "Concert ticket" in prof_html
    assert "850.50" in prof_html
    assert "Entertainment" in prof_html
