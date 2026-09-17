import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError, type DayOut, type SuggestionOut } from './api'

const MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
const WEEKDAYS = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb']
const ADMIN_KEY = 'tph_admin_key'

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

export default function AdminScreen() {
  const [adminKey, setAdminKey] = useState<string>(() => localStorage.getItem(ADMIN_KEY) ?? '')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const [checking, setChecking] = useState(!!localStorage.getItem(ADMIN_KEY))

  const now = new Date()
  const [month, setMonth] = useState({ year: now.getFullYear(), month: now.getMonth() })
  const [days, setDays] = useState<DayOut[]>([])
  const [suggestions, setSuggestions] = useState<SuggestionOut[]>([])
  const [selectedDay, setSelectedDay] = useState<string | null>(null)
  const [noteDraft, setNoteDraft] = useState('')
  const [instagramDraft, setInstagramDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState('')

  const loadData = useCallback(async (key: string) => {
    const [dayRows, sugRows] = await Promise.all([api.getDays(), api.getSuggestions(key)])
    setDays(dayRows)
    setSuggestions(sugRows)
  }, [])

  useEffect(() => {
    if (!adminKey) return
    setChecking(true)
    loadData(adminKey)
      .catch((e: Error) => {
        if (e instanceof ApiError && e.status === 401) {
          localStorage.removeItem(ADMIN_KEY)
          setAdminKey('')
        }
      })
      .finally(() => setChecking(false))
  }, [adminKey, loadData])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!password.trim()) return
    setLoginError('')
    setBusy(true)
    try {
      await loadData(password.trim())
      localStorage.setItem(ADMIN_KEY, password.trim())
      setAdminKey(password.trim())
      setPassword('')
    } catch (err) {
      setLoginError(err instanceof ApiError && err.status === 401 ? 'senha errada, hein amigo!' : err instanceof Error ? err.message : 'deu ruim')
    } finally {
      setBusy(false)
    }
  }

  const logout = () => {
    localStorage.removeItem(ADMIN_KEY)
    setAdminKey('')
    setDays([])
    setSuggestions([])
    setSelectedDay(null)
  }

  const refresh = async () => {
    await loadData(adminKey)
    setNoteDraft('')
    setInstagramDraft('')
    setSelectedDay(null)
  }

  const setDay = async (has: boolean) => {
    if (!selectedDay) return
    setBusy(true)
    setFeedback('')
    try {
      await api.setDay(selectedDay, has, noteDraft.trim() || null, instagramDraft.trim() || null, adminKey)
      await refresh()
    } catch (e) {
      setFeedback(e instanceof Error ? e.message : 'deu ruim')
    } finally {
      setBusy(false)
    }
  }

  const removeDay = async () => {
    if (!selectedDay) return
    setBusy(true)
    setFeedback('')
    try {
      await api.unsetDay(selectedDay, adminKey)
      await refresh()
    } catch (e) {
      setFeedback(e instanceof Error ? e.message : 'deu ruim')
    } finally {
      setBusy(false)
    }
  }

  const confirmSuggestion = async (s: SuggestionOut) => {
    setBusy(true)
    setFeedback('')
    try {
      await api.confirmSuggestion(s.id, true, s.instagram ?? null, adminKey)
      await refresh()
    } catch (e) {
      setFeedback(e instanceof Error ? e.message : 'deu ruim')
    } finally {
      setBusy(false)
    }
  }

  const dismissSuggestion = async (id: number) => {
    setBusy(true)
    setFeedback('')
    try {
      await api.dismissSuggestion(id, adminKey)
      await refresh()
    } catch (e) {
      setFeedback(e instanceof Error ? e.message : 'deu ruim')
    } finally {
      setBusy(false)
    }
  }

  if (checking) {
    return (
      <div className="screen">
        <main className="mid">
          <p>carregando...</p>
        </main>
      </div>
    )
  }

  if (!adminKey) {
    return (
      <div className="screen">
        <header className="topbar">
          <Link className="admin-link" to="/">
            voltar
          </Link>
        </header>
        <main className="mid">
          <form className="login-card" onSubmit={handleLogin}>
            <h1 className="login-title">área admin</h1>
            <input
              className="input"
              type="password"
              placeholder="senha do admin"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
            />
            {loginError && <p className="error">{loginError}</p>}
            <button className="btn primary-btn" type="submit" disabled={busy}>
              entrar
            </button>
          </form>
        </main>
      </div>
    )
  }

  const dayMap = new Map(days.map((d) => [d.day, d]))
  const cells = buildCells(month.year, month.month)
  const selected = selectedDay ? dayMap.get(selectedDay) : undefined
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
          ← site
        </Link>
        <button className="admin-link logout" onClick={logout}>
          sair
        </button>
      </header>

      <main className="admin-body">
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
              const isSelected = key === selectedDay
              const cls = [
                'cal-cell',
                day ? 'has-yes' : '',
                isToday ? 'today' : '',
                isSelected ? 'selected' : '',
              ]
                .filter(Boolean)
                .join(' ')
              return (
                <button
                  key={key}
                  className={cls}
                  onClick={() => {
                    setSelectedDay(key)
                    setNoteDraft(day?.note ?? '')
                    setInstagramDraft(day?.instagram ?? '')
                    setFeedback('')
                  }}
                >
                  {c.getDate()}
                </button>
              )
            })}
          </div>
          <div className="legend">
            <span className="legend-yes">SIM marcado</span>
            <span className="legend-null">não marcado</span>
          </div>
        </section>

        <section className="panel-col">
          <div className="panel">
            <h3 className="panel-title">{selectedDay ? fmtPt(selectedDay) : 'clica num dia'}</h3>
            {!selectedDay && <p className="muted">clica num dia do calendário pra marcar que tem palquinho (ou remover).</p>}
            {selectedDay && (
              <>
                <p className="current-status">
                  {selected ? 'marcado: palquinho SIM 🎉' : 'ainda não marcado'}
                </p>
                <textarea
                  className="textarea"
                  placeholder="nota (opcional) — ex.: 'na casa do Bruno'"
                  value={noteDraft}
                  onChange={(e) => setNoteDraft(e.target.value)}
                  rows={2}
                />
                <input
                  className="input"
                  type="text"
                  placeholder="link do instagram do anúncio (opcional)"
                  value={instagramDraft}
                  onChange={(e) => setInstagramDraft(e.target.value)}
                  maxLength={300}
                />
                <div className="panel-actions">
                  <button className="btn yes-btn" onClick={() => setDay(true)} disabled={busy}>
                    marcar SIM
                  </button>
                </div>
                {selected && (
                  <button className="btn ghost danger" onClick={removeDay} disabled={busy}>
                    remover marcação
                  </button>
                )}
              </>
            )}
            {feedback && <p className="error">{feedback}</p>}
          </div>

          <div className="panel">
            <h3 className="panel-title">sugestões dos amigos ({suggestions.length})</h3>
            {suggestions.length === 0 && <p className="muted">nenhuma sugestão pendente. </p>}
            <ul className="suggestions">
              {suggestions.map((s) => (
                <li key={s.id} className="suggestion">
                  <div className="suggestion-info">
                    <span className="suggestion-day">{fmtPt(s.day)}</span>
                    <span className="suggestion-organizer">organiza: {s.organizer}</span>
                    {s.instagram && (
                      <a
                        className="suggestion-instagram"
                        href={s.instagram}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        ver anúncio no instagram ↗
                      </a>
                    )}
                  </div>
                  <div className="suggestion-actions">
                    <button className="btn yes-btn small" onClick={() => confirmSuggestion(s)} disabled={busy}>
                      confirmar SIM
                    </button>
                    <button className="btn ghost small" onClick={() => dismissSuggestion(s.id)} disabled={busy}>
                      descartar
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </main>
    </div>
  )
}