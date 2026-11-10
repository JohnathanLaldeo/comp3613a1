"""Integration tests I1-I10: real routes via TestClient on a SQLite test database."""

import re
from datetime import date, datetime, time, timedelta

from fastapi.testclient import TestClient
from sqlmodel import select

from app.models.awards import Prize, Redemption, VolunteerLog
from app.repositories.awards import AwardRepository


# --- helpers ----------------------------------------------------------------


def make_log(db, student, *, hours=3, status="pending", approved_at=None, activity="Beach cleanup"):
    log = VolunteerLog(
        student_id=student.id,
        event_date=date(2026, 11, 1),
        hours=hours,
        activity=activity,
        status=status,
        approved_at=approved_at,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log.id


def make_prize(db, *, points_required=5, stock_available=3, name="Movie voucher"):
    prize = Prize(
        name=name,
        description="Two tickets",
        points_required=points_required,
        stock_available=stock_available,
    )
    db.add(prize)
    db.commit()
    db.refresh(prize)
    return prize.id


def reload(db, model, pk):
    """Re-read a row after the app changed it in its own session."""
    db.expire_all()
    return db.get(model, pk)


def redemptions_for(db, student_id):
    db.expire_all()
    return db.exec(select(Redemption).where(Redemption.student_id == student_id)).all()


def flash_messages(html: str) -> list[str]:
    return re.findall(r'<div class="alert[^"]*" role="alert">(.*?)</div>', html, re.S)


def stat_value(html: str, label: str) -> int:
    match = re.search(
        rf'{re.escape(label)}</span>\s*<strong class="stat-value">(\d+)</strong>', html
    )
    assert match, f"{label!r} stat not found on the page"
    return int(match.group(1))


# --- volunteer hours --------------------------------------------------------


def test_i1_student_logs_hours_saved_as_pending(student_client, student_user, db):
    response = student_client.post(
        "/app/hours/new",
        data={"event_date": "2026-11-01", "hours": "3", "activity": "Beach cleanup", "notes": ""},
        follow_redirects=False,
    )

    assert response.status_code == 303
    logs = db.exec(select(VolunteerLog).where(VolunteerLog.student_id == student_user.id)).all()
    assert len(logs) == 1
    assert logs[0].status == "pending"
    assert logs[0].hours == 3
    assert logs[0].activity == "Beach cleanup"


def test_i2_admin_approves_and_student_total_increases(admin_client, admin_user, student_user, db):
    log_id = make_log(db, student_user, hours=4)
    repo = AwardRepository(db)
    assert repo.get_approved_hours(student_user.id) == 0

    response = admin_client.post(
        f"/admin/review/{log_id}/approve", data={"admin_notes": ""}, follow_redirects=False
    )

    assert response.status_code == 303
    log = reload(db, VolunteerLog, log_id)
    assert log.status == "approved"
    assert log.approved_by_id == admin_user.id
    assert log.approved_at is not None
    assert repo.get_approved_hours(student_user.id) == 4


def test_i3_admin_reject_without_reason_is_blocked(admin_client, student_user, db):
    log_id = make_log(db, student_user)

    response = admin_client.post(
        f"/admin/review/{log_id}/reject", data={"admin_notes": "  "}, follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith(f"/admin/review/{log_id}")
    assert reload(db, VolunteerLog, log_id).status == "pending"

    detail = admin_client.get(response.headers["location"])
    assert "Please provide a rejection reason" in detail.text


def test_i4_admin_reject_with_reason_saves_reason(admin_client, admin_user, student_user, db):
    log_id = make_log(db, student_user)

    response = admin_client.post(
        f"/admin/review/{log_id}/reject",
        data={"admin_notes": "Event date is outside the term"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    log = reload(db, VolunteerLog, log_id)
    assert log.status == "rejected"
    assert log.admin_notes == "Event date is outside the term"
    assert log.approved_by_id == admin_user.id


# --- prizes -----------------------------------------------------------------


def test_i5_student_redeems_affordable_prize(student_client, student_user, db):
    make_log(db, student_user, hours=10, status="approved", approved_at=datetime.utcnow())
    prize_id = make_prize(db, points_required=5, stock_available=3)

    response = student_client.post(f"/app/prizes/{prize_id}/redeem", follow_redirects=False)

    assert response.status_code == 303
    redemptions = redemptions_for(db, student_user.id)
    assert len(redemptions) == 1
    assert redemptions[0].prize_id == prize_id
    assert reload(db, Prize, prize_id).stock_available == 2


def test_i6_student_redeems_same_prize_again_is_refused(student_client, student_user, db):
    make_log(db, student_user, hours=10, status="approved", approved_at=datetime.utcnow())
    prize_id = make_prize(db, points_required=5, stock_available=3)
    student_client.post(f"/app/prizes/{prize_id}/redeem", follow_redirects=False)

    response = student_client.post(f"/app/prizes/{prize_id}/redeem")  # follows to /app/prizes

    assert response.status_code == 200
    assert "Prize already redeemed" in flash_messages(response.text)
    assert len(redemptions_for(db, student_user.id)) == 1
    assert reload(db, Prize, prize_id).stock_available == 2


def test_i7_student_redeems_too_expensive_prize_is_refused(student_client, student_user, db):
    make_log(db, student_user, hours=2, status="approved", approved_at=datetime.utcnow())
    prize_id = make_prize(db, points_required=5, stock_available=3)

    response = student_client.post(f"/app/prizes/{prize_id}/redeem")  # follows to /app/prizes

    assert response.status_code == 200
    assert "You need more approved hours to redeem this prize" in flash_messages(response.text)
    assert redemptions_for(db, student_user.id) == []
    assert reload(db, Prize, prize_id).stock_available == 3


# --- access control ---------------------------------------------------------


def test_i8_student_cannot_open_admin(student_client):
    response = student_client.get("/admin")

    assert response.status_code == 401
    assert "Admin Dashboard" not in response.text


def test_i9_anonymous_cannot_open_app(anon_client: TestClient):
    response = anon_client.get("/app")

    assert response.status_code == 401
    assert "Unauthorized" in response.text


# --- admin dashboard --------------------------------------------------------


def test_i10_admin_dashboard_counts(admin_client, admin_user, student_user, db):
    now = datetime.utcnow()
    yesterday = datetime.combine(now.date(), time.min) - timedelta(hours=1)

    make_log(db, student_user, status="pending")
    make_log(db, student_user, status="pending")
    make_log(db, student_user, status="approved", approved_at=now)
    make_log(db, student_user, status="approved", approved_at=yesterday)  # not today
    make_log(db, student_user, status="rejected", approved_at=now)
    make_log(db, student_user, status="rejected", approved_at=now)
    make_log(db, student_user, status="rejected", approved_at=yesterday)  # not today

    response = admin_client.get("/admin")

    assert response.status_code == 200
    assert stat_value(response.text, "Pending Reviews") == 2
    assert stat_value(response.text, "Approved Today") == 1
    assert stat_value(response.text, "Rejected Today") == 2


# --- extra (beyond the I1-I10 plan) -----------------------------------------


def test_i11_redeeming_spends_points(student_client, student_user, db):
    make_log(db, student_user, hours=8, status="approved", approved_at=datetime.utcnow())
    first = make_prize(db, points_required=5, name="Movie voucher")
    second = make_prize(db, points_required=5, name="Cafe voucher")

    student_client.post(f"/app/prizes/{first}/redeem")
    response = student_client.post(f"/app/prizes/{second}/redeem")  # only 3 points left

    assert "You need more approved hours to redeem this prize" in flash_messages(response.text)
    assert [r.prize_id for r in redemptions_for(db, student_user.id)] == [first]
    assert "3 points available" in response.text


def test_i21_my_hours_filter_reason_and_resubmit(student_client, student_user, db):
    make_log(db, student_user, activity="Food drive", status="pending")
    rejected_id = make_log(db, student_user, activity="Tutoring", hours=2, status="rejected")
    log = db.get(VolunteerLog, rejected_id)
    log.admin_notes = "Hours do not match the sign-in sheet"
    db.add(log)
    db.commit()

    rejected_only = student_client.get("/app/hours?status=rejected").text
    resubmit_form = student_client.get(f"/app/hours/new?resubmit={rejected_id}").text

    assert "Tutoring" in rejected_only and "Food drive" not in rejected_only
    assert "Hours do not match the sign-in sheet" in rejected_only
    assert f"resubmit={rejected_id}" in rejected_only
    assert 'value="Tutoring"' in resubmit_form
    assert 'value="2"' in resubmit_form


def test_i12_admin_approve_missing_log_is_handled(admin_client):
    response = admin_client.post("/admin/review/9999/approve", data={"admin_notes": ""})

    assert response.status_code == 200  # redirected back to the queue, not a 500
    assert "Volunteer log not found" in flash_messages(response.text)
