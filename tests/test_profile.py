import html as html_lib
import re
from pathlib import Path
import pytest
from app import app
from database.db import (
    create_user,
    get_user_by_id,
    get_user_expenses,
    get_user_stats,
    get_user_category_breakdown,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_profile_unauthenticated_redirects(client):
    """Visiting /profile without being logged in redirects to /login."""
    response = client.get("/profile", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/login" or response.headers["Location"].endswith("/login")


def test_profile_authenticated_demo_user(client):
    """Visiting /profile while logged in as Demo User returns HTTP 200 and live DB user info."""
    demo_user = get_user_by_id(1)
    assert demo_user is not None

    with client.session_transaction() as sess:
        sess["user_id"] = demo_user["id"]
        sess["user_name"] = demo_user["name"]
        sess["user_email"] = demo_user["email"]

    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert demo_user["name"] in html
    assert demo_user["email"] in html


def test_profile_summary_stats_live_query(client):
    """The page displays live summary stats from database queries."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    stats = get_user_stats(1)
    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert "Total Spent" in html
    assert "Total Transactions" in html
    assert "Top Category" in html
    # Check that live numbers from DB are rendered
    assert f"{stats['total_spent']:.2f}" in html
    assert str(stats["transaction_count"]) in html
    assert stats["top_category"] in html


def test_profile_transaction_history_table_live_query(client):
    """The page displays the user's real transactions from database."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    expenses = get_user_expenses(1)
    assert len(expenses) >= 8

    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert "<table" in html
    # At least 1 header row + at least 8 data rows
    row_count = len(re.findall(r"<tr>", html))
    assert row_count >= 9

    # Check some expense descriptions are rendered
    unescaped_html = html_lib.unescape(html)
    for exp in expenses[:3]:
        assert exp["description"] in unescaped_html


def test_profile_category_breakdown_live_query(client):
    """The page displays category breakdown computed from live database rows."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    breakdown = get_user_category_breakdown(1)
    assert len(breakdown) >= 3

    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert "Category Breakdown" in html
    for item in breakdown[:3]:
        assert item["category"] in html
        assert f"{item['amount']:.2f}" in html


def test_profile_new_user_empty_state(client):
    """A new user with zero expenses sees clean 0 stats and empty states without errors."""
    import time
    email = f"empty_user_{int(time.time())}@example.com"
    new_user_id = create_user("Empty State User", email, "password123")

    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id
        sess["user_name"] = "Empty State User"
        sess["user_email"] = email

    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Empty State User" in html
    assert "₹0.00" in html
    assert "None" in html or "Top Category" in html
    assert "No transactions logged yet" in html
    assert "No category spending recorded yet" in html


def test_navbar_logged_in_state(client):
    """The navbar shows the logged-in state (username + logout link)."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Demo User"

    response = client.get("/profile")
    html = response.get_data(as_text=True)
    assert "Logout" in html
    assert "Demo User" in html


def test_no_hex_color_in_profile_html():
    """No hex colour values appear in profile.html — only CSS variables."""
    profile_html = Path("templates/profile.html").read_text(encoding="utf-8")
    hex_colors = re.findall(r"#[0-9a-fA-F]{3,8}\b", profile_html)
    assert len(hex_colors) == 0, f"Found hex colors in profile.html: {hex_colors}"


def test_no_inline_styles_in_profile_html():
    """No inline styles appear in profile.html."""
    profile_html = Path("templates/profile.html").read_text(encoding="utf-8")
    assert "style=" not in profile_html.lower(), "Found inline style attribute in profile.html"
