#!/usr/bin/env python3
"""
Patch em todos os HTMLs de /site/perspectivas/ para integrar:
1. Capa hero (PNG gerado) no lugar do gradient do .post-capa
2. OG image apontando pra capa OG (1200x630)
3. Bloco de share no rodapé (LinkedIn · WhatsApp · IG Feed · IG Stories)
4. CSS do bloco de share injetado no <style> do post

Idempotente — pode ser rodado quantas vezes for.
"""
import json, os, re, html

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE = os.path.join(ROOT, "site")
DATA = os.path.join(SITE, "perspectivas-data.json")
POSTS_DIR = os.path.join(SITE, "perspectivas")
BASE_URL = "https://www.gestaoatto.com.br"

SHARE_CSS = """
/* ===== SHARE (gerado automaticamente — não editar manualmente) ===== */
.post-share{max-width:720px;margin:48px auto 0;padding:32px 0;border-top:1px solid var(--linha);border-bottom:1px solid var(--linha)}
.post-share .share-label{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:var(--cinza-medio);margin-bottom:16px}
.post-share .share-actions{display:flex;flex-wrap:wrap;gap:10px}
.post-share a{display:inline-flex;align-items:center;gap:8px;padding:10px 18px;border:1px solid var(--linha);border-radius:100px;font-family:'Outfit',sans-serif;font-weight:400;font-size:14px;color:var(--tinta);transition:all .2s;text-decoration:none}
.post-share a:hover{border-color:var(--azul-atto);color:var(--azul-atto);background:rgba(26,58,143,.03)}
.post-share a.primary{background:var(--azul-atto);border-color:var(--azul-atto);color:#fff}
.post-share a.primary:hover{background:var(--azul-noite);border-color:var(--azul-noite);color:#fff}
.post-share svg{width:15px;height:15px}
"""

# SVG mini-ícones inline (monocromos, herdam currentColor)
ICON_LI = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.5 2h-17A1.5 1.5 0 002 3.5v17A1.5 1.5 0 003.5 22h17a1.5 1.5 0 001.5-1.5v-17A1.5 1.5 0 0020.5 2zM8 19H5v-9h3zM6.5 8.25A1.75 1.75 0 118.3 6.5a1.78 1.78 0 01-1.8 1.75zM19 19h-3v-4.74c0-1.42-.6-1.93-1.38-1.93A1.74 1.74 0 0013 14.19a.66.66 0 000 .14V19h-3v-9h2.9v1.3a3.11 3.11 0 012.7-1.4c1.55 0 3.36.86 3.36 3.66z"/></svg>'
ICON_WA = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M17.5 14.4c-.3-.1-1.8-.9-2-1s-.5-.2-.7.2-.8 1-1 1.2-.4.2-.7 0a8 8 0 01-2.3-1.5 9 9 0 01-1.6-2c-.2-.3 0-.5.1-.7l.6-.6.3-.4a.5.5 0 000-.4l-.9-2.2c-.2-.6-.5-.5-.7-.5H8a1.2 1.2 0 00-.8.4 3.4 3.4 0 00-1 2.6 5.9 5.9 0 001.2 3.1 13.5 13.5 0 005.1 4.5 17 17 0 001.7.6 4 4 0 001.9.1 3 3 0 002-1.4 2.5 2.5 0 00.2-1.4c-.1-.1-.3-.2-.6-.4zM12 2a10 10 0 00-8.5 15.3L2 22l4.8-1.3A10 10 0 1012 2zm0 18.3a8.3 8.3 0 01-4.3-1.2l-.3-.2-2.8.8.7-2.8-.2-.3a8.3 8.3 0 1111.6 3z"/></svg>'
ICON_DL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg>'

def url_encode(s):
    import urllib.parse
    return urllib.parse.quote(s)

def strip_html(text):
    return html.unescape(re.sub(r'<[^>]+>', '', text))

def render_share(slug, titulo):
    url = f"{BASE_URL}/perspectivas/{slug}.html"
    share_text = f"{titulo} — Perspectivas Atto"
    li = f"https://www.linkedin.com/sharing/share-offsite/?url={url_encode(url)}"
    wa = f"https://wa.me/?text={url_encode(share_text + ' ' + url)}"
    ig_feed = f"../assets/capas/{slug}_ig-feed.png"
    ig_story = f"../assets/capas/{slug}_ig-story.png"
    return f"""<div class="post-share">
  <div class="share-label">Compartilhe esta perspectiva</div>
  <div class="share-actions">
    <a class="primary" href="{li}" target="_blank" rel="noopener">{ICON_LI} LinkedIn</a>
    <a href="{wa}" target="_blank" rel="noopener">{ICON_WA} WhatsApp</a>
    <a href="{ig_feed}" download>{ICON_DL} Baixar para Instagram Feed</a>
    <a href="{ig_story}" download>{ICON_DL} Baixar para Instagram Stories</a>
  </div>
</div>"""

# ============================================================
def patch_post(html_path, post):
    slug = post["slug"]
    titulo = strip_html(post["titulo"])
    excerpt = post.get("excerpt", "")
    with open(html_path, encoding="utf-8") as f:
        src = f.read()
    original = src

    capa_hero = f"../assets/capas/{slug}_hero.png"
    capa_og = f"{BASE_URL}/assets/capas/{slug}_og.png"

    # 1) Injeta <img> dentro de .post-capa (idempotente)
    src = re.sub(
        r'<div class="post-capa">\s*(<img[^>]*>)?\s*</div>',
        f'<div class="post-capa"><img src="{capa_hero}" alt="{html.escape(titulo)}" loading="eager" /></div>',
        src, count=1
    )

    # 2) OG/Twitter image — substitui ou injeta
    if 'og:image' in src:
        src = re.sub(r'<meta property="og:image" content="[^"]*"\s*/?>',
                     f'<meta property="og:image" content="{capa_og}">', src)
    else:
        src = re.sub(r'(<meta property="og:description"[^>]*>)',
                     r'\1\n<meta property="og:image" content="'+capa_og+'">', src, count=1)
    if 'twitter:image' in src:
        src = re.sub(r'<meta (?:name|property)="twitter:image" content="[^"]*"\s*/?>',
                     f'<meta name="twitter:image" content="{capa_og}">', src)
    else:
        # Adiciona no fim do <head> se não existir twitter:image
        src = re.sub(r'(<meta property="og:image"[^>]*>)',
                     r'\1\n<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:title" content="'+html.escape(titulo)+'">\n<meta name="twitter:description" content="'+html.escape(excerpt)+'">\n<meta name="twitter:image" content="'+capa_og+'">',
                     src, count=1)

    # 3) CSS do share — injeta dentro do <style> do post se não existir
    if '.post-share{' not in src:
        src = src.replace('@media (max-width:720px){', SHARE_CSS.strip() + '\n@media (max-width:720px){', 1)

    # 4) Bloco de share — insere dentro de .post-footer logo no início (antes de .author-block)
    share_html = render_share(slug, titulo)
    if '<div class="post-share">' in src:
        # Já existe — substitui
        src = re.sub(r'<div class="post-share">.*?</div>\s*</div>',
                     share_html, src, count=1, flags=re.DOTALL)
    else:
        src = src.replace('<div class="author-block">',
                          share_html + '\n      <div class="author-block">', 1)

    if src != original:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(src)
        return True
    return False

# ============================================================
def main():
    with open(DATA, encoding="utf-8") as f:
        posts = json.load(f)

    touched = 0
    for post in posts:
        html_path = os.path.join(POSTS_DIR, f"{post['slug']}.html")
        if not os.path.exists(html_path):
            print(f"  MISSING: {html_path}")
            continue
        if patch_post(html_path, post):
            print(f"  ✓ patched: {post['slug']}")
            touched += 1
        else:
            print(f"  · unchanged: {post['slug']}")
    print(f"\n{touched}/{len(posts)} post(s) atualizado(s).")

if __name__ == "__main__":
    main()
