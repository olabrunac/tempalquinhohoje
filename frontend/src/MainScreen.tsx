import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type TodayOut } from './api'
import VoteModal from './VoteModal'

const WEEKDAYS = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado']
const MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

function fmtDay(day: string): string {
  const [y, m, d] = day.split('-').map(Number)
  return `${WEEKDAYS[new Date(y, m - 1, d).getDay()]}, ${d} de ${MONTHS[m - 1]} de ${y}`
}

export default function MainScreen() {
  const [today, setToday] = useState<TodayOut | null>(null)
  const [error, setError] = useState('')
  const [showVote, setShowVote] = useState(false)
  const [voted, setVoted] = useState(false)

  useEffect(() => {
    api
      .getToday()
      .then(setToday)
      .catch((e: Error) => setError(e.message))
  }, [])

  const has = today?.has_palquinho ?? null
  const statusClass = has === null ? 'unknown' : has ? 'yes' : 'no'
  const big = has === null ? '?' : has ? 'SIM' : 'NÃO'

  return (
    <div className={`screen ${statusClass}`}>
      <header className="topbar">
        <span className="date-line">
          {today ? fmtDay(today.day) : 'carregando...'}
        </span>
        <Link className="admin-link" to="/admin">
          admin
        </Link>
      </header>

      {error ? (
        <main className="mid">
          <p className="error">Deu ruim: {error}</p>
        </main>
      ) : (
        <main className="mid">
          <h1 className="big-answer">{big}</h1>

          {has === null && (
            <div className="unset-box">
              <p className="unset-text">
                hoje <strong>ainda não foi marcado</strong>.
              </p>
              {voted ? (
                <p className="unset-text ok">voto enviado, valeu! 🎉</p>
              ) : (
                <button className="btn vote-btn" onClick={() => setShowVote(true)}>
                  acho que sim — votar
                </button>
              )}
            </div>
          )}

          {today?.note && <p className="note">{today.note}</p>}
        </main>
      )}

      {showVote && today && (
        <VoteModal
          day={today.day}
          onClose={() => setShowVote(false)}
          onVoted={() => {
            setShowVote(false)
            setVoted(true)
          }}
        />
      )}
    </div>
  )
}