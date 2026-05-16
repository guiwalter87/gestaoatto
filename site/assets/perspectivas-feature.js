/**
 * Perspectivas Feature — renderiza dinamicamente o bloco "Em destaque" no
 * topo da página /perspectivas.html, sempre apontando para o post publicado
 * mais recente (data <= hoje BRT).
 *
 * Fonte única de verdade: /perspectivas-data.json (mesmo arquivo da home e
 * do grid). Resolve o descompasso histórico em que o cron do GitHub Actions
 * (publish_scheduled.py) atrasava e o destaque ficava preso em um post antigo
 * enquanto a home e o grid já mostravam os mais novos.
 *
 * Container alvo: <div id="persp-feature" class="persp-feature-grid">
 * Marcação CSS já existente em perspectivas.html é reproduzida 1:1.
 */
(function () {
  'use strict';

  const MESES_PT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

  function formatMonthYear(iso) {
    if (!iso) return '';
    const [y, m] = iso.split('-');
    const idx = parseInt(m, 10) - 1;
    return `${MESES_PT[idx] || ''} · ${y}`;
  }

  function escapeAttr(s) {
    return String(s || '').replace(/"/g, '&quot;');
  }

  function renderFeature(post) {
    const tag = post.categoria || '';
    const monthYear = formatMonthYear(post.data);
    const leituraNum = (post.leitura || '').replace(/[^0-9]/g, '') || '';
    const minutosTxt = leituraNum ? `${leituraNum} min de leitura` : (post.leitura || '');
    const capa = `assets/capas/${post.slug}_hero.png`;
    const slugAttr = escapeAttr(post.slug);

    return `
      <div class="persp-feature-body">
        <div class="kicker" style="font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.15em;text-transform:uppercase">Em destaque · ${monthYear}</div>
        <div class="meta">
          <span>${tag}</span>
          <span>${monthYear}</span>
          <span>${minutosTxt}</span>
        </div>
        <h2>${post.titulo}</h2>
        <p class="excerpt">${post.excerpt || ''}</p>
        <a href="perspectivas/${slugAttr}.html" class="btn-primary" style="display:inline-flex;align-items:center">Ler a tese completa <span class="arrow" style="margin-left:12px">→</span></a>
      </div>
      <a href="perspectivas/${slugAttr}.html" style="display:block">
        <div class="persp-feature-img" style="background-image:url('${capa}')"></div>
      </a>
    `;
  }

  async function load() {
    const container = document.getElementById('persp-feature');
    if (!container) return;

    try {
      const res = await fetch('perspectivas-data.json', { cache: 'no-cache' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Hoje em BRT (UTC-3). Mesma barreira de visibilidade do feed e do grid.
      const nowUtc = new Date();
      const brtNow = new Date(nowUtc.getTime() - 3 * 60 * 60 * 1000);
      const todayBrtIso = brtNow.toISOString().slice(0, 10); // YYYY-MM-DD
      const visiveis = data.filter((post) => (post.data || '') <= todayBrtIso);
      const sorted = visiveis.sort((a, b) => new Date(b.data) - new Date(a.data));

      if (sorted.length === 0) return; // mantém fallback estático visível
      container.innerHTML = renderFeature(sorted[0]);
    } catch (err) {
      console.error('[perspectivas-feature] falhou ao carregar:', err);
      // fallback silencioso: mantém o conteúdo estático que já estiver no container
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', load);
  } else {
    load();
  }
})();
