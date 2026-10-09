from datetime import date, datetime

from pydantic import BaseModel, Field

# Limites de tamanho: cortam spam/abusos antes de chegar no banco.
MAX_ORGANIZER = 80  # casa com String(80) do model
MAX_INSTAGRAM = 300  # casa com String(300) do model
MAX_NOTE = 2000
MAX_EVENTS_PER_DAY = 5  # trava de segurança: 5 eventos por dia é o suficiente


class EventOut(BaseModel):
    id: int
    position: int
    note: str
    instagram: str | None = None

    class Config:
        from_attributes = True


class EventIn(BaseModel):
    note: str = Field(min_length=1, max_length=MAX_NOTE)
    instagram: str | None = Field(default=None, max_length=MAX_INSTAGRAM)


class DayOut(BaseModel):
    day: date
    has_palquinho: bool
    is_other_event: bool = False  # sem palquinho, mas é outro evento (laranja)
    events: list[EventOut] = Field(default_factory=list)

    class Config:
        from_attributes = True


class TodayOut(BaseModel):
    day: date
    has_palquinho: bool | None = None  # None = não marcado ainda
    is_other_event: bool = False
    events: list[EventOut] = Field(default_factory=list)


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
    # Só faz sentido com has_palquinho=false: dia sem palquinho que é outro evento
    # (laranja). Com has_palquinho=true o site ignora — o dia é verde.
    is_other_event: bool = False
    # A lista inteira substitui os eventos do dia. Limite de 5 corta erro de digitação
    # e abuso antes do banco; o frontend esconde o "+" no mesmo ponto.
    events: list[EventIn] = Field(default_factory=list, max_length=MAX_EVENTS_PER_DAY)


class DashboardOut(BaseModel):
    days: list[DayOut]
    pending: list[SuggestionOut]
    archive: list[SuggestionOut]
