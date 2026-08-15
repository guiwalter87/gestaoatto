/* ==========================================================================
   Atto · Consentimento de cookies (LGPD) + Google Consent Mode v2
   v1.1 · 2026-08-15 (analytics + marketing)
   --------------------------------------------------------------------------
   - O padrão "denied" e a leitura da escolha salva acontecem INLINE no <head>
     (antes do GTM). Este arquivo cuida só da interface do banner.
   - Escolha guardada em localStorage["atto_consent"] por 12 meses.
   - Qualquer elemento com [data-cookie-prefs] reabre o banner.
   - 'Aceitar' libera analytics_storage E ad_storage/ad_user_data/ad_personalization
     (GA4 + Meta Pixel). Emite dataLayer.push({event:'consent_update', ...}).
   ========================================================================== */
(function () {
  'use strict';

  var KEY = 'atto_consent';
  var TTL_MS = 365 * 24 * 60 * 60 * 1000;
  var dl = (window.dataLayer = window.dataLayer || []);
  function gtag() { dl.push(arguments); }

  function readChoice() {
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return null;
      var obj = JSON.parse(raw);
      if (!obj || !obj.ts || (Date.now() - obj.ts) > TTL_MS) return null;
      return obj;
    } catch (e) { return null; }
  }

  function saveChoice(analytics) {
    var obj = { analytics: analytics ? 'granted' : 'denied', ts: Date.now(), v: 1 };
    try { localStorage.setItem(KEY, JSON.stringify(obj)); } catch (e) { /* modo privado */ }
    return obj;
  }

  function applyChoice(analytics) {
    var state = analytics ? 'granted' : 'denied';
    gtag('consent', 'update', {
      analytics_storage: state,
      ad_storage: state,
      ad_user_data: state,
      ad_personalization: state
    });
    dl.push({ event: 'consent_update', consent_analytics: state, consent_ads: state });
  }

  // ---------------------------------------------------------------- estilos
  var CSS = '' +
    '.atto-cc{position:fixed;left:20px;right:20px;bottom:20px;z-index:9999;max-width:520px;margin:0 auto;' +
    'background:#0f172a;color:#e2e8f0;border:1px solid rgba(255,255,255,.08);border-radius:14px;' +
    'box-shadow:0 20px 50px rgba(0,0,0,.35);padding:18px 20px;font-family:"Outfit","Inter",system-ui,-apple-system,Segoe UI,sans-serif;' +
    'font-size:14px;line-height:1.5;transform:translateY(20px);opacity:0;transition:transform .35s cubic-bezier(.2,.8,.2,1),opacity .35s}' +
    '.atto-cc.is-open{transform:none;opacity:1}' +
    '.atto-cc[hidden]{display:none}' +
    '.atto-cc h2{margin:0 0 6px;font-size:15px;font-weight:600;letter-spacing:-.01em;color:#fff}' +
    '.atto-cc p{margin:0 0 14px;color:#cbd5e1}' +
    '.atto-cc a{color:#5eead4;text-decoration:none;border-bottom:1px solid rgba(94,234,212,.4)}' +
    '.atto-cc .atto-cc-actions{display:flex;gap:10px;flex-wrap:wrap;align-items:center}' +
    '.atto-cc button{font:inherit;font-weight:600;font-size:13px;letter-spacing:.02em;border-radius:8px;padding:10px 16px;cursor:pointer;border:1px solid transparent;transition:background .2s,color .2s,border-color .2s}' +
    '.atto-cc .atto-cc-accept{background:#2dd4bf;color:#0f172a}' +
    '.atto-cc .atto-cc-accept:hover{background:#5eead4}' +
    '.atto-cc .atto-cc-decline{background:transparent;color:#e2e8f0;border-color:rgba(255,255,255,.22)}' +
    '.atto-cc .atto-cc-decline:hover{border-color:rgba(255,255,255,.5)}' +
    '.atto-cc button:focus-visible{outline:2px solid #5eead4;outline-offset:2px}' +
    '@media (min-width:900px){.atto-cc{left:24px;right:auto;bottom:24px;margin:0}}' +
    '@media (prefers-reduced-motion:reduce){.atto-cc{transition:none}}';

  function injectStyle() {
    if (document.getElementById('atto-cc-style')) return;
    var s = document.createElement('style');
    s.id = 'atto-cc-style';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  // ---------------------------------------------------------------- banner
  var banner = null;

  function politicaHref() {
    return /\/perspectivas\//.test(location.pathname) ? '../politica-privacidade.html' : 'politica-privacidade.html';
  }

  function build() {
    if (banner) return banner;
    injectStyle();
    banner = document.createElement('section');
    banner.className = 'atto-cc';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-modal', 'false');
    banner.setAttribute('aria-labelledby', 'atto-cc-title');
    banner.setAttribute('aria-describedby', 'atto-cc-desc');
    banner.hidden = true;
    banner.innerHTML =
      '<h2 id="atto-cc-title">Cookies e privacidade</h2>' +
      '<p id="atto-cc-desc">Usamos cookies de análise (Google Analytics) para entender como o conteúdo é lido e cookies de marketing (Meta Pixel) ' +
      'para medir e direcionar nossa comunicação nas redes sociais. Nenhum dado é vendido. Você pode mudar sua escolha a qualquer momento em ' +
      '<a href="' + politicaHref() + '">Política de privacidade</a>.</p>' +
      '<div class="atto-cc-actions">' +
        '<button type="button" class="atto-cc-accept">Aceitar</button>' +
        '<button type="button" class="atto-cc-decline">Recusar</button>' +
      '</div>';
    document.body.appendChild(banner);

    banner.querySelector('.atto-cc-accept').addEventListener('click', function () { decide(true); });
    banner.querySelector('.atto-cc-decline').addEventListener('click', function () { decide(false); });
    banner.addEventListener('keydown', function (e) { if (e.key === 'Escape') decide(false); });
    return banner;
  }

  function open() {
    var b = build();
    b.hidden = false;
    requestAnimationFrame(function () { b.classList.add('is-open'); });
    var btn = b.querySelector('.atto-cc-accept');
    if (btn) setTimeout(function () { btn.focus({ preventScroll: true }); }, 380);
  }

  function close() {
    if (!banner) return;
    banner.classList.remove('is-open');
    setTimeout(function () { banner.hidden = true; }, 380);
  }

  function decide(accept) {
    saveChoice(accept);
    applyChoice(accept);
    close();
  }

  // ---------------------------------------------------------------- init
  function init() {
    var choice = readChoice();
    if (!choice) open();          // o "denied" padrão já vale desde o <head>
    document.addEventListener('click', function (e) {
      var t = e.target && e.target.closest ? e.target.closest('[data-cookie-prefs]') : null;
      if (!t) return;
      e.preventDefault();
      open();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // API mínima para depuração/uso futuro
  window.attoConsent = { open: open, get: readChoice, set: decide };
})();
