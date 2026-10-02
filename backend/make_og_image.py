"""Gera a imagem de preview (OG image) do site: quadrada, fundo preto, com os
dois polegares grandes centralizados lado a lado (verde SIM, vermelho NAO).

Uso: python backend/make_og_image.py
Saida: frontend/public/og.png (1200x1200, quadrado).
"""

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 1200
GREEN = "#16a34a"
RED = "#dc2626"
BLACK = "#000000"

# arte do polegar em coordenadas 0..100 (mesma do favicon.ts)
THUMB_PATH = [
    (32, 50), (32, 75), (38, 81), (65, 81), (70, 81), (74, 77), (75, 72),
    (81, 48), (82, 42), (77, 37), (71, 37), (57, 37), (59, 33), (60, 25),
    (57, 20), (55, 17), (50, 17), (48, 21), (45, 27), (43, 36), (38, 42),
    (32, 45), (32, 50),
]
THUMB_BAR = [(20, 46), (29, 81)]

# centro da arte do polegar nas coordenadas 0..100
THUMB_CX, THUMB_CY = 51.0, 49.0


def draw_thumb(d, cx, cy, height, color, up=True):
    """Polegar com a altura dada em px, centralizado em (cx, cy). up=False gira 180 graus."""
    scale = height / (81 - 17)

    def place(pts):
        return [(cx + (p[0] - THUMB_CX) * scale, cy + (p[1] - THUMB_CY) * scale) for p in pts]

    if up:
        d.polygon(place(THUMB_PATH), fill=color)
        p = place(THUMB_BAR)
        d.rectangle([p[0][0], p[0][1], p[1][0], p[1][1]], fill=color)
    else:
        d.polygon([(2 * cx - x, 2 * cy - y) for x, y in place(THUMB_PATH)], fill=color)
        p = place(THUMB_BAR)
        d.rectangle(
            [2 * cx - p[1][0], 2 * cy - p[1][1], 2 * cx - p[0][0], 2 * cy - p[0][1]],
            fill=color,
        )


def main():
    img = Image.new("RGB", (SIZE, SIZE), BLACK)
    d = ImageDraw.Draw(img)

    # dois polegares grandes, centralizados verticalmente e lado a lado
    thumb_h = 500
    cy = SIZE / 2
    draw_thumb(d, SIZE * 0.265, cy, thumb_h, GREEN, up=True)
    draw_thumb(d, SIZE * 0.735, cy, thumb_h, RED, up=False)

    out = Path(__file__).resolve().parent.parent / "frontend" / "public" / "og.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    print(f"gerado: {out} ({SIZE}x{SIZE})")


if __name__ == "__main__":
    main()