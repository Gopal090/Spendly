import re
from pathlib import Path
import pytest
from app import app


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


def test_profile_authenticated_returns_200(client):
    """Visiting /profile while logged in returns HTTP 200."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Nitish Kumar"
        sess["user_email"] = "nitish@example.com"

    response = client.get("/profile")
    assert response.status_code == 200


def test_profile_user_info_card(client):
    """The page displays a user info card with a name and email."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Nitish Kumar"
        sess["user_email"] = "nitish@example.com"

    response = client.get("/profile")
    html = response.get_data(as_text=True)
    assert "Nitish Kumar" in html
    assert "nitish@example.com" in html


def test_profile_summary_stats(client):
    """The page displays at least three summary stat values (total spent, count, top category)."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    response = client.get("/profile")
    html = response.get_data(as_text=True)
    assert "Total Spent" in html
    assert "Total Transactions" in html or "Transactions" in html
    assert "Top Category" in html


def test_profile_transaction_history_table(client):
    """The page displays a transaction history table with at least three hardcoded rows."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    response = client.get("/profile")
    html = response.get_data(as_text=True)
    assert "<table" in html
    row_count = len(re.findall(r"<tr>", html))
    assert row_count >= 4  # 1 header row + at least 3 transaction rows


def test_profile_category_breakdown(client):
    """The page displays a category breakdown section with at least three categories."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    response = client.get("/profile")
    html = response.get_data(as_text=True)
    assert "Category Breakdown" in html
    categories_found = sum(
        1 for cat in ["Food", "Bills", "Health", "Transport", "Entertainment"] if cat in html
    )
    assert categories_found >= 3


def test_navbar_logged_in_state(client):
    """The navbar shows the logged-in state (username + logout link)."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Nitish Kumar"

    response = client.get("/profile")
    html = response.get_data(as_text=True)
    assert "Logout" in html
    assert "Nitish Kumar" in html


def test_no_hex_color_in_profile_html():
    """No hex colour values appear in profile.html — only CSS variables."""
    profile_html = Path("templates/profile.html").read_text(encoding="utf-8")
    hex_colors = re.findall(r"#[0-9a-fA-F]{3,8}\b", profile_html)
    assert len(hex_colors) == 0, f"Found hex colors in profile.html: {hex_colors}"


def test_no_inline_styles_in_profile_html():
    """No inline styles appear in profile.html."""
    profile_html = Path("templates/profile.html").read_text(encoding="utf-8")
    assert "style=" not in profile_html.lower(), "Found inline style attribute in profile.html"
