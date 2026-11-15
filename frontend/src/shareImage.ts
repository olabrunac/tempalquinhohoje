import { toSvg } from 'html-to-image'

// Prefixo do data URL que o html-to-image devolve em `toSvg`.
const SVG_PREFIX = 'data:image/svg+xml;charset=utf-8,'
const ATTR = 'data-font-exata'

// Ao clonar o cartão, o html-to-image arredonda TODO tamanho de fonte pra
// `floor(px) - 0.1` (uma defesa dele contra overflow de arredondamento). Nos
// textos pequenos do cartão da semana (~9px) isso é quase 5% menor, e a imagem
// gerada quebra as linhas em pontos diferentes da prévia: uma nota de 2 linhas
// vira 1, outra fica com uma sobra órfã tipo "30)" sozinha na última linha.
//
// O tamanho vai pro SVG dentro do shorthand `font` (Chrome serializa
// "font: 600 8.9px / 11.74px system-ui…"), então a gente marca o valor real de
// cada elemento antes do clone e devolve esse valor no SVG antes de rasterizar.
// Assim o PNG fica igual ao que está na tela (mesmo tamanho, mesma quebra de
// linha, mesmo espaçamento entre os eventos).
function marcarTamanhos(node: HTMLElement): HTMLElement[] {
  const els = [node, ...Array.from(node.querySelectorAll<HTMLElement>('*'))]
  els.forEach((el) => el.setAttribute(ATTR, getComputedStyle(el).fontSize))
  return els
}

function restaurarTamanhos(svg: string): string {
  return svg.replace(/<[a-zA-Z][^>]*\sdata-font-exata="[^"]*"[^>]*>/g, (tag) => {
    const real = new RegExp(`\\s${ATTR}="([^"]*)"`).exec(tag)?.[1] ?? ''
    const limpo = tag.replace(new RegExp(`\\s${ATTR}="[^"]*"`), '')
    if (!real) return limpo
    return (
      limpo
        // shorthand `font`: primeiro "<n>px" depois de `font:` é o tamanho
        .replace(/font:([^;"]*?)(\d+(?:\.\d+)?)px/, (_m, antes: string) => `font:${antes}${real}`)
        // e, se algum dia vier como longhand, cobre também
        .replace(/(font-size:\s*)([^;"]*)/g, `$1${real}`)
    )
  })
}

function carregarImagem(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('não deu pra rasterizar o cartão'))
    img.src = url
  })
}

// Mesma saída do `toPng`, mas com o tamanho de fonte real (ver comentário acima).
export async function toPngExato(node: HTMLElement, pixelRatio: number): Promise<string> {
  const marcados = marcarTamanhos(node)
  let dataUrl = ''
  try {
    const svgUrl = await toSvg(node, { cacheBust: true })
    const svg = restaurarTamanhos(decodeURIComponent(svgUrl.slice(SVG_PREFIX.length)))
    dataUrl = SVG_PREFIX + encodeURIComponent(svg)
  } finally {
    marcados.forEach((el) => el.removeAttribute(ATTR))
  }

  const img = await carregarImagem(dataUrl)
  const canvas = document.createElement('canvas')
  // getBoundingClientRect (e não offsetWidth/Height) pra não perder a fração de
  // px: o cartão de stories tem 533,33px de altura e 533 * 3,6 dava 1919 em vez
  // dos 1920 anunciados.
  const { width, height } = node.getBoundingClientRect()
  canvas.width = Math.round(width * pixelRatio)
  canvas.height = Math.round(height * pixelRatio)
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('não deu pra gerar a imagem')
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
  return canvas.toDataURL('image/png')
}
