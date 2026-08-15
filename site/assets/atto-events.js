/* ==========================================================================
   Atto · Data Layer Events
   v2.0 · 2026-08-15
   --------------------------------------------------------------------------
   Publica eventos semânticos no window.dataLayer (lidos pelo Google Tag
   Manager, que os envia ao GA4). Não chama gtag() diretamente.

   Eventos:
     generate_lead      lead comercial — lead_source: form|whatsapp|telefone|email
     form_start         primeiro foco no formulário de contato
     form_submit        tentativa de envio (validação HTML5 ok)
     form_error         Formspree respondeu erro / rede falhou (error_code)
     cta_click          qualquer CTA — cta_id, cta_position, cta_role
     share              compartilhar Perspectiva — method: whatsapp|linkedin|copy
     file_download      link para .pdf .xlsx .docx .pptx .zip .png .jpg
     newsletter_click   link para newsletter.html
     vaga_click         card de vaga (Candidatar-se)
     rh_email_click     mailto para recrutamento (Jéssica)
     email_click        mailto que não é comercial nem RH
     perspectiva_lida   rolagem 25/50/75/90% em artigos (percent_scrolled)

   Dimensões de página (page_family, vertical_atto, article_section,
   article_author) já entram no dataLayer inline no <head>; o GTM as anexa
   a todos os eventos. Este script só as reaproveita como fallback.

   Overrides opcionais no HTML: data-cta, data-cta-pos, data-cta-role.
   ========================================================================== */
(function () {
  'use strict';

  var dl = (window.dataLayer = window.dataLayer || []);
  var WA_COMERCIAL = '5554999079939';
  var EMAIL_COMERCIAL = 'contato@gestaoatto.com.br';
  var EMAIL_RH = 'jessica.varela@gestaoatto.com.br';
  var DOWNLOAD_EXT = /\.(pdf|xlsx?|docx?|pptx?|zip|csv|png|jpe?g|svg|webp)(\?|#|$)/i;

  function push(evt, params) {
    var payload = { event: evt };
    for (var k in params) {
      if (params.hasOwnProperty(k) && params[k] !== undefined && params[k] !== null && params[k] !== '') {
        payload[k] = params[k];
      }
    }
    dl.push(payload);
  }

  function slugFromPath(path) {
    var m = (path || location.pathname).match(/\/perspectivas\/([^\/]+)\.html/);
    return m ? m[1] : null;
  }

  function isPerspectiva() { return !!slugFromPath(); }

  function cleanText(el) {
    return (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80);
  }

  function pageFamilyFallback() {
    for (var i = 0; i < dl.length; i++) {
      if (dl[i] && dl[i].page_family) return dl[i].page_family;
    }
    return undefined;
  }

  // ------------------------------------------------------------------------
  // Inferência de CTA: id (intenção), posição, papel
  // ------------------------------------------------------------------------
  function ctaId(a, href) {
    if (a.dataset && a.dataset.cta) return a.dataset.cta;
    var h = (href || '').toLowerCase();
    if (/contato\.html/.test(h)) return 'agendar';
    if (/diagnostico-90-dias/.test(h)) return 'diagnostico';
    if (/rotina-mensal/.test(h)) return 'rotina_mensal';
    if (/metodo\.html/.test(h)) return 'metodo';
    if (/atuacao\.html/.test(h)) return 'atuacao';
    if (/newsletter\.html/.test(h)) return 'newsletter';
    if (/perspectivas\.html/.test(h)) return 'perspectivas';
    if (/\/perspectivas\/[^\/]+\.html/.test(h)) return 'ler_perspectiva';
    if (/clientes\.html/.test(h)) return 'clientes';
    if (/(vagas|trabalhe-conosco)\.html/.test(h)) return 'carreiras';
    if (/direcao-estrategica/.test(h)) return 'frente_direcao';
    if (/performance-financeira/.test(h)) return 'frente_performance';
    if (/pessoas-lideranca/.test(h)) return 'frente_pessoas';
    if (/governanca-ma/.test(h)) return 'frente_governanca';
    if (/contratacao-estrategica/.test(h)) return 'frente_contratacao';
    if (/(industria-manufatura|comercio-distribuicao)/.test(h)) return 'setor';
    if (/(sobre|time)\.html/.test(h)) return 'institucional';
    if (/rqs\.html/.test(h)) return 'rqs';
    var seg = h.replace(/[?#].*$/, '').split('/').pop().replace(/\.html$/, '');
    return seg || 'link';
  }

  function ctaPosition(a) {
    if (a.dataset && a.dataset.ctaPos) return a.dataset.ctaPos;
    var c = function (sel) { return !!a.closest(sel); };
    if (c('header, nav')) return 'header';
    if (c('.hero, .page-hero, .post-hero')) return 'hero';
    if (c('.cta-final')) return 'cta_final';
    if (c('.agendar')) return 'agendar_block';
    if (c('.solucoes')) return 'solucoes';
    if (c('.post-share, .share-actions')) return 'share';
    if (c('.form-card, form')) return 'form';
    if (c('.info-side')) return 'contato_lateral';
    if (c('.persp-header, .persp-grid, .persp-list, .feature, .posts-grid')) return 'perspectivas';
    if (c('.post-nav')) return 'post_nav';
    if (c('.post-body, article')) return 'artigo';
    if (c('.vag-list, .vagas')) return 'vagas';
    if (c('.timeline, .metodo')) return 'metodo';
    if (c('footer')) return 'footer';
    var sec = a.closest('section[id], section[class]');
    if (sec) return sec.id || (sec.className || '').split(/\s+/)[0] || 'body';
    return 'body';
  }

  function ctaRole(a) {
    if (a.dataset && a.dataset.ctaRole) return a.dataset.ctaRole;
    var cl = a.classList;
    if (cl.contains('cta-nav')) return 'nav';
    if (cl.contains('btn-primary')) return 'primary';
    if (cl.contains('btn-ghost')) return 'secondary';
    if (cl.contains('sol-item') || cl.contains('timeline-col') || cl.contains('metodo-q') ||
        cl.contains('vag-card') || cl.contains('persp-card') || cl.contains('pg-cta')) return 'card';
    return 'link';
  }

  var CTA_SELECTOR = 'a[data-cta], a.cta-nav, a.btn-primary, a.btn-ghost, a.sol-item, ' +
    'a.timeline-col, a.metodo-q, a.vag-card, a.pg-cta, a.persp-card, a.feature-link, ' +
    '.post-share a, .share-actions a, .cta-final a, .agendar a, .hero a, .page-hero a';

  // ------------------------------------------------------------------------
  // 1. Cliques (delegação global)
  // ------------------------------------------------------------------------
  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var href = a.getAttribute('href') || '';
    var hrefLower = href.toLowerCase();
    var text = cleanText(a);
    var pos = ctaPosition(a);
    var base = { link_url: a.href, link_text: text, cta_position: pos, page_family: pageFamilyFallback() };
    var slug = slugFromPath();

    // WhatsApp
    if (/^https?:\/\/(wa\.me|api\.whatsapp\.com|chat\.whatsapp\.com)/.test(hrefLower) || /^whatsapp:/.test(hrefLower)) {
      if (hrefLower.indexOf(WA_COMERCIAL) !== -1) {
        push('generate_lead', Object.assign({ lead_source: 'whatsapp', currency: 'BRL', value: 0 }, base));
      } else {
        push('share', Object.assign({ method: 'whatsapp', content_type: slug ? 'perspectiva' : 'pagina', item_id: slug || location.pathname }, base));
      }
      return;
    }
    // LinkedIn share
    if (/linkedin\.com\/(sharing|shareArticle)/.test(hrefLower)) {
      push('share', Object.assign({ method: 'linkedin', content_type: slug ? 'perspectiva' : 'pagina', item_id: slug || location.pathname }, base));
      return;
    }
    // E-mail
    if (/^mailto:/.test(hrefLower)) {
      var addr = hrefLower.replace(/^mailto:/, '').split('?')[0];
      if (addr === EMAIL_COMERCIAL) {
        push('generate_lead', Object.assign({ lead_source: 'email', currency: 'BRL', value: 0 }, base));
      } else if (addr === EMAIL_RH) {
        push('rh_email_click', base);
      } else {
        push('email_click', Object.assign({ email_domain: addr.split('@')[1] }, base));
      }
      return;
    }
    // Telefone
    if (/^tel:/.test(hrefLower)) {
      push('generate_lead', Object.assign({ lead_source: 'telefone', currency: 'BRL', value: 0 }, base));
      return;
    }
    // Vaga
    if (a.classList.contains('vag-card')) {
      var t = a.querySelector('.vc-title, h3, h4, strong');
      push('vaga_click', Object.assign({ vaga_titulo: t ? cleanText(t) : text }, base));
      return;
    }
    // Download
    if (DOWNLOAD_EXT.test(hrefLower) && !/^https?:\/\/(fonts|www\.googletagmanager)/.test(hrefLower)) {
      var file = href.split('?')[0].split('#')[0].split('/').pop();
      push('file_download', Object.assign({ file_name: file, file_extension: (file.split('.').pop() || '').toLowerCase() }, base));
      return;
    }
    // Newsletter
    if (/newsletter\.html/.test(hrefLower)) {
      push('newsletter_click', base);
      push('cta_click', Object.assign({ cta_id: 'newsletter', cta_role: ctaRole(a) }, base));
      return;
    }
    // CTA genérico
    if (a.matches(CTA_SELECTOR)) {
      push('cta_click', Object.assign({ cta_id: ctaId(a, href), cta_role: ctaRole(a) }, base));
    }
  }, { passive: true, capture: true });

  // ------------------------------------------------------------------------
  // 2. Formulário de contato (Formspree via fetch, sucesso na própria página)
  // ------------------------------------------------------------------------
  var form = document.getElementById('contato-form');
  if (form) {
    var started = false;
    var subjectOf = function () {
      var s = form.querySelector('[name="assunto"]');
      return s && s.value ? String(s.value).slice(0, 80) : undefined;
    };
    form.addEventListener('focusin', function () {
      if (started) return;
      started = true;
      push('form_start', { form_id: 'contato' });
    }, { passive: true });

    form.addEventListener('submit', function (e) {
      if (!window.fetch || !window.FormData) {
        push('form_submit', { form_id: 'contato', form_subject: subjectOf(), transport: 'native' });
        return; // fallback: envio tradicional
      }
      e.preventDefault();
      var btn = form.querySelector('button[type="submit"]');
      var msgOk = document.getElementById('contato-sucesso');
      var msgErr = document.getElementById('contato-erro');
      if (msgErr) msgErr.hidden = true;
      if (btn) { btn.disabled = true; btn.setAttribute('aria-busy', 'true'); }
      var subject = subjectOf();
      push('form_submit', { form_id: 'contato', form_subject: subject, transport: 'fetch' });

      fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { 'Accept': 'application/json' }
      }).then(function (res) {
        if (res.ok) {
          push('generate_lead', { lead_source: 'form', form_id: 'contato', form_subject: subject, cta_position: 'form', currency: 'BRL', value: 0 });
          form.hidden = true;
          if (msgOk) { msgOk.hidden = false; msgOk.focus && msgOk.focus(); }
          return;
        }
        return res.json().catch(function () { return {}; }).then(function (data) {
          var code = (data && data.errors && data.errors[0] && (data.errors[0].code || data.errors[0].message)) || ('http_' + res.status);
          throw new Error(code);
        });
      }).catch(function (err) {
        push('form_error', { form_id: 'contato', error_code: String(err && err.message || 'network').slice(0, 60) });
        if (msgErr) msgErr.hidden = false;
        if (btn) { btn.disabled = false; btn.removeAttribute('aria-busy'); }
      });
    });
  }

  // ------------------------------------------------------------------------
  // 3. Leitura de Perspectivas — marcos de rolagem 25/50/75/90
  // ------------------------------------------------------------------------
  if (isPerspectiva()) {
    var marks = [25, 50, 75, 90];
    var fired = {};
    var ticking = false;
    var slug = slugFromPath();
    var check = function () {
      var doc = document.documentElement;
      var total = doc.scrollHeight - window.innerHeight;
      if (total <= 0) return;
      var pct = Math.round(((window.scrollY || doc.scrollTop) / total) * 100);
      for (var i = 0; i < marks.length; i++) {
        var m = marks[i];
        if (!fired[m] && pct >= m) {
          fired[m] = true;
          push('perspectiva_lida', { percent_scrolled: m, article_slug: slug, article_title: document.title });
        }
      }
      if (fired[90]) window.removeEventListener('scroll', onScroll);
    };
    var onScroll = function () {
      if (ticking) return;
      ticking = true;
      setTimeout(function () { ticking = false; check(); }, 120);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    setTimeout(check, 800);
  }
})();
