import { useCallback, useEffect, useRef, useState } from 'react'
import { toPng } from 'html-to-image'
import ShareCard, { buildWeek, type ShareEvent, type ShareState } from './ShareCard'

interface ShareModalProps {
  day: string
  state: ShareState
  events: ShareEvent[]
  stateOf: (day: string) => ShareState
  onClose: () => void
}

// Exporta o cartão como PNG. O cartão é desenhado em 360px (feed) e 300px
// (stories) de largura; o pixelRatio leva pro tamanho final de 1080px.
const PIXEL_RATIO: Record<'feed' | 'story', number> = { feed: 3, story: 3.6 }

function dataUrlToBlob(dataUrl: string): Blob {
  const [meta, b64] = dataUrl.split(',')
  const mime = meta.match(/:(.*?);/)?.[1] || 'image/png'
  const byteChars = atob(b64)
  const byteNumbers = new Array(byteChars.length)
  for (let i = 0; i < byteChars.length; i++) {
    byteNumbers[i] = byteChars.charCodeAt(i)
  }
  const byteArray = new Uint8Array(byteNumbers)
  return new Blob([byteArray], { type: mime })
}

function buildShareText(day: string, state: ShareState, events: ShareEvent[]): string {
  const d = new Date(day + 'T12:00:00')
  const datePt = d.toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })
  const big = state === 'yes' ? 'SIM' : state === 'other' ? 'outro rolê' : 'NÃO'
  const notes = events
    .map((e) => e.note.trim())
    .filter(Boolean)
    .join(' · ')
  const base = `tem palquinho hoje? — ${datePt}: ${big}`
  if (notes) return `${base}\n${notes}\n\nVeja em tempalquinhohoje.com`
  return `${base}\nVeja em tempalquinhohoje.com`
}

export default function ShareModal({ day, state, events, stateOf, onClose }: ShareModalProps) {
  const feedRef = useRef<HTMLDivElement>(null)
  const storyRef = useRef<HTMLDivElement>(null)
  const [busy, setBusy] = useState<'feed' | 'story' | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const week = buildWeek(day, state, stateOf)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const download = useCallback(
    async (variant: 'feed' | 'story') => {
      const node = variant === 'feed' ? feedRef.current : storyRef.current
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

  const shareImageNative = useCallback(
    async (variant: 'feed' | 'story') => {
      const node = variant === 'feed' ? feedRef.current : storyRef.current
      if (!node) return
      setBusy(variant)
      setError('')
      try {
        const dataUrl = await toPng(node, { pixelRatio: PIXEL_RATIO[variant], cacheBust: true })
        const blob = dataUrlToBlob(dataUrl)
        const file = new File([blob], `palquinho-${day}-${variant}.png`, { type: 'image/png' })
        const url = new URL(window.location.href)
        const shareData: ShareData = {
          title: 'tem palquinho hoje?',
          text: buildShareText(day, state, events),
          url: `${url.origin}/?dia=${day}`,
          files: [file],
        }
        if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
          await navigator.share(shareData)
        } else {
          const a = document.createElement('a')
          a.href = dataUrl
          a.download = file.name
          a.click()
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'não deu pra gerar a imagem')
      } finally {
        setBusy(null)
      }
    },
    [day, state, events],
  )

  const shareLink = useCallback(async () => {
    const url = new URL(window.location.href)
    const shareData: ShareData = {
      title: 'tem palquinho hoje?',
      text: buildShareText(day, state, events),
      url: `${url.origin}/?dia=${day}`,
    }
    if (navigator.share) {
      try {
        await navigator.share(shareData)
      } catch (e) {
        // ignore
      }
      return
    }
    // fallback: copy to clipboard
    try {
      await navigator.clipboard.writeText(shareData.text + '\n' + shareData.url)
      setNotice('link copiado para a área de transferência')
      setTimeout(() => setNotice(''), 1200)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'não deu pra copiar o link')
    }
  }, [day, state, events])

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
            compartilhar dia
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
        <p className="modal-sub">é assim que a imagem fica. compartilha, baixa ou manda o link.</p>

        <div className="share-modal-body">
          <div className="share-item">
            <div ref={feedRef}>
              <ShareCard variant="feed" day={day} state={state} events={events} week={week} />
            </div>
            <span className="share-caption">feed · 1080 × 1080</span>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
              <button className="btn primary-btn" onClick={() => shareImageNative('feed')} disabled={busy !== null}>
                {busy === 'feed' ? 'gerando...' : 'compartilhar imagem (feed)'}
              </button>
              <button className="btn ghost" onClick={() => download('feed')} disabled={busy !== null}>
                baixar feed
              </button>
            </div>
          </div>

          <div className="share-item">
            <div ref={storyRef}>
              <ShareCard variant="story" day={day} state={state} events={events} week={week} />
            </div>
            <span className="share-caption">stories · 1080 × 1920</span>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
              <button className="btn primary-btn" onClick={() => shareImageNative('story')} disabled={busy !== null}>
                {busy === 'story' ? 'gerando...' : 'compartilhar imagem (stories)'}
              </button>
              <button className="btn ghost" onClick={() => download('story')} disabled={busy !== null}>
                baixar stories
              </button>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', justifyContent: 'center', flexWrap: 'wrap' }}>
          <button className="btn primary-btn" onClick={shareLink} disabled={busy !== null}>
            compartilhar link do dia
          </button>
          <button className="btn ghost" onClick={downloadBoth} disabled={busy !== null}>
            baixar os dois
          </button>
        </div>

        {error && <p className="error">{error}</p>}
        {notice && <p className="modal-sub">{notice}</p>}
      </div>
    </div>
  )
}
