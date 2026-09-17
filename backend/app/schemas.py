from datetime import date, datetime

from pydantic import BaseModel


class DayOut(BaseModel):
    day: date
    has_palquinho: bool
    note: str | None = None
    instagram: str | None = None

    class Config:
        from_attributes = True


class TodayOut(BaseModel):
    day: date
    has_palquinho: bool | None = None  # None = não marcado ainda
    note: str | None = None
    instagram: str | None = None


class SuggestionIn(BaseModel):
    day: date
    organizer: str
    instagram: str | None = None


class SuggestionOut(BaseModel):
    id: int
    day: date
    organizer: str
    instagram: str | None = None
    status: str
    created_at: datetime
    has_palquinho: bool | None = None  # estado atual do dia (ajuda o admin)

    class Config:
        from_attributes = True


class DaySetIn(BaseModel):
    has_palquinho: bool
    note: str | None = None
    instagram: str | None = None


class VisitDayOut(BaseModel):
    day: date
    count: int


class VisitsAdminOut(BaseModel):
    total: int
    today: int
    days: list[VisitDayOut]
