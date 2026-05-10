/**
 * Perspectivas Grid — renderiza dinamicamente TODOS os posts publicados
 * (data <= hoje BRT) na página /perspectivas.html, em ordem decrescente.
 *
 * Fonte única de verdade: /perspectivas-data.json (mesmo arquivo da home).
 * Isso elimina o descompasso entre home e perspectivas.html que ocorria
 * quando o cron do GitHub Actions (publish_scheduled.py) atrasava ou falhava.
 *
 * Para adicionar novo post:
 *   1) Criar /perspectivas/{slug}.html
 *   2) Adicionar entrada no /perspectivas-data.json (com slug, titulo, categoria,
 *      data, excerpt, leitura, tag_class, autor)
 *   3) Posts com data > hoje BRT ficam ocultos automaticamente até a data chegar.
 *
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

  function renderCard(post) {
    const tagClass = post.tag_class || 'img-teal';
    const capa = `assets/capas/${post.slug}_hero.png`;
    const monthYear = formatMonthYear(post.data);
    const leitura = post.leitura || '';
    const autor = post.autor || '';
    // titulo e excerpt vêm do JSON e podem conter <em> ou &amp; já com HTML válido —
    // são tratados como HTML pois é conteúdo controlado por nós (não é input de usuário).
    return `
      <a href="perspectivas/${post.slug}.html" class="persp-card" data-publish-date="${escapeAttr(post.data)}">
        <div class="persp-card-img ${tagClass}" style="background-image:url('${capa}');background-size:cover;background-position:center"><span class="tag">${post.categoria}</span></div>
        <div class="persp-card-meta"><span>${leitura}</span><span>${monthYear}</span></div>
        <h3>${post.titulo}</h3>
        <p>${post.excerpt || ''}</p>
        ${autor ? `<span class="author">${autor}</span>` : ''}
      </a>
    `;
  }

  async function load() {
    const container = document.getElementById('persp-grid');
    if (!container) return;

    try {
      const res = await fetch('perspectivas-data.json', { cache: 'no-cache' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Hoje em BRT (UTC-3). Mesma barreira de visibilidade da home —
      // posts agendados para o futuro NÃO podem aparecer no grid.
      const nowUtc = new Date();
      const brtNow = new Date(nowUtc.getTime() - 3 * 60 * 60 * 1000);
      const todayBrtIso = brtNow.toISOString().slice(0, 10); // YYYY-MM-DD
      const visiveis = data.filter((post) => (post.data || '') <= todayBrtIso);
      const sorted = visiveis.sort((a, b) => new Date(b.data) - new Date(a.data));

      if (sorted.length === 0) return; // mantém fallback estático visível
      container.innerHTML = sorted.map(renderCard).join('');
    } catch (err) {
      console.error('[perspectivas-grid] falhou ao carregar:', err);
      // fallback silencioso: mantém o conteúdo estático que já estiver no container
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', load);
  } else {
    load();
  }
})();
