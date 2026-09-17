import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import confetti from 'canvas-confetti'
import { api, readHomeCache, writeHomeCache, ADMIN_KEY, type DayOut, type TodayOut } from './api'
import { setFavicon } from './favicon'
import SuggestionModal from './SuggestionModal'

const WEEKDAYS = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado']
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

function fireConfetti() {
  const colors = ['#ef4444', '#f97316', '#facc15', '#22c55e', '#3b82f6', '#6366f1', '#8b5cf6', '#ec4899']
  const defaults = { spread: 70, ticks: 220, gravity: 1, startVelocity: 45, colors, zIndex: 1 } as const
  void confetti({ ...defaults, particleCount: 140, origin: { x: 0.2, y: 0.7 } })
  void confetti({ ...defaults, particleCount: 140, origin: { x: 0.8, y: 0.7 } })
}

const WEEK_CHIP = 52
const WEEK_GAP_TARGET = 5.6 // 0.35rem — gap definido no CSS

function fitWeekGap(el: HTMLElement) {
  const style = getComputedStyle(el)
  const content = el.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight)
  const totalChips = 7 * WEEK_CHIP
  if (totalChips + 6 * WEEK_GAP_TARGET <= content) {
    el.style.removeProperty('gap')
    return
  }
  const gap = Math.max(1, Math.floor((content - totalChips) / 6))
  el.style.gap = `${gap}px`
}

export default function MainScreen() {
  const weekRef = useRef<HTMLElement>(null)
  const confettiFired = useRef(false)
  const [today, setToday] = useState<TodayOut | null>(null)
  const [days, setDays] = useState<DayOut[]>([])
  const [error, setError] = useState('')
  const [showSuggestion, setShowSuggestion] = useState(false)
  const [thankYou, setThankYou] = useState(false)

  useEffect(() => {
    const week = weekRef.current
    if (!week) return
    const apply = () => fitWeekGap(week)
    apply()
    window.addEventListener('resize', apply)
    return () => window.removeEventListener('resize', apply)
  }, [])

  useEffect(() => {
    if (!localStorage.getItem(ADMIN_KEY)) {
      api.registerVisit().catch(() => {})
    }
    const day = iso(new Date())
    const cached = readHomeCache(day)
    if (cached) {
      setToday(cached.today)
      setDays(cached.days)
      setFavicon(cached.today.has_palquinho === true)
      if (cached.today.has_palquinho === true && !confettiFired.current) {
        confettiFired.current = true
        fireConfetti()
      }
    }
    api
      .fetchHome()
      .then(({ today: t, days: d }) => {
        setToday(t)
        setDays(d)
        setFavicon(t.has_palquinho === true)
        if (t.has_palquinho === true && !confettiFired.current) {
          confettiFired.current = true
          fireConfetti()
        }
        writeHomeCache(day, { today: t, days: d })
      })
      .catch((e: Error) => {
        if (!cached) setError(e.message)
      })
  }, [])

  const hasPalquinho = today?.has_palquinho ?? false
  const loading = !today && !error

  const dayMap = new Map(days.map((d) => [d.day, d]))
  const todayIso = iso(new Date())
  const week = currentWeek()

  return (
    <div className={`screen ${hasPalquinho ? 'yes' : 'no'}`}>
      {error ? (
        <main className="mid">
          <p className="error">Deu ruim: {error}</p>
        </main>
      ) : (
        <main className="mid">
          {!loading && (
            <>
              {today && <p className="date-line">{fmtDay(today.day)}</p>}
              <h1 className="big-answer">{hasPalquinho ? 'SIM' : 'NÃO'}</h1>
              {today?.note && <p className="note">{today.note}</p>}
              {today?.instagram && (
                <a
                  className="event-insta"
                  href={today.instagram}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  ver anúncio no instagram ↗
                </a>
              )}
            </>
          )}
        </main>
      )}

      <footer className="week" ref={weekRef}>
        {week.map((d) => {
          const key = iso(d)
          const day = dayMap.get(key)
          const has = day?.has_palquinho ?? false
          const isToday = key === todayIso
          const isPast = key < todayIso
          const cls = [
            'week-day',
            has ? 'yes' : 'no',
            isToday ? 'today' : '',
            isPast ? 'past' : '',
            day?.instagram ? 'clickable' : '',
          ]
            .filter(Boolean)
            .join(' ')
          const title = has
            ? day?.note || (day?.instagram ? 'ver anúncio no instagram ↗' : 'tem palquinho! 🎉')
            : day?.note || 'acho que não tem'
          const inner = (
            <>
              <span className="week-dow">{WEEKDAYS_SHORT[d.getDay()]}</span>
              <span className="week-num">{d.getDate()}</span>
            </>
          )
          return day?.instagram ? (
            <a
              key={key}
              className={cls}
              href={day.instagram}
              target="_blank"
              rel="noopener noreferrer"
              title={title}
            >
              {inner}
            </a>
          ) : (
            <div key={key} className={cls} title={title}>
              {inner}
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