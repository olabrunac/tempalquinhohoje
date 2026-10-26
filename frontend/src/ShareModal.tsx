import { useCallback, useEffect, useRef, useState } from 'react'
import { toPng } from 'html-to-image'
import ShareCard, { buildWeek, ShareWeekCard, type ShareEvent, type ShareState } from './ShareCard'

interface ShareModalProps {
  day: string
  state: ShareState
  events: ShareEvent[]
  notes: string[]
  stateOf: (day: string) => ShareState
  notesOf: (day: string) => string[]
  onClose: () => void
}

type Variant = 'week' | 'feed' | 'story'

// Exporta o cartão como PNG. O cartão é desenhado em 360px (feed/semana) e 300px
// (stories) de largura; o pixelRatio leva pro tamanho final de 1080px.
const PIXEL_RATIO: Record<Variant, number> = { week: 3, feed: 3, story: 3.6 }

export default function ShareModal({ day, state, events, notes, stateOf, notesOf, onClose }: ShareModalProps) {
  const weekRef = useRef<HTMLDivElement>(null)
  const feedRef = useRef<HTMLDivElement>(null)
  const storyRef = useRef<HTMLDivElement>(null)
  const [busy, setBusy] = useState<Variant | null>(null)
  const [error, setError] = useState('')

  const week = buildWeek(day, state, notes, stateOf, notesOf)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const download = useCallback(
    async (variant: Variant) => {
      const node = variant === 'week' ? weekRef.current : variant === 'feed' ? feedRef.current : storyRef.current
      if (!node) return
      setBusy(variant)
      setError('')
      try {
        const dataUrl = await toPng(node, { pixelRatio: PIXEL_RATIO[variant], cacheBust: true })
        const a = document.createElement('a')
        a.href = dataUrl
        a.download = `palquinho-${day}-${variant}.png`
        a.click()
      } catch (e) {
        setError(e instanceof Error ? e.message : 'não deu pra gerar a imagem')
      } finally {
        setBusy(null)
      }
    },
    [day],
  )

  const downloadBoth = async () => {
    await download('feed')
    await download('story')
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal modal-wide"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="share-title"
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <h2 id="share-title" className="modal-title">
            compartilhar
          </h2>
          <button
            type="button"
            className="btn ghost small"
            onClick={onClose}
            aria-label="Fechar modal"
            style={{ padding: '0.2rem 0.5rem', fontSize: '1.2rem', lineHeight: 1 }}
          >
            ✕
          </button>
        </div>
        <p className="modal-sub">é assim que a imagem fica. baixa no tamanho que quiser e posta.</p>

        <div className="share-modal-body">
          <div className="share-item">
            <div ref={weekRef}>
              <ShareWeekCard week={week} />
            </div>
            <span className="share-caption">semana · feed 1080 × 1350</span>
            <button className="btn primary-btn" onClick={() => download('week')} disabled={busy !== null}>
              {busy === 'week' ? 'gerando...' : 'baixar semana'}
            </button>
          </div>

          <div className="share-item">
            <div ref={feedRef}>
              <ShareCard variant="feed" day={day} state={state} events={events} week={week} />
            </div>
            <span className="share-caption">feed · 1080 × 1350</span>
            <button className="btn primary-btn" onClick={() => download('feed')} disabled={busy !== null}>
              {busy === 'feed' ? 'gerando...' : 'baixar feed'}
            </button>
          </div>

          <div className="share-item">
            <div ref={storyRef}>
              <ShareCard variant="story" day={day} state={state} events={events} week={week} />
            </div>
            <span className="share-caption">stories · 1080 × 1920</span>
            <button className="btn primary-btn" onClick={() => download('story')} disabled={busy !== null}>
              {busy === 'story' ? 'gerando...' : 'baixar stories'}
            </button>
          </div>
        </div>

        {error && <p className="error">{error}</p>}

        <div className="modal-actions">
          <button className="btn ghost" onClick={downloadBoth} disabled={busy !== null}>
            baixar os dois
          </button>
        </div>
      </div>
    </div>
  )
}
