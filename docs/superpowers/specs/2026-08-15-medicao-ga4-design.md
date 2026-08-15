# Medição GA4 do site da Atto — especificação (aprovada em 15/08/2026)

## Objetivo
Transformar o GA4 (`G-PTS41WC8HS`, propriedade 303668551) de "instalado" em uma
medição confiável de leads comerciais e engajamento editorial, no padrão de
agência: instrumentação semântica no site, propriedade configurada, relatório
executivo semanal.

## Decisões do dono do negócio
- LGPD: banner leve próprio (Aceitar/Recusar) + Consent Mode v2. Sem CMP paga.
- Conversão principal (`generate_lead`): formulário confirmado + WhatsApp comercial
  + telefone + e-mail comercial. Candidaturas/RH ficam em funil separado.
- Mídia paga é provável → migrar para Google Tag Manager agora.
- Relatório: painel Looker Studio + resumo semanal por e-mail (segunda, 07:00).

## Estado encontrado (auditoria 15/08/2026)
- gtag direto em 46 páginas; `atto-events.js` v1 (whatsapp/email/tel/cta/form/leitura).
- Retenção de eventos 2 meses; filtro interno em "Teste"; Signals off; ocultação de
  e-mail off; Search Console vinculado; sem Google Ads.
- Key events: `cta_agendar`, `perspectiva_lida`, `whatsapp_click`, `purchase`.
- Nos últimos 28 dias NÃO dispararam: `form_submit`, `whatsapp_click`, `tel_click`.
- Form de contato = POST tradicional para Formspree (sai do site; sucesso invisível).
- ~60 CTAs apontam para `contato.html#agendar`, âncora inexistente.
- Newsletter (Brevo) chega como referral `sendibm3.com` (sem UTM).
- Sem banner/Consent Mode; política de privacidade genérica sobre cookies.

## Camada A — site (repositório `site/site/`)
1. **GTM** substitui o snippet gtag em todas as páginas vivas. Antes do GTM:
   `gtag('consent','default', {analytics_storage:'denied', ad_storage:'denied',
   ad_user_data:'denied', ad_personalization:'denied', wait_for_update:500})`.
   `<noscript>` do GTM logo após `<body>`.
2. **`assets/atto-consent.js` + CSS**: banner discreto, Aceitar/Recusar, escolha
   guardada em `localStorage` (12 meses), `gtag('consent','update',…)`, link
   "Preferências de cookies" no rodapé reabre o banner. Push `consent_update` no
   dataLayer.
3. **`assets/atto-events.js` v2** — envia ao `dataLayer` (não ao gtag):
   - `generate_lead` {lead_source: form|whatsapp|telefone|email, form_subject,
     cta_position, page_family, vertical_atto}
   - `form_start`, `form_submit` (tentativa), `form_error` {error_code}
   - `cta_click` {cta_id, cta_position, cta_role, link_url, link_text}
   - `share` {method: whatsapp|linkedin|copy, content_type: perspectiva, item_id}
   - `file_download` {file_name, file_extension, link_url}
   - `newsletter_click` {cta_position}
   - `vaga_click` {vaga_titulo, link_url}; `rh_email_click`
   - `perspectiva_lida` {percent_scrolled: 25|50|75|90, article_*, vertical_atto}
   - `page_metadata` mantido (article_section, article_author, vertical_atto,
     page_family).
   Identificação de CTAs por `data-cta`, `data-cta-pos`, `data-cta-role` adicionados
   ao HTML; fallback por classe/`closest()`.
4. **contato.html**: envio via `fetch` para Formspree (`Accept: application/json`),
   sucesso inline (bloco "Recebido"), erro inline; `id="agendar"` no bloco do form;
   `id="contato-form"`.
5. **WhatsApp comercial**: `wa.me/5554999079939?text=…` pré-preenchido, sem UTM.
6. **politica-privacidade.html**: tabela de cookies (`_ga`, `_ga_PTS41WC8HS`,
   13 meses), operadores nomeados (Google, Formspree, Brevo, GitHub Pages, Google
   Fonts, Unsplash), base legal do analytics = consentimento, como revogar, data.
7. **docs/UTM.md**: convenção de UTMs (newsletter Brevo, LinkedIn, Instagram, WhatsApp
   Business) e como ligar o auto-UTM do Brevo.
8. Incluir `atto-events.js` na página `guerras-geopolitica…` (estava sem).

## Camada B — GTM + GA4
- **GTM** (JSON importado): tag GA4 Config (`G-PTS41WC8HS`, consent-aware);
  variáveis de dataLayer para todos os parâmetros; triggers Custom Event; uma tag
  GA4 Event por evento; Consent Initialization garantido antes do config.
- **GA4 admin**: retenção 14 meses; Signals on; ocultação de e-mail e query params;
  filtro interno ativo (IP 45.227.187.31); key events = `generate_lead`,
  `form_submit`, `newsletter_click` (remover `purchase`; manter `perspectiva_lida`
  fora de key events); dimensões personalizadas de evento: `cta_id`, `cta_position`,
  `lead_source`, `form_subject`, `share_method`, `page_family` (mantendo as 3
  existentes); grupo de canais personalizado com Newsletter e WhatsApp; públicos:
  "Leitor recorrente (≥2 Perspectivas)", "Visitou serviço sem lead", "Lead"; atribuição
  data-driven; validação em DebugView.

## Camada C — relatório
- Looker Studio "Atto · Comercial & Conteúdo": leads por origem/vertical/CTA; funil
  visita → página de serviço → contato → lead; aquisição por canal; ranking de
  Perspectivas (leitura 90%, share); tendência mensal.
- Envio semanal por e-mail (segunda 07:00) para guilherme.walter@gestaoatto.com.br.

## Fora de escopo (por ora)
Newsletter Brevo e Google Forms (RH) seguem em iframe: inscrições/candidaturas
medidas nas plataformas de origem, não no GA4. Server-side tagging. Pixels de mídia
paga (o GTM já deixa pronto).
