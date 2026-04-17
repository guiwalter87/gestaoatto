#!/usr/bin/env python3
"""
Gerador de capas editoriais Atto — Perspectivas.

Para cada post do perspectivas-data.json, gera 4 formatos:
  - hero      1600x900   (capa do post + preview redes)
  - og        1200x630   (OG image pra LinkedIn/WhatsApp/Facebook)
  - ig-feed   1080x1080  (Instagram Feed)
  - ig-story  1080x1920  (Instagram Stories)

Formatos IG usam `titulo_curto` se disponível (mais impacto em pouco espaço).

Uso:
  python scripts/capas.py                  # gera todos
  python scripts/capas.py --slug <slug>    # regenera um só
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import json, os, textwrap, argparse, re, html

# ============================================================
# CONFIG
# ============================================================
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE = os.path.join(ROOT, "site")
DATA_PATH = os.path.join(SITE, "perspectivas-data.json")
FONT_DIR = "/Users/guilhermewalter/Documents/Claude/Projects/Site da Atto/fonts"
OUT_DIR = os.path.join(SITE, "assets", "capas")
LOGO_PATH = os.path.join(SITE, "assets", "atto_logo_white_o.png")

OUTFIT = os.path.join(FONT_DIR, "Outfit-VariableFont_wght.ttf")
MONO = os.path.join(FONT_DIR, "JetBrainsMono-VariableFont_wght.ttf")

AZUL_ATTO = (26, 58, 143)
AZUL_NOITE = (8, 18, 56)
TEAL = (0, 181, 184)

FORMATOS = [
    ("hero",     1600, 900,  False),   # (label, W, H, usa_titulo_curto)
    ("og",       1200, 630,  False),
    ("ig-feed",  1080, 1080, True),
    ("ig-story", 1080, 1920, True),
]

MESES_PT = {1:"jan", 2:"fev", 3:"mar", 4:"abr", 5:"mai", 6:"jun",
            7:"jul", 8:"ago", 9:"set", 10:"out", 11:"nov", 12:"dez"}

# ============================================================
# HELPERS
# ============================================================
def outfit(size, weight=400):
    f = ImageFont.truetype(OUTFIT, size)
    try: f.set_variation_by_axes([weight])
    except: pass
    return f

def mono(size, weight=400):
    f = ImageFont.truetype(MONO, size)
    try: f.set_variation_by_axes([weight])
    except: pass
    return f

def strip_html(text):
    """Remove tags HTML do título pra usar em imagem."""
    return html.unescape(re.sub(r'<[^>]+>', '', text))

def formatar_data(iso):
    """2026-03-22 -> '22 Mar · 2026'"""
    y, m, d = iso.split("-")
    mes = MESES_PT[int(m)].capitalize()
    return f"{int(d):02d} {mes} · {y}"

def add_grain(img, intensity=5):
    arr = np.array(img, dtype=np.int16)
    noise = np.random.randint(-intensity, intensity, arr.shape[:2], dtype=np.int16)
    for c in range(3):
        arr[:, :, c] = np.clip(arr[:, :, c] + noise, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))

def blob(img, cx, cy, r, color, alpha=180, blur=None):
    b = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (alpha,))
    b = b.filter(ImageFilter.GaussianBlur(blur or r // 2))
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    return Image.alpha_composite(img, b)

def fit_title(d, text, max_w_px, max_lines, sizes, weight=220):
    """Encontra o maior tamanho que cabe em max_lines dentro de max_w_px.

    NUNCA quebra palavra no meio (break_long_words=False). Se a palavra mais
    longa não couber na largura, o tamanho é rejeitado e tenta o próximo menor.
    """
    for size in sizes:
        f = outfit(size, weight)
        # Palavra mais longa precisa caber na largura disponível
        longest = max(text.split(), key=len)
        if d.textbbox((0, 0), longest, font=f)[2] > max_w_px:
            continue
        for chars in range(10, 90, 2):
            lines = textwrap.wrap(text, chars, break_long_words=False, break_on_hyphens=False)
            if len(lines) > max_lines:
                continue
            if all(d.textbbox((0, 0), ln, font=f)[2] <= max_w_px for ln in lines):
                return lines, size
    # Último recurso — usa o menor tamanho mesmo que ultrapasse
    return textwrap.wrap(text, 60, break_long_words=False, break_on_hyphens=False), sizes[-1]

# ============================================================
# GERADOR
# ============================================================
def gerar_capa(W, H, numero, categoria, titulo, data, leitura, out_path, formato_label):
    """Gerador universal adaptável a qualquer aspect ratio."""
    diag = (W * W + H * H) ** 0.5
    scale = diag / 1835.0  # baseline = 1600x900

    # Fundo + mesh blobs
    img = Image.new('RGBA', (W, H), AZUL_NOITE + (255,))
    img = blob(img, int(W * 0.9),  int(H * 0.85), int(560 * scale), TEAL,       alpha=110, blur=int(280 * scale))
    img = blob(img, int(W * 0.05), int(H * 0.1),  int(640 * scale), AZUL_ATTO,  alpha=160, blur=int(290 * scale))
    img = add_grain(img.convert('RGB'), 5).convert('RGBA')

    # Grid diagonal fininho
    grid = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    step = max(50, int(70 * scale))
    for i in range(-H, W + H, step):
        gd.line([(i, 0), (i + H, H)], fill=(255, 255, 255, 8), width=1)
    img = Image.alpha_composite(img, grid)

    d = ImageDraw.Draw(img, 'RGBA')

    # Margens — formatos estreitos (largura <= 1200) ganham margem lateral menor
    is_narrow = W <= 1200
    if is_narrow:
        PAD_L = int(W * 0.07)
        PAD_R = int(W * 0.07)
    else:
        PAD_L = int(100 * scale)
        PAD_R = int(100 * scale)
    PAD_T = int(90 * scale)
    PAD_B = int(90 * scale)

    # 1) Número grande (topo)
    num_size = int(H * 0.28) if H <= 1200 else int(H * 0.24)
    d.text((PAD_L, PAD_T - int(20 * scale)), numero, fill=TEAL + (220,), font=outfit(num_size, 160))
    num_bottom = PAD_T + int(num_size * 0.95)

    # 2) Kicker + linha teal
    kicker_y = num_bottom + int(50 * scale)
    kicker = f"PERSPECTIVAS · {categoria.upper()}"
    kicker_size = max(int(20 * scale), 12)
    d.text((PAD_L, kicker_y), kicker, fill=TEAL + (255,), font=mono(kicker_size, 500))
    line_y = kicker_y + int(kicker_size * 1.8)
    d.rectangle([PAD_L, line_y, PAD_L + int(130 * scale), line_y + max(2, int(3 * scale))], fill=TEAL)

    # 3) Título — auto-fit em altura e largura
    title_y = line_y + int(40 * scale)
    meta_y = H - PAD_B + int(10 * scale)
    title_max_h = meta_y - int(40 * scale) - title_y
    title_max_w = W - PAD_L - PAD_R

    # Tamanhos candidatos — proporcionais à largura,
    # mas formatos verticais (H > W) ganham tamanho maior pra aproveitar o espaço
    is_tall = H > W
    if is_tall:
        base_size = int(W * 0.085)   # story 9:16 — título grande
    elif is_narrow:
        base_size = int(W * 0.062)   # feed quadrado
    else:
        base_size = int(W * 0.048)   # hero / og landscape
    sizes = [int(base_size * m) for m in (1.0, 0.92, 0.84, 0.76, 0.68, 0.6, 0.52, 0.45)]

    chosen_lines, chosen_size = None, None
    for s in sizes:
        line_h = int(s * 1.15)
        max_lines = max(2, title_max_h // line_h)
        lines, fsize = fit_title(d, titulo, title_max_w, max_lines, [s])
        if fsize == s and len(lines) * line_h <= title_max_h:
            chosen_lines, chosen_size = lines, s
            break
    if chosen_lines is None:
        chosen_size = sizes[-1]
        chosen_lines = textwrap.wrap(titulo, 44)

    line_h = int(chosen_size * 1.15)
    y = title_y
    for line in chosen_lines:
        d.text((PAD_L, y), line, fill=(255, 255, 255, 255), font=outfit(chosen_size, 220))
        y += line_h

    # 4) Rodapé — meta à esquerda, logo à direita
    meta_size = max(int(15 * scale), 10)
    d.text((PAD_L, meta_y), f"{data.upper()}   ·   {leitura.upper()}", fill=(255, 255, 255, 160), font=mono(meta_size, 500))

    # Logo (Att branco + O colorido)
    if os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert('RGBA')
        logo_h = int(H * 0.06) if H <= 1200 else int(H * 0.055)
        ratio = logo_h / logo.height
        logo = logo.resize((int(logo.width * ratio), logo_h), Image.LANCZOS)
        lx = W - PAD_R - logo.width
        ly = meta_y - int(logo_h * 0.3)
        img.paste(logo, (lx, ly), logo)

    img.convert('RGB').save(out_path, 'PNG', optimize=True)
    return chosen_size, len(chosen_lines)


# ============================================================
# PIPELINE
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", help="Gera capa de um slug específico (default: todos)")
    parser.add_argument("--only", choices=[f[0] for f in FORMATOS], help="Gera apenas um formato")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    with open(DATA_PATH, encoding="utf-8") as f:
        posts = json.load(f)

    if args.slug:
        posts = [p for p in posts if p["slug"] == args.slug]
        if not posts:
            raise SystemExit(f"Slug {args.slug} não encontrado em {DATA_PATH}")

    # Numeração cronológica (01 = mais antigo)
    # Ordena por data crescente e atribui número
    posts_sorted = sorted(posts, key=lambda p: p["data"])
    numero_by_slug = {p["slug"]: f"{i+1:02d}" for i, p in enumerate(posts_sorted)}
    # Se usando --slug, precisamos pegar a numeração da base completa
    if args.slug:
        with open(DATA_PATH, encoding="utf-8") as f:
            all_posts = json.load(f)
        all_sorted = sorted(all_posts, key=lambda p: p["data"])
        numero_by_slug = {p["slug"]: f"{i+1:02d}" for i, p in enumerate(all_sorted)}

    total = 0
    for post in posts:
        slug = post["slug"]
        numero = numero_by_slug[slug]
        categoria = post["categoria"]
        titulo_longo = strip_html(post["titulo"])
        titulo_curto = post.get("titulo_curto", titulo_longo)
        data = formatar_data(post["data"])
        leitura = post.get("leitura", "")

        print(f"\n[#{numero}] {slug}")
        for label, W, H, usa_curto in FORMATOS:
            if args.only and args.only != label:
                continue
            titulo = titulo_curto if usa_curto else titulo_longo
            out = os.path.join(OUT_DIR, f"{slug}_{label}.png")
            fsize, nlines = gerar_capa(W, H, numero, categoria, titulo, data, leitura, out, label)
            print(f"  {label:10s} {W}x{H}  t:{fsize}px  {nlines}L  -> {os.path.basename(out)}")
            total += 1

    print(f"\n✓ {total} capa(s) gerada(s) em {OUT_DIR}")


if __name__ == "__main__":
    main()
