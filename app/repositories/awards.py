from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Session, func, select

from app.models.awards import Prize, Redemption, VolunteerLog
from app.models.user import User


class AwardRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_volunteer_log(
        self,
        *,
        student_id: int,
        event_date,
        hours: int,
        activity: str,
        notes: str | None = None,
    ) -> VolunteerLog:
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)
        log = VolunteerLog(
            student_id=student_id,
            event_date=event_date,
            hours=hours,
            activity=activity,
            notes=notes,
            status="pending",
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_user_logs(self, student_id: int) -> list[VolunteerLog]:
        return self.db.exec(
            select(VolunteerLog)
            .where(VolunteerLog.student_id == student_id)
            .order_by(VolunteerLog.submitted_at.desc())
        ).all()

    def get_pending_logs(self) -> list[VolunteerLog]:
        return self.db.exec(
            select(VolunteerLog)
            .where(VolunteerLog.status == "pending")
            .order_by(VolunteerLog.submitted_at.asc())
        ).all()

    def get_pending_summaries(self, limit: int | None = None) -> list[dict]:
        statement = (
            select(VolunteerLog, User.username)
            .join(User, VolunteerLog.student_id == User.id)
            .where(VolunteerLog.status == "pending")
            .order_by(VolunteerLog.submitted_at.desc())
        )
        if limit is not None:
            statement = statement.limit(limit)
        rows = self.db.exec(statement).all()
        return [
            {
                "log_id": log.id,
                "student": username,
                "event_date": log.event_date,
                "activity": log.activity,
                "hours": log.hours,
                "status": log.status,
            }
            for log, username in rows
        ]

    def count_logs(
        self,
        status: str,
        *,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(VolunteerLog)
            .where(VolunteerLog.status == status)
        )
        if starts_at is not None:
            statement = statement.where(VolunteerLog.approved_at >= starts_at)
        if ends_at is not None:
            statement = statement.where(VolunteerLog.approved_at < ends_at)
        return int(self.db.exec(statement).one())

    def get_log_by_id(self, log_id: int) -> Optional[VolunteerLog]:
        return self.db.get(VolunteerLog, log_id)

    def update_log_status(
        self,
        *,
        log_id: int,
        status: str,
        admin_id: int,
        admin_notes: str | None = None,
    ) -> VolunteerLog:
        log = self.db.get(VolunteerLog, log_id)
        if log is None:
            raise ValueError("Volunteer log not found")

        log.status = status
        log.approved_by_id = admin_id
        log.admin_notes = admin_notes or log.admin_notes
        log.approved_at = datetime.utcnow()
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_approved_hours(self, student_id: int) -> int:
        result = self.db.exec(
            select(func.coalesce(func.sum(VolunteerLog.hours), 0))
            .where(VolunteerLog.student_id == student_id)
            .where(VolunteerLog.status == "approved")
        ).one()
        return int(result or 0)

    def get_all_prizes(self) -> list[Prize]:
        return self.db.exec(
            select(Prize)
            .where(Prize.active == True)
            .order_by(Prize.points_required.asc(), Prize.name.asc())
        ).all()

    def get_prize_by_id(self, prize_id: int) -> Optional[Prize]:
        return self.db.get(Prize, prize_id)

    def create_prize(self, **payload) -> Prize:
        prize = Prize(**payload)
        self.db.add(prize)
        self.db.commit()
        self.db.refresh(prize)
        return prize

    def redeem_prize(self, *, student_id: int, prize_id: int) -> Redemption:
        prize = self.db.get(Prize, prize_id)
        if prize is None or not prize.active:
            raise ValueError("Prize not available")
        if prize.stock_available <= 0:
            raise ValueError("Prize is out of stock")

        existing = self.db.exec(
            select(Redemption)
            .where(Redemption.student_id == student_id)
            .where(Redemption.prize_id == prize_id)
            .where(Redemption.status == "redeemed")
        ).first()
        if existing:
            raise ValueError("Prize already redeemed")

        redemption = Redemption(student_id=student_id, prize_id=prize_id, status="redeemed")
        prize.stock_available -= 1
        self.db.add(redemption)
        self.db.add(prize)
        self.db.commit()
        self.db.refresh(redemption)
        return redemption

    def get_student_redemptions(self, student_id: int) -> list[Redemption]:
        return self.db.exec(
            select(Redemption)
            .where(Redemption.student_id == student_id)
            .order_by(Redemption.redeemed_at.desc())
        ).all()

    def get_redemption_count(self, student_id: int) -> int:
        return self.db.exec(
            select(func.count()).select_from(Redemption).where(Redemption.student_id == student_id)
        ).one()
