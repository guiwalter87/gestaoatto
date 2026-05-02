# Atto Studio

Central local de criação e gestão de Perspectivas. Roda em
`http://127.0.0.1:8765` (sem internet, sem login, tudo local).

## Como abrir

Da primeira vez:

1. Vá em `site/scripts/atto_studio/`.
2. Dê duplo-clique em **`instalar-na-area-de-trabalho.command`**.
   - Se o macOS reclamar de "desenvolvedor não identificado", clique com o
     botão direito → **Abrir** → **Abrir** mesmo. Só precisa fazer isso uma vez.
3. O atalho **`Atto Studio.command`** aparece na sua Área de Trabalho.

A partir daí, basta duplo-clique no atalho da Desktop sempre que quiser
abrir o Atto Studio. O script:

1. Sobe um servidor local em `127.0.0.1:8765`.
2. Abre o Safari nesta URL.
3. Roda até você dar `Ctrl+C` no Terminal ou fechar a janela.

## O que ele faz

### Aba "Nova perspectiva"

Formulário para criar um post novo. Campos:

| Campo | Notas |
|---|---|
| Título | Aparece na capa, no card e no `<title>`. |
| Título curto | Versão enxuta para Instagram (Feed e Stories). |
| Slug | Auto-gerado do título; pode editar manualmente. |
| Categoria | Direção, Performance, Pessoas, Governança, M&A, Sucessão, Indústria, Distribuição. |
| Autor | Guilherme, Juliano ou Patrícia. |
| Data | Datas futuras viram agendamento automático. |
| Tempo de leitura | Em minutos. |
| Resumo | Excerpt que aparece nos cards e no meta-description. |
| Texto | Markdown (`##`, `**bold**`, `*itálico*`, listas, links). |
| Fontes | Bloco que aparece destacado ao final. |

Ao clicar **Criar e gerar capas**, o app:

1. Renderiza o HTML do post a partir do template oficial.
2. Salva em `site/perspectivas/<slug>.html`.
3. Adiciona entrada em `site/perspectivas-data.json` (com numeração automática).
4. Se a data for futura, adiciona em `scripts/scheduled_posts.json` e
   inclui `<meta robots="noindex,nofollow">` no HTML.
5. Roda `scripts/capas.py --slug <slug>` para gerar 4 PNGs (hero, OG, IG Feed, IG Stories).

Em seguida, **Commitar + push agora** faz o `git add . && git commit && git push origin main`
no repositório.

### Importar texto criado no chat

O fluxo recomendado é: você e o Claude (no chat do Cowork) escrevem o
texto juntos, fechado em um JSON com todos os campos preenchidos. Depois,
no Atto Studio, você clica em **"Importar do chat"** no topo da página
de criação, cola o JSON e o formulário se preenche sozinho.

Formato esperado (objeto único):

```json
{
  "slug": "selic-alta-fpa-empresa-media",
  "titulo": "Selic alta em 2026 mudou o jogo do FP&A.",
  "titulo_curto": "FP&A em ciclo de juros altos.",
  "categoria": "Performance",
  "author": "Juliano Walter",
  "data": "2026-05-09",
  "minutes": 10,
  "excerpt": "Em ciclo de juros elevados, o orçamento anual deixou de proteger.",
  "body": "## O orçamento anual sozinho deixou de proteger\n\nPor décadas...",
  "sources": "Boletins do Banco Central..."
}
```

Para importar **vários posts em lote**, basta colar um array `[ {...}, {...} ]`.
O primeiro preenche o formulário; depois de cada "Criar e gerar capas",
o próximo é carregado automaticamente.

O campo `slug` é opcional (gera do título se vazio). Se a `data` for
futura, o post é tratado como agendado automaticamente.

### Conteúdo para redes sociais (gerado automaticamente)

Junto com o post, o app gera:

- **Texto LinkedIn** (long-form): título + 2 primeiros parágrafos + link + autor + hashtags.
- **Legenda Instagram**: título curto + excerpt + CTA de bio + hashtags.
- **4 capas baixáveis**: Hero (1600×900), OG (1200×630 para LinkedIn), Instagram Feed
  (1080×1080) e Instagram Stories (1080×1920).

Todos os textos aparecem no painel de resultado em textareas editáveis. Cada um tem
botão **Copiar** que joga direto pro clipboard. As capas tem cards com thumbnail e
clicar baixa o PNG.

Hashtags por categoria:

| Categoria | Hashtags |
|---|---|
| Direção | #estrategia #lideranca #empresamedia #direcao #gestao |
| Performance | #fpa #financascorporativas #performancefinanceira #empresamedia |
| Pessoas | #pessoas #lideranca #rh #engajamento #recrutamentoeselecao |
| Governança | #governancacorporativa #conselhoconsultivo #empresafamiliar |
| M&A | #fusoeseaquisicoes #ma #valuation #middlemarket |
| Sucessão | #sucessao #empresafamiliar #governancafamiliar |
| Indústria | #industriabrasileira #manufatura #gestaoindustrial |
| Distribuição | #distribuicao #comerciob2b #gestaocomercial |

Todas as variações terminam com `#attoestrategias #perspectivas`.

### Aba "Posts"

Lista de tudo que existe. Cada item mostra status (Publicado / Agendado /
Rascunho), categoria, data, capa e botões para ver no site ou regenerar
capas.

### Aba "Agendamento"

Calendário do mês (com botões de avançar/voltar) destacando datas com
posts agendados ou já publicados.

## Requisitos

- macOS Sonoma+ (já tem Python 3.9+).
- Pillow + numpy instalados (já estão, são deps do `capas.py`).
- Fontes em `~/Documents/Claude/Projects/Site da Atto/fonts/`
  (Outfit + JetBrains Mono — já estão).
- Git configurado e autenticado para `git push origin main` funcionar.
  Se ainda não estiver, rode uma vez no Terminal:
  ```
  git config --global user.name "Guilherme Walter"
  git config --global user.email "guilherme.walter@gestaoatto.com.br"
  ```

## Atualizar dependências

Se `flask` ou `markdown` faltarem, o launcher tenta instalar via
`pip install --user`. Se isso falhar (políticas do PEP 668 do Python 3.12+),
ele tenta com `--break-system-packages`.

Para forçar manualmente:

```bash
python3 -m pip install --user --break-system-packages flask markdown
```

## Limites conhecidos

- **Não é um editor visual.** O texto é Markdown puro. Para WYSIWYG com
  preview ao vivo, é uma melhoria futura.
- **Não roda em Windows/Linux** sem ajuste de paths no `app.py`.
- **Não substitui o GitHub Action `Publish scheduled posts`.** Ele continua
  rodando às 07:00 BRT pra ativar posts cuja data chegou.

## Estrutura

```
atto_studio/
├── app.py                              # Backend Flask
├── post_template.html                  # Template do post HTML
├── requirements.txt                    # flask, markdown
├── README.md                           # você está aqui
├── Atto Studio.command                 # Launcher para macOS
├── instalar-na-area-de-trabalho.command  # Cópia o launcher pra Desktop
├── templates/
│   ├── base.html
│   ├── new.html
│   ├── posts.html
│   └── schedule.html
└── static/
    ├── style.css
    └── app.js
```
