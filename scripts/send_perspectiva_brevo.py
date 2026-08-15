#!/usr/bin/env python3
"""
send_perspectiva_brevo.py <slug>

Envia a newsletter de uma Perspectiva recém publicada para a lista
"Perspectivas Atto" (List ID 3) via API do Brevo, no design da Atto.

Idempotente: mantém scripts/newsletter_sent.json com os slugs já enviados.
Se o slug já foi enviado, não reenvia.

Requer a variável de ambiente BREVO_API_KEY (segredo do repositório).

Uso:
  python3 scripts/send_perspectiva_brevo.py fim-orcamento-anual-forecast-continuo-empresa-media

Saída:
  - "Sent: <slug> (campaign <id>)" em caso de envio
  - "Already sent: <slug>" se já constava no registro
  - exit 0 em sucesso ou no-op; exit != 0 em erro de API
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE = REPO_ROOT / "site"
DATA_JSON = SITE / "perspectivas-data.json"
SENT_REGISTRY = REPO_ROOT / "scripts" / "newsletter_sent.json"

BASE = "https://www.gestaoatto.com.br"
LIST_ID = 3
SENDER = {"name": "Perspectivas Atto", "email": "perspectivas@gestaoatto.com.br"}
REPLY_TO = {"email": "contato@gestaoatto.com.br", "name": "Atto Estratégias"}
API = "https://api.brevo.com/v3"

AUTOR_POR_CATEGORIA = {
    "Performance": "Juliano Walter",
    "Indústria": "Juliano Walter",
    "Distribuição": "Juliano Walter",
    "Pessoas": "Patrícia Misturini",
    "Direção": "Guilherme Walter",
    "Governança": "Guilherme Walter",
    "M&A": "Guilherme Walter",
    "Sucessão": "Guilherme Walter",
}

EMAIL_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR" xmlns="http://www.w3.org/1999/xhtml"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge"><title>Perspectivas Atto</title>
<!--[if mso]><style>table,td,div,p,a{font-family:Arial,Helvetica,sans-serif !important;}</style><![endif]-->
</head><body style="margin:0;padding:0;background:#F4F2EC;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">__EXCERPT__</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F4F2EC;"><tr>
<td align="center" style="padding:28px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:600px;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #E2DDD2;">
<tr><td align="center" style="background:#080F1E;padding:22px 24px;">
<img src="https://www.gestaoatto.com.br/assets/atto_logo_dark.png" width="132" alt="Atto Estrategias" style="display:block;border:0;width:132px;height:auto;"></td></tr>
<tr><td style="height:4px;background:#00B5B8;line-height:4px;font-size:0;">&nbsp;</td></tr>
<tr><td style="padding:26px 34px 0 34px;font-family:'Courier New',monospace;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#00857F;">Perspectiva __NUMERO__ &nbsp;&middot;&nbsp; __CATEGORIA__ &nbsp;&middot;&nbsp; __LEITURA__ de leitura</td></tr>
<tr><td style="padding:14px 34px 0 34px;font-family:'Helvetica Neue',Arial,sans-serif;font-size:27px;line-height:1.22;font-weight:700;color:#0A0E1A;letter-spacing:-0.5px;">__TITULO__</td></tr>
<tr><td style="padding:22px 34px 0 34px;"><img src="__HERO__" width="532" alt="" style="display:block;border:0;width:100%;height:auto;border-radius:8px;"></td></tr>
<tr><td style="padding:22px 34px 0 34px;font-family:'Helvetica Neue',Arial,sans-serif;font-size:16px;line-height:1.7;color:#3A3F4A;">__EXCERPT__</td></tr>
<tr><td style="padding:26px 34px 4px 34px;"><table role="presentation" cellpadding="0" cellspacing="0"><tr>
<td align="center" bgcolor="#1A3A8F" style="border-radius:8px;"><a href="__LINK__" style="display:inline-block;padding:15px 30px;font-family:'Helvetica Neue',Arial,sans-serif;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:8px;">Ler a Perspectiva &nbsp;&rarr;</a></td>
</tr></table></td></tr>
<tr><td style="padding:16px 34px 30px 34px;font-family:'Helvetica Neue',Arial,sans-serif;font-size:14px;color:#6B6F7A;border-bottom:1px solid #E2DDD2;">Por __AUTOR__ &nbsp;&middot;&nbsp; Atto Estrategias &amp; Educacao</td></tr>
<tr><td style="padding:26px 34px 30px 34px;background:#0C1733;">
<div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;line-height:1.7;color:#B9C0CC;"><strong style="color:#ffffff;">Perspectivas Atto</strong><br>Direcao, Financas, Pessoas e M&amp;A para empresas que crescem com metodo.</div>
<div style="font-family:'Courier New',monospace;font-size:11px;letter-spacing:1px;color:#7E8796;padding-top:16px;">
<a href="https://www.linkedin.com/company/gestaoatto" style="color:#2FE0D6;text-decoration:none;">LinkedIn</a> &nbsp;&middot;&nbsp;
<a href="https://www.instagram.com/gestaoatto" style="color:#2FE0D6;text-decoration:none;">Instagram</a> &nbsp;&middot;&nbsp;
<a href="https://www.gestaoatto.com.br/perspectivas.html?utm_source=brevo&amp;utm_medium=email&amp;utm_campaign=__CAMPANHA__&amp;utm_content=rodape" style="color:#2FE0D6;text-decoration:none;">Todas as Perspectivas</a></div>
<div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;line-height:1.6;color:#6B7280;padding-top:18px;">Atto Estrategias &amp; Educacao &middot; Caxias do Sul / RS<br>Voce recebe este e-mail porque assinou as Perspectivas Atto. <a href="{{ unsubscribe }}" style="color:#9AA3B2;text-decoration:underline;">Cancelar inscricao</a>.</div>
</td></tr>
</table></td></tr></table></body></html>"""


def load_entry(slug: str) -> dict:
    data = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    for e in data:
        if e.get("slug") == slug:
            return e
    raise SystemExit(f"Slug nao encontrado em perspectivas-data.json: {slug}")


def load_sent() -> list:
    if SENT_REGISTRY.exists():
        try:
            return json.loads(SENT_REGISTRY.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_sent(sent: list) -> None:
    SENT_REGISTRY.write_text(json.dumps(sent, ensure_ascii=False, indent=2), encoding="utf-8")


def build_html(e: dict) -> str:
    autor = (e.get("autor") or "").replace("Por ", "").strip()
    if not autor:
        autor = AUTOR_POR_CATEGORIA.get(e.get("categoria", ""), "Atto Estrategias")
    # Prefere a capa do Instagram (com o rosto do autor, mais humanizada);
    # cai para a hero 16:9 quando a capa de IG ainda nao foi gerada.
    capas = SITE / "assets" / "capas"
    if (capas / f"{e['slug']}_ig-feed.png").exists():
        hero = f"{BASE}/assets/capas/{e['slug']}_ig-feed.png"
    else:
        hero = f"{BASE}/assets/capas/{e['slug']}_hero.png"
    # Links com UTM (convenção em docs/UTM.md): a newsletter aparece no GA4
    # como brevo / email / perspectiva-NN em vez de "referral sendibm3.com".
    campanha = f"perspectiva-{e.get('numero', '')}".rstrip("-") or "perspectiva"
    utm = f"utm_source=brevo&utm_medium=email&utm_campaign={campanha}"
    link = f"{BASE}/perspectivas/{e['slug']}.html?{utm}&utm_content=cta-ler"
    html = EMAIL_TEMPLATE
    repl = {
        "__NUMERO__": str(e.get("numero", "")),
        "__CATEGORIA__": e.get("categoria", ""),
        "__LEITURA__": e.get("leitura", ""),
        "__TITULO__": e.get("titulo", ""),
        "__EXCERPT__": e.get("excerpt", ""),
        "__HERO__": hero,
        "__LINK__": link,
        "__CAMPANHA__": campanha,
        "__AUTOR__": autor,
    }
    for k, v in repl.items():
        html = html.replace(k, v)
    return html


def api_post(path: str, key: str, payload: dict | None):
    url = f"{API}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else b""
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("api-key", key)
    req.add_header("content-type", "application/json")
    req.add_header("accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as ex:
        raise SystemExit(f"Erro da API Brevo ({ex.code}) em {path}: {ex.read().decode('utf-8', 'ignore')}")


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: send_perspectiva_brevo.py <slug>", file=sys.stderr)
        return 2
    slug = sys.argv[1].strip()

    key = os.environ.get("BREVO_API_KEY")
    if not key:
        raise SystemExit("BREVO_API_KEY nao definido no ambiente.")

    sent = load_sent()
    if slug in sent:
        print(f"Already sent: {slug}")
        return 0

    e = load_entry(slug)
    html = build_html(e)
    subject = e.get("titulo") or "Nova Perspectiva Atto"

    campaign = {
        "name": f"Perspectiva {e.get('numero','')} - {slug}",
        "subject": subject,
        "sender": SENDER,
        "replyTo": REPLY_TO["email"],
        "type": "classic",
        "htmlContent": html,
        "recipients": {"listIds": [LIST_ID]},
    }
    status, res = api_post("/emailCampaigns", key, campaign)
    cid = res.get("id")
    if not cid:
        raise SystemExit(f"Nao recebeu id de campanha do Brevo: {status} {res}")

    api_post(f"/emailCampaigns/{cid}/sendNow", key, None)

    sent.append(slug)
    save_sent(sent)
    print(f"Sent: {slug} (campaign {cid})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
