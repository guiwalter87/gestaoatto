#!/usr/bin/env python3
"""Radar Atto: produz a edicao do dia (pesquisa + redacao via API do Claude) e gera as 3 artes.

Executado pelo GitHub Actions (radar-producao.yml). Variaveis de ambiente:
  ANTHROPIC_API_KEY  (secret)
  RADAR_MODEL        (opcional; se vazio, usa o Sonnet mais recente disponivel)
  RADAR_DATA         (opcional; AAAA-MM-DD, padrao = hoje em Brasilia)
Saida: radar/edicoes/AAAA-MM-DD/{edicao.json, story_1..3.jpg} e site/radar/AAAA-MM-DD/story_1..3.jpg
Codigo de saida 78 = dia sem edicao (fim de semana/feriado).
"""
import datetime, json, os, re, shutil, subprocess, sys, time, urllib.request, urllib.error

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
BRT = datetime.timezone(datetime.timedelta(hours=-3))

FERIADOS = {  # nacionais (sem edicao)
    "2026-10-12", "2026-11-02", "2026-11-20", "2026-12-25",
    "2027-01-01", "2027-02-08", "2027-02-09", "2027-03-26", "2027-04-21", "2027-05-01",
    "2027-05-27", "2027-09-07", "2027-10-12", "2027-11-02", "2027-11-15", "2027-11-20", "2027-12-25",
}
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]


def api(caminho, corpo=None, tentativas=4):
    h = {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"}
    for t in range(tentativas):
        try:
            req = urllib.request.Request("https://api.anthropic.com" + caminho,
                                         data=json.dumps(corpo).encode() if corpo else None, headers=h,
                                         method="POST" if corpo else "GET")
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:500]
            if e.code in (429, 500, 502, 503, 529) and t < tentativas - 1:
                time.sleep(20 * (t + 1))
                continue
            raise RuntimeError(f"API Anthropic {e.code}: {msg}")


def modelo():
    m = os.environ.get("RADAR_MODEL", "").strip()
    if m:
        return m
    lista = api("/v1/models?limit=100")["data"]
    sonnets = [x for x in lista if "sonnet" in x["id"]]
    return (sonnets or lista)[0]["id"]  # a API lista do mais recente para o mais antigo


def historico_recente(dias=45):
    f = os.path.join(AQUI, "historico.json")
    hist = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else []
    corte = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()
    return [h for h in hist if h["data"] >= corte]


ESQUEMA = """{
  "data": "AAAA-MM-DD",
  "blocos": [
    {"titulo": "Mundo", "icone": "globo", "ref": "dd/mm",
     "indicadores": [
       {"nome": "S&P 500", "valor": "7.637", "var": "1,14%", "dir": "up"},
       {"nome": "Brent", "valor": "US$ 104,82", "var": "0,95%", "dir": "down"},
       {"nome": "VIX", "valor": "15,44", "var": "12,82%", "dir": "down"}],
     "itens": [{"chapeu": "JUROS NOS EUA", "titulo": "...", "frase": "...", "fonte": "CNBC", "url": "https://..."}]},
    {"titulo": "Brasil", "icone": "bandeira", "ref": "dd/mm",
     "indicadores": [
       {"nome": "Ibovespa", "valor": "185.992", "var": "0,24%", "dir": "up"},
       {"nome": "Dólar", "valor": "R$ 5,13", "var": "0,48%", "dir": "down"},
       {"nome": "DI jan/29", "valor": "13,77%", "var": "0,13 p.p.", "dir": "down"}],
     "itens": [...3 itens...]},
    {"titulo": "Serra Gaúcha", "icone": "serra", "itens": [...1 a 3 itens...]}
  ],
  "checagem": "texto curto: como cada numero foi confirmado (duas fontes)"
}"""


def prompt(data):
    d = datetime.date.fromisoformat(data)
    inicio = d - datetime.timedelta(days=2 if d.weekday() == 0 else 1)  # segunda: desde sabado
    ref = d - datetime.timedelta(days=3 if d.weekday() == 0 else 1)
    linha = open(os.path.join(AQUI, "linha_editorial.md"), encoding="utf-8").read()
    hist = "\n".join(f"- {h['data']} [{h['bloco']}] {h['titulo']}" for h in historico_recente()) or "(vazio)"
    return f"""Você é o editor do RADAR ATTO, publicação diária de negócios da Atto Estratégias & Educação (Caxias do Sul, RS).
Hoje é {DIAS[d.weekday()]}, {d.strftime('%d/%m/%Y')}. Produza a edição de hoje.

LINHA EDITORIAL (siga à risca):
{linha}

REGRAS DESTA EDIÇÃO
1. Só notícias publicadas a partir de {inicio.strftime('%d/%m/%Y')} 00:00 (horário de Brasília). Confira a data de cada matéria.
2. NÃO repita fatos já publicados. Histórico recente:
{hist}
3. Indicadores: fechamento do pregão de {ref.strftime('%d/%m/%Y')} (dia útil anterior). Mundo: S&P 500 (pontos), Brent (US$/barril), VIX. Brasil: Ibovespa (pontos), Dólar comercial (R$), DI jan/29 (taxa e variação em pontos percentuais, p.p.). "ref" = "{ref.strftime('%d/%m')}". "dir": "up" se subiu, "down" se caiu. Valores no padrão brasileiro. Confirme cada número em duas fontes.
4. Mundo e Brasil: exatamente 3 itens cada. Serra Gaúcha: 1 a 3 itens (nunca complete com notícia fraca; em dia fraco aceite 1 notícia do RS com impacto na indústria da região).
5. Chapéu: 1 a 3 palavras em caixa alta (tema; na Serra, a cidade). Título: no máximo 55 caracteres. Frase: no máximo 115 caracteres, uma única frase. Fonte: nome do veículo. Inclua a URL da matéria em "url".
6. Proibido usar travessão (—), meia-risca (–) ou hífen entre espaços ( - ). Nunca use "PME". Sem emojis, sem opinião, sem previsão.
7. Apartidarismo absoluto: nada de eleições, pesquisas, declarações de políticos ou avaliação de governo. Atos de governo só como fato, sem atribuir mérito ou culpa.
8. O primeiro item de cada bloco é a manchete: a notícia de maior impacto para o empresário.

Pesquise com a ferramenta de busca (priorize as fontes da linha editorial). Ao final, responda SOMENTE com um JSON válido, sem texto antes ou depois, neste formato:
{ESQUEMA}
"""


def extrair_json(resp):
    txt = "".join(b.get("text", "") for b in resp["content"] if b.get("type") == "text")
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("Resposta sem JSON")
    return json.loads(m.group(0))


def validar(ed, data):
    erros = []
    if [b["titulo"] for b in ed.get("blocos", [])] != ["Mundo", "Brasil", "Serra Gaúcha"]:
        erros.append("Os blocos devem ser exatamente Mundo, Brasil e Serra Gaúcha, nessa ordem.")
    for b in ed.get("blocos", []):
        n = len(b.get("itens", []))
        if b["titulo"] in ("Mundo", "Brasil") and n != 3:
            erros.append(f"{b['titulo']} precisa de 3 itens (tem {n}).")
        if b["titulo"] == "Serra Gaúcha" and not 1 <= n <= 3:
            erros.append(f"Serra Gaúcha precisa de 1 a 3 itens (tem {n}).")
        if b["titulo"] in ("Mundo", "Brasil") and len(b.get("indicadores", [])) != 3:
            erros.append(f"{b['titulo']} precisa de 3 indicadores.")
        for it in b.get("itens", []):
            if len(it.get("titulo", "")) > 58:
                erros.append(f"Título longo demais: {it['titulo']}")
            if len(it.get("frase", "")) > 120:
                erros.append(f"Frase longa demais: {it['frase']}")
            for campo in ("chapeu", "titulo", "frase"):
                v = it.get(campo, "")
                if "—" in v or "–" in v or " - " in v:
                    erros.append(f"Travessão/hífen proibido em: {v}")
                if re.search(r"\bPMEs?\b", v):
                    erros.append(f"Termo PME proibido em: {v}")
    ed["data"] = data
    return erros


def produzir(data):
    mdl = modelo()
    print("Modelo:", mdl)
    msgs = [{"role": "user", "content": prompt(data)}]
    ferramentas = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 25,
                    "user_location": {"type": "approximate", "city": "Caxias do Sul", "region": "Rio Grande do Sul", "country": "BR", "timezone": "America/Sao_Paulo"}}]
    for tentativa in range(3):
        resp = api("/v1/messages", {"model": mdl, "max_tokens": 16000, "tools": ferramentas, "messages": msgs})
        while resp.get("stop_reason") == "pause_turn":
            msgs.append({"role": "assistant", "content": resp["content"]})
            resp = api("/v1/messages", {"model": mdl, "max_tokens": 16000, "tools": ferramentas, "messages": msgs})
        try:
            ed = extrair_json(resp)
            erros = validar(ed, data)
        except Exception as e:
            ed, erros = None, [f"JSON inválido: {e}"]
        if not erros:
            return ed
        print("Ajustes pedidos:", erros)
        msgs.append({"role": "assistant", "content": resp["content"]})
        msgs.append({"role": "user", "content": "Corrija estes problemas e devolva SOMENTE o JSON completo corrigido:\n- " + "\n- ".join(erros)})
    raise SystemExit("Não foi possível produzir uma edição válida após 3 tentativas.")


def main():
    data = os.environ.get("RADAR_DATA") or datetime.datetime.now(BRT).date().isoformat()
    d = datetime.date.fromisoformat(data)
    if d.weekday() >= 5 or data in FERIADOS:
        print("Sem edição hoje (fim de semana ou feriado).")
        sys.exit(78)
    ed = produzir(data)
    pasta = os.path.join(AQUI, "edicoes", data)
    os.makedirs(pasta, exist_ok=True)
    json.dump(ed, open(os.path.join(pasta, "edicao.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, os.path.join(AQUI, "gerar_radar_jornal.py"), os.path.join(pasta, "edicao.json"), pasta], check=True)
    site = os.path.join(RAIZ, "site", "radar", data)
    os.makedirs(site, exist_ok=True)
    for i in (1, 2, 3):
        shutil.copy(os.path.join(pasta, f"story_{i}.jpg"), os.path.join(site, f"story_{i}.jpg"))
    print("Edição pronta:", data)


if __name__ == "__main__":
    main()
