from datetime import date, datetime

from pydantic import BaseModel


class DayOut(BaseModel):
    day: date
    has_palquinho: bool
    note: str | None = None

    class Config:
        from_attributes = True


class TodayOut(BaseModel):
    day: date
    has_palquinho: bool | None = None  # None = não marcado ainda
    note: str | None = None


class VoteIn(BaseModel):
    day: date
    name: str
    vote: bool


class VoteOut(BaseModel):
    id: int
    day: date
    name: str
    vote: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DaySetIn(BaseModel):
    has_palquinho: bool
    note: str | None = None


class SuggestionOut(BaseModel):
    day: date
    has_palquinho: bool | None = None  # None = ainda não confirmado
    votes: list[VoteOut]
