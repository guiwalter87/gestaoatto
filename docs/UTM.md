# Convenção de UTMs — Atto (gestaoatto.com.br)

Sem UTM, o GA4 classifica a newsletter como "referral de sendibm3.com" e os posts
de LinkedIn/Instagram como "Organic Social" genérico. Com a convenção abaixo, cada
canal aparece com nome próprio no relatório e dá para saber **qual e-mail / qual
post gerou lead**.

## Regras
- Sempre minúsculas, sem acento, palavras separadas por `-`.
- `utm_source` = de onde vem (plataforma). `utm_medium` = tipo de canal.
  `utm_campaign` = a peça (edição da newsletter, tema do post). `utm_content` = a
  posição/variação do link (opcional).
- Nunca usar UTM em links **internos** do site (quebra a atribuição da sessão).
- WhatsApp: usar `utm_medium=whatsapp` para que o GA4 separe do "Direct".

## Tabela

| Canal | utm_source | utm_medium | utm_campaign | utm_content (opcional) |
|---|---|---|---|---|
| Newsletter Perspectivas (Brevo) | `brevo` | `email` | `perspectiva-NN` (ex.: `perspectiva-22`) | `cta-topo` / `cta-final` / `logo` |
| LinkedIn — página da empresa | `linkedin` | `social` | `perspectiva-NN` ou `institucional-<tema>` | `post` / `artigo` / `bio` |
| LinkedIn — perfil pessoal (Guilherme) | `linkedin` | `social` | `perspectiva-NN` | `guilherme` |
| Instagram (bio, stories, legenda) | `instagram` | `social` | `perspectiva-NN` / `bio` | `bio` / `stories` / `carrossel` |
| WhatsApp (lista de transmissão, grupos) | `whatsapp` | `whatsapp` | `perspectiva-NN` / `convite-<evento>` | — |
| Assinatura de e-mail dos sócios | `assinatura` | `email` | `institucional` | `guilherme` / `juliano` / `patricia` |
| Google Perfil da Empresa | `google` | `organic` | `perfil-empresa` | — |
| Eventos / palestras (QR code) | `evento` | `offline` | `<nome-do-evento-aaaa>` | `slide` / `banner` |

### Exemplos prontos
- Newsletter → artigo:
  `https://www.gestaoatto.com.br/perspectivas/modo-fundador-empresa-media-delegar-sem-abdicar.html?utm_source=brevo&utm_medium=email&utm_campaign=perspectiva-22&utm_content=cta-topo`
- LinkedIn → home:
  `https://www.gestaoatto.com.br/?utm_source=linkedin&utm_medium=social&utm_campaign=institucional-clientes&utm_content=post`
- Instagram bio:
  `https://www.gestaoatto.com.br/perspectivas.html?utm_source=instagram&utm_medium=social&utm_campaign=bio&utm_content=bio`

## Brevo — UTM automático
Em **Campanhas → Configurações → Rastreamento do Google Analytics** (ou, na
criação de cada campanha, seção "Configurações avançadas → Rastreamento"),
ativar o rastreamento com:
`utm_source=brevo`, `utm_medium=email`, `utm_campaign={{campaign.name}}`.
Manter o nome da campanha no padrão `perspectiva-NN` para bater com a convenção.
O script `scripts/send_perspectiva_brevo.py` já pode montar os links com UTM
(ver seção "Links" no script).

## Como conferir no GA4
Relatórios → Aquisição → Aquisição de tráfego → dimensão
"Origem/mídia da sessão" ou "Campanha da sessão". No painel Looker Studio a aba
"Aquisição" já usa essa convenção.

## Instagram — link da bio (a partir de 15/08/2026)
O link da bio aponta para a página própria `https://www.gestaoatto.com.br/links.html?utm_source=instagram&utm_medium=social&utm_campaign=bio`
(substitui o Linktree). Os botões dessa página são links internos **sem UTM** (para não
sobrescrever a atribuição da sessão); cada clique é medido pelo evento `cta_click` com
`cta_position=links` e `cta_id` = agendar / ler_perspectiva / perspectivas / newsletter /
site / linkedin (WhatsApp vira `generate_lead`).
