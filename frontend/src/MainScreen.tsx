import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type TodayOut } from './api'
import SuggestionModal from './SuggestionModal'

const WEEKDAYS = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado']
const MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

function fmtDay(day: string): string {
  const [y, m, d] = day.split('-').map(Number)
  return `${WEEKDAYS[new Date(y, m - 1, d).getDay()]}, ${d} de ${MONTHS[m - 1]} de ${y}`
}

export default function MainScreen() {
  const [today, setToday] = useState<TodayOut | null>(null)
  const [error, setError] = useState('')
  const [showSuggestion, setShowSuggestion] = useState(false)
  const [thankYou, setThankYou] = useState(false)

  useEffect(() => {
    api
      .getToday()
      .then(setToday)
      .catch((e: Error) => setError(e.message))
  }, [])

  const hasPalquinho = today?.has_palquinho ?? false
  const loading = !today && !error

  return (
    <div className={`screen ${hasPalquinho ? 'yes' : 'no'}`}>
      <header className="topbar">
        {today ? <span className="date-line">{fmtDay(today.day)}</span> : <span />}
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
          {!loading && (
            <>
              <h1 className="big-answer">{hasPalquinho ? 'SIM' : 'NÃO'}</h1>
              {today?.note && <p className="note">{today.note}</p>}
            </>
          )}
        </main>
      )}

      {thankYou ? (
        <div className="corner-thanks">mandado! o admin vai confirmar 🎉</div>
      ) : (
        <button className="corner-suggest" onClick={() => setShowSuggestion(true)}>
          sabe de algum palquinho? ✨
        </button>
      )}

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