# Sistema de agendamento de Perspectivas

Este diretório contém o agendador de posts editoriais do site. Posts entram em
`scheduled_posts.json` com uma `publish_date` futura, e são publicados
automaticamente pelo workflow `.github/workflows/publish-scheduled.yml` quando a
data chega.

## Como funciona

1. Cada post agendado tem três marcas no repositório enquanto ainda não foi
   publicado:
   - O HTML do post existe em `perspectivas/<slug>.html`, mas com a tag
     `<meta name="robots" content="noindex,nofollow"><!-- SCHEDULED:DATA -->`
     no `<head>` para impedir que o Google o indexe antes da hora.
   - O `perspectivas.html` (a grade) ainda não tem o card do post.
   - O `sitemap.xml` ainda não tem a URL do post.
2. O GitHub Action `publish-scheduled.yml` roda diariamente às 10:00 UTC
   (07:00 BRT) e dispara `python3 scripts/publish_scheduled.py`.
3. Para cada post cuja `publish_date` for menor ou igual à data corrente, o
   script:
   - Remove a meta robots do HTML do post.
   - Insere o card no bloco `<!-- SCHEDULED-POSTS-START -->` do
     `perspectivas.html` (mais novos no topo).
   - Insere a URL no bloco `<!-- SCHEDULED-SITEMAP-START -->` do
     `sitemap.xml`.
4. Se houve qualquer publicação, o workflow faz commit e push automaticamente.
   Se não, sai sem mexer no repositório.

O script é idempotente: posts já publicados são ignorados em execuções
subsequentes, sem duplicar cards nem URLs.

## Adicionando um novo post agendado

1. Crie o HTML do post em `perspectivas/<slug>.html`, seguindo o template dos
   posts existentes. **Inclua a tag** logo abaixo do `<meta name="theme-color">`:
   ```html
   <meta name="robots" content="noindex,nofollow"><!-- SCHEDULED:YYYY-MM-DD -->
   ```
   (substitua `YYYY-MM-DD` pela data desejada de publicação).
2. Adicione uma entrada em `scripts/scheduled_posts.json` com `slug`,
   `publish_date`, `tag`, `tag_class`, `minutes`, `month`, `year`, `h3`,
   `summary` e `author`.
3. Faça commit e push. O workflow assume daqui em diante.

## Disparando manualmente

No GitHub: vá em **Actions > Publish scheduled posts > Run workflow**.

Localmente, para testar com data simulada:
```bash
python3 scripts/publish_scheduled.py 2026-05-09
```
(roda como se fosse o dia 09/05; útil para verificar antes de subir).

## Cores de capa válidas (`tag_class`)

Use uma das classes já existentes em `perspectivas.html`:

| Classe       | Visual                                  |
|--------------|------------------------------------------|
| `img-blue`   | Gradiente azul-noite → azul-atto         |
| `img-teal`   | Gradiente azul-atto → teal-atto          |
| `img-paper`  | Papel escuro com tag invertida           |
| `img-roxo`   | Gradiente roxo → azul-atto               |
| `img-dark`   | Tinta preta sólida                       |
| `img-warm`   | Gradiente em tons quentes                |
