#!/usr/bin/env python3
"""Radar Atto v2: gera os 3 stories diarios (1080x1920, JPEG) a partir de um JSON.

Uso: python3 gerar_radar.py edicao.json pasta_saida/
JSON:
{
  "data": "2026-09-18",
  "edicao": 1,
  "blocos": [
    {"titulo": "Mundo", "icone": "globo", "itens": [{"titulo": "...", "frase": "...", "fonte": "..."}]},
    {"titulo": "Brasil", "icone": "bandeira", "itens": [...]},
    {"titulo": "Serra Gaúcha", "icone": "serra", "itens": [...]}
  ]
}
O ultimo story recebe automaticamente o convite para ativar o sino.
"""
import io, json, os, sys, random, datetime, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
W, H = 1080, 1920
M = 84

TEAL = (38, 201, 206)
WHITE = (240, 244, 250)
BODY = (170, 184, 206)
MUTE = (110, 130, 162)
NAVY_T = (13, 24, 50)
NAVY_B = (6, 10, 22)
NAVY_INK = (8, 15, 30)

DIAS = ["SEGUNDA", "TERÇA", "QUARTA", "QUINTA", "SEXTA", "SÁBADO", "DOMINGO"]
MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

_fc = {}


def font(name, size, wght):
    k = (name, size, wght)
    if k not in _fc:
        f = ImageFont.truetype(io.BytesIO(open(os.path.join(ASSETS, name), "rb").read()), size)
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
        _fc[k] = f
    return _fc[k]


def outfit(size, wght=400):
    return font("Outfit-VariableFont_wght.ttf", size, wght)


def mono(size, wght=500):
    return font("JetBrainsMono-VariableFont_wght.ttf", size, wght)


# ---------------------------------------------------------------- fundo
def fundo(seed):
    grad = Image.linear_gradient("L").resize((W, H))
    grad = grad.point(lambda v: int(255 * ((v / 255) ** 1.15)))
    img = Image.composite(Image.new("RGB", (W, H), NAVY_B), Image.new("RGB", (W, H), NAVY_T), grad).convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((-380, 1250, 560, 2250), fill=(0, 181, 184, 70))
    g.ellipse((620, -300, 1500, 520), fill=(26, 58, 143, 90))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(190)))
    rnd = random.Random(seed)
    noise = Image.new("L", (W, H))
    noise.putdata([128 + rnd.randint(-4, 4) for _ in range(W * H)])
    grain = Image.merge("RGBA", (noise, noise, noise, Image.new("L", (W, H), 10)))
    return Image.alpha_composite(img, grain).convert("RGB")


# ---------------------------------------------------------------- icones (desenhados em 4x e reduzidos)
S = 4


def estrela(d, cx, cy, r, cor, pontas=5):
    pts = []
    for i in range(pontas * 2):
        ang = -math.pi / 2 + i * math.pi / pontas
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=cor)


def icone(tipo, px, cor=TEAL):
    Z = px * S
    im = Image.new("RGBA", (Z, Z), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = max(2, int(Z * 0.05))
    c = Z / 2
    if tipo == "globo":
        r = Z * 0.40
        d.ellipse((c - r, c - r, c + r, c + r), outline=cor, width=lw)
        d.ellipse((c - r * 0.42, c - r, c + r * 0.42, c + r), outline=cor, width=lw)
        d.line((c - r, c, c + r, c), fill=cor, width=lw)
        for f in (-0.55, 0.55):
            y = c + r * f
            dx = r * math.sqrt(1 - f * f) * 0.94
            d.line((c - dx, y, c + dx, y), fill=cor, width=lw)
    elif tipo == "cruzeiro":  # Cruzeiro do Sul
        estrela(d, c + Z * 0.02, c - Z * 0.33, Z * 0.10, cor)
        estrela(d, c - Z * 0.02, c + Z * 0.33, Z * 0.12, cor)
        estrela(d, c - Z * 0.31, c - Z * 0.02, Z * 0.09, cor)
        estrela(d, c + Z * 0.29, c - Z * 0.07, Z * 0.095, cor)
        estrela(d, c + Z * 0.14, c + Z * 0.11, Z * 0.055, cor)
    elif tipo == "bandeira":
        w, h = Z * 0.86, Z * 0.60
        x0, y0 = c - w / 2, c - h / 2
        d.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=Z * 0.06, outline=cor, width=lw)
        m = Z * 0.07
        d.polygon([(c, y0 + m), (x0 + w - m, c), (c, y0 + h - m), (x0 + m, c)], outline=cor, width=lw)
        r = Z * 0.14
        d.ellipse((c - r, c - r, c + r, c + r), fill=cor)
        faixa = Image.new("L", im.size, 0)
        fd = ImageDraw.Draw(faixa)
        R = r * 3.2
        fd.arc((c - R, c - r * 0.25, c + R, c - r * 0.25 + 2 * R), 180, 360, fill=255, width=int(lw * 0.8))
        circ = Image.new("L", im.size, 0)
        ImageDraw.Draw(circ).ellipse((c - r, c - r, c + r, c + r), fill=255)
        from PIL import ImageChops
        corte = ImageChops.multiply(faixa, circ)
        alpha = im.getchannel("A")
        im.putalpha(ImageChops.subtract(alpha, corte))
        d = ImageDraw.Draw(im)
    elif tipo == "serra":
        base = c + Z * 0.28
        s = Z * 0.09
        d.ellipse((c + Z * 0.23 - s, c - Z * 0.29 - s, c + Z * 0.23 + s, c - Z * 0.29 + s), outline=cor, width=lw)
        d.line([(c - Z * 0.44, base), (c - Z * 0.16, c - Z * 0.16), (c + Z * 0.02, c + Z * 0.05),
                (c + Z * 0.16, c - Z * 0.07), (c + Z * 0.44, base)], fill=cor, width=lw, joint="curve")
        d.line((c - Z * 0.44, base, c + Z * 0.44, base), fill=cor, width=lw)
        d.line([(c - Z * 0.27, c - Z * 0.01), (c - Z * 0.21, c + Z * 0.04), (c - Z * 0.16, c - Z * 0.01),
                (c - Z * 0.11, c + Z * 0.04), (c - Z * 0.05, c + Z * 0.0)], fill=cor, width=int(lw * 0.8), joint="curve")
    elif tipo == "radar":
        r = Z * 0.44
        sweep = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sweep)
        for i in range(60):
            a = max(0, 150 - i * 3)
            sd.pieslice((c - r, c - r, c + r, c + r), -90 - (i + 1) * 1.2, -90 - i * 1.2, fill=cor + (a,))
        im.alpha_composite(sweep)
        d = ImageDraw.Draw(im)
        for k, rr in enumerate((0.44, 0.30, 0.16)):
            q = Z * rr
            d.ellipse((c - q, c - q, c + q, c + q), outline=cor + ((255, 170, 120)[k],), width=lw)
        d.line((c, c, c, c - r), fill=cor, width=lw)
        b = Z * 0.055
        d.ellipse((c - b, c - b, c + b, c + b), fill=cor)
        bx, by, bb = c + Z * 0.21, c - Z * 0.16, Z * 0.05
        d.ellipse((bx - bb, by - bb, bx + bb, by + bb), fill=WHITE)
    elif tipo == "sino":
        r = Z * 0.24
        top = c - Z * 0.30
        d.pieslice((c - r, top, c + r, top + 2 * r), 180, 360, fill=cor)
        d.polygon([(c - r, top + r), (c + r, top + r), (c + r * 1.35, c + Z * 0.18), (c - r * 1.35, c + Z * 0.18)], fill=cor)
        d.rounded_rectangle((c - Z * 0.40, c + Z * 0.14, c + Z * 0.40, c + Z * 0.24), radius=Z * 0.05, fill=cor)
        k = Z * 0.075
        d.ellipse((c - k, c + Z * 0.25, c + k, c + Z * 0.25 + 2 * k), fill=cor)
        d.rounded_rectangle((c - Z * 0.035, top - Z * 0.07, c + Z * 0.035, top + Z * 0.02), radius=Z * 0.03, fill=cor)
    return im.resize((px, px), Image.LANCZOS)


# ---------------------------------------------------------------- componentes
def _cola(img, im, pos):
    img.paste(im, (int(pos[0]), int(pos[1])), im)

def quebra(texto, f, largura, d):
    linhas, atual = [], ""
    texto = texto.replace("R$ ", "R$\u00a0").replace("US$ ", "US$\u00a0")
    pal = [x for x in texto.split(" ") if x]
    if len(pal) > 2 and len(pal[-1]) <= 4:  # evita palavra curta sozinha na ultima linha
        pal[-2:] = [pal[-2] + "\u00a0" + pal[-1]]
    for p in pal:
        t = (atual + " " + p).strip()
        if d.textlength(t, font=f) <= largura:
            atual = t
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def masthead(img, d, edicao):
    _cola(img, icone("radar", 84), (M, 236))
    x = M + 104
    f1, f2 = outfit(54, 700), outfit(54, 300)
    d.text((x, 238), "RADAR", font=f1, fill=WHITE)
    d.text((x + d.textlength("RADAR", font=f1) + 12, 238), "ATTO", font=f2, fill=TEAL)
    txt = "NEGÓCIOS EM 1 MINUTO"
    d.text((x + 2, 304), txt, font=mono(19, 500), fill=MUTE)


def calendario(img, d, data_iso):
    dt = datetime.date.fromisoformat(data_iso)
    w, h = 128, 150
    x, y = W - M - w, 222
    d.rounded_rectangle((x, y, x + w, y + h), radius=18, fill=(255, 255, 255, 14), outline=(255, 255, 255, 46), width=2)
    d.rounded_rectangle((x, y, x + w, y + 42), radius=18, fill=TEAL)
    d.rectangle((x + 1, y + 24, x + w - 1, y + 42), fill=TEAL)
    for ax in (x + 34, x + w - 34):
        d.rounded_rectangle((ax - 5, y - 12, ax + 5, y + 12), radius=5, fill=WHITE)
    mes = MESES[dt.month - 1]
    fm = mono(21, 700)
    d.text((x + (w - d.textlength(mes, font=fm)) / 2, y + 8), mes, font=fm, fill=NAVY_INK)
    dia = f"{dt.day:02d}"
    fdia = outfit(66, 600)
    d.text((x + (w - d.textlength(dia, font=fdia)) / 2, y + 42), dia, font=fdia, fill=WHITE)
    sem = DIAS[dt.weekday()]
    fs = mono(15, 600)
    d.text((x + (w - d.textlength(sem, font=fs)) / 2, y + 120), sem, font=fs, fill=TEAL)


def progresso(d, idx, n, y, nomes):
    gap = 14
    hgt = 54
    larg = (W - 2 * M - gap * (n - 1)) / n
    f = outfit(24, 600)
    for i in range(n):
        x0 = M + i * (larg + gap)
        rot = nomes[i].upper()
        if i == idx:
            d.rounded_rectangle((x0, y, x0 + larg, y + hgt), radius=hgt // 2, fill=TEAL)
            cor = NAVY_INK
        else:
            d.rounded_rectangle((x0, y, x0 + larg, y + hgt), radius=hgt // 2, fill=(255, 255, 255, 10), outline=(255, 255, 255, 60), width=2)
            cor = BODY
        d.text((x0 + larg / 2, y + hgt / 2 + 1), rot, font=f, fill=cor, anchor="mm")


def cabecalho_bloco(img, d, bloco, idx, n):
    y = 496
    r = 60
    cx, cy = M + r, y + r
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(38, 201, 206, 26), outline=(38, 201, 206, 130), width=2)
    _cola(img, icone(bloco.get("icone", "globo"), 72), (int(cx - 36), int(cy - 36)))
    x = M + 2 * r + 30
    d.text((x, y + 2), f"{idx + 1:02d} DE {n:02d}", font=mono(20, 600), fill=TEAL)
    d.text((x - 3, y + 22), bloco["titulo"], font=outfit(84, 400), fill=WHITE)


TOPO = 690
BASE_NORMAL = 1600
BASE_ULTIMO = 1410


def layout_itens(d, itens, esc):
    x0 = M + 92
    larg = W - x0 - M
    ft, ff, fs = outfit(int(46 * esc), 600), outfit(int(32 * esc), 400), mono(int(21 * esc), 500)
    blocos, total = [], 0
    for it in itens:
        lt = quebra(it["titulo"], ft, larg, d)
        lf = quebra(it["frase"], ff, larg, d)
        h = len(lt) * int(58 * esc) + 14 + len(lf) * int(45 * esc) + 16 + int(26 * esc)
        blocos.append((lt, lf, it.get("fonte", ""), h))
        total += h
    total += (len(itens) - 1) * int(80 * esc)
    return blocos, total, (ft, ff, fs, x0, esc)


def escala_necessaria(bloco, base):
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    esc = 1.0
    while esc > 0.80:
        _, total, _ = layout_itens(tmp, bloco["itens"], esc)
        if total <= base - TOPO:
            break
        esc -= 0.02
    return esc


def desenhar_itens(d, bloco, esc):
    blocos, total, (ft, ff, fs, x0, esc) = layout_itens(d, bloco["itens"], esc)
    y = TOPO
    esp = int(80 * esc)
    for i, (lt, lf, fonte, h) in enumerate(blocos):
        d.text((M, y + 6), f"{i + 1:02d}", font=mono(int(32 * esc), 600), fill=TEAL)
        yy = y
        for l in lt:
            d.text((x0, yy), l, font=ft, fill=WHITE)
            yy += int(58 * esc)
        yy += 14
        for l in lf:
            d.text((x0, yy), l, font=ff, fill=BODY)
            yy += int(45 * esc)
        yy += 16
        if fonte:
            d.text((x0, yy), f"FONTE · {fonte.upper()}", font=fs, fill=MUTE)
        y += h
        if i < len(blocos) - 1:
            y += esp // 2
            d.line((x0, y, W - M, y), fill=(255, 255, 255, 28), width=1)
            y += esp // 2


def cta_sino(img, d):
    x0, y0, x1, y1 = M, 1456, W - M, 1620
    d.rounded_rectangle((x0, y0, x1, y1), radius=26, fill=(38, 201, 206, 30), outline=(38, 201, 206, 150), width=2)
    r = 48
    cx, cy = x0 + 34 + r, (y0 + y1) // 2
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=TEAL)
    _cola(img, icone("sino", 60, NAVY_INK), (cx - 30, cy - 30))
    tx = cx + r + 30
    d.text((tx, y0 + 34), "Ative o sino no nosso perfil", font=outfit(38, 600), fill=WHITE)
    d.text((tx, y0 + 88), "e comece o dia atualizado em 1 minuto", font=outfit(29, 400), fill=BODY)


def rodape(img, d):
    yf = 1668
    d.line((M, yf, W - M, yf), fill=(255, 255, 255, 34), width=1)
    d.text((M, yf + 32), "UMA PUBLICAÇÃO", font=mono(17, 500), fill=MUTE)
    logo = Image.open(os.path.join(ASSETS, "logo_branco_colorido.png")).convert("RGBA")
    lw = 104
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    _cola(img, logo, (M + 172, yf + 16))
    at = "@gestaoatto"
    f = mono(22, 600)
    d.text((W - M - d.textlength(at, font=f), yf + 30), at, font=f, fill=TEAL)


def story(bloco, idx, n, ed, destino, esc):
    img = fundo(idx * 7919 + int(ed["data"].replace("-", "")) % 1000)
    d = ImageDraw.Draw(img, "RGBA")
    masthead(img, d, ed.get("edicao"))
    calendario(img, d, ed["data"])
    progresso(d, idx, n, 404, [b["titulo"] for b in ed["blocos"]])
    cabecalho_bloco(img, d, bloco, idx, n)
    desenhar_itens(d, bloco, esc)
    if idx == n - 1:
        cta_sino(img, d)
    rodape(img, d)
    img.convert("RGB").save(destino, "JPEG", quality=92, optimize=True)
    return destino


def main():
    ed = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    n = len(ed["blocos"])
    esc = min(escala_necessaria(b, BASE_ULTIMO if i == n - 1 else BASE_NORMAL) for i, b in enumerate(ed["blocos"]))
    if esc < 0.84:
        print("AVISO: texto longo demais, encurtar titulos/frases", file=sys.stderr)
    arqs = [story(b, i, n, ed, os.path.join(out, f"story_{i + 1}.jpg"), esc) for i, b in enumerate(ed["blocos"])]
    print("\n".join(arqs))


if __name__ == "__main__":
    main()
