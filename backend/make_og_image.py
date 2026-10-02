"""Gera a imagem de preview (OG image) do site: metade SIM (verde) / metade NAO (vermelho).

Uso: python backend/make_og_image.py
Saida: frontend/public/og.png (1200x630, padrão de OG image).
"""

from pathlib import Path

from PIL import Image, ImageDraw

W, H = 1200, 630
GREEN = "#16a34a"
RED = "#dc2626"
INK = "#0b0b0b"

THUMB_UP = [
    # (x, y) em coordenadas 0..100, mesmo desenho do favicon
    (32, 50, 38, 81),  # placeholder, substituido abaixo
]


def rounded_rect(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def draw_thumb(draw, cx, cy, scale, up=True):
    """Desenha o mesmo polegar do favicon, centralizado em (cx, cy)."""
    # caminho do polegar em coordenadas 0..100 (mesma arte do favicon.ts)
    path = [
        (32, 50), (32, 75), (38, 81), (65, 81), (70, 81), (74, 77), (75, 72),
        (81, 48), (82, 42), (77, 37), (71, 37), (57, 37), (59, 33), (60, 25),
        (57, 20), (55, 17), (50, 17), (48, 21), (45, 27), (43, 36), (38, 42),
        (32, 45), (32, 50),
    ]
    bar = [(20, 46), (29, 81)]

    def place(pts):
        out = []
        for pt in pts:
            x, y = pt[0], pt[1]
            nx = cx + (x - 50) * scale
            ny = cy + (y - 49) * scale
            out.append((nx, ny))
        return out

    if up:
        draw.polygon(place(path), fill="#ffffff")
        p = place(bar)
        draw.rectangle([p[0][0], p[0][1], p[1][0], p[1][1]], fill="#ffffff")
    else:
        # mesma arte rotacionada 180 graus (igual ao favicon do NAO)
        pts = place(path)
        rot = [(2 * cx - x, 2 * cy - y) for (x, y) in pts]
        draw.polygon(rot, fill="#ffffff")
        p = place(bar)
        draw.rectangle(
            [2 * cx - p[1][0], 2 * cy - p[1][1], 2 * cx - p[0][0], 2 * cy - p[0][1]],
            fill="#ffffff",
        )


def split_x(y: float) -> float:
    """X da divisoria diagonal no ponto y. Vai de W (topo direita) ate 0 (base esquerda)."""
    return W * (1.0 - y / H)


def main():
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)

    # divisao diagonal: verde no triangulo de cima-esquerda, vermelho embaixo-direita
    for y in range(H):
        xb = split_x(y)
        d.line([(0, y), (xb, y)], fill=GREEN)
        d.line([(xb, y), (W, y)], fill=RED)

    # linha divisoria preta sobre a diagonal
    d.line([(W, 0), (0, H)], fill=INK, width=6)

    try:
        from PIL import ImageFont

        font_big = ImageFont.truetype("arialbd.ttf", 150)
        font_sub = ImageFont.truetype("arial.ttf", 38)
    except Exception:
        font_big = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    def label(cx, cy, big, small):
        draw_thumb(d, cx, cy, 1.6, up=big)
        bbox = d.textbbox((0, 0), "SIM" if big else "NAO", font=font_big)
        d.text((cx - (bbox[2] - bbox[0]) / 2, cy + 70), "SIM" if big else "NAO", font=font_big, fill="#ffffff")
        bbox2 = d.textbbox((0, 0), small, font=font_sub)
        d.text((cx - (bbox2[2] - bbox2[0]) / 2, cy + 165), small, font=font_sub, fill="#ffffff")

    label(W * 0.26, H * 0.30, True, "tem palquinho")
    label(W * 0.74, H * 0.72, False, "sem palquinho")

    # marca d'agua com o nome do site
    try:
        font_wm = ImageFont.truetype("arialbd.ttf", 36)
        bbox3 = d.textbbox((0, 0), "tem palquinho hoje?", font=font_wm)
        d.text((W - (bbox3[2] - bbox3[0]) - 36, H - 62), "tem palquinho hoje?", font=font_wm, fill="#ffffff")
    except Exception:
        pass

    out = Path(__file__).resolve().parent.parent / "frontend" / "public" / "og.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    print(f"gerado: {out} ({W}x{H})")


if __name__ == "__main__":
    main()