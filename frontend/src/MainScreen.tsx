import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import confetti from 'canvas-confetti'
import { api, ADMIN_KEY, type DayOut, type TodayOut } from './api'
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
const WEEK_GAP_TARGET = 5.6

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
  const [selectedDayIso, setSelectedDayIso] = useState<string | null>(null)
  const [menuOpen, setMenuOpen] = useState(false)

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

    api
      .getToday()
      .then((t) => {
        setToday(t)
        setFavicon(t.has_palquinho === true)
        if (t.has_palquinho === true && !confettiFired.current) {
          confettiFired.current = true
          fireConfetti()
        }
      })
      .catch((e: Error) => {
        setError(e.message)
      })

    api
      .getDays()
      .then((d) => {
        setDays(d)
      })
      .catch(() => {})
  }, [])

  const todayIso = iso(new Date())
  const activeIso = selectedDayIso ?? todayIso
  const dayMap = new Map(days.map((d) => [d.day, d]))
  const currentDayData = activeIso === todayIso ? today : dayMap.get(activeIso)

  const hasPalquinho = currentDayData?.has_palquinho ?? false
  const status = currentDayData?.status ?? (hasPalquinho ? 'yes' : 'no')
  const loading = !today && !error && activeIso === todayIso
  const screenClass = loading ? 'unknown' : hasPalquinho ? 'yes' : status === 'other' ? 'other' : 'no'

  const week = currentWeek()

  return (
    <div className={`screen ${screenClass}`}>
      <main className="mid">
        {selectedDayIso && selectedDayIso !== todayIso && (
          <button
            type="button"
            className="admin-link"
            onClick={() => setSelectedDayIso(null)}
            style={{ marginBottom: '-0.5rem', background: 'rgba(255,255,255,0.1)', padding: '0.3rem 0.8rem', borderRadius: '999px', color: '#fff' }}
          >
            ← voltar para hoje
          </button>
        )}
        {error ? (
          <p className="error">Deu ruim: {error}</p>
        ) : loading ? (
          <h1 className="big-answer muted" style={{ opacity: 0.3 }}>...</h1>
        ) : (
          <>
            <p className="date-line">{fmtDay(activeIso)}</p>
            <h1 className="big-answer">{hasPalquinho ? 'SIM' : 'NÃO'}</h1>
            {currentDayData?.note && <p className="note">{currentDayData.note}</p>}
            {currentDayData?.instagram && (
              <a
                className="event-insta"
                href={currentDayData.instagram}
                target="_blank"
                rel="noopener noreferrer"
              >
                ver anúncio no instagram ↗
              </a>
            )}
          </>
        )}
      </main>

      <footer className="week" ref={weekRef}>
        {week.map((d) => {
          const key = iso(d)
          const day = dayMap.get(key)
          const has = day?.has_palquinho ?? false
          const st = day?.status ?? (has ? 'yes' : 'no')
          const isToday = key === todayIso
          const isPast = key < todayIso
          const isSelected = key === activeIso
          const cls = [
            'week-day',
            has ? 'yes' : st === 'other' ? 'other' : 'no',
            isToday ? 'today' : '',
            isPast ? 'past' : '',
            isSelected ? 'selected' : '',
          ]
            .filter(Boolean)
            .join(' ')
          const title = has
            ? day?.note || 'tem palquinho! 🎉'
            : st === 'other'
            ? day?.note || 'outro evento'
            : day?.note || 'acho que não tem'
          const inner = (
            <>
              <span className="week-dow">{WEEKDAYS_SHORT[d.getDay()]}</span>
              <span className="week-num">{d.getDate()}</span>
            </>
          )
          return (
            <button
              type="button"
              key={key}
              className={cls}
              title={title}
              onClick={() => setSelectedDayIso(key)}
              style={{ background: undefined, border: 'none', cursor: 'pointer', padding: 0 }}
            >
              {inner}
            </button>
          )
        })}
      </footer>

      <div className="corner-nav hamburger-container">
        {thankYou ? (
          <div className="corner-thanks">mandado! o admin vai confirmar 🎉</div>
        ) : (
          <button
            type="button"
            className="hamburger-btn"
            onClick={() => setMenuOpen((o) => !o)}
            aria-label="menu de opções"
          >
            ☰
          </button>
        )}
        {menuOpen && (
          <div className="menu-dropdown">
            <button
              type="button"
              className="menu-item"
              onClick={() => {
                setMenuOpen(false)
                setShowSuggestion(true)
              }}
            >
              sabe de algum? clica aqui
            </button>
            <Link
              className="menu-item"
              to="/eventos"
              onClick={() => setMenuOpen(false)}
            >
              outros eventos
            </Link>
          </div>
        )}
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
