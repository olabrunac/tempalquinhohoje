import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError, type DayOut, type EventDraft, type SuggestionOut } from './api'

// Mesmo limite do backend (schemas.MAX_EVENTS_PER_DAY) — o "+" some aqui antes
// de você chegar no 422, e o backend fecha a brecha se alguém chamar a API direto.
const MAX_EVENTS = 3

const MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
const WEEKDAYS = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb']

function iso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function fmtPt(day: string): string {
  const [y, m, d] = day.split('-').map(Number)
  return `${d} de ${MONTHS[m - 1]} de ${y}`
}

function fmtShort(day: string): string {
  const [, m, d] = day.split('-').map(Number)
  return `${d} ${MONTHS[m - 1].slice(0, 3)}`
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
  // A senha fica só na memória do React (não vai pro localStorage/sessionStorage):
  // qualquer script injetado na página não consegue ler a variável do storage.
  // Efeito colateral: ao fechar/recarregar a aba, precisa logar de novo.
  const [adminKey, setAdminKey] = useState<string>('')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const [checking, setChecking] = useState(false)

  const now = new Date()
  const [month, setMonth] = useState({ year: now.getFullYear(), month: now.getMonth() })
  const [days, setDays] = useState<DayOut[]>([])
  const [suggestions, setSuggestions] = useState<SuggestionOut[]>([])
  const [suggestionArchive, setSuggestionArchive] = useState<SuggestionOut[]>([])
  const [suggestionTab, setSuggestionTab] = useState<'pending' | 'archive'>('pending')
  const [selectedDay, setSelectedDay] = useState<string | null>(null)
  // Rascunho dos eventos do dia selecionado. Cada linha da lista é um evento
  // com nota + link próprios; o id só existe depois de salvo.
  const [eventDrafts, setEventDrafts] = useState<EventDraft[]>([])
  // Qual dos três botões está selecionado no rascunho (pra prévia refletir a cor
  // antes de salvar). null = dia ainda não marcado.
  const [draftState, setDraftState] = useState<'yes' | 'no' | 'other' | null>(null)
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState('')

  const loadData = useCallback(async (key: string) => {
    const data = await api.getDashboard(key)
    setDays(data.days)
    setSuggestions(data.pending)
    setSuggestionArchive(data.archive)
  }, [])

  useEffect(() => {
    if (!adminKey) return
    setChecking(true)
    loadData(adminKey)
      .catch((e: Error) => {
        if (e instanceof ApiError && e.status === 401) {
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
      setAdminKey(password.trim())
      setPassword('')
    } catch (err) {
      const msg = err instanceof ApiError && err.status === 401
        ? 'senha errada!'
        : err instanceof ApiError && err.status === 429
          ? 'muitas tentativas, espera alguns minutos'
          : err instanceof Error ? err.message : 'deu ruim'
      setLoginError(msg)
    } finally {
      setBusy(false)
    }
  }

  const logout = () => {
    setAdminKey('')
    setDays([])
    setSuggestions([])
    setSuggestionArchive([])
    setSelectedDay(null)
  }

  const refresh = async () => {
    await loadData(adminKey)
    setEventDrafts([])
    setSelectedDay(null)
  }

  const selectDay = (day: DayOut | undefined, key: string) => {
    setSelectedDay(key)
    setEventDrafts(
      (day?.events ?? []).map((e) => ({ note: e.note, instagram: e.instagram ?? '' }))
    )
    setDraftState(
      day ? (day.has_palquinho ? 'yes' : day.is_other_event ? 'other' : 'no') : null
    )
    setFeedback('')
  }

  

  const updateEvent = (idx: number, patch: Partial<EventDraft>) => {
    setEventDrafts((prev) => prev.map((e, i) => (i === idx ? { ...e, ...patch } : e)))
  }

  const addEvent = () => {
    setEventDrafts((prev) => (prev.length >= MAX_EVENTS ? prev : [...prev, { note: '', instagram: '' }]))
  }

  const removeEvent = (idx: number) => {
    if (!window.confirm('apagar esse evento do dia?')) return
    setEventDrafts((prev) => prev.filter((_, i) => i !== idx))
  }

  // Três botões porque são três intenções diferentes:
//   SIM                    → verde, tem palquinho
//   NÃO                    → vermelho, só pra deixar a nota do dia
//   NÃO (outro evento)     → laranja, o dia é de outro rolê
const setDay = async (has: boolean, isOther: boolean) => {
    if (!selectedDay) return
    const comNota = eventDrafts.filter((e) => e.note.trim())
    if (comNota.length > MAX_EVENTS) {
      setFeedback(`no máximo ${MAX_EVENTS} eventos por dia`)
      return
    }
    setBusy(true)
    setFeedback('')
    try {
      await api.setDay(selectedDay, has, isOther, eventDrafts, adminKey)
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
      await api.confirmSuggestion(s.id, true, s.organizer, s.instagram ?? null, adminKey)
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
      <div className="screen admin">
        <main className="mid">
          <p>carregando...</p>
        </main>
      </div>
    )
  }

  if (!adminKey) {
    return (
      <div className="screen admin">
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
              aria-label="Senha do admin"
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
  // A prévia e o painel do dia leem o rascunho, que já vem do salvo ao clicar no dia.
  const previewState: 'yes' | 'no' | 'other' = draftState ?? (selected ? 'no' : 'no')

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
            <button className="btn ghost" onClick={() => nav(-1)} aria-label="mês anterior">
              ←
            </button>
            <h2 className="calendar-title">
              {MONTHS[month.month]} {month.year}
            </h2>
            <button className="btn ghost" onClick={() => nav(1)} aria-label="próximo mês">
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
                day ? (day.has_palquinho ? 'has-yes' : day.is_other_event ? 'has-other' : 'has-no') : '',
                isToday ? 'today' : '',
                isSelected ? 'selected' : '',
              ]
                .filter(Boolean)
                .join(' ')
              return (
                <button
                  key={key}
                  className={cls}
                  onClick={() => selectDay(day, key)}
                  aria-label={`${c.getDate()} de ${MONTHS[month.month]} de ${month.year}`}
                >
                  {c.getDate()}
                </button>
              )
            })}
          </div>
          <div className="legend">
            <span className="legend-yes">SIM</span>
            <span className="legend-no">NÃO</span>
            <span className="legend-other" style={{ color: 'var(--orange)', fontWeight: 600 }}>outro rolê</span>
            <span className="legend-null">vazio</span>
          </div>

          {/* Prévia do dia selecionado: mostra como fica na página pública de eventos,
              refletindo o que está sendo digitado (rascunho), antes de salvar. */}
          <div className="panel" style={{ marginTop: '1rem' }}>
            <h3 className="panel-title">{selectedDay ? `prévia — ${fmtPt(selectedDay)}` : 'prévia do evento'}</h3>
            {!selectedDay && <p className="muted">clica num dia do calendário pra ver a prévia de como ele aparece no site.</p>}
            {selectedDay && (
              <>
                <p className="current-status" style={{ color: previewState === 'other' ? 'var(--orange)' : previewState === 'yes' ? 'var(--green)' : 'var(--red)' }}>
                  {previewState === 'yes'
                    ? 'SIMMMM tem palquinho!!!!'
                    : previewState === 'other'
                      ? 'Tem rolê confirmado!!!'
                      : 'NÃO tem palquinho'}
                </p>
                {eventDrafts.some((e) => e.note.trim()) ? (
                  <div className="preview-events">
                    {eventDrafts
                      .filter((e) => e.note.trim())
                      .map((e, idx) => {
                        const link = e.instagram?.trim()
                        return (
                          <div key={idx} className="preview-event">
                            {link ? (
                              <a href={link} target="_blank" rel="noopener noreferrer">
                                {e.note.trim()} <span aria-hidden="true">↗</span>
                              </a>
                            ) : (
                              e.note.trim()
                            )}
                          </div>
                        )
                      })}
                  </div>
                ) : (
                  <p className="muted" style={{ fontSize: '0.9rem' }}>sem nota nem link — só o dia marcado aparece.</p>
                )}
              </>
            )}
          </div>
        </section>

        <section className="panel-col">
          <div className="panel">
            <h3 className="panel-title">{selectedDay ? fmtPt(selectedDay) : 'clica num dia'}</h3>
            {!selectedDay && <p className="muted">clica num dia do calendário pra marcar que tem palquinho (ou remover).</p>}
            {selectedDay && (
              <>
                <p className="current-status" style={{ color: previewState === 'other' ? 'var(--orange)' : previewState === 'yes' ? 'var(--green)' : 'var(--red)' }}>
                  {previewState === 'yes'
                    ? 'marcado: palquinho SIM'
                    : previewState === 'other'
                      ? 'marcado: NÃO (outro rolê, laranja)'
                      : selected
                        ? 'marcado: NÃO (vermelho)'
                        : 'ainda não marcado'}
                </p>

                <div className="event-editor">
                  {eventDrafts.map((ev, idx) => (
                    <div key={idx} className="event-row">
                      <div className="event-row-head">
                        <span className="event-row-num">{idx + 1}</span>
                        <button
                          className="btn ghost small danger"
                          onClick={() => removeEvent(idx)}
                          disabled={busy}
                          title="apagar esse evento"
                          aria-label={`Apagar evento ${idx + 1}`}
                        >
                          ✕
                        </button>
                      </div>
                      <input
                        className="input"
                        type="text"
                        placeholder="ex.: 14:00 - Churrasco da Bateria"
                        value={ev.note}
                        onChange={(e) => updateEvent(idx, { note: e.target.value })}
                        maxLength={2000}
                        aria-label={`Nota do evento ${idx + 1}`}
                      />
                      <input
                        className="input"
                        type="text"
                        placeholder="link do instagram desse evento (opcional)"
                        value={ev.instagram ?? ''}
                        onChange={(e) => updateEvent(idx, { instagram: e.target.value })}
                        maxLength={300}
                        aria-label={`Instagram do evento ${idx + 1}`}
                      />
                    </div>
                  ))}
                  <button className="btn ghost" onClick={addEvent} disabled={busy || eventDrafts.length >= MAX_EVENTS}>
                    + adicionar evento
                  </button>
                  {eventDrafts.length >= MAX_EVENTS && (
                    <p className="muted" style={{ fontSize: '0.78rem' }}>
                      máximo de {MAX_EVENTS} eventos por dia
                    </p>
                  )}
                </div>

                <div className="panel-actions" style={{ flexDirection: 'column', gap: '0.5rem' }}>
                  <button className="btn yes-btn" onClick={() => setDay(true, false)} disabled={busy}>
                    marcar SIM
                  </button>
                  <div style={{ display: 'flex', gap: '0.75rem', width: '100%' }}>
                    <button className="btn no-btn" onClick={() => setDay(false, false)} disabled={busy}>
                      marcar NÃO
                    </button>
                    <button
                      className="btn other-btn"
                      onClick={() => setDay(false, true)}
                      disabled={busy}
                      title="não tem palquinho, mas o dia é de outro rolê (laranja)"
                    >
                      NÃO (outro rolê)
                    </button>
                  </div>
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
            <div className="panel-head">
              <h3 className="panel-title">sugestões</h3>
              <div className="seg">
                <button
                  className={`seg-btn ${suggestionTab === 'pending' ? 'active' : ''}`}
                  onClick={() => setSuggestionTab('pending')}
                >
                  pendentes ({suggestions.length})
                </button>
                <button
                  className={`seg-btn ${suggestionTab === 'archive' ? 'active' : ''}`}
                  onClick={() => setSuggestionTab('archive')}
                >
                  arquivo ({suggestionArchive.length})
                </button>
              </div>
            </div>
            {suggestionTab === 'pending' ? (
              suggestions.length === 0 ? (
                <p className="muted">nenhuma sugestão pendente.</p>
              ) : (
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
              )
            ) : suggestionArchive.length === 0 ? (
              <p className="muted">nada arquivado ainda.</p>
            ) : (
              <ul className="suggestions">
                {suggestionArchive.map((s) => (
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
                      <span className={`suggestion-badge ${s.action === 'confirm' ? 'confirmed' : 'dismissed'}`}>
                        {s.action === 'confirm' ? '✓ confirmada' : '✗ descartada'}
                        {s.solved_at ? ` · ${fmtShort(s.solved_at.slice(0, 10))}` : ''}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}