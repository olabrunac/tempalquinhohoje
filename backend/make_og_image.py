"""Gera a imagem de preview (OG image) do site: quadrada, fundo preto, com os
dois polegares grandes centralizados lado a lado (verde SIM, vermelho NAO).

use a mesma arte do favicon em frontend/src/favicon.ts (mesmo path e mesmo rect
da barra, para o polegar ficar identico ao icone do site).

Uso: python backend/make_og_image.py
Saida: frontend/public/og.png (1200x1200, quadrado).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 1200
GREEN = "#16a34a"
RED = "#dc2626"
BLACK = "#000000"
WHITE = "#ffffff"

# viewBox 0 0 100 100, igual ao favicon
VIEWBOX = 100.0

# mesmo path do favicon.ts, em pontos (o path e a barra da barra lateral)
FAVICON_THUMB = [
    (32, 50), (32, 75), (38, 81), (65, 81), (70, 81), (74, 77), (75, 72),
    (81, 48), (82, 42), (77, 37), (71, 37), (57, 37), (59, 33), (60, 25),
    (57, 20), (55, 17), (50, 17), (48, 21), (45, 27), (43, 36), (38, 42),
    (32, 45),
]
FAVICON_BAR = {"x": 20, "y": 46, "w": 9, "h": 35, "rx": 3}


def draw_favicon_thumb(d, cx, cy, height, bg, up=True):
    """Desenha o favicon inteiro (fundo arredondado + polegar) no tamanho height,
    centralizado em (cx, cy). up=False gira 180 graus, como o favicon faz."""
    scale = height / VIEWBOX
    ox = cx - VIEWBOX * scale / 2
    oy = cy - VIEWBOX * scale / 2

    def pt(x, y):
        return (ox + x * scale, oy + y * scale)

    if not up:
        def pt(x, y):
            return (ox + (VIEWBOX - x) * scale, oy + (VIEWBOX - y) * scale)

    # fundo arredondado
    r = 24 * scale
    d.rounded_rectangle(
        [ox, oy, ox + VIEWBOX * scale, oy + VIEWBOX * scale],
        radius=r,
        fill=bg,
    )

    # arte do polegar: mesma geometria do favicon.ts
    d.polygon([pt(x, y) for x, y in FAVICON_THUMB], fill=WHITE)
    bx, by = FAVICON_BAR["x"], FAVICON_BAR["y"]
    p1 = pt(bx, by)
    p2 = pt(bx + FAVICON_BAR["w"], by + FAVICON_BAR["h"])
    d.rounded_rectangle(
        [min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])],
        radius=FAVICON_BAR["rx"] * scale,
        fill=WHITE,
    )


def main():
    img = Image.new("RGB", (SIZE, SIZE), BLACK)
    d = ImageDraw.Draw(img)

    # dois favicons grandes, centralizados verticalmente e lado a lado
    box = 500
    cy = SIZE / 2
    draw_favicon_thumb(d, SIZE * 0.265, cy, box, GREEN, up=True)
    draw_favicon_thumb(d, SIZE * 0.735, cy, box, RED, up=False)

    out = Path(__file__).resolve().parent.parent / "frontend" / "public" / "og.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    print(f"gerado: {out} ({SIZE}x{SIZE})")


if __name__ == "__main__":
    main()