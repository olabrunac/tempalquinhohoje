function faviconData(hasPalquinho: boolean): string {
  const bg = hasPalquinho ? '#16a34a' : '#dc2626'
  const transform = hasPalquinho ? '' : 'transform="translate(100, 100) rotate(180)"'
  const svg = `
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>
      <rect width='100' height='100' rx='24' fill='${bg}'/>
      <g ${transform} fill='#ffffff'>
        <path d='M32 50 L32 75 C32 78 35 81 38 81 L65 81 C70 81 74 77 75 72 L81 48 C82 42 77 37 71 37 L57 37 C59 33 60 25 57 20 C55 17 50 17 48 21 C45 27 43 36 38 42 L32 45 Z' />
        <rect x='20' y='46' width='9' height='35' rx='3' />
      </g>
    </svg>
  `.trim()
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}

export function setFavicon(hasPalquinho: boolean): void {
  const icon = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
  if (icon) icon.href = faviconData(hasPalquinho)
}
