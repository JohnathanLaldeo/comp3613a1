"""Request/response schemas for the Student Awards JSON API."""

from datetime import date, datetime
from typing import Literal, Optional

from sqlmodel import SQLModel


class LoginRequest(SQLModel):
    username: str
    password: str


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class LogCreate(SQLModel):
    event_date: date
    hours: int
    activity: str
    notes: Optional[str] = None


class LogDecision(SQLModel):
    status: Literal["approved", "rejected"]
    admin_notes: Optional[str] = None


class LogRead(SQLModel):
    id: int
    student_id: int
    event_date: date
    hours: int
    activity: str
    notes: Optional[str] = None
    status: str
    admin_notes: Optional[str] = None
    submitted_at: datetime
    approved_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None


class PrizeRead(SQLModel):
    id: int
    name: str
    description: str
    points_required: int
    category: str
    stock_available: int


class RedemptionRead(SQLModel):
    id: int
    student_id: int
    prize_id: int
    redeemed_at: datetime
    status: str


class BalanceRead(SQLModel):
    approved_hours: int
    points_spent: int
    points: int


class DashboardRead(SQLModel):
    pending_reviews: int
    approved_today: int
    rejected_today: int
