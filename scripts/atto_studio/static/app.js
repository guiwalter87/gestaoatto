/* Atto Studio — frontend interactions */

// ----------------------------------------
// SHARED
// ----------------------------------------
async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || "GET",
    headers: { "Content-Type": "application/json" },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  return await res.json().catch(() => ({}));
}

function toast(msg, kind = "") {
  const t = document.getElementById("toast");
  if (!t) return;
  t.textContent = msg;
  t.className = "toast show " + kind;
  setTimeout(() => (t.className = "toast " + kind), 3000);
}

function setStatus(text) {
  const el = document.getElementById("statusLabel");
  if (el) el.textContent = text;
}

// Health check
api("/api/health").then((d) => {
  const dot = document.getElementById("health");
  if (dot) {
    dot.className = "status-dot " + (d.ok ? "ok" : "err");
    dot.title = d.ok
      ? `OK · ${d.data_count} posts · ${d.scheduled_count} agendados`
      : "Erro de conexão com o backend";
  }
});

// ----------------------------------------
// NEW POST FORM
// ----------------------------------------
function initNewPostForm(opts) {
  const f = (id) => document.getElementById(id);
  const titulo = f("titulo");
  const slug = f("slug");
  const excerpt = f("excerpt");
  const excerptCount = f("excerptCount");
  const btnCreate = f("btnCreate");
  const regenSlug = f("regenSlug");
  const result = f("resultPanel");
  const resultLog = f("resultLog");

  // ===== v2: edit mode =====
  const editData = opts && opts.editData ? opts.editData : null;
  const isEditMode = !!editData;
  let slugManuallyEdited = isEditMode;  // em edit, o slug é fixo

  if (isEditMode) {
    // Pré-popula o formulário com dados existentes
    titulo.value = editData.titulo || "";
    f("titulo_curto").value = editData.titulo_curto || "";
    slug.value = editData.slug || "";
    slug.readOnly = true;
    slug.title = "Slug não pode ser alterado em modo edição (preserva URLs e capas).";
    if (regenSlug) regenSlug.style.display = "none";
    if (editData.categoria) f("categoria").value = editData.categoria;
    f("data").value = editData.data || "";
    f("minutes").value = editData.minutes || 10;
    excerpt.value = editData.excerpt || "";
    f("body").value = editData.body || "";
    f("sources").value = editData.sources || "";
    setStatus(`Editando #${editData.numero} — salve quando terminar.`);
  }

  // Auto-slug
  titulo.addEventListener("input", async () => {
    if (slugManuallyEdited) return;
    const r = await api("/api/slug", { method: "POST", body: { titulo: titulo.value } });
    slug.value = r.slug || "";
  });
  slug.addEventListener("input", () => { slugManuallyEdited = true; });
  regenSlug.addEventListener("click", async () => {
    const r = await api("/api/slug", { method: "POST", body: { titulo: titulo.value } });
    slug.value = r.slug || "";
    slugManuallyEdited = false;
  });

  // Excerpt counter
  const updateCount = () => { excerptCount.textContent = excerpt.value.length; };
  excerpt.addEventListener("input", updateCount);
  updateCount();

  // ===== v2: duplicate check live (com debounce) =====
  let dupTimer = null;
  const dupBanner = document.getElementById("dupBanner");
  const dupList = document.getElementById("dupList");

  function renderDupes(similar, risk) {
    if (!dupBanner) return;
    if (!similar || similar.length === 0 || risk === "baixo") {
      dupBanner.classList.add("hidden");
      return;
    }
    dupBanner.classList.remove("hidden");
    dupBanner.classList.remove("risk-alto", "risk-medio", "risk-baixo");
    dupBanner.classList.add("risk-" + risk);
    dupList.innerHTML = "";
    similar.slice(0, 3).forEach((p) => {
      const li = document.createElement("li");
      const pct = Math.round(p.similarity * 100);
      const status = p.data ? new Date(p.data).toLocaleDateString("pt-BR") : "";
      li.innerHTML = `<strong>#${p.numero}</strong> — ${p.titulo} <span class="sim">${pct}% similaridade · ${status}</span>`;
      dupList.appendChild(li);
    });
  }

  function checkDupes() {
    if (isEditMode) return; // não checa em edit
    clearTimeout(dupTimer);
    dupTimer = setTimeout(async () => {
      const t = titulo.value.trim();
      const e = excerpt.value.trim();
      if (t.length < 15) {
        if (dupBanner) dupBanner.classList.add("hidden");
        return;
      }
      const r = await api("/api/duplicate-check", {
        method: "POST",
        body: { titulo: t, excerpt: e, body: f("body").value },
      });
      if (r.ok) renderDupes(r.similar, r.risk);
    }, 600);
  }
  titulo.addEventListener("input", checkDupes);
  excerpt.addEventListener("input", checkDupes);

  // ---- IMPORTAR DO CHAT (paste de JSON) ----
  let importQueue = [];   // posts em fila de batch
  let queueIndex = 0;

  const btnImport = f("btnImport");
  const importDialog = f("importDialog");
  const importJson = f("importJson");
  const btnImportConfirm = f("btnImportConfirm");
  const importQueueEl = f("importQueue");
  const importQueueList = f("importQueueList");

  function fillFormFromPost(post) {
    const setVal = (id, v) => { if (v !== undefined && v !== null) f(id).value = v; };
    setVal("titulo", post.titulo || "");
    setVal("titulo_curto", post.titulo_curto || "");
    setVal("slug", post.slug || "");
    if (post.categoria) f("categoria").value = post.categoria;
    if (post.author) f("author").value = post.author;
    setVal("data", post.data || "");
    setVal("minutes", post.minutes || 10);
    setVal("excerpt", post.excerpt || "");
    setVal("body", post.body || "");
    setVal("sources", post.sources || "");
    updateCount();
    if (post.titulo) titulo.dispatchEvent(new Event("input"));
  }

  function renderQueue() {
    if (importQueue.length <= 1) {
      importQueueEl.classList.add("hidden");
      return;
    }
    importQueueEl.classList.remove("hidden");
    importQueueList.innerHTML = "";
    importQueue.forEach((p, i) => {
      const li = document.createElement("li");
      li.textContent = `${p.titulo || "(sem título)"} · ${p.data || "?"}`;
      if (i < queueIndex) li.classList.add("is-done");
      if (i === queueIndex) li.classList.add("is-current");
      importQueueList.appendChild(li);
    });
  }

  if (btnImport) {
    btnImport.addEventListener("click", () => {
      importJson.value = "";
      importDialog.showModal();
      setTimeout(() => importJson.focus(), 50);
    });
  }

  if (btnImportConfirm) {
    btnImportConfirm.addEventListener("click", () => {
      let parsed;
      try {
        parsed = JSON.parse(importJson.value.trim());
      } catch (e) {
        toast("JSON inválido: " + e.message, "error");
        return;
      }
      // Aceita objeto único ou array
      if (Array.isArray(parsed)) {
        importQueue = parsed;
      } else if (parsed.posts && Array.isArray(parsed.posts)) {
        importQueue = parsed.posts;
      } else {
        importQueue = [parsed];
      }
      if (!importQueue.length) {
        toast("Nenhum post encontrado no JSON.", "error");
        return;
      }
      queueIndex = 0;
      fillFormFromPost(importQueue[0]);
      renderQueue();
      importDialog.close();
      const msg = importQueue.length === 1
        ? "Formulário preenchido, revise e clique em Criar."
        : `${importQueue.length} posts na fila. O formulário tem o post 1; depois de criar, clique de novo em Criar para o próximo.`;
      toast(msg, "success");
      setStatus(importQueue.length === 1
        ? "Pronto para criar."
        : `Fila: post ${queueIndex + 1} de ${importQueue.length}.`);
    });
  }

  // Hook após criação bem-sucedida — se há fila, avança para o próximo
  window.__attoOnCreateSuccess = (r) => {
    if (importQueue.length > 1 && queueIndex < importQueue.length - 1) {
      queueIndex++;
      fillFormFromPost(importQueue[queueIndex]);
      renderQueue();
      setStatus(`Fila: post ${queueIndex + 1} de ${importQueue.length}. Clique em Criar para continuar.`);
    } else if (importQueue.length > 1) {
      // Última, marca tudo como done
      queueIndex = importQueue.length;
      renderQueue();
      setStatus("Fila concluída.");
      setTimeout(() => { importQueue = []; importQueueEl.classList.add("hidden"); }, 4000);
    }
  };

  // Create
  btnCreate.addEventListener("click", async () => {
    const data = {
      titulo: titulo.value.trim(),
      titulo_curto: f("titulo_curto").value.trim(),
      slug: slug.value.trim(),
      categoria: f("categoria").value,
      author: f("author").value,
      data: f("data").value,
      minutes: parseInt(f("minutes").value || "10", 10),
      excerpt: excerpt.value.trim(),
      body: f("body").value,
      sources: f("sources").value,
      scheduled: true,  // sempre tenta agendar; backend decide se é futuro
    };

    if (!data.titulo || !data.body || !data.excerpt || !data.data) {
      toast("Preencha pelo menos título, data, resumo e texto.", "error");
      return;
    }

    btnCreate.disabled = true;

    // v2: route to /api/edit if in edit mode (preserves numero + capas)
    let r;
    if (isEditMode) {
      setStatus("Salvando alterações e regenerando capa (~10-15s)...");
      r = await api(`/api/edit/${editData.slug}`, { method: "POST", body: data });
      // edit endpoint doesn't return capa_log / social; fill defaults
      r.scheduled = r.scheduled || false;
      r.scheduled_msg = r.message || "alterações salvas";
      r.post_path = `site/perspectivas/${editData.slug}.html`;
      r.capa_log = r.capa_ok ? "Capa regenerada." : "Capa não regenerada.";
    } else {
      setStatus("Criando post e gerando capas (pode levar 10-20s)...");
      r = await api("/api/create", { method: "POST", body: data });
    }

    btnCreate.disabled = false;

    if (!r.ok) {
      result.classList.remove("hidden");
      result.classList.remove("success");
      result.classList.add("error");
      f("resultTitle").textContent = "Erro ao criar";
      resultLog.textContent = r.error || "Erro desconhecido";
      setStatus("Erro.");
      toast("Falha na criação", "error");
      return;
    }

    result.classList.remove("hidden");
    result.classList.remove("error");
    result.classList.add("success");
    const status = r.scheduled ? `Post agendado: ${r.scheduled_msg}` : "Post publicado.";
    f("resultTitle").textContent = `${status} (${r.slug})`;
    resultLog.textContent = [
      `Slug: ${r.slug}`,
      `Arquivo: ${r.post_path}`,
      "",
      "Capas:",
      r.capa_log,
    ].join("\n");
    setStatus(r.scheduled ? "Agendado." : "Publicado localmente.");
    toast(status, "success");

    // Avança fila do batch import, se houver
    if (typeof window.__attoOnCreateSuccess === "function") {
      window.__attoOnCreateSuccess(r);
    }

    // Popula bloco de capas
    const t = Date.now();
    const formats = [
      ["Hero", "hero"], ["Og", "og"], ["Feed", "ig-feed"], ["Story", "ig-story"]
    ];
    const linkIds = { hero: "capaHeroLink", og: "capaOgLink",
                      "ig-feed": "capaFeedLink", "ig-story": "capaStoryLink" };
    const thumbIds = { hero: "capaThumbHero", og: "capaThumbOg",
                       "ig-feed": "capaThumbFeed", "ig-story": "capaThumbStory" };
    Object.entries(linkIds).forEach(([fmt, id]) => {
      const url = `/api/capa/${r.slug}/${fmt}?t=${t}`;
      f(id).href = url;
      f(id).download = `${r.slug}_${fmt}.png`;
      f(thumbIds[fmt]).src = url;
    });

    // Popula textos de redes sociais
    if (r.social) {
      f("socialLinkedin").value = r.social.linkedin || "";
      f("socialInstagram").value = r.social.instagram || "";
    }

    // Wire dos botões "Copiar"
    document.querySelectorAll("[data-copy-target]").forEach((btn) => {
      btn.onclick = async () => {
        const target = f(btn.dataset.copyTarget);
        if (!target) return;
        try {
          await navigator.clipboard.writeText(target.value);
          toast("Copiado.", "success");
        } catch (e) {
          target.select();
          document.execCommand("copy");
          toast("Copiado.", "success");
        }
      };
    });

    // Botão de ver capa
    f("btnViewCover").onclick = () => {
      f("coverImg").src = `/api/capa/${r.slug}/hero?t=${Date.now()}`;
      f("coverDialog").showModal();
    };

    // Botão git push
    f("btnGitPush").onclick = async () => {
      setStatus("Commitando e enviando...");
      const g = await api("/api/git-commit-push", {
        method: "POST",
        body: { message: `feat(perspectivas): ${r.scheduled ? "agendar" : "publicar"} ${r.slug}` },
      });
      resultLog.textContent += "\n\n— GIT —\n" + g.log;
      if (g.ok) {
        setStatus("Enviado pro GitHub.");
        toast("Push feito. GitHub Pages atualiza em ~10 min.", "success");
      } else {
        setStatus("Erro no push.");
        toast("Falha no push", "error");
      }
    };
  });
}

// ----------------------------------------
// POSTS LIST
// ----------------------------------------
function initPostsList() {
  document.querySelectorAll(".filter-bar .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".filter-bar .chip").forEach((c) => c.classList.remove("is-active"));
      chip.classList.add("is-active");
      const filter = chip.dataset.filter;
      document.querySelectorAll(".post-row").forEach((row) => {
        if (filter === "all" || row.dataset.status === filter) {
          row.classList.remove("is-hidden");
        } else {
          row.classList.add("is-hidden");
        }
      });
    });
  });
}

async function regenCover(slug) {
  toast("Gerando capas...", "");
  const r = await api(`/api/run-capa/${slug}`, { method: "POST" });
  if (r.ok) {
    toast("Capas regeneradas.", "success");
    // Recarrega imagens
    document.querySelectorAll(`img[src*='/${slug}/hero']`).forEach((img) => {
      img.src = img.src.split("?")[0] + "?t=" + Date.now();
    });
  } else {
    toast("Falha: " + (r.log || "").slice(0, 80), "error");
  }
}

// ----------------------------------------
// POSTS — DELETE / EDIT / RESCHEDULE / PUBLISH NOW (v2)
// ----------------------------------------
function deletePost(slug, numero) {
  const dlg = document.getElementById("deleteDialog");
  const label = document.getElementById("deleteNumLabel");
  const btn = document.getElementById("deleteConfirm");
  label.textContent = `${numero} (${slug})`;
  btn.onclick = async () => {
    btn.disabled = true;
    const r = await api(`/api/delete/${slug}`, { method: "POST" });
    btn.disabled = false;
    dlg.close();
    if (r.ok) {
      toast(r.message || "Post excluído.", "success");
      // Remove o cartão da tela sem reload
      document.querySelector(`.post-row[data-slug='${slug}']`)?.remove();
    } else {
      toast("Falha ao excluir: " + (r.error || ""), "error");
    }
  };
  dlg.showModal();
}

function reschedulePost(slug, currentDate) {
  const dlg = document.getElementById("rescheduleDialog");
  const label = document.getElementById("rescheduleSlugLabel");
  const input = document.getElementById("rescheduleDate");
  const btn = document.getElementById("rescheduleConfirm");
  label.textContent = slug;
  input.value = currentDate || "";
  btn.onclick = async () => {
    const newDate = input.value;
    if (!newDate) {
      toast("Escolha uma data.", "error");
      return;
    }
    btn.disabled = true;
    const r = await api(`/api/reschedule/${slug}`, { method: "POST", body: { data: newDate } });
    btn.disabled = false;
    dlg.close();
    if (r.ok) {
      toast(r.message || "Reagendado.", "success");
      setTimeout(() => location.reload(), 800);
    } else {
      toast("Falha: " + (r.error || ""), "error");
    }
  };
  dlg.showModal();
}

function publishNow(slug, numero) {
  const dlg = document.getElementById("publishDialog");
  const label = document.getElementById("publishNumLabel");
  const btn = document.getElementById("publishConfirm");
  label.textContent = `Perspectiva ${numero}`;
  btn.onclick = async () => {
    btn.disabled = true;
    const r = await api(`/api/publish-now/${slug}`, { method: "POST" });
    btn.disabled = false;
    dlg.close();
    if (r.ok) {
      toast(r.message || "Publicado.", "success");
      setTimeout(() => location.reload(), 800);
    } else {
      toast("Falha: " + (r.error || ""), "error");
    }
  };
  dlg.showModal();
}

function editPost(slug) {
  // Abre o formulário de edição numa nova janela (reutiliza o /?edit=slug)
  window.location.href = `/?edit=${encodeURIComponent(slug)}`;
}

// ----------------------------------------
// CALENDAR
// ----------------------------------------
function initCalendar(posts, todayIso) {
  const today = new Date(todayIso + "T12:00:00");
  let cursor = new Date(today.getFullYear(), today.getMonth(), 1);

  const monthLabel = document.getElementById("monthLabel");
  const calEl = document.getElementById("calendar");

  function render() {
    const y = cursor.getFullYear();
    const m = cursor.getMonth();
    const monthNames = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
    monthLabel.textContent = `${monthNames[m]} de ${y}`;

    calEl.innerHTML = "";
    ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"].forEach((d) => {
      const h = document.createElement("div");
      h.className = "cal-head";
      h.textContent = d;
      calEl.appendChild(h);
    });

    const firstDay = new Date(y, m, 1).getDay();
    const lastDate = new Date(y, m + 1, 0).getDate();
    for (let i = 0; i < firstDay; i++) {
      const c = document.createElement("div");
      c.className = "cal-cell empty";
      calEl.appendChild(c);
    }
    for (let d = 1; d <= lastDate; d++) {
      const c = document.createElement("div");
      c.className = "cal-cell";
      const iso = `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      if (iso === todayIso) c.classList.add("today");

      const day = document.createElement("div");
      day.className = "cal-day";
      day.textContent = d;
      c.appendChild(day);

      const events = posts.filter((p) => (p.publish_date || p.data) === iso);
      events.forEach((p) => {
        const ev = document.createElement("div");
        ev.className = "cal-event " + (p.status || "");
        ev.title = `${p.titulo || p.h3 || p.slug}\n${p.categoria || ""}`;
        ev.textContent = (p.titulo || p.h3 || p.slug).slice(0, 50);
        c.appendChild(ev);
      });
      calEl.appendChild(c);
    }
  }

  document.getElementById("prevMonth").onclick = () => {
    cursor.setMonth(cursor.getMonth() - 1);
    render();
  };
  document.getElementById("nextMonth").onclick = () => {
    cursor.setMonth(cursor.getMonth() + 1);
    render();
  };
  render();
}
