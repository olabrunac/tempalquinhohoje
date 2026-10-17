import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import confetti from 'canvas-confetti'
import { api, type DayOut, type EventItem, type TodayOut } from './api'
import { setFavicon } from './favicon'
import { VERSION } from './version'
import SuggestionModal from './SuggestionModal'
import ShareModal from './ShareModal'
import type { ShareEvent, ShareState } from './ShareCard'

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

// Cada evento do dia tem nota e link próprios. Sem link, a nota é só texto.
function EventList({ events }: { events?: EventItem[] }) {
  if (!events?.length) return null
  return (
    <div className="notes-list-simple">
      {events.map((e) =>
        e.instagram ? (
          <a key={e.id} className="note-text-simple note-link" href={e.instagram} target="_blank" rel="noopener noreferrer">
            {e.note} <span aria-hidden="true">↗</span>
          </a>
        ) : (
          <p key={e.id} className="note-text-simple">
            {e.note}
          </p>
        )
      )}
    </div>
  )
}

function getWeekDays(start: Date): Date[] {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start)
    d.setDate(start.getDate() + i)
    return d
  })
}

// Lê o ?dia= da URL do link compartilhado (2026-10-15). Devolve null se não
// tiver ou se for inválido — aí a tela fica no comportamento normal (hoje).
function parseDiaParam(): string | null {
  const v = new URLSearchParams(window.location.search).get('dia')
  if (!v || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return null
  const [y, m, d] = v.split('-').map(Number)
  const dt = new Date(y, m - 1, d)
  if (dt.getFullYear() !== y || dt.getMonth() !== m - 1 || dt.getDate() !== d) return null
  return v
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
  const navigate = useNavigate()
  const weekRef = useRef<HTMLElement>(null)
  const confettiFired = useRef(false)
  const [today, setToday] = useState<TodayOut | null>(null)
  const [days, setDays] = useState<DayOut[]>([])
  const [error, setError] = useState('')
  const [showSuggestion, setShowSuggestion] = useState(false)
  const [showShare, setShowShare] = useState(false)
  const [thankYou, setThankYou] = useState(false)
  const [daysLoaded, setDaysLoaded] = useState(false)
  const [selectedDayIso, setSelectedDayIso] = useState<string | null>(() => parseDiaParam())

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (showSuggestion || e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }
      if (e.key === 'ç' || e.key === 'Ç') {
        e.preventDefault()
        navigate('/admin')
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [navigate, showSuggestion])

  const [weekStart, setWeekStart] = useState<Date>(() => {
    const dia = parseDiaParam()
    // Link compartilhado: abre já na semana daquele dia, com ele selecionado.
    const t = dia ? new Date(dia + 'T12:00:00') : new Date()
    const start = new Date(t)
    start.setDate(t.getDate() - t.getDay())
    return start
  })
  const [animKey, setAnimKey] = useState(0)
  const [slideDir, setSlideDir] = useState(1)

  useEffect(() => {
    const week = weekRef.current
    if (!week) return
    const apply = () => fitWeekGap(week)
    apply()
    window.addEventListener('resize', apply)
    return () => window.removeEventListener('resize', apply)
  }, [weekStart])

  useEffect(() => {
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
        setDaysLoaded(true)
      })
      .catch(() => {
        setDaysLoaded(true)
      })
  }, [])

  const todayIso = iso(new Date())
  const activeIso = selectedDayIso ?? todayIso
  const dayMap = new Map(days.map((d) => [d.day, d]))
  const currentDayData = activeIso === todayIso ? today : dayMap.get(activeIso)

  const hasPalquinho = currentDayData?.has_palquinho ?? false
// has_palquinho null = não marcado (mostra NÃO). O laranja vem de is_other_event,
  // que o admin escolheu no botão — o dia pode ter nota e continuar vermelho.
  const isOther = currentDayData?.has_palquinho === false && currentDayData.is_other_event
  // Hoje depende do /today; um dia navegado/compartilhado depende do /days —
  // os dois precisam estar prontos antes de mostrar SIM/NÃO (senão pisca NÃO).
  const loading = !error && (!today || (activeIso !== todayIso && !daysLoaded))
  const screenClass = loading ? 'unknown' : hasPalquinho ? 'yes' : isOther ? 'other' : 'no'

  const week = getWeekDays(weekStart)
  const activeIndex = week.findIndex((d) => iso(d) === activeIso)

  // Dados da imagem "compartilhar dia": o dia em exibição (hoje ou navegado na
  // semana). A cor e os eventos vêm do que está na tela; a semana, dos dias salvos.
  const shareState: ShareState = hasPalquinho ? 'yes' : isOther ? 'other' : 'no'
  const shareEvents: ShareEvent[] = (currentDayData?.events ?? []).map((e) => ({ note: e.note, instagram: e.instagram }))
  const shareStateOf = (k: string): ShareState => {
    const dd = k === todayIso ? today : dayMap.get(k)
    if (!dd) return 'no'
    return dd.has_palquinho ? 'yes' : dd.is_other_event ? 'other' : 'no'
  }

  const goLeft = () => {
    if (activeIndex > 0) {
      setSelectedDayIso(iso(week[activeIndex - 1]))
    } else {
      const newStart = new Date(weekStart)
      newStart.setDate(weekStart.getDate() - 7)
      setWeekStart(newStart)
      setSlideDir(-1)
      setAnimKey((k) => k + 1)
      const newWeek = getWeekDays(newStart)
      setSelectedDayIso(iso(newWeek[6]))
    }
  }

  const goRight = () => {
    if (activeIndex >= 0 && activeIndex < 6) {
      setSelectedDayIso(iso(week[activeIndex + 1]))
    } else {
      const newStart = new Date(weekStart)
      newStart.setDate(weekStart.getDate() + 7)
      setWeekStart(newStart)
      setSlideDir(1)
      setAnimKey((k) => k + 1)
      const newWeek = getWeekDays(newStart)
      setSelectedDayIso(iso(newWeek[0]))
    }
  }

  return (
    <div className={`screen ${screenClass}`}>
      <main className="mid">
        {error ? (
          <p className="error">Deu ruim: {error}</p>
        ) : loading ? (
          <h1 className="big-answer muted" style={{ opacity: 0.3 }}>...</h1>
        ) : (
          <div className="answer-block">
            <div className="back-slot">
              {selectedDayIso && selectedDayIso !== todayIso && (
                <button
                  type="button"
                  className="admin-link"
                  onClick={() => setSelectedDayIso(null)}
                  style={{ background: 'rgba(255,255,255,0.1)', padding: '0.3rem 0.8rem', borderRadius: '999px', color: '#fff' }}
                >
                  voltar para hoje
                </button>
              )}
            </div>
            <p className="date-line">{fmtDay(activeIso)}</p>
            <h1 className="big-answer">{hasPalquinho ? 'SIM' : (activeIso === '2026-10-04' || activeIso === '2026-10-25') ? '13' : 'NÃO'}</h1>
          </div>
        )}
        <div className="extra-block">
          <EventList events={currentDayData?.events} />
        </div>
      </main>

      <div className="week-nav-container">
        <button type="button" className="week-arrow" onClick={goLeft} aria-label="dia anterior">
          ‹
        </button>
        <footer className="week slide-anim" ref={weekRef} key={animKey} style={{ '--slide-dir': `${slideDir * 20}px` } as React.CSSProperties}>
          {week.map((d) => {
            const key = iso(d)
            const day = dayMap.get(key)
            const has = day?.has_palquinho ?? false
            const isOtherDay = day?.has_palquinho === false && day.is_other_event
            const notas = day?.events.map((e) => e.note.replace(/\n/g, ' · ')).join(' · ')
            const isToday = key === todayIso
            const isPast = key < todayIso
            const isViewing = key === activeIso
            const cls = [
              'week-day',
              has ? 'yes' : isOtherDay ? 'other' : 'no',
              isToday ? 'today' : '',
              isPast ? 'past' : '',
              isViewing ? 'viewing' : '',
            ]
              .filter(Boolean)
              .join(' ')
            const title = notas || (has ? 'tem palquinho! 🎉' : isOtherDay ? 'outro evento' : 'acho que não tem')
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
        <button type="button" className="week-arrow" onClick={goRight} aria-label="próximo dia">
          ›
        </button>
      </div>

      <div className="corner-nav">
        {thankYou ? (
          <div className="corner-thanks">mandado! o admin vai confirmar</div>
        ) : (
          <button className="corner-suggest" onClick={() => setShowSuggestion(true)}>
            quer divulgar um evento? manda aqui
          </button>
        )}
        <Link className="corner-suggest" to="/eventos" style={{ display: 'inline-block', textAlign: 'center' }}>
          calendário de eventos
        </Link>
        <div className="corner-icons">
          <button
            type="button"
            className="corner-insta corner-share"
            onClick={() => setShowShare(true)}
            disabled={loading}
            aria-label="Compartilhar o dia (gerar imagem)"
            title="compartilhar o dia (gerar imagem)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M4 12v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7" />
              <polyline points="16 6 12 2 8 6" />
              <line x1="12" y1="2" x2="12" y2="15" />
            </svg>
          </button>
          <a
            className="corner-insta"
            href="https://www.instagram.com/tempalquinhohoje/"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Instagram do tem palquinho hoje"
            title="@tempalquinhohoje no Instagram"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
              <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
              <line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
            </svg>
          </a>
        </div>
      </div>

      <span className="app-version">v{VERSION}</span>

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

      {showShare && (
        <ShareModal
          day={activeIso}
          state={shareState}
          events={shareEvents}
          stateOf={shareStateOf}
          onClose={() => setShowShare(false)}
        />
      )}
    </div>
  )
}
