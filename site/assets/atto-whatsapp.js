/* ==========================================================================
   Atto · Botão flutuante de WhatsApp
   v1.0 · 2026-08-16
   --------------------------------------------------------------------------
   Botão fixo no canto inferior direito. Ao clicar, abre um cartão com duas
   opções (sem exibir os números):
     1. Falar com um dos sócios      → +55 51 99333-3826
     2. Falar sobre vagas em aberto  → +55 54 99907-9939
   Os cliques são medidos pelo atto-events.js (generate_lead / lead_source
   whatsapp) e levam o atributo data-wa-topic (socios | vagas).
   Convive com o banner de cookies: sobe quando o banner está aberto.
   ========================================================================== */
(function () {
  'use strict';
  if (/\/links\.html$/.test(location.pathname)) return;   // a página /links já tem o botão de WhatsApp

  var NUM_SOCIOS = '5551993333826';
  var NUM_VAGAS  = '5554999079939';
  var MSG_SOCIOS = 'Olá, vim pelo site da Atto e gostaria de falar com um dos sócios.';
  var MSG_VAGAS  = 'Olá, vim pelo site da Atto e gostaria de saber sobre as vagas em aberto.';

  function wa(num, msg) { return 'https://wa.me/' + num + '?text=' + encodeURIComponent(msg); }

  var CSS = '' +
    '.atto-wa{position:fixed;right:22px;bottom:22px;z-index:9998;font-family:"Outfit","Inter",system-ui,-apple-system,Segoe UI,sans-serif;transition:bottom .3s ease}' +
    '.atto-wa-btn{width:58px;height:58px;border-radius:50%;border:none;cursor:pointer;background:#25D366;color:#fff;display:flex;align-items:center;justify-content:center;' +
      'box-shadow:0 10px 30px rgba(37,211,102,.35),0 2px 8px rgba(0,0,0,.18);transition:transform .2s,box-shadow .2s;position:relative}' +
    '.atto-wa-btn:hover{transform:translateY(-2px) scale(1.04);box-shadow:0 14px 36px rgba(37,211,102,.42),0 3px 10px rgba(0,0,0,.2)}' +
    '.atto-wa-btn:focus-visible{outline:3px solid rgba(37,211,102,.5);outline-offset:3px}' +
    '.atto-wa-btn svg{width:30px;height:30px;transition:transform .25s}' +
    '.atto-wa.is-open .atto-wa-btn svg.ico-wa{transform:rotate(90deg) scale(0);position:absolute}' +
    '.atto-wa-btn svg.ico-x{position:absolute;transform:rotate(-90deg) scale(0)}' +
    '.atto-wa.is-open .atto-wa-btn svg.ico-x{transform:none}' +
    '.atto-wa-pulse{position:absolute;inset:0;border-radius:50%;background:#25D366;opacity:.45;animation:attoWaPulse 2.4s ease-out infinite;pointer-events:none}' +
    '.atto-wa.is-open .atto-wa-pulse{display:none}' +
    '@keyframes attoWaPulse{0%{transform:scale(1);opacity:.45}70%{transform:scale(1.55);opacity:0}100%{transform:scale(1.55);opacity:0}}' +
    '.atto-wa-card{position:absolute;right:0;bottom:72px;width:min(320px,calc(100vw - 44px));background:#0f172a;color:#e2e8f0;border:1px solid rgba(255,255,255,.08);border-radius:14px;' +
      'box-shadow:0 20px 50px rgba(0,0,0,.35);padding:16px;transform:translateY(12px) scale(.98);opacity:0;pointer-events:none;transition:transform .25s cubic-bezier(.2,.8,.2,1),opacity .25s;transform-origin:bottom right}' +
    '.atto-wa.is-open .atto-wa-card{transform:none;opacity:1;pointer-events:auto}' +
    '.atto-wa-card h2{margin:0 0 4px;font-size:15px;font-weight:600;letter-spacing:-.01em;color:#fff}' +
    '.atto-wa-card p{margin:0 0 12px;font-size:13px;line-height:1.45;color:#94a3b8}' +
    '.atto-wa-opt{display:flex;align-items:center;gap:12px;padding:12px 12px;border-radius:10px;text-decoration:none;color:#e2e8f0;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);transition:background .2s,border-color .2s,transform .2s}' +
    '.atto-wa-opt+.atto-wa-opt{margin-top:8px}' +
    '.atto-wa-opt:hover{background:rgba(37,211,102,.12);border-color:rgba(37,211,102,.5);transform:translateX(2px)}' +
    '.atto-wa-opt .ic{flex-shrink:0;width:38px;height:38px;border-radius:50%;background:rgba(37,211,102,.16);color:#25D366;display:flex;align-items:center;justify-content:center}' +
    '.atto-wa-opt .ic svg{width:20px;height:20px}' +
    '.atto-wa-opt .t{display:flex;flex-direction:column;gap:2px;line-height:1.3}' +
    '.atto-wa-opt .t strong{font-size:14.5px;font-weight:500;color:#fff}' +
    '.atto-wa-opt .t span{font-size:12px;color:#94a3b8}' +
    '.atto-wa-opt .arrow{margin-left:auto;color:#25D366;font-size:16px}' +
    '@media (max-width:640px){.atto-wa{right:16px;bottom:16px}.atto-wa-btn{width:54px;height:54px}}' +
    '@media (prefers-reduced-motion:reduce){.atto-wa-pulse{animation:none}.atto-wa-card,.atto-wa-btn,.atto-wa-btn svg{transition:none}}';

  var ICON_WA = '<svg class="ico-wa" viewBox="0 0 32 32" fill="currentColor" aria-hidden="true"><path d="M16.02 3C8.9 3 3.13 8.76 3.13 15.87c0 2.27.6 4.48 1.73 6.42L3 29l6.9-1.81a12.9 12.9 0 0 0 6.12 1.55h.01c7.11 0 12.88-5.76 12.88-12.87C28.9 8.76 23.13 3 16.02 3zm0 23.56h-.01a10.7 10.7 0 0 1-5.45-1.49l-.39-.23-4.1 1.07 1.1-3.99-.26-.41a10.65 10.65 0 0 1-1.64-5.64c0-5.9 4.8-10.7 10.71-10.7 2.86 0 5.55 1.11 7.57 3.13a10.64 10.64 0 0 1 3.13 7.57c0 5.9-4.8 10.69-10.66 10.69zm5.86-8.01c-.32-.16-1.9-.94-2.2-1.05-.29-.11-.51-.16-.72.16-.21.32-.83 1.05-1.02 1.26-.19.21-.37.24-.69.08-.32-.16-1.36-.5-2.58-1.6-.95-.85-1.6-1.9-1.78-2.22-.19-.32-.02-.5.14-.66.14-.14.32-.37.48-.56.16-.19.21-.32.32-.53.11-.21.05-.4-.03-.56-.08-.16-.72-1.74-.99-2.38-.26-.63-.52-.54-.72-.55h-.61c-.21 0-.56.08-.85.4-.29.32-1.12 1.09-1.12 2.66s1.15 3.09 1.31 3.3c.16.21 2.26 3.45 5.47 4.84.76.33 1.36.53 1.82.68.77.24 1.46.21 2.01.13.61-.09 1.9-.78 2.16-1.53.27-.75.27-1.39.19-1.53-.08-.13-.29-.21-.61-.37z"/></svg>';
  var ICON_X  = '<svg class="ico-x" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
  var ICON_PEOPLE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>';
  var ICON_BRIEF  = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16M2 12h20"/></svg>';

  function build() {
    var style = document.createElement('style'); style.id = 'atto-wa-style'; style.textContent = CSS; document.head.appendChild(style);
    var root = document.createElement('div');
    root.className = 'atto-wa';
    root.innerHTML =
      '<div class="atto-wa-card" id="atto-wa-card" role="dialog" aria-label="Falar no WhatsApp">' +
        '<h2>Falar no WhatsApp</h2>' +
        '<p>Escolha com quem você quer conversar. Atendimento em horário comercial.</p>' +
        '<a class="atto-wa-opt" href="' + wa(NUM_SOCIOS, MSG_SOCIOS) + '" target="_blank" rel="noopener" data-wa-topic="socios" data-cta-pos="whatsapp_flutuante">' +
          '<span class="ic">' + ICON_PEOPLE + '</span><span class="t"><strong>Falar com um dos sócios</strong><span>Direção, finanças, pessoas e M&amp;A</span></span><span class="arrow">→</span></a>' +
        '<a class="atto-wa-opt" href="' + wa(NUM_VAGAS, MSG_VAGAS) + '" target="_blank" rel="noopener" data-wa-topic="vagas" data-cta-pos="whatsapp_flutuante">' +
          '<span class="ic">' + ICON_BRIEF + '</span><span class="t"><strong>Falar sobre vagas em aberto</strong><span>Processos seletivos conduzidos pela Atto</span></span><span class="arrow">→</span></a>' +
      '</div>' +
      '<button type="button" class="atto-wa-btn" aria-label="Abrir opções de WhatsApp" aria-expanded="false" aria-controls="atto-wa-card"><span class="atto-wa-pulse"></span>' + ICON_WA + ICON_X + '</button>';
    document.body.appendChild(root);

    var btn = root.querySelector('.atto-wa-btn');
    function setOpen(o) { root.classList.toggle('is-open', o); btn.setAttribute('aria-expanded', o ? 'true' : 'false'); }
    btn.addEventListener('click', function () {
      var o = !root.classList.contains('is-open');
      setOpen(o);
      if (o && window.dataLayer) window.dataLayer.push({ event: 'whatsapp_widget_open', cta_position: 'whatsapp_flutuante' });
    });
    document.addEventListener('click', function (e) { if (!root.contains(e.target)) setOpen(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setOpen(false); });
    root.querySelectorAll('.atto-wa-opt').forEach(function (a) { a.addEventListener('click', function () { setTimeout(function () { setOpen(false); }, 150); }); });

    // Não sobrepor o banner de cookies enquanto ele estiver aberto (em telas estreitas eles compartilham a base)
    function ajustar() {
      var cc = document.querySelector('.atto-cc.is-open');
      if (cc && window.innerWidth < 900) {
        root.style.bottom = (cc.getBoundingClientRect().height + 36) + 'px';
      } else {
        root.style.bottom = '';
      }
    }
    var mo = new MutationObserver(ajustar);
    mo.observe(document.body, { childList: true, subtree: false, attributes: true, attributeFilter: ['class', 'hidden'] });
    setInterval(ajustar, 1200);
    window.addEventListener('resize', ajustar);
    ajustar();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build); else build();
})();
