from datetime import date, datetime, timedelta, timezone

# "Hoje" do site é o dia de quem usa: horário de Brasília.
# Brasil não tem horário de verão desde 2019 — fuso fixo UTC-3 (sem depender de tzdata).
BRAZIL_TZ = timezone(timedelta(hours=-3))


def today_local() -> date:
    """Dia atual no horário de Brasília — usado pra marcar dia, visita e sugestão."""
    return datetime.now(BRAZIL_TZ).date()