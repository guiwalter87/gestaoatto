#!/usr/bin/env python3
"""
make_newsletter_cover.py

Gera o ícone 300×300 da Newsletter "Perspectivas Atto" no LinkedIn.
Reaproveita exatamente as cores e fontes das capas dos posts (Outfit + JetBrains Mono,
gradiente navy noite → azul atto + blob teal) para manter a coesão visual.

A renderização é feita em 600×600 e downsampleada para 300×300, para garantir
nitidez nos displays Retina do feed do LinkedIn.

Uso:
    cd ~/Documents/Claude/Projects/Site\\ da\\ Atto/site
    python3 scripts/make_newsletter_cover.py

Saída:
    ~/Desktop/atto_newsletter_300.png

Pode ser rodado quantas vezes quiser; sobrescreve o arquivo existente.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import os
from pathlib import Path

# ============================================================
# CONFIG (mesmas constantes do capas.py)
# ============================================================
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE = os.path.join(ROOT, "site")
FONT_DIR = "/Users/guilhermewalter/Documents/Claude/Projects/Site da Atto/fonts"
LOGO_PATH = os.path.join(SITE, "assets", "atto_logo_white_o.png")
OUT_PATH = os.path.expanduser("~/Desktop/atto_newsletter_300.png")

OUTFIT = os.path.join(FONT_DIR, "Outfit-VariableFont_wght.ttf")
MONO = os.path.join(FONT_DIR, "JetBrainsMono-VariableFont_wght.ttf")

AZUL_ATTO = (26, 58, 143)
AZUL_NOITE = (8, 18, 56)
TEAL = (0, 181, 184)

# Renderiza em 600×600 (retina) e downsampleia para 300×300
SCALE = 2
W = H = 300 * SCALE  # 600x600


# ============================================================
# HELPERS
# ============================================================
def blob(img, cx, cy, r, color, alpha=180, blur=None):
    """Pinta um disco borrado por cima da imagem (para gradiente sutil)."""
    b = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (alpha,))
    b = b.filter(ImageFilter.GaussianBlur(blur or r // 2))
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return Image.alpha_composite(img, b)


def add_grain(img, intensity=4):
    """Adiciona ruído sutil para evitar banding no gradiente."""
    arr = np.array(img, dtype=np.int16)
    noise = np.random.randint(-intensity, intensity, arr.shape[:2], dtype=np.int16)
    for c in range(3):
        arr[:, :, c] = np.clip(arr[:, :, c] + noise, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def mono(size, weight=500):
    f = ImageFont.truetype(MONO, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def draw_letter_spaced(d, text, x, y, font, fill, letter_spacing_em=0.12):
    """Desenha texto com letter-spacing manual (Pillow não tem nativo)."""
    sample_h = font.getbbox("A")[3]
    extra = int(sample_h * letter_spacing_em)
    cx = x
    for ch in text:
        d.text((cx, y), ch, fill=fill, font=font)
        bbox = d.textbbox((0, 0), ch, font=font)
        cx += (bbox[2] - bbox[0]) + extra
    return cx - extra  # x final


def measure_letter_spaced(d, text, font, letter_spacing_em=0.12):
    """Mede a largura total do texto com letter-spacing manual."""
    sample_h = font.getbbox("A")[3]
    extra = int(sample_h * letter_spacing_em)
    total = 0
    for i, ch in enumerate(text):
        bbox = d.textbbox((0, 0), ch, font=font)
        total += (bbox[2] - bbox[0])
        if i < len(text) - 1:
            total += extra
    return total


# ============================================================
# RENDER
# ============================================================
def main():
    if not os.path.exists(LOGO_PATH):
        raise SystemExit(
            f"❌ Logo não encontrado em {LOGO_PATH}\n"
            "   Verifique se o caminho do projeto está correto."
        )
    if not os.path.exists(OUTFIT) or not os.path.exists(MONO):
        raise SystemExit(
            f"❌ Fontes não encontradas em {FONT_DIR}\n"
            "   Esse script espera as fontes nos paths do capas.py."
        )

    # 1) Fundo navy + blobs (gradient sintético)
    img = Image.new("RGBA", (W, H), AZUL_NOITE + (255,))
    img = blob(img, int(W * 0.92), int(H * 0.92), int(W * 0.45), TEAL,      alpha=120, blur=int(W * 0.24))
    img = blob(img, int(W * 0.08), int(H * 0.10), int(W * 0.50), AZUL_ATTO, alpha=170, blur=int(W * 0.26))
    img = add_grain(img.convert("RGB"), 3).convert("RGBA")

    # 2) Logo Atto white centralizado (logo branco com o O turquesa)
    logo = Image.open(LOGO_PATH).convert("RGBA")
    target_w = int(W * 0.50)  # logo ocupa metade da largura
    ratio = target_w / logo.width
    logo_w, logo_h = target_w, int(logo.height * ratio)
    logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
    lx = (W - logo_w) // 2
    ly = int(H * 0.32) - logo_h // 2  # centralizado um pouco acima do meio
    img.paste(logo, (lx, ly), logo)

    # 3) Linha teal de acento abaixo do logo
    d = ImageDraw.Draw(img, "RGBA")
    line_y = ly + logo_h + int(H * 0.07)
    line_w = int(W * 0.12)
    line_h = max(2, int(H * 0.008))
    d.rectangle(
        [(W - line_w) // 2, line_y, (W + line_w) // 2, line_y + line_h],
        fill=TEAL,
    )

    # 4) "PERSPECTIVAS" em JetBrains Mono caps com letter-spacing
    perspectivas_size = int(H * 0.057)
    f_mono = mono(perspectivas_size, weight=500)
    text = "PERSPECTIVAS"
    text_w = measure_letter_spaced(d, text, f_mono, 0.14)
    text_x = (W - text_w) // 2
    text_y = line_y + int(H * 0.04)
    draw_letter_spaced(
        d, text, text_x, text_y, f_mono,
        fill=(255, 255, 255, 240),
        letter_spacing_em=0.14,
    )

    # 5) Downsample para 300×300 (qualidade Retina)
    out = img.convert("RGB").resize((300, 300), Image.LANCZOS)

    # 6) Garante a pasta da Desktop e salva
    Path(OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT_PATH, "PNG", optimize=True)

    print(f"\n✓ Logo da Newsletter gerado em:")
    print(f"  {OUT_PATH}\n")
    print("Próximo passo:")
    print("  1. Volta na janela do LinkedIn (Criar newsletter)")
    print("  2. Clique em 'Carregar imagem' e selecione esse arquivo da Desktop")
    print("  3. Confirme que o preview aparece sem distorção")


if __name__ == "__main__":
    main()
