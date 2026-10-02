from datetime import date, datetime

from pydantic import BaseModel, Field

# Limites de tamanho: cortam spam/abusos antes de chegar no banco.
MAX_ORGANIZER = 80  # casa com String(80) do model
MAX_INSTAGRAM = 300  # casa com String(300) do model
MAX_NOTE = 2000


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


class HomeOut(BaseModel):
    today: TodayOut
    days: list[DayOut]


class SuggestionIn(BaseModel):
    day: date
    organizer: str = Field(min_length=1, max_length=MAX_ORGANIZER)
    instagram: str | None = Field(default=None, max_length=MAX_INSTAGRAM)


class SuggestionOut(BaseModel):
    id: int
    day: date
    organizer: str
    instagram: str | None = None
    status: str
    action: str | None = None  # confirm / dismiss (só quando resolvida)
    solved_at: datetime | None = None
    created_at: datetime
    has_palquinho: bool | None = None  # estado atual do dia (ajuda o admin)

    class Config:
        from_attributes = True


class DaySetIn(BaseModel):
    has_palquinho: bool
    note: str | None = Field(default=None, max_length=MAX_NOTE)
    instagram: str | None = Field(default=None, max_length=MAX_INSTAGRAM)


class DashboardOut(BaseModel):
    days: list[DayOut]
    pending: list[SuggestionOut]
    archive: list[SuggestionOut]
