"""Render do Story do Instagram (1080x1920) em Pillow.

Porta o visual do cartão do site (frontend/src/ShareCard.tsx, variante "story")
para o servidor: fundo preto, SIM verde / NÃO vermelho / outro rolê laranja,
lista da semana com anel no dia e confete (só quando tem palquinho).

Feito pra rodar num endpoint que a API do Instagram busca por URL, então o
desenho espelha os mesmos valores do CSS (escala 3.6x de um cartão de 300px).
"""

from __future__ import annotations

import re
from datetime import date
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --- geometria (cartão de 300x533px do site escalado 3.6x -> 1080x1920) ---
W, H = 1080, 1920
SCALE = 3.6
PAD_X = 86
PAD_Y = 216
CONTENT_GAP = 50  # gap: 14px * 3.6

GREEN = (22, 163, 74)  # --green: #16a34a
RED = (220, 38, 38)  # --red: #dc2626
ORANGE = (249, 115, 22)  # --orange: #f97316
WHITE = (255, 255, 255)
DATE_COLOR = (213, 219, 228)  # #d5dbe4
NOTE_COLOR = (229, 231, 235)  # #e5e7eb
HANDLE_COLOR = (213, 219, 228)  # #d5dbe4
FOOTER_COLOR = (174, 182, 196)  # #aeb6c4
VIEWING_RING = (96, 165, 250)  # #60a5fa

STATE_COLOR = {"yes": GREEN, "no": RED, "other": ORANGE}

# Mesma paleta do confete do site (canvas-confetti).
CONFETTI_COLORS = [
    (239, 68, 68),  # #ef4444
    (249, 115, 22),  # #f97316
    (250, 204, 21),  # #facc15
    (34, 197, 94),  # #22c55e
    (59, 130, 246),  # #3b82f6
    (99, 102, 241),  # #6366f1
    (139, 92, 246),  # #8b5cf6
    (236, 72, 153),  # #ec4899
]

MONTHS = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]
WEEKDAYS_FULL = [
    "domingo",
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
]

_ASSETS = Path(__file__).resolve().parent / "assets"


@lru_cache(maxsize=None)
def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(_ASSETS / name), int(size))


def _regular(size: int) -> ImageFont.FreeTypeFont:
    return _font("Inter_400Regular.ttf", size)


def _semibold(size: int) -> ImageFont.FreeTypeFont:
    return _font("Inter_600SemiBold.ttf", size)


def _bold(size: int) -> ImageFont.FreeTypeFont:
    return _font("Inter_700Bold.ttf", size)


def _black(size: int) -> ImageFont.FreeTypeFont:
    return _font("Inter_900Black.ttf", size)


def fmt_date(day: date) -> str:
    """"quinta-feira, 15 de outubro de 2026" — mesmo formato do site."""
    dow = WEEKDAYS_FULL[(day.weekday() + 1) % 7]  # Python: seg=0 -> dom=0
    return f"{dow}, {day.day} de {MONTHS[day.month - 1]} de {day.year}"


def insta_handle(url: str | None) -> str | None:
    """Extrai "@alguem" de um link/@/nome de Instagram. Espelha o frontend."""
    if not url:
        return None
    t = url.strip()
    if not t:
        return None
    m = re.search(r"instagram\.com/([^/?#\s]+)", t, re.IGNORECASE)
    if m:
        u = m.group(1)
    else:
        u = re.sub(r"^@", "", t)
        u = re.split(r"[/?#\s]", u)[0]
    u = u.rstrip("/")
    if not u or u in ("p", "reel"):
        return None
    return "@" + u


def _mute(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Reproduz o filtro CSS saturate(0.78) brightness(0.82) do confete."""
    r, g, b = rgb
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    r = lum + 0.78 * (r - lum)
    g = lum + 0.78 * (g - lum)
    b = lum + 0.78 * (b - lum)
    return (int(r * 0.82), int(g * 0.82), int(b * 0.82))


def _confetti_layer() -> Image.Image:
    """Confete determinístico (o mesmo LCG do site, seed 7) — fica igual a cada render."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    seed = 7

    def rnd() -> float:
        nonlocal seed
        seed = (seed * 9301 + 49297) % 233280
        return seed / 233280

    for _ in range(90):
        color = _mute(CONFETTI_COLORS[int(rnd() * len(CONFETTI_COLORS))])
        x = rnd() / 100 * W
        y = rnd() / 100 * H
        w = (6 + rnd() * 6) * SCALE
        h = (11 + rnd() * 9) * SCALE
        rot = round(rnd() * 360)
        alpha = int((0.5 + rnd() * 0.3) * 255)

        piece = Image.new("RGBA", (int(w) + 2, int(h) + 2), (0, 0, 0, 0))
        pd = ImageDraw.Draw(piece)
        pd.rounded_rectangle(
            [1, 1, int(w), int(h)], radius=7, fill=(*color, alpha)
        )
        piece = piece.rotate(rot, expand=True, resample=Image.BICUBIC)
        layer.alpha_composite(
            piece, (int(x - piece.width / 2), int(y - piece.height / 2))
        )
    return layer


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    """Quebra em linhas pra caber em max_w, preservando as linhas explícitas (\\n)."""
    out: list[str] = []
    for raw in text.split("\n"):
        words = raw.split()
        if not words:
            continue
        cur = words[0]
        for word in words[1:]:
            test = f"{cur} {word}"
            if draw.textlength(test, font=font) <= max_w:
                cur = test
            else:
                out.append(cur)
                cur = word
        out.append(cur)
    return out


def _text_height(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[3] - box[1]


def render_story_jpeg(
    day: date,
    state: str,
    notes: list[str],
    handles: list[str],
    week: list[dict],
) -> bytes:
    """Monta o Story do `day` (estado 'yes'/'no'/'other') e devolve os bytes JPEG."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    if state == "yes":
        img.alpha_composite(_confetti_layer())

    big_label = "SIM" if state == "yes" else "NÃO"
    big_color = STATE_COLOR.get(state, RED)

    # --- medidas (feitas numa camada de texto, pra desenhar tudo junto depois) ---
    tl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(tl)

    date_font = _regular(53)
    big_font = _black(346)
    note_font = _semibold(60)
    handle_font = _bold(47)
    footer_font = _regular(39)

    date_h = _text_height(td, fmt_date(day), date_font)
    big_h = _text_height(td, big_label, big_font)
    note_line_h = round(60 * 1.35)
    note_lines: list[str] = []
    for n in notes:
        note_lines.extend(_wrap(td, n, note_font, W - 2 * PAD_X))
    note_h = len(note_lines) * note_line_h
    handle_h = _text_height(td, " · ".join(handles), handle_font) if handles else 0

    # --- bottom: semana + rodapé (ancorado embaixo) ---
    chip = 130
    chip_gap = 18
    footer_gap = 36
    footer_h = _text_height(td, "tempalquinhohoje.com · @tempalquinhohoje", footer_font)
    bottom_h = chip + footer_gap + footer_h
    bottom_top = H - PAD_Y - bottom_h

    # --- meio: SIM/NÃO + nota + @, centralizado no espaço livre ---
    blocks: list[tuple[str, int]] = [("big", big_h)]
    if note_h:
        blocks.append(("note", note_h))
    if handle_h:
        blocks.append(("handle", handle_h))
    content_h = sum(h for _, h in blocks) + CONTENT_GAP * (len(blocks) - 1)
    top = PAD_Y + date_h
    content_top = top + max(0, (bottom_top - top - content_h) / 2)

    # --- desenha chips da semana na base (o texto/glow vem por cima) ---
    n = len(week) or 7
    total_w = n * chip + (n - 1) * chip_gap
    x0 = (W - total_w) / 2
    dow_font = _bold(29)
    num_font = _bold(47)
    chip_texts: list[tuple[int, int, int, str, str, bool]] = []
    for i, d in enumerate(week):
        x = int(x0 + i * (chip + chip_gap))
        color = STATE_COLOR.get(d["state"], RED)
        ImageDraw.Draw(img).rounded_rectangle(
            [x, bottom_top, x + chip, bottom_top + chip], radius=32, fill=(*color, 255)
        )
        if d.get("viewing"):
            ImageDraw.Draw(img).rounded_rectangle(
                [x + 6, bottom_top + 6, x + chip - 6, bottom_top + chip - 6],
                radius=26,
                outline=(*VIEWING_RING, 255),
                width=11,
            )
        chip_texts.append((x, bottom_top, chip, d["dow"].upper(), str(d["num"]), True))

    # --- monta toda a camada de texto ---
    # data (topo)
    td.text((W / 2, PAD_Y + date_h / 2), fmt_date(day), font=date_font, fill=(*DATE_COLOR, 255), anchor="mm")
    # meio
    y = content_top
    for kind, h in blocks:
        if kind == "big":
            td.text((W / 2, y + big_h / 2), big_label, font=big_font, fill=(*big_color, 255), anchor="mm")
        elif kind == "note":
            yy = y
            for line in note_lines:
                td.text((W / 2, yy + note_line_h / 2), line, font=note_font, fill=(*NOTE_COLOR, 255), anchor="mm")
                yy += note_line_h
        elif kind == "handle":
            td.text((W / 2, y + handle_h / 2), " · ".join(handles), font=handle_font, fill=(*HANDLE_COLOR, 255), anchor="mm")
        y += h + CONTENT_GAP
    # chips (dow em cima, número embaixo)
    for x, cy, cw, dow, num, _ in chip_texts:
        cx = x + cw / 2
        td.text((cx, cy + 44), dow, font=dow_font, fill=(*WHITE, 255), anchor="mm")
        td.text((cx, cy + 86), num, font=num_font, fill=(*WHITE, 255), anchor="mm")
    # rodapé
    footer = "tempalquinhohoje.com · @tempalquinhohoje"
    td.text((W / 2, bottom_top + chip + footer_gap + footer_h / 2), footer, font=footer_font, fill=(*FOOTER_COLOR, 255), anchor="mm")

    # --- glow: duas camadas de preto borrado atrás do texto (text-shadow do site) ---
    alpha = tl.split()[3]
    for blur in (60, 180):
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        glow.paste((0, 0, 0, 255), (0, 0, W, H), alpha)
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(blur)))
    img.alpha_composite(tl)

    out = BytesIO()
    img.convert("RGB").save(out, "JPEG", quality=90, optimize=True)
    return out.getvalue()
