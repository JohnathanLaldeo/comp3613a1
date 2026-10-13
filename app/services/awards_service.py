from __future__ import annotations

from datetime import date

from app.repositories.awards import AwardRepository


class AwardService:
    def __init__(self, repo: AwardRepository):
        self.repo = repo

    def get_student_dashboard(self, student_id: int):
        logs = self.repo.get_user_logs(student_id)
        approved_hours = self.repo.get_approved_hours(student_id)
        pending_count = sum(1 for log in logs if log.status == "pending")
        prizes = self.repo.get_all_prizes()
        return {
            "approved_hours": approved_hours,
            "pending_hours": sum(log.hours for log in logs if log.status == "pending"),
            "pending_count": pending_count,
            "logs": logs[:5],
            "prizes": prizes,
            "points": approved_hours,
        }

    def create_log(
        self,
        *,
        student_id: int,
        event_date: date,
        hours: int,
        activity: str,
        notes: str | None = None,
    ):
        if not activity.strip():
            raise ValueError("Please add an activity")
        if hours <= 0:
            raise ValueError("Hours must be greater than zero")
        notes_value = (notes or "").strip() or None
        return self.repo.create_volunteer_log(
            student_id=student_id,
            event_date=event_date,
            hours=hours,
            activity=activity.strip(),
            notes=notes_value,
        )

    def get_student_hours(self, student_id: int):
        logs = self.repo.get_user_logs(student_id)
        return {"logs": logs, "approved_hours": self.repo.get_approved_hours(student_id)}

    def get_admin_queue(self):
        logs = self.repo.get_pending_logs()
        return {
            "pending_logs": logs,
            "total_pending": len(logs),
        }

    def decide_log(self, *, log_id: int, admin_id: int, action: str, admin_notes: str | None = None):
        if action not in {"approved", "rejected"}:
            raise ValueError("Unsupported decision")
        note_value = (admin_notes or "").strip() or None
        return self.repo.update_log_status(
            log_id=log_id,
            status=action,
            admin_id=admin_id,
            admin_notes=note_value,
        )

    def get_prize_catalog(self, student_id: int):
        prizes = self.repo.get_all_prizes()
        redemptions = self.repo.get_student_redemptions(student_id)
        redeemed_ids = {item.prize_id for item in redemptions}
        approved_hours = self.repo.get_approved_hours(student_id)
        return {
            "prizes": prizes,
            "redeemed_ids": redeemed_ids,
            "approved_hours": approved_hours,
        }

    def redeem_prize(self, *, student_id: int, prize_id: int):
        prize = self.repo.get_prize_by_id(prize_id)
        if prize is None:
            raise ValueError("Prize not found")
        points = self.repo.get_approved_hours(student_id)
        if points < prize.points_required:
            raise ValueError("You need more approved hours to redeem this prize")
        return self.repo.redeem_prize(student_id=student_id, prize_id=prize_id)
