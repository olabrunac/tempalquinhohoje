import { useState } from 'react'
import { api } from './api'

interface Props {
  onClose: () => void
  onSent: () => void
}

function todayIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function SuggestionModal({ onClose, onSent }: Props) {
  const [day, setDay] = useState(todayIso())
  const [organizer, setOrganizer] = useState('')
  const [instagram, setInstagram] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)

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

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">sabe de algum palquinho?</h2>
        <p className="modal-sub">manda a data e quem ta organizando o rolê, bota o insta do post anunciando tbm pra gente confirmar certinho</p>
        <input
          className="input"
          type="date"
          value={day}
          onChange={(e) => setDay(e.target.value)}
          disabled={sending}
        />
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