import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import confetti from 'canvas-confetti'
import { api, type DayOut, type EventItem, type TodayOut } from './api'
import { setFavicon } from './favicon'
import { VERSION } from './version'
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

// "qui, 19/11" — formato curto do aviso de próximo palquinho.
function fmtShort(day: string): string {
  const [y, m, d] = day.split('-').map(Number)
  return `${WEEKDAYS_SHORT[new Date(y, m - 1, d).getDay()]}, ${d}/${m}`
}

const VOTER_KEY = 'tph_voter'
const VOTE_PREFIX = 'tph_vote:'

// Token anônimo do navegador: identifica a resposta de "você vai?" sem nome,
// e-mail ou IP. É o que permite trocar o voto em vez de somar outro.
function getVoter(): string {
  try {
    const saved = localStorage.getItem(VOTER_KEY)
    if (saved) return saved
    const created = crypto.randomUUID().replace(/-/g, '')
    localStorage.setItem(VOTER_KEY, created)
    return created
  } catch {
    return crypto.randomUUID().replace(/-/g, '')
  }
}

// Respostas já dadas neste navegador (por dia), pra não perguntar de novo.
function readVotes(): Record<string, boolean> {
  const out: Record<string, boolean> = {}
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (!key?.startsWith(VOTE_PREFIX)) continue
      out[key.slice(VOTE_PREFIX.length)] = localStorage.getItem(key) === '1'
    }
  } catch {
    // storage bloqueado: o voto vale só nesta aba
  }
  return out
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
  const [today, setToday] = useState<TodayOut | null>(null)
  const [days, setDays] = useState<DayOut[]>([])
  const [error, setError] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const [showSuggestion, setShowSuggestion] = useState(false)
  const [thankYou, setThankYou] = useState(false)
  const [selectedDayIso, setSelectedDayIso] = useState<string | null>(null)
  const [myVotes, setMyVotes] = useState<Record<string, boolean>>(readVotes)
  const [voteCounts, setVoteCounts] = useState<Record<string, { going: number; total: number }>>({})
  const [voting, setVoting] = useState(false)
  const [voteError, setVoteError] = useState('')
  const voterRef = useRef<string | null>(null)

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

  useEffect(() => {
    if (!menuOpen) return
    const closeOnEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [menuOpen])

  const [weekStart, setWeekStart] = useState<Date>(() => {
    const t = new Date()
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
// has_palquinho null = não marcado (mostra NÃO). O laranja vem de is_other_event,
  // que o admin escolheu no botão — o dia pode ter nota e continuar vermelho.
  const isOther = currentDayData?.has_palquinho === false && currentDayData.is_other_event
  const loading = !today && !error && activeIso === todayIso
  const screenClass = loading ? 'unknown' : hasPalquinho ? 'yes' : isOther ? 'other' : 'no'

  // Confete sempre que o dia visto vira SIM: ao abrir o site num dia SIM e ao
  // navegar pra um dia SIM. Clicar no SIM também solta de novo (onClick abaixo).
  useEffect(() => {
    if (loading || !hasPalquinho) return
    fireConfetti()
  }, [activeIso, hasPalquinho, loading])

  // O erro do voto vale só pro dia em que aconteceu: ao trocar de dia, some.
  useEffect(() => {
    setVoteError('')
  }, [activeIso])

  const week = getWeekDays(weekStart)
  const activeIndex = week.findIndex((d) => iso(d) === activeIso)

  // Próximo dia SIM a partir do dia que está na tela (nunca no passado).
  // Tem que ser relativo ao dia VISTO: num dia depois do próximo palquinho, olhar
  // "de hoje" apontaria pra uma data já passada daquele dia. O /days já vem ordenado.
  const nextYes =
    days.find((d) => d.has_palquinho && d.day > activeIso && d.day >= todayIso) ?? null

  // "você vai?": contagem do servidor, com override otimista depois do voto.
  const votes = voteCounts[activeIso] ?? {
    going: currentDayData?.going_count ?? 0,
    total: currentDayData?.total_count ?? 0,
  }
  const myVote = myVotes[activeIso]
  const canVote = hasPalquinho && activeIso >= todayIso
  const voteLabel =
    votes.total === 0
      ? '0 respostas'
      : `${votes.going}/${votes.total} ${votes.going === 1 ? 'vai' : 'vão'}`

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

  // Pula direto pro dia do "próximo palquinho" (muda a semana se precisar).
  const goToDay = (target: string) => {
    const [y, m, d] = target.split('-').map(Number)
    const date = new Date(y, m - 1, d)
    const start = new Date(date)
    start.setDate(date.getDate() - date.getDay())
    setSlideDir(iso(start) >= iso(weekStart) ? 1 : -1)
    setWeekStart(start)
    setAnimKey((k) => k + 1)
    setSelectedDayIso(target)
  }

  // Responde "você vai?" de forma otimista: o número muda na hora e o servidor
  // confirma depois. Se falhar, volta tudo — contador não pode mentir na tela.
  const sendVote = async (choice: boolean) => {
    // Não bloqueia repetir a MESMA resposta: o endpoint é idempotente e isso cura
    // o caso do localStorage velho (dia desmarcado e remarcado apaga os votos).
    if (voting) return
    if (!voterRef.current) voterRef.current = getVoter()

    const day = activeIso
    const prev = myVote
    const prevCount = votes
    const nextGoing = prevCount.going + (choice ? 1 : 0) - (prev === true ? 1 : 0)
    const nextTotal = prevCount.total + (prev === undefined ? 1 : 0)

    setVoting(true)
    setVoteError('')
    setMyVotes((m) => ({ ...m, [day]: choice }))
    setVoteCounts((c) => ({ ...c, [day]: { going: nextGoing, total: nextTotal } }))
    try {
      localStorage.setItem(VOTE_PREFIX + day, choice ? '1' : '0')
    } catch {
      // sem storage: vale só nesta aba
    }

    try {
      const res = await api.vote(day, voterRef.current, choice)
      setVoteCounts((c) => ({ ...c, [day]: { going: res.going_count, total: res.total_count } }))
    } catch {
      setMyVotes((m) => {
        const next = { ...m }
        if (prev === undefined) delete next[day]
        else next[day] = prev
        return next
      })
      setVoteCounts((c) => ({ ...c, [day]: prevCount }))
      try {
        if (prev === undefined) localStorage.removeItem(VOTE_PREFIX + day)
        else localStorage.setItem(VOTE_PREFIX + day, prev ? '1' : '0')
      } catch {
        // sem storage: nada a desfazer
      }
      setVoteError('não deu pra registrar — tenta de novo')
    } finally {
      setVoting(false)
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
            <div className="day-head">
              <p className="date-line">{fmtDay(activeIso)}</p>
              {canVote ? (
                <div className="day-poll">
                  <span className="poll-q">você vai?</span>
                  <button
                    type="button"
                    className={`poll-chip${myVote === true ? ' on yes' : ''}`}
                    onClick={() => sendVote(true)}
                    disabled={voting}
                    aria-pressed={myVote === true}
                  >
                    Sim
                  </button>
                  <button
                    type="button"
                    className={`poll-chip${myVote === false ? ' on no' : ''}`}
                    onClick={() => sendVote(false)}
                    disabled={voting}
                    aria-pressed={myVote === false}
                  >
                    Não
                  </button>
                  <span className="poll-count">{voteLabel}</span>
                </div>
              ) : !hasPalquinho && nextYes ? (
                <button
                  type="button"
                  className="day-notice"
                  onClick={() => goToDay(nextYes.day)}
                  title="ir para esse dia"
                >
                  <span className="notice-dot" aria-hidden="true" />
                  próximo palquinho: {fmtShort(nextYes.day)}
                </button>
              ) : null}
              {voteError && <span className="poll-error">{voteError}</span>}
            </div>
            {hasPalquinho ? (
              <h1 className="big-answer">
                <button
                  type="button"
                  className="big-answer-btn"
                  onClick={fireConfetti}
                  aria-label="soltar confete de novo"
                  title="clicou no SIM? mais confete"
                >
                  SIM
                </button>
              </h1>
            ) : (
              <h1 className="big-answer">{(activeIso === '2026-10-04' || activeIso === '2026-10-25') ? '13' : 'NÃO'}</h1>
            )}
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
          <button
            type="button"
            className="corner-gear"
            onClick={() => setMenuOpen(true)}
            aria-label="abrir menu"
            aria-haspopup="dialog"
            aria-expanded={menuOpen}
            title="menu"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </button>
        )}
      </div>

      {menuOpen && (
        <div className="modal-backdrop" onClick={() => setMenuOpen(false)}>
          <div
            className="menu-panel"
            role="dialog"
            aria-modal="true"
            aria-label="menu"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              className="menu-item menu-item-primary"
              autoFocus
              onClick={() => {
                setMenuOpen(false)
                setShowSuggestion(true)
              }}
            >
              quer divulgar um evento? manda aqui
            </button>
            <Link className="menu-item" to="/eventos" onClick={() => setMenuOpen(false)}>
              calendário de eventos
            </Link>
            <a
              className="menu-item menu-item-insta"
              href="https://www.instagram.com/tempalquinhohoje/"
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setMenuOpen(false)}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
                <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
                <line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
              </svg>
              @tempalquinhohoje
            </a>
            <p className="menu-note">
              O tempalquinhohoje é uma iniciativa autônoma de estudantes sem relação com organizadores e instituições da universidade!
            </p>
          </div>
        </div>
      )}

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
    </div>
  )
}
