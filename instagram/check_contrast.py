"""Valida o PNG do post do Instagram: contraste WCAG do texto + % de confete.

Uso:
  python instagram/check_contrast.py instagram/post-exact.png
  python instagram/check_contrast.py instagram/post-exact.png 706,691,108,51

A 2a opcao (caixa do emoji em pixels do PNG: x,y,w,h) exclui o emoji da medicao —
senao o branco do rosto vira "texto" e o amarelo "fundo", gerando falso positivo
(~1,3:1). Medir a caixa: envolver o emoji em <span id="emo">, getBoundingClientRect() * 3.

Contraste = texto branco (L=1) vs pixel MAIS CLARO do fundo em raio 6px ao redor
de cada glifo, com a mascara de texto dilatada 3px (ignora borda antialiased).
"""
import sys
from PIL import Image
import numpy as np


def lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def dilate(m, k):
    d = m.copy()
    for _ in range(k):
        n = d.copy()
        n[1:, :] |= d[:-1, :]
        n[:-1, :] |= d[1:, :]
        n[:, 1:] |= d[:, :-1]
        n[:, :-1] |= d[:, 1:]
        d = n
    return d


path = sys.argv[1] if len(sys.argv) > 1 else 'instagram/post-exact.png'
EB = tuple(int(v) for v in sys.argv[2].split(',')) if len(sys.argv) > 2 else None

im = Image.open(path).convert('RGB')
a = np.asarray(im).astype(np.float32)
H, W, _ = a.shape
print('tamanho PNG:', im.size)

chroma_a = a.max(axis=2) - a.min(axis=2)
print('confete: %.2f%% de pixels coloridos' % (100.0 * int((chroma_a > 40).sum()) / (H * W)))

L = 0.2126 * lin(a[:, :, 0]) + 0.7152 * lin(a[:, :, 1]) + 0.0722 * lin(a[:, :, 2])

# texto = acromatico (R~G~B) e claro; inclui a borda antialiased do glifo
text_mask = (chroma_a < 45) & (L > 0.15)
if EB:
    ex = np.zeros((H, W), dtype=bool)
    ex[EB[1]:EB[1] + EB[3], EB[0]:EB[0] + EB[2]] = True
    text_mask = text_mask & ~ex

ys, xs = np.nonzero(text_mask)
print('pixels de texto:', len(ys))

bg_of_text = dilate(text_mask, 3)

R = 6
worst = 1e9
sum_c = 0.0
n = 0
wpos = None
for y, x in zip(ys, xs):
    y0, y1 = max(0, y - R), min(H, y + R + 1)
    x0, x1 = max(0, x - R), min(W, x + R + 1)
    pL = L[y0:y1, x0:x1]
    pBG = bg_of_text[y0:y1, x0:x1]
    bg = pL[~pBG]
    if bg.size == 0:
        continue
    i = int(np.argmax(bg))
    b = float(bg[i])
    cr = 1.05 / (b + 0.05)
    if cr < worst:
        by, bx = np.nonzero(~pBG)
        worst = cr
        wpos = (int(x), int(y), int(x0 + bx[i]), int(y0 + by[i]), round(b, 3))
    sum_c += cr
    n += 1

print('amostras:', n)
print('CONTRASTE MINIMO: %.2f:1' % worst, ' em glifo/fundo', wpos)
print('CONTRASTE MEDIO:  %.2f:1' % (sum_c / n))
print('meta AA (4.5:1):', 'PASSOU' if worst >= 4.5 else 'FALHOU')
print('meta AAA (7:1) media:', 'PASSOU' if (sum_c / n) >= 7 else 'FALHOU')
