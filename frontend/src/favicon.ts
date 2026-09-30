function faviconData(hasPalquinho: boolean): string {
  const color = hasPalquinho ? '#16a34a' : '#dc2626'
  const accent = hasPalquinho ? '#22c55e' : '#ef4444'
  const svg = `
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>
      <rect width='100' height='100' rx='22' fill='#0a0a0a'/>
      <path d='M30 15 L70 15 L85 75 L15 75 Z' fill='${color}' opacity='0.2'/>
      <ellipse cx='50' cy='75' rx='35' ry='6' fill='${color}'/>
      <ellipse cx='50' cy='73' rx='30' ry='4' fill='${accent}'/>
      <rect x='46' y='30' width='8' height='20' rx='4' fill='#ffffff'/>
      <path d='M40 40 C40 50 60 50 60 40' stroke='#ffffff' stroke-width='3' fill='none' stroke-linecap='round'/>
      <line x1='50' y1='50' x2='50' y2='68' stroke='#ffffff' stroke-width='4' stroke-linecap='round'/>
      <line x1='40' y1='68' x2='60' y2='68' stroke='#ffffff' stroke-width='4' stroke-linecap='round'/>
    </svg>
  `.trim()
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}

export function setFavicon(hasPalquinho: boolean): void {
  const icon = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
  if (icon) icon.href = faviconData(hasPalquinho)
}
