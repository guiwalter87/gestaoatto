/**
 * Perspectivas Feed — carrega dinamicamente os 3 últimos posts
 * a partir de /perspectivas-data.json e renderiza no container #persp-feed.
 *
 * Para adicionar novo post:
 *   1) Criar /perspectivas/{slug}.html
 *   2) Adicionar entrada no /perspectivas-data.json (no topo, ou em qualquer posição —
 *      o script ordena por data descendente)
 */
(function () {
  'use strict';

  const MESES_PT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

  function formatDate(iso) {
    if (!iso) return '';
    const [y, m] = iso.split('-');
    const idx = parseInt(m, 10) - 1;
    return `${MESES_PT[idx] || ''} · ${y}`;
  }

  function categoriaSlug(cat) {
    return (cat || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]/g, '');
  }

  function renderCard(post) {
    const capa = `assets/capas/${post.slug}_hero.png`;
    return `
      <a class="persp-card" href="perspectivas/${post.slug}.html">
        <div class="persp-cover" aria-hidden="true" style="background-image:url('${capa}')"></div>
        <div class="persp-body">
          <div class="persp-tag">${post.categoria}</div>
          <h3>${post.titulo}</h3>
          <p class="persp-excerpt">${post.excerpt || ''}</p>
          <div class="persp-meta">
            <span>Perspectiva</span>
            <span>${formatDate(post.data)}</span>
            <span>${post.leitura}</span>
          </div>
        </div>
      </a>
    `;
  }

  async function load() {
    const container = document.getElementById('persp-feed');
    if (!container) return;

    try {
      const res = await fetch('perspectivas-data.json', { cache: 'no-cache' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const sorted = [...data].sort((a, b) => new Date(b.data) - new Date(a.data));
      const latest = sorted.slice(0, 3);
      container.innerHTML = latest.map(renderCard).join('');
    } catch (err) {
      console.error('[perspectivas-feed] falhou ao carregar:', err);
      // fallback silencioso: deixa o conteúdo estático que já estiver no container
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', load);
  } else {
    load();
  }
})();
