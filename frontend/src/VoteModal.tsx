import { useState } from 'react'
import { api } from './api'

interface Props {
  day: string
  onClose: () => void
  onVoted: () => void
}

export default function VoteModal({ day, onClose, onVoted }: Props) {
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)

  const submit = async (vote: boolean) => {
    if (!name.trim()) {
      setError('diz o teu nome primeiro, chefia!')
      return
    }
    setSending(true)
    setError('')
    try {
      await api.vote({ day, name: name.trim(), vote })
      onVoted()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'deu ruim')
      setSending(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">e aí, tem palquinho?</h2>
        <p className="modal-sub">deixa teu palpite</p>
        <input
          className="input"
          type="text"
          placeholder="teu nome"
          maxLength={40}
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={sending}
          autoFocus
        />
        {error && <p className="error">{error}</p>}
        <div className="modal-actions">
          <button className="btn yes-btn" onClick={() => submit(true)} disabled={sending}>
            SIM 🎉
          </button>
          <button className="btn no-btn" onClick={() => submit(false)} disabled={sending}>
            NÃO 😴
          </button>
        </div>
        <button className="btn ghost modal-close" onClick={onClose} disabled={sending}>
          cancelar
        </button>
      </div>
    </div>
  )
}