import { useState } from 'react'
import { api } from './api'

interface Props {
  onClose: () => void
  onSent: () => void
}

const MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
const WEEKDAYS_FULL = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado']
const WEEKDAYS_SHORT = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb']

function iso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function buildCells(year: number, month: number): (Date | null)[] {
  const first = new Date(year, month, 1)
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells: (Date | null)[] = []
  for (let i = 0; i < first.getDay(); i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d))
  return cells
}

function fmtDay(day: string): string {
  const [y, m, d] = day.split('-').map(Number)
  return `${WEEKDAYS_FULL[new Date(y, m - 1, d).getDay()]}, ${d} de ${MONTHS[m - 1]}`
}

export default function SuggestionModal({ onClose, onSent }: Props) {
  const now = new Date()
  const todayIso = iso(now)
  const minView = new Date(now.getFullYear(), now.getMonth(), 1)

  const [day, setDay] = useState(todayIso)
  const [view, setView] = useState({ year: now.getFullYear(), month: now.getMonth() })
  const [organizer, setOrganizer] = useState('')
  const [instagram, setInstagram] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)

  const nav = (delta: number) => {
    const next = new Date(view.year, view.month + delta, 1)
    if (next < minView) return
    setView({ year: next.getFullYear(), month: next.getMonth() })
  }

  const submit = async () => {
    setError('')
    if (!day) {
      setError('escolhe o dia!')
      return
    }
    if (!organizer.trim()) {
      setError('diz quem tu acha que organiza!')
      return
    }
    setSending(true)
    try {
      await api.suggest({ day, organizer: organizer.trim(), instagram: instagram.trim() || null })
      onSent()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'deu ruim')
      setSending(false)
    }
  }

  const cells = buildCells(view.year, view.month)

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">envie sua sugestão de rolê!</h2>
        <p className="modal-sub">mande aqui as infos do palquinho/evento que iremos confirmar e publicar</p>

        <div className="mini-cal">
          <div className="mini-cal-nav">
            <button type="button" className="btn ghost" onClick={() => nav(-1)} disabled={sending} aria-label="mês anterior">
              ‹
            </button>
            <span className="mini-cal-title">
              {MONTHS[view.month]} {view.year}
            </span>
            <button type="button" className="btn ghost" onClick={() => nav(1)} disabled={sending} aria-label="próximo mês">
              ›
            </button>
          </div>
          <div className="mini-cal-grid">
            {WEEKDAYS_SHORT.map((w) => (
              <div key={w} className="mini-cal-weekday">
                {w}
              </div>
            ))}
            {cells.map((c, i) => {
              if (!c) return <div key={i} className="mini-cal-empty" />
              const key = iso(c)
              const isPast = key < todayIso
              const isSelected = key === day
              const cls = [
                'mini-cal-cell',
                isPast ? 'past' : '',
                key === todayIso ? 'today' : '',
                isSelected ? 'selected' : '',
              ]
                .filter(Boolean)
                .join(' ')
              return (
                <button
                  type="button"
                  key={key}
                  className={cls}
                  disabled={isPast}
                  onClick={() => setDay(key)}
                >
                  {c.getDate()}
                </button>
              )
            })}
          </div>
        </div>
        {day && <p className="mini-cal-date">data: {fmtDay(day)}</p>}

        <input
          className="input"
          type="text"
          placeholder="organizador(a)"
          maxLength={80}
          value={organizer}
          onChange={(e) => setOrganizer(e.target.value)}
          disabled={sending}
          autoFocus
        />
        <input
          className="input"
          type="text"
          placeholder="link do instagram do anúncio (opcional)"
          maxLength={300}
          value={instagram}
          onChange={(e) => setInstagram(e.target.value)}
          disabled={sending}
        />
        {error && <p className="error">{error}</p>}
        <div className="modal-actions">
          <button className="btn yes-btn" onClick={submit} disabled={sending}>
            enviar
          </button>
          <button className="btn no-btn" onClick={onClose} disabled={sending}>
            cancelar
          </button>
        </div>
      </div>
    </div>
  )
}