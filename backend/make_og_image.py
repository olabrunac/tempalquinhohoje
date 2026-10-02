"""Gera a imagem de preview (OG image) do site: quadrada, dividida na diagonal
com o polegar do favicon verde (SIM) e vermelho (NAO).

Uso: python backend/make_og_image.py
Saida: frontend/public/og.png (1200x1200, quadrado).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 1200
GREEN = "#16a34a"
RED = "#dc2626"
INK = "#0b0b0b"
WHITE = "#ffffff"

# arte do polegar em coordenadas 0..100 (mesma do favicon.ts)
THUMB_PATH = [
    (32, 50), (32, 75), (38, 81), (65, 81), (70, 81), (74, 77), (75, 72),
    (81, 48), (82, 42), (77, 37), (71, 37), (57, 37), (59, 33), (60, 25),
    (57, 20), (55, 17), (50, 17), (48, 21), (45, 27), (43, 36), (38, 42),
    (32, 45), (32, 50),
]
THUMB_BAR = [(20, 46), (29, 81)]


def draw_thumb(d, cx, cy, scale, up=True):
    """Polegar do favicon, centralizado em (cx, cy). up=False espelha 180 graus."""
    def place(pts):
        return [(cx + (p[0] - 50) * scale, cy + (p[1] - 49) * scale) for p in pts]

    if up:
        d.polygon(place(THUMB_PATH), fill=WHITE)
        p = place(THUMB_BAR)
        d.rectangle([p[0][0], p[0][1], p[1][0], p[1][1]], fill=WHITE)
    else:
        d.polygon([(2 * cx - x, 2 * cy - y) for x, y in place(THUMB_PATH)], fill=WHITE)
        p = place(THUMB_BAR)
        d.rectangle(
            [2 * cx - p[1][0], 2 * cy - p[1][1], 2 * cx - p[0][0], 2 * cy - p[0][1]],
            fill=WHITE,
        )


def font(size, bold=True):
    for name in (("arialbd.ttf", "arial.ttf") if bold else ("arial.ttf",)):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def split_x(y):
    """X da diagonal em y: (SIZE, 0) topo-direita -> (0, SIZE) base-esquerda."""
    return SIZE * (1.0 - y / SIZE)


def main():
    img = Image.new("RGB", (SIZE, SIZE), INK)
    d = ImageDraw.Draw(img)

    # fills: verde acima-esquerda, vermelho abaixo-direita
    for y in range(SIZE):
        xb = split_x(y)
        d.line([(0, y), (xb, y)], fill=GREEN)
        d.line([(xb, y), (SIZE, y)], fill=RED)

    d.line([(SIZE, 0), (0, SIZE)], fill=INK, width=8)

    f_word = font(200)

    def bloco(cx, cy, up, word):
        """Polegar + palavra empilhados, espelhados entre si pela diagonal."""
        scale = 3.0
        half_t = (81 - 17) * scale / 2  # altura/2 do polegar
        half_w = (82 - 20) * scale / 2  # largura/2 do polegar
        bbox = d.textbbox((0, 0), word, font=f_word)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        if up:
            # polegar acima, texto abaixo
            draw_thumb(d, cx, cy - 40, scale, up=True)
            tx, ty = cx - tw / 2 - bbox[0], cy + 40
        else:
            # texto acima, polegar abaixo (espelho do verde)
            tx, ty = cx - tw / 2 - bbox[0], cy - 40 - th
            draw_thumb(d, cx, cy + 40 + th / 2, scale, up=False)
        d.text((tx, ty), word, font=f_word, fill=WHITE)

    # centroides dos triangulos: verde (400,400), vermelho (800,800)
    bloco(SIZE * 0.30, SIZE * 0.32, True, "SIM")
    bloco(SIZE * 0.70, SIZE * 0.68, False, "NAO")

    out = Path(__file__).resolve().parent.parent / "frontend" / "public" / "og.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    print(f"gerado: {out} ({SIZE}x{SIZE})")


if __name__ == "__main__":
    main()