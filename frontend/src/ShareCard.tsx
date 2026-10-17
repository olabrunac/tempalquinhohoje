import { useMemo } from 'react'

// Estado visual de um dia no cartão: verde (SIM), laranja (outro rolê) ou
// vermelho (NÃO / sem marcação). Casa com o que a tela pública mostra.
export type ShareState = 'yes' | 'no' | 'other'

export interface ShareEvent {
  note: string
  instagram?: string | null
}

export interface ShareWeekDay {
  day: string
  num: number
  dow: string
  state: ShareState
  viewing: boolean
  notes: string[]
}

const MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
const WEEKDAYS = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb']
const WEEKDAYS_FULL = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado']

// Mesma paleta do confete da tela principal (canvas-confetti).
const COLORS = ['#ef4444', '#f97316', '#facc15', '#22c55e', '#3b82f6', '#6366f1', '#8b5cf6', '#ec4899']

function isoLocal(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function fmtPtFull(day: string): string {
  const [y, m, d] = day.split('-').map(Number)
  const wd = new Date(y, m - 1, d).getDay()
  return `${WEEKDAYS_FULL[wd]}, ${d} de ${MONTHS[m - 1]} de ${y}`
}

// Extrai "@alguem" de um link do Instagram. Aceita link completo, "@alguem"
// ou só "alguem". Sem info útil, devolve null.
export function instaHandle(url?: string | null): string | null {
  if (!url) return null
  const t = url.trim()
  if (!t) return null
  const m = t.match(/instagram\.com\/([^/?#\s]+)/i)
  let u = m ? m[1] : t.replace(/^@/, '').split(/[/?#\s]/)[0]
  u = u.replace(/\/+$/, '')
  if (!u || u === 'p' || u === 'reel') return null
  return '@' + u
}

// Monta a semana (domingo→sábado) que contém o dia compartilhado. Dias sem
// marcação aparecem como "no" (mesmo default da tela principal). O dia central
// usa o estado/notas que estão na tela (rascunho); os outros vêm do salvo.
export function buildWeek(
  centerDay: string,
  centerState: ShareState,
  centerNotes: string[],
  stateOf: (day: string) => ShareState,
  notesOf: (day: string) => string[],
): ShareWeekDay[] {
  const [y, m, d] = centerDay.split('-').map(Number)
  const center = new Date(y, m - 1, d)
  const sunday = new Date(y, m - 1, d - center.getDay())
  const out: ShareWeekDay[] = []
  for (let i = 0; i < 7; i++) {
    const dt = new Date(sunday.getFullYear(), sunday.getMonth(), sunday.getDate() + i)
    const key = isoLocal(dt)
    const viewing = key === centerDay
    out.push({
      day: key,
      num: dt.getDate(),
      dow: WEEKDAYS[dt.getDay()],
      state: viewing ? centerState : stateOf(key),
      viewing,
      notes: viewing ? centerNotes : notesOf(key),
    })
  }
  return out
}

// "Calendário da semana: 12 a 18 de outubro" (ou, virando o mês, com os dois meses).
export function fmtWeekRange(week: ShareWeekDay[]): string {
  const [, m1, d1] = week[0].day.split('-').map(Number)
  const [, m2, d2] = week[week.length - 1].day.split('-').map(Number)
  const core = m1 === m2 ? `${d1} a ${d2} de ${MONTHS[m1 - 1]}` : `${d1} de ${MONTHS[m1 - 1]} a ${d2} de ${MONTHS[m2 - 1]}`
  return `Calendário da semana: ${core}`
}

function Confetti() {
  const pieces = useMemo(() => {
    let seed = 7
    const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280
    return Array.from({ length: 90 }, () => ({
      color: COLORS[Math.floor(rnd() * COLORS.length)],
      x: rnd() * 100,
      y: rnd() * 100,
      w: 6 + rnd() * 6,
      h: 11 + rnd() * 9,
      r: Math.round(rnd() * 360),
      o: 0.5 + rnd() * 0.3,
    }))
  }, [])

  return (
    <div className="sc-confetti" aria-hidden="true">
      {pieces.map((p, i) => (
        <i
          key={i}
          style={{
            left: `${p.x.toFixed(2)}%`,
            top: `${p.y.toFixed(2)}%`,
            width: `${p.w.toFixed(1)}px`,
            height: `${p.h.toFixed(1)}px`,
            background: p.color,
            transform: `rotate(${p.r}deg)`,
            opacity: p.o.toFixed(2),
          }}
        />
      ))}
    </div>
  )
}

interface ShareCardProps {
  variant: 'feed' | 'story'
  day: string
  state: ShareState
  events: ShareEvent[]
  week: ShareWeekDay[]
}

// Cartão para compartilhar. Renderizado on/off-screen e exportado como PNG
// (html-to-image) no ShareModal. Roda em dev/preview; não vai pro site público.
export default function ShareCard({ variant, day, state, events, week }: ShareCardProps) {
  const notes = events.map((e) => e.note.trim()).filter(Boolean)
  const handles = Array.from(new Set(events.map((e) => instaHandle(e.instagram)).filter(Boolean))) as string[]
  const bigLabel = state === 'yes' ? 'SIM' : 'NÃO'

  return (
    <div className={`sc-card sc-${variant}`}>
      {state === 'yes' && <Confetti />}
      <div className="sc-top">
        <span className="sc-date">{fmtPtFull(day)}</span>
      </div>
      <div className="sc-content">
        <div className={`sc-big sc-${state}`}>{bigLabel}</div>
        {notes.length > 0 && <div className="sc-note">{notes.join('\n')}</div>}
        {handles.length > 0 && <div className="sc-handle">{handles.join(' · ')}</div>}
      </div>
      <div className="sc-bottom">
        <div className="sc-week">
          {week.map((d) => (
            <div key={d.day} className={`sc-day sc-${d.state}${d.viewing ? ' sc-viewing' : ''}`}>
              <span className="sc-dow">{d.dow}</span>
              <span className="sc-num">{d.num}</span>
            </div>
          ))}
        </div>
        <div className="sc-footer">tempalquinhohoje.com · @tempalquinhohoje</div>
      </div>
    </div>
  )
}

interface ShareWeekCardProps {
  week: ShareWeekDay[]
}

// Cartão da semana (feed): lista vertical dos dias, cada um com seu quadrado
// colorido e a(s) nota(s) do dia ao lado. Mesmo fundo preto e tipografia do card
// do dia. Renderizado on/off-screen e exportado como PNG no ShareModal.
export function ShareWeekCard({ week }: ShareWeekCardProps) {
  return (
    <div className="sc-card sc-feed sc-weekcard">
      <div className="sc-top">
        <span className="sc-date">{fmtWeekRange(week)}</span>
      </div>
      <div className="sc-week-list">
        {week.map((d) => (
          <div key={d.day} className="sc-wrow">
            <div className={`sc-wsq sc-${d.state}`}>
              <span className="sc-dow">{d.dow}</span>
              <span className="sc-num">{d.num}</span>
            </div>
            {d.notes.length > 0 && d.state !== 'no' && (
              <div className="sc-wnotes">
                {d.notes.map((n, i) => (
                  <span key={i} className="sc-wnote">
                    {n}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="sc-footer">tempalquinhohoje.com · @tempalquinhohoje</div>
    </div>
  )
}
