from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.repositories.awards import AwardRepository
from app.utilities.errors import ConflictError, NotFoundError


class AwardService:
    def __init__(self, repo: AwardRepository):
        self.repo = repo

    def get_points_balance(self, student_id: int) -> int:
        """Spendable points: approved hours minus the cost of prizes already redeemed."""
        return self.repo.get_approved_hours(student_id) - self.repo.get_points_spent(student_id)

    def get_balance(self, student_id: int) -> dict:
        approved = self.repo.get_approved_hours(student_id)
        spent = self.repo.get_points_spent(student_id)
        return {"approved_hours": approved, "points_spent": spent, "points": approved - spent}

    def list_student_logs(self, student_id: int):
        return self.repo.get_user_logs(student_id)

    def list_logs(self, status: str | None = None):
        return self.repo.get_logs(status)

    def list_prizes(self):
        return self.repo.get_all_prizes()

    def list_student_redemptions(self, student_id: int):
        return self.repo.get_student_redemptions(student_id)

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
            "points": self.get_points_balance(student_id),
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

    LOG_STATUSES = ("pending", "approved", "rejected")

    def get_student_hours(self, student_id: int, status: str | None = None):
        logs = self.repo.get_user_logs(student_id)
        status_filter = status if status in self.LOG_STATUSES else None
        if status_filter:
            logs = [log for log in logs if log.status == status_filter]
        return {
            "logs": logs,
            "status_filter": status_filter,
            "rejected_logs": [log for log in logs if log.status == "rejected" and log.admin_notes],
            "approved_hours": self.repo.get_approved_hours(student_id),
        }

    def get_resubmit_source(self, *, student_id: int, log_id: int):
        """A student's own rejected log, used to prefill the resubmit form."""
        log = self.repo.get_log_by_id(log_id)
        if log is None or log.student_id != student_id or log.status != "rejected":
            return None
        return log

    def get_admin_queue(self):
        return {
            "pending_logs": self.repo.get_pending_summaries(),
            "total_pending": self.repo.count_logs("pending"),
        }

    def get_log_for_review(self, log_id: int):
        return self.repo.get_log_by_id(log_id)

    def get_admin_dashboard(self):
        day_start = datetime.combine(datetime.utcnow().date(), time.min)
        next_day = day_start + timedelta(days=1)
        return {
            "pending_reviews": self.repo.count_logs("pending"),
            "approved_today": self.repo.count_logs(
                "approved",
                starts_at=day_start,
                ends_at=next_day,
            ),
            "rejected_today": self.repo.count_logs(
                "rejected",
                starts_at=day_start,
                ends_at=next_day,
            ),
            "latest_pending": self.repo.get_pending_summaries(limit=2),
        }

    def decide_log(self, *, log_id: int, admin_id: int, action: str, admin_notes: str | None = None):
        if action not in {"approved", "rejected"}:
            raise ValueError("Unsupported decision")
        note_value = (admin_notes or "").strip() or None
        if action == "rejected" and note_value is None:
            raise ValueError("Please provide a rejection reason")
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
        return {
            "prizes": prizes,
            "redeemed_ids": redeemed_ids,
            "approved_hours": self.repo.get_approved_hours(student_id),
            "points": self.get_points_balance(student_id),
        }

    def get_prize_confirmation(self, *, student_id: int, prize_id: int):
        prize = self.repo.get_prize_by_id(prize_id)
        if prize is None:
            raise NotFoundError("Prize not found")

        current_balance = self.get_points_balance(student_id)
        cost = prize.points_required
        return {
            "prize": prize,
            "cost": cost,
            "current_balance": current_balance,
            "balance_after": current_balance - cost,
        }

    def redeem_prize(self, *, student_id: int, prize_id: int):
        prize = self.repo.get_prize_by_id(prize_id)
        if prize is None:
            raise NotFoundError("Prize not found")
        already = any(
            r.prize_id == prize_id and r.status == "redeemed"
            for r in self.repo.get_student_redemptions(student_id)
        )
        if already:
            raise ConflictError("Prize already redeemed")
        if self.get_points_balance(student_id) < prize.points_required:
            raise ValueError("You need more approved hours to redeem this prize")
        return self.repo.redeem_prize(student_id=student_id, prize_id=prize_id)
