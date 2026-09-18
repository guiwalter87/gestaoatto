#!/usr/bin/env python3
"""Radar Atto, variante "capa de jornal" v2 (referencia: Jornal do Comercio).
Uso: python3 gerar_radar_jornal.py edicao.json pasta_saida/
Campos extras opcionais no JSON:
  item["chapeu"]      rotulo acima do titulo (ex.: "JUROS", "CAXIAS DO SUL")
  bloco["indicadores"] lista de {"nome","valor","var","dir":"up|down|flat"}
"""
import os, sys, json, datetime, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import gerar_radar as g

W, H, M = 1080, 1920, 64
A = g.ASSETS
PAPEL = (246, 243, 236)
TINTA = (17, 20, 28)
TINTA2 = (62, 68, 82)
CINZA = (128, 132, 140)
NAVY = (13, 24, 50)
AZUL = (26, 58, 143)
TEAL = (0, 136, 142)
VERDE = (22, 140, 76)
VERM = (196, 40, 40)
CAIXA = (232, 236, 242)

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
DIAS_C = ["SEGUNDA", "TERÇA", "QUARTA", "QUINTA", "SEXTA", "SÁBADO", "DOMINGO"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
MESES_C = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

_fc = {}


def f(nome, t):
    k = (nome, t)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(os.path.join(A, nome), t)
    return _fc[k]


def caslon(t): return f("libre-caslon-condensed-latin-700-normal.woff", t)
def cond8(t): return f("roboto-condensed-latin-800-normal.woff", t)
def cond7(t): return f("roboto-condensed-latin-700-normal.woff", t)
def cond4(t): return f("roboto-condensed-latin-400-normal.woff", t)
def serif(t): return f("source-serif-4-latin-400-normal.woff", t)
def serifb(t): return f("source-serif-4-latin-700-normal.woff", t)


def papel(seed):
    img = Image.new("RGB", (W, H), PAPEL)
    rnd = random.Random(seed)
    n = Image.new("L", (W, H))
    n.putdata([128 + rnd.randint(-7, 7) for _ in range(W * H)])
    tex = Image.merge("RGB", (n, n, n))
    img = Image.blend(img, Image.composite(img, tex, Image.new("L", (W, H), 238)), 0.5)
    vin = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vin).rectangle((0, 0, W, H), outline=50, width=50)
    vin = vin.filter(ImageFilter.GaussianBlur(70))
    return Image.composite(Image.new("RGB", (W, H), (226, 220, 206)), img, vin)


def regua(d, y, tipo="fina", x0=M, x1=W - M):
    if tipo == "dupla":
        d.line((x0, y, x1, y), fill=TINTA, width=4)
        d.line((x0, y + 8, x1, y + 8), fill=TINTA, width=1)
    elif tipo == "grossa":
        d.line((x0, y, x1, y), fill=NAVY, width=6)
    else:
        d.line((x0, y, x1, y), fill=TINTA, width=1)


def par(d, x, y, texto, fonte, larg, lh, cor, desenhar=True):
    for l in g.quebra(texto, fonte, larg, d):
        if desenhar:
            d.text((x, y), l, font=fonte, fill=cor)
        y += lh
    return y


def seta(d, x, y, dirc, cor, s=14):
    if dirc == "up":
        d.polygon([(x, y + s), (x + s, y + s), (x + s / 2, y)], fill=cor)
    elif dirc == "down":
        d.polygon([(x, y), (x + s, y), (x + s / 2, y + s)], fill=cor)
    else:
        d.rectangle((x, y + s / 2 - 2, x + s, y + s / 2 + 2), fill=cor)


def cabecalho(img, d, ed, idx):
    dt = datetime.date.fromisoformat(ed["data"])
    n = len(ed["blocos"])
    # faixa superior
    y = 206
    d.text((M, y), "NEGÓCIOS EM 1 MINUTO", font=cond7(21), fill=TEAL)
    d.text((W - M, y), "MUNDO · BRASIL · SERRA GAÚCHA", font=cond7(21), fill=TINTA2, anchor="ra")
    # nome do jornal + bloco de data (como o "93 anos" do JC)
    d.text((M - 4, 236), "Radar Atto", font=caslon(150), fill=NAVY)
    dia = f"{dt.day:02d}"
    fx = W - M
    d.text((fx, 250), dia, font=cond8(118), fill=NAVY, anchor="ra")
    wdia = d.textlength(dia, font=cond8(118))
    d.text((fx - wdia - 12, 262), MESES_C[dt.month - 1], font=cond8(40), fill=TEAL, anchor="ra")
    d.text((fx - wdia - 12, 309), DIAS_C[dt.weekday()], font=cond7(22), fill=TINTA2, anchor="ra")
    d.text((fx - wdia - 12, 336), str(dt.year), font=cond7(22), fill=TINTA2, anchor="ra")
    # linha de servico
    y = 412
    regua(d, y)
    d.text((M, y + 14), "Edição matinal", font=serifb(20), fill=TINTA2)
    regua(d, y + 54, "dupla")
    # cadernos
    y = 486
    gap = 8
    larg = (W - 2 * M - gap * (n - 1)) / n
    for i, b in enumerate(ed["blocos"]):
        x0 = M + i * (larg + gap)
        rot = b["titulo"].upper()
        if i == idx:
            d.rectangle((x0, y, x0 + larg, y + 52), fill=NAVY)
            cor = PAPEL
        else:
            d.rectangle((x0, y, x0 + larg, y + 52), fill=CAIXA)
            cor = TINTA2
        d.text((x0 + larg / 2, y + 27), rot, font=cond7(25), fill=cor, anchor="mm")


ESTILO = os.environ.get("RADAR_IND", "C")


def cor_var(it):
    return VERDE if it.get("dir") == "up" else VERM if it.get("dir") == "down" else CINZA


def indicadores(d, y, inds, desenhar=True, ref=""):
    n = len(inds)
    tit = "MERCADO" + (f" · FECHAMENTO {ref}" if ref else "")
    if ESTILO == "A":  # cartoes com faixa de cor
        h = 176
        if not desenhar:
            return y + h
        d.text((M, y), tit, font=cond7(20), fill=TEAL)
        gap = 16
        lc = (W - 2 * M - gap * (n - 1)) / n
        top = y + 34
        for i, it in enumerate(inds):
            x = M + i * (lc + gap)
            c = cor_var(it)
            d.rectangle((x, top, x + lc, top + h - 34), fill=(255, 255, 255), outline=(214, 218, 226), width=1)
            d.rectangle((x, top, x + lc, top + 6), fill=c)
            d.text((x + 18, top + 20), it["nome"].upper(), font=cond7(20), fill=TINTA2)
            d.text((x + 18, top + 46), it["valor"], font=cond8(40), fill=NAVY)
            pill = it.get("var", "")
            fw = cond7(21)
            pw = d.textlength(pill, font=fw) + 44
            d.rounded_rectangle((x + 18, top + 98, x + 18 + pw, top + 130), radius=16, fill=c + (34,))
            seta(d, x + 30, top + 107, it.get("dir", "flat"), c, 13)
            d.text((x + 52, top + 102), pill, font=fw, fill=c)
        return y + h
    if ESTILO == "B":  # faixa ticker escura
        h = 150
        if not desenhar:
            return y + h
        d.rectangle((M, y, W - M, y + h), fill=NAVY)
        d.rectangle((M, y, W - M, y + 36), fill=(20, 38, 76))
        d.text((M + 20, y + 7), tit, font=cond7(20), fill=(38, 201, 206))
        lc = (W - 2 * M) / n
        for i, it in enumerate(inds):
            x = M + i * lc
            if i:
                d.line((x, y + 50, x, y + h - 14), fill=(60, 78, 112), width=1)
            c = {"up": (60, 214, 120), "down": (255, 96, 96)}.get(it.get("dir"), (170, 180, 200))
            d.text((x + 22, y + 48), it["nome"].upper(), font=cond7(19), fill=(170, 184, 206))
            d.text((x + 22, y + 72), it["valor"], font=cond8(40), fill=(244, 246, 250))
            seta(d, x + 24, y + 124, it.get("dir", "flat"), c, 12)
            d.text((x + 44, y + 118), it.get("var", ""), font=cond7(21), fill=c)
        return y + h
    # C: tabela classica de jornal
    lh = 50
    h = 44 + lh * n + 8
    if not desenhar:
        return y + h
    d.line((M, y, W - M, y), fill=NAVY, width=4)
    d.text((M, y + 12), tit, font=cond7(20), fill=TEAL)
    d.text((W - M - 250, y + 12), "FECHAMENTO", font=cond7(18), fill=CINZA, anchor="ra")
    d.text((W - M, y + 12), "VARIAÇÃO NO DIA", font=cond7(18), fill=CINZA, anchor="ra")
    yy = y + 44
    for i, it in enumerate(inds):
        if i % 2 == 0:
            d.rectangle((M, yy, W - M, yy + lh), fill=CAIXA)
        c = cor_var(it)
        d.text((M + 16, yy + 10), it["nome"], font=cond7(28), fill=TINTA)
        d.text((W - M - 250, yy + 8), it["valor"], font=cond8(30), fill=NAVY, anchor="ra")
        v = it.get("var", "")
        vw = d.textlength(v, font=cond7(26))
        d.text((W - M - 16, yy + 10), v, font=cond7(26), fill=c, anchor="ra")
        seta(d, W - M - 16 - vw - 24, yy + 18, it.get("dir", "flat"), c, 14)
        yy += lh
    d.line((M, yy + 4, W - M, yy + 4), fill=NAVY, width=1)
    return y + h


def corpo(img, d, bloco, y, e, desenhar=True):
    itens = bloco["itens"]
    lt = W - 2 * M
    lead = itens[0]
    if lead.get("chapeu"):
        if desenhar:
            d.text((M, y), lead["chapeu"].upper(), font=cond7(int(24 * e)), fill=TEAL)
        y += int(36 * e)
    fm = cond8(int((86 if len(lead["titulo"]) <= 40 else 76) * e))
    y = par(d, M, y, lead["titulo"], fm, lt, int(fm.size * 1.05), TINTA, desenhar) + int(14 * e)
    y = par(d, M, y, lead["frase"], serif(int(32 * e)), lt, int(44 * e), TINTA2, desenhar) + 8
    if desenhar:
        d.text((M, y), f"Fonte: {lead.get('fonte', '')}", font=cond4(20), fill=CINZA)
    y += int(46 * e)
    if bloco.get("indicadores"):
        y = indicadores(d, y, bloco["indicadores"], desenhar, bloco.get("ref", "")) + int(28 * e)
    else:
        if desenhar:
            regua(d, y)
        y += int(30 * e)
    resto = itens[1:3]
    if resto:
        cols = len(resto)
        gc = 40
        lc = (lt - gc * (cols - 1)) / cols
        topo, fundo = y, y
        for k, it in enumerate(resto):
            x = M + k * (lc + gc)
            yy = topo
            if it.get("chapeu"):
                if desenhar:
                    d.text((x, yy), it["chapeu"].upper(), font=cond7(int(22 * e)), fill=TEAL)
                yy += int(32 * e)
            ft = cond7(int(44 * e))
            yy = par(d, x, yy, it["titulo"], ft, lc, int(ft.size * 1.1), TINTA, desenhar) + 10
            yy = par(d, x, yy, it["frase"], serif(int(27 * e)), lc, int(38 * e), TINTA2, desenhar) + 8
            if desenhar:
                d.text((x, yy), f"Fonte: {it.get('fonte', '')}", font=cond4(19), fill=CINZA)
            fundo = max(fundo, yy + 28)
        if desenhar:
            for k in range(1, cols):
                xl = M + k * (lc + gc) - gc / 2
                d.line((xl, topo, xl, fundo), fill=(160, 164, 172), width=1)
        y = fundo
    return y


def capa(ed, idx, destino):
    bloco = ed["blocos"][idx]
    n = len(ed["blocos"])
    ult = idx == n - 1
    img = papel(idx + 21)
    d = ImageDraw.Draw(img, "RGBA")
    cabecalho(img, d, ed, idx)

    # abertura do caderno
    y = 566
    ic = g.icone(bloco.get("icone", "globo"), 40, NAVY)
    img.paste(ic, (M, y - 4), ic)
    tit = bloco["titulo"].upper()
    d.text((M + 52, y), tit, font=cond8(30), fill=NAVY)
    wt = d.textlength(tit, font=cond8(30))
    d.line((M + 52 + wt + 18, y + 18, W - M - 70, y + 18), fill=NAVY, width=2)
    d.text((W - M, y + 2), f"{idx + 1} DE {n}", font=cond7(22), fill=CINZA, anchor="ra")
    y0 = y + 60

    limite = 1452 if ult else 1632
    esc = 0.8
    for e in (1.25, 1.2, 1.15, 1.1, 1.05, 1.0, 0.95, 0.9, 0.85, 0.8):
        if corpo(img, d, bloco, y0, e, desenhar=False) <= limite:
            esc = e
            break
    corpo(img, d, bloco, y0, esc)

    if ult:
        bx0, by0, bx1, by1 = M, 1478, W - M, 1622
        d.rectangle((bx0, by0, bx1, by1), fill=NAVY)
        r = 44
        cx, cy = bx0 + 34 + r, (by0 + by1) // 2
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(38, 201, 206))
        s = g.icone("sino", 56, NAVY)
        img.paste(s, (cx - 28, cy - 28), s)
        d.text((cx + r + 28, by0 + 30), "Ative o sino no nosso perfil", font=cond8(42), fill=PAPEL)
        d.text((cx + r + 28, by0 + 84), "e comece o dia atualizado em 1 minuto", font=serif(27), fill=(190, 204, 224))

    yf = 1664
    regua(d, yf, "dupla")
    d.text((M, yf + 28), "gestaoatto.com.br", font=cond7(23), fill=TINTA2)
    d.text((W - M, yf + 28), "@gestaoatto", font=cond7(23), fill=TEAL, anchor="ra")
    img.save(destino, "JPEG", quality=92, optimize=True)
    return destino


def main():
    ed = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for i in range(len(ed["blocos"])):
        print(capa(ed, i, os.path.join(out, f"story_{i + 1}.jpg")))


if __name__ == "__main__":
    main()
