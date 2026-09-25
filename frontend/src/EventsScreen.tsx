import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type DayOut } from './api'

const MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
const WEEKDAYS = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb']

function iso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function fmtPt(day: string): string {
  const [y, m, d] = day.split('-').map(Number)
  return `${d} de ${MONTHS[m - 1]} de ${y}`
}

function buildCells(year: number, month: number): (Date | null)[] {
  const first = new Date(year, month, 1)
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells: (Date | null)[] = []
  for (let i = 0; i < first.getDay(); i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d))
  return cells
}

export default function EventsScreen() {
  const now = new Date()
  const [month, setMonth] = useState({ year: now.getFullYear(), month: now.getMonth() })
  const [days, setDays] = useState<DayOut[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedDay, setSelectedDay] = useState<DayOut | null>(null)

  useEffect(() => {
    api
      .getDays()
      .then((d) => {
        setDays(d.filter((x) => x.status === 'yes' || x.status === 'other' || x.has_palquinho))
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const dayMap = new Map(days.map((d) => [d.day, d]))
  const cells = buildCells(month.year, month.month)
  const todayIso = iso(now)

  const nav = (delta: number) => {
    const next = new Date(month.year, month.month + delta, 1)
    setMonth({ year: next.getFullYear(), month: next.getMonth() })
    setSelectedDay(null)
  }

  return (
    <div className="screen admin">
      <header className="topbar">
        <Link className="admin-link" to="/">
          ← voltar
        </Link>
        <span className="admin-link" style={{ cursor: 'default' }}>outros eventos</span>
      </header>

      <main className="admin-body" style={{ gridTemplateColumns: '1fr', maxWidth: '600px' }}>
        <section className="calendar-col">
          <div className="calendar-nav">
            <button className="btn ghost" onClick={() => nav(-1)}>
              ←
            </button>
            <h2 className="calendar-title">
              {MONTHS[month.month]} {month.year}
            </h2>
            <button className="btn ghost" onClick={() => nav(1)}>
              →
            </button>
          </div>
          {loading ? (
            <p className="muted" style={{ textAlign: 'center', padding: '2rem' }}>carregando...</p>
          ) : (
            <div className="calendar-grid">
              {WEEKDAYS.map((w) => (
                <div key={w} className="cal-weekday">
                  {w}
                </div>
              ))}
              {cells.map((c, i) => {
                if (!c) return <div key={i} className="cal-empty" />
                const key = iso(c)
                const day = dayMap.get(key)
                const isToday = key === todayIso
                const isSelected = selectedDay?.day === key
                const hasEvent = !!day
                const status = day?.status ?? (day?.has_palquinho ? 'yes' : 'no')

                const cls = [
                  'cal-cell',
                  hasEvent ? (status === 'other' ? 'has-other' : 'has-yes') : '',
                  isToday ? 'today' : '',
                  isSelected ? 'selected' : '',
                ]
                  .filter(Boolean)
                  .join(' ')

                return (
                  <button
                    key={key}
                    className={cls}
                    disabled={!hasEvent}
                    onClick={() => {
                      if (day) setSelectedDay(day)
                    }}
                    style={{ cursor: hasEvent ? 'pointer' : 'default', opacity: hasEvent ? 1 : 0.4 }}
                  >
                    {c.getDate()}
                  </button>
                )
              })}
            </div>
          )}
          <div className="legend">
            <span className="legend-yes">palquinho SIM</span>
            <span style={{ color: 'var(--orange)' }}>● outro evento</span>
          </div>

          {selectedDay && (
            <div className="panel" style={{ marginTop: '1rem' }}>
              <h3 className="panel-title">{fmtPt(selectedDay.day)}</h3>
              <p className="current-status" style={{ color: selectedDay.status === 'other' ? 'var(--orange)' : 'var(--green)' }}>
                {selectedDay.status === 'other' ? '🗓️ Outro evento confirmado' : '🎉 Palquinho SIM confirmado'}
              </p>
              {selectedDay.note && <p className="muted">{selectedDay.note}</p>}
              {selectedDay.instagram && (
                <a
                  className="event-insta"
                  style={{ display: 'inline-block', marginTop: '0.5rem', textAlign: 'center' }}
                  href={selectedDay.instagram}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  ver anúncio no instagram ↗
                </a>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
