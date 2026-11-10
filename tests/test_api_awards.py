"""Integration tests I13-I20: the JSON REST API (/api/...) with Bearer tokens."""

from datetime import datetime

import pytest

from app.models.awards import VolunteerLog
from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME, STUDENT_PASSWORD, STUDENT_USERNAME
from tests.test_integration_awards import make_log, make_prize, reload


def _token(anon_client, username, password):
    response = anon_client.post("/api/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def student_headers(anon_client, student_user):
    return {"Authorization": f"Bearer {_token(anon_client, STUDENT_USERNAME, STUDENT_PASSWORD)}"}


@pytest.fixture
def admin_headers(anon_client, admin_user):
    return {"Authorization": f"Bearer {_token(anon_client, ADMIN_USERNAME, ADMIN_PASSWORD)}"}


# --- auth / authorization ---------------------------------------------------


def test_i13_api_login_returns_token_and_rejects_bad_password(anon_client, student_user):
    ok = anon_client.post("/api/login", json={"username": STUDENT_USERNAME, "password": STUDENT_PASSWORD})
    bad = anon_client.post("/api/login", json={"username": STUDENT_USERNAME, "password": "wrong"})

    assert ok.status_code == 200
    assert ok.json()["token_type"] == "bearer"
    assert ok.json()["role"] == "regular_user"
    assert ok.json()["access_token"]
    assert bad.status_code == 401


def test_i14_api_without_token_is_401_json(anon_client):
    response = anon_client.get("/api/logs")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_i15_api_student_cannot_use_admin_endpoints(anon_client, student_headers):
    assert anon_client.get("/api/admin/logs", headers=student_headers).status_code == 403
    assert anon_client.patch(
        "/api/admin/logs/1", json={"status": "approved"}, headers=student_headers
    ).status_code == 403
    assert anon_client.get("/api/admin/dashboard", headers=student_headers).status_code == 403


# --- volunteer logs ---------------------------------------------------------


def test_i16_api_student_creates_and_lists_logs(anon_client, student_headers, student_user):
    created = anon_client.post(
        "/api/logs",
        json={"event_date": "2026-11-01", "hours": 3, "activity": "  Beach cleanup  "},
        headers=student_headers,
    )
    invalid = anon_client.post(
        "/api/logs",
        json={"event_date": "2026-11-01", "hours": 0, "activity": "Beach cleanup"},
        headers=student_headers,
    )
    listed = anon_client.get("/api/logs", headers=student_headers)

    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    assert created.json()["activity"] == "Beach cleanup"
    assert created.json()["student_id"] == student_user.id
    assert invalid.status_code == 400
    assert [log["id"] for log in listed.json()] == [created.json()["id"]]


def test_i17_api_admin_reviews_logs(anon_client, admin_headers, admin_user, student_user, db):
    log_id = make_log(db, student_user, hours=4)
    url = f"/api/admin/logs/{log_id}"

    pending = anon_client.get("/api/admin/logs?status=pending", headers=admin_headers)
    no_reason = anon_client.patch(url, json={"status": "rejected"}, headers=admin_headers)
    bad_status = anon_client.patch(url, json={"status": "maybe"}, headers=admin_headers)
    missing = anon_client.patch("/api/admin/logs/9999", json={"status": "approved"}, headers=admin_headers)
    approved = anon_client.patch(url, json={"status": "approved"}, headers=admin_headers)

    assert [log["id"] for log in pending.json()] == [log_id]
    assert no_reason.status_code == 400
    assert bad_status.status_code == 422
    assert missing.status_code == 404
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["approved_by_id"] == admin_user.id
    assert reload(db, VolunteerLog, log_id).status == "approved"


def test_i18_api_admin_dashboard_counts(anon_client, admin_headers, student_user, db):
    make_log(db, student_user, status="pending")
    make_log(db, student_user, status="approved", approved_at=datetime.utcnow())
    make_log(db, student_user, status="rejected", approved_at=datetime.utcnow())

    response = anon_client.get("/api/admin/dashboard", headers=admin_headers)

    assert response.status_code == 200
    assert response.json() == {"pending_reviews": 1, "approved_today": 1, "rejected_today": 1}


# --- prizes / redemptions ---------------------------------------------------


def test_i19_api_redeem_status_codes(anon_client, student_headers, student_user, db):
    make_log(db, student_user, hours=8, status="approved", approved_at=datetime.utcnow())
    cheap = make_prize(db, points_required=5, name="Coffee card")
    pricey = make_prize(db, points_required=12, name="Festival pass")

    first = anon_client.post(f"/api/prizes/{cheap}/redemptions", headers=student_headers)
    again = anon_client.post(f"/api/prizes/{cheap}/redemptions", headers=student_headers)
    too_expensive = anon_client.post(f"/api/prizes/{pricey}/redemptions", headers=student_headers)
    unknown = anon_client.post("/api/prizes/9999/redemptions", headers=student_headers)

    assert first.status_code == 201
    assert first.json()["prize_id"] == cheap
    assert again.status_code == 409
    assert too_expensive.status_code == 400
    assert unknown.status_code == 404


def test_i20_api_balance_and_redemptions_reflect_spending(anon_client, student_headers, student_user, db):
    make_log(db, student_user, hours=8, status="approved", approved_at=datetime.utcnow())
    prize_id = make_prize(db, points_required=5)

    before = anon_client.get("/api/me/balance", headers=student_headers).json()
    anon_client.post(f"/api/prizes/{prize_id}/redemptions", headers=student_headers)
    after = anon_client.get("/api/me/balance", headers=student_headers).json()
    redemptions = anon_client.get("/api/redemptions", headers=student_headers).json()
    prizes = anon_client.get("/api/prizes", headers=student_headers).json()

    assert before == {"approved_hours": 8, "points_spent": 0, "points": 8}
    assert after == {"approved_hours": 8, "points_spent": 5, "points": 3}
    assert [r["prize_id"] for r in redemptions] == [prize_id]
    assert prizes[0]["stock_available"] == 2
