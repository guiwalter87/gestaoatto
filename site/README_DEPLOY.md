# Deploy · Site Atto (GitHub Pages)

Guia passo-a-passo para colocar `www.gestaoatto.com.br` no ar a partir desta pasta.

## 1. O que está pronto

- 16 páginas institucionais (`index.html`, `metodo.html`, `diagnostico-90-dias.html`, `rotina-mensal.html`, `direcao-estrategica.html`, `performance-financeira.html`, `pessoas-lideranca.html`, `governanca-ma.html`, `industria-manufatura.html`, `comercio-distribuicao.html`, `perspectivas.html`, `sobre.html`, `time.html`, `atuacao.html`, `trabalhe-conosco.html`, `clientes.html`, `contato.html`)
- 7 matérias de Perspectivas em `perspectivas/`
- Páginas legais: `politica-privacidade.html`, `termos-uso.html`
- `sitemap.xml`, `robots.txt`, `404.html`, `.nojekyll`
- `CNAME` já aponta para `www.gestaoatto.com.br`
- Assets em `assets/` (logos, imagens editoriais, `site.css`)

## 2. Ajustes obrigatórios antes do go-live

### 2.1 Google Analytics 4
Todas as páginas têm placeholder `G-XXXXXXXXXX`. Substituir pelo Measurement ID real. Um comando do terminal resolve:

```bash
cd "<pasta do site>"
find . -name "*.html" -exec sed -i '' 's/G-XXXXXXXXXX/SEU_GA_ID/g' {} +
```

### 2.2 Formulário de contato (`contato.html`)
Hoje é um mock que dispara `alert`. Para receber os leads:

1. Criar conta em https://formspree.io (plano free aceita 50 submissões/mês)
2. Criar um novo form, copiar o endpoint (formato `https://formspree.io/f/ABCDEFGH`)
3. Em `contato.html`, substituir a tag `<form onsubmit="...">` por:
   ```html
   <form action="https://formspree.io/f/ABCDEFGH" method="POST">
   ```
4. Adicionar atributo `name="..."` em cada `<input>`, `<select>` e `<textarea>` (ex.: `name="nome"`, `name="cargo"`, `name="empresa"`, `name="email"`, `name="whatsapp"`, `name="assunto"`, `name="contexto"`)

### 2.3 Imagens reais
Os assets em `assets/clientes*`, `assets/editorial`, `assets/institucional` e `assets/time` já estão no repositório. Se precisar trocar foto do time ou logos de cliente, basta substituir o arquivo mantendo o mesmo nome.

## 3. Deploy no GitHub Pages

### 3.1 Subir para o GitHub

```bash
cd "<pasta do site>"
# O .git já existe, só falta o remote
git add -A
git commit -m "Site institucional Atto — go-live"
git remote add origin https://github.com/<seu-user>/gestaoatto-site.git
git branch -M main
git push -u origin main
```

### 3.2 Habilitar Pages

1. Em https://github.com/<seu-user>/gestaoatto-site → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` · Folder: `/ (root)` · **Save**
4. Aguardar 1–2 min; a primeira URL será `<seu-user>.github.io/gestaoatto-site/` (só pra validar)

### 3.3 DNS no registro.br (domínio `gestaoatto.com.br`)

No painel do registro.br, editar DNS para:

**Subdomínio `www`** (onde o site vai responder):
- Tipo: `CNAME`
- Nome: `www`
- Valor: `<seu-user>.github.io`

**Apex `gestaoatto.com.br`** (redireciona para `www`):
- Tipo: `A` · Nome: `@` · Valor: `185.199.108.153`
- Tipo: `A` · Nome: `@` · Valor: `185.199.109.153`
- Tipo: `A` · Nome: `@` · Valor: `185.199.110.153`
- Tipo: `A` · Nome: `@` · Valor: `185.199.111.153`

Propagação DNS: até 24h (normalmente 1–2h).

### 3.4 HTTPS

Depois do DNS propagar, voltar em **Settings → Pages** e marcar **Enforce HTTPS**. O GitHub provisiona certificado Let's Encrypt automaticamente.

## 4. Migração do Wix Clássico

O site antigo continua em `www.gestaoatto.com.br` via Wix Editor Clássico (site ID `72dbf630-8d3c-4914-909c-1d9a1844f1cb`). A troca é feita no **DNS do registro.br** — basta alterar o CNAME/A records apontando para o GitHub, como descrito em 3.3. Não precisa desativar o Wix antes; assim que o DNS propagar, o domínio passa a servir o novo site.

Recomendo **não cancelar a assinatura Wix** até confirmar que o novo site está estável (24–48h depois do go-live).

## 5. Atualizações futuras

Qualquer alteração:

```bash
cd "<pasta do site>"
# edita os HTMLs
git add -A
git commit -m "Descrição da alteração"
git push
```

O GitHub Pages republica em ~1 minuto.
