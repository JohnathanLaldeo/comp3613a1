"""Unit tests U1-U10: AwardService rules with a fake repository (no database)."""

from datetime import date
from types import SimpleNamespace

import pytest

from app.services.awards_service import AwardService


class FakeAwardRepository:
    """Stands in for AwardRepository; records what the service asked it to do."""

    def __init__(self, *, approved_hours: int = 0, points_spent: int = 0, prizes=None):
        self.approved_hours = approved_hours
        self.points_spent = points_spent
        self.prizes = {prize.id: prize for prize in (prizes or [])}
        self.created_logs: list[dict] = []
        self.status_updates: list[dict] = []
        self.redemptions: list[SimpleNamespace] = []

    def create_volunteer_log(self, **fields):
        self.created_logs.append(fields)
        return SimpleNamespace(id=len(self.created_logs), status="pending", **fields)

    def update_log_status(self, **fields):
        self.status_updates.append(fields)
        return SimpleNamespace(id=fields["log_id"], **fields)

    def get_prize_by_id(self, prize_id: int):
        return self.prizes.get(prize_id)

    def get_approved_hours(self, student_id: int) -> int:
        return self.approved_hours

    def get_points_spent(self, student_id: int) -> int:
        return self.points_spent

    def get_student_redemptions(self, student_id: int):
        return [r for r in self.redemptions if r.student_id == student_id]

    def redeem_prize(self, *, student_id: int, prize_id: int):
        redemption = SimpleNamespace(
            id=len(self.redemptions) + 1,
            student_id=student_id,
            prize_id=prize_id,
            status="redeemed",
        )
        self.redemptions.append(redemption)
        return redemption


def make_prize(prize_id: int = 1, points_required: int = 5):
    return SimpleNamespace(id=prize_id, name="Movie voucher", points_required=points_required)


def log_kwargs(**overrides):
    values = {
        "student_id": 1,
        "event_date": date(2026, 11, 1),
        "hours": 3,
        "activity": "Beach cleanup",
        "notes": None,
    }
    values.update(overrides)
    return values


# --- create_log -------------------------------------------------------------


def test_u1_create_log_blank_activity_raises():
    repo = FakeAwardRepository()
    service = AwardService(repo)

    with pytest.raises(ValueError):
        service.create_log(**log_kwargs(activity="   "))

    assert repo.created_logs == []


def test_u2_create_log_zero_hours_raises():
    repo = FakeAwardRepository()
    service = AwardService(repo)

    with pytest.raises(ValueError):
        service.create_log(**log_kwargs(hours=0))

    assert repo.created_logs == []


def test_u3_create_log_trims_activity_and_blank_notes_become_none():
    repo = FakeAwardRepository()
    service = AwardService(repo)

    service.create_log(**log_kwargs(activity="  Beach cleanup  ", notes="   "))

    assert len(repo.created_logs) == 1
    saved = repo.created_logs[0]
    assert saved["activity"] == "Beach cleanup"
    assert saved["notes"] is None


# --- decide_log -------------------------------------------------------------


def test_u4_decide_log_unsupported_action_raises():
    repo = FakeAwardRepository()
    service = AwardService(repo)

    with pytest.raises(ValueError):
        service.decide_log(log_id=1, admin_id=2, action="maybe")

    assert repo.status_updates == []


def test_u5_decide_log_reject_without_notes_raises():
    repo = FakeAwardRepository()
    service = AwardService(repo)

    with pytest.raises(ValueError):
        service.decide_log(log_id=1, admin_id=2, action="rejected", admin_notes=None)

    assert repo.status_updates == []


def test_u6_decide_log_reject_with_whitespace_notes_raises():
    repo = FakeAwardRepository()
    service = AwardService(repo)

    with pytest.raises(ValueError):
        service.decide_log(log_id=1, admin_id=2, action="rejected", admin_notes="   ")

    assert repo.status_updates == []


def test_u7_decide_log_approve_without_notes_saves_none():
    repo = FakeAwardRepository()
    service = AwardService(repo)

    service.decide_log(log_id=1, admin_id=2, action="approved")

    assert repo.status_updates == [
        {"log_id": 1, "status": "approved", "admin_id": 2, "admin_notes": None}
    ]


# --- redeem_prize -----------------------------------------------------------


def test_u8_redeem_unknown_prize_raises():
    repo = FakeAwardRepository(approved_hours=100)
    service = AwardService(repo)

    with pytest.raises(ValueError):
        service.redeem_prize(student_id=1, prize_id=999)

    assert repo.redemptions == []


def test_u9_redeem_with_hours_below_cost_raises():
    repo = FakeAwardRepository(approved_hours=4, prizes=[make_prize(points_required=5)])
    service = AwardService(repo)

    with pytest.raises(ValueError):
        service.redeem_prize(student_id=1, prize_id=1)

    assert repo.redemptions == []


def test_u10_redeem_with_hours_equal_to_cost_creates_redemption():
    repo = FakeAwardRepository(approved_hours=5, prizes=[make_prize(points_required=5)])
    service = AwardService(repo)

    redemption = service.redeem_prize(student_id=1, prize_id=1)

    assert len(repo.redemptions) == 1
    assert redemption.student_id == 1
    assert redemption.prize_id == 1
    assert redemption.status == "redeemed"


# --- extra (beyond the U1-U10 plan): points are spent on redemption ---------


def test_u11_redeem_uses_balance_after_points_already_spent():
    repo = FakeAwardRepository(
        approved_hours=8, points_spent=5, prizes=[make_prize(points_required=5)]
    )
    service = AwardService(repo)

    with pytest.raises(ValueError):
        service.redeem_prize(student_id=1, prize_id=1)  # balance is 3, cost is 5

    assert repo.redemptions == []
