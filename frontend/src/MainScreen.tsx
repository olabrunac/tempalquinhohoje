import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type DayOut, type TodayOut } from './api'
import SuggestionModal from './SuggestionModal'

const WEEKDAYS = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado']
const WEEKDAYS_SHORT = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb']
const MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

function fmtDay(day: string): string {
  const [y, m, d] = day.split('-').map(Number)
  return `${WEEKDAYS[new Date(y, m - 1, d).getDay()]}, ${d} de ${MONTHS[m - 1]} de ${y}`
}

function iso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function currentWeek(): Date[] {
  const today = new Date()
  const start = new Date(today)
  start.setDate(today.getDate() - today.getDay())
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start)
    d.setDate(start.getDate() + i)
    return d
  })
}

export default function MainScreen() {
  const [today, setToday] = useState<TodayOut | null>(null)
  const [days, setDays] = useState<DayOut[]>([])
  const [error, setError] = useState('')
  const [showSuggestion, setShowSuggestion] = useState(false)
  const [thankYou, setThankYou] = useState(false)

  useEffect(() => {
    Promise.all([api.getToday(), api.getDays()])
      .then(([t, d]) => {
        setToday(t)
        setDays(d)
      })
      .catch((e: Error) => setError(e.message))
  }, [])

  const hasPalquinho = today?.has_palquinho ?? false
  const loading = !today && !error

  const dayMap = new Map(days.map((d) => [d.day, d.has_palquinho]))
  const todayIso = iso(new Date())
  const week = currentWeek()

  return (
    <div className={`screen ${hasPalquinho ? 'yes' : 'no'}`}>
      <header className="topbar">
        {today ? <span className="date-line">{fmtDay(today.day)}</span> : <span />}
      </header>

      {error ? (
        <main className="mid">
          <p className="error">Deu ruim: {error}</p>
        </main>
      ) : (
        <main className="mid">
          {!loading && (
            <>
              <h1 className="big-answer">{hasPalquinho ? 'SIM' : 'NÃO'}</h1>
              {today?.note && <p className="note">{today.note}</p>}
            </>
          )}
        </main>
      )}

      <footer className="week">
        {week.map((d) => {
          const key = iso(d)
          const has = dayMap.get(key) ?? false
          const isToday = key === todayIso
          const isPast = key < todayIso
          const cls = ['week-day', has ? 'yes' : 'no', isToday ? 'today' : '', isPast ? 'past' : '']
            .filter(Boolean)
            .join(' ')
          return (
            <div key={key} className={cls}>
              <span className="week-dow">{WEEKDAYS_SHORT[d.getDay()]}</span>
              <span className="week-num">{d.getDate()}</span>
            </div>
          )
        })}
      </footer>

      <div className="corner-nav">
        {thankYou ? (
          <div className="corner-thanks">mandado! o admin vai confirmar 🎉</div>
        ) : (
          <button className="corner-suggest" onClick={() => setShowSuggestion(true)}>
            sabe de algum palquinho?
          </button>
        )}
        <Link className="corner-admin" to="/admin">
          admin
        </Link>
      </div>

      {showSuggestion && (
        <SuggestionModal
          onClose={() => setShowSuggestion(false)}
          onSent={() => {
            setShowSuggestion(false)
            setThankYou(true)
            setTimeout(() => setThankYou(false), 5000)
          }}
        />
      )}
    </div>
  )
}