#!/usr/bin/env python3
"""Radar Atto no GitHub Actions: aprovação por issue e publicação no Instagram.

  python3 radar/radar_gh.py abrir AAAA-MM-DD     -> abre a issue de aprovação com as 3 artes
  python3 radar/radar_gh.py publicar AAAA-MM-DD  -> às 07:20 confere a aprovação e publica
  python3 radar/radar_gh.py renovar              -> renova o token do Instagram e atualiza o secret

Variáveis: GITHUB_TOKEN, GITHUB_REPOSITORY, IG_ACCESS_TOKEN, IG_USER_ID, RADAR_GH_TOKEN (só p/ renovar).
Aprovação: comentário do dono do repositório contendo "aprovado". "não publicar" cancela.
"""
import base64, datetime, json, os, sys, time, unicodedata, urllib.parse, urllib.request, urllib.error

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("GITHUB_REPOSITORY", "guiwalter87/gestaoatto")
SITE = "https://www.gestaoatto.com.br/radar"
GRAPH = "https://graph.instagram.com/v23.0"
BRT = datetime.timezone(datetime.timedelta(hours=-3))
ROTULO = "radar-aprovacao"


def http(metodo, url, dados=None, headers=None, form=False, tentativas=3):
    h = dict(headers or {})
    corpo = None
    if dados is not None:
        if form:
            corpo = urllib.parse.urlencode(dados).encode()
        else:
            corpo = json.dumps(dados).encode()
            h["Content-Type"] = "application/json"
    for t in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, corpo, h, method=metodo), timeout=60) as r:
                txt = r.read().decode()
                return json.loads(txt) if txt.strip() else {}
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:400]
            if e.code >= 500 and t < tentativas - 1:
                time.sleep(8)
                continue
            raise RuntimeError(f"HTTP {e.code} {url.split('?')[0]}: {msg}")


def gh(metodo, caminho, dados=None, token=None):
    return http(metodo, f"https://api.github.com/repos/{REPO}{caminho}", dados,
                {"Authorization": "Bearer " + (token or os.environ["GITHUB_TOKEN"]), "Accept": "application/vnd.github+json"})


def normal(s):
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()


def titulo_issue(data):
    d = datetime.date.fromisoformat(data)
    return f"Radar Atto {d.strftime('%d/%m')}: aprovação"


def achar_issue(data):
    for it in gh("GET", f"/issues?labels={ROTULO}&state=open&per_page=30"):
        if it["title"] == titulo_issue(data):
            return it
    return None


def abrir(data):
    if achar_issue(data):
        print("Issue de aprovação já existe para", data)
        return
    ed = json.load(open(os.path.join(AQUI, "edicoes", data, "edicao.json"), encoding="utf-8"))
    sha = os.environ.get("GITHUB_SHA", "main")
    raw = f"https://github.com/{REPO}/blob/{sha}/radar/edicoes/{data}"
    linhas = [f"**Edição de {datetime.date.fromisoformat(data).strftime('%d/%m/%Y')}.** Publicação automática às **07:20**, somente com aprovação.", "",
              "Para aprovar, comente **aprovado**. Para cancelar, comente **não publicar**.", "",
              f'<img src="{raw}/story_1.jpg?raw=true" width="32%"> <img src="{raw}/story_2.jpg?raw=true" width="32%"> <img src="{raw}/story_3.jpg?raw=true" width="32%">', ""]
    for b in ed["blocos"]:
        linhas.append(f"### {b['titulo']}")
        for it in b["itens"]:
            linhas.append(f"- **{it['titulo']}**. {it['frase']} _(Fonte: {it.get('fonte','')}{' · ' + it['url'] if it.get('url') else ''})_")
        for ind in b.get("indicadores", []):
            linhas.append(f"  - {ind['nome']}: {ind['valor']} ({'+' if ind.get('dir') == 'up' else '−' if ind.get('dir') == 'down' else ''}{ind.get('var','')})")
        linhas.append("")
    if ed.get("checagem"):
        linhas += ["<details><summary>Checagem dos números</summary>", "", ed["checagem"], "</details>"]
    try:
        gh("POST", "/labels", {"name": ROTULO, "color": "00888e"})
    except RuntimeError:
        pass
    dono = REPO.split("/")[0]
    it = gh("POST", "/issues", {"title": titulo_issue(data), "body": "\n".join(linhas), "labels": [ROTULO], "assignees": [dono]})
    print("Issue aberta:", it["html_url"])


def decisao(issue):
    ok = None
    for c in gh("GET", f"/issues/{issue['number']}/comments?per_page=100"):
        if c.get("author_association") not in ("OWNER", "MEMBER", "COLLABORATOR"):
            continue
        t = normal(c["body"])
        if "nao publicar" in t:
            ok = False
        elif "aprovad" in t:
            ok = True
    return ok


def comentar_e_fechar(issue, texto):
    gh("POST", f"/issues/{issue['number']}/comments", {"body": texto})
    gh("PATCH", f"/issues/{issue['number']}", {"state": "closed"})


def esperar_url(url, limite=600):
    t0 = time.time()
    while time.time() - t0 < limite:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=20) as r:
                if r.status == 200 and "image" in r.headers.get("Content-Type", ""):
                    return True
        except Exception:
            pass
        time.sleep(15)
    return False


def container(url):
    tok, uid = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
    cid = http("POST", f"{GRAPH}/{uid}/media", {"image_url": url, "media_type": "STORIES", "access_token": tok}, form=True)["id"]
    for _ in range(40):
        st = http("GET", f"{GRAPH}/{cid}?" + urllib.parse.urlencode({"fields": "status_code", "access_token": tok}))
        if st.get("status_code") == "FINISHED":
            return cid
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container com erro: {st}")
        time.sleep(4)
    raise RuntimeError("Container não ficou pronto")


def publicar(data, simular=False):
    issue = achar_issue(data)
    if not issue:
        print("Nenhuma issue de aprovação aberta para", data)
        return
    dec = decisao(issue)
    if dec is not True:
        motivo = "cancelada (não publicar)" if dec is False else "sem aprovação até 07:20"
        comentar_e_fechar(issue, f"Edição **não publicada**: {motivo}.")
        print("Não publicado:", motivo)
        return
    urls = [f"{SITE}/{data}/story_{i}.jpg" for i in (1, 2, 3)]
    for u in urls:
        if not esperar_url(u):
            comentar_e_fechar(issue, f"Falha: a arte {u} não ficou disponível no site. Nada publicado.")
            raise SystemExit("Arte indisponível")
    ids = []
    for u in urls:
        cid = container(u)
        if simular:
            ids.append("simulado:" + cid)
            continue
        r = http("POST", f"{GRAPH}/{os.environ['IG_USER_ID']}/media_publish",
                 {"creation_id": cid, "access_token": os.environ["IG_ACCESS_TOKEN"]}, form=True)
        ids.append(r["id"])
        time.sleep(3)
    if not simular:
        registrar(data)
    txt = "Teste concluído: os 3 stories foram preparados pela Meta, **sem publicar**." if simular else "Publicado no Instagram às " + datetime.datetime.now(BRT).strftime("%H:%M") + "."
    comentar_e_fechar(issue, txt + "\n\nIDs: " + ", ".join(ids))
    print(txt)


def registrar(data):
    hf = os.path.join(AQUI, "historico.json")
    hist = json.load(open(hf, encoding="utf-8")) if os.path.exists(hf) else []
    ed = json.load(open(os.path.join(AQUI, "edicoes", data, "edicao.json"), encoding="utf-8"))
    for b in ed["blocos"]:
        for it in b["itens"]:
            hist.append({"data": data, "bloco": b["titulo"], "titulo": it["titulo"], "fonte": it.get("fonte", "")})
    json.dump(hist, open(hf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def renovar():
    r = http("GET", "https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
        {"grant_type": "ig_refresh_token", "access_token": os.environ["IG_ACCESS_TOKEN"]}))
    novo, dias = r["access_token"], int(r.get("expires_in", 0)) // 86400
    from nacl import encoding, public
    adm = os.environ["RADAR_GH_TOKEN"]
    chave = gh("GET", "/actions/secrets/public-key", token=adm)
    caixa = public.SealedBox(public.PublicKey(chave["key"].encode(), encoding.Base64Encoder()))
    cifrado = base64.b64encode(caixa.encrypt(novo.encode())).decode()
    gh("PUT", "/actions/secrets/IG_ACCESS_TOKEN", {"encrypted_value": cifrado, "key_id": chave["key_id"]}, token=adm)
    print(f"Token do Instagram renovado ({dias} dias de validade) e secret atualizado.")


if __name__ == "__main__":
    cmd = sys.argv[1]
    data = sys.argv[2] if len(sys.argv) > 2 else datetime.datetime.now(BRT).date().isoformat()
    if cmd == "abrir":
        abrir(data)
    elif cmd == "publicar":
        publicar(data, simular=os.environ.get("RADAR_SIMULAR") == "1")
    elif cmd == "renovar":
        renovar()
