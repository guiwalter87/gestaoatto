#!/usr/bin/env python3
"""
Atto Studio — backend Flask.

Centro local de criação e gestão de Perspectivas. Roda em http://127.0.0.1:8765
e oferece formulário de criação, listagem com status, calendário de
agendamento e botões de pipeline (capas, patch, commit/push).

Reaproveita o pipeline existente:
- scripts/capas.py        — gera 4 PNGs (hero, og, ig-feed, ig-story)
- scripts/patch_posts.py  — injeta capa + share block no HTML
- scripts/inject_site_js.py — injeta scroll-progress + site.js
- scripts/publish_scheduled.py — publica posts agendados
- scripts/scheduled_posts.json — registry de posts (incluindo agendados)
- site/perspectivas-data.json  — registry oficial usado pelo capas.py

Uso:
    python3 app.py        # sobe em http://127.0.0.1:8765
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import markdown as md
from flask import Flask, jsonify, render_template, request, send_file

# Carrega .env se houver (silencioso se não)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# Cliente Anthropic é importado dinamicamente para não quebrar o app se
# o usuário ainda não instalou. Importação tardia em api_generate_text.

# ============================================================
# PATHS
# ============================================================
STUDIO_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = STUDIO_DIR.parent
REPO_ROOT = SCRIPTS_DIR.parent
SITE = REPO_ROOT / "site"

PERSPECTIVAS_DIR = SITE / "perspectivas"
PERSPECTIVAS_HTML = SITE / "perspectivas.html"
SITEMAP = SITE / "sitemap.xml"
DATA_JSON = SITE / "perspectivas-data.json"
SCHEDULED_JSON = SCRIPTS_DIR / "scheduled_posts.json"
CAPAS_DIR = SITE / "assets" / "capas"
TEMPLATE_HTML = STUDIO_DIR / "post_template.html"
# Fonte markdown preservada de cada post (para suportar edit limpo)
SOURCES_DIR = STUDIO_DIR / "sources"
SOURCES_DIR.mkdir(exist_ok=True)

CAPAS_PY = SCRIPTS_DIR / "capas.py"
PATCH_PY = SCRIPTS_DIR / "patch_posts.py"
INJECT_PY = SCRIPTS_DIR / "inject_site_js.py"

# ============================================================
# CONSTANTES
# ============================================================
CATEGORIAS = ["Direção", "Performance", "Pessoas", "Governança", "M&A",
              "Sucessão", "Indústria", "Distribuição"]

# Mapeamento categoria → tag_class de cor (consistente com perspectivas.html)
TAG_CLASS = {
    "Direção": "img-dark",
    "Performance": "img-blue",
    "Pessoas": "img-paper",
    "Governança": "img-teal",
    "M&A": "img-roxo",
    "Sucessão": "img-warm",
    "Indústria": "img-teal",
    "Distribuição": "img-teal",
}

AUTORES = {
    "Guilherme Walter": "Direção Estratégica · Governança & M&A",
    "Juliano Walter": "Performance Financeira",
    "Patrícia Misturini": "Pessoas & Liderança",
}

MESES_PT = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
            7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
MESES_FULL = {1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio",
              6: "junho", 7: "julho", 8: "agosto", 9: "setembro", 10: "outubro",
              11: "novembro", 12: "dezembro"}

NOINDEX_TAG = '<meta name="robots" content="noindex,nofollow"><!-- SCHEDULED:{date} -->\n'

# Hashtags por categoria — em letras minúsculas, sem acento
HASHTAGS_BY_CAT = {
    "Direção":      ["estrategia", "lideranca", "empresamedia", "direcao", "gestao"],
    "Performance":  ["fpa", "financascorporativas", "performancefinanceira", "empresamedia"],
    "Pessoas":      ["pessoas", "lideranca", "rh", "engajamento", "recrutamentoeselecao"],
    "Governança":   ["governancacorporativa", "conselhoconsultivo", "empresafamiliar"],
    "M&A":          ["fusoeseaquisicoes", "ma", "valuation", "middlemarket"],
    "Sucessão":     ["sucessao", "empresafamiliar", "governancafamiliar"],
    "Indústria":    ["industriabrasileira", "manufatura", "gestaoindustrial"],
    "Distribuição": ["distribuicao", "comerciob2b", "gestaocomercial"],
}
ATTO_TAGS = ["attoestrategias", "perspectivas"]

# ============================================================
# APP
# ============================================================
app = Flask(__name__, template_folder=str(STUDIO_DIR / "templates"),
            static_folder=str(STUDIO_DIR / "static"))


# ============================================================
# HELPERS — slugify, datas, pipeline
# ============================================================
def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80]


def today_brt() -> date:
    return datetime.now(timezone(timedelta(hours=-3))).date()


def fmt_date_human(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{int(d)} de {MESES_FULL[int(m)]} de {y}"


def fmt_date_card(iso: str) -> tuple[str, int]:
    y, m, d = iso.split("-")
    return MESES_PT[int(m)], int(y)


def load_data() -> list[dict]:
    if not DATA_JSON.exists():
        return []
    return json.loads(DATA_JSON.read_text(encoding="utf-8"))


def save_data(data: list[dict]) -> None:
    DATA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                         encoding="utf-8")


def load_scheduled() -> dict:
    if not SCHEDULED_JSON.exists():
        return {"_doc": "Registry do scheduler.", "scheduled": []}
    return json.loads(SCHEDULED_JSON.read_text(encoding="utf-8"))


def save_scheduled(reg: dict) -> None:
    SCHEDULED_JSON.write_text(json.dumps(reg, ensure_ascii=False, indent=2),
                              encoding="utf-8")


def source_path(slug: str) -> Path:
    """Caminho do arquivo de fonte markdown (preservado para edição)."""
    return SOURCES_DIR / f"{slug}.json"


def save_source(slug: str, body: str, sources: str = "") -> None:
    """Salva a fonte markdown do post para suportar edição posterior."""
    payload = {"slug": slug, "body": body, "sources": sources,
               "saved_at": datetime.now(timezone(timedelta(hours=-3))).isoformat()}
    source_path(slug).write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                  encoding="utf-8")


def load_source(slug: str) -> dict | None:
    """Carrega a fonte markdown do post se preservada.

    Para posts legados (sem source preservada), tenta extrair do HTML.
    Retorna None se não conseguir.
    """
    sp = source_path(slug)
    if sp.exists():
        try:
            return json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            pass
    # fallback: tentar reconstruir markdown a partir do HTML existente
    post_path = PERSPECTIVAS_DIR / f"{slug}.html"
    if not post_path.exists():
        return None
    html = post_path.read_text(encoding="utf-8")
    m = re.search(r'<div class="post-body">(.*?)</div>\s*(?:<div class="post-sources">|<div class="post-share">|<div class="post-footer">)',
                  html, re.DOTALL)
    if not m:
        return None
    inner = m.group(1)
    inner = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n', inner, flags=re.DOTALL)
    inner = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n', inner, flags=re.DOTALL)
    inner = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', inner, flags=re.DOTALL)
    inner = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', inner, flags=re.DOTALL)
    inner = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', inner, flags=re.DOTALL)
    inner = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', inner, flags=re.DOTALL)
    inner = re.sub(r'<[^>]+>', '', inner)
    body = inner.strip()
    # Sources
    sources = ""
    ms = re.search(r'<div class="post-sources">.*?<h2[^>]*>[^<]*</h2>(.*?)</div>', html, re.DOTALL)
    if ms:
        s = ms.group(1)
        s = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', s, flags=re.DOTALL)
        s = re.sub(r'<[^>]+>', '', s)
        sources = s.strip()
    return {"slug": slug, "body": body, "sources": sources, "fallback": True}


def delete_source(slug: str) -> None:
    """Remove a fonte markdown do post."""
    sp = source_path(slug)
    if sp.exists():
        try:
            sp.unlink()
        except Exception:
            pass


def post_status(slug: str, publish_date: str | None) -> str:
    """Retorna: published | scheduled | draft."""
    today = today_brt()
    post_path = PERSPECTIVAS_DIR / f"{slug}.html"
    if not post_path.exists():
        return "draft"
    if publish_date:
        pdate = datetime.strptime(publish_date, "%Y-%m-%d").date()
        if pdate > today:
            return "scheduled"
    # Verifica noindex
    html = post_path.read_text(encoding="utf-8")
    if "SCHEDULED:" in html:
        return "scheduled"
    return "published"


def first_paragraphs(body_md: str, n: int = 2) -> list[str]:
    """Extrai os N primeiros parágrafos do markdown, ignorando títulos H2/H3."""
    paragraphs: list[str] = []
    for block in body_md.strip().split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("#"):
            continue
        # remove inline markdown básico para o destino social
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", block)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = " ".join(text.split())
        paragraphs.append(text)
        if len(paragraphs) >= n:
            break
    return paragraphs


def social_copy(meta: dict, body_md: str) -> dict:
    """Gera texto pronto para LinkedIn (longo) e legenda Instagram (curta).

    Tudo determinístico. O usuário pode editar antes de postar.
    """
    titulo = meta["titulo"]
    titulo_curto = meta.get("titulo_curto") or titulo
    excerpt = meta.get("excerpt", "")
    slug = meta["slug"]
    author = meta.get("author", "")
    categoria = meta.get("categoria", "")
    url = f"https://www.gestaoatto.com.br/perspectivas/{slug}.html"

    paragraphs = first_paragraphs(body_md, n=2)
    para1 = paragraphs[0] if len(paragraphs) > 0 else excerpt
    para2 = paragraphs[1] if len(paragraphs) > 1 else ""

    cat_tags = HASHTAGS_BY_CAT.get(categoria, [])
    all_tags = cat_tags + ATTO_TAGS
    hashtags_line = " ".join(f"#{t}" for t in all_tags)

    # ---------- LinkedIn (long-form, profissional) ----------
    linkedin_lines = [titulo, ""]
    if para1:
        linkedin_lines.append(para1)
        linkedin_lines.append("")
    if para2:
        linkedin_lines.append(para2)
        linkedin_lines.append("")
    linkedin_lines.append(f"Texto completo: {url}")
    if author:
        linkedin_lines.append("")
        linkedin_lines.append(f"Por {author} · Atto Estratégias & Educação")
    linkedin_lines.append("")
    linkedin_lines.append(hashtags_line)
    linkedin_text = "\n".join(linkedin_lines).strip()

    # ---------- Instagram (curto, com pause visual) ----------
    instagram_lines = [titulo_curto, ""]
    if excerpt:
        # corta excerpt em ~220 chars para caber bem
        ex = excerpt if len(excerpt) <= 220 else excerpt[:217].rsplit(" ", 1)[0] + "..."
        instagram_lines.append(ex)
        instagram_lines.append("")
    instagram_lines.append("Leitura completa no link da bio.")
    instagram_lines.append("")
    instagram_lines.append("—")
    instagram_lines.append("")
    instagram_lines.append(hashtags_line)
    instagram_caption = "\n".join(instagram_lines).strip()

    return {
        "linkedin": linkedin_text,
        "instagram": instagram_caption,
        "url": url,
        "hashtags": hashtags_line,
    }


def merge_posts() -> list[dict]:
    """Combina perspectivas-data.json + scheduled_posts.json em uma lista
    única, deduplica por slug, anexa status."""
    data = load_data()
    scheduled = load_scheduled().get("scheduled", [])
    by_slug: dict[str, dict] = {p["slug"]: dict(p) for p in data}
    for s in scheduled:
        slug = s["slug"]
        if slug in by_slug:
            by_slug[slug]["publish_date"] = s.get("publish_date")
        else:
            by_slug[slug] = {
                "slug": slug,
                "titulo": s.get("h3", ""),
                "categoria": s.get("tag", ""),
                "data": s.get("publish_date", ""),
                "leitura": f"{s.get('minutes', '?')} min",
                "publish_date": s.get("publish_date"),
            }
    out = list(by_slug.values())
    for p in out:
        p["status"] = post_status(p["slug"], p.get("publish_date") or p.get("data"))
    out.sort(key=lambda p: (p.get("data") or p.get("publish_date") or ""), reverse=True)
    return out


def render_post_html(meta: dict, body_md: str, sources: str = "",
                     scheduled_for: str | None = None) -> str:
    """Renderiza HTML do post a partir do template + markdown body."""
    template = TEMPLATE_HTML.read_text(encoding="utf-8")
    body_html = md.markdown(body_md, extensions=["extra"]) if body_md else ""

    sources_block = ""
    if sources.strip():
        sources_html = md.markdown(sources, extensions=["extra"]) if sources else ""
        sources_block = (
            '<div class="post-sources">\n'
            '<h2>Fontes consultadas</h2>\n'
            f"{sources_html}\n"
            "</div>"
        )

    noindex_line = NOINDEX_TAG.format(date=scheduled_for) if scheduled_for else ""

    return template.format(
        TITLE=meta["titulo"],
        DESCRIPTION=meta.get("excerpt", ""),
        AUTHOR=meta["author"],
        AUTHOR_INITIAL=meta["author"][0].upper(),
        AUTHOR_AREA=AUTORES.get(meta["author"], meta.get("categoria", "")),
        SLUG=meta["slug"],
        DATE_ISO=meta["data"],
        DATE_HUMAN=fmt_date_human(meta["data"]),
        MINUTES=meta["minutes"],
        TAG_LABEL=meta["categoria"],
        CATEGORY=meta["categoria"],
        BODY_HTML=body_html,
        SOURCES_BLOCK=sources_block,
        NOINDEX_LINE=noindex_line,
    )


def run_capa(slug: str) -> tuple[bool, str]:
    """Executa scripts/capas.py --slug <slug> e retorna (ok, output)."""
    try:
        proc = subprocess.run(
            [sys.executable, str(CAPAS_PY), "--slug", slug],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        return proc.returncode == 0, (proc.stdout + proc.stderr).strip()
    except subprocess.TimeoutExpired:
        return False, "Timeout (60s) ao rodar capas.py"
    except Exception as e:
        return False, f"Erro: {e}"


def run_patch() -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            [sys.executable, str(PATCH_PY)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        return proc.returncode == 0, (proc.stdout + proc.stderr).strip()
    except Exception as e:
        return False, f"Erro: {e}"


def run_git(args: list[str]) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        return proc.returncode == 0, (proc.stdout + proc.stderr).strip()
    except Exception as e:
        return False, f"Erro: {e}"


# ============================================================
# ROUTES — páginas
# ============================================================
@app.route("/")
def page_new():
    """Form de criação ou edição de Perspectiva.

    Se receber ?edit=SLUG, carrega o post existente e renderiza em modo edição.
    """
    edit_slug = request.args.get("edit", "").strip()
    edit_data = None
    if edit_slug:
        data = load_data()
        post = next((p for p in data if p.get("slug") == edit_slug), None)
        if post:
            src = load_source(edit_slug) or {"body": "", "sources": ""}
            edit_data = {
                "slug": edit_slug,
                "numero": post.get("numero", ""),
                "titulo": post.get("titulo", ""),
                "titulo_curto": post.get("titulo_curto", ""),
                "categoria": post.get("categoria", ""),
                "data": post.get("data", ""),
                "minutes": int(re.sub(r"[^0-9]", "", post.get("leitura", "10 min")) or "10"),
                "excerpt": post.get("excerpt", ""),
                "body": src.get("body", ""),
                "sources": src.get("sources", ""),
                "fallback": src.get("fallback", False),
            }
    return render_template(
        "new.html",
        categorias=CATEGORIAS,
        tag_class=TAG_CLASS,
        autores=list(AUTORES.keys()),
        today=today_brt().isoformat(),
        edit_data=edit_data,
    )


@app.route("/posts")
def page_posts():
    return render_template("posts.html", posts=merge_posts())


@app.route("/agendamento")
def page_schedule():
    today = today_brt()
    return render_template(
        "schedule.html",
        posts=merge_posts(),
        today=today.isoformat(),
        meses_pt=MESES_FULL,
    )


# ============================================================
# ROUTES — API
# ============================================================
@app.post("/api/slug")
def api_slug():
    titulo = (request.json or {}).get("titulo", "")
    return jsonify({"slug": slugify(titulo)})


@app.post("/api/create")
def api_create():
    """Cria um post novo. Espera JSON com:
        titulo, titulo_curto?, categoria, data (YYYY-MM-DD),
        author, minutes, excerpt, body, sources?, scheduled (bool)
    Salva HTML, atualiza data.json e (se agendado) scheduled_posts.json,
    e dispara capas.py."""
    p = request.json or {}

    required = ["titulo", "categoria", "data", "author", "minutes", "excerpt", "body"]
    missing = [k for k in required if not p.get(k)]
    if missing:
        return jsonify({"ok": False, "error": f"Campos faltando: {', '.join(missing)}"}), 400

    slug = p.get("slug") or slugify(p["titulo"])
    titulo = p["titulo"].strip()
    titulo_curto = (p.get("titulo_curto") or titulo).strip()
    categoria = p["categoria"]
    data_iso = p["data"]
    author = p["author"]
    minutes = int(p["minutes"])
    excerpt = p["excerpt"].strip()
    body = p["body"]
    sources = p.get("sources", "")
    scheduled = bool(p.get("scheduled", False))

    # Validar data
    try:
        pdate = datetime.strptime(data_iso, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"ok": False, "error": "Data inválida (use YYYY-MM-DD)"}), 400

    is_future = pdate > today_brt()

    meta = {
        "slug": slug,
        "titulo": titulo,
        "titulo_curto": titulo_curto,
        "categoria": categoria,
        "data": data_iso,
        "minutes": minutes,
        "excerpt": excerpt,
        "author": author,
    }

    # 1) Renderiza e salva o HTML
    html = render_post_html(meta, body, sources,
                            scheduled_for=data_iso if (scheduled and is_future) else None)
    post_path = PERSPECTIVAS_DIR / f"{slug}.html"
    post_path.write_text(html, encoding="utf-8")

    # 1b) Preserva a fonte markdown para edição futura
    save_source(slug, body, sources)

    # 2) Atualiza perspectivas-data.json
    data = load_data()
    # Calcula próximo número
    numeros = [int(x.get("numero", 0)) for x in data]
    proximo = max(numeros) + 1 if numeros else 1
    # Remove entrada existente do mesmo slug (se já tinha) para não duplicar
    data = [x for x in data if x["slug"] != slug]
    data.insert(0, {
        "slug": slug,
        "numero": f"{proximo:02d}",
        "titulo": titulo,
        "titulo_curto": titulo_curto,
        "categoria": categoria,
        "data": data_iso,
        "excerpt": excerpt,
        "leitura": f"{minutes} min",
    })
    save_data(data)

    # 3) Se agendado pro futuro, adiciona em scheduled_posts.json também
    sched_msg = ""
    if scheduled and is_future:
        reg = load_scheduled()
        reg.setdefault("scheduled", [])
        reg["scheduled"] = [s for s in reg["scheduled"] if s["slug"] != slug]
        mes_label, ano = fmt_date_card(data_iso)
        reg["scheduled"].append({
            "slug": slug,
            "publish_date": data_iso,
            "tag": categoria,
            "tag_class": TAG_CLASS.get(categoria, "img-blue"),
            "minutes": minutes,
            "month": mes_label,
            "year": ano,
            "h3": titulo,
            "summary": excerpt,
            "author": f"Por {author}",
        })
        save_scheduled(reg)
        sched_msg = f"agendado para {data_iso}"

    # 4) Roda capas.py
    capa_ok, capa_log = run_capa(slug)

    # 5) Gera textos de redes sociais (LinkedIn + Instagram)
    social = social_copy(meta, body)

    return jsonify({
        "ok": True,
        "slug": slug,
        "scheduled": scheduled and is_future,
        "scheduled_msg": sched_msg,
        "capa_ok": capa_ok,
        "capa_log": capa_log,
        "post_path": str(post_path.relative_to(REPO_ROOT)),
        "social": social,
    })


@app.post("/api/generate-text")
def api_generate_text():
    """Gera o corpo do post em Markdown via Claude API.

    Espera no body JSON: titulo, excerpt, categoria, author, angle (opcional).
    Devolve { ok: true, body: <markdown> } ou { ok: false, error: <msg> }.
    """
    p = request.json or {}
    titulo = p.get("titulo", "").strip()
    excerpt = p.get("excerpt", "").strip()
    categoria = p.get("categoria", "").strip()
    author = p.get("author", "").strip()
    angle = p.get("angle", "").strip()

    if not titulo or not excerpt:
        return jsonify({"ok": False, "error": "Preencha pelo menos título e resumo antes de gerar."}), 400

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return jsonify({
            "ok": False,
            "error": "ANTHROPIC_API_KEY não configurada. Crie um arquivo "
                     "scripts/atto_studio/.env (use .env.example como base) "
                     "e cole sua chave de console.anthropic.com.",
        }), 400

    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5").strip()

    try:
        from anthropic import Anthropic
    except ImportError:
        return jsonify({"ok": False,
                        "error": "Pacote 'anthropic' não instalado. Rode: "
                                 "pip install --user anthropic python-dotenv"}), 500

    try:
        from prompt_atto import SYSTEM_PROMPT, build_user_prompt
    except ImportError as e:
        return jsonify({"ok": False, "error": f"prompt_atto.py não encontrado: {e}"}), 500

    user_prompt = build_user_prompt(titulo, excerpt, categoria, author, angle)

    try:
        client = Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        body_md = "".join(block.text for block in msg.content if hasattr(block, "text"))
        usage = {
            "input_tokens": msg.usage.input_tokens,
            "output_tokens": msg.usage.output_tokens,
        }
    except Exception as e:
        return jsonify({"ok": False, "error": f"Erro chamando Claude: {e}"}), 500

    # Defesa em profundidade: substitui qualquer travessão remanescente
    cleaned = body_md.replace("—", ",").replace("–", ",")

    return jsonify({
        "ok": True,
        "body": cleaned,
        "model": model,
        "usage": usage,
    })


@app.get("/api/social/<slug>")
def api_social(slug: str):
    """Regenera o copy de redes sociais para um post existente."""
    data = load_data()
    post = next((p for p in data if p["slug"] == slug), None)
    if not post:
        return jsonify({"ok": False, "error": "Post não encontrado em perspectivas-data.json"}), 404

    # tenta extrair body do HTML existente; se não der, usa só excerpt
    post_path = PERSPECTIVAS_DIR / f"{slug}.html"
    body = ""
    if post_path.exists():
        html = post_path.read_text(encoding="utf-8")
        m = re.search(r'<div class="post-body">(.*?)</div>\s*<div class="post-footer">',
                      html, re.DOTALL)
        if m:
            inner = m.group(1)
            # converte os parágrafos pra markdown-ish para reaproveitar first_paragraphs
            inner = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1', inner, flags=re.DOTALL)
            inner = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1', inner, flags=re.DOTALL)
            inner = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', inner, flags=re.DOTALL)
            inner = re.sub(r'<[^>]+>', '', inner)  # tira o que sobrou de tags
            body = inner

    meta = {
        "slug": slug,
        "titulo": post.get("titulo", ""),
        "titulo_curto": post.get("titulo_curto", ""),
        "excerpt": post.get("excerpt", ""),
        "categoria": post.get("categoria", ""),
        "author": "",
    }
    return jsonify({"ok": True, "social": social_copy(meta, body)})


@app.post("/api/run-patch")
def api_run_patch():
    ok, log = run_patch()
    return jsonify({"ok": ok, "log": log})


@app.post("/api/run-capa/<slug>")
def api_run_capa(slug: str):
    ok, log = run_capa(slug)
    return jsonify({"ok": ok, "log": log})


@app.post("/api/git-commit-push")
def api_git_commit_push():
    """Faz add/commit/push do estado atual."""
    msg = (request.json or {}).get("message", "publish: atualizado via Atto Studio")
    ok1, l1 = run_git(["add", "."])
    if not ok1:
        return jsonify({"ok": False, "step": "add", "log": l1}), 500
    ok2, l2 = run_git(["commit", "-m", msg])
    if not ok2 and "nothing to commit" not in l2:
        return jsonify({"ok": False, "step": "commit", "log": l2}), 500
    ok3, l3 = run_git(["push", "origin", "main"])
    return jsonify({
        "ok": ok3,
        "log": "\n".join([f"$ git add .\n{l1}",
                          f"$ git commit -m '{msg}'\n{l2}",
                          f"$ git push origin main\n{l3}"]),
    })


@app.get("/api/capa/<slug>/<format>")
def api_capa(slug: str, format: str):
    """Devolve o PNG de uma capa."""
    if format not in ("hero", "og", "ig-feed", "ig-story"):
        return "Format inválido", 400
    path = CAPAS_DIR / f"{slug}_{format}.png"
    if not path.exists():
        return "Não gerado ainda", 404
    return send_file(path, mimetype="image/png")


@app.get("/api/posts")
def api_posts():
    return jsonify(merge_posts())


# ============================================================
# ROUTES — gerenciamento avançado (v2)
# ============================================================
@app.post("/api/delete/<slug>")
def api_delete(slug: str):
    """Apaga completamente um post: HTML, capas (4), entradas em JSON e fonte."""
    data = load_data()
    post = next((p for p in data if p.get("slug") == slug), None)
    if not post:
        return jsonify({"ok": False, "error": "Post não encontrado."}), 404

    removed = []
    # 1) HTML
    post_path = PERSPECTIVAS_DIR / f"{slug}.html"
    if post_path.exists():
        try:
            post_path.unlink()
            removed.append(post_path.name)
        except Exception as e:
            return jsonify({"ok": False, "error": f"Falha ao remover HTML: {e}"}), 500

    # 2) Capas (4 variantes)
    for variant in ("hero", "og", "ig-feed", "ig-story"):
        cp = CAPAS_DIR / f"{slug}_{variant}.png"
        if cp.exists():
            try:
                cp.unlink()
                removed.append(cp.name)
            except Exception:
                pass

    # 3) perspectivas-data.json
    new_data = [p for p in data if p.get("slug") != slug]
    save_data(new_data)

    # 4) scheduled_posts.json
    reg = load_scheduled()
    reg["scheduled"] = [s for s in reg.get("scheduled", []) if s.get("slug") != slug]
    save_scheduled(reg)

    # 5) Fonte markdown
    delete_source(slug)
    removed.append(f"sources/{slug}.json")

    return jsonify({
        "ok": True,
        "slug": slug,
        "removed_files": removed,
        "numero": post.get("numero"),
        "message": f"Post #{post.get('numero')} ({slug}) removido. {len(removed)} arquivos apagados.",
    })


@app.post("/api/edit/<slug>")
def api_edit(slug: str):
    """Edita um post existente. Aceita qualquer subconjunto dos campos:
    titulo, titulo_curto, categoria, data, author, minutes, excerpt, body, sources.
    Preserva o número original da Perspectiva.
    Re-renderiza HTML, atualiza JSONs e regenera capa.
    """
    p = request.json or {}
    data = load_data()
    post = next((x for x in data if x.get("slug") == slug), None)
    if not post:
        return jsonify({"ok": False, "error": "Post não encontrado."}), 404

    # Carrega fonte atual para usar como base
    src = load_source(slug) or {"body": "", "sources": ""}

    # Campos atualizáveis (com fallback para o valor atual)
    titulo = (p.get("titulo") or post.get("titulo", "")).strip()
    titulo_curto = (p.get("titulo_curto") or post.get("titulo_curto") or titulo).strip()
    categoria = p.get("categoria") or post.get("categoria", "")
    data_iso = p.get("data") or post.get("data", "")
    author = p.get("author") or post.get("author", "")
    minutes_raw = p.get("minutes", post.get("leitura", "10 min"))
    if isinstance(minutes_raw, str):
        minutes = int(re.sub(r"[^0-9]", "", minutes_raw) or "10")
    else:
        minutes = int(minutes_raw)
    excerpt = (p.get("excerpt") or post.get("excerpt", "")).strip()
    body = p.get("body") if p.get("body") is not None else src.get("body", "")
    sources = p.get("sources") if p.get("sources") is not None else src.get("sources", "")

    # Valida data
    try:
        pdate = datetime.strptime(data_iso, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"ok": False, "error": "Data inválida (use YYYY-MM-DD)."}), 400
    is_future = pdate > today_brt()

    meta = {
        "slug": slug,
        "titulo": titulo,
        "titulo_curto": titulo_curto,
        "categoria": categoria,
        "data": data_iso,
        "minutes": minutes,
        "excerpt": excerpt,
        "author": author,
    }

    # 1) Re-renderiza HTML
    html = render_post_html(meta, body, sources,
                            scheduled_for=data_iso if is_future else None)
    post_path = PERSPECTIVAS_DIR / f"{slug}.html"
    post_path.write_text(html, encoding="utf-8")

    # 1b) Atualiza fonte preservada
    save_source(slug, body, sources)

    # 2) Atualiza perspectivas-data.json PRESERVANDO o numero
    numero = post.get("numero")
    new_data = [x for x in data if x.get("slug") != slug]
    new_entry = {
        "slug": slug,
        "numero": numero,
        "titulo": titulo,
        "titulo_curto": titulo_curto,
        "categoria": categoria,
        "data": data_iso,
        "excerpt": excerpt,
        "leitura": f"{minutes} min",
    }
    # Mantém ordem por número desc
    new_data.append(new_entry)
    new_data.sort(key=lambda x: int(x.get("numero", 0)), reverse=True)
    save_data(new_data)

    # 3) Atualiza scheduled_posts.json se for futuro
    reg = load_scheduled()
    reg.setdefault("scheduled", [])
    reg["scheduled"] = [s for s in reg["scheduled"] if s.get("slug") != slug]
    if is_future:
        mes_label, ano = fmt_date_card(data_iso)
        reg["scheduled"].append({
            "slug": slug,
            "publish_date": data_iso,
            "tag": categoria,
            "tag_class": TAG_CLASS.get(categoria, "img-blue"),
            "minutes": minutes,
            "month": mes_label,
            "year": ano,
            "h3": titulo,
            "summary": excerpt,
            "author": f"Por {author}",
        })
    save_scheduled(reg)

    # 4) Regenera capa (título/data/categoria/minutos podem ter mudado)
    capa_ok, capa_log = run_capa(slug)

    # 5) Re-aplica patch_posts.py para reinjetar hero+share (capa pode ter mudado)
    patch_ok, patch_log = run_patch()

    return jsonify({
        "ok": True,
        "slug": slug,
        "numero": numero,
        "scheduled": is_future,
        "capa_ok": capa_ok,
        "patch_ok": patch_ok,
        "message": f"Post #{numero} atualizado.",
    })


@app.post("/api/reschedule/<slug>")
def api_reschedule(slug: str):
    """Muda só a data de publicação. Regenera capa e atualiza HTML."""
    p = request.json or {}
    new_date = (p.get("data") or p.get("new_date") or "").strip()
    try:
        pdate = datetime.strptime(new_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"ok": False, "error": "Data inválida (use YYYY-MM-DD)."}), 400

    data = load_data()
    post = next((x for x in data if x.get("slug") == slug), None)
    if not post:
        return jsonify({"ok": False, "error": "Post não encontrado."}), 404
    post["data"] = new_date

    # Atualiza scheduled_posts.json
    is_future = pdate > today_brt()
    reg = load_scheduled()
    reg.setdefault("scheduled", [])
    reg["scheduled"] = [s for s in reg["scheduled"] if s.get("slug") != slug]
    if is_future:
        mes_label, ano = fmt_date_card(new_date)
        reg["scheduled"].append({
            "slug": slug,
            "publish_date": new_date,
            "tag": post.get("categoria", ""),
            "tag_class": TAG_CLASS.get(post.get("categoria", ""), "img-blue"),
            "minutes": int(re.sub(r"[^0-9]", "", post.get("leitura", "10 min")) or "10"),
            "month": mes_label,
            "year": ano,
            "h3": post.get("titulo", ""),
            "summary": post.get("excerpt", ""),
            "author": "",
        })
    save_scheduled(reg)
    save_data(data)

    # Atualiza datas no HTML
    post_path = PERSPECTIVAS_DIR / f"{slug}.html"
    if post_path.exists():
        html = post_path.read_text(encoding="utf-8")
        human = fmt_date_human(new_date)
        html = re.sub(r'(article:published_time" content=")[^"]+(")', rf'\g<1>{new_date}\g<2>', html)
        html = re.sub(r'(datetime=")[^"]+(")', rf'\g<1>{new_date}\g<2>', html)
        html = re.sub(r'("datePublished"\s*:\s*")[^"]+(")', rf'\g<1>{new_date}\g<2>', html)
        # SCHEDULED marker
        if is_future:
            if "SCHEDULED:" in html:
                html = re.sub(r'(SCHEDULED:)[^\s<>-]+', rf'\g<1>{new_date}', html)
            else:
                html = NOINDEX_TAG.format(date=new_date) + html
        else:
            html = re.sub(r'<meta name="robots" content="noindex,nofollow"><!-- SCHEDULED:[^\s<>-]+ -->\n?', '', html)
        # Data humana (substitui só a primeira ocorrência, evita estragar conteúdo)
        old_human = re.compile(r'\d{1,2}\s+de\s+(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+\d{4}', re.IGNORECASE)
        html = old_human.sub(human, html, count=1)
        post_path.write_text(html, encoding="utf-8")

    # Regenera capa (data aparece no rodapé da capa)
    capa_ok, _ = run_capa(slug)

    return jsonify({
        "ok": True,
        "slug": slug,
        "new_date": new_date,
        "is_future": is_future,
        "capa_ok": capa_ok,
        "message": f"Post #{post.get('numero')} reagendado para {new_date}.",
    })


@app.post("/api/publish-now/<slug>")
def api_publish_now(slug: str):
    """Força publicação imediata: remove noindex, ajusta data para hoje,
    remove do scheduled_posts.json."""
    data = load_data()
    post = next((x for x in data if x.get("slug") == slug), None)
    if not post:
        return jsonify({"ok": False, "error": "Post não encontrado."}), 404

    today_iso = today_brt().isoformat()
    post["data"] = today_iso
    save_data(data)

    # Remove do scheduled
    reg = load_scheduled()
    reg["scheduled"] = [s for s in reg.get("scheduled", []) if s.get("slug") != slug]
    save_scheduled(reg)

    # Remove noindex e ajusta data no HTML
    post_path = PERSPECTIVAS_DIR / f"{slug}.html"
    if post_path.exists():
        html = post_path.read_text(encoding="utf-8")
        html = re.sub(r'<meta name="robots" content="noindex,nofollow"><!-- SCHEDULED:[^\s<>-]+ -->\n?', '', html)
        html = re.sub(r'(article:published_time" content=")[^"]+(")', rf'\g<1>{today_iso}\g<2>', html)
        html = re.sub(r'("datePublished"\s*:\s*")[^"]+(")', rf'\g<1>{today_iso}\g<2>', html)
        old_human = re.compile(r'\d{1,2}\s+de\s+(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+\d{4}', re.IGNORECASE)
        html = old_human.sub(fmt_date_human(today_iso), html, count=1)
        post_path.write_text(html, encoding="utf-8")

    # Regenera capa com nova data
    run_capa(slug)

    return jsonify({
        "ok": True,
        "slug": slug,
        "published_at": today_iso,
        "message": f"Post #{post.get('numero')} publicado agora.",
    })


@app.post("/api/duplicate-check")
def api_duplicate_check():
    """Recebe {titulo, excerpt, body?} e retorna até 5 posts existentes
    mais similares por tokens compartilhados. Ajuda a evitar canibalização.
    """
    p = request.json or {}
    titulo = (p.get("titulo") or "").lower()
    excerpt = (p.get("excerpt") or "").lower()
    body = (p.get("body") or "").lower()
    query = f"{titulo} {titulo} {excerpt} {body}"  # peso 2 no título

    # Tokeniza removendo stopwords PT comuns
    STOP = {"a","o","as","os","de","do","da","dos","das","e","ou","que","para","por","com","em","no","na","nos","nas","um","uma","uns","umas","se","ser","ter","mais","menos","ao","aos","à","às","é","é","sua","seu","suas","seus","esse","essa","esses","essas","este","esta","estes","estas","isso","isto","como","quando","onde","ele","ela","eles","elas","minha","minhas","meu","meus","muito","muita","muitos","muitas"}
    def tokenize(text: str) -> set[str]:
        words = re.findall(r"[a-zA-Záàâãéêíóôõúçñ]{4,}", text.lower())
        return {w for w in words if w not in STOP}

    qtokens = tokenize(query)
    if not qtokens:
        return jsonify({"ok": True, "similar": []})

    results = []
    for post in load_data():
        ptext = f"{post.get('titulo','')} {post.get('titulo','')} {post.get('excerpt','')}"
        # também carrega corpo se tiver fonte
        src = load_source(post.get("slug", ""))
        if src:
            ptext += " " + (src.get("body") or "")[:2000]
        ptokens = tokenize(ptext)
        if not ptokens:
            continue
        inter = qtokens & ptokens
        union = qtokens | ptokens
        jaccard = len(inter) / len(union) if union else 0
        if jaccard > 0.05:
            results.append({
                "numero": post.get("numero"),
                "slug": post.get("slug"),
                "titulo": post.get("titulo"),
                "categoria": post.get("categoria"),
                "data": post.get("data"),
                "similarity": round(jaccard, 3),
                "shared_words": sorted(inter, key=lambda x: -len(x))[:10],
            })
    results.sort(key=lambda x: -x["similarity"])
    top = results[:5]
    risk = "alto" if top and top[0]["similarity"] > 0.25 else ("medio" if top and top[0]["similarity"] > 0.12 else "baixo")
    return jsonify({"ok": True, "similar": top, "risk": risk})


@app.post("/api/seo-score")
def api_seo_score():
    """Avalia o SEO de um post. Aceita {titulo, excerpt, body, slug} no JSON.
    Retorna nota 0-100 + checklist com hint específico para cada falha.
    """
    p = request.json or {}
    titulo = (p.get("titulo") or "").strip()
    excerpt = (p.get("excerpt") or "").strip()
    body = (p.get("body") or "").strip()
    slug = (p.get("slug") or "").strip()

    checks = []
    def add(name, passed, weight, hint=""):
        checks.append({"name": name, "passed": passed, "weight": weight, "hint": hint if not passed else ""})

    # 1. Título
    add("Título tem 30-80 caracteres", 30 <= len(titulo) <= 80, 10,
        f"Atual: {len(titulo)}. Ideal entre 30 e 80 para Google.")
    add("Título termina com ponto", titulo.endswith(".") if titulo else False, 5,
        "Padrão Atto: título termina com ponto final.")
    add("Título tem dois pontos (estrutura tema: ângulo)", ":" in titulo, 5,
        "Padrão Atto: 'tema: ângulo do artigo.'")

    # 2. Slug
    slug_ok = bool(re.match(r"^[a-z0-9-]{10,70}$", slug))
    add("Slug entre 10-70 chars, kebab-case", slug_ok, 8,
        f"Atual: '{slug}' ({len(slug)} chars). Use kebab-case 10-70 chars.")

    # 3. Excerpt
    add("Excerpt tem 80-220 caracteres", 80 <= len(excerpt) <= 220, 10,
        f"Atual: {len(excerpt)}. Ideal entre 80-220 para meta-description.")

    # 4. Corpo
    word_count = len(body.split())
    add("Corpo tem 800-3000 palavras", 800 <= word_count <= 3000, 12,
        f"Atual: {word_count} palavras. Padrão Atto: 800-3000.")
    add("Tem pelo menos 3 H2", body.count("\n## ") >= 3, 10,
        f"Atual: {body.count(chr(10) + '## ')}. Recomendado: 3-7 H2.")
    add("Tem pelo menos 1 H3", body.count("\n### ") >= 1, 5,
        "Adicionar pelo menos um H3 para estrutura.")

    # 5. Parágrafos
    paragraphs = [b for b in body.split("\n\n") if b.strip() and not b.strip().startswith("#")]
    long_paragraphs = [p for p in paragraphs if len(p.split()) > 120]
    add("Sem parágrafos com >120 palavras", len(long_paragraphs) == 0, 8,
        f"{len(long_paragraphs)} parágrafo(s) com >120 palavras. Quebre para leitura.")

    # 6. Sem listas-bala agressivas (padrão Atto: usar H3 em vez de bullets longos)
    bullet_count = sum(1 for line in body.split("\n") if re.match(r"^\s*[-*]\s", line))
    add("Uso moderado de listas-bala (<= 8)", bullet_count <= 8, 5,
        f"{bullet_count} bullets. Padrão Atto usa H3 em vez de listas longas.")

    # 7. Sem CTAs comerciais
    cta_words = ["fale conosco", "agende uma", "marque uma conversa", "entre em contato", "saiba mais"]
    has_cta = any(w in body.lower() for w in cta_words)
    add("Sem CTA comercial agressivo", not has_cta, 6,
        "Padrão Atto: encerrar em 'Como a Atto conduz', observacional, não vendedor.")

    # 8. Tom em terceira pessoa (heurística)
    voce_count = len(re.findall(r"\bvoc[êe]\b", body, re.IGNORECASE))
    add("Tom em terceira pessoa (poucos 'você')", voce_count <= 3, 6,
        f"{voce_count} ocorrências de 'você'. Padrão Atto usa 'a empresa', 'o sócio'.")

    # 9. Encerramento padrão Atto
    has_como_atto = "## Como a Atto" in body or "## O que a Atto" in body
    add("Tem seção de encerramento padrão Atto", has_como_atto, 5,
        "Adicionar '## Como a Atto conduz' ou '## O que a Atto observa em campo'.")

    # 10. Sem emojis
    has_emoji = bool(re.search(r"[\U0001F300-\U0001FAFF]", body))
    add("Sem emojis no corpo", not has_emoji, 5,
        "Padrão Atto: sem emojis no corpo do artigo.")

    score = sum(c["weight"] for c in checks if c["passed"])
    total = sum(c["weight"] for c in checks)
    return jsonify({
        "ok": True,
        "score": round(score / total * 100) if total else 0,
        "max": 100,
        "passed": sum(1 for c in checks if c["passed"]),
        "total_checks": len(checks),
        "checks": checks,
    })


@app.post("/api/brand-voice-check")
def api_brand_voice_check():
    """Validação leve de tom Atto sem chamar API externa (rápido e offline).
    Para validação profunda use a skill brand-voice:enforce-voice via Cowork.
    """
    p = request.json or {}
    body = p.get("body", "")
    issues = []

    # Travessões — proibido no padrão Atto
    if "—" in body or "–" in body:
        n = body.count("—") + body.count("–")
        issues.append({"severity": "high", "rule": "Sem travessões (—/–)",
                       "hint": f"{n} travessão(ões) encontrado(s). Use vírgula ou ponto."})

    # Aspas inglesas “ ” em vez de portuguesas
    if "“" in body or "”" in body:
        issues.append({"severity": "low", "rule": "Aspas portuguesas",
                       "hint": "Use aspas duplas \"\" em vez de “ ”."})

    # Clichês banidos
    cliches = ["pensar fora da caixa", "ganha-ganha", "sinergia", "alavancar resultados",
               "estourar a curva", "fazer a diferença", "transforma vidas"]
    for c in cliches:
        if c in body.lower():
            issues.append({"severity": "high", "rule": "Clichê banido",
                           "hint": f"Remover '{c}' — clichê fora do padrão Atto."})

    # Muito advérbio em -mente
    mente_count = len(re.findall(r"\b\w+mente\b", body, re.IGNORECASE))
    if mente_count > 8:
        issues.append({"severity": "medium", "rule": "Advérbios em -mente",
                       "hint": f"{mente_count} advérbios em -mente. Reduza para abaixo de 8."})

    # Tom de marketing
    marketing_words = ["incrível", "revolucionário", "imperdível", "sensacional", "fantástico", "extraordinário"]
    found_marketing = [w for w in marketing_words if w in body.lower()]
    if found_marketing:
        issues.append({"severity": "high", "rule": "Tom de marketing",
                       "hint": f"Palavras vendedoras encontradas: {', '.join(found_marketing)}."})

    score = max(0, 100 - sum({"high": 15, "medium": 8, "low": 3}.get(i["severity"], 5) for i in issues))
    return jsonify({"ok": True, "voice_score": score, "issues": issues})


@app.get("/api/preview/<slug>")
def api_preview(slug: str):
    """Serve o HTML renderizado do post para preview local."""
    post_path = PERSPECTIVAS_DIR / f"{slug}.html"
    if not post_path.exists():
        return "Post não encontrado", 404
    html = post_path.read_text(encoding="utf-8")
    # Reescreve caminhos relativos para o Atto Studio servir
    html = html.replace('href="../assets/', 'href="/preview-asset/')
    html = html.replace('src="../assets/', 'src="/preview-asset/')
    return html


@app.get("/preview-asset/<path:asset_path>")
def preview_asset(asset_path: str):
    """Serve qualquer asset estático do site para o preview funcionar."""
    asset = SITE / "assets" / asset_path
    if not asset.exists():
        return "Asset não encontrado", 404
    mimes = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
             ".svg": "image/svg+xml", ".css": "text/css", ".js": "application/javascript",
             ".woff": "font/woff", ".woff2": "font/woff2"}
    mime = mimes.get(asset.suffix.lower(), "application/octet-stream")
    return send_file(asset, mimetype=mime)


@app.get("/api/source/<slug>")
def api_source(slug: str):
    """Retorna a fonte markdown preservada (ou reconstruída) de um post."""
    src = load_source(slug)
    if not src:
        return jsonify({"ok": False, "error": "Fonte não encontrada"}), 404
    data = load_data()
    post = next((p for p in data if p.get("slug") == slug), None) or {}
    return jsonify({"ok": True, "source": src, "meta": post})


@app.get("/api/health")
def api_health():
    return jsonify({"ok": True, "today": today_brt().isoformat(),
                    "data_count": len(load_data()),
                    "scheduled_count": len(load_scheduled().get("scheduled", []))})


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    port = int(os.environ.get("ATTO_STUDIO_PORT", "8765"))
    print(f"\n┌─────────────────────────────────────────────────┐")
    print(f"│  Atto Studio · Perspectivas                     │")
    print(f"│  http://127.0.0.1:{port}                            │")
    print(f"│  Ctrl+C pra parar                               │")
    print(f"└─────────────────────────────────────────────────┘\n")
    app.run(host="127.0.0.1", port=port, debug=False)
