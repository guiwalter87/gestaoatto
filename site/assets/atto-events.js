/* ==========================================================================
   Atto · GA4 Custom Events Tracker
   v1.0 · 2026-05-02
   --------------------------------------------------------------------------
   Events emitidos:
     - whatsapp_click  → click em link wa.me / api.whatsapp / whatsapp:
     - email_click     → click em link mailto:
     - tel_click       → click em link tel:
     - cta_agendar     → click no CTA "Agende conversa"
     - form_submit     → submit do form de contato
     - perspectiva_lida → scroll 90% em /perspectivas/*
   --------------------------------------------------------------------------
   Custom dimensions emitidos quando aplicável:
     - article_section, article_author, vertical_atto
   ========================================================================== */
(function () {
  'use strict';

  // Garantir que gtag esteja disponível (carregado pelo snippet GA4)
  function gtag() {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(arguments);
  }

  // Helpers de leitura de metadados da página
  function getMeta(name) {
    var el = document.querySelector('meta[name="' + name + '"], meta[property="' + name + '"]');
    return el ? el.getAttribute('content') : null;
  }

  function getArticleMeta() {
    var section = getMeta('article:section');
    var author = getMeta('article:author');
    var meta = {};
    if (section) meta.article_section = section;
    if (author) meta.article_author = author;
    // Vertical inferida pela URL
    var path = location.pathname.toLowerCase();
    var vertical = null;
    if (/direcao|metodo|atuacao|diagnostico/.test(path)) vertical = 'Direção';
    else if (/performance/.test(path)) vertical = 'Performance Financeira';
    else if (/pessoas|lideranca/.test(path)) vertical = 'Gente & Gestão';
    else if (/governanca|m-?a/.test(path)) vertical = 'Governança & M&A';
    else if (/contratacao/.test(path)) vertical = 'Contratação Estratégica';
    else if (/perspectivas/.test(path)) vertical = 'Perspectivas';
    if (vertical) meta.vertical_atto = vertical;
    return meta;
  }

  // ========================================================================
  // 1. CLICKS em wa.me / mailto / tel / CTA agendar
  // ========================================================================
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a');
    if (!a) return;
    var href = (a.getAttribute('href') || '').toLowerCase();
    if (!href) return;

    var meta = getArticleMeta();
    meta.link_url = a.href;
    meta.link_text = (a.textContent || '').trim().slice(0, 80);

    if (/^https?:\/\/(?:wa\.me|api\.whatsapp\.com|chat\.whatsapp\.com)/.test(href) || /^whatsapp:/.test(href)) {
      gtag('event', 'whatsapp_click', meta);
    } else if (/^mailto:/.test(href)) {
      gtag('event', 'email_click', meta);
    } else if (/^tel:/.test(href)) {
      gtag('event', 'tel_click', meta);
    } else if (a.classList.contains('cta-nav') || /agend(e|ar)\s+conversa/i.test(a.textContent)) {
      gtag('event', 'cta_agendar', meta);
    }
  }, { passive: true });

  // ========================================================================
  // 2. FORM SUBMIT em /contato.html (e qualquer form com .contato-form)
  // ========================================================================
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form || form.tagName !== 'FORM') return;
    var path = location.pathname.toLowerCase();
    var isContato = /contato/.test(path) || form.classList.contains('contato-form') || form.id === 'contato-form';
    if (!isContato) return;

    var data = {};
    data.form_id = form.id || 'contato';
    data.form_action = form.action || '';
    // Tentar capturar assunto (sem PII)
    var assunto = form.querySelector('[name="assunto"], select');
    if (assunto && assunto.value) data.form_subject = assunto.value.slice(0, 80);

    gtag('event', 'form_submit', data);
  }, { passive: true });

  // ========================================================================
  // 3. SCROLL 90% em páginas de Perspectiva (artigos editoriais)
  // ========================================================================
  var path = location.pathname.toLowerCase();
  var isPerspectiva = /\/perspectivas\/[^\/]+\.html/.test(path);
  if (isPerspectiva) {
    var fired = false;
    var ticking = false;

    function checkScroll() {
      if (fired) return;
      var doc = document.documentElement;
      var scrolled = (window.scrollY || doc.scrollTop) + window.innerHeight;
      var height = doc.scrollHeight;
      if (height > 0 && (scrolled / height) >= 0.9) {
        fired = true;
        var meta = getArticleMeta();
        meta.article_path = path;
        meta.article_title = document.title;
        gtag('event', 'perspectiva_lida', meta);
        window.removeEventListener('scroll', onScroll);
      }
    }

    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        checkScroll();
        ticking = false;
      });
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    // Verifica também ao carregar (se a página for curta)
    setTimeout(checkScroll, 500);
  }

  // ========================================================================
  // 4. PAGE METADATA enriquecimento (envia dimensions custom em todo pageview)
  // ========================================================================
  // Reenvia config com user_properties pra populá-las no relatório
  try {
    var pageMeta = getArticleMeta();
    if (Object.keys(pageMeta).length > 0) {
      gtag('event', 'page_metadata', pageMeta);
    }
  } catch (err) {
    // silent
  }
})();
