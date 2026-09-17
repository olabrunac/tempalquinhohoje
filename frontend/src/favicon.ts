function faviconData(emoji: string): string {
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>${emoji}</text></svg>`
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}

export function setFavicon(hasPalquinho: boolean): void {
  const icon = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
  if (icon) icon.href = faviconData(hasPalquinho ? '✅' : '❌')
}