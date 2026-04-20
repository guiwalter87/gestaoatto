/* ============================================================
   ATTO — SITE.JS · motion, scroll progress e counter
   Shared em todas as páginas (menos home, que tem inline)
   ============================================================ */

(function(){
  'use strict';

  /* ===== SCROLL PROGRESS BAR ===== */
  (function(){
    const bar = document.querySelector('.scroll-progress');
    if (!bar) return;
    function update(){
      const h = document.documentElement;
      const max = h.scrollHeight - h.clientHeight;
      const pct = max > 0 ? (h.scrollTop / max) * 100 : 0;
      bar.style.width = pct + '%';
    }
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    update();
  })();

  /* ===== MOTION REVEALS (auto-apply a elementos comuns) ===== */
  (function(){
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    // Selectors que recebem .reveal automaticamente
    const autoTag = [
      '.breadcrumb', '.page-hero .kicker', '.page-hero h1', '.page-hero .lead', '.page-hero .actions',
      '.section-label', '.section-title', '.section-lead',
      '.intro-grid', '.sintomas-grid', '.sintomas-list li',
      '.entregas-list', '.entrega-item',
      '.timeline-grid', '.timeline-col',
      '.prova-quote', '.prova-meta',
      '.cta-final h2', '.cta-final p', '.cta-final .actions',
      '.faq-list', '.faq-item'
    ];
    autoTag.forEach(sel => {
      document.querySelectorAll(sel).forEach(el => el.classList.add('reveal'));
    });

    // Staggering em grids
    ['.timeline-col', '.entrega-item', '.sintomas-list li', '.faq-item'].forEach(sel => {
      document.querySelectorAll(sel).forEach((el, i) => {
        el.style.transitionDelay = (i * 0.08) + 's';
      });
    });

    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -60px' });

    document.querySelectorAll('.reveal').forEach(el => io.observe(el));
  })();

  /* ===== COUNTER ANIMATION (se houver data-count no DOM) ===== */
  (function(){
    const els = document.querySelectorAll('[data-count]');
    if (!els.length) return;

    const easeOutCubic = t => 1 - Math.pow(1 - t, 3);
    function animateCount(el){
      const target = parseFloat(el.dataset.count);
      const decimals = parseInt(el.dataset.decimals || '0', 10);
      const duration = 1500;
      const start = performance.now();
      function fmt(v){
        return decimals
          ? v.toFixed(decimals).replace('.', ',')
          : Math.round(v).toLocaleString('pt-BR');
      }
      function step(now){
        const p = Math.min((now - start) / duration, 1);
        el.textContent = fmt(target * easeOutCubic(p));
        if (p < 1) requestAnimationFrame(step);
        else el.textContent = fmt(target);
      }
      requestAnimationFrame(step);
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting && !e.target.dataset.counted) {
          e.target.dataset.counted = '1';
          animateCount(e.target);
        }
      });
    }, { threshold: 0.4 });
    els.forEach(el => io.observe(el));
  })();

})();
