# Logos dos Clientes Atto

Pasta contendo logos dos clientes da Atto Estratégias & Educação, extraídos da Apresentação Institucional 2026.

## Informações de Extração

- **Origem**: Apresentação Institucional 2026 (PDF)
- **Página de origem**: 21
- **Seção**: "ALGUNS CLIENTES"
- **Data de extração**: 2026-04-14
- **Total de logos extraídos**: 19

## Características

- **Formato**: PNG com canal alpha (transparência)
- **Fundo**: Branco removido com chroma key (transparência aplicada)
- **Dimensões**: Otimizadas para ~300px de largura (altura proporcional)
- **Qualidade**: RGBA LANCZOS4 (interpolação de alta qualidade)

## Detalhes dos Logos

| # | Arquivo | Dimensões (final) | Tamanho | Página | Notas |
|---|---------|-------------------|--------|--------|-------|
| 1 | `cliente_01.png` | 109x115 | 0.7 KB | 21 | Cliente 1 |
| 2 | `cliente_02.png` | 255x117 | 1.4 KB | 21 | Cliente 2 |
| 3 | `cliente_03.png` | 280x106 | 1.1 KB | 21 | Cliente 3 |
| 4 | `cliente_04.png` | 300x90 | 12.8 KB | 21 | Cliente 4 |
| 5 | `cliente_05.png` | 160x73 | 0.8 KB | 21 | Cliente 5 |
| 6 | `cliente_06.png` | 112x136 | 0.9 KB | 21 | Cliente 6 |
| 7 | `cliente_07.png` | 234x76 | 0.8 KB | 21 | Cliente 7 |
| 8 | `cliente_08.png` | 287x118 | 1.7 KB | 21 | Cliente 8 |
| 9 | `cliente_09.png` | 300x99 | 8.0 KB | 21 | Cliente 9 |
| 10 | `cliente_10.png` | 238x131 | 1.5 KB | 21 | Cliente 10 |
| 11 | `cliente_11.png` | 145x121 | 1.1 KB | 21 | Cliente 11 |
| 12 | `cliente_12.png` | 300x87 | 15.4 KB | 21 | Cliente 12 |
| 13 | `cliente_13.png` | 180x74 | 0.9 KB | 21 | Cliente 13 |
| 14 | `cliente_14.png` | 84x82 | 0.5 KB | 21 | Cliente 14 |
| 15 | `cliente_15.png` | 181x119 | 1.6 KB | 21 | Cliente 15 |
| 16 | `cliente_16.png` | 271x85 | 1.4 KB | 21 | Cliente 16 |
| 17 | `cliente_17.png` | 176x67 | 1.0 KB | 21 | Cliente 17 |
| 18 | `cliente_18.png` | 148x141 | 1.4 KB | 21 | Cliente 18 |
| 19 | `cliente_19.png` | 300x99 | 17.4 KB | 21 | Cliente 19 |

## Notas Técnicas

- Os logos foram extraídos usando detecção de contornos (OpenCV Canny Edge Detection)
- Transparência (alpha channel) foi aplicada usando chroma key no branco com tolerância de ~25 em RGB
- Logos pequenos (< 100px) podem aparecer pixelados ao aumentar - use em tamanho apropriado
- Alguns logos podem ser rasters (fotografias/imagens) em vez de vetores - qualidade pode variar

## Utilização

Para usar os logos no site:

```html
<img src="/assets/clientes/cliente_01.png" alt="Logo do Cliente" class="client-logo">
```

## Próximos Passos

- [ ] Revisar cada logo e renomear com nome da empresa se identificável
- [ ] Validar qualidade de renderização em diferentes tamanhos
- [ ] Otimizar tamanho de arquivos se necessário (webp, etc)
- [ ] Atualizar nomes de arquivos com nomes reais dos clientes

---

*Gerado automaticamente via extração de PDF*
