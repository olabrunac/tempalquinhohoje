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

function cleanNote(note?: string | null): string | null {
  if (!note) return null
  return note.replace(/^\[EVENTO\]\s*/i, '')
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
        setDays(d.filter((x) => x.has_palquinho || x.note?.startsWith('[EVENTO]')))
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

      <main className="admin-body events-body" style={{ gridTemplateColumns: '1fr' }}>
        <section className="calendar-col">
          <div className="calendar-nav">
            <button className="btn ghost" onClick={() => nav(-1)}>
              ←
            </button>
            <h2 className="calendar-title" style={{ fontSize: '1.4rem' }}>
              {MONTHS[month.month]} {month.year}
            </h2>
            <button className="btn ghost" onClick={() => nav(1)}>
              →
            </button>
          </div>
          {loading ? (
            <p className="muted" style={{ textAlign: 'center', padding: '2rem' }}>carregando...</p>
          ) : (
            <div className="calendar-grid events-calendar-grid">
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
                const isOther = day && !day.has_palquinho && day.note?.startsWith('[EVENTO]')

                const cls = [
                  'cal-cell',
                  hasEvent ? (isOther ? 'has-other' : 'has-yes') : '',
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
          <div className="legend" style={{ fontSize: '0.95rem' }}>
            <span className="legend-yes">Tem palquinho</span>
            <span className="legend-other" style={{ color: 'var(--orange)', fontWeight: 600 }}>Tem rolê!</span>
          </div>

          {selectedDay && (
            <div className="panel" style={{ marginTop: '1rem' }}>
              <h3 className="panel-title">{fmtPt(selectedDay.day)}</h3>
              <p className="current-status" style={{ color: !selectedDay.has_palquinho && selectedDay.note?.startsWith('[EVENTO]') ? 'var(--orange)' : 'var(--green)' }}>
                {!selectedDay.has_palquinho && selectedDay.note?.startsWith('[EVENTO]') ? 'Tem rolê confirmado!!!' : 'Tem palquinho confirmado'}
              </p>
              {cleanNote(selectedDay?.note) && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.5rem' }}>
                  {cleanNote(selectedDay?.note)
                    ?.split('\n')
                    .map((line, idx) => line.trim() && (
                      <div key={idx} className="muted" style={{ background: '#1f2937', padding: '0.5rem 0.8rem', borderRadius: '8px', color: '#e5e7eb', fontSize: '0.95rem' }}>
                        {line}
                      </div>
                    ))}
                </div>
              )}
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
