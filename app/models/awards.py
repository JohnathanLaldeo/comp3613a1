from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class VolunteerLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id", index=True)
    approved_by_id: Optional[int] = Field(default=None, foreign_key="user.id")
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    event_date: date
    hours: int = Field(default=1, ge=1, le=100)

    activity: str
    notes: Optional[str] = None
    status: str = Field(default="pending", index=True)
    admin_notes: Optional[str] = None

    approved_at: Optional[datetime] = Field(default=None, index=True)


class Prize(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str
    points_required: int = Field(default=0, ge=0)
    category: str = Field(default="General")
    active: bool = Field(default=True)
    stock_available: int = Field(default=1, ge=0)


class Redemption(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id", index=True)
    prize_id: int = Field(foreign_key="prize.id", index=True)
    redeemed_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="redeemed", index=True)
    notes: Optional[str] = None
